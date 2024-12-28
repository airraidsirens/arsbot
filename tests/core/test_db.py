import sqlalchemy as sa

from arsbot.core.db import bot_session


def test_validate_config():
    with bot_session() as session:
        result = session.execute(sa.text("SELECT 1 + 1"))
    assert result.one() == (2,)
