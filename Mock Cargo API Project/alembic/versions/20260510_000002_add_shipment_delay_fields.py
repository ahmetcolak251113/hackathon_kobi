"""add shipment delay fields

Revision ID: 20260510_000002
Revises: 20260510_000001
Create Date: 2026-05-10 00:00:02
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "20260510_000002"
down_revision: Union[str, None] = "20260510_000001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    existing_columns = {column["name"] for column in inspector.get_columns("shipments")}

    if "is_delayed" not in existing_columns:
        op.add_column("shipments", sa.Column("is_delayed", sa.Boolean(), nullable=False, server_default=sa.false()))
        op.alter_column("shipments", "is_delayed", server_default=None)

    if "delay_reason" not in existing_columns:
        op.add_column("shipments", sa.Column("delay_reason", sa.String(length=255), nullable=True))

    if "delay_seconds" not in existing_columns:
        op.add_column("shipments", sa.Column("delay_seconds", sa.Integer(), nullable=True))


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    existing_columns = {column["name"] for column in inspector.get_columns("shipments")}

    if "delay_seconds" in existing_columns:
        op.drop_column("shipments", "delay_seconds")
    if "delay_reason" in existing_columns:
        op.drop_column("shipments", "delay_reason")
    if "is_delayed" in existing_columns:
        op.drop_column("shipments", "is_delayed")
