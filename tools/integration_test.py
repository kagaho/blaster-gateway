"""Test APISIX auth/rewrites and NGINX syntax in disposable containers with random keys."""
import json
from pathlib import Path
import secrets
import subprocess
import tempfile
import time
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen
import uuid

import yaml
from tools.render_config import build_config, write_config

ROOT = Path(__file__).resolve().parents[1]
MOCK = '''from http.server import BaseHTTPRequestHandler, HTTPServer
import json
class Handler(BaseHTTPRequestHandler):
 def do_GET(self):
  body=json.dumps({"path":self.path,"credential_forwarded":bool(self.headers.get("apikey") or self.headers.get("Authorization"))}).encode()
  self.send_response(200);self.send_header("Content-Type","application/json");self.send_header("Content-Length",str(len(body)));self.end_headers();self.wfile.write(body)
 do_POST=do_GET
 def log_message(self,*args):pass
HTTPServer(("0.0.0.0",8080),Handler).serve_forever()
'''


def main():
    suffix = uuid.uuid4().hex[:10]
    network, backend, gateway = ["blaster-review-" + suffix + end for end in ("", "-mock", "-apisix")]
    def docker(*args, check=True):
        result = subprocess.run(["docker", *args], capture_output=True, text=True)
        if check and result.returncode:
            raise RuntimeError("Docker command failed: " + " ".join(args[:2]))
        return (result.stdout + result.stderr).strip() if args[0] == "logs" else result.stdout.strip()
    keys = {name: secrets.token_urlsafe(48) for name in ("demo-user", "agent-service")}
    count = 0
    try:
        docker("network", "create", network)
        with tempfile.TemporaryDirectory(prefix="blaster-gateway-review-") as temp:
            temp = Path(temp)
            manifest = yaml.safe_load((ROOT / "config/routes.yml").read_text())
            config = build_config(manifest, keys)
            for upstream in config["upstreams"]:
                upstream["nodes"] = {backend + ":8080": 1}
            write_config(config, temp / "runtime")
            docker("run", "-d", "--name", backend, "--network", network,
                   "python:3.12-slim", "python", "-c", MOCK)
            docker("run", "-d", "--name", gateway, "--network", network,
                   "--security-opt", "no-new-privileges:true", "--user", "0:0", "--entrypoint", "/bin/sh", "-p", "127.0.0.1::9080", "-v", f"{ROOT / 'gateway/apisix.yml'}:/usr/local/apisix/conf/config.yaml:ro",
                   "-v", f"{temp / 'runtime'}:/usr/local/apisix/conf/rendered:ro",
                   "-v", f"{ROOT / 'gateway/start-apisix.sh'}:/usr/local/bin/blaster-start:ro",
                   "apache/apisix:3.19.0-debian", "/usr/local/bin/blaster-start")
            try:
                port = docker("port", gateway, "9080/tcp").rsplit(":", 1)[-1]
            except RuntimeError:
                logs = docker("logs", gateway, check=False)
                for value in keys.values(): logs = logs.replace(value, "XXXXXX")
                raise RuntimeError("Gateway startup failed: " + logs[:4500]) from None
            base = "http://127.0.0.1:" + port
            def call(path, key=None, method="GET"):
                headers = {"apikey": key, "Authorization": "Bearer XXXXXX"} if key else {}
                try:
                    with urlopen(Request(base + path, headers=headers, method=method), timeout=3) as response:
                        return response.status, json.load(response)
                except HTTPError as exc:
                    return exc.code, None
            deadline = time.monotonic() + 12
            while True:
                try:
                    if call("/api/inference/v1/models")[0] == 401:
                        break
                except (URLError, OSError):
                    pass
                if time.monotonic() > deadline:
                    logs = docker("exec", gateway, "tail", "-n", "20", "/usr/local/apisix/logs/error.log", check=False) + docker("logs", gateway, check=False)[-1000:]
                    for value in keys.values():
                        logs = logs.replace(value, "XXXXXX")
                    raise RuntimeError("Disposable gateway failed readiness: " + logs[:4500])
                time.sleep(0.5)
            process_status = docker("exec", gateway, "cat", "/proc/1/status")
            fields = dict(line.split(":", 1) for line in process_status.splitlines() if ":" in line)
            assert int(fields["Uid"].split()[0]) != 0, "APISIX must serve as non-root"
            assert int(fields["CapEff"].strip(), 16) == 0, "APISIX retained effective capabilities"
            assert fields["NoNewPrivs"].strip() == "1", "Privilege escalation guard missing"
            count += 1
            for route in manifest["routes"]:
                path = route["uri"].replace("*", "v1/models")
                method = route.get("methods", ["GET"])[0]
                for credential in [None, "XXXXXX"]:
                    assert call(path, credential, method)[0] == 401, "Unauthenticated alias was not denied"
                    count += 1
                consumer = "agent-service" if route["service"] == "agent" else "demo-user"
                status, body = call(path, keys[consumer], method)
                assert status == 200 and not body["credential_forwarded"], "Authorized request or credential stripping failed"
                expected = route.get("target", "/v1/models")
                assert body["path"] == expected, "Backend rewrite failed"
                count += 1
            assert call("/api/agent/health", keys["demo-user"])[0] == 403
            assert call("/")[0] == 404
            count += 2
            # Validate revocation with the real standalone watcher, without restarting APISIX.
            previous = keys["demo-user"]
            keys["demo-user"] = secrets.token_urlsafe(48)
            config = build_config(manifest, keys)
            for upstream in config["upstreams"]:
                upstream["nodes"] = {backend + ":8080": 1}
            write_config(config, temp / "runtime")
            deadline = time.monotonic() + 10
            while call("/api/inference/v1/models", previous)[0] != 401:
                if time.monotonic() > deadline:
                    raise AssertionError("Old key still accepted after standalone reload window")
                time.sleep(0.3)
            assert call("/api/inference/v1/models", keys["demo-user"])[0] == 200
            count += 2
            # Ephemeral test TLS material stays outside Git; no certificate information is printed.
            certs = temp / "tls"; certs.mkdir()
            result = subprocess.run(["openssl", "req", "-x509", "-nodes", "-newkey", "rsa:2048", "-days", "1",
                                     "-keyout", str(certs / "tls.key"), "-out", str(certs / "tls.crt"),
                                     "-subj", "/CN=localhost"], capture_output=True)
            assert result.returncode == 0
            docker("run", "--rm", "--network", network, "--add-host", "apisix:127.0.0.1",
                   "-v", f"{ROOT / 'gateway/nginx.conf'}:/etc/nginx/nginx.conf:ro", "-v", f"{certs}:/run/blaster-tls:ro",
                   "nginx:1.30.6", "nginx", "-t")
            count += 1
    finally:
        docker("rm", "-f", gateway, backend, check=False)
        docker("network", "rm", network, check=False)
    print(json.dumps({"checks_passed": count, "production_services_contacted": False,
                      "temporary_credentials_and_test_tls_retained": False}))


if __name__ == "__main__":
    main()
