import logging
import os

import msgpack
import requests


IP_DB_FILE = "ip_addresses.bin"

log = logging.getLogger("arsbot")


def _load_ip_db():
    try:
        with open(IP_DB_FILE, "rb") as fp:
            return msgpack.load(fp)
    except FileNotFoundError:
        return {}
    except ValueError:
        os.remove(IP_DB_FILE)
        return {}


def _store_ip_db(ip_database: dict):
    with open(IP_DB_FILE, "wb+") as fp:
        fp.write(msgpack.dumps(ip_database))

    log.debug(f"Stored {len(ip_database)} entries to {IP_DB_FILE}")


def get_ip_address_info(post_ip_address: str):
    ip_database = _load_ip_db()
    if post_ip_address in ip_database:
        return ip_database[post_ip_address]

    ipinfo_response = requests.get(f"https://ipinfo.io/{post_ip_address}")
    if not ipinfo_response.ok:
        log.error(ipinfo_response.content)
        return None

    ipinfo = ipinfo_response.json()

    ip_database[post_ip_address] = ipinfo

    _store_ip_db(ip_database)

    return ipinfo
