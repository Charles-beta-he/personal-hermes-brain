#!/usr/bin/env python3
"""Regression tests for sync-brain.py path filtering."""
import importlib.util
import os
import tempfile
import unittest
from pathlib import Path


SCRIPT = Path('/Users/charles/.hermes/scripts/sync-brain.py')


def load_sync_module(home: Path):
    old_home = os.environ.get('HOME')
    os.environ['HOME'] = str(home)
    try:
        spec = importlib.util.spec_from_file_location('sync_brain_under_test', SCRIPT)
        mod = importlib.util.module_from_spec(spec)
        assert spec.loader is not None
        spec.loader.exec_module(mod)
        return mod
    finally:
        if old_home is None:
            os.environ.pop('HOME', None)
        else:
            os.environ['HOME'] = old_home


class SyncBrainPathFilterTests(unittest.TestCase):
    def test_push_does_not_skip_regular_note_with_brain_in_filename(self):
        with tempfile.TemporaryDirectory() as td:
            home = Path(td)
            src = home / '.hermes/notes/evolution/2026-05-06-symphony-obsidian-local-brain.md'
            src.parent.mkdir(parents=True)
            src.write_text('# local brain evolution\n', encoding='utf-8')

            mod = load_sync_module(home)
            pushed = mod.push()

            dst = home / 'Documents/brain/99-hermes-notes/evolution/2026-05-06-symphony-obsidian-local-brain.md'
            self.assertEqual(pushed, 1)
            self.assertTrue(dst.exists())
            self.assertEqual(dst.read_text(encoding='utf-8'), '# local brain evolution\n')

    def test_push_skips_only_hermes_brain_mirror_subtree(self):
        with tempfile.TemporaryDirectory() as td:
            home = Path(td)
            mirror = home / '.hermes/notes/brain/00-system/source.md'
            mirror.parent.mkdir(parents=True)
            mirror.write_text('# pulled brain mirror\n', encoding='utf-8')

            normal = home / '.hermes/notes/evolution/not-brain-mirror.md'
            normal.parent.mkdir(parents=True, exist_ok=True)
            normal.write_text('# normal note\n', encoding='utf-8')

            mod = load_sync_module(home)
            pushed = mod.push()

            skipped_dst = home / 'Documents/brain/99-hermes-notes/brain/00-system/source.md'
            normal_dst = home / 'Documents/brain/99-hermes-notes/evolution/not-brain-mirror.md'
            self.assertEqual(pushed, 1)
            self.assertFalse(skipped_dst.exists())
            self.assertTrue(normal_dst.exists())


if __name__ == '__main__':
    unittest.main()
