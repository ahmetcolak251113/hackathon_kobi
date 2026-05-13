"""make shipment_items product nullable and add custom_product_name

Revision ID: 20260510_000003
Revises: 20260510_000002
Create Date: 2026-05-10 00:00:03
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "20260510_000003"
down_revision: Union[str, None] = "20260510_000002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    existing_columns = {column["name"] for column in inspector.get_columns("shipment_items")}

    # SQLite requires using batch_alter_table for some alterations
    with op.batch_alter_table("shipment_items") as batch_op:
        if "product_id" in existing_columns:
            batch_op.alter_column("product_id", existing_type=sa.Integer(), nullable=True)
        if "custom_product_name" not in existing_columns:
            batch_op.add_column(sa.Column("custom_product_name", sa.String(length=255), nullable=True))


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    existing_columns = {column["name"] for column in inspector.get_columns("shipment_items")}

    with op.batch_alter_table("shipment_items") as batch_op:
        if "custom_product_name" in existing_columns:
            batch_op.drop_column("custom_product_name")
        if "product_id" in existing_columns:
            batch_op.alter_column("product_id", existing_type=sa.Integer(), nullable=False)
