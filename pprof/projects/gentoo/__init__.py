"""
Import all gentoo based modules.

All manually entered modules can be placed in the following import section.
Portage_Gen based projects will be generated automatically as soon as we
can find an index generated by portage info.
"""
from . import gentoo
from . import bzip2
from . import gzip
from . import sevenz
from . import xz
from . import postgresql
from . import lammps
from . import x264
from . import crafty
from . import info

from pprof.settings import CFG
# Dynamically create projects from the gentoo ebuild index.
def __initialize_dynamic_projects__(autotest_path):
    import os
    import logging
    from pprof.projects.gentoo.portage_gen import PortageFactory

    logger = logging.getLogger(__name__)
    logger.debug("Loading AutoPortage projects from %s", autotest_path)
    if os.path.exists(autotest_path):
        with open(autotest_path, 'r') as ebuilds:
            for line in ebuilds:
                ebuild_data = line.strip('\n')
                ebuild_data = ebuild_data.split('/')
                domain = ebuild_data[0]
                name = ebuild_data[1]
                PortageFactory("Auto{}{}".format(domain, name),
                               domain + "_" + name, domain)


__initialize_dynamic_projects__(CFG['gentoo']['autotest_loc'].value())
