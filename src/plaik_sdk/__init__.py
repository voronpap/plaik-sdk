"""Stable, domain-neutral integration surface for PLAIK extensions."""

from plaik_contracts import (
    ActionRef,
    ConnectionRef,
    EventEnvelope,
    HealthIssue,
    JobExecutionContext,
    PackageCapabilityProvide,
    PackageCapabilityRequire,
    PackageWebDeclaration,
    ResourceRef,
    ScopeRef,
    SecretReference,
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
    "ActionRef",
    "ConnectionRef",
    "EventEnvelope",
    "EventPublisher",
    "Extension",
    "ExtensionRuntime",
    "HealthIssue",
    "JobExecutionContext",
    "JobHandler",
    "JobScheduler",
    "PackageCapabilityProvide",
    "PackageCapabilityRequire",
    "PackageWebDeclaration",
    "ResourceRef",
    "ScopeRef",
    "SecretReader",
    "SecretReference",
    "SecretValue",
    "ServiceResolver",
    "SettingsReader",
    "SlotContributor",
    "WebHookDeclaration",
]
