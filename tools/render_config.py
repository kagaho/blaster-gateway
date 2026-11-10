"""Build standalone APISIX config from nonsecret routes and externally managed keys."""
import argparse
import json
import os
from pathlib import Path
import re
import stat
import tempfile
import time
from urllib.error import HTTPError, URLError
from urllib.parse import quote, urlsplit
from urllib.request import Request, urlopen

import yaml

ROOT = Path(__file__).resolve().parents[1]


def private_file(path):
    path = Path(path).resolve()
    if path.is_relative_to(ROOT):
        raise ValueError("Credential files must remain outside this repository")
    if path.stat().st_mode & (stat.S_IRWXG | stat.S_IRWXO):
        raise ValueError("Credential files must be private to their owner (mode 600)")
    return path.read_text().strip()


def vault_keys(address, token, consumers):
    parsed = urlsplit(address)
    if parsed.username or parsed.password or parsed.query or parsed.fragment:
        raise ValueError("Vault URL must not contain credentials, query parameters, or fragments")
    if not (parsed.scheme == "https" or parsed.scheme == "http" and parsed.hostname in ("localhost", "127.0.0.1", "::1")):
        raise ValueError("Remote Vault requires HTTPS; HTTP is permitted only on loopback")
    def fetch(path):
        req = Request(address.rstrip("/") + "/v1/" + path, headers={"X-Vault-Token": token})
        try:
            with urlopen(req, timeout=15) as response:
                return json.load(response)
        except (HTTPError, URLError, OSError, ValueError):
            raise ValueError("Vault request failed; check availability and scoped reader permissions") from None
    if "root" in fetch("auth/token/lookup-self")["data"].get("policies", []):
        raise ValueError("Root Vault tokens are not accepted; use the scoped reader policy")
    return {name: fetch("apisix/data/consumers/" + quote(name, safe=""))["data"]["data"]["key"] for name in consumers}


def build_config(manifest, keys):
    names = manifest["consumers"]
    if not names or len(names) != len(set(names)):
        raise ValueError("Consumer names must be nonempty and unique")
    if set(keys) != set(names):
        raise ValueError("Credential set must exactly match the consumer manifest")
    for name in names:
        if not re.fullmatch(r"[a-z][a-z0-9-]{0,63}", name):
            raise ValueError("Invalid consumer name")
        key = keys[name]
        if not isinstance(key, str) or not re.fullmatch(r"[A-Za-z0-9._~+/=-]{32,256}", key) or any(p in key.lower() for p in ["xxxxxx", "replace", "changeme"]):
            raise ValueError("API keys must be unique, non-placeholder values of at least 32 characters")
    if len(set(keys.values())) != len(names):
        raise ValueError("API keys must be unique")
    services = manifest["services"]
    for service in services.values():
        if not service["allowed_consumers"] or not set(service["allowed_consumers"]).issubset(names):
            raise ValueError("Each service needs an explicit valid consumer allowlist")
        if not re.fullmatch(r"host\.docker\.internal:\d{2,5}", service["node"]):
            raise ValueError("This single-host profile accepts only explicit host-gateway backend ports")
    routes, ids = [], set()
    for route in manifest["routes"]:
        if route["id"] in ids:
            raise ValueError("Route IDs must be unique")
        ids.add(route["id"])
        service = services[route["service"]]
        rewrite = {"headers": {"remove": ["Authorization"]}}
        if "prefix" in route:
            if route["uri"] != route["prefix"] + "*":
                raise ValueError("Prefix route must match its public URI")
            rewrite["regex_uri"] = ["^" + re.escape(route["prefix"]) + "(.*)$", "/$1"]
        else:
            rewrite["uri"] = route["target"]
        item = {"id": route["id"], "uri": route["uri"], "priority": len(route.get("prefix", route["uri"])),
                "upstream_id": route["service"], "plugins": {
                    "key-auth": {"header": "apikey", "hide_credentials": True},
                    "consumer-restriction": {"whitelist": service["allowed_consumers"]},
                    "proxy-rewrite": rewrite}}
        if route.get("methods"):
            item["methods"] = route["methods"]
        routes.append(item)
    return {"routes": routes,
            "upstreams": [{"id": name, "type": "roundrobin", "nodes": {service["node"]: 1},
                           "timeout": {"connect": 10, "send": 300, "read": 300}} for name, service in services.items()],
            "consumers": [{"username": name, "plugins": {"key-auth": {"key": keys[name]}}} for name in names]}


def write_config(config, directory):
    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=True, mode=0o700)
    os.chmod(directory, 0o700)
    # A directory mount lets atomic replacement appear inside the APISIX container.
    fd, temp = tempfile.mkstemp(prefix=".apisix-", dir=directory)
    try:
        with os.fdopen(fd, "w") as stream:
            yaml.safe_dump(config, stream, sort_keys=False)
            stream.write("#END\n")
            stream.flush()
            os.fsync(stream.fileno())
        destination = directory / "apisix.yaml"
        # APISIX observes second-resolution mtimes: rapid rotations must still differ.
        previous = int(destination.stat().st_mtime) if destination.exists() else 0
        version_time = max(int(time.time()), previous + 1)
        os.utime(temp, (version_time, version_time))
        os.replace(temp, destination)
    finally:
        if os.path.exists(temp):
            os.unlink(temp)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--secrets-file", type=Path, help="Private external JSON consumer-to-key mapping")
    group.add_argument("--vault-token-file", type=Path, help="Private external scoped reader token")
    parser.add_argument("--vault-address", default="http://127.0.0.1:18200")
    args = parser.parse_args()
    try:
        manifest = yaml.safe_load((ROOT / "config/routes.yml").read_text())
        keys = (json.loads(private_file(args.secrets_file)) if args.secrets_file else
                vault_keys(args.vault_address, private_file(args.vault_token_file), manifest["consumers"]))
        write_config(build_config(manifest, keys), ROOT / "runtime/apisix")
    except (ValueError, KeyError, OSError, TypeError):
        parser.exit(1, "Render failed: check private credential files, manifest, and Vault reader access. No configuration was published.\n")
    print("APISIX runtime configuration updated; no credentials printed.")


if __name__ == "__main__":
    main()
