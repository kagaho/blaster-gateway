"""Generate an API key into a new owner-only file outside the repository."""
import argparse
import os
from pathlib import Path
import secrets

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output", type=Path)
    path = parser.parse_args().output.resolve()
    if path.is_relative_to(ROOT):
        parser.error("Choose a private path outside this repository")
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, "w") as stream:
        stream.write(secrets.token_urlsafe(48))
    print("Key created in the selected private file; value not displayed.")


if __name__ == "__main__":
    main()
