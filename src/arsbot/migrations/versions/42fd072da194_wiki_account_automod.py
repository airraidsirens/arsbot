"""wiki_account_automod

Revision ID: 42fd072da194
Revises: 60cdccb2bbcf
Create Date: 2024-11-30 06:52:45.184499

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "42fd072da194"
down_revision: Union[str, None] = "60cdccb2bbcf"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "discord_mediawiki_account_requests",
        sa.Column("automod_spam_categories", sa.String(), nullable=True),
    )
    op.add_column(
        "discord_mediawiki_account_requests",
        sa.Column("automod_manual_review_set_by_id", sa.Integer(), nullable=True),
    )
    op.add_column(
        "discord_mediawiki_account_requests",
        sa.Column("automod_manual_review_set_by_name", sa.String(), nullable=True),
    )
    op.add_column(
        "discord_mediawiki_account_requests",
        sa.Column("automod_manual_review_set_at", sa.DateTime(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("discord_mediawiki_account_requests", "automod_manual_review_set_at")
    op.drop_column(
        "discord_mediawiki_account_requests", "automod_manual_review_set_by_name"
    )
    op.drop_column(
        "discord_mediawiki_account_requests", "automod_manual_review_set_by_id"
    )
    op.drop_column("discord_mediawiki_account_requests", "automod_spam_categories")
