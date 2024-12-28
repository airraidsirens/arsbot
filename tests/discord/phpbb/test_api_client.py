from functools import partial
from urllib.parse import parse_qs

import pytest
import responses

from arsbot.discord.phpbb import api_client

from tests.conftest import read_test_file


def _get_ucp_login_callback(request):
    content = read_test_file("ucp_login.html")
    headers = {
        "X-Server": "pytest",
    }
    return (200, headers, content)


def _get_index_callback(request):
    # TODO: verify phpbb3_cookie_secret
    content = read_test_file("ucp_login_success.html")
    headers = [
        ("X-Server", "pytest"),
        ("Set-Cookie", "phpbb3_cookie_sid=sid1"),
        ("Set-Cookie", "phpbb3_cookie_u=1"),
        ("Set-Cookie", "phpbb3_cookie_secret=abcdefg"),
    ]

    return (200, headers, content)


def _post_login_callback(username, password, request):
    body = parse_qs(request.body)

    headers = [
        ("X-Server", "pytest"),
    ]

    if body.get("username", []) == [username] and body.get("password", []) == [
        password
    ]:
        content = read_test_file("ucp_login_success.html")
        headers.append(("Set-Cookie", "phpbb3_cookie_sid=sid1"))
        headers.append(("Set-Cookie", "phpbb3_cookie_u=1"))
        headers.append(("Set-Cookie", "phpbb3_cookie_secret=abcdefg"))
    elif body.get("username", []) == [username] and body.get("password", []) == [
        "invalid"
    ]:
        content = read_test_file("ucp_login_fail.html")
    else:
        content = read_test_file("ucp_login_error.html")

    return (200, headers, content)


@pytest.fixture(autouse=True)
def patch_api_client(bot_data_dir):
    old_session_file = str(api_client.PHPBB_SESSION_FILE)

    phpbb_session_file = bot_data_dir / "phpbb_session.data"
    api_client.PHPBB_SESSION_FILE = str(phpbb_session_file)

    yield

    api_client.PHPBB_SESSION_FILE = old_session_file


@responses.activate
def test_login_to_phpbb_fails_wrong_password(bot_env_config):
    bot_env_config("PHPBB_PASSWORD", "invalid")

    params = {
        "mode": "login",
        "redirect": "index.php",
    }
    responses.add_callback(
        responses.GET,
        url="https://airraidsirens.net/forums/ucp.php",
        match=[responses.matchers.query_param_matcher(params)],
        callback=_get_ucp_login_callback,
    )

    params = {
        "mode": "login",
    }
    responses.add_callback(
        responses.POST,
        url="https://airraidsirens.net/forums/ucp.php",
        match=[responses.matchers.query_param_matcher(params)],
        callback=partial(_post_login_callback, "testuser", "testpass"),
    )

    with pytest.raises(api_client.PhpBBAuthError) as error:
        api_client._login_to_phpbb()

    assert error.value.args == ("Invalid username/password",)


@responses.activate
def test_login_to_phpbb_fails_missing_error(bot_env_config):
    params = {
        "mode": "login",
        "redirect": "index.php",
    }
    responses.add_callback(
        responses.GET,
        url="https://airraidsirens.net/forums/ucp.php",
        match=[responses.matchers.query_param_matcher(params)],
        callback=_get_ucp_login_callback,
    )

    params = {
        "mode": "login",
    }
    responses.add_callback(
        responses.POST,
        url="https://airraidsirens.net/forums/ucp.php",
        match=[responses.matchers.query_param_matcher(params)],
        callback=partial(_post_login_callback, "testuser_wrong", "testpass_wrong"),
    )

    with pytest.raises(api_client.PhpBBAuthError) as error:
        api_client._login_to_phpbb()

    assert error.value.args == ("Unable to get error message: list index out of range",)


@responses.activate
def test_login_to_phpbb_succeeds(bot_env_config):
    params = {
        "mode": "login",
        "redirect": "index.php",
    }
    responses.add_callback(
        responses.GET,
        url="https://airraidsirens.net/forums/ucp.php",
        match=[responses.matchers.query_param_matcher(params)],
        callback=_get_ucp_login_callback,
    )

    params = {
        "mode": "login",
    }
    responses.add_callback(
        responses.POST,
        url="https://airraidsirens.net/forums/ucp.php",
        match=[responses.matchers.query_param_matcher(params)],
        callback=partial(_post_login_callback, "testuser", "testpass"),
    )

    session, logged_in = api_client._login_to_phpbb()
    assert logged_in is True

    assert session.sid == "sid1"
    assert session.user_id == 1

    responses.add_callback(
        responses.GET,
        url="https://airraidsirens.net/forums/",
        callback=_get_index_callback,
    )

    session, logged_in = api_client._login_to_phpbb()
    assert logged_in is True

    assert session.sid == "sid1"
    assert session.user_id == 1


def test_ban_action_enum():
    assert api_client.BanAction.BANUSER.value == "banuser"
    assert api_client.BanAction.BANEMAIL.value == "banemail"
    assert api_client.BanAction.BANIP.value == "banip"
