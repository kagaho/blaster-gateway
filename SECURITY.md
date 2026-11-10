# Security and publication boundary

[Security review](docs/security-review.md) · [Blaster administration guide](docs/administration.md)

Report a suspected credential exposure privately to the repository owner. Do not include secret values, private keys, certificate metadata, customer prompts, or live deployment details in a public issue. Use a private reporting channel agreed with the owner before transmitting evidence.

All supplied credentials are placeholders; usable keys must be generated and stored outside the repository. The renderer rejects placeholder values, root Vault policies, and remote HTTP Vault addresses. Generated APISIX output is a sensitive plaintext runtime artifact and must remain private.

Run the publication checks before each release:

```bash
python3 tools/security_scan.py
gitleaks dir . --redact=100
gitleaks git . --log-opts='--all' --redact=100
```

The custom scanner inspects publishable files and every reachable Git blob. Independent Gitleaks scanning complements its checks. Neither scan proves a running deployment is secure or revokes credentials that existed in another repository.

No deployment certificates, certificate metadata, Vault initialization records, unseal/recovery material, or credential-bearing source Git history are included. Ephemeral test TLS material is generated outside the repository and deleted after validation.

Publishing requires owner authorization and clean scans. The checked-in examples are public-source material; actual deployments, credentials, certificates, and generated runtime state remain private.
