from arsbot.version import VERSION


def test_version():
    assert len(VERSION.split(".")) == 3
