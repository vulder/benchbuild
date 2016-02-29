"""
Generic experiment to test portage packages within gentoo chroot.
"""
from pprof.projects.gentoo.gentoo import GentooGroup
from pprof.utils.run import run, uchroot
from plumbum import local

class AutoPortage(GentooGroup):
    """
    Generic portage experiment.
    """

    def build(self):
        with local.cwd(self.builddir):
            emerge_in_chroot = uchroot()["/usr/bin/emerge"]
            prog = AutoPortage.DOMAIN + "/" + AutoPortage.NAME
            run(emerge_in_chroot[prog])

    def run_tests(self, experiment):
        pass

def PortageFactory(name, NAME, DOMAIN, BaseClass=AutoPortage):
    newclass = type(name, (BaseClass,), {
        #"__init__" : __init__ ,
        "NAME" : NAME,
        "DOMAIN" : DOMAIN
    })
    return newclass
