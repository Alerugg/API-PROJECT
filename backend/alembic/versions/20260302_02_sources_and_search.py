"""sources_and_search

Revision ID: 20260302_02
Revises: 20260302_01
Create Date: 2026-03-02 00:10:00.000000
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "20260302_02"
down_revision: Union[str, None] = "20260302_01"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "sources",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_sources_name", "sources", ["name"], unique=True)

    bind = op.get_bind()
    raw_json_type = postgresql.JSONB(astext_type=sa.Text()) if bind.dialect.name == "postgresql" else sa.JSON()

    op.create_table(
        "source_records",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("source_id", sa.Integer(), sa.ForeignKey("sources.id"), nullable=False),
        sa.Column("checksum", sa.String(length=64), nullable=False),
        sa.Column("raw_json", raw_json_type, nullable=False),
        sa.Column("ingested_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("source_id", "checksum", name="uq_source_checksum"),
    )
    op.create_index("ix_source_records_source_id", "source_records", ["source_id"], unique=False)
    op.create_index("ix_source_records_checksum", "source_records", ["checksum"], unique=False)

    if bind.dialect.name == "postgresql":
        op.execute(
            """
            CREATE VIEW search_documents AS
            SELECT 'card'::text AS doc_type,
                   c.id AS object_id,
                   c.game_id,
                   c.name::text AS title,
                   NULL::text AS subtitle,
                   to_tsvector('simple', coalesce(c.name, '')) AS tsv
            FROM cards c
            UNION ALL
            SELECT 'set'::text,
                   s.id,
                   s.game_id,
                   s.name::text,
                   s.code::text,
                   to_tsvector('simple', coalesce(s.name, '') || ' ' || coalesce(s.code, ''))
            FROM sets s
            UNION ALL
            SELECT 'print'::text,
                   p.id,
                   s.game_id,
                   (c.name || ' #' || p.collector_number)::text,
                   s.code::text,
                   to_tsvector('simple', coalesce(c.name, '') || ' ' || coalesce(s.name, '') || ' ' || coalesce(p.collector_number, ''))
            FROM prints p
            JOIN cards c ON c.id = p.card_id
            JOIN sets s ON s.id = p.set_id
            """
        )
        op.execute(
            """
            CREATE VIEW print_search_projection AS
            SELECT p.id AS print_id,
                   s.code AS set_code,
                   p.collector_number,
                   (
                     SELECT pi.url
                     FROM print_images pi
                     WHERE pi.print_id = p.id AND pi.is_primary IS TRUE
                     ORDER BY pi.id ASC
                     LIMIT 1
                   ) AS primary_image_url
            FROM prints p
            JOIN sets s ON s.id = p.set_id
            """
        )


def downgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        op.execute("DROP VIEW IF EXISTS print_search_projection")
        op.execute("DROP VIEW IF EXISTS search_documents")
    op.drop_index("ix_source_records_checksum", table_name="source_records")
    op.drop_index("ix_source_records_source_id", table_name="source_records")
    op.drop_table("source_records")
    op.drop_index("ix_sources_name", table_name="sources")
    op.drop_table("sources")
