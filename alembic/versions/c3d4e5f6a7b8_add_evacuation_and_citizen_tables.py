"""Add evacuation_centers, citizen_subscriptions, evacuation_events (F4/F5)

Revision ID: c3d4e5f6a7b8
Revises: b2c3d4e5f6g7
Create Date: 2026-08-11

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = 'c3d4e5f6a7b8'
down_revision: Union[str, None] = 'b2c3d4e5f6g7'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


UTC_NOW = sa.text("timezone('UTC', now())")


def upgrade() -> None:
    center_status = postgresql.ENUM(
        'open', 'full', 'closed', name='evacuationcenterstatus'
    )
    event_kind = postgresql.ENUM(
        'evacuate', 'all_clear', name='evacuationeventkind'
    )

    # --- F5: evacuation_centers ---
    op.create_table(
        'evacuation_centers',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('location_id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=120), nullable=False),
        sa.Column('latitude', sa.Float(), nullable=False),
        sa.Column('longitude', sa.Float(), nullable=False),
        sa.Column('capacity', sa.Integer(), nullable=True),
        sa.Column('contact', sa.String(), nullable=True),
        sa.Column('status', center_status, nullable=False, server_default='open'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=UTC_NOW, nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=UTC_NOW, nullable=False),
        sa.ForeignKeyConstraint(['location_id'], ['locations.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_evacuation_centers_id', 'evacuation_centers', ['id'])
    op.create_index('ix_evacuation_centers_location_id', 'evacuation_centers', ['location_id'])

    # --- F4: citizen_subscriptions ---
    op.create_table(
        'citizen_subscriptions',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('location_id', sa.Integer(), nullable=False),
        sa.Column('endpoint', sa.Text(), nullable=False),
        sa.Column('p256dh', sa.Text(), nullable=False),
        sa.Column('auth', sa.Text(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=UTC_NOW, nullable=False),
        sa.ForeignKeyConstraint(['location_id'], ['locations.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('location_id', 'endpoint', name='uq_citizen_subscription_location_endpoint'),
    )
    op.create_index('ix_citizen_subscriptions_location_id', 'citizen_subscriptions', ['location_id'])

    # --- F4: evacuation_events (audit) ---
    op.create_table(
        'evacuation_events',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('location_id', sa.Integer(), nullable=False),
        sa.Column('dispatch_id', sa.Integer(), nullable=True),
        sa.Column('kind', event_kind, nullable=False),
        sa.Column('authorized_by', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('basis_risk_score', sa.Integer(), nullable=True),
        sa.Column('basis_snapshot', postgresql.JSONB(), nullable=True),
        sa.Column('message', sa.String(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=UTC_NOW, nullable=False),
        sa.ForeignKeyConstraint(['location_id'], ['locations.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['dispatch_id'], ['notification_dispatches.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['authorized_by'], ['admin_users.id']),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_evacuation_events_location_id', 'evacuation_events', ['location_id'])


def downgrade() -> None:
    op.drop_index('ix_evacuation_events_location_id', table_name='evacuation_events')
    op.drop_table('evacuation_events')

    op.drop_index('ix_citizen_subscriptions_location_id', table_name='citizen_subscriptions')
    op.drop_table('citizen_subscriptions')

    op.drop_index('ix_evacuation_centers_location_id', table_name='evacuation_centers')
    op.drop_index('ix_evacuation_centers_id', table_name='evacuation_centers')
    op.drop_table('evacuation_centers')

    op.execute('DROP TYPE IF EXISTS evacuationeventkind')
    op.execute('DROP TYPE IF EXISTS evacuationcenterstatus')
