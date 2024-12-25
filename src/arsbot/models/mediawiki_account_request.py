import sqlalchemy as sa

from .base import BotBase


class MediaWikiAccountRequest(BotBase):
    __tablename__ = "discord_mediawiki_account_requests"

    def __repr__(self) -> str:
        return f"<MediaWikiAccountRequest {self.acrid=} {self.discord_message_id=}>"

    id = sa.Column(
        sa.Integer,
        primary_key=True,
    )
    acrid = sa.Column(
        sa.Integer,
        nullable=False,
        doc="Identifies the mediawiki account request id.",
    )
    username = sa.Column(
        sa.String,
        default=None,
        doc="The username the user requested.",
    )
    name = sa.Column(
        sa.String,
        default=None,
        doc="The name the user requested.",
    )
    email = sa.Column(
        sa.String,
        default=None,
        doc="The email the user requested.",
    )
    biography = sa.Column(
        sa.String,
        default=None,
        doc="The biography the user set.",
    )
    discord_message_id = sa.Column(
        sa.Integer,
        nullable=False,
        doc="Identifies the message id.",
    )
    discord_channel_id = sa.Column(
        sa.Integer,
        nullable=False,
        doc="Identifies the channel id.",
    )
    discord_guild_id = sa.Column(
        sa.Integer,
        nullable=False,
        doc="Identifies the discord server.",
    )
    request_url = sa.Column(
        sa.String,
        nullable=False,
        doc="The endpoint to POST to",
    )
    time_created = sa.Column(
        sa.DateTime,
        nullable=False,
        doc="When the request was created",
    )
    time_resolved = sa.Column(
        sa.DateTime,
        default=None,
        doc="Timestamp when the request was handled.",
    )
    action = sa.Column(
        sa.Integer,
        default=None,
        doc="The action taken",
    )
    handled_by_id = sa.Column(
        sa.Integer,
        default=None,
        doc="Identifies who handled the request.",
    )
    handled_by_name = sa.Column(
        sa.String,
        default=None,
        doc="Identifies the name of the user who handled the request",
    )
    automod_spam_categories = sa.Column(
        sa.String,
        default=None,
        doc="Coma separated list of spam categories that this request was detected in",
    )
    automod_manual_review_set_by_id = sa.Column(
        sa.Integer,
        default=None,
        doc="Identifies the discord id of the user who overrode automod",
    )
    automod_manual_review_set_by_name = sa.Column(
        sa.String,
        default=None,
        doc="Identifies the name of the user who overrode automod",
    )
    automod_manual_review_set_at = sa.Column(
        sa.DateTime,
        default=None,
        doc="Identifies when automod was overrode",
    )
