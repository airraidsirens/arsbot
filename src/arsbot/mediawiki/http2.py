import logging
import os
import re
import urllib.parse

import arrow
from bs4 import BeautifulSoup
from bs4.element import Tag
import requests
import msgpack


log = logging.getLogger("arsbot")
INVALID_SESSION_TEXT = "There seems to be a problem with your login session"


class MWSession(requests.Session):
    pass


def _extract_login_form(form: Tag):
    form_fields = {}

    for field in form.find_all("input"):
        field_attrs = field.attrs
        if "value" not in field_attrs:
            continue
        form_fields[field_attrs["name"]] = field_attrs["value"]

    return form_fields


def _load_session(session):
    try:
        with open("mw_session.data", "rb") as fp:
            session_data = msgpack.load(fp)
    except FileNotFoundError:
        return False
    except ValueError:
        os.remove("mw_session.data")
        return False

    session.cookies.clear()

    for key, value in session_data:
        session.cookies.set(key, value)

    return True


def _validate_session(session):
    base_url = os.environ["WIKI_BASE_URL"]
    response = session.get(base_url)
    home_page = BeautifulSoup(response.text, features="html.parser")
    if home_page.find(id="pt-logout") is not None:
        return True

    return False


def _login_to_mediawiki(force_fresh: bool = False):
    session = MWSession()

    if force_fresh:
        try:
            os.remove("mw_session.data")
        except FileNotFoundError:
            pass

    if _load_session(session) and _validate_session(session):
        return session, True

    base_url = os.environ["WIKI_BASE_URL"]

    url = f"{base_url}/index.php?title=Special:UserLogin"
    response = session.get(url)
    assert response.status_code == 200

    login_page = BeautifulSoup(response.text, features="html.parser")

    login_form_fields = None
    for form in login_page.body.find_all("form"):
        if form.attrs.get("name") != "userlogin":
            continue

        login_form_fields = _extract_login_form(form)
        break

    mw_username = os.environ["WIKI_USERNAME"]
    mw_password = os.environ["WIKI_PASSWORD"]

    login_form = {
        "title": "Special:UserLogin",
        "wpName": mw_username,
        "wpPassword": mw_password,
        "wpRemember": "1",
        "wploginattempt": "Log in",
        "wpEditToken": login_form_fields["wpEditToken"],
        "authAction": login_form_fields["authAction"],
        "force": "",
        "wpLoginToken": login_form_fields["wpLoginToken"],
    }
    url = f"{base_url}/Special:UserLogin"
    response = session.post(url, params=login_form)

    logged_in_page = BeautifulSoup(response.text, features="html.parser")
    if logged_in_page.find(id="pt-logout") is not None:
        # Save cookies
        cookies = msgpack.dumps(session.cookies.items())
        with open("mw_session.data", "wb+") as fp:
            fp.write(cookies)

    return session, True


def _get_accounts(session, url):
    response = session.get(url)

    requests_page = BeautifulSoup(response.text, features="html.parser")

    keys = {"Username", "Name", "Email", "Biography"}

    page_entries = []

    for entry in requests_page.find_all("table"):
        if "mw-confirmaccount-body-0" not in entry.attrs.get("class", []):
            continue

        account_request = {}
        for child in entry.children:
            for key in keys:
                if not child.text.startswith(key):
                    continue

                account_request[key] = child.text.removeprefix(key)

        page_entries.append(account_request)

    account_requests = {}

    if not page_entries:
        return account_requests, None

    mw_date_entered_pat = re.compile(r"(20\d\d-\d\d-\d\dT\d\d:\d\d:\d\d)")

    for index, entry in enumerate(requests_page.find_all("ul")[0].children):
        if not (href := entry.find("a").attrs.get("href")):
            continue

        account_requests[href] = page_entries[index]

        date_res = mw_date_entered_pat.search(entry.contents[0])
        entered_iso = date_res.group(1)
        account_requests[href]["RequestedTimestamp"] = arrow.get(entered_iso)
        href_parts = dict(urllib.parse.parse_qsl(href.removeprefix("/index.php?")))
        account_requests[href]["acrid"] = int(href_parts["acrid"])

    if not (next_url := requests_page.find(rel="next")):
        return account_requests, None

    return account_requests, next_url.attrs["href"]


def _load_account_requests(session):
    account_requests = {}

    base_url = os.environ["WIKI_BASE_URL"]

    next_link = (
        f"{base_url}/index.php?title=Special:ConfirmAccounts/authors&wpShowHeld=0"
    )

    while next_link:
        accounts, next_link = _get_accounts(session, next_link)
        if next_link and not next_link.startswith("https://"):
            next_link = base_url + next_link

        account_requests.update(accounts)

    return account_requests


def create_account_from_request(
    session, email, request, response, response_page, retried
):
    base_url = os.environ["WIKI_BASE_URL"]

    wp_edit_token = response_page.find("input", id="wpEditToken").attrs["value"]

    create_token = None
    for page_input in response_page.find_all("input"):
        if page_input.attrs.get("name", "") == "wpCreateaccountToken":
            create_token = page_input.attrs["value"]

    form = {
        "title": "Special:CreateAccount",
        "wpName": request.username,
        "wpCreateaccountMail": "1",
        "email": email,
        "realname": request.name,
        "reason": "",
        "wpCreateaccount": "Create account",
        "wpEditToken": wp_edit_token,
        "authAction": "create",
        "force": "",
        "wpCreateaccountToken": create_token,
        "AccountRequestId": request.acrid,
    }
    create_url = f"{base_url}/index.php?title=Special:CreateAccount&returnto=Special:ConfirmAccounts/authors"

    create_response = session.post(create_url, params=form)

    create_response_page = BeautifulSoup(create_response.text, features="html.parser")
    page_error = create_response_page.find("div", class_="errorbox")
    error_box = create_response_page.find("div", class_="mw-message-box-error")

    if not page_error and not error_box and create_response.status_code == 200:
        return True
    elif INVALID_SESSION_TEXT in page_error.text and not retried:
        log.debug("retrying...")
        return None
    else:
        log.error(error_box)
        log.error(
            f"unknown issue when handling create: {create_response} {create_response.status_code}"
        )
        return False


def process_account_request(
    request,  # MediaWikiAccountRequest
    approved: bool,
    reviewer_name: str,
    retried: bool = False,
):
    log.debug(f"processing account! {request.acrid}, {approved=}, {reviewer_name=}")

    session, logged_in = _login_to_mediawiki(force_fresh=retried)

    base_url = os.environ["WIKI_BASE_URL"]

    request_url = f"{base_url}/index.php?title=Special:ConfirmAccounts/authors&acrid={request.acrid}"
    response = session.get(request_url)

    request_page = BeautifulSoup(response.text, features="html.parser")

    edit_token = ""
    for form_input in request_page.find_all("input"):
        if form_input.attrs.get("name", "") == "wpEditToken":
            edit_token = form_input.attrs["value"]

    submit_type = "accept" if approved else "spam"
    moderate_user_form = {
        "wpNewName": request.username,
        "wpNewBio": request.biography,
        "wpNotes": "",
        "wpSubmitType": submit_type,
        "wpReason": "",
        "title": "Special:ConfirmAccounts/authors",
        "action": "reject",
        "acrid": request.acrid,
        "wpShowRejects": "",
        "wpEditToken": edit_token,
    }

    update_url = f"{base_url}/Special:ConfirmAccounts/authors"
    response = session.post(update_url, params=moderate_user_form)

    response_page = BeautifulSoup(response.text, features="html.parser")
    page_error = response_page.find("div", class_="errorbox")

    approve_part_1_success = False
    req_value = None

    if approved:
        have_email = response_page.find("input", id="wpEmail")
        if have_email and have_email.attrs["value"] == request.email.removesuffix(
            " (confirmed)"
        ):
            approve_part_1_success = True

            req_value = have_email.attrs["value"]

    if approved and approve_part_1_success and not page_error:
        created = create_account_from_request(
            session=session,
            email=req_value,
            request=request,
            response=response,
            response_page=response_page,
            retried=retried,
        )
        if created is None and not retried:
            return process_account_request(
                request=request,
                approved=approved,
                reviewer_name=reviewer_name,
                retried=True,
            )
        return created

    if response.status_code == 200 and not page_error:
        return True
    elif page_error:
        log.error(page_error.text)
        if INVALID_SESSION_TEXT in page_error.text and not retried:
            log.debug("retrying...")
            return process_account_request(
                request=request,
                approved=approved,
                reviewer_name=reviewer_name,
                retried=True,
            )
        return False
    else:
        log.error("non 200!")
        log.error(response.text)
        return False


def get_pending_accounts():
    session, logged_in = _login_to_mediawiki()

    account_requests = _load_account_requests(session)
    return account_requests
