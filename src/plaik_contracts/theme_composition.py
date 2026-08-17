"""Theme API v1 page/section/block composition contracts.

These types are declarative JSON documents. They do not execute templates,
Python, or Jinja directives. Nested blocks are allowed only where a block
schema says so; recursive or unbounded nesting is rejected.
"""

from __future__ import annotations

import re
from enum import IntEnum, StrEnum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from .packages import SETTING_KEY_PATTERN
from .theme_api import (
    SLOT_ID_PATTERN,
    SLOT_ID_MAX_LENGTH,
    _validate_web_template_path,
    require_public_slot_id,
)

COMPOSITION_SCHEMA_VERSION = 1
SUPPORTED_COMPOSITION_SCHEMA_VERSIONS = frozenset({COMPOSITION_SCHEMA_VERSION})
COMPOSITION_ID_PATTERN = r"^[a-z][a-z0-9-]{0,63}$"
MAX_PAGE_TEMPLATE_BYTES = 64 * 1024
MAX_DEFINITION_BYTES = 16 * 1024
MAX_COMPOSITION_BYTES = 256 * 1024
MAX_SECTIONS_PER_PAGE = 64
MAX_BLOCKS_PER_PARENT = 64
MAX_BLOCK_NESTING_DEPTH = 4
MAX_SETTINGS_PER_SCHEMA = 32
MAX_SETTING_STRING_LENGTH = 4096
MAX_ENUM_CHOICES = 32
MAX_DECLARED_PAGE_TEMPLATES = 64
MAX_DECLARED_SECTION_TYPES = 128
MAX_DECLARED_BLOCK_TYPES = 128


class CompositionSchemaVersion(IntEnum):
    V1 = COMPOSITION_SCHEMA_VERSION


class SettingFieldType(StrEnum):
    STRING = "string"
    INTEGER = "integer"
    BOOLEAN = "boolean"
    ENUM = "enum"


def require_supported_composition_schema(value: int) -> int:
    if value not in SUPPORTED_COMPOSITION_SCHEMA_VERSIONS:
        raise ValueError("unsupported composition schema version")
    return value


def require_composition_id(value: str, *, error: str = "invalid composition id") -> str:
    if not isinstance(value, str) or not re.fullmatch(COMPOSITION_ID_PATTERN, value):
        raise ValueError(error)
    return value


def _require_setting_value(value: Any) -> str | int | bool:
    if type(value) is bool or type(value) is int:
        return value
    if type(value) is str:
        if len(value) > MAX_SETTING_STRING_LENGTH or "\x00" in value:
            raise ValueError("invalid setting value")
        return value
    raise ValueError("invalid setting value")


class SettingFieldSchema(BaseModel):
    """One declarative setting on a section or block definition."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    id: str = Field(pattern=SETTING_KEY_PATTERN, max_length=64)
    type: SettingFieldType
    default: str | int | bool | None = None
    min_length: int | None = Field(default=None, ge=0, le=MAX_SETTING_STRING_LENGTH)
    max_length: int | None = Field(default=None, ge=0, le=MAX_SETTING_STRING_LENGTH)
    minimum: int | None = None
    maximum: int | None = None
    choices: tuple[str, ...] = Field(default=(), max_length=MAX_ENUM_CHOICES)

    @field_validator("default")
    @classmethod
    def validate_default(cls, value: str | int | bool | None) -> str | int | bool | None:
        if value is None:
            return value
        return _require_setting_value(value)

    @field_validator("choices")
    @classmethod
    def validate_choices(cls, value: tuple[str, ...]) -> tuple[str, ...]:
        if len(value) != len(set(value)):
            raise ValueError("duplicate enum choice")
        for choice in value:
            if not isinstance(choice, str) or not choice or "\x00" in choice:
                raise ValueError("invalid enum choice")
            if len(choice) > MAX_SETTING_STRING_LENGTH:
                raise ValueError("invalid enum choice")
        return value

    @model_validator(mode="after")
    def constraints_match_type(self) -> SettingFieldSchema:
        if self.type is SettingFieldType.STRING:
            if self.minimum is not None or self.maximum is not None or self.choices:
                raise ValueError("string setting has invalid constraints")
            if (
                self.min_length is not None
                and self.max_length is not None
                and self.min_length > self.max_length
            ):
                raise ValueError("string setting length range is invalid")
            if self.default is not None and type(self.default) is not str:
                raise ValueError("string setting default is invalid")
        elif self.type is SettingFieldType.INTEGER:
            if (
                self.min_length is not None
                or self.max_length is not None
                or self.choices
            ):
                raise ValueError("integer setting has invalid constraints")
            if (
                self.minimum is not None
                and self.maximum is not None
                and self.minimum > self.maximum
            ):
                raise ValueError("integer setting range is invalid")
            if self.default is not None and type(self.default) is not int:
                raise ValueError("integer setting default is invalid")
        elif self.type is SettingFieldType.BOOLEAN:
            if (
                self.min_length is not None
                or self.max_length is not None
                or self.minimum is not None
                or self.maximum is not None
                or self.choices
            ):
                raise ValueError("boolean setting has invalid constraints")
            if self.default is not None and type(self.default) is not bool:
                raise ValueError("boolean setting default is invalid")
        else:
            if (
                self.min_length is not None
                or self.max_length is not None
                or self.minimum is not None
                or self.maximum is not None
            ):
                raise ValueError("enum setting has invalid constraints")
            if not self.choices:
                raise ValueError("enum setting requires choices")
            if self.default is not None and self.default not in self.choices:
                raise ValueError("enum setting default is invalid")
        return self


def _validate_slot_ids(value: tuple[str, ...]) -> tuple[str, ...]:
    if len(value) != len(set(value)):
        raise ValueError("duplicate slot id")
    for slot_id in value:
        if not isinstance(slot_id, str) or len(slot_id) > SLOT_ID_MAX_LENGTH:
            raise ValueError("invalid slot id")
        if not re.fullmatch(SLOT_ID_PATTERN, slot_id):
            raise ValueError("invalid slot id")
        require_public_slot_id(slot_id)
    return value


def _validate_type_ids(value: tuple[str, ...], *, error: str) -> tuple[str, ...]:
    if len(value) != len(set(value)):
        raise ValueError(error)
    for item in value:
        require_composition_id(item, error=error)
    return value


class BlockDefinition(BaseModel):
    """Declarative schema for one reusable block type."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    type: str = Field(pattern=COMPOSITION_ID_PATTERN, max_length=64)
    template: str = Field(min_length=1, max_length=255)
    settings: tuple[SettingFieldSchema, ...] = Field(
        default=(), max_length=MAX_SETTINGS_PER_SCHEMA
    )
    allowed_blocks: tuple[str, ...] = Field(
        default=(), max_length=MAX_DECLARED_BLOCK_TYPES
    )
    max_blocks: int = Field(default=0, ge=0, le=MAX_BLOCKS_PER_PARENT)
    max_nesting_depth: int = Field(default=0, ge=0, le=MAX_BLOCK_NESTING_DEPTH)
    slots: tuple[str, ...] = Field(default=(), max_length=32)

    @field_validator("template")
    @classmethod
    def validate_template(cls, value: str) -> str:
        return _validate_web_template_path(value)

    @field_validator("settings")
    @classmethod
    def validate_unique_settings(
        cls, value: tuple[SettingFieldSchema, ...]
    ) -> tuple[SettingFieldSchema, ...]:
        ids = [field.id for field in value]
        if len(ids) != len(set(ids)):
            raise ValueError("duplicate setting id")
        return value

    @field_validator("allowed_blocks")
    @classmethod
    def validate_allowed_blocks(cls, value: tuple[str, ...]) -> tuple[str, ...]:
        return _validate_type_ids(value, error="invalid nested block type")

    @field_validator("slots")
    @classmethod
    def validate_slots(cls, value: tuple[str, ...]) -> tuple[str, ...]:
        return _validate_slot_ids(value)

    @model_validator(mode="after")
    def nesting_is_bounded(self) -> BlockDefinition:
        if self.type in self.allowed_blocks:
            raise ValueError("recursive block nesting")
        if self.allowed_blocks:
            if self.max_blocks < 1 or self.max_nesting_depth < 1:
                raise ValueError("unbounded block nesting")
        elif self.max_blocks != 0 or self.max_nesting_depth != 0:
            raise ValueError("block nesting is not declared")
        return self


class SectionDefinition(BaseModel):
    """Declarative schema for one reusable section type."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    type: str = Field(pattern=COMPOSITION_ID_PATTERN, max_length=64)
    template: str = Field(min_length=1, max_length=255)
    settings: tuple[SettingFieldSchema, ...] = Field(
        default=(), max_length=MAX_SETTINGS_PER_SCHEMA
    )
    allowed_blocks: tuple[str, ...] = Field(
        default=(), max_length=MAX_DECLARED_BLOCK_TYPES
    )
    max_blocks: int = Field(default=0, ge=0, le=MAX_BLOCKS_PER_PARENT)
    max_block_nesting_depth: int = Field(default=0, ge=0, le=MAX_BLOCK_NESTING_DEPTH)
    slots: tuple[str, ...] = Field(default=(), max_length=32)

    @field_validator("template")
    @classmethod
    def validate_template(cls, value: str) -> str:
        return _validate_web_template_path(value)

    @field_validator("settings")
    @classmethod
    def validate_unique_settings(
        cls, value: tuple[SettingFieldSchema, ...]
    ) -> tuple[SettingFieldSchema, ...]:
        ids = [field.id for field in value]
        if len(ids) != len(set(ids)):
            raise ValueError("duplicate setting id")
        return value

    @field_validator("allowed_blocks")
    @classmethod
    def validate_allowed_blocks(cls, value: tuple[str, ...]) -> tuple[str, ...]:
        return _validate_type_ids(value, error="invalid nested block type")

    @field_validator("slots")
    @classmethod
    def validate_slots(cls, value: tuple[str, ...]) -> tuple[str, ...]:
        return _validate_slot_ids(value)

    @model_validator(mode="after")
    def nesting_is_bounded(self) -> SectionDefinition:
        if self.allowed_blocks:
            if self.max_blocks < 1 or self.max_block_nesting_depth < 1:
                raise ValueError("unbounded block nesting")
        elif self.max_blocks != 0 or self.max_block_nesting_depth != 0:
            raise ValueError("block nesting is not declared")
        return self


class BlockInstance(BaseModel):
    """One configured block inside a section or parent block."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    type: str = Field(pattern=COMPOSITION_ID_PATTERN, max_length=64)
    settings: dict[str, str | int | bool] = Field(
        default_factory=dict, max_length=MAX_SETTINGS_PER_SCHEMA
    )
    blocks: dict[str, BlockInstance] = Field(
        default_factory=dict, max_length=MAX_BLOCKS_PER_PARENT
    )
    block_order: tuple[str, ...] = Field(default=(), max_length=MAX_BLOCKS_PER_PARENT)
    enabled: bool = True

    @field_validator("settings")
    @classmethod
    def validate_settings(cls, value: dict[str, str | int | bool]) -> dict[str, str | int | bool]:
        return _validate_instance_settings(value)

    @field_validator("blocks")
    @classmethod
    def validate_block_ids(cls, value: dict[str, BlockInstance]) -> dict[str, BlockInstance]:
        for instance_id in value:
            require_composition_id(instance_id, error="invalid block instance id")
        return value

    @model_validator(mode="after")
    def order_matches_blocks(self) -> BlockInstance:
        _require_deterministic_order(self.block_order, self.blocks, kind="block")
        return self


class SectionInstance(BaseModel):
    """One configured section inside a page template."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    type: str = Field(pattern=COMPOSITION_ID_PATTERN, max_length=64)
    settings: dict[str, str | int | bool] = Field(
        default_factory=dict, max_length=MAX_SETTINGS_PER_SCHEMA
    )
    blocks: dict[str, BlockInstance] = Field(
        default_factory=dict, max_length=MAX_BLOCKS_PER_PARENT
    )
    block_order: tuple[str, ...] = Field(default=(), max_length=MAX_BLOCKS_PER_PARENT)
    enabled: bool = True

    @field_validator("settings")
    @classmethod
    def validate_settings(cls, value: dict[str, str | int | bool]) -> dict[str, str | int | bool]:
        return _validate_instance_settings(value)

    @field_validator("blocks")
    @classmethod
    def validate_block_ids(cls, value: dict[str, BlockInstance]) -> dict[str, BlockInstance]:
        for instance_id in value:
            require_composition_id(instance_id, error="invalid block instance id")
        return value

    @model_validator(mode="after")
    def order_matches_blocks(self) -> SectionInstance:
        _require_deterministic_order(self.block_order, self.blocks, kind="block")
        return self


class PageTemplate(BaseModel):
    """Declarative page composition document."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: int
    sections: dict[str, SectionInstance] = Field(
        default_factory=dict, max_length=MAX_SECTIONS_PER_PAGE
    )
    order: tuple[str, ...] = Field(max_length=MAX_SECTIONS_PER_PAGE)

    @field_validator("schema_version")
    @classmethod
    def validate_schema_version(cls, value: int) -> int:
        return require_supported_composition_schema(value)

    @field_validator("sections")
    @classmethod
    def validate_section_ids(
        cls, value: dict[str, SectionInstance]
    ) -> dict[str, SectionInstance]:
        for instance_id in value:
            require_composition_id(instance_id, error="invalid section instance id")
        return value

    @model_validator(mode="after")
    def unique_ids_and_order(self) -> PageTemplate:
        _require_deterministic_order(self.order, self.sections, kind="section")
        seen: set[str] = set()
        for section_id, section in self.sections.items():
            _register_instance_id(seen, section_id)
            _collect_block_ids(section.blocks, seen)
        return self


def _validate_instance_settings(
    value: dict[str, str | int | bool],
) -> dict[str, str | int | bool]:
    validated: dict[str, str | int | bool] = {}
    for key, raw in value.items():
        if not re.fullmatch(SETTING_KEY_PATTERN, key):
            raise ValueError("invalid setting id")
        validated[key] = _require_setting_value(raw)
    return validated


def _require_deterministic_order(
    order: tuple[str, ...],
    items: dict[str, Any],
    *,
    kind: str,
) -> None:
    if len(order) != len(set(order)):
        raise ValueError(f"duplicate {kind} instance id")
    if set(order) != set(items) or len(order) != len(items):
        raise ValueError(f"{kind} order must list each instance exactly once")


def _register_instance_id(seen: set[str], instance_id: str) -> None:
    if instance_id in seen:
        raise ValueError("duplicate instance id")
    seen.add(instance_id)


def _collect_block_ids(blocks: dict[str, BlockInstance], seen: set[str]) -> None:
    for instance_id, block in blocks.items():
        _register_instance_id(seen, instance_id)
        _collect_block_ids(block.blocks, seen)


def validate_settings_against_schema(
    values: dict[str, str | int | bool],
    schema: tuple[SettingFieldSchema, ...] | list[SettingFieldSchema],
) -> dict[str, str | int | bool]:
    """Fail closed if instance settings do not match the declared schema."""

    fields = {field.id: field for field in schema}
    unknown = sorted(set(values) - set(fields))
    if unknown:
        raise ValueError("unknown setting")
    resolved: dict[str, str | int | bool] = {}
    for field in schema:
        if field.id in values:
            resolved[field.id] = _check_setting_value(values[field.id], field)
        elif field.default is not None:
            resolved[field.id] = field.default
        else:
            raise ValueError("missing required setting")
    return resolved


def _check_setting_value(
    value: str | int | bool, field: SettingFieldSchema
) -> str | int | bool:
    if field.type is SettingFieldType.STRING:
        if type(value) is not str:
            raise ValueError("invalid setting value")
        if field.min_length is not None and len(value) < field.min_length:
            raise ValueError("invalid setting value")
        if field.max_length is not None and len(value) > field.max_length:
            raise ValueError("invalid setting value")
        return value
    if field.type is SettingFieldType.INTEGER:
        if type(value) is not int:
            raise ValueError("invalid setting value")
        if field.minimum is not None and value < field.minimum:
            raise ValueError("invalid setting value")
        if field.maximum is not None and value > field.maximum:
            raise ValueError("invalid setting value")
        return value
    if field.type is SettingFieldType.BOOLEAN:
        if type(value) is not bool:
            raise ValueError("invalid setting value")
        return value
    if type(value) is not str or value not in field.choices:
        raise ValueError("invalid setting value")
    return value


def reject_block_type_cycles(definitions: dict[str, BlockDefinition]) -> None:
    """Reject recursive allowed_blocks graphs across a catalog."""

    gray: set[str] = set()
    black: set[str] = set()

    def visit(node: str) -> None:
        gray.add(node)
        definition = definitions.get(node)
        if definition is None:
            return
        for nested in definition.allowed_blocks:
            if nested not in definitions:
                continue
            if nested in gray:
                raise ValueError("recursive block nesting")
            if nested not in black:
                visit(nested)
        gray.remove(node)
        black.add(node)

    for type_id in definitions:
        if type_id not in black:
            visit(type_id)


BlockInstance.model_rebuild()
SectionInstance.model_rebuild()
PageTemplate.model_rebuild()
