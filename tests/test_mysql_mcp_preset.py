#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Tests for MySQL MCP preset (tương thích cấu hình MySQL Workbench)."""

import os
import sys
import unittest
from unittest import mock

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from studio.services import mcp_service as ms


class TestMySQLConnectionParsing(unittest.TestCase):
    def test_parse_mysql_url(self):
        parsed = ms.parse_mysql_connection_string(
            "mysql://easysalon:s3cret@db.easysalon.dev:3306/easysalon"
        )
        self.assertEqual(parsed["host"], "db.easysalon.dev")
        self.assertEqual(parsed["port"], 3306)
        self.assertEqual(parsed["user"], "easysalon")
        self.assertEqual(parsed["password"], "s3cret")
        self.assertEqual(parsed["database"], "easysalon")

    def test_parse_workbench_key_value_string(self):
        parsed = ms.parse_mysql_connection_string(
            "host=db.easysalon.dev;port=3306;user=easysalon;password=pwd;database=easysalon"
        )
        self.assertEqual(parsed["host"], "db.easysalon.dev")
        self.assertEqual(parsed["port"], 3306)
        self.assertEqual(parsed["user"], "easysalon")
        self.assertEqual(parsed["password"], "pwd")
        self.assertEqual(parsed["database"], "easysalon")

    def test_empty_defaults(self):
        parsed = ms.parse_mysql_connection_string("")
        self.assertEqual(parsed["port"], 3306)
        self.assertEqual(parsed["host"], "")


class TestMySQLMcpPreset(unittest.TestCase):
    def test_save_mysql_preset_uses_env_vars(self):
        captured = {}

        def fake_save(name, cfg, target="both"):
            captured["name"] = name
            captured["cfg"] = cfg
            return {"success": True, "name": name}

        with mock.patch.object(ms, "save_mcp_server", fake_save):
            res = ms.save_mysql_mcp_preset(
                server_name="mysql",
                host="db.easysalon.dev",
                port=3306,
                user="easysalon",
                password="secret",
                database="easysalon",
                ssl=True,
            )

        self.assertTrue(res["success"])
        cfg = captured["cfg"]
        self.assertEqual(captured["name"], "mysql")
        self.assertEqual(cfg["command"], "npx")
        self.assertIn("@benborla29/mcp-server-mysql", cfg["args"])
        env = cfg["env"]
        self.assertEqual(env["MYSQL_HOST"], "db.easysalon.dev")
        self.assertEqual(env["MYSQL_PORT"], "3306")
        self.assertEqual(env["MYSQL_USER"], "easysalon")
        self.assertEqual(env["MYSQL_PASS"], "secret")
        self.assertEqual(env["MYSQL_DB"], "easysalon")
        self.assertEqual(env["MYSQL_SSL"], "true")
        # Mặc định read-only
        self.assertEqual(env["ALLOW_INSERT_OPERATION"], "false")
        self.assertEqual(env["ALLOW_UPDATE_OPERATION"], "false")
        self.assertEqual(env["ALLOW_DELETE_OPERATION"], "false")

    def test_save_mysql_preset_without_password(self):
        captured = {}

        def fake_save(name, cfg, target="both"):
            captured["cfg"] = cfg
            return {"success": True, "name": name}

        with mock.patch.object(ms, "save_mcp_server", fake_save):
            ms.save_mysql_mcp_preset(host="127.0.0.1", user="root", password="", ssl=False)

        env = captured["cfg"]["env"]
        self.assertEqual(env["MYSQL_PASS"], "")
        self.assertEqual(env["MYSQL_SSL"], "false")
        self.assertNotIn("MYSQL_DB", env)

    def test_detection_marks_mysql_preset(self):
        gemini_cfg = {
            "mcpServers": {
                "mysql": {
                    "command": "npx",
                    "args": ["-y", "@benborla29/mcp-server-mysql"],
                    "env": {
                        "MYSQL_HOST": "db.easysalon.dev",
                        "MYSQL_PORT": "3306",
                        "MYSQL_USER": "easysalon",
                    },
                }
            }
        }
        with mock.patch.object(ms, "_read_json_file", side_effect=[gemini_cfg, {}]), \
             mock.patch.object(ms, "_get_live_opencode_statuses", return_value={}):
            servers = ms.get_all_mcp_servers()

        self.assertEqual(len(servers), 1)
        self.assertEqual(servers[0]["name"], "mysql")
        self.assertEqual(servers[0]["preset"], "mysql")


if __name__ == "__main__":
    unittest.main()
