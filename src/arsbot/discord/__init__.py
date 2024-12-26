import sys
import warnings

# 'audioop' is deprecated and slated for removal in Python 3.13
warnings.filterwarnings(
    action="ignore",
    category=DeprecationWarning,
    module="discord.player",
)


if sys.version_info.minor >= 13:  # pragma: nocover
    # Removed in 3.13, discord.player relies on it
    class AudioopNamespace:
        def mul(self, *args, **kwargs):
            pass

    sys.modules["audioop"] = AudioopNamespace()
