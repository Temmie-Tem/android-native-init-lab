#!/usr/bin/env python3
"""Repository boundary check for private device identifiers.

Enforces `docs/operations/PUBLIC_TREE_SANITIZATION_POLICY.md` over the tracked
tree. Host-only; contacts no device and reads nothing outside the repository.

Layers, in order (policy section 5):

  1. known real identifiers          -> fail outright, matched exactly
  2. approved values                 -> subtracted before any judgement
  3. unknown serial-shaped tokens    -> reported for review

The known-identifier list is stored as SHA-256 digests rather than plaintext.
That is self-consistency, not secrecy: it keeps this file from tripping the very
check it implements, and the real values remain in immutable Git history
regardless. Anyone auditing the list can confirm a digest by hashing a candidate.

Exit status is 0 when the tree is clean and 1 when anything is reported.
"""

from __future__ import annotations

import argparse
import hashlib
import re
import subprocess
import sys
from pathlib import Path

# SHA-256 of each maintainer device serial. See the module docstring for why
# these are digests. Lengths are listed separately so an identifier embedded in
# a longer alphanumeric run is still found.
KNOWN_IDENTIFIER_DIGESTS = {
    "7f6dd1b66bdac00e950f3ddb207b7d8b2fca6859c7cdff99a3b96607d111fe46": "DEVICE-A90-01",
    "c5302ccc08374d408ca3ec4df0ef23770d5ecd35ce173b7d150c4316e9a0757b": "DEVICE-S22P-01",
}
KNOWN_IDENTIFIER_LENGTHS = (11,)

# Layer 2. Public aliases and the redaction token contain '-' and so are never
# produced by the tokenizer; they are listed for the reader, not for the match.
APPROVED_VALUES = frozenset(
    {
        "RFCM0000000",              # test fixture, DEVICE-A90-01
        "RFCT0000000",              # test fixture, DEVICE-S22P-01
        "DEVICE-A90-01",
        "DEVICE-S22P-01",
        "REDACTED-DEVICE-SERIAL",
    }
)

# Layer 1 tokenizer: maximal alphanumeric runs. Deliberately independent of the
# layer 3 heuristic, so an exact identifier is caught whatever shape it has.
TOKEN = re.compile(r"[A-Za-z0-9]{8,64}")

# Layer 3 heuristic: a Samsung-style serial is eleven characters beginning with
# 'R' and containing at least one digit.
#
# The match is anchored to a whole token rather than written with \b. A word
# boundary treats '_' as a word character, so \bR[0-9A-Z]{10}\b does not match
# an identifier embedded in a udev path such as
# 'usb-SAMSUNG_SAMSUNG_Android_<serial>-if00', which would let this check report
# a clean tree while an identifier is still present. Policy section 5.4.
SERIAL_SHAPED = re.compile(r"^R[0-9A-Z]{10}$")
HAS_DIGIT = re.compile(r"[0-9]")

SKIP_SUFFIXES = (
    ".png", ".jpg", ".jpeg", ".gif", ".webp", ".ico", ".pdf",
    ".zip", ".gz", ".xz", ".bz2", ".tar", ".img", ".bin", ".so", ".ko",
)


def repo_root() -> Path:
    current = Path(__file__).resolve()
    for parent in current.parents:
        if (parent / ".git").is_dir():
            return parent
    raise RuntimeError(f"could not locate repo root from {current}")


def digest(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def find_known_identifiers(text: str) -> set[str]:
    """Layer 1. Return the labels of any known identifier present in `text`."""
    found: set[str] = set()
    for match in TOKEN.finditer(text):
        token = match.group(0).upper()
        for length in KNOWN_IDENTIFIER_LENGTHS:
            if len(token) < length:
                continue
            for start in range(len(token) - length + 1):
                label = KNOWN_IDENTIFIER_DIGESTS.get(digest(token[start : start + length]))
                if label is not None:
                    found.add(label)
    return found


def find_unknown_candidates(text: str) -> set[str]:
    """Layer 3. Serial-shaped tokens that are neither known nor approved."""
    found: set[str] = set()
    for match in TOKEN.finditer(text):
        token = match.group(0)
        if not SERIAL_SHAPED.match(token) or not HAS_DIGIT.search(token):
            continue
        if token in APPROVED_VALUES:
            continue
        if digest(token) in KNOWN_IDENTIFIER_DIGESTS:
            continue  # already reported by layer 1
        found.add(token)
    return found


def tracked_files(root: Path) -> list[str]:
    result = subprocess.run(
        ["git", "ls-files"], cwd=root, capture_output=True, text=True, check=True
    )
    return result.stdout.split("\n")


def check(root: Path) -> tuple[list[str], list[str]]:
    known: list[str] = []
    unknown: list[str] = []
    for rel in tracked_files(root):
        rel = rel.strip()
        if not rel or rel.endswith(SKIP_SUFFIXES):
            continue
        path = root / rel
        try:
            text = path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue
        for label in sorted(find_known_identifiers(text)):
            known.append(f"{rel}: known private identifier for {label}")
        for token in sorted(find_unknown_candidates(text)):
            unknown.append(f"{rel}: unrecognised serial-shaped token {token!r}")
    return known, unknown


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "--quiet", action="store_true", help="print findings only, no summary"
    )
    args = parser.parse_args(argv)

    root = repo_root()
    known, unknown = check(root)

    for line in known:
        print(f"FAIL {line}")
    for line in unknown:
        print(f"WARN {line}")

    if not args.quiet:
        total = len(known) + len(unknown)
        if total == 0:
            print("repository boundary check: clean")
        else:
            print(
                f"repository boundary check: {len(known)} known, "
                f"{len(unknown)} unrecognised"
            )
    return 1 if (known or unknown) else 0


if __name__ == "__main__":
    sys.exit(main())
