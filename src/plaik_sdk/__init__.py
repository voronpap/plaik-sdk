"""Stable, domain-neutral integration surface for PLAIK extensions."""

from plaik_contracts import (
    JobExecutionContext,
    PackageStorefrontDeclaration,
    StorefrontHookDeclaration,
)

from .runtime import (
    EventPublisher,
    Extension,
    ExtensionRuntime,
    JobHandler,
    JobScheduler,
    SecretReader,
    SecretValue,
    ServiceResolver,
    SettingsReader,
    SlotContributor,
)

__all__ = [
    "EventPublisher",
    "Extension",
    "ExtensionRuntime",
    "JobExecutionContext",
    "JobHandler",
    "JobScheduler",
    "PackageStorefrontDeclaration",
    "SecretReader",
    "SecretValue",
    "ServiceResolver",
    "SettingsReader",
    "SlotContributor",
    "StorefrontHookDeclaration",
]
