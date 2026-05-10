"""make shipment_items unit_price nullable

Revision ID: 20260510_000004
Revises: 20260510_000003
Create Date: 2026-05-10 00:00:04
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "20260510_000004"
down_revision: Union[str, None] = "20260510_000003"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    existing_columns = {column["name"] for column in inspector.get_columns("shipment_items")}

    if "unit_price" in existing_columns:
        with op.batch_alter_table("shipment_items") as batch_op:
            batch_op.alter_column("unit_price", existing_type=sa.Numeric(10, 2), nullable=True)


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    existing_columns = {column["name"] for column in inspector.get_columns("shipment_items")}

    if "unit_price" in existing_columns:
        with op.batch_alter_table("shipment_items") as batch_op:
            batch_op.alter_column("unit_price", existing_type=sa.Numeric(10, 2), nullable=False)
