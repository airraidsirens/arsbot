import sqlalchemy as sa

from ..db import BotBase


class PhpbbPostRequest(BotBase):
    __tablename__ = "discord_phpbb_post_requests"

    def __repr__(self) -> str:
        return f"<PhpbbPostRequest {self.post_id=} {self.is_for_new_topic=} {self.discord_message_id=}>"

    id = sa.Column(
        sa.Integer,
        primary_key=True,
    )
    author_id = sa.Column(
        sa.Integer,
        nullable=False,
        doc="The ID of the authors phpbb account.",
    )
    author_name = sa.Column(
        sa.String,
        nullable=False,
        doc="The name of the authors phpbb account.",
    )
    author_url = sa.Column(
        sa.String,
        nullable=False,
        doc="The URL to the authors phpbb account.",
    )
    forum_name = sa.Column(
        sa.String,
        nullable=False,
        doc="The name of the phpbb forum.",
    )
    forum_url = sa.Column(
        sa.String,
        nullable=False,
        doc="The URL of the phpbb forum.",
    )
    post_id = sa.Column(
        sa.Integer,
        nullable=False,
        doc="The ID of the phpbb post.",
    )
    post_ip_address = sa.Column(
        sa.String,
        nullable=False,
        doc="The IP address used to create the post.",
    )
    post_ip_hostname = sa.Column(
        sa.String,
        default=None,
        doc="The hostname resolved from the IP address.",
    )
    post_ip_location = sa.Column(
        sa.String,
        default=None,
        doc="The location that the IP address is registered to.",
    )
    post_ip_organization = sa.Column(
        sa.String,
        default=None,
        doc="The organization that owns the IP address.",
    )
    post_text = sa.Column(
        sa.String,
        default=None,
        doc="The text within the phpbb post.",
    )
    post_time = sa.Column(
        sa.DateTime,
        nullable=False,
        doc="When the post was created.",
    )
    topic_name = sa.Column(
        sa.String,
        nullable=False,
        doc="The name of the topic for the phpbb post.",
    )
    topic_url = sa.Column(
        sa.String,
        nullable=False,
        doc="The URL of the topic for the phpbb post.",
    )
    user_group_list = sa.Column(
        sa.String,
        nullable=False,
        doc="The list of groups the user belongs to.",
    )
    user_join_date = sa.Column(
        sa.DateTime,
        nullable=False,
        doc="When the user joined the board.",
    )
    user_post_count = sa.Column(
        sa.Integer,
        nullable=False,
        doc="The amount of posts the user has created.",
    )
    user_warning_count = sa.Column(
        sa.Integer,
        nullable=False,
        doc="The amount of warnings the user has received.",
    )
    is_for_new_topic = sa.Column(
        sa.Integer, nullable=False, doc="Whether or not this record is for a new topic."
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
