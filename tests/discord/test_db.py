import sqlalchemy as sa

from arsbot.discord.db import BotBase, bot_session


def test_validate_config(bot_data_dir, bot_env_config):
    with bot_session() as session:
        BotBase.metadata.create_all(session.bind)

        result = session.execute(sa.text("SELECT 1 + 1"))
        assert result.one() == (2,)
