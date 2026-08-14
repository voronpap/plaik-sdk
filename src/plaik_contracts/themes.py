"""Web theme manifest contracts."""

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from .packages import PACKAGE_ID_PATTERN, SEMVER_PATTERN


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

    @model_validator(mode="after")
    def reject_self_parent(self) -> "ThemeManifest":
        if self.parent == self.id:
            raise ValueError("theme cannot inherit from itself")
        return self
