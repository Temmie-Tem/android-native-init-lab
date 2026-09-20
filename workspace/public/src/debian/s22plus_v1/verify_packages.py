#!/usr/bin/env python3
"""Recheck retained Debian signatures, index hashes and every installed .deb."""
import hashlib
import json
from pathlib import Path
import re
import subprocess
import sys


def sha(data):
    return hashlib.sha256(data).hexdigest()


def verify(out):
    indexes, receipts = {}, []
    for release in sorted((out / 'apt-lists').glob('*InRelease')):
        checked = subprocess.run(['gpgv', '--keyring',
            '/usr/share/keyrings/debian-archive-keyring.gpg', release],
            capture_output=True, check=True)
        (out / (release.name + '.gpgv.log')).write_bytes(checked.stdout + checked.stderr)
        prefix = release.name.removesuffix('InRelease')
        candidates = list((out / 'apt-lists').glob(prefix + 'main_binary-arm64_Packages*'))
        if len(candidates) != 1:
            raise ValueError('ambiguous Packages input')
        packages = candidates[0]
        raw = subprocess.check_output(['/usr/lib/apt/apt-helper', 'cat-file', packages])
        checksum = re.search(r'^ ([0-9a-f]{64}) +(\d+) +main/binary-arm64/Packages$',
                             release.read_text(), re.M)
        if not checksum or checksum.group(1) != sha(raw) or int(checksum.group(2)) != len(raw):
            raise ValueError('signed Packages identity differs')
        receipts.append(dict(release_sha256=sha(release.read_bytes()), packages_sha256=sha(raw)))
        for block in raw.decode().split('\n\n'):
            fields = dict(line.split(': ', 1) for line in block.splitlines()
                          if ': ' in line and not line.startswith(' '))
            if all(name in fields for name in ('Package', 'Version', 'Architecture', 'SHA256', 'Size')):
                key = (fields['Package'], fields['Version'], fields['Architecture'])
                indexes.setdefault(key, set()).add((fields['SHA256'], int(fields['Size'])))
    wanted = set(tuple(line.split('\t')) for line in (out / 'packages.tsv').read_text().splitlines())
    found, artifacts = set(), []
    for package in sorted((out / 'debs').glob('*.deb')):
        fields = subprocess.check_output(['dpkg-deb', '-f', package,
            'Package', 'Version', 'Architecture'], text=True)
        record = dict(line.split(': ', 1) for line in fields.splitlines())
        key = tuple(record[x] for x in ('Package', 'Version', 'Architecture'))
        identity = (sha(package.read_bytes()), package.stat().st_size)
        if key not in wanted or identity not in indexes.get(key, set()) or key in found:
            raise ValueError('package missing, duplicated or outside signed closure: ' + str(key))
        found.add(key)
        artifacts.append(dict(package=key[0], version=key[1], architecture=key[2],
                              sha256=identity[0], size=identity[1], file=package.name))
    if not receipts or found != wanted:
        raise ValueError('incomplete installed-package closure: ' + str(sorted(wanted - found)))
    result = dict(verdict='PASS_SIGNED_PACKAGE_CLOSURE_H0', count=len(found),
                  repositories=receipts, packages=artifacts)
    (out / 'package-lock.json').write_text(json.dumps(result, indent=2) + '\n')
    return result


if __name__ == '__main__':
    print(verify(Path(sys.argv[1]))['count'])
