"""
Projects module.

By default, only projects that are listed in the configuration are
loaded automatically. See configuration variables:
 *_PLUGINS_AUTOLOAD
 *_PLUGINS_PROJECTS

"""
import logging
import importlib

from benchbuild.settings import CFG

LOG = logging.getLogger(__name__)


def discover():
    if CFG["plugins"]["autoload"].value():
        project_plugins = CFG["plugins"]["projects"].value()
        for pp in project_plugins:
            LOG.debug("Found project: %s", pp)
            try:
                importlib.import_module(pp)
            except ImportError as ie:
                LOG.error("Could not find '%s'", pp)
                LOG.error("ImportError: %s", ie.msg)
