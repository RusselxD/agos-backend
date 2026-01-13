
from fastapi import HTTPException
from app.api.v1.dependencies import CurrentUser
from app.schemas import SystemSettingsUpdate
from sqlalchemy.ext.asyncio import AsyncSession
from app.crud.system_settings import system_settings as system_settings_crud
from app.crud.admin_audit_log import admin_audit_log as admin_audit_log_crud
from app.schemas import AdminAuditLogCreate

class SystemSettingsService:

    async def update_setting(self, db: AsyncSession, key: str, value: SystemSettingsUpdate, current_user: CurrentUser) -> any:
        
        settings = await system_settings_crud.get(db=db, key=key)

        if not settings:
            raise HTTPException(status_code=404, detail="System settings not found")
    
        # Store old value for audit log
        old_value = settings.json_value
        
        updated_settings = await system_settings_crud.update(db=db, db_obj=settings, obj_in=value)

        # Log the update action with descriptive message
        audit_message = self._format_audit_message(key, old_value, updated_settings.json_value)
        await admin_audit_log_crud.create_only(db=db, obj_in=AdminAuditLogCreate(
            admin_user_id=current_user.id,
            action=audit_message
        ))

        return updated_settings.json_value
    
    # Generate descriptive audit log message based on setting key
    def _format_audit_message(self, key: str, old_value: any, new_value: any) -> str:
        
        if key == "data_retention_days":
            return f"Changed data retention period from {old_value} to {new_value} days"
        
        elif key == "sensor_config":
            changes = []
            if old_value.get("installation_height") != new_value.get("installation_height"):
                changes.append(f"installation height from {old_value.get('installation_height')}cm to {new_value.get('installation_height')}cm")
            if old_value.get("warning_threshold") != new_value.get("warning_threshold"):
                changes.append(f"warning threshold from {old_value.get('warning_threshold')}cm to {new_value.get('warning_threshold')}cm")
            if old_value.get("critical_threshold") != new_value.get("critical_threshold"):
                changes.append(f"critical threshold from {old_value.get('critical_threshold')}cm to {new_value.get('critical_threshold')}cm")
            return f"Updated sensor config: {', '.join(changes)}" if changes else f"Updated sensor config (no changes)"
        
        elif key == "alert_thresholds":
            changes = []
            for tier_key in ["tier_1_max", "tier_2_min", "tier_2_max", "tier_3_min"]:
                if old_value.get(tier_key) != new_value.get(tier_key):
                    changes.append(f"{tier_key} from {old_value.get(tier_key)}% to {new_value.get(tier_key)}%")
            return f"Updated alert thresholds: {', '.join(changes)}" if changes else f"Updated alert thresholds (no changes)"
        
        # Fallback for unknown keys
        return f"Updated system setting '{key}' from {old_value} to {new_value}"

system_settings_service = SystemSettingsService()