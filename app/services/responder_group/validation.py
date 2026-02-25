"""Validation helpers for responder group operations."""

from fastapi import HTTPException, status

from app.models.responder_related.group import DEFAULT_ACTIVE_RESPONDERS_GROUP_NAME


def validate_group_name(name: str) -> str:
    """Normalize and validate group name. Raises HTTPException if invalid."""
    normalized = name.strip()
    if not normalized:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Group name cannot be empty.",
        )
    if normalized.casefold() == DEFAULT_ACTIVE_RESPONDERS_GROUP_NAME.casefold():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="This group name is reserved for the system default active-responders group.",
        )
    return normalized


def validate_not_default_group(group_name: str, action: str = "changed") -> None:
    """Raise if group is the system default (cannot be modified for certain actions)."""
    if group_name.casefold() == DEFAULT_ACTIVE_RESPONDERS_GROUP_NAME.casefold():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"The system default active-responders group cannot be {action}.",
        )
