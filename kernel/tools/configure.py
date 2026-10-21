#!/usr/bin/env python3
"""Apply and verify a small CoffeeKernel fragment against a Debian kernel .config.

No Kconfig dependency: Linux `make olddefconfig` still resolves dependencies.
This helper MUST be followed by `make olddefconfig` and a strict verification.
"""
from __future__ import annotations
import argparse
import lzma
import re
from pathlib import Path

ACTIVE = re.compile(r'^(CONFIG_[A-Z0-9_]+)=(.*)$')
INACTIVE = re.compile(r'^# (CONFIG_[A-Z0-9_]+) is not set$')


def read_text(path: Path) -> str:
    if path.suffix == '.xz':
        return lzma.open(path, 'rt', encoding='utf-8').read()
    return path.read_text(encoding='utf-8')


def parse(text: str) -> dict[str, str]:
    result: dict[str, str] = {}
    for line in text.splitlines():
        match = ACTIVE.fullmatch(line) or INACTIVE.fullmatch(line)
        if match:
            key = match.group(1)
            if key in result:
                raise ValueError(f'Duplicate config key: {key}')
            result[key] = match.group(2) if match.re is ACTIVE else 'n'
    return result


def fragment_lines(text: str) -> dict[str, str]:
    values = parse(text)
    if not values:
        raise ValueError('Empty kernel config fragment')
    for line in text.splitlines():
        line = line.strip()
        if line and not line.startswith('#') and not ACTIVE.fullmatch(line):
            raise ValueError(f'Invalid fragment line: {line}')
        if line.startswith('# CONFIG_') and not INACTIVE.fullmatch(line):
            raise ValueError(f'Invalid fragment line: {line}')
    return values


def render_line(key: str, value: str) -> str:
    return f'# {key} is not set' if value == 'n' else f'{key}={value}'


def merge(base: str, changes: dict[str, str]) -> str:
    result = []
    seen = set()
    for line in base.splitlines():
        match = ACTIVE.fullmatch(line) or INACTIVE.fullmatch(line)
        if match and match.group(1) in changes:
            key = match.group(1)
            if key in seen:
                raise ValueError(f'Duplicate config key in base: {key}')
            result.append(render_line(key, changes[key]))
            seen.add(key)
        else:
            result.append(line)
    for key in sorted(set(changes) - seen):
        result.append(render_line(key, changes[key]))
    return '\n'.join(result) + '\n'


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--base', type=Path, required=True, help='Debian .config or .config.xz')
    p.add_argument('--fragment', type=Path, required=True)
    p.add_argument('--output', type=Path, help='Write modified config (not used with --verify)')
    p.add_argument('--verify', action='store_true', help='Fail if olddefconfig changed any fragment key')
    args = p.parse_args()
    changes = fragment_lines(args.fragment.read_text())
    original = read_text(args.base)
    cert_keys = ('CONFIG_SYSTEM_TRUSTED_KEYS', 'CONFIG_SYSTEM_REVOCATION_KEYS')
    if args.verify:
        actual = parse(original)
        # Building from Debian's own source package should not depend on
        # certificate files unavailable to derivative builders.
        for key in cert_keys:
            if key in actual and actual[key] not in ('""', 'n'):
                print(f'FAILED: {key} refers to external certificate material: {actual[key]}')
                return 1
        failed = [(k, desired, actual.get(k, 'MISSING')) for k, desired in changes.items() if actual.get(k) != desired]
        if failed:
            for k, expected, observed in failed:
                print(f'FAILED: {k} expected {expected}, got {observed}')
            return 1
        print(f'PASS: {len(changes)} kernel configuration settings retained')
        return 0
    if args.output is None:
        p.error('--output required without --verify')
    args.output.parent.mkdir(parents=True, exist_ok=True)
    present = parse(original)
    for key in cert_keys:
        if key in present:
            changes[key] = '""'
    args.output.write_text(merge(original, changes))
    print(f'Applied {len(changes)} config settings to {args.output}')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
