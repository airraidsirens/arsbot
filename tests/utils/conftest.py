import pytest

from arsbot.utils import ipinfo


@pytest.fixture(autouse=True, scope="function")
def patch_ipinfo(bot_data_dir):
    old_ip_db_file = str(ipinfo.IP_DB_FILE)

    ip_db_file = bot_data_dir / "ip_addresses.bin"
    ipinfo.IP_DB_FILE = str(ip_db_file)

    yield

    ipinfo.IP_DB_FILE = old_ip_db_file
