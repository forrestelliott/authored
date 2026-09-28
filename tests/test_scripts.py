"""CLI regressions; uses only the standard library and temporary evidence."""

import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]


class ScriptTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)

    def file(self, name, text):
        path = self.root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text)
        return path

    def run_script(self, script, *args):
        return subprocess.run(
            [sys.executable, str(ROOT / 'scripts' / script), *map(str, args)],
            cwd=self.root, capture_output=True, text=True,
            env=dict(os.environ, PYTHONDONTWRITEBYTECODE='1'),
        )

    def test_snapshot_collisions_fail_before_writing(self):
        for names in [('a/draft.txt', 'b/draft.txt'),
                      ('c/Draft.txt', 'd/draft.txt')]:
            with self.subTest(names=names):
                sources = [self.file(name, name) for name in names]
                out = self.root / 'evidence'
                result = self.run_script('snapshot.py', *sources, '--out', out)
                self.assertNotEqual(result.returncode, 0)
                self.assertIn('collision', result.stderr)
                self.assertNotIn('Traceback', result.stderr)
                self.assertFalse(out.exists())
                self.assertEqual([p.read_text() for p in sources], list(names))

    def test_snapshot_file_directory_collision(self):
        file = self.file('a/folder', 'file')
        self.file('b/folder/draft.txt', 'draft')
        out = self.root / 'evidence'
        result = self.run_script('snapshot.py', file, self.root / 'b/folder', '--out', out)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('collision', result.stderr)
        self.assertFalse(out.exists())

    def test_snapshot_rejects_nested_and_equal_output(self):
        self.file('source/draft.txt', 'unchanged')
        for out in [self.root / 'source/evidence', self.root / 'source']:
            with self.subTest(out=out):
                result = self.run_script('snapshot.py', self.root / 'source', '--out', out)
                self.assertNotEqual(result.returncode, 0)
                self.assertNotIn('Traceback', result.stderr)
                self.assertFalse((out / 'originals').exists())

    def test_snapshot_sibling_output_and_hashes(self):
        source = self.file('source/draft.txt', 'original evidence')
        before = source.stat()
        out = self.root / 'evidence'
        result = self.run_script('snapshot.py', source.parent, '--out', out)
        self.assertEqual(result.returncode, 0, result.stderr)
        record = json.loads((out / 'manifest.json').read_text())['files'][0]
        archived = out / record['archive_path']
        self.assertEqual(archived.read_bytes(), source.read_bytes())
        self.assertEqual(record['sha256'], hashlib.sha256(source.read_bytes()).hexdigest())
        self.assertEqual(archived.stat().st_mode & 0o222, 0)
        self.assertEqual(source.stat().st_mtime_ns, before.st_mtime_ns)
        again = self.run_script('snapshot.py', source.parent, '--out', out)
        self.assertNotEqual(again.returncode, 0)
        self.assertEqual(archived.read_text(), 'original evidence')

    def test_report_empty_drafts_gives_actionable_error(self):
        draft = self.file('source/empty.txt', '')
        output = self.root / 'report.html'
        result = self.run_script('report.py', draft.parent, '--drafts', draft,
                                 '--out', output)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('No readable words', result.stderr)
        self.assertNotIn('Traceback', result.stderr)
        self.assertFalse(output.exists())

    def test_partial_overlap_counts_only_matching_words(self):
        first = self.file('source/first.txt', '')
        words = [f'word{i}' for i in range(100)]
        last = self.file('source/last.txt', ' '.join(words))
        notes = self.file('source/notes.txt', ' '.join(words[:40]))
        output = self.root / 'report.html'
        result = self.run_script('report.py', first.parent, '--drafts', first, last,
                                 '--sources', notes, '--out', output)
        self.assertEqual(result.returncode, 0, result.stderr)
        report = output.read_text()
        self.assertEqual(re.findall(r'class="t" style="width:([\d.]+)%', report), ['40.00'])
        self.assertEqual(re.findall(r'class="w" style="width:([\d.]+)%', report), ['0.00', '60.00'])
        result = self.run_script('draft_diff.py', first, last, '--sources', notes)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn('shares 40%', result.stdout)
        self.assertNotIn('came from notes.txt', result.stdout)

    def test_sample_workflow(self):
        fixture = ROOT / 'evals/fixtures/maya-broad-street'
        before = {p.name: p.read_bytes() for p in fixture.iterdir()}
        evidence = self.root / 'evidence'
        result = self.run_script('snapshot.py', fixture, '--out', evidence)
        self.assertEqual(result.returncode, 0, result.stderr)
        for script in ['timeline.py', 'report.py']:
            result = self.run_script(script, evidence)
            self.assertEqual(result.returncode, 0, result.stderr)
        self.assertTrue((evidence / 'report.html').is_file())
        self.assertEqual(before, {p.name: p.read_bytes() for p in fixture.iterdir()})


if __name__ == '__main__':
    unittest.main()
