#!/usr/bin/env python3
#
from benchbuild.project import Project
from benchbuild.experiment import Experiment
from plumbum import cli, local
from os import path, getenv
from benchbuild.experiment import Experiment as E
from {base_module} import {base_class} as PBC

import logging
import os
import sys
import dill

log = logging.getLogger("run")
log.setLevel(logging.ERROR)
log.addHandler(logging.StreamHandler(stream=sys.stderr))

EXPERIMENT_NAME = getenv("BB_EXPERIMENT", "unknown")
DOMAIN_NAME = getenv("BB_DOMAIN", PBC.DOMAIN)
GROUP_NAME = getenv("BB_GROUP", PBC.GROUP)

if not len(sys.argv) >= 2:
    log.error("Not enough arguments provided!\\n")
    log.error("Got: " + sys.argv + "\\n")
    sys.exit(1)

f = None
RUN_F = sys.argv[1]
ARGS = sys.argv[2:]
PROJECT_NAME = path.basename(RUN_F)

if path.exists("{blobf}"):
    with local.env(BB_DB_HOST="{db_host}",
                   BB_DB_PORT="{db_port}",
                   BB_DB_NAME="{db_name}",
                   BB_DB_USER="{db_user}",
                   BB_DB_PASS="{db_pass}",
                   BB_PROJECT=PROJECT_NAME,
                   PATH="{path}",
                   LD_LIBRARY_PATH="{ld_lib_path}",
                   BB_CMD=RUN_F):
        with open("{blobf}", "rb") as p:
            f = dill.load(p)
        if f is not None:
            project_cls = type("Dyn_" + PROJECT_NAME, (PBC,), {{
                "NAME": PROJECT_NAME,
                "DOMAIN": DOMAIN_NAME,
                "GROUP": GROUP_NAME,
                "__module__": "__main__"
            }})

            experiment_cls = type(EXPERIMENT_NAME, (E,), {{
                "NAME": EXPERIMENT_NAME
            }})

            e = experiment_cls([PROJECT_NAME], [GROUP_NAME])
            p = project_cls(e)

            if not sys.stdin.isatty():
                f(RUN_F, ARGS, has_stdin=True, project_name=PROJECT_NAME)
            else:
                f(RUN_F, ARGS, project_name=PROJECT_NAME)
        else:
            sys.exit(1)