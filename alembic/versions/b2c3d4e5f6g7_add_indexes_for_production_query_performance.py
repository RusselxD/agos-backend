"""Add indexes for production query performance

Revision ID: b2c3d4e5f6g7
Revises: a1b2c3d4e5f6
Create Date: 2026-04-02

"""
from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = 'b2c3d4e5f6g7'
down_revision: Union[str, None] = 'a1b2c3d4e5f6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Escalation query: filters on status + sent_at + escalation_count with JOIN on dispatch.type
    op.create_index('ix_notification_deliveries_status_sent_at', 'notification_deliveries', ['status', 'sent_at'])
    op.create_index('ix_notification_deliveries_responder_id', 'notification_deliveries', ['responder_id'])

    # Notification dispatches type filter
    op.create_index('ix_notification_dispatches_type', 'notification_dispatches', ['type'])

    # Sensor readings: frequently filtered by device + timestamp
    op.create_index('ix_sensor_readings_device_timestamp', 'sensor_readings', ['sensor_device_id', 'timestamp'])

    # Model readings: filtered by camera device
    op.create_index('ix_model_readings_camera_device_id', 'model_readings', ['camera_device_id'])


def downgrade() -> None:
    op.drop_index('ix_model_readings_camera_device_id', 'model_readings')
    op.drop_index('ix_sensor_readings_device_timestamp', 'sensor_readings')
    op.drop_index('ix_notification_dispatches_type', 'notification_dispatches')
    op.drop_index('ix_notification_deliveries_responder_id', 'notification_deliveries')
    op.drop_index('ix_notification_deliveries_status_sent_at', 'notification_deliveries')
