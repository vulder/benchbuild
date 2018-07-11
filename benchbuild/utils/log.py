import logging

from benchbuild import settings


def configure_migrate_log():
    migrate_log = logging.getLogger("migrate.versioning")
    migrate_log.setLevel(logging.ERROR)
    migrate_log.propagate = True


def configure_plumbum_log():
    plumbum_format = logging.Formatter('$> %(message)s')
    plumbum_hdl = logging.StreamHandler()
    plumbum_hdl.setFormatter(plumbum_format)
    plumbum_local = logging.getLogger("plumbum.local")
    if settings.CFG["debug"].value():
        plumbum_local.setLevel(logging.DEBUG)
    plumbum_local.addHandler(plumbum_hdl)
    plumbum_local.propagate = False


def configure():
    """Load logging configuration from our own defaults."""
    log_levels = {
        5: logging.NOTSET,
        4: logging.DEBUG,
        3: logging.INFO,
        2: logging.WARNING,
        1: logging.ERROR,
        0: logging.CRITICAL
    }

    logging.captureWarnings(True)
    root_logger = logging.getLogger()
    if settings.CFG["debug"].value():
        details_format = logging.Formatter(
            '%(name)s (%(filename)s:%(lineno)s) [%(levelname)s] %(message)s')
        details_hdl = logging.StreamHandler()
        details_hdl.setFormatter(details_format)
        root_logger.addHandler(details_hdl)
    else:
        brief_format = logging.Formatter('%(message)s')
        console_hdl = logging.StreamHandler()
        console_hdl.setFormatter(brief_format)
        root_logger.addHandler(console_hdl)
    root_logger.setLevel(log_levels[settings.CFG["verbosity"].value()])

    configure_plumbum_log()
    configure_migrate_log()


def set_defaults():
    """Configure the loggers default settings."""
    pass
