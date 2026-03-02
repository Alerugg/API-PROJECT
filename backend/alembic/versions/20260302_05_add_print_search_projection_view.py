"""add_print_search_projection_view

Revision ID: 20260302_05
Revises: 20260302_04
Create Date: 2026-03-02 03:00:00.000000

"""

from typing import Sequence, Union

from alembic import op


revision: str = "20260302_05"
down_revision: Union[str, None] = "20260302_04"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(
        """
        CREATE VIEW print_search_projection AS
        SELECT
            p.id AS print_id,
            s.code AS set_code,
            p.collector_number,
            (
                SELECT pi.url
                FROM print_images pi
                WHERE pi.print_id = p.id AND pi.is_primary = true
                ORDER BY pi.id ASC
                LIMIT 1
            ) AS primary_image_url
        FROM prints p
        JOIN sets s ON s.id = p.set_id
        """
    )


def downgrade() -> None:
    op.execute("DROP VIEW IF EXISTS print_search_projection")
