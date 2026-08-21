# PLAIK SDK

Public extension-development surface for **PLAIK**.

This repository owns the stable interfaces that third-party modules, integrations, themes and packs may depend on. It must remain usable without importing private PLAIK Core implementation details.

## Scope

- public contracts and typed protocol surfaces;
- package manifest and schema definitions, including capability `provides` / `requires`;
- Theme API v1 presentation contracts (`theme_api`, dotted UI slots, `UiState`, page/section/block composition, settings/presets/revisions);
- domain-neutral kernel refs (`ScopeRef`, `ResourceRef`, `SecretReference`, `ConnectionRef`, `EventEnvelope`, `HealthIssue`, optional `ActionRef`);
- `ExtensionRuntime.health` (`HealthReporter`) for package-owned `HealthIssue` reports, not process `/health`;
- SDK helpers;
- compatibility validators;
- scaffolding and developer tooling (`plaik-sdk new|validate|test|build|inspect`);
- public examples required to author PLAIK extensions.

A package must depend only on released `plaik-sdk`. It must not import `plaik_core`.

```bash
plaik-sdk new module catalog
plaik-sdk validate catalog
plaik-sdk test catalog
plaik-sdk build catalog
plaik-sdk inspect catalog
```

The operator CLI in PLAIK exposes the same loop as `plaik dev` and `plaik package`.

Module and integration slot templates live under package `web/`. Manifest `web.slots[].template` and `web.hooks[].template` are relative to that directory (for example `slot.html`). Do not use a package-root `templates/` path for those fields; Core install staging resolves `{package}/web/{template}`. Theme packages still use Theme API `templates/` for layouts, sections and pages.

`SecretReference` is a pointer (`provider`, `key`, `version`) with a redacted repr. It is not a secret value. Capability ids are shared contract names, not provider-package namespaces. Packs may require capabilities and must not provide them.

## Out of scope

- Core runtime implementation — `voronpap/plaik`;
- official business packages/themes/integrations — `voronpap/plaik-packages`;
- internal acceptance, regression and security tests;
- agent instructions, CI control-plane, deployment and production evidence.

Internal validation lives in the private `plaik-internal` repository.

## Dependency direction

```text
plaik-sdk
   ├──> plaik
   └──> plaik-packages
```

Consumers depend on released SDK artifacts with explicit compatibility ranges. No Git submodules are used for normal product composition.

PLAIK runtime **0.4.x** requires `plaik-sdk>=0.4.0,<0.5.0`. Official 0.4 modules depend on this SDK; they must not import `plaik_core`. GitHub Release `v0.4.0` publishes the 0.4.0 SDK wheel.

## License

Apache License 2.0.
