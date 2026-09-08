from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade():
    op.create_table(
        "m3u_sources",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("input_url", sa.String(500), nullable=True),
        sa.Column("input_file", sa.String(500), nullable=True),
        sa.Column("path", sa.String(500), nullable=True),
        sa.Column("m3u_provided_epg_url", sa.Text(), nullable=True),
        sa.Column("channel_count", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.String(30), nullable=False),
        sa.Column("updated_at", sa.String(30), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "channels",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("channel_id", sa.String(100), nullable=False),
        sa.Column("tvg_prefix", sa.String(100), nullable=True),
        sa.Column("tvg_suffix", sa.String(50), nullable=True),
        sa.Column("tvg_ids", sa.JSON(), nullable=True),
        sa.Column("titles", sa.JSON(), nullable=True),
        sa.Column("clean_titles", sa.JSON(), nullable=True),
        sa.Column("display_name", sa.String(300), nullable=True),
        sa.Column("tvg_names", sa.JSON(), nullable=True),
        sa.Column("country", sa.JSON(), nullable=True),
        sa.Column("group_titles", sa.JSON(), nullable=True),
        sa.Column("tvg_logos", sa.JSON(), nullable=True),
        sa.Column("resolutions", sa.JSON(), nullable=True),
        sa.Column("flags", sa.JSON(), nullable=True),
        sa.Column("m3u_provided_uris", sa.JSON(), nullable=True),
        sa.Column("matched_feed_id", sa.String(50), nullable=True),
        sa.Column("canonical_name", sa.String(200), nullable=True),
        sa.Column("alt_names", sa.JSON(), nullable=True),
        sa.Column("categories", sa.JSON(), nullable=True),
        sa.Column("website", sa.String(500), nullable=True),
        sa.Column("visit_count", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("is_favorite", sa.Boolean(), nullable=False, server_default=sa.text("0")),
        sa.Column("created_at", sa.String(30), nullable=False),
        sa.Column("updated_at", sa.String(30), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "m3u_channels",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("channel_id", sa.Integer(), nullable=False),
        sa.Column("source_id", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.String(30), nullable=False),
        sa.Column("updated_at", sa.String(30), nullable=False),
        sa.ForeignKeyConstraint(["channel_id"], ["channels.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["source_id"], ["m3u_sources.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("channel_id", "source_id"),
    )
    op.create_table(
        "feeds",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("channel_id", sa.Integer(), nullable=False),
        sa.Column("feed_id", sa.String(50), nullable=True),
        sa.Column("feed_name", sa.String(100), nullable=True),
        sa.Column("format", sa.String(20), nullable=True),
        sa.Column("is_main", sa.Boolean(), nullable=True),
        sa.Column("broadcast_area", sa.JSON(), nullable=True),
        sa.Column("languages", sa.JSON(), nullable=True),
        sa.Column("streams", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.String(30), nullable=False),
        sa.Column("updated_at", sa.String(30), nullable=False),
        sa.ForeignKeyConstraint(["channel_id"], ["channels.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("channel_id", "feed_id"),
    )

    op.create_index("idx_channel_channel_id", "channels", ["channel_id"])
    op.create_index("idx_channel_tvg_suffix", "channels", ["tvg_suffix"])
    op.create_index("idx_m3u_source", "m3u_channels", ["source_id"])
    op.create_index("idx_feed_channel", "feeds", ["channel_id"])
    op.create_index("idx_feed_format", "feeds", ["format"])
    op.create_index("idx_feed_broadcast", "feeds", [sa.text("json_extract(broadcast_area, '$[0]')")])
    op.create_table(
        "watch_sessions",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("channel_id", sa.Integer(), nullable=False),
        sa.Column("started_at", sa.String(30), nullable=False),
        sa.Column("ended_at", sa.String(30), nullable=False),
        sa.Column("duration_seconds", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("completed", sa.Boolean(), nullable=False, server_default=sa.text("0")),
        sa.Column("created_at", sa.String(30), nullable=False),
        sa.ForeignKeyConstraint(["channel_id"], ["channels.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("idx_watch_channel", "watch_sessions", ["channel_id"])
    op.create_index("idx_watch_started", "watch_sessions", ["started_at"])
    op.create_index("idx_watch_ended", "watch_sessions", ["ended_at"])
    op.create_table(
        "audit_logs",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("category", sa.String(60), nullable=False),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("details", sa.JSON(), nullable=True),
        sa.Column("reason", sa.String(200), nullable=True),
        sa.Column("shared", sa.Boolean(), nullable=False, server_default=sa.text("0")),
        sa.Column("created_at", sa.String(30), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("idx_audit_category", "audit_logs", ["category"])
    op.create_index("idx_audit_created", "audit_logs", ["created_at"])

    op.create_table(
        "settings",
        sa.Column("key", sa.String(200), nullable=False),
        sa.Column("value", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.String(30), nullable=False),
        sa.Column("updated_at", sa.String(30), nullable=False),
        sa.PrimaryKeyConstraint("key"),
    )
    op.create_index("idx_settings_key", "settings", ["key"])


def downgrade():
    op.drop_column("channels", "visit_count")
    op.drop_table("watch_sessions")
    op.drop_table("audit_logs")
    op.drop_table("settings")
    op.drop_table("feeds")
    op.drop_table("m3u_channels")
    op.drop_table("channels")
    op.drop_table("m3u_sources")
