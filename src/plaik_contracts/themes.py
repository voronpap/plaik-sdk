"""Web theme manifest contracts."""

from typing import Literal
import re

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from .packages import PACKAGE_ID_PATTERN, SEMVER_PATTERN
from .theme_api import (
    SLOT_ID_PATTERN,
    require_public_slot_id,
    require_supported_theme_api,
    slot_ids_are_unique,
)
from .theme_composition import (
    COMPOSITION_ID_PATTERN,
    MAX_DECLARED_BLOCK_TYPES,
    MAX_DECLARED_PAGE_TEMPLATES,
    MAX_DECLARED_SECTION_TYPES,
    require_composition_id,
)


class ThemeAssets(BaseModel):
    model_config = ConfigDict(extra="forbid")

    css: list[str] = Field(default_factory=list)
    js: list[str] = Field(default_factory=list)


class ThemeManifest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str = Field(pattern=PACKAGE_ID_PATTERN)
    type: Literal["theme"] = "theme"
    version: str = Field(pattern=SEMVER_PATTERN)
    name: str = Field(min_length=1, max_length=120)
    core: str
    parent: str | None = Field(default=None, pattern=PACKAGE_ID_PATTERN)
    layouts: list[str] = Field(min_length=1)
    assets: ThemeAssets
    hooks: list[str] = Field(default_factory=list)
    theme_api: int | None = None
    slots: list[str] = Field(default_factory=list, max_length=256)
    page_templates: list[str] = Field(
        default_factory=list, max_length=MAX_DECLARED_PAGE_TEMPLATES
    )
    sections: list[str] = Field(
        default_factory=list, max_length=MAX_DECLARED_SECTION_TYPES
    )
    blocks: list[str] = Field(
        default_factory=list, max_length=MAX_DECLARED_BLOCK_TYPES
    )

    @field_validator("theme_api")
    @classmethod
    def validate_theme_api(cls, value: int | None) -> int | None:
        if value is None:
            return value
        return require_supported_theme_api(value)

    @field_validator("slots")
    @classmethod
    def validate_slot_ids(cls, value: list[str]) -> list[str]:
        slot_ids_are_unique(value)
        for slot_id in value:
            if not re.fullmatch(SLOT_ID_PATTERN, slot_id):
                raise ValueError("invalid slot id")
            require_public_slot_id(slot_id)
        return value

    @field_validator("page_templates", "sections", "blocks")
    @classmethod
    def validate_composition_ids(cls, value: list[str]) -> list[str]:
        if len(value) != len(set(value)):
            raise ValueError("duplicate composition id")
        for item in value:
            if not re.fullmatch(COMPOSITION_ID_PATTERN, item):
                raise ValueError("invalid composition id")
            require_composition_id(item)
        return value

    @model_validator(mode="after")
    def reject_self_parent(self) -> "ThemeManifest":
        if self.parent == self.id:
            raise ValueError("theme cannot inherit from itself")
        if self.slots and self.theme_api is None:
            raise ValueError("theme slots require Theme API v1")
        if (
            self.page_templates or self.sections or self.blocks
        ) and self.theme_api is None:
            raise ValueError("theme composition requires Theme API v1")
        return self
