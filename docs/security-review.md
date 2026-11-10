# Security review and publication preparation

[Project overview](../README.md) · [Blaster administration guide](administration.md) · [Validation record](validation.md)

Scope: both source repositories' checked-out files and release references, the consolidated implementation, generated-file boundaries, and every reachable Git blob in this new repository. Values identified as potential source credentials were kept only in a private temporary comparison list and were never copied into this repository.

## Findings and treatment

| Finding in the source material | Significance | Consolidated treatment |
| --- | --- | --- |
| Hardcoded API-key defaults and a weak shared bearer-token example | A copied client or published history can expose usable access | Defaults and original clients are excluded; credentials must be external and non-placeholder |
| Legacy RAG paths bypassed authentication | The protected gateway could be bypassed using another public path | Every retained service alias traverses key authentication and service ACLs |
| All consumers were accepted on every protected route | Authentication did not establish service-level authorization | Explicit per-service allowlists; agent access restricted to its service account |
| Automatic root-token and unseal-key reads from initialization files | Routine rendering had unnecessary administrative access | Manual Vault custody/lifecycle; read-only policy; renderer rejects root policy |
| TLS verification disabled in client examples | Clients could not authenticate the endpoint | Maintained procedures use normal verification and external CA trust |
| Runtime APISIX YAML contains usable plaintext keys | Vault storage does not remove runtime credential exposure | Ignored runtime output, owner-only permissions, read-only container mount, restricted host access |
| Configuration and operational history mixed with credentials or deployment metadata | Redacting only the latest working tree would leave recoverable data | New clean Git history; only sanitized milestone notes retained |
| APISIX, Vault, GUI, and backend ports had separate exposure paths | Direct host ports can bypass the intended policy boundary | No APISIX host port, Vault loopback-only, UI root unpublished; external backend firewall still required |
| Authentication mode copied from incomplete templates | Switching could drop routes or activate placeholders | No blind authentication-switch script or deployable incomplete OIDC template |

These changes apply only to the new local repository. The original repositories and deployments were not changed. Rotate any source credential that was real or reused; sanitization does not revoke it or remove it from previously published repositories, clones, backups, or caches.

## Vault and certificate audit

The new `vault/` tree contains only a local administration server configuration and a read-only policy. It contains no initialization records, unseal/recovery data, token files, certificate files, private/public key blocks, signing requests, certificate subjects, issuer information, serials, fingerprints, or copied validity dates.

Deployment TLS files live in an operator-supplied directory outside this repository. Public config names the expected mount paths only. The integration test creates short-lived test TLS material outside Git, prints no certificate information, and deletes it with its temporary directory; it is unrelated to deployment or Vault identity.

Forbidden certificate/key file extensions and PEM encodings are checked across the publishable tree and reachable Git blobs. Generated diagram assets are created from code and contain no imported screenshots or deployment metadata.

## History and versioning boundary

Original `.git` directories, session files, generated APISIX data, live certificate directories, initialization data, and backups are not imported. Original source tags are represented by clearly labeled sanitized notes on archive branches. New release tags point only into this clean repository.

The private exact-match scan compares candidate source credential literals against both new source files and every reachable Git blob. Gitleaks independently scans the filesystem and complete reachable Git history with redacted reporting. See [validation](validation.md) for recorded outcomes and tools.

## Runtime permissions and exposure

The selected APISIX image normally uses its own non-root UID. Private rendered files belong to the host operator. The reviewed startup wrapper briefly runs with container root to prepare writable APISIX state, then uses `setpriv` to drop to the non-root runtime-directory owner before starting APISIX. Runtime directories with a root owner or primary group are rejected. It does not weaken the credential file's mode to make it readable.

This bootstrap is a tradeoff to review for the deployment's container/user-namespace model. It is not a fully rootless container guarantee. The runtime directory owner must map correctly into the container. Docker/host administrators can still inspect credentials and process memory.

Both NGINX and APISIX access-log formats omit query strings and authentication headers. APISIX private log files stay inside its container; inspect them with the administration commands rather than publishing raw diagnostics. Error logs can still contain sensitive operational context.

The supplied local Vault profile uses HTTP only over its loopback administration port and isolated container network. TLS at NGINX does not encrypt a separate Vault connection. Remote Vault must use HTTPS; the renderer enforces this. A production Vault deployment needs a separately reviewed storage, unseal/authentication, audit, backup, and transport design.

## Remaining boundaries

- External backend listeners and firewall rules are not controlled by this repository. Prevent direct untrusted access and add backend authentication/TLS when leaving the single-host boundary.
- A previously rendered key remains active while Vault is sealed or a subsequent render fails. Revocation requires successful rendering and verification; rollback must not restore revoked keys.
- The root Langfuse GUI and an OIDC/Okta deployment are deliberately not enabled. Their authentication and application dependencies need a separate implementation/review.
- Dependency/image version tags were verified against upstream registries. This review is not a complete operating-system/container vulnerability assessment, penetration test, or production certification.
- Real backend integration and the operator's actual CA/certificate configuration remain outside isolated mock-backend tests.

## Release review

Review the [README](../README.md), [administration guide](administration.md), source provenance, runtime permission model, route/consumer policy, scan results, and branches/tags. Confirm that source credentials have been rotated where necessary and that historical route names and architecture descriptions are appropriate to share.

Public-source release does not deploy the gateway or publish its private runtime state. Repeat the publication scans for subsequent releases and keep deployment credentials outside Git.
