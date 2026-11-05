#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Tests for Jira real-time notification differentiation:
- Brand new tasks: tagged as 'Task mới' (type: issue_created, title: 'Task mới vừa log: ...')
- Tasks logged in the past and updated later: tagged as 'Cập nhật doc' (type: issue_updated, title: 'Cập nhật doc: ...')
"""

import json
import os
import sys
import unittest
from datetime import datetime, timedelta, timezone
from unittest import mock

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from studio.services import jira_service as js

TZ = timezone(timedelta(hours=7))


def _jira_ts(dt):
    """Format datetime theo chuẩn Jira: 2026-11-05T09:00:00.000+0700."""
    return dt.astimezone(TZ).strftime("%Y-%m-%dT%H:%M:%S.000%z")


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


class TestJiraDocUpdateNotifications(unittest.TestCase):
    def setUp(self):
        # Reset cache before each test
        js._JIRA_SEEN_CACHE = {
            "initialized": False,
            "issues": set(),
            "issue_updates": {},
            "comments": set(),
            "last_check": 0.0
        }
        js._SELF_CREATED_SUBTASKS.clear()

    @mock.patch("studio.services.jira_service.get_jira_config")
    @mock.patch("urllib.request.urlopen")
    def test_brand_new_task_detected_as_task_moi(self, mock_urlopen, mock_cfg):
        mock_cfg.return_value = {
            "is_configured": True,
            "host": "https://example.atlassian.net",
            "email": "user@test.com",
            "api_token": "secret"
        }

        # 1st call: initialization
        mock_urlopen.return_value = _FakeResponse({"issues": []})
        init_res = js.check_jira_updates()
        self.assertTrue(init_res["initialized"])
        self.assertEqual(len(init_res["notifications"]), 0)

        # 2nd call: Brand new task created just now
        now = datetime.now(TZ)
        new_task = {
            "key": "EAS-12600",
            "fields": {
                "summary": "Tính năng mới thanh toán QR",
                "issuetype": {"name": "Improvement", "subtask": False},
                "reporter": {"displayName": "Nguyễn Văn A", "accountId": "acc_a", "emailAddress": "a@test.com"},
                "created": _jira_ts(now),
                "updated": _jira_ts(now + timedelta(seconds=5)),
                "comment": {"comments": []}
            }
        }
        mock_urlopen.return_value = _FakeResponse({"issues": [new_task]})
        res = js.check_jira_updates()
        notifs = res.get("notifications", [])
        self.assertEqual(len(notifs), 1)
        n = notifs[0]
        self.assertEqual(n["type"], "issue_created")
        self.assertEqual(n["key"], "EAS-12600")
        self.assertEqual(n["title"], "Task mới vừa log: EAS-12600")
        self.assertIn("vừa log Improvement [EAS-12600]", n["message"])

    @mock.patch("studio.services.jira_service.get_jira_config")
    @mock.patch("urllib.request.urlopen")
    def test_old_task_updated_detected_as_cap_nhat_doc(self, mock_urlopen, mock_cfg):
        mock_cfg.return_value = {
            "is_configured": True,
            "host": "https://example.atlassian.net",
            "email": "user@test.com",
            "api_token": "secret"
        }

        # 1st call: initialization
        mock_urlopen.return_value = _FakeResponse({"issues": []})
        js.check_jira_updates()

        # 2nd call: EAS-12473 was created 20 days ago and updated today
        old_task_updated = {
            "key": "EAS-12473",
            "changelog": {
                "histories": [
                    {
                        "author": {"displayName": "Trần Dương", "accountId": "acc_td", "emailAddress": "td@test.com"},
                        "created": "2026-11-05T08:59:13.524+0700",
                        "items": [{"field": "description"}]
                    }
                ]
            },
            "fields": {
                "summary": "WQL_Bổ sung trường thông tin TKNH, CCCD, Email",
                "issuetype": {"name": "Improvement", "subtask": False},
                "reporter": {"displayName": "Lê Đình Đức", "accountId": "acc_ldd", "emailAddress": "ldd@test.com"},
                "created": "2026-10-16T16:15:17.160+0700",
                "updated": "2026-11-05T08:59:13.524+0700",
                "comment": {"comments": []}
            }
        }
        mock_urlopen.return_value = _FakeResponse({"issues": [old_task_updated]})
        res = js.check_jira_updates()
        notifs = res.get("notifications", [])
        self.assertEqual(len(notifs), 1)
        n = notifs[0]
        self.assertEqual(n["type"], "issue_updated")
        self.assertEqual(n["key"], "EAS-12473")
        self.assertEqual(n["title"], "Cập nhật doc: EAS-12473")
        self.assertEqual(n["author"], "Trần Dương")
        self.assertIn("vừa cập nhật doc Improvement [EAS-12473]", n["message"])

    @mock.patch("studio.services.jira_service.get_jira_config")
    @mock.patch("urllib.request.urlopen")
    def test_cached_task_updated_triggers_doc_update(self, mock_urlopen, mock_cfg):
        mock_cfg.return_value = {
            "is_configured": True,
            "host": "https://example.atlassian.net",
            "email": "user@test.com",
            "api_token": "secret"
        }

        # 1st call: initialization with existing task
        task = {
            "key": "EAS-12500",
            "fields": {
                "summary": "Báo cáo doanh thu theo ngày",
                "issuetype": {"name": "Story", "subtask": False},
                "reporter": {"displayName": "Hoàng Nam", "accountId": "acc_hn", "emailAddress": "hn@test.com"},
                "created": "2026-11-01T10:00:00.000+0700",
                "updated": "2026-11-01T10:00:00.000+0700",
                "comment": {"comments": []}
            }
        }
        mock_urlopen.return_value = _FakeResponse({"issues": [task]})
        js.check_jira_updates()

        # 2nd call: same task, updated timestamp changed
        task_updated = {
            "key": "EAS-12500",
            "changelog": {
                "histories": [
                    {
                        "author": {"displayName": "Hoàng Nam", "accountId": "acc_hn", "emailAddress": "hn@test.com"},
                        "created": "2026-11-05T09:30:00.000+0700",
                        "items": [{"field": "description"}]
                    }
                ]
            },
            "fields": {
                "summary": "Báo cáo doanh thu theo ngày",
                "issuetype": {"name": "Story", "subtask": False},
                "reporter": {"displayName": "Hoàng Nam", "accountId": "acc_hn", "emailAddress": "hn@test.com"},
                "created": "2026-11-01T10:00:00.000+0700",
                "updated": "2026-11-05T09:30:00.000+0700",
                "comment": {"comments": []}
            }
        }
        mock_urlopen.return_value = _FakeResponse({"issues": [task_updated]})
        res = js.check_jira_updates()
        notifs = res.get("notifications", [])
        self.assertEqual(len(notifs), 1)
        self.assertEqual(notifs[0]["type"], "issue_updated")
        self.assertEqual(notifs[0]["title"], "Cập nhật doc: EAS-12500")

    @mock.patch("studio.services.jira_service.get_jira_config")
    @mock.patch("urllib.request.urlopen")
    def test_comment_does_not_duplicate_doc_update(self, mock_urlopen, mock_cfg):
        mock_cfg.return_value = {
            "is_configured": True,
            "host": "https://example.atlassian.net",
            "email": "user@test.com",
            "api_token": "secret"
        }

        # 1st call: initialization
        task = {
            "key": "EAS-12500",
            "fields": {
                "summary": "Báo cáo doanh thu theo ngày",
                "issuetype": {"name": "Story", "subtask": False},
                "reporter": {"displayName": "Hoàng Nam"},
                "created": "2026-11-01T10:00:00.000+0700",
                "updated": "2026-11-01T10:00:00.000+0700",
                "comment": {"comments": []}
            }
        }
        mock_urlopen.return_value = _FakeResponse({"issues": [task]})
        js.check_jira_updates()

        # 2nd call: new comment added (which updates the issue's updated timestamp too)
        task_with_comment = {
            "key": "EAS-12500",
            "fields": {
                "summary": "Báo cáo doanh thu theo ngày",
                "issuetype": {"name": "Story", "subtask": False},
                "reporter": {"displayName": "Hoàng Nam"},
                "created": "2026-11-01T10:00:00.000+0700",
                "updated": "2026-11-05T09:35:00.000+0700",
                "comment": {
                    "comments": [
                        {
                            "id": "comm_999",
                            "author": {"displayName": "Tester B"},
                            "body": "Đã test xong trên staging",
                            "created": "2026-11-05T09:35:00.000+0700"
                        }
                    ]
                }
            }
        }
        mock_urlopen.return_value = _FakeResponse({"issues": [task_with_comment]})
        res = js.check_jira_updates()
        notifs = res.get("notifications", [])
        # Only comment notification, no duplicate doc update notification
        self.assertEqual(len(notifs), 1)
        self.assertEqual(notifs[0]["type"], "comment_added")
        self.assertEqual(notifs[0]["id"], "comment_comm_999")


if __name__ == "__main__":
    unittest.main()
