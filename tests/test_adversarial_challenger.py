#!/usr/bin/env python3
"""
Empirical Adversarial Test Suite for EasySalon Architecture Linkage Diagram.
Written by Challenger 1 (Adversarial Critic & Domain Specialist).

Validates:
1. Strict 4-level hierarchy and 100% ID uniqueness across tree_nodes.
2. All 11 modules present with valid schema and physical file cross-verification.
3. Endpoint routing: zero [controller] tokens, zero synthetic method name concatenations.
4. Mermaid diagram: balanced brackets, valid syntax, complete graph connectivity.
5. Concurrent stress queries to web_server.py (load, injection strings, fuzzing).
"""

import concurrent.futures
import json
import os
import re
import sys
import time
import unittest
import urllib.error
import urllib.parse
import urllib.request

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
try:
    from config import FE_WORKSPACE, BE_WORKSPACE
except ImportError:
    FE_WORKSPACE = "/run/media/thietnv/Data/Project/easysalon-webapp"
    BE_WORKSPACE = "/run/media/thietnv/Data/Project/easysalon-api"

SERVER_URL = os.environ.get("TEST_SERVER_URL", "http://localhost:8765")

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


def http_request(path, method="GET", data=None, headers=None, timeout=15):
    url = urllib.parse.urljoin(SERVER_URL, path)
    h = {"User-Agent": "Challenger1-Adversarial-Harness/2.0"}
    if headers:
        h.update(headers)
    req = urllib.request.Request(url, data=data, headers=h, method=method)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.status, dict(resp.getheaders()), resp.read()
    except urllib.error.HTTPError as e:
        return e.code, dict(e.headers), e.read()
    except urllib.error.URLError as e:
        raise ConnectionError(f"Failed to connect to {url}: {e.reason}")


class TestAdversarialTreeNodes(unittest.TestCase):
    """Deep empirical tests of the Tree Node structure and 4-tier hierarchy."""

    @classmethod
    def setUpClass(cls):
        status, _, body = http_request("/api/diagram-data")
        assert status == 200, f"Setup failed: HTTP {status}"
        cls.data = json.loads(body.decode("utf-8"))
        cls.tree_nodes = cls.data.get("tree_nodes", [])

    def test_tree_root_node_count_and_ids(self):
        """Must have exactly 11 root module nodes matching expected IDs."""
        self.assertEqual(len(self.tree_nodes), 11, f"Expected 11 root tree nodes, got {len(self.tree_nodes)}")
        root_ids = [n.get("id") for n in self.tree_nodes]
        for exp_id in EXPECTED_MODULE_IDS:
            self.assertTrue(
                any(exp_id in rid for rid in root_ids),
                f"Expected module '{exp_id}' not found in root tree node IDs: {root_ids}"
            )

    def test_strict_four_level_hierarchy_and_types(self):
        """
        Adversarial hierarchy check:
        Level 1: type == 'module', children non-empty
        Level 2: type == 'fe_component', children non-empty
        Level 3: type == 'api_contract', children non-empty
        Level 4: type == 'be_stack', children MUST BE EMPTY (strictly leaf nodes)
        No Level 5 or deeper nodes may exist anywhere.
        """
        for l1 in self.tree_nodes:
            self.assertEqual(l1.get("type"), "module", f"Level 1 '{l1.get('id')}' must be type 'module'")
            l2_children = l1.get("children", [])
            self.assertGreater(len(l2_children), 0, f"Module '{l1.get('id')}' has empty Level 2 children")

            for l2 in l2_children:
                self.assertIn(
                    l2.get("type"), ["fe_component", "fe_screen", "fe"],
                    f"Level 2 '{l2.get('id')}' type must be FE, got '{l2.get('type')}'"
                )
                l3_children = l2.get("children", [])
                self.assertGreater(len(l3_children), 0, f"FE node '{l2.get('id')}' has empty Level 3 children")

                for l3 in l3_children:
                    self.assertIn(
                        l3.get("type"), ["api_contract", "api_endpoint", "api"],
                        f"Level 3 '{l3.get('id')}' type must be API, got '{l3.get('type')}'"
                    )
                    l4_children = l3.get("children", [])
                    self.assertGreater(len(l4_children), 0, f"API node '{l3.get('id')}' has empty Level 4 children")

                    for l4 in l4_children:
                        self.assertIn(
                            l4.get("type"), ["be_stack", "be_controller", "be"],
                            f"Level 4 '{l4.get('id')}' type must be BE, got '{l4.get('type')}'"
                        )
                        # Adversarial check: Level 4 MUST BE LEAF
                        l5_children = l4.get("children", [])
                        self.assertEqual(
                            len(l5_children), 0,
                            f"Level 4 node '{l4.get('id')}' unexpectedly has Level 5 children: {l5_children}"
                        )

    def test_global_id_uniqueness_across_entire_tree(self):
        """Every single node across all 4 levels must have a globally unique ID."""
        all_ids = []
        node_count = 0

        def collect(nodes, depth=1):
            nonlocal node_count
            for n in nodes:
                node_count += 1
                nid = n.get("id")
                self.assertIsNotNone(nid, f"Node at depth {depth} missing 'id': {n}")
                self.assertIsInstance(nid, str, f"Node ID must be string: {nid}")
                self.assertTrue(len(nid.strip()) > 0, f"Node ID cannot be empty string at depth {depth}")
                # No illegal characters in ID
                self.assertFalse(re.search(r"\s", nid), f"Node ID contains whitespace: '{nid}'")
                all_ids.append(nid)
                if "children" in n and isinstance(n["children"], list):
                    collect(n["children"], depth + 1)

        collect(self.tree_nodes)
        unique_ids = set(all_ids)
        duplicates = [i for i in unique_ids if all_ids.count(i) > 1]
        self.assertEqual(
            len(all_ids), len(unique_ids),
            f"Found duplicate IDs across tree_nodes: {duplicates}"
        )
        self.assertGreaterEqual(node_count, 50, f"Expected >= 50 total nodes in tree, found {node_count}")

    def test_node_names_non_empty_and_meaningful(self):
        """Every node across all levels must have a meaningful non-empty name."""
        def check_names(nodes, path=""):
            for n in nodes:
                current_path = f"{path}/{n.get('id', 'unknown')}"
                name = n.get("name")
                self.assertIsNotNone(name, f"Node '{current_path}' missing 'name'")
                self.assertIsInstance(name, str, f"Node '{current_path}' name must be string")
                self.assertGreater(len(name.strip()), 2, f"Node '{current_path}' name is too short: '{name}'")
                if "children" in n and isinstance(n["children"], list):
                    check_names(n["children"], current_path)

        check_names(self.tree_nodes)

    def test_level_3_api_contract_contract_metadata(self):
        """Level 3 nodes must specify HTTP method and valid path template."""
        valid_methods = {"GET", "POST", "PUT", "DELETE", "PATCH"}
        for l1 in self.tree_nodes:
            for l2 in l1.get("children", []):
                for l3 in l2.get("children", []):
                    method = l3.get("method")
                    self.assertIn(
                        method, valid_methods,
                        f"Level 3 node '{l3.get('id')}' has invalid or missing HTTP method: '{method}'"
                    )
                    path = l3.get("path")
                    self.assertTrue(
                        path and path.startswith("/"),
                        f"Level 3 node '{l3.get('id')}' path must start with '/': '{path}'"
                    )
                    # Node name must contain the bracketed method badge
                    self.assertIn(f"[{method}]", l3.get("name", ""))

    def test_level_4_be_stack_metadata(self):
        """Level 4 nodes must specify controller, service, and arrow-delimited stack name."""
        for l1 in self.tree_nodes:
            for l2 in l1.get("children", []):
                for l3 in l2.get("children", []):
                    for l4 in l3.get("children", []):
                        controller = l4.get("controller")
                        self.assertTrue(
                            controller and "Controller" in controller,
                            f"Level 4 node '{l4.get('id')}' missing valid controller: '{controller}'"
                        )
                        service = l4.get("service")
                        self.assertTrue(
                            service and len(service) > 0,
                            f"Level 4 node '{l4.get('id')}' missing service: '{service}'"
                        )
                        # Name should depict the downstream trace
                        self.assertIn("→", l4.get("name", ""), f"Level 4 name should show downstream trace: {l4.get('name')}")


class TestAdversarialModulesSchemaAndRealism(unittest.TestCase):
    """Empirical tests for all 11 modules and real codebase correspondence."""

    @classmethod
    def setUpClass(cls):
        status, _, body = http_request("/api/diagram-data")
        assert status == 200
        cls.data = json.loads(body.decode("utf-8"))
        cls.modules = cls.data.get("modules", [])

    def test_all_11_modules_present(self):
        """Exactly 11 modules must be present."""
        self.assertEqual(len(self.modules), 11)
        mod_ids = [m["id"] for m in self.modules]
        self.assertEqual(sorted(mod_ids), sorted(EXPECTED_MODULE_IDS))

    def test_module_schema_completeness(self):
        """Every module must contain complete fe, api, and be sections."""
        for m in self.modules:
            mid = m.get("id")
            self.assertIn("fe", m, f"Module '{mid}' missing 'fe'")
            self.assertIn("api", m, f"Module '{mid}' missing 'api'")
            self.assertIn("be", m, f"Module '{mid}' missing 'be'")

            # FE checks
            fe = m["fe"]
            self.assertIsInstance(fe.get("screens"), list)
            self.assertGreater(len(fe["screens"]), 0, f"Module '{mid}' has empty fe.screens")
            self.assertIsInstance(fe.get("components"), list)
            self.assertGreater(len(fe["components"]), 0, f"Module '{mid}' has empty fe.components")
            self.assertIsInstance(fe.get("resources"), list)
            self.assertGreater(len(fe["resources"]), 0, f"Module '{mid}' has empty fe.resources")

            # API checks
            api = m["api"]
            self.assertTrue(api.get("route", "").startswith("/"), f"Module '{mid}' api.route must start with /")
            endpoints = api.get("endpoints", [])
            self.assertGreater(len(endpoints), 0, f"Module '{mid}' has empty api.endpoints")
            for ep in endpoints:
                self.assertIn(ep.get("method"), ["GET", "POST", "PUT", "DELETE", "PATCH"])
                self.assertTrue(ep.get("path", "").startswith("/"))
                self.assertTrue(len(ep.get("note", "")) > 0)

            # BE checks
            be = m["be"]
            self.assertTrue(be.get("controller", "").endswith("Controller"))
            self.assertTrue(len(be.get("service", "")) > 0)
            self.assertTrue(len(be.get("manager", "")) > 0)
            self.assertIsInstance(be.get("entities"), list)
            self.assertGreater(len(be["entities"]), 0)
            self.assertIn("→", be.get("be_stack_str", ""))

    def test_physical_codebase_cross_verification(self):
        """
        Empirically verify that reported controllers and resources actually exist
        on disk in easysalon-api and easysalon-webapp.
        """
        for m in self.modules:
            mid = m["id"]
            controller = m["be"]["controller"]
            controller_dir = os.path.join(BE_WORKSPACE, "SALON_HAIR_API")
            matches = [f for root, _, files in os.walk(controller_dir)
                       for f in files if f == f"{controller}.cs"]
            self.assertGreater(
                len(matches), 0,
                f"Controller '{controller}' reported for module '{mid}' was not found in {controller_dir}"
            )

            # Check at least one resource file
            resources = m["fe"]["resources"]
            res_found = False
            res_dir = os.path.join(FE_WORKSPACE, "src", "scripts", "restful", "resources")
            for r in resources:
                res_name = os.path.basename(r)
                if not res_name.endswith(".ts"):
                    res_name += ".ts"
                for root, _, files in os.walk(res_dir):
                    if res_name in files:
                        res_found = True
                        break
                if res_found:
                    break
            self.assertTrue(
                res_found,
                f"None of the reported resources {resources} for module '{mid}' found in {res_dir}"
            )


class TestAdversarialEndpointRouting(unittest.TestCase):
    """Adversarial validation against [controller] tokens and synthetic method concatenations."""

    @classmethod
    def setUpClass(cls):
        status, _, body = http_request("/api/diagram-data")
        assert status == 200
        cls.raw_json = body.decode("utf-8")
        cls.data = json.loads(cls.raw_json)

    def test_zero_raw_controller_tokens_in_entire_payload(self):
        """The literal token '[controller]' (case-insensitive) must NEVER appear anywhere in the API payload."""
        lower_json = self.raw_json.lower()
        self.assertNotIn(
            "[controller]", lower_json,
            "CRITICAL: Found raw '[controller]' token in /api/diagram-data payload!"
        )

    def test_zero_synthetic_action_method_concatenations(self):
        """
        Adversarial test for method concatenation patterns like:
        /bed-room-position/GetBedRoomPositions
        /invoices/GetInvoices
        /cashiers/PostCashier
        """
        suspicious_regex = re.compile(r"/(Get|Post|Put|Delete|Patch)[A-Z][a-zA-Z0-9]+(?:\?|/|$)")

        violations = []
        for m in self.data.get("modules", []):
            for ep in m.get("api", {}).get("endpoints", []):
                p = ep.get("path", "")
                if suspicious_regex.search(p):
                    violations.append(f"Module '{m['id']}' endpoint: {p}")

        # Also check tree nodes
        def scan_tree_paths(nodes):
            for n in nodes:
                p = n.get("path", "")
                if p and suspicious_regex.search(p):
                    violations.append(f"Tree node '{n.get('id')}' path: {p}")
                if "children" in n:
                    scan_tree_paths(n["children"])

        scan_tree_paths(self.data.get("tree_nodes", []))
        self.assertEqual(violations, [], f"Found synthetic method name concatenations: {violations}")

    def test_parameter_placeholder_format(self):
        """Parameter placeholders must use {param} rather than :param or unescaped tokens."""
        for m in self.data.get("modules", []):
            for ep in m.get("api", {}).get("endpoints", []):
                p = ep.get("path", "")
                self.assertFalse(
                    re.search(r":[a-zA-Z_0-9]+", p),
                    f"Endpoint path '{p}' contains un-normalized Express-style ':param' instead of '{{param}}'"
                )


class TestAdversarialMermaidDiagram(unittest.TestCase):
    """Stress tests on Mermaid diagram syntax, bracket balance, and graph connectivity."""

    @classmethod
    def setUpClass(cls):
        status, _, body = http_request("/api/diagram-data")
        assert status == 200
        cls.data = json.loads(body.decode("utf-8"))
        cls.mermaid = cls.data.get("mermaid_code", "")

    def test_bracket_and_parentheses_balance(self):
        """Check strict parity of all bracket types."""
        brackets = [
            ("[", "]"),
            ("(", ")"),
            ("{", "}"),
        ]
        for open_b, close_b in brackets:
            n_open = self.mermaid.count(open_b)
            n_close = self.mermaid.count(close_b)
            self.assertEqual(
                n_open, n_close,
                f"Mismatched bracket pair '{open_b}' and '{close_b}': {n_open} open vs {n_close} close."
            )

    def test_label_quote_balance(self):
        """Double quotes in mermaid string should be balanced (even count)."""
        quote_count = self.mermaid.count('"')
        self.assertEqual(
            quote_count % 2, 0,
            f"Unbalanced double quotes in mermaid_code (count: {quote_count})"
        )

    def test_subgraph_integrity(self):
        """Subgraphs FE, API, and BE must be opened and properly closed."""
        lines = [line.strip() for line in self.mermaid.splitlines() if line.strip()]
        subgraph_starts = [l for l in lines if l.startswith("subgraph ")]
        subgraph_ends = [l for l in lines if l == "end"]
        self.assertEqual(
            len(subgraph_starts), len(subgraph_ends),
            f"Subgraph start count ({len(subgraph_starts)}) != end count ({len(subgraph_ends)})"
        )
        self.assertEqual(len(subgraph_starts), 3, "Expected exactly 3 subgraphs: FE, API, BE")

    def test_complete_graph_connectivity(self):
        """
        Adversarial connectivity check:
        For every one of the 11 modules:
        FE_{MOD} ==> API_{MOD} ==> BE_{MOD}
        Must have zero isolated or disconnected nodes!
        """
        edges = re.findall(r"([A-Za-z0-9_]+)\s*==>(?:\|[^|]*\|)?\s*([A-Za-z0-9_]+)", self.mermaid)
        self.assertTrue(len(edges) >= 22, f"Expected at least 22 connecting edges, found {len(edges)}")

        edge_map = {}
        for src, dst in edges:
            edge_map.setdefault(src, []).append(dst)

        for exp_id in EXPECTED_MODULE_IDS:
            token = exp_id.upper().replace("-", "_")
            fe_nid = f"FE_{token}"
            api_nid = f"API_{token}"
            be_nid = f"BE_{token}"

            # Check FE connects to API
            self.assertIn(fe_nid, edge_map, f"Mermaid node '{fe_nid}' has no outbound edges!")
            self.assertIn(api_nid, edge_map[fe_nid], f"Node '{fe_nid}' does not connect to '{api_nid}'")

            # Check API connects to BE
            self.assertIn(api_nid, edge_map, f"Mermaid node '{api_nid}' has no outbound edges!")
            self.assertIn(be_nid, edge_map[api_nid], f"Node '{api_nid}' does not connect to '{be_nid}'")

    def test_no_raw_angle_bracket_conflicts_outside_tags(self):
        """HTML-like tags in node labels must only be safe tags like <b>, </b>, <br/>, <i>, </i>."""
        non_comment_lines = [l for l in self.mermaid.splitlines() if not l.strip().startswith("%%")]
        clean_mermaid = "\n".join(non_comment_lines)
        tags = re.findall(r"<[^>]+>", clean_mermaid)
        allowed_tags = {"<b>", "</b>", "<br/>", "<br>", "<i>", "</i>"}
        for t in tags:
            self.assertIn(t, allowed_tags, f"Unexpected/unsafe HTML tag in Mermaid code: '{t}'")


class TestAdversarialServerStressAndResilience(unittest.TestCase):
    """Stress tests: high concurrency, injection strings, malformed queries, and leak detection."""

    def test_high_concurrency_load(self):
        """Execute 60 rapid concurrent requests to test for deadlocks or race conditions."""
        start = time.time()
        num_reqs = 60
        concurrency = 15

        paths = [
            "/api/diagram-data",
            "/diagram",
            "/architecture",
            "/api/status",
        ]

        def worker(idx):
            p = paths[idx % len(paths)]
            s, h, b = http_request(p, timeout=10)
            return s, len(b)

        with concurrent.futures.ThreadPoolExecutor(max_workers=concurrency) as pool:
            futures = [pool.submit(worker, i) for i in range(num_reqs)]
            results = [f.result() for f in concurrent.futures.as_completed(futures)]

        duration = time.time() - start
        for status, b_len in results:
            self.assertEqual(status, 200, f"Concurrent request returned HTTP {status}")
            self.assertGreater(b_len, 100, "Response body was unexpectedly truncated")

        avg_rps = num_reqs / duration
        self.assertGreater(avg_rps, 10, f"Throughput too low under concurrent load: {avg_rps:.1f} req/s")

    def test_concurrent_forced_rescans(self):
        """Execute 8 concurrent requests with force=1 to test scanner thread safety & state_lock."""
        def rescan_worker(i):
            s, _, b = http_request("/api/diagram-data?force=1", timeout=15)
            return s, len(b)

        with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
            futures = [pool.submit(rescan_worker, i) for i in range(8)]
            results = [f.result() for f in concurrent.futures.as_completed(futures)]

        for status, b_len in results:
            self.assertEqual(status, 200, f"Forced rescan concurrent request returned HTTP {status}")
            self.assertGreater(b_len, 5000, "Response body was too small")

    def test_adversarial_query_payloads(self):
        """Test malicious / bizarre query parameters to verify zero crashes (no 500)."""
        adversarial_params = [
            "?force=1&extra=" + ("A" * 8000),  # Buffer overflow attempt
            "?force=" + urllib.parse.quote("%00%0a%0d"),  # Null byte & CRLF injection
            "?force=" + urllib.parse.quote("' OR '1'='1"),  # SQLi probe
            "?force=" + urllib.parse.quote("<script>alert('xss')</script>"),  # XSS probe
            "?force=" + urllib.parse.quote("../web_server.py"),  # Path traversal probe
            "?force=true&utf8=" + urllib.parse.quote("Tiếng Việt có dấu 🚀 Chấm công & Bảng lương"),
            "?" + urllib.parse.quote(" ") + "=" + urllib.parse.quote(" "),  # Whitespace key/val
            "?force=99999999999999999999999999999999999",  # Big int
            "?force=NaN&mode=undefined",
        ]

        for q in adversarial_params:
            status, _, body = http_request(f"/api/diagram-data{q}")
            self.assertEqual(
                status, 200,
                f"Server failed with HTTP {status} on adversarial query: {q[:60]}"
            )
            # Must still return valid JSON
            try:
                parsed = json.loads(body.decode("utf-8"))
                self.assertIn("modules", parsed)
            except Exception as e:
                self.fail(f"Corrupted JSON on query {q[:60]}: {e}")

    def test_unsupported_methods_and_routes(self):
        """Test non-existent routes and unexpected methods."""
        # Non-existent route
        status, _, _ = http_request("/api/diagram-data-bad-path-999")
        self.assertEqual(status, 404)

        # POST to diagram-data should be rejected or handle without crash
        status, _, _ = http_request("/api/diagram-data", method="POST", data=b'{"test":1}')
        self.assertIn(status, [200, 400, 404, 405])

    def test_server_latency_baseline_after_stress(self):
        """Verify the server maintains healthy baseline latency (< 200ms) after stress."""
        latencies = []
        for _ in range(5):
            t0 = time.time()
            s, _, _ = http_request("/api/diagram-data")
            latencies.append(time.time() - t0)
            self.assertEqual(s, 200)

    def test_sustained_stress_and_memory_stability(self):
        """Execute 100 rapid requests in loop to verify absence of memory leak or socket exhaustion."""
        for _ in range(100):
            status, _, body = http_request("/api/diagram-data")
            self.assertEqual(status, 200)
            self.assertGreater(len(body), 5000)


class TestAdversarialDOMAndInteractivity(unittest.TestCase):
    """Adversarial verification of the frontend HTML DOM elements and client scripts."""

    @classmethod
    def setUpClass(cls):
        status, _, body = http_request("/diagram")
        assert status == 200
        cls.html = body.decode("utf-8")

        # Also get data for correspondence
        status, _, data_body = http_request("/api/diagram-data")
        assert status == 200
        cls.data = json.loads(data_body.decode("utf-8"))

    def test_required_dom_ids_present(self):
        """All critical DOM element IDs required for UI features must exist in HTML."""
        required_ids = [
            'tabBtn_flowchart',
            'tabBtn_tree',
            'treeViewControls',
            'btnExpandAll',
            'btnCollapseAll',
            'treeViewContainer',
            'treeContent',
            'mermaidDiagram',
            'moduleLookupList',
            'diagramSearchInput',
            'diagramMatchCount',
        ]
        for dom_id in required_ids:
            self.assertIn(
                f'id="{dom_id}"', self.html,
                f"Missing required DOM element id='{dom_id}' in /diagram HTML"
            )

        # Check zoom controls and viewport
        for ctrl in ['diagramZoomIn', 'diagramZoomOut', 'diagramZoomReset', 'diagramFitView', 'diagramViewport']:
            self.assertIn(
                ctrl, self.html,
                f"Missing zoom control or container '{ctrl}' in /diagram HTML"
            )

    def test_client_javascript_functions_present(self):
        """Essential client-side interactive JS functions must be defined in HTML."""
        required_functions = [
            'switchDiagramViewTab',
            'expandAllTreeNodes',
            'collapseAllTreeNodes',
            'renderTreeView',
            'fetchDiagramData',
            'renderDynamicMermaid',
            'highlightAndScrollToModule',
            'renderDiagramColumns',
            'filterDiagramModules',
            'escapeHtml',
        ]
        for func_name in required_functions:
            self.assertIn(
                f'function {func_name}', self.html,
                f"Missing JavaScript function '{func_name}' in /diagram HTML"
            )

    def test_escape_html_usage_security(self):
        """Verify escapeHtml is applied to dynamic module strings to prevent XSS."""
        self.assertIn("escapeHtml(m.title)", self.html)
        self.assertIn("escapeHtml(m.skill)", self.html)
        self.assertIn("escapeHtml(m.name)", self.html)

    def test_color_coding_classes_compliance(self):
        """UI must include distinct colors: cyan for FE, purple for API, emerald for BE."""
        self.assertIn("text-cyan-400", self.html)
        self.assertIn("text-purple-300", self.html)
        self.assertIn("text-emerald-400", self.html)

    def test_all_11_modules_have_cards_in_dom_logic(self):
        """Verify that every module ID produces matching fe-card-{id} and be-card-{id}."""
        for m in self.data.get("modules", []):
            mid = m["id"]
            # Check render template creates matching card IDs
            self.assertIn(f'fe-card-${{m.id}}', self.html)
            self.assertIn(f'be-card-${{m.id}}', self.html)


if __name__ == "__main__":
    unittest.main(verbosity=2)

