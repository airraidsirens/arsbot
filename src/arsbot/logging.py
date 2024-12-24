import logging
import logging.config
import os
import pathlib

import yaml


def setup_loggers():
    logging_file = os.environ.get("LOGGING_FILE", "etc/logger.yml")

    logger_yml = pathlib.Path(logging_file)
    if logger_yml.is_file():
        with open(logger_yml, "r") as fp:
            log_config = yaml.safe_load(fp)
        logging.config.dictConfig(log_config)
        return

    logger = logging.getLogger("discord.client")
    logger.setLevel(logging.WARNING)

    logger = logging.getLogger("discord.gateway")
    logger.setLevel(logging.WARNING)

    logger = logging.getLogger("discord.http")
    logger.setLevel(logging.WARNING)
