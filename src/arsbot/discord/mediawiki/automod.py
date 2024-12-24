from dataclasses import dataclass
import enum
import re

URL_PAT = re.compile(
    (
        r"(https?:\/\/(www\.)?[-a-zA-Z0-9@:%._\+~#=]{1,256}\.[a-zA-Z0-9()]{1,6})\b([-a-zA-Z0-9()@:%_\+.~#?&\/\/=]*)"
    ),
    flags=re.MULTILINE,
)

NON_ASCII_PAT = re.compile((r"[^\x00-\x7F‘’]+"), flags=re.MULTILINE)

HTML_PATH = re.compile((r"<[^>]*>"), flags=re.MULTILINE)


@dataclass
class Request:
    username: str
    email: str
    biography: str
    handled_by_name: str


class SpamCategory(enum.Enum):
    HAS_LINK = 1
    HAS_NON_ASCII = 2
    HAS_HTML = 3


def get_spam_categories_for_request(request_tuple):
    spam_flags = set()

    request = Request(*request_tuple)

    if URL_PAT.findall(request.biography):
        spam_flags.add(SpamCategory.HAS_LINK)

    if NON_ASCII_PAT.findall(request.biography):
        spam_flags.add(SpamCategory.HAS_NON_ASCII)

    if HTML_PATH.findall(request.biography):
        spam_flags.add(SpamCategory.HAS_HTML)

    return spam_flags
