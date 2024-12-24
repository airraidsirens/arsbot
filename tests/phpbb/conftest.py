import pytest

from arsbot.phpbb import http as phpbb_http


@pytest.fixture
def patch_phpbb(bot_data_dir):
    old_session_file = str(phpbb_http.PHPBB_SESSION_FILE)

    phpbb_session_file = bot_data_dir / "phpbb_session.data"
    phpbb_http.PHPBB_SESSION_FILE = str(phpbb_session_file)

    yield

    phpbb_http.PHPBB_SESSION_FILE = old_session_file
