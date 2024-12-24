import json
import re

import responses

from arsbot.utils.ipinfo import get_ip_address_info


class Counter:
    def __init__(self):
        self._count = 0

    def incr(self) -> None:
        self._count += 1

    def reset(self) -> None:
        self._count = 0

    @property
    def count(self) -> int:
        return self._count


counter = Counter()


def _get_ipinfo_callback(request):
    ip = request.url.removeprefix("https://ipinfo.io/")

    ip_addrs = {
        "127.0.0.1": {
            "hostname": "localhost",
            "city": "Los Angeles",
            "region": "California",
            "country": "USA",
            "org": "localnet",
            "status_code": 200,
        },
    }

    ip_info = ip_addrs.get(ip, {})
    staus_code = ip_info.pop("status_code", 404)
    content = json.dumps(ip_info)
    headers = {
        "Content-Type": "application/json",
    }

    counter.incr()
    return (staus_code, headers, content)


@responses.activate
def test_get_ip_address_info(bot_env_config, patch_ipinfo):
    counter.reset()

    responses.add_callback(
        responses.GET,
        url=re.compile(r"https://ipinfo\.io/[0-9\.]+$"),
        callback=_get_ipinfo_callback,
    )

    expected = {
        "hostname": "localhost",
        "city": "Los Angeles",
        "region": "California",
        "country": "USA",
        "org": "localnet",
    }

    ip_info = get_ip_address_info("127.0.0.1")
    assert ip_info == expected
    assert counter.count == 1

    # Make sure cache worked
    ip_info = get_ip_address_info("127.0.0.1")
    assert ip_info == expected
    assert counter.count == 1

    # Make sure broken responses work
    ip_info = get_ip_address_info("0")
    assert ip_info is None
    assert counter.count == 2

    # Shouldn't be cached since the response failed
    ip_info = get_ip_address_info("0")
    assert ip_info is None
    assert counter.count == 3
