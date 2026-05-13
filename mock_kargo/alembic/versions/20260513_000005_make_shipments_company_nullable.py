"""make shipments company nullable

Revision ID: 20260513_000005
Revises: 20260510_000004
Create Date: 2026-05-13 00:00:05
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "20260513_000005"
down_revision: Union[str, None] = "20260510_000004"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    existing_columns = {column["name"] for column in inspector.get_columns("shipments")}

    if "company_id" in existing_columns:
        with op.batch_alter_table("shipments") as batch_op:
            batch_op.alter_column("company_id", existing_type=sa.Integer(), nullable=True)


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    existing_columns = {column["name"] for column in inspector.get_columns("shipments")}

    if "company_id" in existing_columns:
        with op.batch_alter_table("shipments") as batch_op:
            batch_op.alter_column("company_id", existing_type=sa.Integer(), nullable=False)
