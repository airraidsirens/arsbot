from sqlalchemy.orm import Session

from ...db import bot_session
from ...models import MediaWikiAccountRequest
from ...mediawiki.automod import (
    SpamCategory,
    get_spam_categories_for_request,
)
from ....utils.text_table import TextTable


def _get_spam_scores(session: Session, action: int):
    requests = (
        session.query(
            MediaWikiAccountRequest.username,
            MediaWikiAccountRequest.email,
            MediaWikiAccountRequest.biography,
            MediaWikiAccountRequest.handled_by_name,
        )
        .filter_by(action=action)
        .filter(
            MediaWikiAccountRequest.automod_spam_categories != "",
        )
    )

    spam_results = [get_spam_categories_for_request(result) for result in requests]

    as_spam = [len(categories) > 0 for categories in spam_results].count(True)

    not_as_spam = [len(categories) == 0 for categories in spam_results].count(True)

    has_link = [
        SpamCategory.HAS_LINK in categories for categories in spam_results
    ].count(True)

    has_non_ascii = [
        SpamCategory.HAS_NON_ASCII in categories for categories in spam_results
    ].count(True)

    has_html = [
        SpamCategory.HAS_HTML in categories for categories in spam_results
    ].count(True)

    total_requests = as_spam + not_as_spam

    if not total_requests:
        catch_rate = "No Requests"
    elif action == 1:
        catch_rate = round((100 - ((as_spam / total_requests) * 100)), 2)
    else:
        catch_rate = round(((as_spam / total_requests) * 100), 2)

    action_str = "approved" if action == 1 else "denied"

    table = TextTable()

    table.set_header("WIP AutoMod Stats")
    table.set_footer("End of Stats")

    table.add_key_value("action", action_str)
    table.add_key_value("total", total_requests)
    table.add_key_value("catch_%", catch_rate)
    table.add_key_value("not_as_spam", not_as_spam)
    table.add_key_value("as_spam", as_spam)
    table.add_key_value("has_link", has_link)
    table.add_key_value("has_non_ascii", has_non_ascii)
    table.add_key_value("has_html", has_html)

    message = table.str()

    return message


def automod_wiki_stats():
    with bot_session() as session:
        return _get_spam_scores(session=session, action=0)
