#!/usr/bin/env python3
"""Generate verifiable build provenance; doesn't assert reproducibility."""
import hashlib
import json
import os
from pathlib import Path


def digest(path):
    p = Path(path)
    if not p.is_file():
        return None
    h = hashlib.sha256()
    with p.open('rb') as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b''):
            h.update(chunk)
    return h.hexdigest()


def main():
    e = os.environ
    get = lambda name: e.get('COFFEE_PROVENANCE_' + name, '')
    data = {
        'kernel_flavor': 'coffee', 'kernel_version': get('KERNEL_VERSION'),
        'package_version': get('PACKAGE_VERSION'),
        'source_tree': get('SOURCE_DIR'), 'source_archive_sha256': digest(get('TARBALL')),
        'base_config_sha256': digest(get('BASE_CONFIG')),
        'fragment_sha256': digest(get('FRAGMENT')),
        'configured_kernel_sha256': digest(get('CONFIG')),
        'build_note': 'Unsigned; boot tests and performance benchmarks NOT performed by this script.'
    }
    Path(get('OUT')).write_text(json.dumps(data, indent=2, sort_keys=True) + '\n')


if __name__ == '__main__':
    main()
