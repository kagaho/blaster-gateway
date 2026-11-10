# Changelog

## v1.1.1 — 2026-11-09

Publication preparation for the reviewed consolidated source.

- Replace local-only status text with durable release and deployment-boundary documentation.
- Retain the reviewed v1.1.0 implementation and sanitized source milestone history.
- Repeat publication scans before pushing the public-source edition.

## v1.1.0 — 2026-11-09

Consolidated portfolio and security-review candidate, prepared locally for owner review.

- Merge the gateway implementation and later platform narrative into one top-down README.
- Add static/animated workflows, architecture and lifecycle diagrams, and the Blaster administration guide.
- Add one Compose deployment, canonical APIs, protected legacy aliases, and per-service consumer allowlists.
- Replace root-token rendering with scoped Vault access or private external credential files.
- Reject placeholder/duplicate credentials, preserve atomic private runtime output, and keep TLS verification enabled.
- Remove imported credential defaults, deployment IPs, certificate metadata, session data, and unsafe source Git objects.
- Use fictional host `192.168.15.10`, gateway `192.168.15.1`, and subnet `192.168.15.0/24` in examples.
- Add security-focused tests, real disposable gateway integration, documentation checks, full-history scans, CI configuration, and MIT licensing.

Source repositories and live services are unchanged. This tag preserves the local review milestone preceding the publication edition.

## v1.0.0 — 2026-11-09

Clean consolidation baseline with license, exclusions, and source provenance. Does not import either source repository's Git objects.

## Preserved source milestones

- `source/v2.0.1`: sanitized note for the APISIX migration milestone.
- `source/v2.1.0`: sanitized directory-mount/reload milestone; original tag shares its commit with v2.0.1.
- `source/v2.2.0`: sanitized Vault-transition milestone; fuller Vault scripts appear at a later source head.

These source tags represent documentation reconstructions on archive branches, not runnable original snapshots. See [provenance](docs/provenance.md).
