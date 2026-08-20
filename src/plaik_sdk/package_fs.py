"""Load and inspect a package directory or zip without importing Core."""

from __future__ import annotations

import ast
import json
import zipfile
from pathlib import Path, PurePosixPath

from plaik_contracts import PackageManifest, PackageType, ThemeManifest

from .errors import PackageDevError


SKIP_DIR_NAMES = frozenset(
    {".git", ".hg", ".svn", ".venv", "__pycache__", "dist", ".pytest_cache"}
)
SKIP_FILE_SUFFIXES = frozenset({".pyc", ".pyo", ".so"})
MANIFEST_NAME = "manifest.json"
EXTENSION_NAME = "extension.py"
CORE_RANGE = ">=0.4.0,<0.5.0"


def package_root(path: Path | None = None) -> Path:
    root = Path.cwd() if path is None else Path(path)
    if root.is_file() and root.suffix == ".zip":
        return root
    if not root.is_dir():
        raise PackageDevError(f"package path does not exist: {root}")
    return root.resolve()


def load_manifest_document(root: Path) -> dict:
    if root.is_file() and root.suffix == ".zip":
        with zipfile.ZipFile(root) as archive:
            try:
                raw = archive.read(MANIFEST_NAME)
            except KeyError as error:
                raise PackageDevError("artifact is missing manifest.json") from error
        try:
            document = json.loads(raw.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as error:
            raise PackageDevError("manifest.json is not valid JSON") from error
        if not isinstance(document, dict):
            raise PackageDevError("manifest.json must be an object")
        return document
    manifest_path = root / MANIFEST_NAME
    if not manifest_path.is_file():
        raise PackageDevError(f"missing {MANIFEST_NAME} in {root}")
    try:
        document = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise PackageDevError("manifest.json is not valid JSON") from error
    if not isinstance(document, dict):
        raise PackageDevError("manifest.json must be an object")
    return document


def load_package_manifest(root: Path) -> PackageManifest:
    document = load_manifest_document(root)
    if document.get("type") == "theme":
        raise PackageDevError("theme packages use ThemeManifest; inspect as a theme")
    try:
        return PackageManifest.model_validate(document)
    except Exception as error:
        raise PackageDevError(f"invalid package manifest: {error}") from error


def load_theme_manifest(root: Path) -> ThemeManifest:
    document = load_manifest_document(root)
    try:
        return ThemeManifest.model_validate(document)
    except Exception as error:
        raise PackageDevError(f"invalid theme manifest: {error}") from error


def iter_package_files(root: Path) -> tuple[Path, ...]:
    files: list[Path] = []
    for path in sorted(root.rglob("*")):
        if not path.is_file() or path.is_symlink():
            continue
        relative = path.relative_to(root)
        if any(part in SKIP_DIR_NAMES for part in relative.parts):
            continue
        if path.suffix in SKIP_FILE_SUFFIXES:
            continue
        files.append(path)
    return tuple(files)


def reject_core_imports(root: Path) -> None:
    leaked: list[str] = []
    for path in iter_package_files(root):
        if path.suffix != ".py":
            continue
        try:
            tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        except (OSError, SyntaxError) as error:
            raise PackageDevError(f"cannot parse {path.name}: {error}") from error
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                if any(alias.name == "plaik_core" or alias.name.startswith("plaik_core.") for alias in node.names):
                    leaked.append(str(path.relative_to(root)))
                    break
            elif isinstance(node, ast.ImportFrom) and node.module:
                if node.module == "plaik_core" or node.module.startswith("plaik_core."):
                    leaked.append(str(path.relative_to(root)))
                    break
    if leaked:
        raise PackageDevError(
            "package must not import plaik_core: " + ", ".join(leaked)
        )


def require_declared_files(root: Path, manifest: PackageManifest) -> None:
    for migration in manifest.migrations:
        path = root.joinpath(*PurePosixPath(migration.path).parts)
        if not path.is_file() or path.is_symlink():
            raise PackageDevError(f"declared migration is missing: {migration.path}")
    if manifest.type in {PackageType.MODULE, PackageType.INTEGRATION}:
        extension = root / EXTENSION_NAME
        if not extension.is_file() or extension.is_symlink():
            raise PackageDevError(f"missing {EXTENSION_NAME} for {manifest.type} package")
    elif (root / EXTENSION_NAME).exists():
        raise PackageDevError(f"{manifest.type} packages must not ship {EXTENSION_NAME}")
