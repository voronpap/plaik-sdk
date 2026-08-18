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
- scaffolding and developer tooling;
- public examples required to author PLAIK extensions.

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

## License

Apache License 2.0.
