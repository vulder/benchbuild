# BenchBuild: Empirical-Research Toolkit
![image](https://travis-ci.org/PolyJIT/benchbuild.svg?branch=master)
[![Codacy Badge](https://api.codacy.com/project/badge/Grade/217af919753b4d16b3760282c1274751)](https://www.codacy.com/app/polyjit/benchbuild_2?utm_source=github.com&amp;utm_medium=referral&amp;utm_content=PolyJIT/benchbuild&amp;utm_campaign=Badge_Grade)
[![Documentation Status](https://readthedocs.org/projects/pprof-study/badge/?version=master)](http://pprof-study.readthedocs.io/en/master/?badge=master)
[![codecov](https://codecov.io/gh/PolyJIT/benchbuild/branch/master/graph/badge.svg)](https://codecov.io/gh/PolyJIT/benchbuild)
[![BCH compliance](https://bettercodehub.com/edge/badge/PolyJIT/benchbuild?branch=master)](https://bettercodehub.com/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

BenchBuild provides a lightweight toolkit to conduct empirical compile-time and run-time experiments.
Striving to automate all tedious and error-prone tasks, it downloads, configure and builds all supported projects fully automatic and provides tools to wrap the compiler and any resulting binary with a customized measurement.

All results can be stored as the user desires.
BenchBuild tracks the execution status of all its managed projects inside an own database.

## Features

- Wrap compilation commands with arbitrary measurement functions written in python.
- Wrap binary commands with arbitrary measurement functions written in python.
- Parallel benchmarking using the SLURM cluster manager.
- Compile-time support for the gentoo portage tree using the `uchroot` command.

## Database

BenchBuild stores results/maintenance data about your experiments inside a database.
While a sqlite3 in-memory database is used by default, you might want to provide a more permanent solution to keep your experiment data persistent.

### PostgreSQL

The preferred way is using a more sophisticated DBMS such as PostgreSQL.
If you are using features like SLURM, make sure that your DBMS is reachable from all nodes that might run benchbuild.

Setup your postgres cluster with a user and a database for benchbuild to use.

```sql
CREATE USER benchbuild;
CREATE DATABASE benchbuild;
```

In the configuration you supply the complete connect-string in sqlalchemy's format, e.g.: `postgresql+psycopg2://benchbuild:benchbuild@localhost:5432/benchbuild`

```yaml
# .benchbuild.yml
db:
  connect_string:
    default: sqlite://
    value:  postgresql+psycopg2://benchbuild:benchbuild@localhost:5432/benchbuild
```

### SQLite

As mentioned, by default we use an in-memory sqlite database. You can persist this one for your local usage, by supplying a filename in the database configuration.

```yaml
# .benchbuild.yml
db:
  connect_string:
    default: sqlite://
    value:  sqlite:////absolute/path/to/sqlite.db
```

## Advanced Features

Advanced features require additional packages on your system.

### UnionFS

We can maintain UnionFS mounts for uchroot-based projects, such as all Gentoo derived projects.
This avoids continuous unpacking of the container-filesystem and keeps one unpacked version as
a read-only layer at the bottom of the filesystem-stack.

You need to configure subuid/subgid ranges in `/etc/subuid` `/etc/subgid` for the user that
runs `benchbuild` in this mode. In addition, you need a working fuse installation. This involves
an installation of `libfuse` with its headers.
The `benchbuild bootstrap` command may help you with the installation and setup.

## Installation

After you have installed all necessary libraries, you can just clone this repo and install via pip.

```bash
$ pip install benchbuild
```

This will pull in all necessary python libraries into your local python installation.
The installed program to control the study is called `benchbuild`.

## Configuration

`benchbuild` can be configured in various ways: (1) command-line arguments, (2) configuration file in .json format, (3) environment variables. 
You can dump the current active configuration with the command:

```bash
benchbuild run -d
```

# Documentation

For detailed API information please refer to the full
[documentation](https://polyjit.github.io/benchbuild):

You can dump this information in YAML format using the command:
```bash
benchbuild run -s
```

It dumps \_all\_ configuration to YAML, even those that are usually derived automatically (like UUIDs).
In the future, this will be avoided automatically.
For now, you should remove all ID related variables from the resulting YAML file.
The configuration file is searched from the current directory upwards automatically.
Some key configuration variables:

```
  BB_BUILD_DIR     The directory we place our temporary artifacts in.
  BB_TMP_DIR       The directory we place our downloads in.
  BB_CLEAN         Should the build directory be cleaned after the run?
  BB_CONFIG_FILE   Where is the config file? If you prefere an absolute location over automatic discovery.
  BB_DB_HOST       Hostname of the database
  BB_DB_NAME       Name of the database
  BB_DB_USER       Username of the database
  BB_DB_PASS       Password of the database
  BB_DB_ROLLBACK   For testing Rollback all db actions after a run.
  BB_JOBS          Number of threads to use for compiling / run-time testing.
```

You can set these in the .json config file or directly via environment
variables. However, make sure that the values you pass in from the
environment are valid JSON, or the configuration structure may ignore
your input (or break).

### SLURM Configuration

If you want to run experiments in parallel on a cluster managed by
SLURM, you can use BenchBuild to generate a bash script that is
compatible with SLURM's sbatch command. The following settings control
SLURM's configuration:

```
  BB_SLURM_ACCOUNT         The resource account log in to.
  BB_SLURM_CPUS_PER_TASK   How many cores/threads should we request per node?
  BB_SLURM_EXCLUSIVE       Should we request the node exclusively or share it with other tasks?
  BB_SLURM_MAX_RUNNING     We generate array-Jobs. This parameter controls the number of array elements that are allowed to run in parallel.
  BB_SLURM_MULTITHREAD     Should Hyper-Threading be enabled or not?
  BB_SLURM_NICE            Adjust our priority on the cluster manually.
  BB_SLURM_NICE_CLEAN      Adjust the priority of the clean jobs.
  BB_SLURM_NODE_DIR        Where can we place our artifacts on the node?
  BB_SLURM_PARTITION       Which partition should we run in?
  BB_SLURM_SCRIPT          Base name of our resulting batch script.
  BB_SLURM_TIMELIMIT       Enforce a timelimit on our batch jobs.
```

### Gentoo Configuration

BenchBuild supports compile-time experiments on the complete portage
tree of Gentoo Linux. You need to configure a few settings to make it
work:

```
  BB_GENTOO_AUTOTEST_LOC           A txt file that lists all gentoo package atoms that should be considered.
  BB_GENTOO_AUTOTEST_FTP_PROXY     Proxy server for gentoo downloads.
  BB_GENTOO_AUTOTEST_HTTP_PROXY    Proxy server for gentoo downloads.
  BB_GENTOO_AUTOTEST_RSYNC_PROXY   Proxy server for gentoo downloads.
```

#### Convert an automatic Gentoo project to a static one

Gentoo projects are generated dynamically based on the `AutoPortage`
class found in `pprof.gentoo.portage_gen`. If you want to define
run-time tests for a dynamically generated project, you need to convert
it to a static one, i.e., define a subclass of `AutoPortage` and add it
to the configuration.

```python
from pprof.projects.gentoo.portage_gen import AutoPortage

class BZip(AutoPortage):
  NAME = "app-arch"
  DOMAIN = "bzip2"

  def run_tests(self, run):
    """Add your custom test routines here."""
```

Now we just need to add this to the plugin registry via `benchbuild`'s
configuration file @ `CFG["plugins"]["projects"]`.
