#!/usr/bin/evn python
# encoding: utf-8

from pprof.project import ProjectFactory, log_with, log
from pprof.settings import config
from group import PprofGroup

from os import path
from glob import glob
from plumbum import FG, local
from plumbum.cmd import cat


class Crocopat(PprofGroup):

    """ crocopat benchmark """

    class Factory:

        def create(self, exp):
            return Crocopat(exp, "crocopat", "verification")
    ProjectFactory.addFactory("Crocopat", Factory())

    def run_tests(self, experiment):
        exp = experiment(self.run_f)

        programs = glob(path.join(self.testdir, "programs", "*.rml"))
        projects = glob(path.join(self.testdir, "projects", "*.rsf"))
        for program in programs:
            for project in projects:
                (cat[project] | exp[program]) & FG(retcode=None)

    src_dir = "crocopat-2.1.4"
    src_file = src_dir + ".zip"
    src_uri = "http://crocopat.googlecode.com/files/" + src_file

    def download(self):
        from pprof.utils.downloader import Wget
        from plumbum.cmd import unzip

        crocopat_dir = path.join(self.builddir, self.src_dir)
        with local.cwd(self.builddir):
            Wget(self.src_uri, self.src_file)
            unzip(path.join(self.builddir, self.src_file))

    def configure(self):
        pass

    def build(self):
        from plumbum.cmd import make
        from pprof.utils.compiler import clang_cxx

        crocopat_dir = path.join(self.builddir, self.src_dir, "src")
        with local.cwd(crocopat_dir):
            cflags = self.cflags + ["-I.", "-ansi"]
            ldflags = self.ldflags + ["-L.", "-lrelbdd"]
            make["CXX=" + str(clang_cxx()),
                 "CFLAGS=" + " ".join(cflags),
                 "LFLAGS=" + " ".join(ldflags)] & FG