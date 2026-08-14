"""Public protocols injected into an extension by the Platform composition."""

from __future__ import annotations

import re
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Protocol, TypeVar, runtime_checkable

from plaik_contracts import JobExecutionContext


_PACKAGE_ID = re.compile(r"^[a-z][a-z0-9-]{1,63}$")
_STORE_ID = re.compile(r"^[a-z0-9][a-z0-9-]{1,63}$")
_LOCALE = re.compile(r"^[a-z]{2,3}(?:-[A-Z]{2})?$")
T = TypeVar("T")


@runtime_checkable
class SecretValue(Protocol):
    """Opaque provider value; plaintext is revealed only by an explicit call."""

    def get_secret_value(self) -> str: ...


@runtime_checkable
class SettingsReader(Protocol):
    """Read settings already scoped to the receiving package and store."""

    def get(self, key: str, default: T | None = None) -> Any | T | None: ...


@runtime_checkable
class SecretReader(Protocol):
    """Resolve only secret names declared and granted to this package."""

    def get(self, key: str) -> SecretValue: ...


@runtime_checkable
class ServiceResolver(Protocol):
    def resolve(self, contract: str, version: str = "*") -> Any: ...


@runtime_checkable
class EventPublisher(Protocol):
    def publish(
        self,
        contract: str,
        version: str,
        payload: Mapping[str, Any],
        *,
        idempotency_key: str | None = None,
    ) -> None: ...


@runtime_checkable
class JobScheduler(Protocol):
    def enqueue(
        self,
        job_type: str,
        payload: Mapping[str, Any],
        *,
        idempotency_key: str,
        maximum_attempts: int = 5,
        scheduled_at: datetime | None = None,
    ) -> str: ...


@runtime_checkable
class JobHandler(Protocol):
    """Handle one leased attempt using its idempotency and fencing context."""

    def __call__(self, context: JobExecutionContext) -> None: ...


@runtime_checkable
class SlotContributor(Protocol):
    def bind(
        self,
        slot: str,
        version: str,
        template: str,
        *,
        position: int = 100,
    ) -> None: ...


@dataclass(frozen=True, slots=True)
class ExtensionRuntime:
    """The complete capability set visible to one extension instance."""

    package_id: str
    store_id: str
    locale: str
    settings: SettingsReader
    secrets: SecretReader
    services: ServiceResolver
    events: EventPublisher
    jobs: JobScheduler
    slots: SlotContributor

    def __post_init__(self) -> None:
        if not _PACKAGE_ID.fullmatch(self.package_id):
            raise ValueError("invalid SDK package id")
        if not _STORE_ID.fullmatch(self.store_id):
            raise ValueError("invalid SDK store id")
        if not _LOCALE.fullmatch(self.locale):
            raise ValueError("invalid SDK locale")


@runtime_checkable
class Extension(Protocol):
    """Supported extension entry point loaded after manifest verification."""

    def register(self, runtime: ExtensionRuntime) -> None: ...
