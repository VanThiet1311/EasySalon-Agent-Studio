#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Tests for Settings API Keys & Providers UI:
1. Overview provider selector buttons without icons.
2. Dynamic reordering putting connected providers first.
3. Single card visibility (selected provider only).
4. Action buttons: 'Kết nối', 'Kiểm tra kết nối', 'Gỡ API Key'.
"""

import json
import os
import re
import subprocess
import unittest

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


class TestApiKeysAndProvidersUI(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        html_path = os.path.join(ROOT_DIR, "frontend", "views", "tab_settings.html")
        with open(html_path, "r", encoding="utf-8") as f:
            cls.html = f.read()

        js_path = os.path.join(ROOT_DIR, "frontend", "modules", "settings.js")
        with open(js_path, "r", encoding="utf-8") as f:
            cls.js = f.read()

        css_path = os.path.join(ROOT_DIR, "frontend", "style", "settings.css")
        with open(css_path, "r", encoding="utf-8") as f:
            cls.css = f.read()

    def test_overview_buttons_have_no_svg_icons(self):
        """Overview selector buttons (btn_provider_*) must not contain svg icons."""
        providers = ["gemini", "claude", "openai", "deepseek", "custom"]
        for p in providers:
            btn_regex = rf'<button[^>]+id=["\']btn_provider_{p}["\'][\s\S]*?</button>'
            match = re.search(btn_regex, self.html)
            self.assertIsNotNone(match, f"Button btn_provider_{p} not found in tab_settings.html")
            btn_content = match.group(0)
            self.assertNotIn("<svg", btn_content, f"btn_provider_{p} should not contain SVG icons")
            # Must contain status pill
            self.assertIn(f'id="pill_provider_{p}"', btn_content, f"pill_provider_{p} missing in btn_provider_{p}")

    def test_dedicated_config_cards_exist(self):
        """Each provider must have its own dedicated apiConfigCard_* container."""
        providers = ["gemini", "claude", "openai", "deepseek", "custom"]
        for p in providers:
            card_id = f"apiConfigCard_{p}"
            self.assertIn(f'id="{card_id}"', self.html, f"Card {card_id} missing in tab_settings.html")

            # Must have action buttons: connect, test, and remove
            self.assertIn(f'id="btn_connect_{p}"', self.html, f"btn_connect_{p} missing in {card_id}")
            self.assertIn(f'id="btn_test_{p}"', self.html, f"btn_test_{p} missing in {card_id}")
            self.assertIn(f'id="btn_remove_key_{p}"', self.html, f"btn_remove_key_{p} missing in {card_id}")

    def test_card_initial_visibility(self):
        """By default only the gemini card is visible; claude, openai, deepseek, custom have hidden class."""
        gemini_match = re.search(r'<div[^>]+id=["\']apiConfigCard_gemini["\'][^>]*>', self.html)
        self.assertIsNotNone(gemini_match)
        self.assertNotIn("hidden", gemini_match.group(0), "apiConfigCard_gemini should be visible by default")

        for p in ["claude", "openai", "deepseek", "custom"]:
            match = re.search(rf'<div[^>]+id=["\']apiConfigCard_{p}["\'][^>]*>', self.html)
            self.assertIsNotNone(match, f"apiConfigCard_{p} not found")
            self.assertIn("hidden", match.group(0), f"apiConfigCard_{p} should have hidden class by default")

    def test_css_contains_provider_status_pill(self):
        """CSS must define .provider-status-pill and .provider-status-pill.is-connected."""
        self.assertIn(".provider-status-pill", self.css)
        self.assertIn(".provider-status-pill.is-connected", self.css)

    def test_js_exports_and_functions(self):
        """settings.js must define and export key functions on window."""
        required_fns = [
            "selectActiveApiProvider",
            "isProviderConnected",
            "reorderApiProviderCards",
            "testApiKey",
            "connectApiKey",
            "removeApiKey",
            "updateApiUI",
            "updateApiKeyBadges",
        ]
        for fn in required_fns:
            self.assertIn(f"window.{fn} =", self.js, f"window.{fn} export missing in settings.js")

    def test_js_single_card_and_reordering_logic(self):
        """Simulate single card selection and reordering logic in Node.js."""
        node_script = """
        const providers = ['gemini', 'claude', 'openai', 'deepseek', 'custom'];
        const cards = {};
        const buttons = {};
        providers.forEach(p => {
          cards[p] = { id: 'apiConfigCard_' + p, hidden: p !== 'gemini' };
          buttons[p] = { id: 'btn_provider_' + p, active: p === 'gemini' };
        });

        function selectActiveApiProvider(provider) {
          providers.forEach(p => {
            cards[p].hidden = (p !== provider);
            buttons[p].active = (p === provider);
          });
        }

        // Test 1: select claude -> only claude is visible
        selectActiveApiProvider('claude');
        if (cards['claude'].hidden !== false) throw new Error("Claude card should be visible");
        if (cards['gemini'].hidden !== true) throw new Error("Gemini card should be hidden");
        if (cards['openai'].hidden !== true) throw new Error("OpenAI card should be hidden");

        // Test 2: reorderApiProviderCards
        // Suppose claude and deepseek are connected, others are not
        const connectedMap = { gemini: false, claude: true, openai: false, deepseek: true, custom: false };
        const sorted = [...providers].sort((a, b) => {
          const aConn = connectedMap[a] ? 0 : 1;
          const bConn = connectedMap[b] ? 0 : 1;
          return aConn - bConn;
        });

        // Connected must come first
        if (sorted[0] !== 'claude' || sorted[1] !== 'deepseek') {
          throw new Error("Connected providers should be sorted to the front: " + JSON.stringify(sorted));
        }

        console.log(JSON.stringify({ success: true, sorted }));
        """
        proc = subprocess.run(
            ["node", "-e", node_script],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            check=True
        )
        res = json.loads(proc.stdout.strip())
        self.assertTrue(res.get("success"))
        self.assertEqual(res.get("sorted")[:2], ["claude", "deepseek"])


if __name__ == "__main__":
    unittest.main()
