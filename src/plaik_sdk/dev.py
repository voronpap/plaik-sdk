"""Validate, inspect, build and test a public PLAIK package."""

from __future__ import annotations

import importlib.util
import json
import zipfile
from pathlib import Path
from types import SimpleNamespace
from typing import Any

from plaik_contracts import PackageType

from .errors import PackageDevError
from .package_fs import (
    MANIFEST_NAME,
    iter_package_files,
    load_manifest_document,
    load_package_manifest,
    load_theme_manifest,
    package_root,
    reject_core_imports,
    require_declared_files,
)
from .runtime import Extension, ExtensionRuntime
from .scaffold import create_package


class _NullAdapter:
    def get(self, *_args: object, **_kwargs: object) -> Any:
        return None

    def resolve(self, *_args: object, **_kwargs: object) -> object:
        return object()

    def publish(self, *_args: object, **_kwargs: object) -> None:
        return None

    def enqueue(self, *_args: object, **_kwargs: object) -> str:
        return "dev-job"

    def register(self, *_args: object, **_kwargs: object) -> None:
        return None

    def bind(self, *_args: object, **_kwargs: object) -> None:
        return None

    def report(self, *_args: object, **_kwargs: object) -> None:
        return None

    def subscribe(self, *_args: object, **_kwargs: object) -> None:
        return None

    def transaction(self):
        raise PackageDevError("package SQL is unavailable in isolated package tests")


def validate_package(path: Path | None = None) -> dict[str, Any]:
    root = package_root(path)
    if root.suffix == ".zip":
        raise PackageDevError("validate a package directory, then build the zip")
    document = load_manifest_document(root)
    reject_core_imports(root)
    if document.get("type") == "theme":
        manifest = load_theme_manifest(root)
        return {
            "id": manifest.id,
            "type": manifest.type,
            "version": manifest.version,
            "ok": True,
        }
    manifest = load_package_manifest(root)
    require_declared_files(root, manifest)
    return {
        "id": manifest.id,
        "type": manifest.type.value,
        "version": manifest.version,
        "ok": True,
    }


def inspect_package(path: Path | None = None) -> dict[str, Any]:
    root = package_root(path)
    document = load_manifest_document(root)
    if document.get("type") == "theme":
        manifest = load_theme_manifest(root)
        return {
            "id": manifest.id,
            "type": "theme",
            "version": manifest.version,
            "name": manifest.name,
            "core": manifest.core,
            "theme_api": manifest.theme_api,
            "slots": list(manifest.slots),
        }
    manifest = load_package_manifest(root)
    summary = {
        "id": manifest.id,
        "type": manifest.type.value,
        "version": manifest.version,
        "name": manifest.name,
        "core": manifest.core,
        "provides": [item.model_dump(mode="json") for item in manifest.provides],
        "requires": [item.model_dump(mode="json") for item in manifest.requires],
        "settings": [item.model_dump(mode="json") for item in manifest.settings],
        "services": [item.model_dump(mode="json") for item in manifest.services],
        "events": [item.model_dump(mode="json") for item in manifest.events],
        "migrations": [item.model_dump(mode="json") for item in manifest.migrations],
        "permissions": [item.model_dump(mode="json") for item in manifest.permissions],
    }
    if root.is_dir():
        require_declared_files(root, manifest)
    return summary


def build_package(path: Path | None = None, *, output: Path | None = None) -> Path:
    root = package_root(path)
    if root.suffix == ".zip":
        raise PackageDevError("build from a package directory")
    validate_package(root)
    document = load_manifest_document(root)
    package_id = str(document["id"])
    version = str(document["version"])
    destination = (
        Path(output).resolve()
        if output is not None
        else (root / "dist" / f"{package_id}-{version}.zip")
    )
    if destination.exists():
        raise PackageDevError(f"build output already exists: {destination}")
    destination.parent.mkdir(parents=True, exist_ok=True)
    files = [
        path
        for path in iter_package_files(root)
        if path.relative_to(root).parts[0] != "dist"
    ]
    if not any(path.name == MANIFEST_NAME for path in files):
        raise PackageDevError("package build is missing manifest.json")
    with zipfile.ZipFile(destination, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for path in files:
            archive.write(path, path.relative_to(root).as_posix())
    return destination


def run_package_test(path: Path | None = None) -> dict[str, Any]:
    root = package_root(path)
    report = validate_package(root)
    document = load_manifest_document(root)
    if document.get("type") in {PackageType.PACK.value, PackageType.THEME.value}:
        return {**report, "registered": False}
    runtime = development_runtime(str(document["id"]))
    register = load_register(root)
    register(runtime)
    if not isinstance(runtime, ExtensionRuntime):
        raise PackageDevError("package test runtime is invalid")
    return {**report, "registered": True}


def load_register(root: Path):
    extension = root / "extension.py"
    spec = importlib.util.spec_from_file_location(
        f"plaik_dev_{root.name.replace('-', '_')}",
        extension,
    )
    if spec is None or spec.loader is None:
        raise PackageDevError("cannot load extension.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    register = getattr(module, "register", None)
    if not callable(register):
        raise PackageDevError("extension.py must define register(runtime)")
    if not isinstance(register, Extension) and not callable(register):
        raise PackageDevError("extension.py register is not callable")
    return register


def development_runtime(package_id: str) -> ExtensionRuntime:
    adapter = _NullAdapter()
    return ExtensionRuntime(
        package_id=package_id,
        store_id="dev-store",
        locale="uk-UA",
        settings=adapter,
        secrets=adapter,
        services=adapter,
        events=adapter,
        jobs=adapter,
        slots=adapter,
        health=adapter,
        sql=adapter,
        admin=adapter,
    )


def dumps(document: dict[str, Any]) -> str:
    return json.dumps(document, indent=2) + "\n"


__all__ = [
    "PackageDevError",
    "SimpleNamespace",
    "build_package",
    "create_package",
    "development_runtime",
    "dumps",
    "inspect_package",
    "run_package_test",
    "validate_package",
]
