# Contributing

Keep the README focused on the system's purpose and architecture. Put operating procedures in the [Blaster administration guide](docs/administration.md), and distinguish historical reports from new observations.

Review route and consumer changes as access-control changes. Every new service needs an explicit consumer allowlist. Keep keys, TLS material, private deployment identifiers, and generated runtime files outside the repository.

Run the local checks:

```bash
python3 -m unittest discover -s tests -v
python3 tools/check_docs.py
python3 tools/security_scan.py
git diff --check
```

With Docker, Python, OpenSSL, and the documented images available, run the isolated integration test:

```bash
python3 -m tools.integration_test
```

It creates disposable containers and a private temporary directory, uses generated credentials, and removes its resources. It does not use the live backends or source deployment. Review [validation](docs/validation.md) for its scope.

The workflow animation is generated with Pillow and DejaVu Sans:

```bash
python3 -m pip install Pillow==11.1.0
python3 tools/generate_diagrams.py
```

Include both static and animated assets when changing the diagram. Contributions to original repository code and documentation use the [MIT license](LICENSE).
