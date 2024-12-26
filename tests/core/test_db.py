import sqlalchemy as sa


def test_validate_config(sql_session):
    result = sql_session.execute(sa.text("SELECT 1 + 1"))
    assert result.one() == (2,)
