#!/usr/bin/env python3
"""
EasySalon Studio Server (Main Entrypoint)
Khởi chạy HTTP Server, kích hoạt 2 AI Terminal ngầm (FE & BE), Hàng đợi (Queue) và Auto-Watch Hot Reload.
"""

import argparse
import http.server
import os
import socketserver
import sys
import threading
import time

from config import WEB_PORT, WEB_HOST
from studio.state import app_state, state_lock, load_queue_state, save_queue_state_unlocked
from studio.terminals import ensure_background_terminals, start_queue_worker, cleanup_background_terminals
from studio.telegram_bot import start_telegram_service
from studio.dev_watch import get_dev_watch_state, get_watched_python_files
from studio.handler import AgentStudioHandler


def main():
    parser = argparse.ArgumentParser(description="EasySalon Multi-Agent Studio Server")
    parser.add_argument("--port", type=int, default=WEB_PORT, help=f"Port to listen on (default {WEB_PORT})")
    parser.add_argument("--host", default=WEB_HOST, help=f"Host to bind to (default {WEB_HOST})")
    parser.add_argument("-w", "--watch", dest="watch", action="store_true", default=True, help="Auto-watch source files and hot-reload (default: True)")
    parser.add_argument("--no-watch", dest="watch", action="store_false", help="Disable auto-watch mode")
    args = parser.parse_args()

    port = args.port
    host = args.host
    watch_mode = args.watch

    initial_watch = get_dev_watch_state()
    initial_py_hash = initial_watch["py_hash"]

    print("\n" + "=" * 70)
    print(">> Kiểm tra và tự động kích hoạt 2 Terminal ngầm (FE & BE)...")
    ensure_background_terminals()
    load_queue_state()
    start_queue_worker()
    start_telegram_service()
    print("=" * 70)

    class ThreadedHTTPServer(socketserver.ThreadingMixIn, http.server.HTTPServer):
        daemon_threads = True
        allow_reuse_address = True

    try:
        server = ThreadedHTTPServer((host, port), AgentStudioHandler)
        print("\n[EasySalon Studio] Server is live.")
        print(f"Local URL: http://localhost:{port}")
        if watch_mode:
            print("🔥 Auto-Watch / Hot Reload: BẬT (Tự động lưu nháp & cập nhật web khi có code mới)")
        print("=" * 70 + "\n")

        if watch_mode:
            def _backend_file_watcher():
                while True:
                    time.sleep(1.2)
                    try:
                        st = get_dev_watch_state()
                        if st["py_hash"] != initial_py_hash:
                            with state_lock:
                                busy = any(t.get("is_running") for t in app_state["active_tasks"].values()) or app_state.get("is_running", False)
                            if busy:
                                continue
                            for py_fp in get_watched_python_files():
                                if os.path.exists(py_fp):
                                    with open(py_fp, "r", encoding="utf-8") as f:
                                        compile(f.read(), py_fp, "exec")
                            print("\n🔄 [Auto-Watch] Phát hiện thay đổi mã nguồn Python Backend, đang tự động tải lại server...")
                            cleanup_background_terminals()
                            with state_lock:
                                save_queue_state_unlocked()
                            server.server_close()
                            os.execv(sys.executable, [sys.executable] + sys.argv)
                    except SyntaxError as se:
                        print(f"⚠️ [Auto-Watch] Bỏ qua tải lại do lỗi cú pháp tạm thời: {se}")
                    except Exception:
                        pass

            watcher_thread = threading.Thread(target=_backend_file_watcher, daemon=True)
            watcher_thread.start()

        server.serve_forever()
    except KeyboardInterrupt:
        sys.exit(0)
    except Exception as e:
        print(f"Error starting server: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
