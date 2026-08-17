"""Domain-neutral kernel refs for Core 0.3 public contracts.

These types are shared by Core, SDK and packages. They must not import
``plaik_core`` and must not encode commerce meaning.
"""

from __future__ import annotations

from collections.abc import Mapping
from datetime import datetime
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from .packages import (
    CONTRACT_NAME_PATTERN,
    PACKAGE_ID_PATTERN,
    PERMISSION_ID_PATTERN,
    STABLE_SEMVER_PATTERN,
)


_SCOPE_ID_PATTERN = r"^[a-z0-9][a-z0-9._-]{0,63}$"
_POINTER_PROVIDER = r"^[a-z][a-z0-9_-]{0,31}$"
_POINTER_KEY = r"^[A-Za-z0-9][A-Za-z0-9_./:-]{0,254}$"
_KIND_PATTERN = r"^[a-z][a-z0-9_.-]{0,63}$"
_RESOURCE_ID_PATTERN = r"^[A-Za-z0-9][A-Za-z0-9._:-]{0,127}$"
_ISSUE_CODE = r"^[a-z][a-z0-9_.-]{1,127}$"
_CORRELATION_ID = r"^[A-Za-z0-9][A-Za-z0-9._:-]{7,127}$"
_JOB_TYPE = r"^[a-z][a-z0-9_.-]{1,127}$"


class ScopeLevel(StrEnum):
    INSTALLATION = "installation"
    GROUP = "group"
    STORE = "store"


class ScopeRef(BaseModel):
    """Immutable installation → group → store point. Same shape as Core StoreContext."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    installation_id: str = Field(
        default="default",
        min_length=1,
        max_length=64,
        pattern=_SCOPE_ID_PATTERN,
    )
    group_id: str | None = Field(
        default=None,
        min_length=1,
        max_length=64,
        pattern=_SCOPE_ID_PATTERN,
    )
    store_id: str | None = Field(
        default=None,
        min_length=1,
        max_length=64,
        pattern=_SCOPE_ID_PATTERN,
    )

    @model_validator(mode="after")
    def validate_hierarchy(self) -> "ScopeRef":
        if self.store_id is not None and self.group_id is None:
            raise ValueError("store context requires a group_id")
        return self

    @classmethod
    def installation(cls, installation_id: str = "default") -> "ScopeRef":
        return cls(installation_id=installation_id)

    @classmethod
    def group(cls, group_id: str, installation_id: str = "default") -> "ScopeRef":
        return cls(installation_id=installation_id, group_id=group_id)

    @classmethod
    def store(
        cls,
        group_id: str,
        store_id: str,
        installation_id: str = "default",
    ) -> "ScopeRef":
        return cls(
            installation_id=installation_id,
            group_id=group_id,
            store_id=store_id,
        )

    @property
    def level(self) -> ScopeLevel:
        if self.store_id is not None:
            return ScopeLevel.STORE
        if self.group_id is not None:
            return ScopeLevel.GROUP
        return ScopeLevel.INSTALLATION

    @property
    def key(self) -> str:
        parts = [self.installation_id]
        if self.group_id is not None:
            parts.append(self.group_id)
        if self.store_id is not None:
            parts.append(self.store_id)
        return f"{self.level.value}:" + ":".join(parts)

    @property
    def parent(self) -> ScopeRef | None:
        if self.store_id is not None:
            return ScopeRef.group(self.group_id or "", self.installation_id)
        if self.group_id is not None:
            return ScopeRef.installation(self.installation_id)
        return None

    def inheritance_chain(self) -> tuple[ScopeRef, ...]:
        chain = [ScopeRef.installation(self.installation_id)]
        if self.group_id is not None:
            chain.append(ScopeRef.group(self.group_id, self.installation_id))
        if self.store_id is not None:
            chain.append(
                ScopeRef.store(
                    self.group_id or "",
                    self.store_id,
                    self.installation_id,
                )
            )
        return tuple(chain)


class SecretReference(BaseModel):
    """Pointer to a secret held by an external provider. Never the value itself."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    provider: str = Field(min_length=1, max_length=32, pattern=_POINTER_PROVIDER)
    key: str = Field(min_length=1, max_length=255, pattern=_POINTER_KEY)
    version: str | None = Field(default=None, min_length=1, max_length=128)

    def redacted(self) -> dict[str, str]:
        output = {"provider": self.provider, "key": "[REDACTED]"}
        if self.version is not None:
            output["version"] = self.version
        return output

    def __str__(self) -> str:
        return f"<secret-reference provider={self.provider}>"

    def __repr__(self) -> str:
        return f"SecretReference(provider={self.provider!r}, key=<redacted>)"


class ResourceRef(BaseModel):
    """Package-owned resource identity inside a scope. Kind is not a Core taxonomy."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    owner: str = Field(pattern=PACKAGE_ID_PATTERN)
    kind: str = Field(pattern=_KIND_PATTERN, max_length=64)
    id: str = Field(pattern=_RESOURCE_ID_PATTERN, max_length=128)
    scope: ScopeRef


class ConnectionRef(BaseModel):
    """Named connection whose credential is a public SecretReference pointer."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    owner: str = Field(pattern=PACKAGE_ID_PATTERN)
    id: str = Field(pattern=_KIND_PATTERN, max_length=64)
    kind: str = Field(pattern=_KIND_PATTERN, max_length=64)
    secret: SecretReference


class EventEnvelope(BaseModel):
    """Durable event wrapper. Payload is the versioned contract body."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    id: str = Field(min_length=1, max_length=128)
    owner: str = Field(pattern=PACKAGE_ID_PATTERN)
    contract: str = Field(pattern=CONTRACT_NAME_PATTERN, max_length=192)
    version: str = Field(pattern=STABLE_SEMVER_PATTERN)
    payload: dict[str, Any]
    scope: ScopeRef
    resource: ResourceRef | None = None
    idempotency_key: str | None = Field(default=None, min_length=1, max_length=128)
    correlation_id: str | None = Field(default=None, pattern=_CORRELATION_ID)
    created_at: datetime

    @field_validator("payload")
    @classmethod
    def validate_payload_mapping(cls, value: Mapping[str, Any]) -> dict[str, Any]:
        return dict(value)

    @field_validator("created_at")
    @classmethod
    def validate_timezone(cls, value: datetime) -> datetime:
        if value.tzinfo is None:
            raise ValueError("event envelope created_at must be timezone-aware")
        return value


class HealthSeverity(StrEnum):
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class HealthIssue(BaseModel):
    """Package-owned diagnostic issue. Not process /health or doctor."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    owner: str = Field(pattern=PACKAGE_ID_PATTERN)
    code: str = Field(pattern=_ISSUE_CODE, max_length=128)
    severity: HealthSeverity
    scope: ScopeRef
    message: str = Field(min_length=1, max_length=512)


class ActionRef(BaseModel):
    """Optional named action bound to an existing permission and optional job."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    permission_id: str = Field(pattern=PERMISSION_ID_PATTERN)
    job_type: str | None = Field(default=None, pattern=_JOB_TYPE, max_length=128)
