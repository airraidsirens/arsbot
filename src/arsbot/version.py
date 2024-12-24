import importlib.metadata
import subprocess


VERSION = importlib.metadata.version("arsbot")

_git_version_process = subprocess.run(
    "git describe --always --dirty".split(" "),
    stdout=subprocess.PIPE,
    stderr=subprocess.STDOUT,
)
GIT_VERSION = _git_version_process.stdout.decode("utf-8").strip()

_git_datetime_raw_process = subprocess.run(
    ["git", "log", "-1", '--format="%at"'],
    stdout=subprocess.PIPE,
    stderr=subprocess.STDOUT,
)
__git_datetime_raw = (
    _git_datetime_raw_process.stdout.decode("utf-8").strip().replace('"', "")
)

_git_datetime_process = subprocess.run(
    ["date", "-d", f"@{__git_datetime_raw}", "+%Y/%m/%d_%H:%M:%S_%Z"],
    stdout=subprocess.PIPE,
    stderr=subprocess.STDOUT,
)
GIT_DATETIME = _git_datetime_process.stdout.decode("utf-8").strip()

_git_user_name_process = subprocess.run(
    'git log -1 --format="%an"'.split(" "),
    stdout=subprocess.PIPE,
    stderr=subprocess.STDOUT,
)
GIT_USER_NAME = _git_user_name_process.stdout.decode("utf-8").strip().replace('"', "")

_git_user_email_process = subprocess.run(
    'git log -1 --format="%ae"'.split(" "),
    stdout=subprocess.PIPE,
    stderr=subprocess.STDOUT,
)
GIT_USER_EMAIL = _git_user_email_process.stdout.decode("utf-8").strip().replace('"', "")
