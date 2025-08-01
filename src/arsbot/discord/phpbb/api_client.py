import enum
import functools
from dataclasses import dataclass
import logging
import os
import re
import sys
import time
import typing as t
from urllib.parse import parse_qs, urlparse

import arrow
from bs4 import BeautifulSoup
from bs4.element import Tag
import msgpack
import requests
from forcediphttpsadapter.adapters import ForcedIPHTTPSAdapter

from arsbot.version import VERSION
from arsbot.utils.ipinfo import get_ip_address_info


log = logging.getLogger("arsbot")


class PhpBBAuthError(Exception):
    pass


class PhpBBADMError(Exception):
    pass


PHPBB_SESSION_FILE = "phpbb_session.data"

_vi = sys.version_info
_PY_VERSION = f"{_vi.major}.{_vi.minor}.{_vi.micro}"
DEFAULT_HEADERS = {"User-Agent": f"arsbot v{VERSION}; Python {_PY_VERSION}"}


def on_request_end(session, response, *args, **kwargs):
    # log.debug('on_request_end, saving session...')
    session.save_session()


class PhpBBSession(requests.Session):
    def __init__(self, *args, **kwargs):
        self._base_url = kwargs.pop("base_url", None)

        super().__init__(*args, **kwargs)

        on_request_end_with_session = functools.partial(on_request_end, self)

        self.hooks["response"].append(on_request_end_with_session)

        self.headers.update(DEFAULT_HEADERS)

    def request(self, method, url, **kwargs) -> requests.Response:
        if url.startswith("https://") or url.startswith("http://"):
            print(f"GOT HTTP REQUEST in PhpBBSession.request: {method} {url}")
            return super().request(method, url, **kwargs)

        parsed_url = urlparse(self._base_url)
        hostname = parsed_url.netloc

        new_url = f"{parsed_url.scheme}://{hostname}{parsed_url.path}{url}"
        url = new_url

        return super().request(method, url, **kwargs)

    def save_session(self):
        # log.debug('Saving session!')

        cookies = msgpack.dumps(self.cookies.items())
        with open(PHPBB_SESSION_FILE, "wb+") as fp:
            fp.write(cookies)

    def load_session(self) -> bool:
        try:
            with open(PHPBB_SESSION_FILE, "rb") as fp:
                session_data = msgpack.load(fp)
        except FileNotFoundError:
            log.debug("Unable to load session file: FileNotFoundError")
            return False
        except ValueError as exc:
            log.debug(f"Unable to load session file: {exc}")
            os.remove(PHPBB_SESSION_FILE)
            return False

        self.cookies.clear()

        for key, value in session_data:
            self.cookies.set(key, value)

        # log.debug(f'Restored cookies from session file, sid: {self.sid}')

        return True

    @property
    def sid(self) -> t.Optional[str]:
        for key, value in self.cookies.items():
            if key.startswith("phpbb3_") and key.endswith("_sid"):
                return value

        return None

    @property
    def user_id(self) -> t.Optional[int]:
        for key, value in self.cookies.items():
            if key.startswith("phpbb3_") and key.endswith("_u"):
                return int(value)

        return None


class BanAction(enum.Enum):
    BANUSER = "banuser"
    BANEMAIL = "banemail"
    BANIP = "banip"


@dataclass
class PhpBBPostRequest:
    topic_name: str
    topic_url: str
    forum_name: str
    forum_url: str
    author_name: str
    author_url: str
    author_id: int
    mode: str
    post_time: arrow.Arrow
    post_ip_address: str
    post_ip_hostname: t.Optional[str]
    post_ip_location: str
    post_ip_organization: str
    post_text: str
    post_id: int
    user_join_date: arrow.Arrow
    user_warning_count: int
    user_post_count: int
    user_group_list: str

    @property
    def is_for_new_topic(self) -> bool:
        return self.mode == "unapproved_topics"


def _load_session(session: PhpBBSession) -> bool:
    try:
        with open(PHPBB_SESSION_FILE, "rb") as fp:
            session_data = msgpack.load(fp)
    except FileNotFoundError:
        return False
    except ValueError:
        os.remove(PHPBB_SESSION_FILE)
        return False

    session.cookies.clear()

    for key, value in session_data:
        session.cookies.set(key, value)

    return True


def _validate_session(session: PhpBBSession) -> bool:
    response = session.get("/")
    index_page = BeautifulSoup(response.text, features="html.parser")

    footer = index_page.find(id="wrapfooter")
    if footer and "[ Administration Control Panel ]" in footer.text:
        return True

    return False


def _extract_form_fields(form: Tag):
    form_fields = {}

    for field in form.find_all("input"):
        field_attrs = field.attrs
        if "value" not in field_attrs:
            continue
        form_fields[field_attrs["name"]] = field_attrs["value"]

    return form_fields


def _login_to_phpbb(force_fresh: bool = False):
    base_url = os.environ["PHPBB_BASE_URL"]
    session = PhpBBSession(base_url=base_url)

    if base_ip := os.environ.get("PHPBB_IP"):
        session.mount(base_url, ForcedIPHTTPSAdapter(dest_ip=base_ip))

    if force_fresh:
        try:
            os.remove(PHPBB_SESSION_FILE)
        except FileNotFoundError:
            pass

    if session.load_session() and _validate_session(session):
        # log.debug(f'Loaded session from backup!!')
        return session, True

    log.debug("Unable to load session from backup, creating a fresh session")

    session.cookies.clear()

    params = {
        "mode": "login",
        "redirect": "index.php",
    }
    url = "/ucp.php"
    response = session.get(url, params=params)
    # print(response.text)
    assert response.status_code == 200, response.status_code

    # Reload again cuz phpbb is weird..
    response = session.get(url, params=params)
    assert response.status_code == 200

    login_page = BeautifulSoup(response.text, features="html.parser")

    login_form_fields = None
    for form in login_page.body.find_all("form"):
        if not form.attrs.get("action").startswith("./ucp.php?mode=login"):
            continue

        login_form_fields = _extract_form_fields(form)
        break

    if login_form_fields is None:
        raise PhpBBAuthError("Unable to find login form!")

    # From phpBB/includes/functions.php:2070
    #
    # // If creation_time and the time() now is zero we can assume
    #    it was not a human doing this (the check for if ($diff)...
    #
    # We basically have to sleep() for a bit during auth checks, otherwise
    # the creation_time checker will kick us out.
    time.sleep(3)

    phpbb_username = os.environ["PHPBB_USERNAME"]
    phpbb_password = os.environ["PHPBB_PASSWORD"]

    params = {
        "mode": "login",
    }
    login_form = {
        "username": phpbb_username,
        "password": phpbb_password,
        "autologin": "on",
        "redirect": "./ucp.php?mode=login&redirect=index.php",
        "creation_time": login_form_fields["creation_time"],
        "form_token": login_form_fields["form_token"],
        "sid": login_form_fields["sid"],
        "login": "Login",
    }
    url = "/ucp.php"
    response = session.post(url, params=params, data=login_form)

    logged_in_page = BeautifulSoup(response.text, features="html.parser")
    footer = logged_in_page.find(id="wrapfooter")
    if not footer or "[ Administration Control Panel ]" not in footer.text:
        try:
            error_message = logged_in_page.select("form")[1].find(class_="error").text
        except Exception as exc:
            print(response.text)
            raise PhpBBAuthError(f"Unable to get error message: {exc}")
        else:
            raise PhpBBAuthError(error_message)

    return session, True


def _extract_moderatable_post(row: Tag):
    topic_approval_request = {
        "topic_name": "",
        "topic_url": "",
        "forum_name": "",
        "forum_url": "",
        "author_name": "",
        "author_url": "",
        "author_id": None,
        "post_time": "",
        # These are pulled in from a different function
        "post_ip_address": "",
        "post_ip_hostname": "",
        "post_ip_location": "",
        "post_ip_organization": "",
        "post_text": "",
    }

    topic_info_cell = row.select("td")[0]

    topic_title = topic_info_cell.find(class_="topictitle")
    topic_approval_request["topic_name"] = topic_title.text
    topic_approval_request["topic_url"] = topic_title.attrs["href"].removeprefix(".")

    forum_info_cell = topic_info_cell.select_one("span")
    topic_approval_request["forum_name"] = forum_info_cell.text.removeprefix("Forum: ")
    topic_approval_request["forum_url"] = (
        forum_info_cell.select_one("a").attrs["href"].removeprefix(".")
    )

    author_info_cell = row.select("td")[1]
    author_info_href = author_info_cell.select_one("a")
    topic_approval_request["author_name"] = author_info_href.text
    topic_approval_request["author_url"] = author_info_href.attrs["href"].removeprefix(
        "."
    )

    # Get the author ID
    query_args = parse_qs(urlparse(topic_approval_request["author_url"]).query)
    author_id = int(query_args["u"][0])

    topic_approval_request["author_id"] = author_id

    post_details_cell = row.select("td")[2]

    # NOTE: The bot's user preferences are set to UTC and the date formatting
    #       will only work with the format below!
    post_time = arrow.get(post_details_cell.text, "MMMM Do, YYYY, h:mm a")
    topic_approval_request["post_time"] = post_time

    return topic_approval_request


def _extract_user_details(session: PhpBBSession, topic_approval_request: dict):
    user_details = {
        "user_join_date": "",
        "user_warning_count": "",
        "user_post_count": "",
        "user_group_list": "",
    }

    author_response = session.get(topic_approval_request["author_url"])
    assert author_response.ok

    author_page = BeautifulSoup(author_response.text, features="html.parser")

    user_stats = author_page.find_all("form")[0].find_all(class_="row1")[1]
    join_date_text = user_stats.select("tr")[0].select("td")[1].text
    join_date = arrow.get(join_date_text, "MMMM Do, YYYY, h:mm a")
    user_details["user_join_date"] = join_date

    warning_count_text = user_stats.select("tr")[2].select("td")[1].text
    warning_count = warning_count_text.removesuffix(" [ View user notes  | Warn user ]")
    user_details["user_warning_count"] = int(warning_count)

    post_count = user_stats.select("tr")[3].select("td")[1].find(class_="gen").text
    user_details["user_post_count"] = int(post_count)

    groups_index = None
    tr_array = author_page.find_all("form")[0].find_all("tr")
    for tr_index, tr_field in enumerate(tr_array):
        row_cell = tr_field.select_one("td")
        if row_cell is not None and row_cell.text == "Groups: ":
            groups_index = tr_index
            break

    assert groups_index is not None

    groups_cell = tr_array[groups_index]
    group_list = ", ".join([c.text for c in groups_cell.select("select")[0].children])
    user_details["user_group_list"] = group_list

    return user_details


def _replace_unicode(text: str) -> str:
    return (
        re.sub("(\u2018|\u2019)", "'", text).encode("ascii", "replace").decode("utf-8")
    )


def _extract_post_details(session: PhpBBSession, topic_approval_request: dict):
    post_details = {
        "post_id": None,
        "post_text": "",
        "post_ip_address": "",
        "post_ip_hostname": "",
        "post_ip_location": "",
        "post_ip_organization": "",
    }

    query_args = parse_qs(urlparse(topic_approval_request["topic_url"]).query)
    post_id = int(query_args["p"][0])
    post_details["post_id"] = post_id

    # Pull more details on the post itself (IP & content)
    moderate_post_view_url = f"/mcp.php?i=queue&mode=approve_details&p={post_id}"
    moderate_post_response = session.get(moderate_post_view_url)
    assert moderate_post_response.ok
    moderate_post_page = BeautifulSoup(
        moderate_post_response.text, features="html.parser"
    )

    if not (post_moderation_form := moderate_post_page.select_one("form")):
        print(f"Cant find post form for {post_id}")
        return {}

    post_moderation_fields = post_moderation_form.select("tr")
    post_ip_address = (
        post_moderation_fields[3]
        .select_one("span")
        .text.strip()
        .removesuffix(" (Look up IP)")
    )

    # 1 for blockquote, 0 for non blockquote
    inner_post_blocks = [
        c for c in post_moderation_fields[6].find(class_="postbody").children
    ]
    post_block_index = 0
    if str(inner_post_blocks[0]).startswith("<blockquote"):
        post_block_index = 1

    if post_block_index < len(inner_post_blocks):
        inner_post_block = str(inner_post_blocks[post_block_index]).strip()
    else:
        inner_post_block = ""
    post_details["post_text"] = _replace_unicode(str(inner_post_block))
    post_details["post_ip_address"] = post_ip_address

    ipinfo = get_ip_address_info(post_ip_address)
    if not ipinfo:
        return post_details

    post_details["post_ip_hostname"] = ipinfo.get("hostname")
    post_details["post_ip_location"] = (
        f"{ipinfo['city']} {ipinfo['region']} {ipinfo['country']}"
    )
    post_details["post_ip_organization"] = ipinfo["org"]

    return post_details


def _extract_last_approved_post_date(page: BeautifulSoup) -> t.Optional[arrow.Arrow]:
    content_styles = {"class": "tablebg", "width": "100%", "cellspacing": "1"}

    for table in reversed(page.find_all("table", content_styles)):
        # Not a post in a topic
        if not table.find("div", {"class": "postbody"}):
            continue

        # Post hasn't been approved yet
        if table.find("span", {"class": "postapprove"}):
            continue

        # Get the posted date
        post_info = table.find("td", {"class": "gensmall"})
        post_text = post_info.text

        posted_needle = "Posted: "
        posted_index = post_text.rindex(posted_needle)
        post_date_text = post_text[posted_index + len(posted_needle) :].strip()
        last_post_date = arrow.get(post_date_text, "MMMM Do, YYYY, h:mm a")

        return last_post_date

    return None


def _extract_topic_details(session: PhpBBSession, topic_approval_request: dict):
    topic_details = {
        "last_approved_post_date": "",
    }

    topic_url = topic_approval_request["topic_url"]
    topic_response = session.get(topic_url)
    assert topic_response.ok

    topic_page = BeautifulSoup(topic_response.text, features="html.parser")

    topic_href = topic_page.find(id="pageheader").select_one("a").attrs["href"]
    topic_id = int(parse_qs(urlparse(topic_href).query)["t"][0])

    topic_url = "/viewtopic.php"
    topic_params = {
        "t": topic_id,
    }

    topic_response = session.get(topic_url, params=topic_params)
    assert topic_response.ok

    topic_page = BeautifulSoup(topic_response.text, features="html.parser")
    page_x_of_y_text = topic_page.find(
        class_="nav", valign="middle", nowrap="nowrap"
    ).text[1:]

    PAGE_PAT = re.compile(r"Page (\d+) of (\d+)")
    this_page, last_page = PAGE_PAT.search(page_x_of_y_text).groups()

    for cur_page_number_neg in range(-int(last_page), 0):
        start_at = (abs(cur_page_number_neg) * 10) - 10

        topic_url = "/viewtopic.php"
        topic_params = {
            "t": topic_id,
        }
        if start_at:
            topic_params["start"] = start_at

        topic_response = session.get(topic_url, params=topic_params)
        assert topic_response.ok

        topic_page = BeautifulSoup(topic_response.text, features="html.parser")

        last_post_date = _extract_last_approved_post_date(topic_page)
        if not last_post_date:
            continue

        topic_details["last_approved_post_date"] = last_post_date
        return topic_details

    log.error(f"Unable to find last post date for topic {topic_id}: {topic_href}")
    return {}


def _load_posts_topics_awaiting_approval(
    session: PhpBBSession,
    mode: str,
    retried: bool = False,
) -> t.List[PhpBBPostRequest]:
    url = f"/mcp.php?i=mcp_queue&mode={mode}"
    response = session.get(url)
    assert response.ok, response.status_code

    posts_awaiting_approval = []

    approvals_page = BeautifulSoup(response.text, features="html.parser")

    mcp_cell = approvals_page.find(id="mcp")
    if not mcp_cell:
        header_cell = approvals_page.find("h2")
        if header_cell and header_cell.text == "To moderate this forum you must login.":
            session, logged_in = _login_to_phpbb(force_fresh=True)
            return _load_posts_topics_awaiting_approval(
                session=session, mode=mode, retried=True
            )
        raise PhpBBAuthError("Unable to access moderator control panel!")

    trs = mcp_cell.select("tr")
    for tr in trs:
        css_classes = set(tr.attrs.get("class", []))
        if len({"row1", "row2"} & css_classes) < 1:
            continue

        topic_approval_request = _extract_moderatable_post(tr)

        try:
            if not (
                post_details := _extract_post_details(session, topic_approval_request)
            ):
                continue
        except IndexError as exc:
            print(f"Failed to get info for {topic_approval_request}")
            print(f"{exc=}")
            continue

        topic_approval_request.update(post_details)

        user_details = _extract_user_details(session, topic_approval_request)
        topic_approval_request.update(user_details)

        if mode == "unapproved_posts":
            topic_details = _extract_topic_details(session, topic_approval_request)
            topic_approval_request.update(topic_details)

        topic_approval_request["mode"] = mode

        posts_awaiting_approval.append(topic_approval_request)

    return posts_awaiting_approval


def _approve_moderated_post(
    session: PhpBBSession, response: requests.Response, post_id: int
) -> bool:
    moderate_post = BeautifulSoup(response.text, features="html.parser")

    moderate_form = moderate_post.select("form")[0]
    moderate_form_fields = _extract_form_fields(moderate_form)

    confirm_action = moderate_form.get("action")
    confirm_qs = parse_qs(urlparse(confirm_action).query)
    confirm_key = confirm_qs["confirm_key"][0]

    mode = moderate_form_fields["mode"]

    params = {
        "i": "queue",
        "p": post_id,
        "confirm_key": confirm_key,
    }
    form_data = {
        "notify_poster": "on",
        "i": "queue",
        "mode": mode,
        "post_id_list[0]": post_id,
        "action": "approve",
        "redirect": f"./mcp.php?i=queue&p={post_id}",
        "confirm_uid": moderate_form_fields["confirm_uid"],
        "sess": moderate_form_fields["sess"],
        "sid": moderate_form_fields["sid"],
        "confirm": "Yes",
    }

    confirm_moderate_post_response = session.post(
        "/mcp.php",
        params=params,
        data=form_data,
    )

    confirm_moderate_post = BeautifulSoup(
        confirm_moderate_post_response.text,
        features="html.parser",
    )

    response_text = None

    paragraphs = confirm_moderate_post.select("p")
    for paragraph in paragraphs:
        if "gen" not in paragraph.attrs.get("class"):
            continue
        if paragraph.attrs.get("style") != "line-height:120%":
            continue
        response_text = [c for c in paragraph.children][0]
        break

    log.debug(response_text)

    return True


def _reject_moderated_post(
    session: PhpBBSession,
    response: requests.Response,
    post_id: int,
    rejection_category: int,
    rejection_reason: str,
) -> bool:
    moderate_post = BeautifulSoup(response.text, features="html.parser")

    moderate_form = moderate_post.select("form")[0]
    moderate_form_fields = _extract_form_fields(moderate_form)

    reason_options = {}
    for option in moderate_form.select("option"):
        reason_id = int(option.attrs["value"])
        reason_string = option.text
        reason_options[reason_id] = reason_string

    confirm_action = moderate_form.get("action")
    confirm_qs = parse_qs(urlparse(confirm_action).query)
    confirm_key = confirm_qs["confirm_key"][0]

    mode = moderate_form_fields["mode"]

    params = {
        "i": "queue",
        "p": post_id,
        "confirm_key": confirm_key,
    }
    form_data = {
        "notify_poster": "on",
        "reason_id": rejection_category,
        "reason": rejection_reason,
        "i": "queue",
        "mode": mode,
        "post_id_list[0]": post_id,
        "action": "disapprove",
        "redirect": f"./mcp.php?i=queue&p=${post_id}&mode={mode}",
        "confirm_uid": moderate_form_fields["confirm_uid"],
        "sess": moderate_form_fields["sess"],
        "sid": moderate_form_fields["sid"],
        "confirm": "Yes",
    }

    confirm_moderate_post_response = session.post(
        "/mcp.php",
        params=params,
        data=form_data,
    )

    confirm_moderate_post = BeautifulSoup(
        confirm_moderate_post_response.text,
        features="html.parser",
    )

    response_text = None

    paragraphs = confirm_moderate_post.select("p")
    for paragraph in paragraphs:
        if "gen" not in paragraph.attrs.get("class"):
            continue
        if paragraph.attrs.get("style") != "line-height:120%":
            continue
        response_text = [c for c in paragraph.children][0]
        break

    log.debug(response_text)

    return True


def _moderate_post(
    session: PhpBBSession,
    post_id: int,
    approve: bool,
    rejection_category: int = None,
    rejection_reason: str = None,
) -> bool:
    url = f"/mcp.php?i=queue&mode=approve_details&p={post_id}"
    response = session.get(url)
    assert response.ok

    params = {
        "i": "queue",
        "p": post_id,
    }

    form_data = {
        "post_id_list[]": post_id,
    }

    if approve:
        form_data["action[approve]"] = "Approve"
    else:
        form_data["action[disapprove]"] = "Disapprove"

    moderate_post_response = session.post(
        "/mcp.php",
        params=params,
        data=form_data,
    )
    assert moderate_post_response.ok

    if approve:
        return _approve_moderated_post(
            session=session,
            response=moderate_post_response,
            post_id=post_id,
        )
    else:
        return _reject_moderated_post(
            session=session,
            response=moderate_post_response,
            post_id=post_id,
            rejection_category=rejection_category,
            rejection_reason=rejection_reason,
        )


def _login_to_adm(
    session: PhpBBSession,
    retried: bool = False,
):
    index_url = "/index.php"

    response = session.get(index_url)

    log.debug(response.status_code)

    index_page = BeautifulSoup(
        response.text,
        features="html.parser",
    )

    try:
        adm_href = (
            index_page.find(id="wrapfooter")
            .select_one("span")
            .contents[1]
            .attrs["href"]
        )
    except Exception as exc:
        if retried:
            raise PhpBBADMError(f"Unable to find adm sid: {exc}")

        session2, logged_in = _login_to_phpbb()

        return _login_to_adm(session=session2, retried=True)

    try:
        session_id = parse_qs(urlparse(adm_href).query)["sid"][0]
    except Exception as exc:
        log.error(f"Unable to exctract adm sid: {exc}")
        return False

    url = "/adm/index.php"
    params = {
        "sid": session_id,
    }
    response = session.get(url, params=params)

    log.debug(response.status_code)

    acp_page = BeautifulSoup(
        response.text,
        features="html.parser",
    )

    reauth_form_html = acp_page.select_one("form")

    # TODO: Redo these checks
    try:
        message = reauth_form_html.select_one("th").text
        if message != "To administer the board you must re-authenticate yourself.":
            log.debug("Didn't find to administer message!")
            return True
    except Exception as exc:
        is_in_adm = acp_page.select_one("h1").text == "Administration Control Panel"

        if is_in_adm:
            log.debug("is in adm!!!")
        else:
            log.error(f"Failed to find re-admin message: {exc}")

        return True

    # TODO: Check if there's a need to login again

    # From phpBB/includes/functions.php:2070
    #
    # // If creation_time and the time() now is zero we can assume
    #    it was not a human doing this (the check for if ($diff)...
    #
    # We basically have to sleep() for a bit during auth checks, otherwise
    # the creation_time checker will kick us out.
    time.sleep(3)

    in_form_fields = _extract_form_fields(reauth_form_html)

    pw_field = "password_" + in_form_fields["credential"]

    phpbb_password = os.environ["PHPBB_PASSWORD"]

    reauth_form = {
        "username": in_form_fields["username"],
        pw_field: phpbb_password,
        "redirect": in_form_fields["redirect"],
        "creation_time": in_form_fields["creation_time"],
        "form_token": in_form_fields["form_token"],
        "sid": in_form_fields["sid"],
        "credential": in_form_fields["credential"],
        "login": in_form_fields["login"],
    }

    url = "/adm/index.php"
    params = {
        "sid": in_form_fields["sid"],
    }
    reauth_response = session.post(url, params=params, data=reauth_form)
    assert reauth_response.ok

    adm_page = BeautifulSoup(reauth_response.text, features="html.parser")

    header_div = adm_page.select_one("h1")

    if not header_div:
        # breakpoint()

        if retried:
            raise PhpBBADMError("Unable to find h1 text")

        session2, logged_in = _login_to_phpbb()

        return _login_to_adm(session=session2, retried=True)

    is_in_adm = header_div.text == "Administration Control Panel"

    if is_in_adm:
        log.debug("in ADM!!!")
        return True

    try:
        sign_in_error_text = adm_page.select_one("form").find(class_="error").text
        log.error("Failed to sign in to ADM")
    except Exception as exc:
        log.error(
            f"unexpected error finding error message after attempting to sign in to adm: {exc}"
        )

        raise exc
    else:
        raise PhpBBADMError(sign_in_error_text)

    return False


def _ban_user(
    session: PhpBBSession,
    user_id: int,
    reviewer_name: str,
    reason_shown: str,
    action: BanAction,
    retried: bool = False,
) -> bool:
    index_url = "/adm/index.php"
    params = {
        "i": "users",
        "u": user_id,
        "sid": session.sid,
    }
    response = session.get(index_url, params=params)

    log.debug(response.status_code)

    user_page = BeautifulSoup(
        response.text,
        features="html.parser",
    )

    user_quick_tools = user_page.find(id="user_quick_tools")
    if not user_quick_tools:
        if retried is False:
            session2, logged_in2 = _login_to_phpbb()

            if not _login_to_adm(session2):
                log.error("failed to sign in to ADM in _ban_user")
                return False

            return _ban_user(
                session=session2,
                user_id=user_id,
                reviewer_name=reviewer_name,
                reason_shown=reason_shown,
                action=action,
                retried=True,
            )

        log.error("Unable to find ban user quick tools!!")
        return False

    quick_actions_form_fields = _extract_form_fields(user_quick_tools)

    reason_via = f"via Discord Bot ({reviewer_name})"

    ban_reasons = {
        "banuser": f"Username banned {reason_via}",
        "banemail": f"Email address banned {reason_via}",
        "banip": f"IP banned {reason_via}",
    }

    if getattr(action, "value", None) not in ban_reasons:
        raise ValueError(f"{action} is not a valid ban action")

    ban_url = "/adm/index.php"
    ban_params = {
        "i": "acp_users",
        "sid": session.sid,
        "mode": "overview",
        "u": user_id,
    }
    ban_data = {
        "action": action.value,
        "ban_reason": ban_reasons[action.value],
        "ban_give_reason": reason_shown,
        "update": quick_actions_form_fields["update"],
        "creation_time": quick_actions_form_fields["creation_time"],
        "form_token": quick_actions_form_fields["form_token"],
    }

    # From phpBB/includes/functions.php:2070
    #
    # // If creation_time and the time() now is zero we can assume
    #    it was not a human doing this (the check for if ($diff)...
    #
    # We basically have to sleep() for a bit during auth checks, otherwise
    # the creation_time checker will kick us out.
    time.sleep(3)

    ban_response = session.post(ban_url, params=ban_params, data=ban_data)
    assert ban_response.ok

    ban_page_result_div = BeautifulSoup(
        ban_response.text,
        features="html.parser",
    )

    ban_message_div = ban_page_result_div.find("div", {"class": "main"}).select_one("p")
    ban_message = ban_message_div.text.removesuffix(" Back to previous page")[:-1]

    log.debug(ban_message)

    if ban_message == "Ban entered successfully.":
        return True

    return False


def unban_username(username: str):
    session, logged_in = _login_to_phpbb()

    if not _login_to_adm(session):
        log.error("failed to sign in to ADM")
        return

    index_url = "/adm/index.php"
    params = {
        "i": "acp_ban",
        "mode": "user",
        "sid": session.sid,
    }
    response = session.get(index_url, params=params)

    log.debug(response.status_code)

    ban_page = BeautifulSoup(
        response.text,
        features="html.parser",
    )

    unban_div = ban_page.find(id="acp_unban")
    unban_form = _extract_form_fields(unban_div)
    select_options = unban_div.find("select", {"name": "unban[]"})

    unban_id = None
    for option in select_options.select("option"):
        if option.text == username:
            unban_id = option.attrs["value"]
            break

    if unban_id is None:
        log.error(f"Unable to find banid for username {username}")
        return False

    unban_params = {
        "i": "acp_ban",
        "sid": session.sid,
        "mode": "user",
    }
    unban_data = {
        "unban[]": unban_id,
        "unbanlength": "",
        "unbanreason": "",
        "unbangivereason": "",
        "unbansubmit": unban_form["unbansubmit"],
        "creation_time": unban_form["creation_time"],
        "form_token": unban_form["form_token"],
    }

    time.sleep(3)

    unban_response = session.post(index_url, params=unban_params, data=unban_data)
    assert unban_response.ok

    unban_page = BeautifulSoup(
        unban_response.text,
        features="html.parser",
    )

    unban_message_div = unban_page.find("div", {"class": "main"}).select_one("p")
    unban_message = unban_message_div.text.removesuffix(" Back to previous page")[:-1]

    log.debug(unban_message)

    if unban_message == "The banlist has been updated successfully.":
        return True

    return False


def ban_user_by_username(
    user_id: int,
    reviewer_name: str,
    reason_shown: str,
) -> bool:
    session, logged_in = _login_to_phpbb()

    if not _login_to_adm(session):
        log.error("failed to sign in to ADM")
        return False

    return _ban_user(
        session=session,
        user_id=user_id,
        reviewer_name=reviewer_name,
        reason_shown=reason_shown,
        action=BanAction.BANUSER,
    )


def load_topics_awaiting_approval():
    session, logged_in = _login_to_phpbb()

    topics_awaiting_approval = _load_posts_topics_awaiting_approval(
        session=session,
        mode="unapproved_topics",
    )

    return topics_awaiting_approval


def load_posts_awaiting_approval():
    session, logged_in = _login_to_phpbb()

    posts_awaiting_approval = _load_posts_topics_awaiting_approval(
        session=session,
        mode="unapproved_posts",
    )

    return posts_awaiting_approval


def moderate_post(
    post_id: int,
    approve: bool,
    rejection_category: int = None,
    rejection_reason: str = None,
) -> bool:
    session, logged_in = _login_to_phpbb()

    response = _moderate_post(
        session=session,
        post_id=post_id,
        approve=approve,
        rejection_category=rejection_category,
        rejection_reason=rejection_reason,
    )

    return response
