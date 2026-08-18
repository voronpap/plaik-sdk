"""Theme API v1 settings, presets, revisions and cache identity contracts.

These types are declarative. They do not execute templates or Python.
Published revision documents are immutable; a new change creates a new revision.
"""

from __future__ import annotations

import re
from datetime import datetime
from enum import IntEnum, StrEnum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from .packages import PACKAGE_ID_PATTERN, SEMVER_PATTERN, SETTING_KEY_PATTERN
from .theme_api import require_supported_theme_api
from .theme_composition import (
    COMPOSITION_ID_PATTERN,
    MAX_DECLARED_PAGE_TEMPLATES,
    PageTemplate,
    SettingFieldSchema,
    _check_setting_value,
    _require_setting_value,
    require_composition_id,
    validate_settings_against_schema,
)

CONFIGURATION_SCHEMA_VERSION = 1
SUPPORTED_CONFIGURATION_SCHEMA_VERSIONS = frozenset({CONFIGURATION_SCHEMA_VERSION})
REVISION_ID_PATTERN = r"^[a-z0-9]{16}$"
MAX_THEME_SETTINGS = 64
MAX_PRESETS = 32
MAX_RESPONSIVE_BREAKPOINTS = 2
CACHE_IDENTITY_FIELD_MAX = 128


class ConfigurationSchemaVersion(IntEnum):
    V1 = CONFIGURATION_SCHEMA_VERSION


class RevisionStatus(StrEnum):
    DRAFT = "draft"
    VALIDATED = "validated"
    PREPARED = "prepared"


class ResponsiveBreakpoint(StrEnum):
    NARROW = "narrow"
    WIDE = "wide"


def require_supported_configuration_schema(value: int) -> int:
    if value not in SUPPORTED_CONFIGURATION_SCHEMA_VERSIONS:
        raise ValueError("unsupported configuration schema version")
    return value


def require_revision_id(value: str) -> str:
    if not isinstance(value, str) or not re.fullmatch(REVISION_ID_PATTERN, value):
        raise ValueError("invalid revision id")
    return value


def require_breakpoint(value: str) -> str:
    try:
        return ResponsiveBreakpoint(value).value
    except ValueError as error:
        raise ValueError("invalid responsive breakpoint") from error


def _validate_setting_map(
    value: dict[str, Any], *, allow_empty: bool = True
) -> dict[str, str | int | bool]:
    if not isinstance(value, dict):
        raise ValueError("invalid setting values")
    if len(value) > MAX_THEME_SETTINGS:
        raise ValueError("too many settings")
    if not allow_empty and not value:
        raise ValueError("invalid setting values")
    validated: dict[str, str | int | bool] = {}
    for key, item in value.items():
        if not isinstance(key, str) or not re.fullmatch(SETTING_KEY_PATTERN, key):
            raise ValueError("invalid setting id")
        validated[key] = _require_setting_value(item)
    return validated


class ThemeSettingsSchema(BaseModel):
    """Declarative global theme settings schema. Editor chrome is optional."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: int
    settings: tuple[SettingFieldSchema, ...] = Field(
        default=(), max_length=MAX_THEME_SETTINGS
    )

    @field_validator("schema_version")
    @classmethod
    def validate_schema_version(cls, value: int) -> int:
        return require_supported_configuration_schema(value)

    @field_validator("settings")
    @classmethod
    def validate_unique_settings(
        cls, value: tuple[SettingFieldSchema, ...]
    ) -> tuple[SettingFieldSchema, ...]:
        ids = [field.id for field in value]
        if len(ids) != len(set(ids)):
            raise ValueError("duplicate setting id")
        return value


class ThemeSettingsValues(BaseModel):
    """Global setting values plus optional bounded responsive overlays."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    values: dict[str, str | int | bool] = Field(
        default_factory=dict, max_length=MAX_THEME_SETTINGS
    )
    responsive: dict[str, dict[str, str | int | bool]] = Field(
        default_factory=dict, max_length=MAX_RESPONSIVE_BREAKPOINTS
    )

    @field_validator("values")
    @classmethod
    def validate_values(
        cls, value: dict[str, str | int | bool]
    ) -> dict[str, str | int | bool]:
        return _validate_setting_map(value)

    @field_validator("responsive")
    @classmethod
    def validate_responsive(
        cls, value: dict[str, dict[str, str | int | bool]]
    ) -> dict[str, dict[str, str | int | bool]]:
        if len(value) != len(set(value)):
            raise ValueError("duplicate responsive breakpoint")
        validated: dict[str, dict[str, str | int | bool]] = {}
        for breakpoint, overlay in value.items():
            require_breakpoint(breakpoint)
            validated[breakpoint] = _validate_setting_map(overlay)
        return validated


class ThemePreset(BaseModel):
    """Validated configuration defaults for one theme codebase.

    Applying a preset creates or updates a revision. It does not mutate theme
    source files.
    """

    model_config = ConfigDict(extra="forbid", frozen=True)

    id: str = Field(pattern=COMPOSITION_ID_PATTERN, max_length=64)
    settings: dict[str, str | int | bool] = Field(
        default_factory=dict, max_length=MAX_THEME_SETTINGS
    )
    pages: dict[str, PageTemplate] = Field(
        default_factory=dict, max_length=MAX_DECLARED_PAGE_TEMPLATES
    )

    @field_validator("settings")
    @classmethod
    def validate_settings(
        cls, value: dict[str, str | int | bool]
    ) -> dict[str, str | int | bool]:
        return _validate_setting_map(value)

    @field_validator("pages")
    @classmethod
    def validate_page_ids(
        cls, value: dict[str, PageTemplate]
    ) -> dict[str, PageTemplate]:
        for page_type in value:
            require_composition_id(page_type, error="invalid page type")
        return value


class ThemeConfigurationRevision(BaseModel):
    """One immutable-after-prepare configuration revision."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    revision_id: str = Field(pattern=REVISION_ID_PATTERN)
    theme_id: str = Field(pattern=PACKAGE_ID_PATTERN)
    theme_version: str = Field(pattern=SEMVER_PATTERN)
    theme_api: int
    status: RevisionStatus
    settings: ThemeSettingsValues = Field(default_factory=ThemeSettingsValues)
    pages: dict[str, PageTemplate] = Field(
        default_factory=dict, max_length=MAX_DECLARED_PAGE_TEMPLATES
    )
    preset_id: str | None = Field(default=None, pattern=COMPOSITION_ID_PATTERN)
    created_at: datetime
    prepared_at: datetime | None = None

    @field_validator("theme_api")
    @classmethod
    def validate_theme_api(cls, value: int) -> int:
        return require_supported_theme_api(value)

    @field_validator("pages")
    @classmethod
    def validate_page_ids(
        cls, value: dict[str, PageTemplate]
    ) -> dict[str, PageTemplate]:
        for page_type in value:
            require_composition_id(page_type, error="invalid page type")
        return value

    @model_validator(mode="after")
    def prepared_requires_timestamp(self) -> ThemeConfigurationRevision:
        if self.status is RevisionStatus.PREPARED and self.prepared_at is None:
            raise ValueError("prepared revision requires prepared_at")
        if self.status is not RevisionStatus.PREPARED and self.prepared_at is not None:
            raise ValueError("prepared_at is only valid on prepared revisions")
        return self


class ThemeCacheIdentity(BaseModel):
    """Deterministic cache identity for Theme API composition output."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    store_id: str = Field(min_length=2, max_length=64, pattern=r"^[a-z0-9][a-z0-9-]{1,63}$")
    theme_id: str = Field(pattern=PACKAGE_ID_PATTERN)
    theme_version: str = Field(pattern=SEMVER_PATTERN)
    revision_id: str = Field(pattern=REVISION_ID_PATTERN)
    locale: str = Field(min_length=2, max_length=32)
    page_type: str = Field(pattern=COMPOSITION_ID_PATTERN)
    slots_generation: str = Field(min_length=1, max_length=CACHE_IDENTITY_FIELD_MAX)

    def key(self) -> str:
        return "|".join(
            (
                self.store_id,
                self.theme_id,
                self.theme_version,
                self.revision_id,
                self.locale,
                self.page_type,
                self.slots_generation,
            )
        )


def validate_theme_settings(
    values: ThemeSettingsValues | dict[str, Any],
    schema: ThemeSettingsSchema,
) -> ThemeSettingsValues:
    """Fail closed if global or responsive settings do not match the schema."""

    payload = (
        values
        if isinstance(values, ThemeSettingsValues)
        else ThemeSettingsValues.model_validate(values)
    )
    resolved = validate_settings_against_schema(payload.values, schema.settings)
    responsive: dict[str, dict[str, str | int | bool]] = {}
    fields = {field.id: field for field in schema.settings}
    for breakpoint, overlay in payload.responsive.items():
        require_breakpoint(breakpoint)
        unknown = sorted(set(overlay) - set(fields))
        if unknown:
            raise ValueError("unknown setting")
        responsive[breakpoint] = {
            key: _check_setting_value(item, fields[key]) for key, item in overlay.items()
        }
    return ThemeSettingsValues(values=resolved, responsive=responsive)
