# Source provenance and merge strategy

Two repositories describe one gateway: `BLASTER-MCP-GW` contains NGINX/APISIX configuration and Vault operations; `Blaster2.0` contains the later ACRA-agent and Langfuse integration narrative.

Source heads inspected:

| Source | Commit | Contribution |
| --- | --- | --- |
| BLASTER-MCP-GW | `106b56b12e8580926a144d64f72d6d0d81065bcd` | Routing, API-key gateway, Vault workflow |
| Blaster2.0 | `b052536` | Agent API, observability, migration and operational context |

The consolidation uses a clean history. Original Git objects, live APISIX output, credential defaults, certificate files and metadata, Vault initialization/unseal data, session state, and machine-specific operator notes are not imported. Neither original repository is modified.

The source tags `v2.0.1` and `v2.1.0` both resolve to `1f5b9577ffff9609f037e94016fc5273dac838e7`; `v2.2.0` resolves to `91b6e3c25987eb2a5be4a6af4e2ffd882155d1e5`. Tag labels and file contents do not always agree about Vault availability; the later head contains the fuller Vault implementation. The new history records that distinction rather than inventing a missing implementation.

`source/v2.0.1`, `source/v2.1.0`, and `source/v2.2.0` tag sanitized milestone notes on archive branches. They are documentation reconstructions, not deployable copies of the original snapshots. New `v1.0.0`, `v1.1.0`, and `v1.1.1` tags version this consolidated repository independently. Main contains the publication edition; the original review candidate remains available at v1.1.0.
