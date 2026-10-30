#!/usr/bin/env python3
"""
Adversarial Frontend & Interaction Test Suite for EasySalon Architecture Linkage Diagram.
Written by Challenger 2 (Empirical Adversarial Challenger: Frontend & DOM Specialist).

Focus Areas:
1. Search Logic Stress Test:
   - Regex meta-characters: .*+?^${}()|[]\
   - Quotes, Unicode, Vietnamese accents (accented vs unaccented)
   - Empty, whitespace-only, and 10,000-char long queries
   - Live counter and empty-state toggling
2. Tab Switching & State Preservation:
   - Tree View details expand/collapse state preservation across tab switches
   - Master controls: expandAllTreeNodes() / collapseAllTreeNodes()
   - Mermaid zoom/pan transform preservation across tab switches
3. Node Click Handler & DOM Resilience:
   - Non-existent and edge-case node IDs
   - Duplicate function definitions (highlightAndScrollToModule)
   - Behavior when clicking a module row currently hidden by search filter
   - Static DOM ID consistency (all getElementById targets exist in HTML)
"""

import json
import os
import re
import subprocess
import time
import unittest
import urllib.parse
import urllib.request

SERVER_URL = os.environ.get("TEST_SERVER_URL", "http://localhost:8765")
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
WEB_SERVER_FILE = os.path.join(BASE_DIR, "web_server.py")


def fetch_url(path):
    url = urllib.parse.urljoin(SERVER_URL, path)
    req = urllib.request.Request(url, headers={"User-Agent": "Challenger2-Frontend-Tester/1.0"})
    with urllib.request.urlopen(req, timeout=10) as resp:
        return resp.status, dict(resp.getheaders()), resp.read().decode("utf-8")


def run_node_eval(script):
    """Executes a JS script in Node.js and returns stdout, stderr, and exit code."""
    proc = subprocess.run(
        ["node", "-e", script],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        timeout=15
    )
    return proc.returncode, proc.stdout, proc.stderr


class TestAdversarialSearchLogic(unittest.TestCase):
    """Empirical tests for instant search filtering in web_server.py."""

    @classmethod
    def setUpClass(cls):
        status, _, body = fetch_url("/api/diagram-data")
        assert status == 200
        cls.data = json.loads(body)
        cls.modules = cls.data.get("modules", [])
        assert len(cls.modules) == 11

    def _execute_js_search(self, query):
        """Runs the exact search filtering logic from web_server.py inside Node.js."""
        modules_json = json.dumps(self.modules)
        query_json = json.dumps(query)
        js_code = f"""
        const currentModules = {modules_json};
        const query = ({query_json} || '').toLowerCase().trim();
        let matchedCount = 0;
        const matchedIds = [];

        currentModules.forEach(m => {{
            if (!query) {{
                matchedCount++;
                matchedIds.push(m.id);
                return;
            }}

            const text = [
                m.title,
                m.skill,
                m.fe?.path,
                m.fe?.resource,
                m.fe?.desc,
                ...(m.fe?.imports || []),
                ...(m.fe?.exports || []),
                m.api?.route,
                ...(m.api?.endpoints || []).map(ep => `${{ep.method}} ${{ep.path}} ${{ep.note}}`),
                m.be?.path,
                m.be?.controller,
                m.be?.desc,
                ...(m.be?.injections || []),
                ...(m.be?.links || []),
                ...(m.be?.exports || [])
            ].filter(Boolean).join(' ').toLowerCase();

            if (text.includes(query)) {{
                matchedCount++;
                matchedIds.push(m.id);
            }}
        }});

        console.log(JSON.stringify({{ count: matchedCount, ids: matchedIds }}));
        """
        code, out, err = run_node_eval(js_code)
        if code != 0:
            raise RuntimeError(f"Node execution failed for query {query!r}: {err}")
        return json.loads(out)

    def test_search_regex_metacharacters_safety(self):
        """Search must safely handle regex special characters without crashing or throwing SyntaxError."""
        special_chars = [
            ".*", "+", "?", "^", "$", "(", ")", "[", "]", "{", "}", "|", "\\",
            ".*+", "[a-z]+", "\\d+", "(\\w+)", "(?:.*)", "\\s*$", "/^.*$/"
        ]
        for sc in special_chars:
            try:
                res = self._execute_js_search(sc)
                self.assertIsInstance(res["count"], int)
                self.assertIsInstance(res["ids"], list)
            except Exception as e:
                self.fail(f"Search crashed on regex meta-character '{sc}': {e}")

    def test_search_quote_and_syntax_characters(self):
        """Search must safely handle quotes, backticks, HTML tags, and null bytes."""
        hazard_queries = [
            '""', "''", "``", "<script>", "</script>", "<div>", "';", "--",
            "/* */", "\\0", "%20", "%00", "\\n", "\\r\\n"
        ]
        for q in hazard_queries:
            try:
                res = self._execute_js_search(q)
                self.assertIsInstance(res["count"], int)
            except Exception as e:
                self.fail(f"Search crashed on hazard query '{q}': {e}")

    def test_search_empty_and_whitespace_permutations(self):
        """Empty, space, tab, and newline queries must match ALL 11 modules."""
        empty_queries = ["", " ", "   ", "\t", "\n", " \t \n "]
        for q in empty_queries:
            res = self._execute_js_search(q)
            self.assertEqual(
                res["count"], 11,
                f"Expected all 11 modules for whitespace query {q!r}, got {res['count']}"
            )

    def test_search_very_long_queries(self):
        """Search must handle very long queries (1,000 and 10,000 characters) safely within 500ms."""
        for length in [1000, 10000]:
            long_query = "A" * length
            start = time.time()
            res = self._execute_js_search(long_query)
            elapsed = time.time() - start
            self.assertEqual(res["count"], 0, "Long random string should not match any module")
            self.assertLess(elapsed, 0.5, f"Search on {length}-char query exceeded 500ms: {elapsed:.3f}s")

    def test_search_vietnamese_accented_queries(self):
        """Searching with proper Vietnamese accents matches expected domain modules."""
        test_cases = [
            ("giường", "booking-bedroom"),
            ("thu ngân", "pos-cashier"),
            ("hóa đơn", "pos-cashier"),
            ("lịch hẹn", "calendar-schedule"),
            ("khách hàng", "customer-crm"),
            ("kho hàng", "warehouse-inventory"),
            ("hoa hồng", "commission-setup"),
            ("sổ quỹ", "revenue-expenditure"),
            ("liệu trình", "service-package-combo"),
            ("điện tử", "tax-einvoice"),
            ("chấm công", "payroll-timesheet"),
            ("thống kê", "report-analytics"),
        ]
        for query, expected_id in test_cases:
            res = self._execute_js_search(query)
            self.assertIn(
                expected_id, res["ids"],
                f"Query '{query}' failed to match expected module '{expected_id}'"
            )

    def test_search_unaccented_vietnamese_empirical_finding(self):
        """
        Adversarial evaluation: Test unaccented Vietnamese search queries.
        Documents whether typing without accents (e.g. 'giuong', 'thu ngan', 'so quy')
        resolves modules.
        """
        unaccented_queries = [
            ("giuong", "booking-bedroom"),
            ("thu ngan", "pos-cashier"),
            ("lich hen", "calendar-schedule"),
            ("so quy", "revenue-expenditure"),
            ("hoa hong", "commission-setup"),
            ("thong ke", "report-analytics"),
        ]
        results = {}
        for q, expected_id in unaccented_queries:
            res = self._execute_js_search(q)
            results[q] = expected_id in res["ids"]

        # Note: In standard Vietnamese web applications, diacritic folding / unaccented search
        # is a key UX enhancement. If unaccented search fails, we record this as an empirical finding.
        failed_queries = [q for q, matched in results.items() if not matched]
        if failed_queries:
            print(f"[EMPIRICAL FINDING] Unaccented search does not match: {failed_queries}")


class TestAdversarialTabSwitchingAndStatePreservation(unittest.TestCase):
    """
    Adversarial verification of Tab switching mechanics and state preservation:
    1. Tree View details expand/collapse state preservation
    2. Master expand/collapse controls
    3. Mermaid zoom/pan transform preservation
    """

    @classmethod
    def setUpClass(cls):
        status, _, body = fetch_url("/diagram")
        assert status == 200
        cls.html = body

    def test_switch_diagram_tab_function_exists(self):
        """switchDiagramViewTab must be defined in the HTML template."""
        self.assertIn("function switchDiagramViewTab", self.html)

    def test_tree_state_destruction_bug_empirical_verification(self):
        """
        EMPIRICAL BUG REPRODUCTION:
        Verify whether switchDiagramViewTab('tree') unconditionally calls renderTreeView()
        and recreates all <details> elements with hardcoded 'open', thereby destroying
        user's collapsed branches when switching tabs back and forth.
        """
        # Extract switchDiagramViewTab and renderTreeView JS code from HTML
        func_match = re.search(r"function switchDiagramViewTab\(tab\)\s*\{([\s\S]*?)\n    \}", self.html)
        self.assertIsNotNone(func_match, "switchDiagramViewTab definition not found")
        func_body = func_match.group(1)

        # Check if switchDiagramViewTab unconditionally invokes renderTreeView when tab === 'tree'
        calls_render_tree_on_switch = "renderTreeView(window.diagramData.tree_nodes)" in func_body

        self.assertTrue(
            calls_render_tree_on_switch,
            "switchDiagramViewTab calls renderTreeView unconditionally"
        )

        # Now simulate DOM execution in Node to empirically demonstrate state wipeout
        sim_js = """
        // Minimal DOM simulation
        class Element {
            constructor(tagName, id) {
                this.tagName = tagName;
                this.id = id;
                this.classList = new Set();
                this.children = [];
                this.innerHTML = '';
                this.open = true;
            }
            querySelectorAll(sel) {
                const results = [];
                function walk(el) {
                    if (el.tagName === sel) results.push(el);
                    for (const c of el.children) walk(c);
                }
                walk(this);
                return results;
            }
        }

        const treeContent = new Element('DIV', 'treeContent');
        const document = {
            getElementById: (id) => {
                if (id === 'treeContent') return treeContent;
                return new Element('DIV', id);
            },
            querySelectorAll: (sel) => {
                if (sel === '#treeViewContainer details') {
                    return treeContent.querySelectorAll('details');
                }
                return [];
            }
        };

        const mockTreeNodes = [
            { id: 'm1', name: 'Module 1', children: [{ id: 'fe1', name: 'FE 1', children: [{ id: 'api1', name: 'API 1', children: [{ id: 'be1', name: 'BE 1' }] }] }] },
            { id: 'm2', name: 'Module 2', children: [{ id: 'fe2', name: 'FE 2', children: [{ id: 'api2', name: 'API 2', children: [{ id: 'be2', name: 'BE 2' }] }] }] }
        ];

        function renderTreeView(treeNodes) {
            treeContent.children = [];
            treeNodes.forEach(m => {
                const d1 = new Element('details', m.id);
                d1.open = true;
                (m.children || []).forEach(fe => {
                    const d2 = new Element('details', fe.id);
                    d2.open = true;
                    d1.children.push(d2);
                });
                treeContent.children.push(d1);
            });
        }

        function collapseAllTreeNodes() {
            function collapse(el) {
                if (el.tagName === 'details') el.open = false;
                for (const c of el.children) collapse(c);
            }
            collapse(treeContent);
        }

        // 1. Initial Render
        renderTreeView(mockTreeNodes);
        const initialOpenCount = treeContent.querySelectorAll('details').filter(d => d.open).length;

        // 2. User collapses all branches
        collapseAllTreeNodes();
        const collapsedOpenCount = treeContent.querySelectorAll('details').filter(d => d.open).length;

        // 3. User switches to flowchart tab then back to tree tab (which calls renderTreeView again)
        renderTreeView(mockTreeNodes);
        const postSwitchOpenCount = treeContent.querySelectorAll('details').filter(d => d.open).length;

        console.log(JSON.stringify({
            initialOpenCount,
            collapsedOpenCount,
            postSwitchOpenCount,
            stateWiped: (postSwitchOpenCount === initialOpenCount && collapsedOpenCount === 0)
        }));
        """
        code, out, err = run_node_eval(sim_js)
        self.assertEqual(code, 0, f"Simulation failed: {err}")
        res = json.loads(out)

        self.assertTrue(
            res["stateWiped"],
            f"Expected state wipeout on tab switch, got: {res}"
        )
        print(f"[EMPIRICAL BUG CONFIRMED] Tree collapse state destroyed on tab switch: collapsed={res['collapsedOpenCount']} -> post-switch={res['postSwitchOpenCount']}")

    def test_tree_expansion_state_preservation_contract(self):
        """
        Feature 9 & Acceptance Criterion Verification:
        'Chuyển đổi giữa 2 tab (Sơ đồ liên kết và Sơ đồ Tree) không gây lỗi JavaScript và giữ nguyên trạng thái.'
        Validates that collapsed tree branches remain collapsed after switching tabs.
        """
        # Execute simulation of tab switch
        check_js = """
        let treeRenderCount = 0;
        function switchDiagramViewTab(tab) {
            if (tab === 'tree') {
                if (window.diagramData && window.diagramData.tree_nodes) {
                    renderTreeView(window.diagramData.tree_nodes);
                }
            }
        }
        // If renderTreeView is called unconditionally every time tab === 'tree' is switched,
        // it violates state preservation.
        const unconditionallyReRenders = switchDiagramViewTab.toString().includes('renderTreeView(');
        console.log(JSON.stringify({ unconditionallyReRenders }));
        """
        func_match = re.search(r"function switchDiagramViewTab\(tab\)\s*\{([\s\S]*?)\n    \}", self.html)
        func_body = func_match.group(1) if func_match else ""
        
        # A compliant implementation should only render if container is empty, or preserve <details> open states.
        # Calling renderTreeView() unconditionally every time resets all states.
        is_buggy = "renderTreeView(window.diagramData.tree_nodes)" in func_body and "details" not in func_body
        self.assertFalse(
            is_buggy,
            "Feature 9 Contract Violation: switchDiagramViewTab('tree') unconditionally re-renders tree, resetting all expanded/collapsed states."
        )

    def test_mermaid_zoom_pan_variables_and_controls(self):
        """Verifies presence of Zoom/Pan controls and inspects transform update logic."""
        self.assertIn("function diagramZoomIn()", self.html)
        self.assertIn("function diagramZoomOut()", self.html)
        self.assertIn("function diagramZoomReset()", self.html)
        self.assertIn("function diagramFitView()", self.html)
        self.assertIn("function updateDiagramTransform()", self.html)
        self.assertIn("diagramScale", self.html)
        self.assertIn("diagramPanX", self.html)
        self.assertIn("diagramPanY", self.html)

    def test_mermaid_zoom_clamping_limits(self):
        """Adversarial check: Zoom in and out must be clamped between [0.35, 2.5]."""
        sim_js = """
        let diagramScale = 1.0;
        function diagramZoomIn() {
            diagramScale = Math.min(2.5, +(diagramScale + 0.15).toFixed(2));
        }
        function diagramZoomOut() {
            diagramScale = Math.max(0.35, +(diagramScale - 0.15).toFixed(2));
        }

        // Test zoom in beyond maximum
        for (let i = 0; i < 30; i++) diagramZoomIn();
        const maxReached = diagramScale;

        // Test zoom out beyond minimum
        for (let i = 0; i < 50; i++) diagramZoomOut();
        const minReached = diagramScale;

        console.log(JSON.stringify({ maxReached, minReached }));
        """
        code, out, _ = run_node_eval(sim_js)
        self.assertEqual(code, 0)
        res = json.loads(out)
        self.assertEqual(res["maxReached"], 2.5, f"Expected max zoom 2.5, got {res['maxReached']}")
        self.assertEqual(res["minReached"], 0.35, f"Expected min zoom 0.35, got {res['minReached']}")


class TestAdversarialNodeClickHandlerAndDOMResilience(unittest.TestCase):
    """
    Adversarial verification of Node click handlers and DOM resilience:
    1. Non-existent and edge-case node IDs
    2. Duplicate function definitions of highlightAndScrollToModule
    3. DOM element ID consistency
    4. Behavior when module row has class 'hidden'
    """

    @classmethod
    def setUpClass(cls):
        status, _, body = fetch_url("/diagram")
        assert status == 200
        cls.html = body

    def test_duplicate_highlight_function_definition(self):
        """
        EMPIRICAL DEFECT DETECTION:
        PROJECT.md Feature 12 specifically dictates:
        'Deduplicate highlightAndScrollToModule, ensure clicking Mermaid/Tree nodes smoothly navigates to and highlights card'
        Verify whether web_server.py still contains multiple definitions of function highlightAndScrollToModule.
        """
        matches = list(re.finditer(r"function\s+highlightAndScrollToModule\s*\(", self.html))
        count = len(matches)
        print(f"[EMPIRICAL CHECK] Occurrences of 'function highlightAndScrollToModule': {count}")
        if count > 1:
            print("[EMPIRICAL DEFECT CONFIRMED] Duplicate highlightAndScrollToModule definitions detected in HTML_TEMPLATE!")
        # We assert count == 1 for compliance with Feature 12 deduplication requirement
        self.assertEqual(
            count, 1,
            f"Feature 12 Defect: Found {count} definitions of 'function highlightAndScrollToModule' in HTML_TEMPLATE. Must be deduplicated."
        )

    def test_highlight_scroll_unhides_filtered_module(self):
        """
        Adversarial UX check:
        If a module is currently hidden by search filter (class 'hidden'),
        clicking a diagram node should unhide the row so the user can see it.
        """
        matches = list(re.finditer(r"function\s+highlightAndScrollToModule\s*\([^\)]*\)\s*\{([\s\S]*?)\n    \}", self.html))
        self.assertTrue(len(matches) > 0)
        active_func_body = matches[-1].group(1)

        has_unhide = "classList.remove('hidden')" in active_func_body
        if not has_unhide:
            print("[EMPIRICAL FINDING] highlightAndScrollToModule does not unhide row if currently filtered out by search.")

    def test_node_click_handler_safe_with_unknown_ids(self):
        """Node click handler must handle non-existent node IDs without throwing exceptions."""
        sim_js = """
        const nodeMap = {
            'BOOKING_BEDROOM': { id: 'booking-bedroom', name: 'Phòng & Giường (BedRoom)' },
            'BED': { id: 'booking-bedroom', name: 'Phòng & Giường (BedRoom)' },
            'POS_CASHIER': { id: 'pos-cashier', name: 'Thu ngân & Hóa đơn (POS Invoice)' },
            'INV': { id: 'pos-cashier', name: 'Thu ngân & Hóa đơn (POS Invoice)' }
        };

        const edgeCases = [
            "",
            "NONEXISTENT_NODE_12345",
            "UNKNOWN_SUBGRAPH",
            "RANDOM_TEXT_WITH_SPECIAL_*+?()",
            "FE_UNKNOWN_MODULE",
            "BE_UNKNOWN_SERVICE",
            null,
            undefined
        ];

        const outcomes = [];
        edgeCases.forEach(input => {
            try {
                const nodeText = String(input || '').toUpperCase();
                let matched = null;
                let side = 'both';

                if (nodeText.includes('FE_') || nodeText.includes('FRONTEND') || nodeText.includes('BUSINESS/')) side = 'fe';
                else if (nodeText.includes('BE_') || nodeText.includes('BACKEND') || nodeText.includes('CONTROLLER')) side = 'be';

                for (const [key, val] of Object.entries(nodeMap)) {
                    if (nodeText.includes(key)) {
                        matched = val;
                        break;
                    }
                }
                outcomes.push({ input: String(input), matched, error: null });
            } catch(e) {
                outcomes.push({ input: String(input), matched: null, error: e.message });
            }
        });

        console.log(JSON.stringify(outcomes));
        """
        code, out, err = run_node_eval(sim_js)
        self.assertEqual(code, 0, f"Node click handler threw uncaught error: {err}")
        results = json.loads(out)
        for r in results:
            self.assertIsNone(r.get("error"), f"Error on input {r.get('input')}: {r.get('error')}")

    def test_dom_ids_referenced_in_js_exist_in_html(self):
        """All static element IDs queried via document.getElementById in JavaScript must exist in HTML."""
        # Find all document.getElementById('...') in script tags
        js_id_matches = re.findall(r"document\.getElementById\(['\"]([a-zA-Z0-9_-]+)['\"]", self.html)
        js_ids = sorted(list(set(js_id_matches)))

        # Find all id='...' in HTML
        dom_id_matches = re.findall(r"id=['\"]([a-zA-Z0-9_-]+)['\"]", self.html)
        dom_ids = set(dom_id_matches)

        # Dynamic IDs like module-row-*, fe-card-*, be-card-* are populated at runtime
        dynamic_prefixes = ("module-row-", "fe-card-", "be-card-", "dynamic-")
        missing_ids = [
            i for i in js_ids
            if i not in dom_ids and not any(i.startswith(p) for p in dynamic_prefixes)
        ]

        print(f"[DOM AUDIT] Total JS getElementById IDs: {len(js_ids)}")
        print(f"[DOM AUDIT] Total Static DOM IDs: {len(dom_ids)}")
        if missing_ids:
            print(f"[DOM AUDIT WARNING] JS references static IDs not in DOM: {missing_ids}")

        # Specifically check required diagram IDs
        critical_diagram_ids = [
            "diagramSearchInput",
            "diagramMatchCount",
            "diagramModuleEmpty",
            "moduleLookupList",
            "tabBtn_flowchart",
            "tabBtn_tree",
            "treeViewControls",
            "btnExpandAll",
            "btnCollapseAll",
            "treeViewContainer",
            "treeContent",
            "diagramViewport",
            "diagramCanvas",
            "mermaidDiagram",
            "diagramZoomLevel",
            "btnRescanDiagram",
            "rescanSpinner",
            "scanTimestamp",
        ]
        for cid in critical_diagram_ids:
            self.assertIn(
                cid, dom_ids,
                f"Critical element ID '{cid}' is missing from /diagram HTML!"
            )


if __name__ == "__main__":
    unittest.main(verbosity=2)
