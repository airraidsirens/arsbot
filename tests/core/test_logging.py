import logging

from arsbot.core.logging import setup_loggers


TEST_LOGGING_CONFIG = """
version: 1
disable_existing_loggers: true
incremental: false

formatters:
  default:
    format: '%(asctime)-8s %(name)-8s %(funcName)-16s:%(lineno)-4d %(levelname)-7s %(message)s'

handlers:
  console:
    class : logging.StreamHandler
    formatter: default
    stream  : ext://sys.stdout

loggers:
  arsbot:
    handlers: [console]
    propagate: false
    level: DEBUG
  discord.client:
    handlers: [console]
    propagate: false
    level: ERROR

root:
  handlers: [console]
  level: DEBUG
"""


def test_setup_loggers(bot_data_dir, bot_env_config):
    logging_file = bot_data_dir / "logger.yaml"
    logging_file.write_text(TEST_LOGGING_CONFIG)

    bot_env_config("LOGGING_FILE", str(logging_file))

    setup_loggers()

    arsbot_log = logging.getLogger("arsbot")
    assert arsbot_log.level == logging.DEBUG

    discord_client_log = logging.getLogger("discord.client")
    assert discord_client_log.level == logging.ERROR

    discord_gateway_log = logging.getLogger("discord.gateway")
    assert discord_gateway_log.level == logging.NOTSET

    discord_http_log = logging.getLogger("discord.http")
    assert discord_http_log.level == logging.NOTSET


def test_setup_loggers_no_file(bot_data_dir, bot_env_config):
    bot_env_config("LOGGING_FILE", str(bot_data_dir / "doesnt_exist"))

    root = logging.getLogger()
    for logging_handler in root.handlers:
        root.removeHandler(logging_handler)

    for logging_filter in root.filters:
        root.removeFilter(logging_filter)

    setup_loggers()

    discord_client_log = logging.getLogger("discord.client")
    assert discord_client_log.level == logging.WARNING

    discord_gateway_log = logging.getLogger("discord.gateway")
    assert discord_gateway_log.level == logging.WARNING

    discord_http_log = logging.getLogger("discord.http")
    assert discord_http_log.level == logging.WARNING
