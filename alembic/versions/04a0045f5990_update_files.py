"""update files

Revision ID: 04a0045f5990
Revises: d8826007fd2b
Create Date: 2025-02-13 15:04:11.449459

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy import table, column


# revision identifiers, used by Alembic.
revision: str = "04a0045f5990"
down_revision: Union[str, None] = "d8826007fd2b"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Создаем временную таблицу для операций
    schedule_files = table(
        "schedule_files", column("id", sa.Integer), column("group_count", sa.Integer)
    )

    op.execute(schedule_files.delete())

    op.add_column(
        "schedule_files", sa.Column("group_count", sa.Integer(), nullable=True)
    )


def downgrade() -> None:
    op.drop_column("schedule_files", "group_count")
