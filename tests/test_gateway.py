"""Security-relevant renderer invariants; no live credentials or production services."""
import json
import os
from pathlib import Path
import secrets
import tempfile
import unittest
from unittest.mock import patch

import yaml
from tools import render_config as renderer
from tools import security_scan as scanner

ROOT = Path(__file__).resolve().parents[1]


class RendererTests(unittest.TestCase):
    def setUp(self):
        self.manifest = yaml.safe_load((ROOT / "config/routes.yml").read_text())
        self.keys = {name: secrets.token_urlsafe(48) for name in self.manifest["consumers"]}

    def test_every_route_requires_authentication_and_explicit_consumer_scope(self):
        config = renderer.build_config(self.manifest, self.keys)
        self.assertEqual(len(config["routes"]), 8)
        for route in config["routes"]:
            self.assertTrue(route["plugins"]["key-auth"]["hide_credentials"])
            self.assertTrue(route["plugins"]["consumer-restriction"]["whitelist"])
        agent = next(r for r in config["routes"] if r["id"] == "agent")
        self.assertEqual(agent["plugins"]["consumer-restriction"]["whitelist"], ["agent-service"])

    def test_legacy_inference_alias_has_priority_but_no_authentication_bypass(self):
        routes = {r["id"]: r for r in renderer.build_config(self.manifest, self.keys)["routes"]}
        self.assertGreater(routes["legacy-inference-mcp"]["priority"], routes["legacy-inference"]["priority"])
        self.assertEqual(routes["legacy-inference-mcp"]["plugins"]["key-auth"], routes["inference"]["plugins"]["key-auth"])

    def test_refuses_placeholder_short_or_duplicate_keys(self):
        for bad in ["XXXXXX", "XXXXXX" * 10, "short"]:
            with self.subTest(case=len(bad)), self.assertRaises(ValueError):
                renderer.build_config(self.manifest, {**self.keys, "demo-user": bad})
        key = secrets.token_urlsafe(48)
        with self.assertRaises(ValueError):
            renderer.build_config(self.manifest, dict.fromkeys(self.keys, key))

    def test_missing_consumer_or_undefined_acl_is_rejected(self):
        with self.assertRaises(ValueError):
            renderer.build_config(self.manifest, {})
        self.manifest["services"]["agent"]["allowed_consumers"] = ["unknown-user"]
        with self.assertRaises(ValueError):
            renderer.build_config(self.manifest, self.keys)

    def test_atomic_file_is_private_and_has_standalone_terminator(self):
        with tempfile.TemporaryDirectory() as temp:
            directory = Path(temp) / "apisix"
            renderer.write_config(renderer.build_config(self.manifest, self.keys), directory)
            file = directory / "apisix.yaml"
            self.assertEqual(file.stat().st_mode & 0o777, 0o600)
            self.assertEqual(directory.stat().st_mode & 0o777, 0o700)
            self.assertTrue(file.read_text().endswith("#END\n"))
            self.assertEqual(yaml.safe_load(file.read_text())["consumers"][0]["username"], "demo-user")

    def test_back_to_back_updates_advance_the_watcher_version(self):
        with tempfile.TemporaryDirectory() as temp:
            directory = Path(temp) / "apisix"
            config = renderer.build_config(self.manifest, self.keys)
            renderer.write_config(config, directory)
            before = int((directory / "apisix.yaml").stat().st_mtime)
            renderer.write_config(config, directory)
            self.assertGreater(int((directory / "apisix.yaml").stat().st_mtime), before)

    def test_credential_file_inside_repository_is_refused(self):
        with self.assertRaises(ValueError):
            renderer.private_file(ROOT / ".env.example")

    def test_group_readable_external_credential_file_is_refused(self):
        with tempfile.TemporaryDirectory() as temp:
            p = Path(temp) / "credential.txt"
            p.write_text("XXXXXX")
            p.chmod(0o644)
            with self.assertRaises(ValueError):
                renderer.private_file(p)

    def test_non_loopback_http_vault_is_refused_before_network(self):
        with patch.object(renderer, "urlopen") as fetch:
            with self.assertRaises(ValueError):
                renderer.vault_keys("http://192.168.15.10:8200", "XXXXXX", [])
            fetch.assert_not_called()

    def test_root_vault_policy_is_refused_before_secret_read(self):
        import io
        response = io.BytesIO(json.dumps({"data": {"policies": ["root"]}}).encode())
        with patch.object(renderer, "urlopen", return_value=response) as fetch:
            with self.assertRaises(ValueError):
                renderer.vault_keys("http://127.0.0.1:18200", "XXXXXX", ["demo-user"])
            self.assertEqual(fetch.call_count, 1)

    def test_generated_yaml_does_not_include_bearer_forwarding(self):
        for route in renderer.build_config(self.manifest, self.keys)["routes"]:
            self.assertIn("Authorization", route["plugins"]["proxy-rewrite"]["headers"]["remove"])


class ScannerTests(unittest.TestCase):
    def test_source_literal_is_reported_without_value(self):
        value = secrets.token_urlsafe(48).encode()
        findings = scanner.findings_for("example.py", value, [value])
        self.assertEqual(findings, ["source-credential-match"])
        self.assertNotIn(value.decode(), json.dumps(findings))

    def test_certificate_material_and_files_are_rejected(self):
        data = b"-----BEGIN " + b"CERTIFICATE-----"
        self.assertIn("pem-material", scanner.findings_for("example.txt", data))
        self.assertIn("forbidden-file", scanner.findings_for("example.crt", b""))

    def test_fictional_topology_is_accepted(self):
        self.assertEqual(scanner.findings_for("example.md", b"192.168.15.10 192.168.15.1 127.0.0.1"), [])


if __name__ == "__main__":
    unittest.main()
