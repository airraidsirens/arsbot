# flake8: noqa: E402
import argparse
import logging

from dotenv import load_dotenv

load_dotenv()

from .core.config import validate_config
from .core.db import bot_session
from .core.logging import setup_loggers
from .discord.run import runbot
from .models.base import BotBase

log = logging.getLogger("arsbot")


parser = argparse.ArgumentParser(
    prog="arsbot",
    description="Runs ARS bot.",
)
parser.add_argument(
    "--action",
    choices=["runbot", "initdb"],
    default="runbot",
    help="Which action to run",
)


def initdb():
    with bot_session() as session:
        BotBase.metadata.create_all(session.bind)


def main():
    args = parser.parse_args()

    setup_loggers()
    validate_config()

    if args.action == "runbot":
        runbot()
    elif args.action == "initdb":
        initdb()

    log.debug("main done!!")
