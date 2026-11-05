#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Regression tests for:
1. Jira ticket-code search must match similar/partial keys (1260 -> EAS-12601, ...).
2. Ticket status transitions must not be blocked client-side by assignee/reporter ownership.

The network layer is mocked, so these tests do not require a live Jira account.
"""

import json
import os
import sys
import unittest
import urllib.parse
from unittest import mock

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from studio.services import jira_service as js


class _FakeResponse:
    def __init__(self, payload, code=200):
        self._body = json.dumps(payload).encode("utf-8")
        self.code = code

    def read(self, *_args):
        return self._body

    def __enter__(self):
        return self

    def __exit__(self, *_exc):
        return False


class _FakeJira:
    """Giả lập Jira Cloud: trả dữ liệu khác nhau theo endpoint."""

    def __init__(self, picker_sections=None, search_issues=None, transition_error=None):
        self.picker_sections = picker_sections or []
        self.search_issues = search_issues or []
        self.transition_error = transition_error
        self.requests = []

    def __call__(self, req, timeout=None):
        url = req.full_url if hasattr(req, "full_url") else str(req)
        method = getattr(req, "get_method", lambda: "GET")()
        self.requests.append({"url": url, "method": method, "data": getattr(req, "data", None)})

        parsed = urllib.parse.urlparse(url)
        if parsed.path.endswith("/rest/api/3/issue/picker"):
            return _FakeResponse({"sections": self.picker_sections})
        if parsed.path.endswith("/rest/api/3/search/jql"):
            return _FakeResponse({"issues": self.search_issues})
        if parsed.path.endswith("/transitions"):
            if method == "POST":
                if self.transition_error:
                    raise self.transition_error
                return _FakeResponse({}, code=204)
            return _FakeResponse({"transitions": []})
        return _FakeResponse({})

    def jql_payload(self):
        for r in self.requests:
            if r["method"] == "POST" and r["data"]:
                return json.loads(r["data"].decode("utf-8"))
        return {}

    def picker_queries(self):
        out = []
        for r in self.requests:
            if "/issue/picker" in r["url"]:
                qs = urllib.parse.parse_qs(urllib.parse.urlparse(r["url"]).query)
                out.append(qs.get("query", [""])[0])
        return out


def _issue(key, summary="Ticket", status="To Do", subtask=False):
    return {
        "id": key,
        "key": key,
        "fields": {
            "summary": summary,
            "status": {"name": status, "statusCategory": {"key": "new"}},
            "issuetype": {"name": "Sub-task" if subtask else "Task", "subtask": subtask},
            "priority": {"name": "Medium"},
            "assignee": {"displayName": "Người khác", "accountId": "other"},
            "reporter": {"displayName": "Người khác", "accountId": "other"},
            "updated": "2026-11-01T10:00:00.000+0700",
            "created": "2026-10-01T10:00:00.000+0700",
        },
    }


def _picker(keys):
    return [{"id": "s1", "issues": [{"key": k, "summaryText": k} for k in keys]}]


def _run_search(fake, **kwargs):
    with mock.patch.object(js, "get_jira_config", return_value={
        "is_configured": True, "is_disabled": False,
        "host": "https://example.atlassian.net", "email": "a@b.c", "api_token": "t",
    }), mock.patch.object(js, "_get_auth_headers", return_value={"Authorization": "Basic x"}), \
            mock.patch.object(js.urllib.request, "urlopen", fake):
        return js.search_jira_issues(**kwargs)


class TestPickerHelper(unittest.TestCase):
    def test_picker_dedupes_and_keeps_order(self):
        fake = _FakeJira(picker_sections=[
            {"id": "recent", "issues": [{"key": "EAS-12601"}, {"key": "EAS-12607"}]},
            {"id": "all", "issues": [{"key": "EAS-12601"}, {"key": "eas-12608"}, {"key": ""}]},
        ])
        with mock.patch.object(js.urllib.request, "urlopen", fake):
            keys = js._search_issue_keys_via_picker(
                {"host": "https://example.atlassian.net"}, {}, "1260", "project in (EAS)"
            )
        self.assertEqual(keys, ["EAS-12601", "EAS-12607", "EAS-12608"])

    def test_picker_respects_limit(self):
        fake = _FakeJira(picker_sections=_picker([f"EAS-{i}" for i in range(10)]))
        with mock.patch.object(js.urllib.request, "urlopen", fake):
            keys = js._search_issue_keys_via_picker({"host": "https://example.atlassian.net"}, {}, "1", limit=3)
        self.assertEqual(keys, ["EAS-0", "EAS-1", "EAS-2"])

    def test_picker_network_error_returns_empty(self):
        with mock.patch.object(js.urllib.request, "urlopen", side_effect=OSError("boom")):
            keys = js._search_issue_keys_via_picker({"host": "https://example.atlassian.net"}, {}, "1260")
        self.assertEqual(keys, [])

    def test_picker_sends_query_and_current_jql(self):
        fake = _FakeJira(picker_sections=_picker(["EAS-12601"]))
        with mock.patch.object(js.urllib.request, "urlopen", fake):
            js._search_issue_keys_via_picker(
                {"host": "https://example.atlassian.net"}, {}, "1260", "project in (EAS, SSLN)"
            )
        self.assertIn("1260", fake.picker_queries())
        qs = urllib.parse.parse_qs(urllib.parse.urlparse(fake.requests[0]["url"]).query)
        self.assertEqual(qs.get("currentJQL", [""])[0], "project in (EAS, SSLN)")


class TestPartialKeySort(unittest.TestCase):
    def test_exact_key_first_then_nearest(self):
        keys = ["EAS-12607", "EAS-1260", "EAS-12601", "EAS-1259"]
        ordered = sorted(keys, key=lambda k: js._partial_key_sort_key(k, "1260"))
        self.assertEqual(ordered[0], "EAS-1260")
        self.assertLess(ordered.index("EAS-12601"), ordered.index("EAS-12607"))

    def test_prefix_priority(self):
        ordered = sorted(["SSLN-12601", "EAS-12601"], key=lambda k: js._partial_key_sort_key(k, "EAS-1260"))
        self.assertEqual(ordered, ["EAS-12601", "SSLN-12601"])

    def test_non_key_values_go_last(self):
        ordered = sorted(["BAD", "EAS-1"], key=lambda k: js._partial_key_sort_key(k, "EAS-1"))
        self.assertEqual(ordered, ["EAS-1", "BAD"])


class TestSearchJiraIssuesPartialKey(unittest.TestCase):
    def test_numeric_query_uses_picker_keys_and_returns_similar(self):
        fake = _FakeJira(
            picker_sections=_picker(["EAS-12601", "EAS-12607", "EAS-1260"]),
            search_issues=[_issue("EAS-12607"), _issue("EAS-12601"), _issue("EAS-1260")],
        )
        res = _run_search(fake, query="1260", max_results=40)

        self.assertTrue(res["success"])
        self.assertEqual([i["key"] for i in res["issues"]], ["EAS-1260", "EAS-12601", "EAS-12607"])
        self.assertIn("1260", fake.picker_queries())
        payload = fake.jql_payload()
        self.assertIn("issueKey in (", payload["jql"])
        self.assertIn("'EAS-12601'", payload["jql"])
        self.assertIn("'EAS-1260'", payload["jql"])

    def test_short_numeric_query_returns_longer_keys(self):
        fake = _FakeJira(
            picker_sections=_picker(["EAS-12601", "EAS-126", "EAS-12611"]),
            search_issues=[_issue("EAS-12611"), _issue("EAS-126"), _issue("EAS-12601")],
        )
        res = _run_search(fake, query="126", max_results=40)
        keys = [i["key"] for i in res["issues"]]
        self.assertEqual(keys[0], "EAS-126")
        self.assertIn("EAS-12601", keys)
        self.assertIn("EAS-12611", keys)

    def test_full_key_query_also_returns_similar(self):
        fake = _FakeJira(
            picker_sections=_picker(["EAS-12601", "EAS-1260"]),
            search_issues=[_issue("EAS-12601"), _issue("EAS-1260")],
        )
        res = _run_search(fake, query="EAS-1260", max_results=40)
        keys = [i["key"] for i in res["issues"]]
        self.assertEqual(keys[0], "EAS-1260")
        self.assertIn("EAS-12601", keys)

    def test_compact_key_query_uses_hyphenated_exact_key(self):
        fake = _FakeJira(
            picker_sections=_picker(["EAS-12601"]),
            search_issues=[_issue("EAS-12601"), _issue("EAS-126")],
        )
        res = _run_search(fake, query="eas1260", max_results=40)
        payload = fake.jql_payload()
        self.assertIn("'EAS-1260'", payload["jql"])
        self.assertIn("'EAS-12601'", payload["jql"])
        self.assertTrue(res["success"])

    def test_picker_failure_falls_back_to_content_search(self):
        fake = _FakeJira(picker_sections=[])
        with mock.patch.object(js.urllib.request, "urlopen", fake):
            # Picker trả rỗng, không có key nào -> fallback summary/text
            res = _run_search(fake, query="1260", max_results=40)
        self.assertTrue(res["success"])
        payload = fake.jql_payload()
        self.assertIn("summary ~ '1260'", payload["jql"])
        self.assertNotIn("issueKey in (", payload["jql"])

    def test_text_query_still_uses_summary_and_text(self):
        fake = _FakeJira(search_issues=[_issue("EAS-1", summary="Thanh toán")])
        res = _run_search(fake, query="thanh toan", max_results=40)
        self.assertTrue(res["success"])
        payload = fake.jql_payload()
        self.assertIn('summary ~ "thanh toan"', payload["jql"])
        self.assertIn('text ~ "thanh toan"', payload["jql"])
        self.assertNotIn("issueKey in (", payload["jql"])
        self.assertEqual(fake.picker_queries(), [])

    def test_key_search_keeps_subtasks(self):
        fake = _FakeJira(
            picker_sections=_picker(["EAS-12601"]),
            search_issues=[_issue("EAS-12601", subtask=True)],
        )
        res = _run_search(fake, query="1260", max_results=40)
        self.assertEqual(len(res["issues"]), 1)
        self.assertTrue(res["issues"][0]["is_subtask"])

    def test_text_search_filters_subtasks(self):
        fake = _FakeJira(search_issues=[_issue("EAS-1"), _issue("EAS-2", subtask=True)])
        res = _run_search(fake, query="thanh toan", max_results=40)
        self.assertEqual([i["key"] for i in res["issues"]], ["EAS-1"])

    def test_project_scope_is_sent_to_picker(self):
        fake = _FakeJira(picker_sections=_picker(["SSLN-1"]))
        _run_search(fake, query="1", project="SSLN", max_results=40)
        qs = urllib.parse.parse_qs(urllib.parse.urlparse(fake.requests[0]["url"]).query)
        self.assertIn("project = 'SSLN'", qs.get("currentJQL", [""])[0])


class TestFreeTransitions(unittest.TestCase):
    def test_normalized_issue_allows_transition(self):
        info = js._normalize_issue_summary(_issue("EAS-1"), "https://example.atlassian.net", "me")
        self.assertTrue(info["can_transition"])
        self.assertFalse(info["is_mine"])

    def test_transition_does_not_call_ownership_gate(self):
        fake = _FakeJira()
        with mock.patch.object(js, "get_jira_config", return_value={
            "is_configured": True, "is_disabled": False,
            "host": "https://example.atlassian.net", "email": "a@b.c", "api_token": "t",
        }), mock.patch.object(js, "_get_auth_headers", return_value={"Authorization": "Basic x"}), \
                mock.patch.object(js, "_resolve_issue_ownership") as ownership, \
                mock.patch.object(js.urllib.request, "urlopen", fake):
            res = js.transition_jira_issue("EAS-12601", transition_id="31")

        self.assertTrue(res["success"])
        ownership.assert_not_called()
        posts = [r for r in fake.requests if r["method"] == "POST"]
        self.assertEqual(len(posts), 1)
        self.assertEqual(json.loads(posts[0]["data"].decode())["transition"]["id"], "31")

    def test_transition_http_error_is_reported(self):
        err = js.urllib.error.HTTPError(
            "https://example.atlassian.net/rest/api/3/issue/EAS-1/transitions",
            403, "Forbidden", {}, None,
        )
        fake = _FakeJira(transition_error=err)
        with mock.patch.object(js, "get_jira_config", return_value={
            "is_configured": True, "is_disabled": False,
            "host": "https://example.atlassian.net", "email": "a@b.c", "api_token": "t",
        }), mock.patch.object(js, "_get_auth_headers", return_value={"Authorization": "Basic x"}), \
                mock.patch.object(js.urllib.request, "urlopen", fake):
            res = js.transition_jira_issue("EAS-1", transition_id="31")
        self.assertFalse(res["success"])
        self.assertIn("chuyển trạng thái", res["message"])


class TestFrontendContract(unittest.TestCase):
    def test_frontend_uses_non_false_fallback(self):
        root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        with open(os.path.join(root, "frontend", "modules", "jira.js"), "r", encoding="utf-8") as f:
            src = f.read()
        self.assertIn("issue.can_transition !== false", src)
        self.assertNotIn("Bạn chỉ có thể đổi trạng thái Ticket do mình tạo", src)
        self.assertNotIn("Chỉ người được gán hoặc người tạo ticket mới được đổi trạng thái", src)


if __name__ == "__main__":
    unittest.main()
