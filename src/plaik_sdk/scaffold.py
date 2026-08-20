"""Create a package tree that depends only on public plaik-sdk."""

from __future__ import annotations

import json
import re
from pathlib import Path

from plaik_contracts.packages import PACKAGE_ID_PATTERN, PackageType

from .errors import PackageDevError
from .package_fs import CORE_RANGE, EXTENSION_NAME, MANIFEST_NAME


_TITLE = re.compile(r"[-_]+")


def create_package(
    package_type: str,
    package_id: str,
    *,
    directory: Path | None = None,
) -> Path:
    """Write a new package directory and return its path."""

    if not re.fullmatch(PACKAGE_ID_PATTERN, package_id):
        raise PackageDevError("invalid package id")
    try:
        kind = PackageType(package_type)
    except ValueError as error:
        raise PackageDevError(
            "package type must be module, integration, theme or pack"
        ) from error
    parent = Path.cwd() if directory is None else Path(directory)
    root = (parent / package_id).resolve()
    if root.exists():
        raise PackageDevError(f"package directory already exists: {root}")
    root.mkdir(parents=True)
    if kind is PackageType.THEME:
        _write_theme(root, package_id)
    elif kind is PackageType.PACK:
        _write_pack(root, package_id)
    else:
        _write_module(root, package_id, kind)
    return root


def _write_module(root: Path, package_id: str, kind: PackageType) -> None:
    name = _display_name(package_id)
    capability = f"{package_id}.resource"
    sql_dir = root / "sql"
    sql_dir.mkdir()
    (sql_dir / "001_init.sql").write_text(
        "-- Package-owned schema. Core sets search_path to this package schema.\n"
        "CREATE TABLE IF NOT EXISTS records (\n"
        "    id TEXT PRIMARY KEY,\n"
        "    payload JSONB NOT NULL\n"
        ");\n",
        encoding="utf-8",
    )
    manifest = {
        "id": package_id,
        "type": kind.value,
        "version": "0.1.0",
        "name": name,
        "core": CORE_RANGE,
        "dependencies": [],
        "conflicts": [],
        "permissions": [
            {
                "id": f"{package_id}.manage",
                "description": f"Manage {name}",
            }
        ],
        "settings": [{"key": "page-size", "secret": False}],
        "services": [{"contract": f"{package_id}.query", "version": "1.0.0"}],
        "events": [{"contract": f"{package_id}.changed", "version": "1.0.0"}],
        "provides": [{"id": capability, "version": "1.0.0"}],
        "requires": [],
        "migrations": [{"version": "001_init", "path": "sql/001_init.sql"}],
        "storage": [],
        "web": {
            "hooks": [],
            "slots": [
                {
                    "slot": "storefront.page.content",
                    "template": "slot.html",
                    "position": 100,
                }
            ],
        },
    }
    _write_json(root / MANIFEST_NAME, manifest)
    web_dir = root / "web"
    web_dir.mkdir()
    (web_dir / "slot.html").write_text(
        f"<section data-plaik-package=\"{package_id}\"></section>\n",
        encoding="utf-8",
    )
    (root / EXTENSION_NAME).write_text(
        _extension_source(package_id),
        encoding="utf-8",
    )
    (root / "README.md").write_text(
        f"# {name}\n\n"
        "This package depends only on public `plaik-sdk`.\n"
        "Do not import `plaik_core`.\n",
        encoding="utf-8",
    )


def _write_pack(root: Path, package_id: str) -> None:
    manifest = {
        "id": package_id,
        "type": "pack",
        "version": "0.1.0",
        "name": _display_name(package_id),
        "core": CORE_RANGE,
        "dependencies": [],
        "conflicts": [],
        "requires": [],
    }
    _write_json(root / MANIFEST_NAME, manifest)
    (root / "README.md").write_text(
        f"# {_display_name(package_id)}\n\n"
        "A pack only selects compatible packages. It must not ship implementation.\n",
        encoding="utf-8",
    )


def _write_theme(root: Path, package_id: str) -> None:
    manifest = {
        "id": package_id,
        "type": "theme",
        "version": "0.1.0",
        "name": _display_name(package_id),
        "core": CORE_RANGE,
        "parent": None,
        "theme_api": 1,
        "layouts": ["full-width"],
        "assets": {"css": ["assets/css/theme.css"], "js": []},
        "hooks": ["displayContent"],
        "slots": ["storefront.page.content"],
        "page_templates": ["home"],
        "sections": ["header"],
        "blocks": ["text"],
        "settings_schema": False,
        "presets": [],
    }
    _write_json(root / MANIFEST_NAME, manifest)
    css = root / "assets" / "css"
    css.mkdir(parents=True)
    (css / "theme.css").write_text(
        f"[data-plaik-theme=\"{package_id}\"] {{ color: inherit; }}\n",
        encoding="utf-8",
    )
    layouts = root / "templates" / "layouts"
    layouts.mkdir(parents=True)
    (layouts / "full-width.html").write_text(
        "<!doctype html><html><body>{{ content }}</body></html>\n",
        encoding="utf-8",
    )
    (root / "README.md").write_text(
        f"# {_display_name(package_id)}\n\nTheme presentation only. No Core imports.\n",
        encoding="utf-8",
    )


def _extension_source(package_id: str) -> str:
    job_type = f"{package_id}.reindex"
    return (
        '"""Package entry point loaded after manifest verification."""\n\n'
        "from plaik_sdk import ExtensionRuntime\n\n\n"
        "def register(runtime: ExtensionRuntime) -> None:\n"
        "    if runtime.package_id != "
        f'"{package_id}"'
        ":\n"
        '        raise ValueError("runtime package id does not match this package")\n\n'
        "    def handle_reindex(context) -> None:\n"
        "        del context\n\n"
        f'    runtime.jobs.register("{job_type}", handle_reindex)\n'
    )


def _display_name(package_id: str) -> str:
    return _TITLE.sub(" ", package_id).title()


def _write_json(path: Path, document: dict) -> None:
    path.write_text(json.dumps(document, indent=2) + "\n", encoding="utf-8")
