"""Test benchbuild's runtime wrappers."""
import tempfile
import unittest
import os

from plumbum import local
from plumbum.cmd import rm

import benchbuild.experiments.empty as empty
import benchbuild.project as project
import benchbuild.utils.compiler as compilers
import benchbuild.utils.wrapping as wrappers


class EmptyProject(project.Project):
    NAME = "test_empty"
    DOMAIN = "debug"
    GROUP = "debug"
    SRC_FILE = "none"

    def build(self):
        pass

    def configure(self):
        pass

    def download(self):
        pass


class WrapperTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp_dir = tempfile.mkdtemp()

    @classmethod
    def tearDownClass(cls):
        if os.path.exists(cls.tmp_dir):
            rm("-r", cls.tmp_dir)


class RunCompiler(WrapperTests):
    def test_create(self):
        with local.cwd(self.tmp_dir):
            cmd = compilers.cc(EmptyProject(empty.Empty()))
        self.assertTrue(os.path.exists(str(cmd)))


class RunStatic(WrapperTests):
    def setUp(self):
        self.tmp_script_fd, self.tmp_script = tempfile.mkstemp(
            dir=self.tmp_dir)
        self.assertTrue(os.path.exists(self.tmp_script))

    def test_create(self):
        with local.cwd(self.tmp_dir):
            self.cmd = wrappers.wrap(self.tmp_script,
                                     EmptyProject(empty.Empty()))
        self.assertTrue(os.path.exists(str(self.cmd)))
        self.assertTrue(os.path.exists("{}.bin".format(self.tmp_script)))


class RunDynamic(WrapperTests):
    def setUp(self):
        self.tmp_script_fd, self.tmp_script = tempfile.mkstemp(
            dir=self.tmp_dir)
        self.assertTrue(os.path.exists(self.tmp_script))

    def test_create(self):
        with local.cwd(self.tmp_dir):
            cmd = wrappers.wrap_dynamic(
                EmptyProject(empty.Empty()), self.tmp_script)
        self.assertTrue(os.path.exists(str(cmd)))
