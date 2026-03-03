"""add_sealed_products_tables

Revision ID: 20260303_08
Revises: 20260303_07
Create Date: 2026-03-03 01:00:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = "20260303_08"
down_revision: Union[str, None] = "20260303_07"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "products",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("game_id", sa.Integer(), nullable=False),
        sa.Column("set_id", sa.Integer(), nullable=True),
        sa.Column("product_type", sa.String(length=100), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("release_date", sa.Date(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["game_id"], ["games.id"]),
        sa.ForeignKeyConstraint(["set_id"], ["sets.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_products_game_id"), "products", ["game_id"], unique=False)
    op.create_index(op.f("ix_products_name"), "products", ["name"], unique=False)
    op.create_index(op.f("ix_products_product_type"), "products", ["product_type"], unique=False)
    op.create_index(op.f("ix_products_set_id"), "products", ["set_id"], unique=False)

    op.create_table(
        "product_variants",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("product_id", sa.Integer(), nullable=False),
        sa.Column("language", sa.String(length=16), nullable=False),
        sa.Column("region", sa.String(length=16), nullable=False),
        sa.Column("packaging", sa.String(length=100), nullable=True),
        sa.Column("sku", sa.String(length=100), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["product_id"], ["products.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("product_id", "language", "region", "packaging", name="uq_product_variant_identity"),
    )
    op.create_index(op.f("ix_product_variants_language"), "product_variants", ["language"], unique=False)
    op.create_index(op.f("ix_product_variants_product_id"), "product_variants", ["product_id"], unique=False)
    op.create_index(op.f("ix_product_variants_region"), "product_variants", ["region"], unique=False)

    op.create_table(
        "product_images",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("product_variant_id", sa.Integer(), nullable=False),
        sa.Column("url", sa.Text(), nullable=False),
        sa.Column("is_primary", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("source", sa.String(length=100), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["product_variant_id"], ["product_variants.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_product_images_product_variant_id"), "product_images", ["product_variant_id"], unique=False)

    op.create_table(
        "product_identifiers",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("product_variant_id", sa.Integer(), nullable=False),
        sa.Column("source", sa.String(length=100), nullable=False),
        sa.Column("external_id", sa.String(length=255), nullable=False),
        sa.ForeignKeyConstraint(["product_variant_id"], ["product_variants.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("source", "external_id", name="uq_product_identifier_source_external"),
    )
    op.create_index(op.f("ix_product_identifiers_external_id"), "product_identifiers", ["external_id"], unique=False)
    op.create_index(op.f("ix_product_identifiers_product_variant_id"), "product_identifiers", ["product_variant_id"], unique=False)
    op.create_index(op.f("ix_product_identifiers_source"), "product_identifiers", ["source"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_product_identifiers_source"), table_name="product_identifiers")
    op.drop_index(op.f("ix_product_identifiers_product_variant_id"), table_name="product_identifiers")
    op.drop_index(op.f("ix_product_identifiers_external_id"), table_name="product_identifiers")
    op.drop_table("product_identifiers")

    op.drop_index(op.f("ix_product_images_product_variant_id"), table_name="product_images")
    op.drop_table("product_images")

    op.drop_index(op.f("ix_product_variants_region"), table_name="product_variants")
    op.drop_index(op.f("ix_product_variants_product_id"), table_name="product_variants")
    op.drop_index(op.f("ix_product_variants_language"), table_name="product_variants")
    op.drop_table("product_variants")

    op.drop_index(op.f("ix_products_set_id"), table_name="products")
    op.drop_index(op.f("ix_products_product_type"), table_name="products")
    op.drop_index(op.f("ix_products_name"), table_name="products")
    op.drop_index(op.f("ix_products_game_id"), table_name="products")
    op.drop_table("products")
