"""Base PLAIK package manifest contracts."""

from enum import StrEnum
from pathlib import PurePosixPath, PureWindowsPath

from packaging.specifiers import InvalidSpecifier, SpecifierSet
from packaging.version import InvalidVersion, Version
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


PACKAGE_ID_PATTERN = r"^[a-z][a-z0-9]*(?:-[a-z0-9]+)*$"
SEMVER_PATTERN = r"^\d+\.\d+\.\d+(?:-[0-9A-Za-z.-]+)?$"
STABLE_SEMVER_PATTERN = r"^\d+\.\d+\.\d+$"
HOOK_PATTERN = r"^[a-z][A-Za-z0-9]{1,63}$"
PERMISSION_ID_PATTERN = r"^[a-z][a-z0-9_.:-]{1,127}(?:\.\*)?$"
SETTING_KEY_PATTERN = r"^[a-z][a-z0-9_.-]{0,63}$"
CONTRACT_NAME_PATTERN = r"^[a-z][a-z0-9-]*(?:\.[a-z][A-Za-z0-9_-]*)+$"
CAPABILITY_ID_PATTERN = r"^[a-z][a-z0-9-]*(?:\.[a-z][A-Za-z0-9_-]*)+$"
STORAGE_ID_PATTERN = r"^[a-z][a-z0-9_.-]{0,63}$"
MIGRATION_VERSION_PATTERN = r"^[0-9A-Za-z][0-9A-Za-z._-]{0,63}$"


class PackageType(StrEnum):
    MODULE = "module"
    INTEGRATION = "integration"
    THEME = "theme"
    PACK = "pack"


class PackageDependency(BaseModel):
    model_config = ConfigDict(extra="forbid")

    package_id: str = Field(pattern=PACKAGE_ID_PATTERN)
    version: str = "*"
    optional: bool = False

    @field_validator("version")
    @classmethod
    def validate_version_range(cls, value: str) -> str:
        if value == "*":
            return value
        try:
            SpecifierSet(value)
        except InvalidSpecifier as error:
            raise ValueError("invalid dependency version range") from error
        return value


class WebHookDeclaration(BaseModel):
    """Persistent module-to-theme render binding stored in package metadata."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    hook: str = Field(pattern=HOOK_PATTERN)
    template: str = Field(min_length=1, max_length=255)
    position: int = Field(default=100, ge=-10_000, le=10_000)

    @field_validator("template")
    @classmethod
    def validate_template_path(cls, value: str) -> str:
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
        ):
            raise ValueError("invalid web template path")
        return value


class PackageWebDeclaration(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    hooks: list[WebHookDeclaration] = Field(default_factory=list, max_length=128)

    @model_validator(mode="after")
    def validate_unique_bindings(self) -> "PackageWebDeclaration":
        identities = [(item.hook, item.template) for item in self.hooks]
        if len(identities) != len(set(identities)):
            raise ValueError("duplicate web hook binding")
        return self


class PackagePermissionDeclaration(BaseModel):
    """Package-owned RBAC permission registered during the package transaction."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    id: str = Field(pattern=PERMISSION_ID_PATTERN)
    description: str = Field(default="", max_length=256)
    dangerous: bool = False


class PackageSettingDeclaration(BaseModel):
    """Relative setting key under the package-owned settings namespace."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    key: str = Field(pattern=SETTING_KEY_PATTERN)
    secret: bool = False


class PackageServiceDeclaration(BaseModel):
    """Versioned service contract owned by the declaring package."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    contract: str = Field(pattern=CONTRACT_NAME_PATTERN, max_length=192)
    version: str = Field(pattern=STABLE_SEMVER_PATTERN)


class PackageEventDeclaration(BaseModel):
    """Versioned event contract owned by the declaring package."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    contract: str = Field(pattern=CONTRACT_NAME_PATTERN, max_length=192)
    version: str = Field(pattern=STABLE_SEMVER_PATTERN)


class PackageCapabilityDeclaration(BaseModel):
    """Named capability advertised by the package for dependency resolution."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    id: str = Field(pattern=CAPABILITY_ID_PATTERN, max_length=192)


class PackageMigrationDeclaration(BaseModel):
    """Forward-only package migration identity and artifact-relative SQL path."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    version: str = Field(pattern=MIGRATION_VERSION_PATTERN)
    path: str = Field(min_length=1, max_length=255)

    @field_validator("path")
    @classmethod
    def validate_migration_path(cls, value: str) -> str:
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
            or not value.endswith(".sql")
        ):
            raise ValueError("invalid package migration path")
        return value


class PackageStorageDeclaration(BaseModel):
    """Package-owned storage namespace for media or private blobs."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    id: str = Field(pattern=STORAGE_ID_PATTERN)
    kind: str = Field(default="private", pattern=r"^(blob|media|private)$")


class PackageManifest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str = Field(pattern=PACKAGE_ID_PATTERN)
    type: PackageType
    version: str = Field(pattern=SEMVER_PATTERN)
    name: str = Field(min_length=1, max_length=120)
    core: str
    dependencies: list[PackageDependency] = Field(default_factory=list)
    conflicts: list[PackageDependency] = Field(default_factory=list)
    web: PackageWebDeclaration = Field(default_factory=PackageWebDeclaration)
    permissions: list[PackagePermissionDeclaration] = Field(
        default_factory=list, max_length=256
    )
    settings: list[PackageSettingDeclaration] = Field(
        default_factory=list, max_length=256
    )
    services: list[PackageServiceDeclaration] = Field(
        default_factory=list, max_length=128
    )
    events: list[PackageEventDeclaration] = Field(default_factory=list, max_length=128)
    capabilities: list[PackageCapabilityDeclaration] = Field(
        default_factory=list, max_length=128
    )
    migrations: list[PackageMigrationDeclaration] = Field(
        default_factory=list, max_length=512
    )
    storage: list[PackageStorageDeclaration] = Field(
        default_factory=list, max_length=64
    )

    @field_validator("core")
    @classmethod
    def validate_core_range(cls, value: str) -> str:
        try:
            SpecifierSet(value)
        except InvalidSpecifier as error:
            raise ValueError("invalid Core version range") from error
        return value

    @model_validator(mode="after")
    def validate_relationships(self) -> "PackageManifest":
        dependency_ids = [dependency.package_id for dependency in self.dependencies]
        conflict_ids = [conflict.package_id for conflict in self.conflicts]
        if len(dependency_ids) != len(set(dependency_ids)):
            raise ValueError("duplicate package dependency")
        if len(conflict_ids) != len(set(conflict_ids)):
            raise ValueError("duplicate package conflict")
        if self.id in dependency_ids or self.id in conflict_ids:
            raise ValueError("package cannot depend on or conflict with itself")
        overlap = set(dependency_ids) & set(conflict_ids)
        if overlap:
            raise ValueError(
                f"package relationship is both dependency and conflict: {sorted(overlap)}"
            )
        if self.web.hooks and self.type not in {
            PackageType.MODULE,
            PackageType.INTEGRATION,
        }:
            raise ValueError("only module or integration packages may declare hooks")
        self._validate_implementation_declarations()
        self._validate_owned_namespaces()
        return self

    def _validate_implementation_declarations(self) -> None:
        has_implementation = any(
            (
                self.permissions,
                self.settings,
                self.services,
                self.events,
                self.capabilities,
                self.migrations,
                self.storage,
            )
        )
        if self.type == PackageType.PACK and (has_implementation or self.web.hooks):
            raise ValueError("pack packages may declare only dependencies and conflicts")
        if self.type == PackageType.THEME and has_implementation:
            raise ValueError(
                "theme packages may not declare permissions, settings, services, "
                "events, capabilities, migrations or storage"
            )

    def _validate_owned_namespaces(self) -> None:
        permission_ids = [item.id for item in self.permissions]
        if len(permission_ids) != len(set(permission_ids)):
            raise ValueError("duplicate package permission")
        for permission in self.permissions:
            _require_owned_name(self.id, permission.id, kind="permission")

        setting_keys = [item.key for item in self.settings]
        if len(setting_keys) != len(set(setting_keys)):
            raise ValueError("duplicate package setting")

        service_keys = [(item.contract, item.version) for item in self.services]
        if len(service_keys) != len(set(service_keys)):
            raise ValueError("duplicate package service declaration")
        for service in self.services:
            _require_owned_contract(self.id, service.contract)
            _require_stable_semver(service.version)

        event_keys = [(item.contract, item.version) for item in self.events]
        if len(event_keys) != len(set(event_keys)):
            raise ValueError("duplicate package event declaration")
        for event in self.events:
            _require_owned_contract(self.id, event.contract)
            _require_stable_semver(event.version)

        capability_ids = [item.id for item in self.capabilities]
        if len(capability_ids) != len(set(capability_ids)):
            raise ValueError("duplicate package capability")
        for capability in self.capabilities:
            _require_owned_contract(self.id, capability.id)

        migration_versions = [item.version for item in self.migrations]
        if len(migration_versions) != len(set(migration_versions)):
            raise ValueError("duplicate package migration version")
        migration_paths = [item.path for item in self.migrations]
        if len(migration_paths) != len(set(migration_paths)):
            raise ValueError("duplicate package migration path")

        storage_ids = [item.id for item in self.storage]
        if len(storage_ids) != len(set(storage_ids)):
            raise ValueError("duplicate package storage declaration")


def _require_owned_name(package_id: str, value: str, *, kind: str) -> None:
    if value == "*" or value.startswith("core.") or value == "core":
        raise ValueError(f"{kind} id reserves core.* for Platform Core")
    prefix = f"{package_id}."
    if not value.startswith(prefix):
        raise ValueError(f"{kind} id must use its package-owned namespace")
    remainder = value[len(prefix) :]
    if not remainder or remainder.startswith(".") or "/." in f".{remainder}":
        raise ValueError(f"invalid {kind} id")


def _require_owned_contract(package_id: str, contract: str) -> None:
    if contract.startswith("core.") or contract == "core":
        raise ValueError("core.* contracts are reserved for Platform Core")
    if not contract.startswith(f"{package_id}."):
        raise ValueError("contract name must use its package-owned namespace")


def _require_stable_semver(value: str) -> None:
    try:
        parsed = Version(value)
    except (InvalidVersion, TypeError) as error:
        raise ValueError("invalid contract version") from error
    if parsed.is_prerelease or parsed.is_devrelease or parsed.local is not None:
        raise ValueError("contract versions must be stable public releases")
