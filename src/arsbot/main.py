# flake8: noqa: E402
import argparse
import logging

from dotenv import load_dotenv

load_dotenv()

from .core.config import validate_config
from .core.logging import setup_loggers
from .discord.run import runbot

log = logging.getLogger("arsbot")


parser = argparse.ArgumentParser(
    prog="arsbot",
    description="Runs ARS bot. No arguments currently supported.",
)


def main():
    _args = parser.parse_args()

    setup_loggers()
    validate_config()

    runbot()

    log.debug("main done!!")
