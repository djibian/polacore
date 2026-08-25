#!/usr/bin/env python3
"""List security invariants from the invariant registry as JSONL.

Emits one JSON object per invariant with exactly "id", "name", and "status".
Reads the default registry docs/security/INVARIANTS.md, or a path supplied
with --registry PATH.

An explicit invariant heading is exactly:  ## P<number> — nonempty-name
where the dash is an em dash (U+2014) surrounded by single spaces and the
name is non-empty.  Any level-2 heading beginning with P followed by digits
that is not a full valid invariant heading fails closed; every level-2
heading closes the prior invariant section; and an invariant must carry its
own first `Status: ...` line within its section before that boundary.

The historical level-3 migration heading (### P37-P111) is ignored rather
than synthesized into invariant entries.
"""

import argparse
import json
import re
import sys

# An explicit invariant heading: "P<digits> — nonempty-name".
_HEADING_RE = re.compile(r'^P(\d+) \u2014 (.+)$')
# A level-2 heading is "invariant-like" if it starts with P followed by digits.
_INVARIANT_LIKE_RE = re.compile(r'^P\d')
# The first backtick status line within an invariant section.
_STATUS_RE = re.compile(r'^Status: `([^`]*)`$')

_LEVEL2 = '## '
_LEVEL3 = '### '


class InvariantError(Exception):
    """Raised when the registry violates the invariant format contract."""


def parse_registry(path):
    """Return a list of {"id", "name", "status"} dicts in registry order."""
    with open(path, 'r', encoding='utf-8') as fh:
        lines = fh.read().splitlines()

    invariants = []
    seen = set()
    current = None  # {"id": ..., "name": ..., "status": None}

    def close_current():
        nonlocal current
        if current is None:
            return
        if current['status'] is None:
            raise InvariantError(
                'invariant %s missing its own Status line' % current['id'])
        invariants.append(current)
        current = None

    for raw in lines:
        line = raw.strip()
        if line.startswith(_LEVEL3):
            # Level-3 headings, including the historical P37-P111 migration
            # range, are ignored rather than synthesized.
            continue
        if line.startswith(_LEVEL2):
            close_current()
            content = line[len(_LEVEL2):]
            if _INVARIANT_LIKE_RE.match(content):
                m = _HEADING_RE.match(content)
                if not m:
                    raise InvariantError(
                        'malformed invariant heading: %s' % line)
                name = m.group(2).strip()
                if not name:
                    raise InvariantError(
                        'empty invariant name in heading: %s' % line)
                inv_id = 'P' + m.group(1)
                if inv_id in seen:
                    raise InvariantError(
                        'duplicate explicit invariant id: %s' % inv_id)
                seen.add(inv_id)
                current = {'id': inv_id, 'name': name, 'status': None}
            continue
        if current is not None and current['status'] is None:
            sm = _STATUS_RE.match(line)
            if sm:
                current['status'] = sm.group(1)

    close_current()
    return invariants


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        '--registry', default='docs/security/INVARIANTS.md',
        help='path to the invariant registry (default: docs/security/INVARIANTS.md)')
    args = parser.parse_args(argv)
    try:
        invariants = parse_registry(args.registry)
    except (OSError, InvariantError) as exc:
        print('list_invariants: error: %s' % exc, file=sys.stderr)
        return 1
    for inv in invariants:
        print(json.dumps({
            'id': inv['id'],
            'name': inv['name'],
            'status': inv['status'],
        }))
    return 0


if __name__ == '__main__':
    sys.exit(main())
