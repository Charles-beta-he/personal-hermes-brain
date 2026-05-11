#!/usr/bin/env python3
"""Tests for local_brain_mempalace_benchmark.py derived-index benchmark."""

import importlib.util
import tempfile
import unittest
from pathlib import Path

SCRIPT = Path(__file__).parent / "local_brain_mempalace_benchmark.py"
spec = importlib.util.spec_from_file_location("local_brain_mempalace_benchmark", SCRIPT)
bench = importlib.util.module_from_spec(spec)
import sys
sys.modules["local_brain_mempalace_benchmark"] = bench
spec.loader.exec_module(bench)


class LocalBrainMemPalaceBenchmarkTestCase(unittest.TestCase):
    def test_isolated_sample_benchmark_writes_no_source_files_and_reports_queries(self):
        with tempfile.TemporaryDirectory() as td:
            source = Path(td) / "brain"
            source.mkdir()
            (source / "A.md").write_text("# A\n\nMemPalace派生索引 source of truth Markdown canonical.\n", encoding="utf-8")
            (source / "B.md").write_text("# B\n\nTemporal facts and bilingual query benchmark.\n", encoding="utf-8")
            before = sorted(p.relative_to(source).as_posix() for p in source.rglob("*"))
            report = bench.run_benchmark(source, queries=["MemPalace派生索引", "temporal facts"], sample_limit=2, no_llm=True)
            after = sorted(p.relative_to(source).as_posix() for p in source.rglob("*"))
            self.assertEqual(before, after)
            self.assertTrue(report["derived_only"])
            self.assertTrue(report["no_llm"])
            self.assertEqual(len(report["queries"]), 2)
            self.assertIn("brainctl_like", report["queries"][0])
            self.assertIn("derived_token_overlap", report["queries"][0])


if __name__ == "__main__":
    unittest.main()
