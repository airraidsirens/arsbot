from arsbot.discord.mediawiki.automod import (
    get_spam_categories_for_request,
    SpamCategory,
)

import pytest


@pytest.mark.parametrize(
    "biography,result",
    [
        ("biography", []),
        ("test test https://google.com test", [SpamCategory.HAS_LINK]),
        ("test test <br> test", [SpamCategory.HAS_HTML]),
        ("test test <br /> test", [SpamCategory.HAS_HTML]),
        (
            'test test <input type="string" name="email" /> test',
            [SpamCategory.HAS_HTML],
        ),
    ],
)
def test_get_spam_categories_for_request(biography, result):
    categories = get_spam_categories_for_request(
        (
            "username",
            "email",
            biography,
            "handled_by_name",
        )
    )

    assert categories == set(result)
