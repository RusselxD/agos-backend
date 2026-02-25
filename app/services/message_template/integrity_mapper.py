"""Map IntegrityError to user-friendly HTTPException for message templates."""

from fastapi import HTTPException, status
from sqlalchemy.exc import IntegrityError


def map_message_template_integrity_error(exc: IntegrityError) -> HTTPException | None:
    """Map database integrity errors to HTTP 400 with meaningful detail."""
    error_text = str(exc.orig).lower()
    constraint_name = (
        getattr(getattr(exc.orig, "diag", None), "constraint_name", None)
        or getattr(exc.orig, "constraint_name", None)
        or ""
    ).lower()

    if (
        constraint_name == "message_templates_template_name_key"
        or constraint_name == "uq_message_templates_template_name"
        or "template_name" in error_text
    ):
        return HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Template name already exists.",
        )

    if constraint_name == "uq_message_templates_auto_send_warning_true":
        return HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only one template can have auto_send_on_warning enabled.",
        )

    if constraint_name == "uq_message_templates_auto_send_critical_true":
        return HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only one template can have auto_send_on_critical enabled.",
        )

    if constraint_name == "uq_message_templates_auto_send_blocked_true":
        return HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only one template can have auto_send_on_blocked enabled.",
        )

    # Fallback when constraint name is not exposed
    if (
        "auto_send_on_warning" in error_text
        or "auto_send_warning" in error_text
        or "warning_true" in error_text
    ):
        return HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only one template can have auto_send_on_warning enabled.",
        )

    if (
        "auto_send_on_critical" in error_text
        or "auto_send_critical" in error_text
        or "critical_true" in error_text
    ):
        return HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only one template can have auto_send_on_critical enabled.",
        )

    if (
        "auto_send_on_blocked" in error_text
        or "auto_send_blocked" in error_text
        or "blocked_true" in error_text
    ):
        return HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only one template can have auto_send_on_blocked enabled.",
        )

    return None
