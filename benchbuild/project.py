"""Project handling for the benchbuild study."""
import copy
import logging
import uuid
import warnings
from abc import abstractmethod
from functools import partial
from os import listdir, path
from typing import Callable, Iterable

from plumbum import ProcessExecutionError, local
from pygtrie import StringTrie

import benchbuild.extensions as ext
import benchbuild.signals as signals
import benchbuild.utils.run as ur
from benchbuild.settings import CFG
from benchbuild.utils.cmd import mkdir, rm, rmdir
from benchbuild.utils.container import Gentoo
from benchbuild.utils.db import persist_project
from benchbuild.utils.run import RunInfo, in_builddir, store_config, unionfs
from benchbuild.utils.versions import get_version_from_cache_dir
from benchbuild.utils.wrapping import wrap

LOG = logging.getLogger(__name__)


class ProjectRegistry(type):
    """Registry for benchbuild projects."""

    projects = StringTrie()

    def __init__(cls, name, bases, attrs):
        """Register a project in the registry."""
        super(ProjectRegistry, cls).__init__(name, bases, attrs)

        if cls.NAME is not None and \
           cls.DOMAIN is not None and \
           cls.GROUP is not None:

           key = "{name}/{group}".format(name=cls.NAME, group=cls.GROUP)
           ProjectRegistry.projects[key] = cls


class ProjectDecorator(ProjectRegistry):
    """
    Decorate the interface of a project with the in_builddir decorator.

    This is just a small safety net for benchbuild users, because we make
    sure to run every project method in the project's build directory.
    """

    decorated_methods = ["build", "configure", "download", "prepare",
                         "run_tests"]

    def __init__(cls, name, bases, attrs):
        unionfs_deco = None
        if CFG["unionfs"]["enable"].value():
            image_dir = CFG["unionfs"]["image"].value()
            prefix = CFG["unionfs"]["image_prefix"].value()
            unionfs_deco = partial(unionfs, image_dir=image_dir,
                                   image_prefix=prefix)
        config_deco = store_config

        methods = ProjectDecorator.decorated_methods
        for key, value in attrs.items():
            if (key in methods) and hasattr(cls, key):
                wrapped_fun = value
                if key == 'configure':
                    wrapped_fun = config_deco(wrapped_fun)

                if unionfs_deco is not None:
                    wrapped_fun = unionfs_deco()(wrapped_fun)

                wrapped_fun = in_builddir('.')(wrapped_fun)
                setattr(cls, key, wrapped_fun)

        super(ProjectDecorator, cls).__init__(name, bases, attrs)


class Project(object, metaclass=ProjectDecorator):
    """
    benchbuild's Project class.

    A project defines how run-time testing and cleaning is done for this
        IR project
    """

    NAME = None
    DOMAIN = None
    GROUP = None
    VERSION = None
    SRC_FILE = None
    CONTAINER = Gentoo()

    def __new__(cls, *args, **kwargs):
        """Create a new project instance and set some defaults."""
        new_self = super(Project, cls).__new__(cls)
        if cls.NAME is None:
            raise AttributeError(
                "{0} @ {1} does not define a NAME class attribute.".format(
                    cls.__name__, cls.__module__))
        if cls.DOMAIN is None:
            raise AttributeError(
                "{0} @ {1} does not define a DOMAIN class attribute.".format(
                    cls.__name__, cls.__module__))
        if cls.GROUP is None:
            raise AttributeError(
                "{0} @ {1} does not define a GROUP class attribute.".format(
                    cls.__name__, cls.__module__))
        if cls.SRC_FILE is None:
            warnings.warn(
                "{0} @ {1} does not offer a source file yet.".format(
                    cls.__name__, cls.__module__))
            cls.SRC_FILE = "<not-set>"
        if cls.CONTAINER is None:
            warnings.warn(
                "{0} @ {1} does not offer a container yet.".format(
                    cls.__name__, cls.__module__))

        new_self.name = cls.NAME
        new_self.domain = cls.DOMAIN
        new_self.group = cls.GROUP
        new_self.src_file = cls.SRC_FILE
        new_self.version = lambda: get_version_from_cache_dir(cls.SRC_FILE)
        new_self.container = cls.CONTAINER

        return new_self

    def __init__(self, exp, group: str = None):
        """
        Setup a new project.

        Args:
            exp: The experiment this project belongs to.
            group: The group this project belongs to. This is useful for
                finding group specific test input files.
        """
        self.experiment = exp
        if group is not None:
            self.group = group
        self.builddir = path.join(str(CFG["build_dir"]),
            "{0}-{1}-{2}-{3}".format(exp.name, self.name, self.group, exp.id))
        if group:
            self.testdir = path.join(
                str(CFG["test_dir"]), self.domain, group, self.name)
        else:
            self.testdir = path.join(
                str(CFG["test_dir"]), self.domain, self.name)

        self.cflags = []
        self.ldflags = []
        self.compiler_extension = \
            ext.RunWithTimeout(ext.RunCompiler(self, exp))

        self.run_f = path.join(self.builddir, self.name)
        persist_project(self)

    def run_tests(self, experiment, run):
        """
        Run the tests of this project.

        Clients override this method to provide customized run-time tests.

        Args:
            experiment: The experiment we run this project under
            run: A function that takes the run command.
        """
        exp = wrap(self.run_f, experiment)
        run(exp)

    def run(self, experiment):
        """
        Run the tests of this project.

        This method initializes the default environment and takes care of
        cleaning up the mess we made, after a successfull run.

        Args:
            experiment: The experiment we run this project under
        """
        from benchbuild.utils.run import (begin_run_group, end_run_group,
                                          fail_run_group)
        CFG["experiment"] = self.experiment.name
        CFG["project"] = self.NAME
        CFG["domain"] = self.DOMAIN
        CFG["group"] = self.GROUP
        CFG["version"] = self.VERSION
        CFG["db"]["run_group"] = str(self.run_uuid)
        with local.cwd(self.builddir):
            group, session = begin_run_group(self)
            signals.handlers.register(fail_run_group, group, session)

            try:
                self.run_tests(experiment, ur.run)
                end_run_group(group, session)
            except ProcessExecutionError:
                fail_run_group(group, session)
                raise
            except KeyboardInterrupt:
                fail_run_group(group, session)
                raise
            finally:
                signals.handlers.deregister(fail_run_group, group, session)

    def clean(self):
        """Clean the project build directory."""
        if path.exists(self.builddir) and listdir(self.builddir) == []:
            rmdir(self.builddir)
        elif path.exists(self.builddir) and listdir(self.builddir) != []:
            rm("-rf", self.builddir)

    @property
    def compiler_extension(self):
        """Return the compiler extension registered to this project."""
        try:
            return self._compiler_extension
        except AttributeError:
            self._compiler_extension = None
            return self._compiler_extension

    @compiler_extension.setter
    def compiler_extension(self,
                           func: Callable[[str, Iterable[str]],
                                          RunInfo]) -> None:
        """
        Set a function as compiler extension.

        Args:
            func: The compiler extension function. The minimal signature that
                is required is ::
                    f(cc, **kwargs)
                where cc is the original compiler command.

        """
        self._compiler_extension = func

    @property
    def runtime_extension(self):
        """Return the runtime extension registered for this project."""
        try:
            return self._runtime_extension
        except AttributeError:
            self._runtime_extension = None
            return self._runtime_extension

    @runtime_extension.setter
    def runtime_extension(self,
                          func: Callable[[str, Iterable[str]],
                                         RunInfo]) -> None:
        """
        Set a function as compiler extension.

        Args:
            func: The compiler extension function. The minimal signature that
                is required is ::
                    f(cc, **kwargs)
                where cc is the original compiler command.

        """
        self._runtime_extension = func

    @property
    def run_uuid(self):
        """
        Get the UUID that groups all tests for one project run.

        Args:
            create_new: Create a fresh UUID (Default: False)
        """
        from os import getenv
        from uuid import uuid4

        try:
            if self._run_uuid is None:
                self._run_uuid = getenv("BB_DB_RUN_GROUP", uuid4())
        except AttributeError:
            self._run_uuid = getenv("BB_DB_RUN_GROUP", uuid4())
        return self._run_uuid

    @run_uuid.setter
    def run_uuid(self, value):
        """
        Set a new UUID for this project.

        Args:
            value: The new value to set.
        """
        from uuid import UUID
        if isinstance(value, UUID):
            self._run_uuid = value

    def prepare(self):
        """Prepare the build diretory."""
        if not path.exists(self.builddir):
            mkdir(self.builddir)

    @abstractmethod
    def download(self):
        """Download the input source for this project."""

    @abstractmethod
    def configure(self):
        """Configure the project."""

    @abstractmethod
    def build(self):
        """Build the project."""

    def clone(self):
        """Create a deepcopy of ourself."""
        new_p = copy.deepcopy(self)
        new_p.run_uuid = uuid.uuid4()
        return new_p


def populate(projects_to_filter=None, group=None):
    """
    Populate the list of projects that belong to this experiment.

    Args:
        projects_to_filter (list):
            List of projects we want to assign to this experiment.
            We intersect the list of projects with the list of supported
            projects to get the list of projects that belong to this
            experiment.
        group (str):
            In addition to the project filter, we provide a way to filter
            whole groups.
    """
    if projects_to_filter is None:
        projects_to_filter = []

    import benchbuild.projects as all_projects
    all_projects.discover()

    prjs = ProjectRegistry.projects
    if projects_to_filter:
        prjs = {}
        for filter_project in set(projects_to_filter):
            try:
                prjs.update({x : y for x, y in ProjectRegistry.projects.items(prefix=filter_project)})
            except KeyError:
                pass

    if group:
        prjs = {
            name: cls
            for name, cls in prjs.items() if cls.GROUP == group
        }

    return {
        x: prjs[x] for x in prjs
        if prjs[x].DOMAIN != "debug" or x in projects_to_filter}