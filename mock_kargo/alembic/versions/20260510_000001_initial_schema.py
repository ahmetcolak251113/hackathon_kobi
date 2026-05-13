"""initial schema

Revision ID: 20260510_000001
Revises:
Create Date: 2026-05-10 00:00:01
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "20260510_000001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "companies",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column("api_key", sa.String(length=64), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_companies_api_key"), "companies", ["api_key"], unique=True)
    op.create_index(op.f("ix_companies_email"), "companies", ["email"], unique=True)
    op.create_index(op.f("ix_companies_id"), "companies", ["id"], unique=False)

    op.create_table(
        "products",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("sku", sa.String(length=64), nullable=False),
        sa.Column("stock_quantity", sa.Integer(), nullable=False),
        sa.Column("unit_price", sa.Numeric(precision=10, scale=2), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_products_id"), "products", ["id"], unique=False)
    op.create_index(op.f("ix_products_sku"), "products", ["sku"], unique=True)

    op.create_table(
        "shipments",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("company_id", sa.Integer(), nullable=False),
        sa.Column("customer_name", sa.String(length=255), nullable=False),
        sa.Column("customer_phone", sa.String(length=64), nullable=False),
        sa.Column("delivery_address", sa.Text(), nullable=False),
        sa.Column("tracking_code", sa.String(length=32), nullable=False),
        sa.Column("current_status", sa.String(length=64), nullable=False),
        sa.Column("estimated_delivery", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["company_id"], ["companies.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_shipments_company_id"), "shipments", ["company_id"], unique=False)
    op.create_index(op.f("ix_shipments_current_status"), "shipments", ["current_status"], unique=False)
    op.create_index(op.f("ix_shipments_id"), "shipments", ["id"], unique=False)
    op.create_index(op.f("ix_shipments_tracking_code"), "shipments", ["tracking_code"], unique=True)

    op.create_table(
        "shipment_items",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("shipment_id", sa.Integer(), nullable=False),
        sa.Column("product_id", sa.Integer(), nullable=False),
        sa.Column("quantity", sa.Integer(), nullable=False),
        sa.Column("unit_price", sa.Numeric(precision=10, scale=2), nullable=False),
        sa.ForeignKeyConstraint(["product_id"], ["products.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["shipment_id"], ["shipments.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("shipment_id", "product_id", name="uq_shipment_product"),
    )
    op.create_index(op.f("ix_shipment_items_id"), "shipment_items", ["id"], unique=False)
    op.create_index(op.f("ix_shipment_items_product_id"), "shipment_items", ["product_id"], unique=False)
    op.create_index(op.f("ix_shipment_items_shipment_id"), "shipment_items", ["shipment_id"], unique=False)

    op.create_table(
        "shipment_status_history",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("shipment_id", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(length=64), nullable=False),
        sa.Column("description", sa.String(length=255), nullable=False),
        sa.Column("location", sa.String(length=255), nullable=False),
        sa.Column("visible_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["shipment_id"], ["shipments.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_shipment_status_history_id"), "shipment_status_history", ["id"], unique=False)
    op.create_index(
        op.f("ix_shipment_status_history_shipment_id"),
        "shipment_status_history",
        ["shipment_id"],
        unique=False,
    )
    op.create_index(op.f("ix_shipment_status_history_status"), "shipment_status_history", ["status"], unique=False)
    op.create_index(
        op.f("ix_shipment_status_history_visible_at"),
        "shipment_status_history",
        ["visible_at"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_shipment_status_history_visible_at"), table_name="shipment_status_history")
    op.drop_index(op.f("ix_shipment_status_history_status"), table_name="shipment_status_history")
    op.drop_index(op.f("ix_shipment_status_history_shipment_id"), table_name="shipment_status_history")
    op.drop_index(op.f("ix_shipment_status_history_id"), table_name="shipment_status_history")
    op.drop_table("shipment_status_history")

    op.drop_index(op.f("ix_shipment_items_shipment_id"), table_name="shipment_items")
    op.drop_index(op.f("ix_shipment_items_product_id"), table_name="shipment_items")
    op.drop_index(op.f("ix_shipment_items_id"), table_name="shipment_items")
    op.drop_table("shipment_items")

    op.drop_index(op.f("ix_shipments_tracking_code"), table_name="shipments")
    op.drop_index(op.f("ix_shipments_id"), table_name="shipments")
    op.drop_index(op.f("ix_shipments_current_status"), table_name="shipments")
    op.drop_index(op.f("ix_shipments_company_id"), table_name="shipments")
    op.drop_table("shipments")

    op.drop_index(op.f("ix_products_sku"), table_name="products")
    op.drop_index(op.f("ix_products_id"), table_name="products")
    op.drop_table("products")

    op.drop_index(op.f("ix_companies_id"), table_name="companies")
    op.drop_index(op.f("ix_companies_email"), table_name="companies")
    op.drop_index(op.f("ix_companies_api_key"), table_name="companies")
    op.drop_table("companies")
