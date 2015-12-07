#!/usr/bin/evn python
#

from pprof.project import Project
from pprof.settings import config
from os import path


class PprofGroup(Project):
    DOMAIN = 'pprof'

    path_suffix = "src"

    def __init__(self, exp, name, domain):
        super(PprofGroup, self).__init__(exp, name, domain, "pprof")
        self.sourcedir = path.join(config["sourcedir"], "src", name)
        self.setup_derived_filenames()
