#!/usr/bin/env python3
"""Unit tests for Git conflict resolution logic (safe, no DB/Jira dependencies)."""

import os
import shutil
import tempfile
import unittest

from studio.services.git_service import (
    parse_git_conflict_content,
    resolve_conflict_content,
    get_git_conflict_file_info,
    resolve_git_conflict_file,
)


class TestGitConflictResolution(unittest.TestCase):
    def setUp(self):
        self.sample_conflict_text = (
            "import React from 'react';\n"
            "\n"
            "<<<<<<< HEAD\n"
            "const theme = 'dark';\n"
            "const version = '2.0.0';\n"
            "=======\n"
            "const theme = 'light';\n"
            "const version = '2.1.0';\n"
            ">>>>>>> feature/new-theme\n"
            "\n"
            "export default function App() {\n"
            "<<<<<<< HEAD\n"
            "  return <div>Old App</div>;\n"
            "=======\n"
            "  return <div>New App</div>;\n"
            ">>>>>>> feature/new-theme\n"
            "}\n"
        )

    def test_parse_git_conflict_content(self):
        blocks = parse_git_conflict_content(self.sample_conflict_text)
        self.assertEqual(len(blocks), 2)

        # Block 0
        b0 = blocks[0]
        self.assertEqual(b0['index'], 0)
        self.assertIn("const theme = 'dark';", b0['current'])
        self.assertIn("const theme = 'light';", b0['incoming'])
        self.assertEqual(b0['current'], b0['current_code'])
        self.assertEqual(b0['incoming'], b0['incoming_code'])
        self.assertTrue(b0['current_header'].startswith("<<<<<<<"))
        self.assertTrue(b0['incoming_footer'].startswith(">>>>>>>"))

        # Block 1
        b1 = blocks[1]
        self.assertEqual(b1['index'], 1)
        self.assertIn("Old App", b1['current'])
        self.assertIn("New App", b1['incoming'])

    def test_resolve_conflict_content_single_block_current(self):
        res = resolve_conflict_content(self.sample_conflict_text, 'current', block_index=0)
        blocks = parse_git_conflict_content(res)
        self.assertEqual(len(blocks), 1)
        self.assertIn("const theme = 'dark';", res)
        self.assertNotIn("const theme = 'light';", res)
        self.assertIn("<<<<<<< HEAD\n  return <div>Old App</div>;", res)

    def test_resolve_conflict_content_single_block_incoming(self):
        res = resolve_conflict_content(self.sample_conflict_text, 'incoming', block_index=0)
        blocks = parse_git_conflict_content(res)
        self.assertEqual(len(blocks), 1)
        self.assertIn("const theme = 'light';", res)
        self.assertNotIn("const theme = 'dark';", res)

    def test_resolve_conflict_content_single_block_both(self):
        res = resolve_conflict_content(self.sample_conflict_text, 'both', block_index=0)
        blocks = parse_git_conflict_content(res)
        self.assertEqual(len(blocks), 1)
        self.assertIn("const theme = 'dark';", res)
        self.assertIn("const theme = 'light';", res)

    def test_resolve_conflict_content_all_current(self):
        for act in ('current', 'ours', 'accept_current'):
            res = resolve_conflict_content(self.sample_conflict_text, act, block_index=None)
            blocks = parse_git_conflict_content(res)
            self.assertEqual(len(blocks), 0)
            self.assertIn("const theme = 'dark';", res)
            self.assertIn("Old App", res)
            self.assertNotIn("const theme = 'light';", res)
            self.assertNotIn("New App", res)
            self.assertNotIn("<<<<<<<", res)
            self.assertNotIn("=======", res)
            self.assertNotIn(">>>>>>>", res)

    def test_resolve_conflict_content_all_incoming(self):
        for act in ('incoming', 'theirs', 'accept_incoming'):
            res = resolve_conflict_content(self.sample_conflict_text, act, block_index=None)
            blocks = parse_git_conflict_content(res)
            self.assertEqual(len(blocks), 0)
            self.assertIn("const theme = 'light';", res)
            self.assertIn("New App", res)
            self.assertNotIn("const theme = 'dark';", res)
            self.assertNotIn("Old App", res)
            self.assertNotIn("<<<<<<<", res)
            self.assertNotIn("=======", res)
            self.assertNotIn(">>>>>>>", res)

    def test_get_git_conflict_file_info_and_resolve_file(self):
        tmp_dir = tempfile.mkdtemp()
        try:
            test_file = os.path.join(tmp_dir, "App.tsx")
            with open(test_file, "w", encoding="utf-8") as f:
                f.write(self.sample_conflict_text)

            info = get_git_conflict_file_info(tmp_dir, "App.tsx")
            self.assertTrue(info['success'])
            self.assertTrue(info['has_conflicts'])
            self.assertEqual(info['conflict_count'], 2)
            self.assertIn('blocks', info)
            self.assertIn('conflict_blocks', info)
            self.assertEqual(len(info['conflict_blocks']), 2)

            # Resolve using 'current'
            res = resolve_git_conflict_file(tmp_dir, "App.tsx", "current")
            self.assertTrue(res['success'])
            self.assertEqual(res['remaining_conflicts_in_file'], 0)

            with open(test_file, "r", encoding="utf-8") as f:
                final_content = f.read()
            self.assertIn("const theme = 'dark';", final_content)
            self.assertNotIn("const theme = 'light';", final_content)
            self.assertNotIn("<<<<<<<", final_content)
        finally:
            shutil.rmtree(tmp_dir, ignore_errors=True)


if __name__ == '__main__':
    unittest.main()
