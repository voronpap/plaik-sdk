"""Stable, domain-neutral integration surface for PLAIK extensions."""

from plaik_contracts import (
    JobExecutionContext,
    PackageWebDeclaration,
    WebHookDeclaration,
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
    "PackageWebDeclaration",
    "SecretReader",
    "SecretValue",
    "ServiceResolver",
    "SettingsReader",
    "SlotContributor",
    "WebHookDeclaration",
]
