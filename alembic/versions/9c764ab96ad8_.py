"""empty message

Revision ID: 9c764ab96ad8
Revises: 4e9049e19c22, e8784ea75fc2
Create Date: 2024-12-10 15:59:28.481239

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '9c764ab96ad8'
down_revision: Union[str, None] = ('4e9049e19c22', 'e8784ea75fc2')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
