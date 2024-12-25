from arsbot.discord.slash_commands.stats_automod.forum_stats import automod_forum_stats


def test_automod_forum_stats():
    text = automod_forum_stats()

    assert text == "Forum stats not implemented yet"
