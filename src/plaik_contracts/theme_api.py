"""Theme API v1 public presentation contracts.

These types are the supported Theme API v1 path. Existing camelCase web hooks
remain a compatibility path and are not silently rewritten as dotted slots.
"""

from enum import IntEnum, StrEnum
from pathlib import PurePosixPath, PureWindowsPath

from pydantic import BaseModel, ConfigDict, Field, field_validator

THEME_API_V1 = 1
SUPPORTED_THEME_API_VERSIONS = frozenset({THEME_API_V1})
SLOT_ID_PATTERN = r"^[a-z][a-z0-9-]*(?:\.[a-z][a-z0-9-]*){1,7}$"
SLOT_ID_MAX_LENGTH = 128


class ThemeApiVersion(IntEnum):
    V1 = THEME_API_V1


class UiState(StrEnum):
    """Domain-neutral presentation states. Packages own business meaning."""

    IDLE = "idle"
    PENDING = "pending"
    LOADING = "loading"
    EMPTY = "empty"
    SUCCESS = "success"
    VALIDATION_ERROR = "validation-error"
    SERVICE_ERROR = "service-error"
    NETWORK_ERROR = "network-error"
    UNAVAILABLE = "unavailable"
    OUT_OF_STOCK = "out-of-stock"
    DISABLED_WITH_REASON = "disabled-with-reason"
    PARTIAL_AVAILABILITY = "partial-availability"


class ThemeCompatibility(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    theme_api: int
    plaik: str = Field(min_length=1, max_length=64)

    @field_validator("theme_api")
    @classmethod
    def validate_theme_api(cls, value: int) -> int:
        return require_supported_theme_api(value)


class SlotDefinition(BaseModel):
    """A theme-declared UI slot. The id is a public presentation contract."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    id: str = Field(pattern=SLOT_ID_PATTERN, max_length=SLOT_ID_MAX_LENGTH)
    states: tuple[UiState, ...] = ()

    @field_validator("id")
    @classmethod
    def reject_reserved_slot(cls, value: str) -> str:
        return require_public_slot_id(value)

    @field_validator("states")
    @classmethod
    def validate_unique_states(cls, value: tuple[UiState, ...]) -> tuple[UiState, ...]:
        if len(value) != len(set(value)):
            raise ValueError("duplicate slot UI state")
        return value


class SlotContribution(BaseModel):
    """A module/integration contribution to one declared Theme API v1 slot."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    slot: str = Field(pattern=SLOT_ID_PATTERN, max_length=SLOT_ID_MAX_LENGTH)
    template: str = Field(min_length=1, max_length=255)
    position: int = Field(default=100, ge=-10_000, le=10_000)

    @field_validator("slot")
    @classmethod
    def reject_reserved_slot(cls, value: str) -> str:
        return require_public_slot_id(value)

    @field_validator("template")
    @classmethod
    def validate_template_path(cls, value: str) -> str:
        return _validate_web_template_path(value)


def _validate_web_template_path(value: str) -> str:
    """Relative template path for package ``web/`` and theme composition.

    Module and integration ``web.slots`` / ``web.hooks`` resolve under
    ``{package}/web/{template}``. Theme section and block templates are
    relative to the theme ``templates/`` root (for example
    ``sections/hero.html``), not a leading ``templates/`` component. A first
    path part of ``templates`` is rejected because package install staging
    would look for ``web/templates/...``. Theme layout files use ThemeManifest
    layout ids and do not go through this helper.
    """
    posix = PurePosixPath(value)
    windows = PureWindowsPath(value)
    if (
        posix.is_absolute()
        or windows.is_absolute()
        or bool(windows.drive)
        or not posix.parts
        or any(part in {"", ".", ".."} for part in posix.parts)
        or posix.as_posix() != value
        or "\\" in value
        or ":" in value
        or "\x00" in value
        or not value.endswith(".html")
        or posix.parts[0] == "templates"
    ):
        raise ValueError("invalid web template path")
    return value


class WebSlotDeclaration(SlotContribution):
    """Durable package-manifest form of a Theme API v1 slot contribution."""


def require_supported_theme_api(value: int) -> int:
    if value not in SUPPORTED_THEME_API_VERSIONS:
        raise ValueError("unsupported Theme API version")
    return value


def require_public_slot_id(value: str) -> str:
    if not isinstance(value, str) or not value:
        raise ValueError("invalid slot id")
    if value == "core" or value.startswith("core."):
        raise ValueError("core.* slots are reserved for Platform Core")
    return value


def slot_ids_are_unique(values: list[str] | tuple[str, ...]) -> None:
    if len(values) != len(set(values)):
        raise ValueError("duplicate slot id")
