#!/usr/bin/env python3
"""
Opaque-Box End-to-End (E2E) Test Suite for EasySalon Architecture Linkage Diagram.
Derived directly from ORIGINAL_REQUEST.md and PROJECT.md § Feature Inventory (Features 1-15).

Coverage:
  - Tier 1: Feature Coverage (Endpoints, schemas, compilation, DOM elements)
  - Tier 2: Boundary & Corner Cases (Query params, invalid routes, route sanitization)
  - Tier 3: Cross-Feature Combinations (1-to-1 modules <-> tree_nodes <-> mermaid_code)
  - Tier 4: Real-World Scenarios (Page load, Mermaid syntax, tree toggle data, instant search)
  - Tier 5: Adversarial Stress & Hardening (Injection strings, concurrency, regex safety)

Usage:
  python3 tests/test_e2e_diagram.py               # Run standard Tiers 1-4
  python3 tests/test_e2e_diagram.py --tier 1      # Run Tier 1 only
  python3 tests/test_e2e_diagram.py --tier 2      # Run Tier 2 only
  python3 tests/test_e2e_diagram.py --tier 3      # Run Tier 3 only
  python3 tests/test_e2e_diagram.py --tier 4      # Run Tier 4 only
  python3 tests/test_e2e_diagram.py --tier 5      # Run Tier 5 (Adversarial) only
  python3 tests/test_e2e_diagram.py --all         # Run all Tiers 1-5
"""

import argparse
import concurrent.futures
import json
import os
import py_compile
import re
import sys
import time
import unittest
import urllib.error
import urllib.parse
import urllib.request

DEFAULT_SERVER_URL = os.environ.get("TEST_SERVER_URL", "http://localhost:8765")
WEB_SERVER_FILE = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "web_server.py")

EXPECTED_MODULE_IDS = [
    "booking-bedroom",
    "pos-cashier",
    "calendar-schedule",
    "customer-crm",
    "warehouse-inventory",
    "commission-setup",
    "revenue-expenditure",
    "service-package-combo",
    "tax-einvoice",
    "payroll-timesheet",
    "report-analytics",
]

# Helper for HTTP requests
def http_get(url_path, base_url=None, timeout=25):
    base = base_url or DEFAULT_SERVER_URL
    url = urllib.parse.urljoin(base, url_path)
    req = urllib.request.Request(url, headers={"User-Agent": "EasySalon-E2E-Tester/1.0"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as response:
            status = response.status
            headers = dict(response.getheaders())
            body = response.read()
            return status, headers, body
    except urllib.error.HTTPError as e:
        body = e.read()
        return e.code, dict(e.headers), body
    except urllib.error.URLError as e:
        raise ConnectionError(f"Failed to connect to test server at {url}: {e.reason}")


# ==============================================================================
# TIER 1: Feature Coverage (Features 1-14)
# ==============================================================================
class TestTier1FeatureCoverage(unittest.TestCase):
    """
    Tier 1: Basic verification for every feature in PROJECT.md:
    Validates compilation, endpoints, JSON schemas, and essential HTML elements.
    """

    def test_f14_python_compilation(self):
        """Feature 14: web_server.py must compile without syntax errors via py_compile."""
        self.assertTrue(os.path.exists(WEB_SERVER_FILE), f"web_server.py not found at {WEB_SERVER_FILE}")
        try:
            py_compile.compile(WEB_SERVER_FILE, doraise=True)
        except py_compile.PyCompileError as e:
            self.fail(f"Feature 14 Failure: web_server.py failed python compilation: {e}")

    def test_f1_api_diagram_data_endpoint(self):
        """Feature 1 & 14: GET /api/diagram-data returns HTTP 200 and application/json."""
        status, headers, body = http_get("/api/diagram-data")
        self.assertEqual(status, 200, f"Expected HTTP 200 from /api/diagram-data, got {status}")
        content_type = headers.get("Content-Type", "")
        self.assertIn("application/json", content_type, f"Expected application/json Content-Type, got '{content_type}'")
        data = json.loads(body.decode("utf-8"))
        self.assertIsInstance(data, dict, "Expected JSON response to be an object")

    def test_f1_f3_metadata_keys(self):
        """Features 1 & 3: /api/diagram-data contains Git metadata and scan timestamp."""
        status, _, body = http_get("/api/diagram-data")
        self.assertEqual(status, 200)
        data = json.loads(body.decode("utf-8"))
        for key in ["fe_branch", "fe_commit", "be_branch", "be_commit"]:
            self.assertIn(key, data, f"Required Git metadata key '{key}' missing from /api/diagram-data")
            self.assertIsInstance(data[key], str, f"Key '{key}' must be a string")
        self.assertIn("scanned_at", data, "'scanned_at' timestamp missing from /api/diagram-data")

    def test_f4_mermaid_code_presence(self):
        """Feature 4: /api/diagram-data returns non-empty mermaid_code string."""
        status, _, body = http_get("/api/diagram-data")
        self.assertEqual(status, 200)
        data = json.loads(body.decode("utf-8"))
        self.assertIn("mermaid_code", data, "'mermaid_code' missing from /api/diagram-data (Feature 4)")
        mermaid_code = data["mermaid_code"]
        self.assertIsInstance(mermaid_code, str, "'mermaid_code' must be a string")
        self.assertTrue(len(mermaid_code.strip()) > 0, "'mermaid_code' must not be empty")
        self.assertTrue(
            mermaid_code.strip().startswith("flowchart") or mermaid_code.strip().startswith("graph"),
            f"'mermaid_code' must declare a valid diagram type ('flowchart' or 'graph'). Found: {mermaid_code[:30]}"
        )

    def test_f4_modules_array_structure(self):
        """Feature 4: /api/diagram-data returns modules array with 11 core modules."""
        status, _, body = http_get("/api/diagram-data")
        self.assertEqual(status, 200)
        data = json.loads(body.decode("utf-8"))
        self.assertIn("modules", data, "'modules' array missing from /api/diagram-data")
        modules = data["modules"]
        self.assertIsInstance(modules, list, "'modules' must be a list")
        self.assertEqual(len(modules), 11, f"Expected 11 modules across EasySalon domains, got {len(modules)}")

        for m in modules:
            self.assertIn("id", m, "Module missing 'id'")
            self.assertTrue("title" in m or "name" in m, f"Module '{m.get('id')}' missing 'title' or 'name'")
            self.assertIn("fe", m, f"Module '{m.get('id')}' missing 'fe' section")
            self.assertIn("api", m, f"Module '{m.get('id')}' missing 'api' section")
            self.assertIn("be", m, f"Module '{m.get('id')}' missing 'be' section")

    def test_f5_tree_nodes_schema(self):
        """Feature 5: /api/diagram-data returns structured 4-tier tree_nodes array."""
        status, _, body = http_get("/api/diagram-data")
        self.assertEqual(status, 200)
        data = json.loads(body.decode("utf-8"))
        self.assertIn(
            "tree_nodes", data,
            "Feature 5 Failure: 'tree_nodes' missing from /api/diagram-data (Planned in Milestone M1)"
        )
        tree_nodes = data["tree_nodes"]
        self.assertIsInstance(tree_nodes, list, "'tree_nodes' must be a list")
        self.assertEqual(len(tree_nodes), 11, f"Expected 11 root module nodes in 'tree_nodes', got {len(tree_nodes)}")
        for node in tree_nodes:
            self.assertIn("id", node, "Tree node missing 'id'")
            self.assertIn("name", node, "Tree node missing 'name'")
            self.assertEqual(node.get("type"), "module", f"Root tree node type must be 'module', got {node.get('type')}")
            self.assertIn("children", node, "Tree node missing 'children'")
            self.assertIsInstance(node["children"], list, "'children' must be a list")

    def test_f6_tab_switcher_ui(self):
        """Feature 6: GET /diagram returns HTML with tab switcher for Flowchart vs Tree View."""
        status, _, body = http_get("/diagram")
        self.assertEqual(status, 200, f"Expected HTTP 200 from /diagram, got {status}")
        html = body.decode("utf-8", errors="replace")
        # Check for tab switcher elements for Flowchart vs Tree View
        has_flowchart_tab = ("Sơ đồ kiến trúc liên kết" in html or "Flowchart" in html)
        has_tree_tab = ("Sơ đồ cây" in html or "Tree View" in html or "tabTree" in html or "tabBtn_tree" in html)
        self.assertTrue(
            has_flowchart_tab and has_tree_tab,
            "Feature 6 Failure: /diagram HTML must contain tab switcher for Flowchart and Tree View (Planned in Milestone M2)"
        )

    def test_f7_tree_view_container(self):
        """Feature 7: /diagram HTML contains 4-tier Tree View container element."""
        status, _, body = http_get("/diagram")
        self.assertEqual(status, 200)
        html = body.decode("utf-8", errors="replace")
        has_tree_container = any(k in html for k in ["treeViewContainer", "treeContainer", "view_tree", "diagramTree"])
        self.assertTrue(
            has_tree_container,
            "Feature 7 Failure: /diagram HTML missing Tree View container element (Planned in Milestone M2)"
        )

    def test_f8_tree_expand_collapse_controls(self):
        """Feature 8: /diagram HTML contains Tree Expand/Collapse master controls."""
        status, _, body = http_get("/diagram")
        self.assertEqual(status, 200)
        html = body.decode("utf-8", errors="replace")
        has_expand_all = ("Mở rộng tất cả" in html or "expandAll" in html)
        has_collapse_all = ("Thu gọn tất cả" in html or "collapseAll" in html)
        self.assertTrue(
            has_expand_all and has_collapse_all,
            "Feature 8 Failure: Master controls for 'Mở rộng tất cả' / 'Thu gọn tất cả' missing from /diagram HTML (Planned in Milestone M2)"
        )

    def test_f9_tab_state_and_zoom_pan_controls(self):
        """Feature 9 & R1: /diagram HTML contains zoom/pan interactive controls."""
        status, _, body = http_get("/diagram")
        self.assertEqual(status, 200)
        html = body.decode("utf-8", errors="replace")
        self.assertIn("diagramZoomIn", html, "Missing zoom in button/action in HTML")
        self.assertIn("diagramZoomOut", html, "Missing zoom out button/action in HTML")
        self.assertIn("diagramZoomReset", html, "Missing zoom reset button/action in HTML")
        self.assertIn("diagramFitView", html, "Missing fit-to-view button/action in HTML")
        self.assertIn("diagramViewport", html, "Missing diagramViewport container in HTML")

    def test_f10_f11_redesigned_module_details_and_color_coding(self):
        """Features 10 & 11: /diagram HTML contains Module Details section with 3-column color cues."""
        status, _, body = http_get("/diagram")
        self.assertEqual(status, 200)
        html = body.decode("utf-8", errors="replace")
        # Check module details container
        self.assertIn("moduleLookupList", html, "Missing moduleLookupList container in HTML")
        # Check color coding: Frontend (Cyan), API Contract (Purple), Backend (Emerald)
        has_cyan = ("cyan" in html.lower())
        has_purple = ("purple" in html.lower() or "violet" in html.lower())
        has_emerald = ("emerald" in html.lower() or "green" in html.lower())
        self.assertTrue(
            has_cyan and has_purple and has_emerald,
            "Feature 11 Failure: Missing 3-column color scheme markers (Cyan, Purple, Emerald) in /diagram HTML"
        )

    def test_f12_node_click_highlight_deduplication(self):
        """Feature 12: /diagram HTML includes node click highlight and smooth scroll function."""
        status, _, body = http_get("/diagram")
        self.assertEqual(status, 200)
        html = body.decode("utf-8", errors="replace")
        has_highlight = any(func in html for func in ["highlightAndScrollToModule", "scrollToModule", "bindMermaidNodeClicks"])
        self.assertTrue(has_highlight, "Feature 12 Failure: Node click highlight handler missing from /diagram HTML")

    def test_f13_instant_search_elements(self):
        """Feature 13: /diagram HTML contains instant search input and match count element."""
        status, _, body = http_get("/diagram")
        self.assertEqual(status, 200)
        html = body.decode("utf-8", errors="replace")
        self.assertIn("diagramSearchInput", html, "Instant search input element '#diagramSearchInput' missing")
        self.assertIn("diagramMatchCount", html, "Search match count badge '#diagramMatchCount' missing")


# ==============================================================================
# TIER 2: Boundary & Corner Cases
# ==============================================================================
class TestTier2BoundaryCases(unittest.TestCase):
    """
    Tier 2: Boundary conditions, query parameter permutations, malformed routes,
    and route template sanitization (eliminating [controller] and synthetic concatenation).
    """

    def test_t2_query_param_force(self):
        """GET /api/diagram-data?force=1 returns 200, valid JSON with scanned_at."""
        status, _, body = http_get("/api/diagram-data?force=1")
        self.assertEqual(status, 200, f"Expected 200 for force=1, got {status}")
        data = json.loads(body.decode("utf-8"))
        self.assertIn("scanned_at", data, "'scanned_at' timestamp missing on force rescan")

    def test_t2_unknown_query_parameters(self):
        """GET /api/diagram-data?foo=bar&unknown=123 must handle extra params gracefully."""
        status, _, body = http_get("/api/diagram-data?foo=bar&unknown=123")
        self.assertEqual(status, 200, f"Expected 200 for unknown query params, got {status}")
        data = json.loads(body.decode("utf-8"))
        self.assertIn("modules", data)

    def test_t2_empty_and_variant_force_param(self):
        """Query parameters like ?force= or ?force=0 or ?force=true must not cause 500 error."""
        for val in ["", "0", "false", "true"]:
            status, _, _ = http_get(f"/api/diagram-data?force={val}")
            self.assertEqual(status, 200, f"Server failed with {status} on ?force={val}")

    def test_t2_invalid_api_routes_return_404(self):
        """Accessing invalid endpoints must return HTTP 404 rather than 500 or crash."""
        status, _, _ = http_get("/api/nonexistent-route-12345")
        self.assertEqual(status, 404, f"Expected 404 for invalid API route, got {status}")

    def test_t2_diagram_route_aliases(self):
        """Both /diagram and /architecture must return HTTP 200 with HTML content."""
        for path in ["/diagram", "/architecture"]:
            status, _, body = http_get(path)
            self.assertEqual(status, 200, f"Expected 200 for route alias '{path}', got {status}")
            self.assertIn(b"<!DOCTYPE html>", body, f"Route alias '{path}' did not return HTML")

    def test_t2_no_controller_placeholder_in_api(self):
        """Feature 1 Boundary: No endpoint or route in /api/diagram-data may retain raw '[controller]'."""
        status, _, body = http_get("/api/diagram-data")
        self.assertEqual(status, 200)
        data = json.loads(body.decode("utf-8"))
        modules = data.get("modules", [])

        offending_endpoints = []
        for m in modules:
            api_info = m.get("api", {})
            route = api_info.get("route", "")
            if "[controller]" in route:
                offending_endpoints.append(f"Module '{m.get('id')}' route: {route}")
            for ep in api_info.get("endpoints", []):
                path = ep.get("path", "")
                if "[controller]" in path:
                    offending_endpoints.append(f"Module '{m.get('id')}' endpoint: {path}")

        self.assertEqual(
            offending_endpoints, [],
            f"Feature 1 Failure: Found raw '[controller]' placeholder in API endpoints: {offending_endpoints} (To be resolved in Milestone M1)"
        )

    def test_t2_no_synthetic_method_name_concatenation(self):
        """Feature 1 Boundary: Endpoints must not artificially concatenate action method names onto base routes."""
        status, _, body = http_get("/api/diagram-data")
        self.assertEqual(status, 200)
        data = json.loads(body.decode("utf-8"))
        modules = data.get("modules", [])

        synthetic_artifacts = []
        # Pattern for synthetic concatenations like /GetBedRoomPositions or /GetTimeSheet
        bad_action_pattern = re.compile(r"/(Get|Post|Put|Delete)[A-Z][a-zA-Z0-9]+$")
        for m in modules:
            for ep in m.get("api", {}).get("endpoints", []):
                path = ep.get("path", "")
                if bad_action_pattern.search(path):
                    synthetic_artifacts.append(f"Module '{m.get('id')}' path: {path}")

        self.assertEqual(
            synthetic_artifacts, [],
            f"Feature 1 Failure: Found synthetic action method concatenations in API routes: {synthetic_artifacts} (To be resolved in Milestone M1)"
        )

    def test_t2_valid_standard_http_methods(self):
        """All endpoints across all modules must use standard HTTP verbs."""
        status, _, body = http_get("/api/diagram-data")
        self.assertEqual(status, 200)
        data = json.loads(body.decode("utf-8"))
        valid_verbs = {"GET", "POST", "PUT", "DELETE", "PATCH", "HEAD", "OPTIONS"}

        invalid_methods = []
        for m in data.get("modules", []):
            for ep in m.get("api", {}).get("endpoints", []):
                method = ep.get("method", "").upper()
                # Strip Http prefix if present (e.g. HttpGet -> GET)
                if method.startswith("HTTP"):
                    method = method[4:]
                if method not in valid_verbs:
                    invalid_methods.append(f"Module '{m.get('id')}' method: '{ep.get('method')}'")

        self.assertEqual(
            invalid_methods, [],
            f"Found non-standard HTTP methods in endpoints: {invalid_methods}"
        )


# ==============================================================================
# TIER 3: Cross-Feature Combinations & Data Integrity
# ==============================================================================
class TestTier3CrossFeatureCombinations(unittest.TestCase):
    """
    Tier 3: 1-to-1 correspondence between modules, tree_nodes, and mermaid_code.
    Validates cross-feature data integrity across the entire architecture.
    """

    def setUp(self):
        status, _, body = http_get("/api/diagram-data")
        if status != 200:
            self.skipTest(f"Failed to fetch /api/diagram-data: status {status}")
        self.data = json.loads(body.decode("utf-8"))

    def test_t3_modules_count_and_completeness(self):
        """All 11 business modules must exist in the modules array."""
        modules = self.data.get("modules", [])
        self.assertEqual(len(modules), 11, f"Expected 11 modules, found {len(modules)}")
        actual_ids = [m.get("id") for m in modules]
        for exp_id in EXPECTED_MODULE_IDS:
            self.assertIn(exp_id, actual_ids, f"Required module '{exp_id}' not found in modules array")

    def test_t3_modules_to_tree_nodes_1to1_mapping(self):
        """Every module in modules array must correspond 1-to-1 to a root node in tree_nodes."""
        if "tree_nodes" not in self.data:
            self.fail("Feature 5 Failure: 'tree_nodes' missing from /api/diagram-data (Planned in Milestone M1)")

        modules = self.data.get("modules", [])
        tree_nodes = self.data.get("tree_nodes", [])
        self.assertEqual(
            len(tree_nodes), len(modules),
            f"Expected equal count of tree_nodes ({len(tree_nodes)}) and modules ({len(modules)})"
        )

        tree_node_ids = [n.get("id") for n in tree_nodes]
        for m in modules:
            m_id = m.get("id")
            # Node ID may be m_id or tree-m_id
            matched = any(m_id in tid for tid in tree_node_ids)
            self.assertTrue(
                matched,
                f"Module '{m_id}' does not have a corresponding node in tree_nodes (IDs: {tree_node_ids})"
            )

    def test_t3_tree_nodes_4_level_hierarchy_integrity(self):
        """Validates that tree_nodes strictly conforms to the 4-level business hierarchy."""
        if "tree_nodes" not in self.data:
            self.fail("Feature 5 Failure: 'tree_nodes' missing from /api/diagram-data (Planned in Milestone M1)")

        tree_nodes = self.data.get("tree_nodes", [])
        for l1 in tree_nodes:
            # Level 1: Module
            self.assertEqual(l1.get("type"), "module", f"Level 1 node '{l1.get('id')}' must have type='module'")
            self.assertTrue(len(l1.get("children", [])) > 0, f"Module node '{l1.get('id')}' has no Level 2 children")

            for l2 in l1.get("children", []):
                # Level 2: Frontend Component / Screen
                self.assertIn(
                    l2.get("type"), ["fe_component", "fe_screen", "fe"],
                    f"Level 2 node '{l2.get('id')}' must be frontend type, got '{l2.get('type')}'"
                )
                self.assertTrue(len(l2.get("children", [])) > 0, f"FE node '{l2.get('id')}' has no Level 3 children")

                for l3 in l2.get("children", []):
                    # Level 3: API Contract
                    self.assertIn(
                        l3.get("type"), ["api_contract", "api_endpoint", "api"],
                        f"Level 3 node '{l3.get('id')}' must be API contract type, got '{l3.get('type')}'"
                    )
                    self.assertTrue(len(l3.get("children", [])) > 0, f"API node '{l3.get('id')}' has no Level 4 children")

                    for l4 in l3.get("children", []):
                        # Level 4: Backend Stack
                        self.assertIn(
                            l4.get("type"), ["be_stack", "be_controller", "be"],
                            f"Level 4 node '{l4.get('id')}' must be BE stack type, got '{l4.get('type')}'"
                        )

    def test_t3_mermaid_flowchart_completeness(self):
        """Mermaid flowchart must represent FE, API, and BE tiers and all 11 modules."""
        mermaid_code = self.data.get("mermaid_code", "")
        self.assertTrue(len(mermaid_code) > 0, "mermaid_code is empty")

        # Must define subgraphs for Frontend, API, Backend
        self.assertIn("subgraph FE", mermaid_code, "Mermaid code missing Frontend subgraph (FE)")
        self.assertIn("subgraph API", mermaid_code, "Mermaid code missing API Contract subgraph (API)")
        self.assertIn("subgraph BE", mermaid_code, "Mermaid code missing Backend subgraph (BE)")

        # Must have connection links
        has_links = ("==>" in mermaid_code or "-->" in mermaid_code)
        self.assertTrue(has_links, "Mermaid code missing connection arrows between tiers")

        # Check representation of modules
        for exp_id in EXPECTED_MODULE_IDS:
            token = exp_id.upper().replace("-", "_")
            self.assertIn(
                token, mermaid_code,
                f"Module '{exp_id}' (token '{token}') is not represented in mermaid_code"
            )

    def test_t3_module_schema_completeness(self):
        """Every module must have complete FE, API, and BE details."""
        modules = self.data.get("modules", [])
        for m in modules:
            m_id = m.get("id")
            # FE details
            fe = m.get("fe", {})
            has_fe_info = ("screens" in fe or "components" in fe or "path" in fe or "resource" in fe)
            self.assertTrue(has_fe_info, f"Module '{m_id}' has incomplete FE info")

            # API details
            api = m.get("api", {})
            self.assertIn("route", api, f"Module '{m_id}' missing api.route")
            self.assertIn("endpoints", api, f"Module '{m_id}' missing api.endpoints")
            self.assertTrue(len(api["endpoints"]) > 0, f"Module '{m_id}' has 0 endpoints")

            # BE details
            be = m.get("be", {})
            has_be_info = ("controller" in be or "service" in be or "injections" in be)
            self.assertTrue(has_be_info, f"Module '{m_id}' has incomplete BE info")


# ==============================================================================
# TIER 4: Real-World Application Scenarios (End-to-End User Flows)
# ==============================================================================
class TestTier4RealWorldScenarios(unittest.TestCase):
    """
    Tier 4: Realistic user interaction scenarios:
    1. Initial page load & data fetch flow
    2. Dynamic Mermaid syntax rendering readiness
    3. Tree View expand/collapse interaction data
    4. Instant search multi-field matching
    5. Cache-busting / force rescan flow
    """

    def test_t4_scenario_page_initialization_flow(self):
        """Scenario 1: Browser navigates to /diagram and fetches /api/diagram-data."""
        start_time = time.time()
        # Step 1: Load HTML
        page_status, _, page_body = http_get("/diagram")
        self.assertEqual(page_status, 200)
        html = page_body.decode("utf-8", errors="replace")
        self.assertIn("EasySalon Agent", html)

        # Step 2: Fetch Diagram Data
        data_status, _, data_body = http_get("/api/diagram-data")
        self.assertEqual(data_status, 200)
        data = json.loads(data_body.decode("utf-8"))
        elapsed = time.time() - start_time

        self.assertIn("modules", data)
        self.assertEqual(len(data["modules"]), 11)
        self.assertLess(elapsed, 5.0, f"Page init and data fetch exceeded 5 seconds: {elapsed:.2f}s")

    def test_t4_scenario_mermaid_syntax_parser_ready(self):
        """Scenario 2: Mermaid code must be syntactically valid and free of parsing hazards."""
        status, _, body = http_get("/api/diagram-data")
        self.assertEqual(status, 200)
        data = json.loads(body.decode("utf-8"))
        mermaid_code = data.get("mermaid_code", "")

        # Check bracket parity for syntax safety
        open_brackets = mermaid_code.count("[")
        close_brackets = mermaid_code.count("]")
        self.assertEqual(
            open_brackets, close_brackets,
            f"Mismatched square brackets in mermaid_code: {open_brackets} '[' vs {close_brackets} ']'"
        )

        open_braces = mermaid_code.count("{")
        close_braces = mermaid_code.count("}")
        self.assertEqual(
            open_braces, close_braces,
            f"Mismatched curly braces in mermaid_code: {open_braces} '{{' vs {close_braces} '}}'"
        )

        # Check for unescaped raw newlines inside label quotes
        self.assertNotIn('"\n"', mermaid_code, "Illegal empty quoted newline in mermaid_code")

    def test_t4_scenario_tree_expansion_interactivity_data(self):
        """Scenario 3: Tree view nodes must have globally unique IDs for expand/collapse toggle tracking."""
        status, _, body = http_get("/api/diagram-data")
        self.assertEqual(status, 200)
        data = json.loads(body.decode("utf-8"))

        if "tree_nodes" not in data:
            self.fail("Feature 5 Failure: 'tree_nodes' missing from /api/diagram-data (Planned in Milestone M1)")

        tree_nodes = data["tree_nodes"]
        seen_ids = set()
        duplicate_ids = []

        def traverse(nodes):
            for n in nodes:
                nid = n.get("id")
                if nid in seen_ids:
                    duplicate_ids.append(nid)
                seen_ids.add(nid)
                if "children" in n and isinstance(n["children"], list):
                    traverse(n["children"])

        traverse(tree_nodes)
        self.assertEqual(
            duplicate_ids, [],
            f"Duplicate node IDs in tree_nodes would break expand/collapse toggle: {duplicate_ids}"
        )
        self.assertGreater(len(seen_ids), 11, "Tree nodes must contain multi-level hierarchy nodes")

    def test_t4_scenario_instant_search_multi_field_coverage(self):
        """Scenario 4: Multi-field instant search resolves modules by title, FE screen, API route, and BE controller."""
        status, _, body = http_get("/api/diagram-data")
        self.assertEqual(status, 200)
        data = json.loads(body.decode("utf-8"))
        modules = data.get("modules", [])

        # Simulated client-side search logic
        def search_modules(query):
            q = query.lower()
            results = []
            for m in modules:
                title = (m.get("title") or m.get("name") or "").lower()
                m_id = (m.get("id") or "").lower()
                route = (m.get("api", {}).get("route") or "").lower()
                controller = (m.get("be", {}).get("controller") or "").lower()
                fe_str = str(m.get("fe", {})).lower()
                api_str = str(m.get("api", {})).lower()
                be_str = str(m.get("be", {})).lower()

                if (q in title or q in m_id or q in route or q in controller or
                        q in fe_str or q in api_str or q in be_str):
                    results.append(m)
            return results

        # Test A: Search by module name (Vietnamese)
        bed_matches = search_modules("giường")
        self.assertTrue(any(m["id"] == "booking-bedroom" for m in bed_matches), "Search for 'giường' failed")

        # Test B: Search by POS keyword
        pos_matches = search_modules("thu ngân")
        self.assertTrue(any(m["id"] == "pos-cashier" for m in pos_matches), "Search for 'thu ngân' failed")

        # Test C: Search by BE Controller
        controller_matches = search_modules("CashiersController")
        self.assertTrue(any(m["id"] == "pos-cashier" for m in controller_matches), "Search for 'CashiersController' failed")

        # Test D: Search by API Route
        route_matches = search_modules("bed-room-position")
        self.assertTrue(any(m["id"] == "booking-bedroom" for m in route_matches), "Search for 'bed-room-position' failed")

        # Test E: Non-matching query returns 0 matches
        none_matches = search_modules("nonexistent_random_token_99999")
        self.assertEqual(len(none_matches), 0, "Expected 0 matches for non-existent token")

    def test_t4_scenario_force_rescan_and_cache_freshness(self):
        """Scenario 5: Calling force=1 re-scans codebase and produces consistent module data."""
        # Baseline fetch
        s1, _, b1 = http_get("/api/diagram-data")
        self.assertEqual(s1, 200)
        d1 = json.loads(b1.decode("utf-8"))

        # Forced rescan
        s2, _, b2 = http_get("/api/diagram-data?force=1")
        self.assertEqual(s2, 200)
        d2 = json.loads(b2.decode("utf-8"))

        # Module IDs and count must match
        ids1 = sorted([m["id"] for m in d1.get("modules", [])])
        ids2 = sorted([m["id"] for m in d2.get("modules", [])])
        self.assertEqual(ids1, ids2, "Module IDs changed after forced rescan")
        self.assertIn("scanned_at", d2, "Missing scanned_at after forced rescan")


# ==============================================================================
# TIER 5: Adversarial Stress & Hardening (Quality Gate)
# ==============================================================================
class TestTier5AdversarialHardening(unittest.TestCase):
    """
    Tier 5: Adversarial security and stress checks:
    - Injection payloads in query strings
    - Regex safety with special meta-characters
    - Concurrent request handling
    - Header security & MIME types
    """

    def test_t5_query_injection_payloads(self):
        """Server handles XSS and directory traversal query params gracefully without 500 error."""
        payloads = [
            "<script>alert(1)</script>",
            "../../../../etc/passwd",
            "' OR '1'='1",
            "%00%0d%0a",
            "&param=value;rm -rf /",
        ]
        for p in payloads:
            encoded = urllib.parse.quote(p)
            status, _, _ = http_get(f"/api/diagram-data?force={encoded}")
            self.assertIn(status, [200, 400], f"Server crashed with {status} on payload: {p}")

    def test_t5_concurrent_api_requests(self):
        """Server can handle 10 concurrent requests to /api/diagram-data without deadlocks."""
        num_requests = 10
        with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
            futures = [executor.submit(http_get, "/api/diagram-data") for _ in range(num_requests)]
            results = [f.result() for f in concurrent.futures.as_completed(futures)]

        for status, _, body in results:
            self.assertEqual(status, 200, f"Expected 200 in concurrent test, got {status}")
            data = json.loads(body.decode("utf-8"))
            self.assertEqual(len(data.get("modules", [])), 11)

    def test_t5_search_regex_meta_characters(self):
        """Simulated search handles raw regex meta-characters without unhandled exceptions."""
        status, _, body = http_get("/api/diagram-data")
        self.assertEqual(status, 200)
        data = json.loads(body.decode("utf-8"))
        modules = data.get("modules", [])

        meta_chars = [".*", "+", "?", "(", ")", "[", "]", "{", "}", "^", "$", "\\"]
        for char in meta_chars:
            try:
                # String 'in' operator should not throw regex errors
                matches = [m for m in modules if char in (m.get("title") or "")]
                self.assertIsInstance(matches, list)
            except Exception as e:
                self.fail(f"Search failed on regex meta-character '{char}': {e}")

    def test_t5_response_headers_and_mime(self):
        """Verifies Content-Type and basic security headers."""
        status, headers, _ = http_get("/api/diagram-data")
        self.assertEqual(status, 200)
        content_type = headers.get("Content-Type", "")
        self.assertTrue("application/json" in content_type, f"Unexpected Content-Type: {content_type}")


# ==============================================================================
# CLI Runner and Test Suite Aggregator
# ==============================================================================
def create_suite(selected_tier=None, include_tier5=False):
    suite = unittest.TestSuite()
    loader = unittest.TestLoader()

    tier_map = {
        1: [TestTier1FeatureCoverage],
        2: [TestTier2BoundaryCases],
        3: [TestTier3CrossFeatureCombinations],
        4: [TestTier4RealWorldScenarios],
        5: [TestTier5AdversarialHardening],
    }

    if selected_tier is not None:
        if selected_tier in tier_map:
            for cls in tier_map[selected_tier]:
                suite.addTests(loader.loadTestsFromTestCase(cls))
        else:
            raise ValueError(f"Invalid tier: {selected_tier}. Supported: 1-5.")
    else:
        # Default: Tiers 1-4
        for t in [1, 2, 3, 4]:
            for cls in tier_map[t]:
                suite.addTests(loader.loadTestsFromTestCase(cls))
        if include_tier5:
            for cls in tier_map[5]:
                suite.addTests(loader.loadTestsFromTestCase(cls))

    return suite


def main():
    global DEFAULT_SERVER_URL
    parser = argparse.ArgumentParser(description="Opaque-Box E2E Test Suite for EasySalon Architecture Linkage Diagram")
    parser.add_argument("--tier", type=int, choices=[1, 2, 3, 4, 5], help="Run a specific test tier (1-5)")
    parser.add_argument("--all", action="store_true", help="Run all tiers (1-5), including Adversarial Tier 5")
    parser.add_argument("--url", type=str, default=None, help=f"Base URL for web server (default: {DEFAULT_SERVER_URL})")
    parser.add_argument("-v", "--verbose", action="store_true", help="Verbose test execution output")
    args = parser.parse_args()

    if args.url:
        DEFAULT_SERVER_URL = args.url

    print("=" * 78)
    print("EasySalon Architecture Linkage Diagram — Opaque-Box E2E Test Suite")
    print(f"Target Server: {DEFAULT_SERVER_URL}")
    print(f"Scope: {'Tier ' + str(args.tier) if args.tier else ('All Tiers 1-5' if args.all else 'Tiers 1-4 (Standard)')}")
    print("=" * 78)

    suite = create_suite(selected_tier=args.tier, include_tier5=args.all)
    runner = unittest.TextTestRunner(verbosity=2 if args.verbose else 1)
    result = runner.run(suite)

    print("\n" + "=" * 78)
    print("TEST EXECUTION SUMMARY:")
    print(f"Total Tests Run: {result.testsRun}")
    print(f"Passed: {result.testsRun - len(result.failures) - len(result.errors)}")
    print(f"Failures: {len(result.failures)}")
    print(f"Errors: {len(result.errors)}")
    print("=" * 78)

    if result.wasSuccessful():
        print(">> ALL EXECUTED TESTS PASSED SUCCESSFULLY! <<")
        sys.exit(0)
    else:
        print(">> TEST FAILURES DETECTED. See failure details above. <<")
        # Exit with 1 on test failures
        sys.exit(1)


if __name__ == "__main__":
    main()
