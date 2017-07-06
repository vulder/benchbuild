"""
The 'polyjit' experiment.

This experiment uses likwid to measure the performance of all binaries
when running with polyjit support enabled.
"""
import copy
import glob
import logging
import uuid
from abc import abstractmethod
import os

from plumbum import local

import benchbuild.extensions as ext
from benchbuild.utils.actions import (Any, RequireAll)
from benchbuild.experiment import RuntimeExperiment
from benchbuild.utils.dict import ExtensibleDict, extend_as_list


LOG = logging.getLogger(__name__)


class PolyJITConfig(object):
    __config = ExtensibleDict(extend_as_list)

    @property
    def argv(self):
        return PolyJITConfig.__config

    def value_to_str(self, key):
        if key not in self.argv:
            return ""
        value = self.argv[key]
        if isinstance(value, list):
            value = " ".join(value)
        LOG.debug("Constructed: {0}={1}".format(key, value))
        return value


class EnablePolyJIT(PolyJITConfig, ext.Extension):
    def __call__(self, binary_command, *args, **kwargs):
        with local.env(PJIT_ARGS=self.value_to_str('PJIT_ARGS')):
            ret = self.call_next(binary_command, *args, **kwargs)
        return ret


class DisablePolyJIT(PolyJITConfig, ext.Extension):
    def __call__(self, binary_command, *args, **kwargs):
        ret = None
        with self.argv(PJIT_ARGS="-polli-no-specialization"):
            with local.env(PJIT_ARGS=self.value_to_str('PJIT_ARGS')):
                ret = self.call_next(binary_command, *args, **kwargs)
        return ret


class RegisterPolyJITLogs(PolyJITConfig, ext.LogTrackingMixin, ext.Extension):
    def __call__(self, *args, **kwargs):
        """Redirect to RunWithTime, but register additional logs."""
        with self.argv(PJIT_ARGS="-polli-enable-log"):
            ret = self.call_next(*args, **kwargs)
        curdir = os.path.realpath(os.path.curdir)
        files = glob.glob(os.path.join(curdir, "polyjit.*.log"))

        for file in files:
            self.add_log(file)

        return ret

class RunWithLikwid(ext.RuntimeExtension):
    """
    Run the given file wrapped by likwid.

    Args:
        project: The benchbuild.project.
        experiment: The benchbuild.experiment.
        config: The benchbuild.settings.config.
        jobs: Number of cores we should use for this exection.
        run_f: The file we want to execute.
        args: List of arguments that should be passed to the wrapped binary.
        **kwargs: Dictionary with our keyword args. We support the following
            entries:

            project_name: The real name of our project. This might not
                be the same as the configured project name, if we got wrapped
                with ::benchbuild.project.wrap_dynamic
            has_stdin: Signals whether we should take care of stdin.
    """

    def __call__(self, binary_command, *args, may_wrap=True, **kwargs):
        from benchbuild.settings import CFG
        from benchbuild.utils.db import persist_likwid, persist_config
        from benchbuild.likwid import get_likwid_perfctr
        from benchbuild.utils.cmd import rm

        self.project.name = kwargs.get("project_name", self.project.name)

        likwid_f = self.project.name + ".txt"
        likwid_path = os.path.join(CFG["likwiddir"], "bin")
        likwid_perfctr = local[os.path.join(likwid_path, "likwid-perfctr")]

        jobs = self.config['jobs']
        for group in ["CLOCK"]:
            run_cmd = \
                likwid_perfctr["-O", "-o", likwid_f, "-m",
                               "-C", "0-{0:d}".format(jobs),
                               "-g", group, binary_command]

            res = []
            with local.env(POLLI_ENABLE_LIKWID=1):
                res = self.call_next(run_cmd, *args, **kwargs)

            likwid_measurement = get_likwid_perfctr(likwid_f)
            for run_info in res:
                persist_likwid(run_info.db_run, run_info.session, likwid_measurement)
                persist_config(run_info.db_run, run_info.session, {
                    "cores": str(jobs),
                    "likwid.group": group
                })
            rm("-f", likwid_f)


class PolyJIT(RuntimeExperiment):
    """The polyjit experiment."""

    @classmethod
    def init_project(cls, project):
        """
        Execute the benchbuild experiment.

        We perform this experiment in 2 steps:
            1. with likwid disabled.
            2. with likwid enabled.

        Args:
            project: The project we initialize.

        Returns:
            The initialized project.
        """
        project.ldflags += ["-lpjit", "-lgomp"]
        project.cflags = ["-fno-omit-frame-pointer",
                          "-rdynamic",
                          "-Xclang", "-load", "-Xclang", "LLVMPolyJIT.so",
                          "-O3",
                          "-mllvm", "-polli-enable-log",
                          "-mllvm", "-polli-allow-modref-calls",
                          "-mllvm", "-polli"]
        return project

    @abstractmethod
    def actions_for_project(self, project):
        pass


class PolyJITFull(PolyJIT):
    """
    An experiment that executes all projects with PolyJIT support.

    This is our default experiment for speedup measurements.
    """

    NAME = "pj"

    def actions_for_project(self, p):
        from benchbuild.settings import CFG

        p.cflags = ["-O3", "-fno-omit-frame-pointer"]

        actns = []
        rawp = copy.deepcopy(p)
        rawp.run_uuid = uuid.uuid4()
        rawp.runtime_extension = \
            ext.RunWithTime(
                ext.SetThreadLimit(
                    ext.RuntimeExtension(rawp, self, config={"jobs": 1}),
                    config={"jobs": 1}))
        actns.append(RequireAll(self.default_runtime_actions(rawp)))

        pollyp = copy.deepcopy(p)
        pollyp.run_uuid = uuid.uuid4()
        pollyp.cflags = ["-Xclang", "-load",
                         "-Xclang", "LLVMPolly.so",
                         "-mllvm", "-polly", "-mllvm", "-polly-parallel"]
        pollyp.runtime_extension = \
            ext.RunWithTime(
                ext.SetThreadLimit(
                    ext.RuntimeExtension(pollyp, self, config={"jobs": 1}),
                    config={"jobs": 1}))
        actns.append(RequireAll(self.default_runtime_actions(pollyp)))

        jitp = copy.deepcopy(p)
        jitp = PolyJIT.init_project(jitp)
        norecomp = copy.deepcopy(jitp)
        norecomp.cflags += ["-mllvm", "-polli-no-recompilation"]

        for i in range(2, int(str(CFG["jobs"])) + 1):
            cp = copy.deepcopy(norecomp)
            cp.run_uuid = uuid.uuid4()
            cfg = {
                "jobs": i,
                "cores": str(i-1),
                "cores-config": str(i),
                "recompilation": "disabled"
            }

            cp.runtime_extension = \
                ext.LogAdditionals(
                    RegisterPolyJITLogs(
                        ext.RunWithTime(
                            DisablePolyJIT(
                                ext.SetThreadLimit(
                                    ext.RuntimeExtension(cp, self, config=cfg),
                                    config=cfg
                                )))))
            actns.append(RequireAll(self.default_runtime_actions(cp)))

        for i in range(2, int(str(CFG["jobs"])) + 1):
            cp = copy.deepcopy(jitp)
            cp.run_uuid = uuid.uuid4()
            cfg = {
                "jobs": i,
                "cores": str(i-1),
                "cores-config": str(i),
                "recompilation": "enabled"
            }
            cp.runtime_extension = \
                ext.LogAdditionals(
                    RegisterPolyJITLogs(
                        ext.RunWithTime(
                            EnablePolyJIT(
                                ext.SetThreadLimit(
                                    ext.RuntimeExtension(cp, self, config=cfg),
                                    config=cfg
                                )))))
            actns.append(RequireAll(self.default_runtime_actions(cp)))

        return [Any(actns)]
