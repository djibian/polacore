#!/usr/bin/env python3
"""Tests for scripts/list_invariants.py.

Runs under:  python3 -m unittest -v tests/test_list_invariants.py
"""

import importlib.util
import json
import os
import subprocess
import sys
import tempfile
import unittest

# Repository paths are derived portably from this test file, never hardcoded.
_HERE = os.path.dirname(os.path.abspath(__file__))
_SCRIPT = os.path.normpath(
    os.path.join(_HERE, '..', 'scripts', 'list_invariants.py'))
_DEFAULT_REGISTRY = os.path.normpath(
    os.path.join(_HERE, '..', 'docs', 'security', 'INVARIANTS.md'))


def _load_module():
    spec = importlib.util.spec_from_file_location('list_invariants', _SCRIPT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _run_cli(registry):
    return subprocess.run(
        [sys.executable, _SCRIPT, '--registry', registry],
        capture_output=True, text=True)


class ListInvariantsTest(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.mod = _load_module()

    def _write_registry(self, lines):
        fd, path = tempfile.mkstemp(suffix='.md')
        with os.fdopen(fd, 'w', encoding='utf-8') as fh:
            fh.write('\n'.join(lines) + '\n')
        self.addCleanup(os.unlink, path)
        return path

    # ---- Real registry ----------------------------------------------------

    def test_real_registry_has_p112_to_p121_active(self):
        invs = self.mod.parse_registry(_DEFAULT_REGISTRY)
        by_id = {inv['id']: inv for inv in invs}
        for num in range(112, 122):
            inv_id = 'P%d' % num
            self.assertIn(inv_id, by_id, 'missing %s' % inv_id)
            self.assertEqual(by_id[inv_id]['status'], 'ACTIVE')

    def test_real_registry_rows_have_exactly_id_name_status(self):
        invs = self.mod.parse_registry(_DEFAULT_REGISTRY)
        self.assertTrue(invs)
        for inv in invs:
            self.assertEqual(
                sorted(inv.keys()), ['id', 'name', 'status'],
                'unexpected keys for %s' % inv)

    def test_cli_outputs_jsonl_for_real_registry(self):
        proc = _run_cli(_DEFAULT_REGISTRY)
        self.assertEqual(proc.returncode, 0, proc.stderr)
        rows = [json.loads(ln) for ln in proc.stdout.splitlines()]
        ids = [row['id'] for row in rows]
        self.assertIn('P112', ids)
        self.assertIn('P121', ids)
        self.assertEqual(len(rows), len(set(ids)), 'duplicate ids in output')

    # ---- Malformed invariant-like headings --------------------------------

    def test_heading_with_wrong_dash_fails(self):
        path = self._write_registry([
            '## Purpose',
            '## P10 - WrongDash',
            'Status: `ACTIVE`',
        ])
        with self.assertRaises(self.mod.InvariantError):
            self.mod.parse_registry(path)
        self.assertNotEqual(_run_cli(path).returncode, 0)

    def test_heading_without_spaces_fails(self):
        path = self._write_registry([
            '## P10\u2014NoSpaces',
            'Status: `ACTIVE`',
        ])
        with self.assertRaises(self.mod.InvariantError):
            self.mod.parse_registry(path)

    def test_heading_empty_name_fails(self):
        path = self._write_registry([
            '## P10 \u2014 ',
            'Status: `ACTIVE`',
        ])
        with self.assertRaises(self.mod.InvariantError):
            self.mod.parse_registry(path)

    def test_heading_with_trailing_text_after_digits_fails(self):
        path = self._write_registry([
            '## P10abc \u2014 Name',
            'Status: `ACTIVE`',
        ])
        with self.assertRaises(self.mod.InvariantError):
            self.mod.parse_registry(path)

    # ---- Section and status semantics -------------------------------------

    def test_missing_own_status_fails(self):
        path = self._write_registry([
            '## P10 \u2014 ValidName',
            'Status: `ACTIVE`',
            '## P11 \u2014 NextInvariant',
            '## Purpose',
        ])
        with self.assertRaises(self.mod.InvariantError):
            self.mod.parse_registry(path)

    def test_duplicate_explicit_id_fails(self):
        path = self._write_registry([
            '## P10 \u2014 First',
            'Status: `ACTIVE`',
            '## P10 \u2014 Second',
            'Status: `ACTIVE`',
        ])
        with self.assertRaises(self.mod.InvariantError):
            self.mod.parse_registry(path)

    def test_level3_migration_range_ignored(self):
        path = self._write_registry([
            '## Historical registry migration',
            '### P37\u2013P111',
            'Status: `ACTIVE / MIGRATION_PENDING`',
            '## P10 \u2014 RealInvariant',
            'Status: `ACTIVE`',
        ])
        invs = self.mod.parse_registry(path)
        self.assertEqual([inv['id'] for inv in invs], ['P10'])

    def test_ordinary_heading_is_valid_boundary(self):
        path = self._write_registry([
            '## P10 \u2014 First',
            'Status: `ACTIVE`',
            '## Purpose',
            'Some prose.',
            '## P11 \u2014 Second',
            'Status: `ACTIVE`',
        ])
        invs = self.mod.parse_registry(path)
        self.assertEqual([inv['id'] for inv in invs], ['P10', 'P11'])
        self.assertEqual(invs[0]['name'], 'First')
        self.assertEqual(invs[1]['name'], 'Second')

    def test_order_is_preserved(self):
        path = self._write_registry([
            '## P3 \u2014 Third',
            'Status: `ACTIVE`',
            '## P1 \u2014 First',
            'Status: `ACTIVE`',
            '## P2 \u2014 Second',
            'Status: `ACTIVE`',
        ])
        invs = self.mod.parse_registry(path)
        self.assertEqual([inv['id'] for inv in invs], ['P3', 'P1', 'P2'])

    def test_first_backtick_status_within_section(self):
        path = self._write_registry([
            '## P10 \u2014 First',
            'text with `not a status` inside',
            'Status: `ACTIVE`',
            'Status: `SUPERSEDED`',
            '## P11 \u2014 Second',
            'Status: `ACTIVE`',
        ])
        invs = self.mod.parse_registry(path)
        self.assertEqual(invs[0]['status'], 'ACTIVE')

    def test_explicit_registry_argument(self):
        # An explicit --registry PATH selects a non-default registry.
        path = self._write_registry([
            '## P7 \u2014 Explicit',
            'Status: `ACTIVE`',
        ])
        self.assertEqual(self.mod.main(['--registry', path]), 0)
        self.assertEqual(
            self.mod.main(['--registry', _DEFAULT_REGISTRY]), 0)

    def test_default_registry_argument(self):
        # With no --registry the default docs/security/INVARIANTS.md is used,
        # resolved from the repository root (derived from __file__).
        repo_root = os.path.normpath(os.path.join(_HERE, '..'))
        prev = os.getcwd()
        os.chdir(repo_root)
        try:
            self.assertEqual(self.mod.main([]), 0)
        finally:
            os.chdir(prev)


if __name__ == '__main__':
    unittest.main()
