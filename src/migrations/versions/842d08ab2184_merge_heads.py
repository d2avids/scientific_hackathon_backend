"""Merge heads

Revision ID: 842d08ab2184
Revises: 13272bcd3daa, 4755a7a3bcfc
Create Date: 2025-04-12 14:15:32.914710

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '842d08ab2184'
down_revision: Union[str, None] = ('13272bcd3daa', '4755a7a3bcfc')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
