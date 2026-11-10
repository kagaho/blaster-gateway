# Validation record

[Project overview](../README.md) · [Security review](security-review.md) · [Administration](administration.md)

Validation uses generated credentials and disposable test services. Neither source deployment nor its backends are contacted. Production TLS and Vault identity material are not used.

## Local checks

```bash
python3 -m pip install -r requirements.txt
python3 -m unittest discover -s tests -v
python3 tools/check_docs.py
python3 tools/security_scan.py
BLASTER_TLS_DIR=/tmp/operator-managed-tls docker compose --profile administration config --quiet
git diff --check
```

The **14 renderer/scanner tests** pass locally. The suite covers route authentication and consumer scope, legacy route priority, placeholder/duplicate/missing credentials, atomic file permissions, rejected in-repository or broadly readable secret files, rejected remote HTTP Vault, and rejected root Vault policy.

The custom security scanner reports file/object locations and rule names without values. It scans publishable files plus all reachable Git blobs, so an archive branch is not omitted simply because it is not checked out.

## Independent secret detection

Gitleaks **v8.30.1**, downloaded from its official release and checked against the published SHA-256 checksum, is used with full redaction:

```bash
gitleaks dir . --redact=100 --report-format json --report-path /tmp/blaster-working-scan.json
gitleaks git . --log-opts='--all' --redact=100 --report-format json --report-path /tmp/blaster-history-scan.json
```

A private comparison list of source credential candidates provides an additional exact-match check. That temporary list and raw scan reports are not committed. No finding should be copied into public documentation with its secret value.

## Disposable gateway integration

```bash
python3 -m tools.integration_test
```

The test starts a temporary mock backend and the actual selected APISIX image, using a random Docker network, loopback-only ephemeral port, and fresh in-memory consumer keys. It exercises:

- Missing/invalid key rejection on every canonical and legacy service route.
- Authorized requests and expected URI rewrites across all configured routes.
- Removal of client authentication headers before reaching the backend.
- Denial of demo-user access to the agent service.
- Non-root APISIX PID 1, no effective capabilities, and enabled no-new-privileges.
- No unauthenticated root GUI route.
- Atomic key rotation, old-key rejection, and new-key acceptance without restarting APISIX.
- NGINX syntax validation with ephemeral test-only TLS material outside the repository.

The real-container run passed **30 checks**. The test removes its containers, network, private temporary runtime file, generated credentials, and test TLS files. It must not be pointed at a production backend. Its fixed mock response does not establish model/agent correctness, RAG quality, streaming performance, or application latency.

## Selected image versions

| Component | Version used for review |
| --- | --- |
| NGINX | `nginx:1.30.6` |
| APISIX | `apache/apisix:3.19.0-debian` |
| Optional local Vault | `hashicorp/vault:2.0.3` |

The image tags were confirmed to exist in the upstream registry. The NGINX version was checked against the [upstream security advisory page](https://nginx.org/en/security_advisories.html). Version tags are not immutable digests; record deployment digests and perform a current image vulnerability review before using the stack beyond this local review scope.

The Vault image's live initialization/authentication lifecycle is not exercised by the gateway mock test; renderer policy/transport checks use controlled test responses. No current production availability or policy state is inferred from the old source narratives.

## Publication state

Local checks and scans are repeated after the release commit so all new reachable blobs are included. GitHub Actions is provided for future use; no remote CI result is claimed because this repository is not published. Review the final local completion report for the check counts and release references.
