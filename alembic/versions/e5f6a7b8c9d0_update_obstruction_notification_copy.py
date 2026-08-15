"""Update the default surface-obstruction notification copy.

Revision ID: e5f6a7b8c9d0
Revises: d4e5f6a7b8c9
Create Date: 2026-08-15

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "e5f6a7b8c9d0"
down_revision: Union[str, None] = "d4e5f6a7b8c9"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Exact-match the seeded default so administrator-authored copy is preserved.
    op.execute(
        sa.text(
            """
            UPDATE notification_templates
            SET title = 'Surface Obstruction Alert',
                message = 'A potential surface obstruction has been detected.'
            WHERE type = 'BLOCKAGE'
              AND title = 'Blockage Alert'
              AND message = 'A blockage has been detected.'
            """
        )
    )


def downgrade() -> None:
    op.execute(
        sa.text(
            """
            UPDATE notification_templates
            SET title = 'Blockage Alert',
                message = 'A blockage has been detected.'
            WHERE type = 'BLOCKAGE'
              AND title = 'Surface Obstruction Alert'
              AND message = 'A potential surface obstruction has been detected.'
            """
        )
    )
