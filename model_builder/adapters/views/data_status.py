"""Metadata-only presentation data for the Data & privacy UI."""

from dataclasses import dataclass
from typing import Tuple

from django.conf import settings
from django.contrib.sessions.backends.base import SessionBase
from django.http import HttpResponse
from django.template.loader import render_to_string

from model_builder.adapters.repositories.recovery_retention import (
    DEFAULT_RECOVERY_RETENTION_SECONDS,
    get_recovery_retention_seconds,
    recovery_retention_choices,
)
from model_builder.adapters.repositories.session_system_repository import SessionSystemRepository
from model_builder.adapters.repositories.workspace_index import WorkspaceIndex

MEBIBYTE = 1024 * 1024
LIVE_CLEANUP_LAG_SECONDS = 60 * 60
WORKSPACE_STORAGE_WARNING_NUMERATOR = 4
WORKSPACE_STORAGE_WARNING_DENOMINATOR = 5


@dataclass(frozen=True)
class RetentionChoice:
    seconds: int
    label: str


@dataclass(frozen=True)
class DataStatus:
    session_cookie_age_display: str
    hot_cache_retention_display: str
    recovery_retention_seconds: int
    recovery_retention_display: str
    recovery_retention_choices: Tuple[RetentionChoice, ...]
    live_cleanup_lag_display: str
    workspace_size_bytes: int
    workspace_size_display: str
    workspace_limit_bytes: int
    workspace_limit_display: str
    show_workspace_storage_warning: bool
    operator_name: str
    hosting_provider_name: str
    hosting_region: str
    security_contact: str
    https_enabled: bool | None
    postgres_encrypted_at_rest: bool | None
    postgres_backups_enabled: bool | None
    postgres_backup_frequency: str
    postgres_backup_retention_days: int
    postgres_backups_encrypted_at_rest: bool | None
    postgres_backup_window: str
    public_shared_instance: bool


def format_duration(seconds: int) -> str:
    if seconds % (24 * 60 * 60) == 0:
        days = seconds // (24 * 60 * 60)
        return f"{days} day" if days == 1 else f"{days} days"
    hours = seconds // (60 * 60)
    return f"{hours} hour" if hours == 1 else f"{hours} hours"


def format_byte_size(size_bytes: int) -> str:
    if size_bytes < 1024:
        return f"{size_bytes} B"
    if size_bytes < MEBIBYTE:
        return f"{_format_display_number(size_bytes / 1024)} KB"
    return f"{_format_display_number(size_bytes / MEBIBYTE)} MB"


def _format_display_number(value: float) -> str:
    if value >= 100:
        formatted = f"{value:,.0f}"
    elif value >= 10:
        formatted = f"{value:,.1f}"
    else:
        formatted = f"{value:,.2f}"
    return formatted.rstrip("0").rstrip(".") if "." in formatted else formatted


def build_data_status(session: SessionBase) -> DataStatus:
    """Build disclosure data from settings and integer workspace metadata only."""
    selected_retention = get_recovery_retention_seconds(session)
    choices = tuple(
        RetentionChoice(
            seconds=seconds,
            label=(
                f"{format_duration(seconds)} (default)"
                if seconds == DEFAULT_RECOVERY_RETENTION_SECONDS
                else format_duration(seconds)
            ),
        )
        for seconds in recovery_retention_choices()
    )
    workspace_size_bytes = WorkspaceIndex(session).workspace_size_bytes()
    workspace_limit_bytes = round(SessionSystemRepository.MAX_PAYLOAD_SIZE_MB * MEBIBYTE)
    show_workspace_storage_warning = (
        workspace_limit_bytes > 0
        and workspace_size_bytes * WORKSPACE_STORAGE_WARNING_DENOMINATOR
        >= workspace_limit_bytes * WORKSPACE_STORAGE_WARNING_NUMERATOR
    )

    return DataStatus(
        session_cookie_age_display=format_duration(settings.SESSION_COOKIE_AGE),
        hot_cache_retention_display=format_duration(SessionSystemRepository.REDIS_CACHE_TIMEOUT_SECONDS),
        recovery_retention_seconds=selected_retention,
        recovery_retention_display=format_duration(selected_retention),
        recovery_retention_choices=choices,
        live_cleanup_lag_display=format_duration(LIVE_CLEANUP_LAG_SECONDS),
        workspace_size_bytes=workspace_size_bytes,
        workspace_size_display=format_byte_size(workspace_size_bytes),
        workspace_limit_bytes=workspace_limit_bytes,
        workspace_limit_display=format_byte_size(workspace_limit_bytes),
        show_workspace_storage_warning=show_workspace_storage_warning,
        operator_name=settings.DATA_PRIVACY_OPERATOR_NAME,
        hosting_provider_name=settings.DATA_PRIVACY_HOSTING_PROVIDER_NAME,
        hosting_region=settings.DATA_PRIVACY_HOSTING_REGION,
        security_contact=settings.DATA_PRIVACY_SECURITY_CONTACT,
        https_enabled=settings.DATA_PRIVACY_HTTPS_ENABLED,
        postgres_encrypted_at_rest=settings.DATA_PRIVACY_POSTGRES_ENCRYPTED_AT_REST,
        postgres_backups_enabled=settings.DATA_PRIVACY_POSTGRES_BACKUPS_ENABLED,
        postgres_backup_frequency=settings.DATA_PRIVACY_POSTGRES_BACKUP_FREQUENCY,
        postgres_backup_retention_days=settings.DATA_PRIVACY_POSTGRES_BACKUP_RETENTION_DAYS,
        postgres_backups_encrypted_at_rest=settings.DATA_PRIVACY_POSTGRES_BACKUPS_ENCRYPTED_AT_REST,
        postgres_backup_window=settings.DATA_PRIVACY_POSTGRES_BACKUP_WINDOW,
        public_shared_instance=bool(settings.DATA_PRIVACY_PUBLIC_SHARED_INSTANCE),
    )


def render_workspace_storage_status(session: SessionBase, *, oob: bool = False) -> str:
    """Render the stable warning region from workspace size metadata only."""
    return render_to_string(
        "model_builder/components/workspace_storage_status.html",
        {"data_status": build_data_status(session), "oob": oob},
    )


def append_workspace_storage_status(response: HttpResponse, session: SessionBase) -> HttpResponse:
    """Append one OOB status update while keeping its live-region container stable."""
    response.content += render_workspace_storage_status(session, oob=True).encode("utf-8")
    return response
