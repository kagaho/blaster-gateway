"""Scan tracked/untracked publishable files and every reachable Git blob without printing values."""
import argparse
import ipaddress
import json
from pathlib import Path
import re
import subprocess

ROOT = Path(__file__).resolve().parents[1]
ALLOWED_IPS = {"0.0.0.0", "127.0.0.1", "192.168.15.10", "192.168.15.1", "192.168.15.0"}
RULES = {
    "pem-material": re.compile(b"-----BEGIN " + rb"(?:[A-Z ]*PRIVATE KEY|CERTIFICATE|PUBLIC KEY|CERTIFICATE REQUEST)-----"),
    "credential-format": re.compile(rb"(?:hvs\.[A-Za-z0-9_-]{12,}|hvb\.[A-Za-z0-9_-]{12,}|gh[pousr]_[A-Za-z0-9_]{20,}|sk-[A-Za-z0-9_-]{20,}|eyJ[A-Za-z0-9_-]{12,}\.[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+)"),
    "certificate-metadata": re.compile(rb"(?im)^\s*(?:issuer\s*=|subject\s*=|serial\s*number\s*:|sha256\s*fingerprint\s*=)"),
    "embedded-credential": re.compile(rb'(?im)^\s*(?:key|client_secret|password|root_token)\s*:\s*[\x27\"]?([A-Za-z0-9+/=_-]{20,})'),
}
FORBIDDEN_SUFFIXES = {".pem", ".crt", ".cer", ".key", ".p12", ".pfx", ".jks", ".keystore"}


def findings_for(path, data, known=()):
    findings = []
    name = Path(path)
    if name.suffix.lower() in FORBIDDEN_SUFFIXES or name.name in {".env", "init-keys.json", "apisix-token.json"}:
        findings.append("forbidden-file")
    for rule, pattern in RULES.items():
        if pattern.search(data):
            findings.append(rule)
    if any(value and value in data for value in known):
        findings.append("source-credential-match")
    if b"\x00" not in data:
        for match in re.finditer(rb"(?<![\w.])(?:\d{1,3}\.){3}\d{1,3}(?![\w.])", data):
            try:
                ip = str(ipaddress.IPv4Address(match[0].decode()))
            except ValueError:
                continue
            if ip not in ALLOWED_IPS:
                findings.append("non-example-ip")
                break
    return sorted(set(findings))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-blocklist", type=Path, help="Private temporary list of source literals; never printed")
    args = parser.parse_args()
    known = [v.encode() for v in json.loads(args.source_blocklist.read_text())] if args.source_blocklist else []
    def git(*args):
        return subprocess.check_output(["git", *args], cwd=ROOT)
    names = git("ls-files", "--cached", "--others", "--exclude-standard", "-z").decode().split("\0")
    findings, files = [], 0
    for name in sorted(set(names)):
        p = ROOT / name
        if not name or not p.is_file():
            continue
        files += 1
        rules = findings_for(name, p.read_bytes(), known)
        if rules:
            findings.append({"scope": "working-tree", "path": name, "rules": rules})
    objects = 0
    for line in git("rev-list", "--objects", "--all").decode().splitlines():
        oid, _, name = line.partition(" ")
        if git("cat-file", "-t", oid).strip() != b"blob":
            continue
        objects += 1
        rules = findings_for(name, git("cat-file", "blob", oid), known)
        if rules:
            findings.append({"scope": "git-history", "object": oid[:12], "path": name, "rules": rules})
    print(json.dumps({"publishable_files": files, "reachable_blobs": objects, "findings": findings}, indent=2))
    return int(bool(findings))


if __name__ == "__main__":
    raise SystemExit(main())
