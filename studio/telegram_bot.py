#!/usr/bin/env python3
"""
EasySalon Studio - Telegram Bot Service (@easysalon_bot)
Dịch vụ thứ 3 tích hợp cho phép giám sát, kiểm tra Staging/Master, Pull Git và điều khiển tác vụ từ xa.
"""

import datetime
import html
import os
import sys
import threading
import time
import uuid
from concurrent.futures import ThreadPoolExecutor

import telebot
from telebot import types

from config import (
    FE_WORKSPACE,
    BE_WORKSPACE,
    get_fe_workspace,
    get_be_workspace,
    get_workspace,
    TELEGRAM_BOT_TOKEN,
    TELEGRAM_BOT_NAME,
    TELEGRAM_ALLOWED_USERS,
    TELEGRAM_ENABLED,
)
from studio.git_ops import (
    get_git_repo_details,
    sync_pull_branch,
    switch_git_branch,
    check_sync_pull_status,
)
from studio.state import (
    app_state,
    state_lock,
    load_messages,
    add_work_log,
)
from studio.terminals import enqueue_task_item

# Khởi tạo TeleBot
bot = telebot.TeleBot(TELEGRAM_BOT_TOKEN, parse_mode="HTML") if TELEGRAM_BOT_TOKEN else None


def is_authorized(user_id: int) -> bool:
    """Kiểm tra quyền truy cập của người dùng Telegram."""
    if not TELEGRAM_ALLOWED_USERS:
        return True
    return str(user_id) in TELEGRAM_ALLOWED_USERS


def auth_guard(handler_func):
    """Decorator kiểm tra quyền người dùng trước khi thực thi lệnh."""
    def wrapper(message, *args, **kwargs):
        if not is_authorized(message.from_user.id):
            bot.reply_to(
                message,
                f"⛔ <b>Bạn không có quyền truy cập Bot này.</b>\n"
                f"Telegram ID của bạn: <code>{message.from_user.id}</code>\n"
                f"Vui lòng thêm ID này vào danh sách cho phép (TELEGRAM_ALLOWED_USERS trong .env)."
            )
            return
        return handler_func(message, *args, **kwargs)
    return wrapper


def auth_callback_guard(handler_func):
    """Decorator kiểm tra quyền khi bấm nút Inline Keyboard."""
    def wrapper(call, *args, **kwargs):
        if not is_authorized(call.from_user.id):
            bot.answer_callback_query(call.id, "⛔ Bạn không có quyền thao tác trên Bot này!", show_alert=True)
            return
        return handler_func(call, *args, **kwargs)
    return wrapper


# ──────────────────────────────────────────────────────────────────────────────
# KEYBOARDS BUILDER
# ──────────────────────────────────────────────────────────────────────────────

def build_main_reply_keyboard():
    """Tạo bàn phím điều khiển Reply Keyboard chính dưới thanh chat."""
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.row(
        types.KeyboardButton("🔄 Kiểm tra Staging / Master"),
        types.KeyboardButton("📊 Git Status")
    )
    markup.row(
        types.KeyboardButton("⬇️ Pull Staging (Cả 2)"),
        types.KeyboardButton("⬇️ Pull Master (Cả 2)")
    )
    markup.row(
        types.KeyboardButton("📋 Hàng đợi tác vụ"),
        types.KeyboardButton("📜 Nhật ký gần nhất")
    )
    markup.row(
        types.KeyboardButton("ℹ️ Hướng dẫn / Menu")
    )
    return markup


def build_sync_inline_keyboard(fe_data=None, be_data=None):
    """Tạo các nút bấm Inline thao tác kéo code nhanh."""
    fe_st_cnt = fe_data.get('staging', {}).get('behind_count', 0) if fe_data else 0
    fe_ms_cnt = fe_data.get('master', {}).get('behind_count', 0) if fe_data else 0
    be_st_cnt = be_data.get('staging', {}).get('behind_count', 0) if be_data else 0
    be_ms_cnt = be_data.get('master', {}).get('behind_count', 0) if be_data else 0

    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.row(
        types.InlineKeyboardButton(f"⬇️ Pull FE Staging{f' ({fe_st_cnt})' if fe_st_cnt else ''}", callback_data="pull:fe:staging"),
        types.InlineKeyboardButton(f"⬇️ Pull BE Staging{f' ({be_st_cnt})' if be_st_cnt else ''}", callback_data="pull:be:staging")
    )
    markup.row(
        types.InlineKeyboardButton(f"⬇️ Pull FE Master{f' ({fe_ms_cnt})' if fe_ms_cnt else ''}", callback_data="pull:fe:master"),
        types.InlineKeyboardButton(f"⬇️ Pull BE Master{f' ({be_ms_cnt})' if be_ms_cnt else ''}", callback_data="pull:be:master")
    )
    markup.row(
        types.InlineKeyboardButton("🚀 Pull Staging Cả 2 (FE & BE)", callback_data="pull:both:staging"),
        types.InlineKeyboardButton("🚀 Pull Master Cả 2 (FE & BE)", callback_data="pull:both:master")
    )
    markup.row(
        types.InlineKeyboardButton("🔄 Kiểm tra cập nhật lại", callback_data="sync:check")
    )
    return markup


# ──────────────────────────────────────────────────────────────────────────────
# CORE LOGIC HELPERS
# ──────────────────────────────────────────────────────────────────────────────

def fetch_and_format_sync_status(do_fetch=True):
    """Gọi kiểm tra trạng thái Staging/Master cho FE & BE và format thông điệp HTML."""
    fe_ws = get_fe_workspace()
    be_ws = get_be_workspace()
    with ThreadPoolExecutor(max_workers=2) as executor:
        f_fe = executor.submit(check_sync_pull_status, fe_ws, ('staging', 'master', 'beta'), do_fetch)
        f_be = executor.submit(check_sync_pull_status, be_ws, ('staging', 'master', 'beta'), do_fetch)
        fe_res = f_fe.result()
        be_res = f_be.result()

    now_str = datetime.datetime.now().strftime("%H:%M:%S - %d/%m/%Y")
    
    fe_curr = get_git_repo_details(fe_ws).get('current_branch', 'unknown')
    be_curr = get_git_repo_details(be_ws).get('current_branch', 'unknown')

    msg_lines = [
        f"<b>🔄 TRẠNG THÁI ĐỒNG BỘ STAGING & MASTER</b>",
        f"⏱ <i>Kiểm tra lúc: {now_str}</i>",
        "",
        f"<b>💻 FRONTEND (easysalon-webapp)</b>",
        f"• Nhánh hiện tại: <code>{html.escape(fe_curr)}</code>"
    ]

    # FE Staging
    st_fe = fe_res.get('staging', {})
    if st_fe.get('needs_pull'):
        msg_lines.append(f"• <b>staging</b>: ⚠️ <b>CÓ {st_fe.get('behind_count', 1)} COMMIT CẦN PULL</b>")
        if st_fe.get('diff_stat'):
            msg_lines.append(f"  <i>Thống kê: {html.escape(st_fe['diff_stat'])}</i>")
        for c in st_fe.get('commits', [])[:5]:
            msg_lines.append(f"  ↳ <code>{html.escape(c['hash'])}</code>: {html.escape(c['subject'])} (<i>{html.escape(c['author'])} • {html.escape(c['date'])}</i>)")
    else:
        lat = st_fe.get('latest_commit')
        lat_str = f" ({lat['hash']} • {lat['date']})" if lat else ""
        msg_lines.append(f"• <b>staging</b>: ✅ Đã mới nhất (0 commit){lat_str}")

    # FE Master
    ms_fe = fe_res.get('master', {})
    if ms_fe.get('needs_pull'):
        msg_lines.append(f"• <b>master</b>: ⚠️ <b>CÓ {ms_fe.get('behind_count', 1)} COMMIT CẦN PULL</b>")
        if ms_fe.get('diff_stat'):
            msg_lines.append(f"  <i>Thống kê: {html.escape(ms_fe['diff_stat'])}</i>")
        for c in ms_fe.get('commits', [])[:5]:
            msg_lines.append(f"  ↳ <code>{html.escape(c['hash'])}</code>: {html.escape(c['subject'])} (<i>{html.escape(c['author'])} • {html.escape(c['date'])}</i>)")
    else:
        lat = ms_fe.get('latest_commit')
        lat_str = f" ({lat['hash']} • {lat['date']})" if lat else ""
        msg_lines.append(f"• <b>master</b>: ✅ Đã mới nhất (0 commit){lat_str}")

    msg_lines.append("")
    msg_lines.append(f"<b>⚙️ BACKEND (easysalon-api)</b>")
    msg_lines.append(f"• Nhánh hiện tại: <code>{html.escape(be_curr)}</code>")

    # BE Staging
    st_be = be_res.get('staging', {})
    if st_be.get('needs_pull'):
        msg_lines.append(f"• <b>staging</b>: ⚠️ <b>CÓ {st_be.get('behind_count', 1)} COMMIT CẦN PULL</b>")
        if st_be.get('diff_stat'):
            msg_lines.append(f"  <i>Thống kê: {html.escape(st_be['diff_stat'])}</i>")
        for c in st_be.get('commits', [])[:5]:
            msg_lines.append(f"  ↳ <code>{html.escape(c['hash'])}</code>: {html.escape(c['subject'])} (<i>{html.escape(c['author'])} • {html.escape(c['date'])}</i>)")
    else:
        lat = st_be.get('latest_commit')
        lat_str = f" ({lat['hash']} • {lat['date']})" if lat else ""
        msg_lines.append(f"• <b>staging</b>: ✅ Đã mới nhất (0 commit){lat_str}")

    # BE Master
    ms_be = be_res.get('master', {})
    if ms_be.get('needs_pull'):
        msg_lines.append(f"• <b>master</b>: ⚠️ <b>CÓ {ms_be.get('behind_count', 1)} COMMIT CẦN PULL</b>")
        if ms_be.get('diff_stat'):
            msg_lines.append(f"  <i>Thống kê: {html.escape(ms_be['diff_stat'])}</i>")
        for c in ms_be.get('commits', [])[:5]:
            msg_lines.append(f"  ↳ <code>{html.escape(c['hash'])}</code>: {html.escape(c['subject'])} (<i>{html.escape(c['author'])} • {html.escape(c['date'])}</i>)")
    else:
        lat = ms_be.get('latest_commit')
        lat_str = f" ({lat['hash']} • {lat['date']})" if lat else ""
        msg_lines.append(f"• <b>master</b>: ✅ Đã mới nhất (0 commit){lat_str}")

    total_behind = (
        st_fe.get('behind_count', 0) +
        ms_fe.get('behind_count', 0) +
        st_be.get('behind_count', 0) +
        ms_be.get('behind_count', 0)
    )

    if total_behind > 0:
        msg_lines.append(f"\n💡 <i>Gợi ý: Bấm các nút dưới đây để kéo code cập nhật ngay:</i>")
    else:
        msg_lines.append(f"\n🎉 <i>Tất cả các nhánh đều đã đồng bộ hoàn toàn với remote!</i>")

    return "\n".join(msg_lines), fe_res, be_res


def execute_pull_for_telegram(target: str, branch: str, chat_id: int):
    """Thực thi pull và thông báo kết quả chi tiết về Telegram."""
    target_label = "Cả 2 (FE & BE)" if target == "both" else ("Frontend" if target == "fe" else "Backend")
    status_msg = bot.send_message(chat_id, f"⏳ Đang thực hiện pull <b>{branch.upper()}</b> cho <b>{target_label}</b> (tự động quay về nhánh hiện tại sau khi pull)...")

    results = {}
    all_ok = True
    any_conflict = False

    if target in ('fe', 'both'):
        res_fe = sync_pull_branch(get_fe_workspace(), branch, return_to_current=True)
        results['fe'] = res_fe
        if not res_fe.get('success'):
            all_ok = False
        if res_fe.get('conflict'):
            any_conflict = True
        fe_details = res_fe.get('message', '')
        if res_fe.get('output') and res_fe.get('output') not in fe_details:
            fe_details += f"\n\n--- Chi tiết Git Output ---\n{res_fe.get('output')}"
        fe_count = len(res_fe.get('pulled_commits', []))
        fe_suffix = f" ({fe_count} commit mới)" if fe_count > 0 else ""
        add_work_log(
            'GIT_SYNC_PULL',
            f"Pull {branch} Frontend (Telegram)" + fe_suffix,
            fe_details,
            'SUCCESS' if res_fe.get('success') else ('CONFLICT' if res_fe.get('conflict') else 'ERROR'),
            target='fe'
        )

    if target in ('be', 'both'):
        res_be = sync_pull_branch(get_be_workspace(), branch, return_to_current=True)
        results['be'] = res_be
        if not res_be.get('success'):
            all_ok = False
        if res_be.get('conflict'):
            any_conflict = True
        be_details = res_be.get('message', '')
        if res_be.get('output') and res_be.get('output') not in be_details:
            be_details += f"\n\n--- Chi tiết Git Output ---\n{res_be.get('output')}"
        be_count = len(res_be.get('pulled_commits', []))
        be_suffix = f" ({be_count} commit mới)" if be_count > 0 else ""
        add_work_log(
            'GIT_SYNC_PULL',
            f"Pull {branch} Backend (Telegram)" + be_suffix,
            be_details,
            'SUCCESS' if res_be.get('success') else ('CONFLICT' if res_be.get('conflict') else 'ERROR'),
            target='be'
        )

    lines = []
    if all_ok:
        lines.append(f"✅ <b>PULL {branch.upper()} THÀNH CÔNG!</b>")
        if 'fe' in results:
            r = results['fe']
            lines.append(f"• <b>Frontend:</b> Đã cập nhật xong, hiện ở nhánh <code>{html.escape(r.get('final_branch', ''))}</code>")
            if r.get('head_commit'):
                lines.append(f"  ↳ Commit: <code>{html.escape(r['head_commit'])}</code>")
        if 'be' in results:
            r = results['be']
            lines.append(f"• <b>Backend:</b> Đã cập nhật xong, hiện ở nhánh <code>{html.escape(r.get('final_branch', ''))}</code>")
            if r.get('head_commit'):
                lines.append(f"  ↳ Commit: <code>{html.escape(r['head_commit'])}</code>")
    elif any_conflict:
        lines.append(f"⚠️ <b>PHÁT HIỆN XUNG ĐỘT (CONFLICT) KHI PULL {branch.upper()}!</b>")
        for role, r in results.items():
            if r.get('conflict'):
                role_name = "Frontend" if role == "fe" else "Backend"
                lines.append(f"• <b>{role_name}:</b> Xung đột tại các file:")
                for cf in r.get('conflicted_files', [])[:5]:
                    lines.append(f"  ❌ <code>{html.escape(cf)}</code>")
    else:
        lines.append(f"❌ <b>PULL {branch.upper()} THẤT BẠI!</b>")
        for role, r in results.items():
            if not r.get('success'):
                role_name = "Frontend" if role == "fe" else "Backend"
                lines.append(f"• <b>{role_name}:</b> {html.escape(r.get('message', 'Lỗi không xác định'))}")

    bot.edit_message_text(
        "\n".join(lines),
        chat_id=chat_id,
        message_id=status_msg.message_id
    )


# ──────────────────────────────────────────────────────────────────────────────
# BOT COMMAND HANDLERS
# ──────────────────────────────────────────────────────────────────────────────

if bot:
    @bot.message_handler(commands=['start', 'help', 'menu'])
    @auth_guard
    def handle_start(message):
        text = (
            f"👋 <b>Chào mừng bạn đến với EasySalon Studio Bot ({TELEGRAM_BOT_NAME})!</b>\n"
            f"Bot đã kết nối trực tiếp với máy tính và 2 repository Frontend & Backend.\n\n"
            f"📌 <b>Các tính năng hỗ trợ:</b>\n"
            f"• <b>Kiểm tra cập nhật:</b> <code>/check</code> (Kiểm tra Staging/Master có gì cần pull không)\n"
            f"• <b>Kéo code:</b> <code>/pull_fe_staging</code>, <code>/pull_be_staging</code>, <code>/pull_both_staging</code>...\n"
            f"• <b>Trạng thái Git:</b> <code>/status</code> (Nhánh, dirty files, commit hiện tại)\n"
            f"• <b>Chuyển nhánh:</b> <code>/switch fe &lt;tên_nhánh&gt;</code>\n"
            f"• <b>Thực hiện tác vụ:</b> <code>/task &lt;fe|be|both&gt; &lt;nội dung&gt;</code>\n"
            f"• <b>Fix bug:</b> <code>/fixbug &lt;fe|be|both&gt; &lt;mô tả lỗi&gt;</code>\n"
            f"• <b>Hàng đợi & Nhật ký:</b> <code>/queue</code>, <code>/logs</code>, <code>/stop</code>\n\n"
            f"<i>Bạn có thể sử dụng các nút bấm tiện lợi bên dưới bàn phím:</i>"
        )
        bot.send_message(message.chat.id, text, reply_markup=build_main_reply_keyboard())


    @bot.message_handler(commands=['check', 'sync'])
    @auth_guard
    def handle_check(message):
        load_msg = bot.send_message(message.chat.id, "⏳ Đang kiểm tra remote origin cho Staging & Master...")
        try:
            report_text, fe_res, be_res = fetch_and_format_sync_status(do_fetch=True)
            bot.edit_message_text(
                report_text,
                chat_id=message.chat.id,
                message_id=load_msg.message_id,
                reply_markup=build_sync_inline_keyboard(fe_res, be_res)
            )
        except Exception as e:
            bot.edit_message_text(f"❌ Lỗi khi kiểm tra: {e}", chat_id=message.chat.id, message_id=load_msg.message_id)


    @bot.message_handler(func=lambda m: m.text == "🔄 Kiểm tra Staging / Master")
    @auth_guard
    def handle_btn_check(message):
        handle_check(message)


    @bot.message_handler(commands=['status', 'git'])
    @auth_guard
    def handle_status(message):
        fe = get_git_repo_details(get_fe_workspace())
        be = get_git_repo_details(get_be_workspace())

        lines = [
            "<b>📊 TRẠNG THÁI GIT (FRONTEND & BACKEND)</b>\n",
            "<b>💻 Frontend (easysalon-webapp):</b>",
            f"• Nhánh: <code>{html.escape(fe.get('current_branch', 'unknown'))}</code>",
            f"• Thay đổi chưa commit: <b>{fe.get('dirty_count', 0)} files</b>",
            f"• Commit: <code>{fe.get('commit_hash', '')}</code> - {html.escape(fe.get('commit_message', ''))} (<i>{fe.get('commit_date', '')}</i>)",
            f"• Đồng bộ upstream: {fe.get('behind_count', 0)} behind / {fe.get('ahead_count', 0)} ahead",
            "",
            "<b>⚙️ Backend (easysalon-api):</b>",
            f"• Nhánh: <code>{html.escape(be.get('current_branch', 'unknown'))}</code>",
            f"• Thay đổi chưa commit: <b>{be.get('dirty_count', 0)} files</b>",
            f"• Commit: <code>{be.get('commit_hash', '')}</code> - {html.escape(be.get('commit_message', ''))} (<i>{be.get('commit_date', '')}</i>)",
            f"• Đồng bộ upstream: {be.get('behind_count', 0)} behind / {be.get('ahead_count', 0)} ahead",
        ]
        bot.send_message(message.chat.id, "\n".join(lines), reply_markup=build_main_reply_keyboard())


    @bot.message_handler(func=lambda m: m.text == "📊 Git Status")
    @auth_guard
    def handle_btn_status(message):
        handle_status(message)


    # Các lệnh Pull
    @bot.message_handler(commands=['pull_fe_staging'])
    @auth_guard
    def cmd_pull_fe_staging(message):
        threading.Thread(target=execute_pull_for_telegram, args=('fe', 'staging', message.chat.id), daemon=True).start()

    @bot.message_handler(commands=['pull_be_staging'])
    @auth_guard
    def cmd_pull_be_staging(message):
        threading.Thread(target=execute_pull_for_telegram, args=('be', 'staging', message.chat.id), daemon=True).start()

    @bot.message_handler(commands=['pull_both_staging'])
    @auth_guard
    def cmd_pull_both_staging(message):
        threading.Thread(target=execute_pull_for_telegram, args=('both', 'staging', message.chat.id), daemon=True).start()

    @bot.message_handler(func=lambda m: m.text == "⬇️ Pull Staging (Cả 2)")
    @auth_guard
    def btn_pull_both_staging(message):
        threading.Thread(target=execute_pull_for_telegram, args=('both', 'staging', message.chat.id), daemon=True).start()

    @bot.message_handler(commands=['pull_fe_master'])
    @auth_guard
    def cmd_pull_fe_master(message):
        threading.Thread(target=execute_pull_for_telegram, args=('fe', 'master', message.chat.id), daemon=True).start()

    @bot.message_handler(commands=['pull_be_master'])
    @auth_guard
    def cmd_pull_be_master(message):
        threading.Thread(target=execute_pull_for_telegram, args=('be', 'master', message.chat.id), daemon=True).start()

    @bot.message_handler(commands=['pull_both_master'])
    @auth_guard
    def cmd_pull_both_master(message):
        threading.Thread(target=execute_pull_for_telegram, args=('both', 'master', message.chat.id), daemon=True).start()

    @bot.message_handler(func=lambda m: m.text == "⬇️ Pull Master (Cả 2)")
    @auth_guard
    def btn_pull_both_master(message):
        threading.Thread(target=execute_pull_for_telegram, args=('both', 'master', message.chat.id), daemon=True).start()


    # Chuyển nhánh
    @bot.message_handler(commands=['switch'])
    @auth_guard
    def handle_switch(message):
        parts = message.text.strip().split(maxsplit=2)
        if len(parts) < 3:
            bot.reply_to(message, "⚠️ Cú pháp: <code>/switch &lt;fe|be&gt; &lt;tên_nhánh&gt;</code>\nVí dụ: <code>/switch fe staging</code>")
            return
        target, branch = parts[1].lower(), parts[2].strip()
        if target not in ('fe', 'be'):
            bot.reply_to(message, "⚠️ Đối tượng phải là <code>fe</code> hoặc <code>be</code>")
            return
        ws = get_workspace(target)
        label = "Frontend" if target == 'fe' else "Backend"
        ok, msg = switch_git_branch(ws, branch)
        if ok:
            bot.reply_to(message, f"✅ <b>[{label}]</b> Đã chuyển sang nhánh <code>{html.escape(branch)}</code> thành công!")
        else:
            bot.reply_to(message, f"❌ <b>[{label}] Lỗi chuyển nhánh:</b>\n{html.escape(msg)}")


    # Xem hàng đợi
    @bot.message_handler(commands=['queue'])
    @auth_guard
    def handle_queue(message):
        with state_lock:
            q = list(app_state.get('task_queue', []))
        if not q:
            bot.reply_to(message, "📋 Hàng đợi tác vụ hiện đang <b>trống</b>.")
            return
        lines = [f"<b>📋 DANH SÁCH HÀNG ĐỢI ({len(q)} tác vụ):</b>\n"]
        for idx, item in enumerate(q, 1):
            status = item.get('status', 'queued')
            icon = "▶️ Đang chạy" if status == 'running' else ("⏳ Đang chờ" if status == 'queued' else "⏹ Đã dừng")
            lines.append(f"{idx}. <b>[{html.escape(item.get('name', 'Tác vụ'))}]</b> ({icon})")
            lines.append(f"   <i>Yêu cầu: {html.escape((item.get('prompt') or item.get('fix_desc') or '')[:70])}...</i>")
        bot.send_message(message.chat.id, "\n".join(lines))


    @bot.message_handler(func=lambda m: m.text == "📋 Hàng đợi tác vụ")
    @auth_guard
    def handle_btn_queue(message):
        handle_queue(message)


    # Chạy Task từ xa
    @bot.message_handler(commands=['task'])
    @auth_guard
    def handle_task(message):
        parts = message.text.strip().split(maxsplit=2)
        if len(parts) < 3:
            bot.reply_to(message, "⚠️ Cú pháp: <code>/task &lt;fe|be|both&gt; &lt;nội dung yêu cầu&gt;</code>\nVí dụ: <code>/task fe Thêm component hiển thị trạng thái giường</code>")
            return
        target = parts[1].lower()
        if target not in ('fe', 'be', 'both'):
            target = 'both'
            prompt = message.text[5:].strip()
        else:
            prompt = parts[2].strip()

        task_id = f"task_{int(time.time())}_{uuid.uuid4().hex[:4]}"
        task_item = {
            'id': task_id,
            'name': f"Task {task_id[-4:].upper()} (Telegram)",
            'type': 'task',
            'mode': 'task',
            'prompt': prompt,
            'target': target,
            'status': 'queued',
            'skills': [],
            'action_type': 'task'
        }
        res = enqueue_task_item(task_item)
        bot.reply_to(
            message,
            f"🚀 <b>Đã đưa tác vụ vào hàng đợi thành công!</b>\n"
            f"• Mã task: <code>{task_id}</code>\n"
            f"• Phạm vi: <b>{target.upper()}</b>\n"
            f"• Vị trí hàng đợi: <b>#{res.get('queue_position', 1)}</b>\n"
            f"• Yêu cầu: <i>{html.escape(prompt)}</i>\n\n"
            f"Hệ thống AI Terminal đang tự động thực thi tuần tự."
        )


    # Chạy Fixbug từ xa
    @bot.message_handler(commands=['fixbug'])
    @auth_guard
    def handle_fixbug(message):
        parts = message.text.strip().split(maxsplit=2)
        if len(parts) < 3:
            bot.reply_to(message, "⚠️ Cú pháp: <code>/fixbug &lt;fe|be|both&gt; &lt;mô tả lỗi&gt;</code>\nVí dụ: <code>/fixbug be Lỗi 500 khi gọi API get-booking</code>")
            return
        target = parts[1].lower()
        if target not in ('fe', 'be', 'both'):
            target = 'both'
            desc = message.text[7:].strip()
        else:
            desc = parts[2].strip()

        task_id = f"fix_{int(time.time())}_{uuid.uuid4().hex[:4]}"
        task_item = {
            'id': task_id,
            'name': f"Fixbug {task_id[-4:].upper()} (Telegram)",
            'type': 'fixbug',
            'mode': 'fixbug',
            'fix_desc': desc,
            'prompt': desc,
            'target': target,
            'status': 'queued',
            'skills': [],
            'action_type': 'fixbug'
        }
        res = enqueue_task_item(task_item)
        bot.reply_to(
            message,
            f"🐞 <b>Đã đưa yêu cầu sửa lỗi vào hàng đợi!</b>\n"
            f"• Mã task: <code>{task_id}</code>\n"
            f"• Phạm vi: <b>{target.upper()}</b>\n"
            f"• Vị trí hàng đợi: <b>#{res.get('queue_position', 1)}</b>\n"
            f"• Mô tả lỗi: <i>{html.escape(desc)}</i>"
        )


    # Dừng tác vụ
    @bot.message_handler(commands=['stop'])
    @auth_guard
    def handle_stop(message):
        with state_lock:
            stopped_cnt = 0
            for tid, ts in app_state.get('active_tasks', {}).items():
                if ts.get('current_process'):
                    try:
                        ts['current_process'].kill()
                        stopped_cnt += 1
                    except Exception:
                        pass
                ts['is_running'] = False
                ts['queue_status'] = 'stopped'
            for q in app_state.get('task_queue', []):
                if q.get('status') in ('running', 'queued'):
                    q['status'] = 'stopped'
                    q['isRunning'] = False
                    stopped_cnt += 1
        bot.reply_to(message, f"⏹ <b>Đã dừng toàn bộ ({stopped_cnt}) tác vụ đang chạy và đang chờ trong hàng đợi.</b>")


    # Xem nhật ký (Logs)
    @bot.message_handler(commands=['logs'])
    @auth_guard
    def handle_logs(message):
        logs = list(reversed(load_messages()))[:5]
        if not logs:
            bot.reply_to(message, "📜 Chưa có bản ghi nhật ký nào.")
            return
        lines = [f"<b>📜 NHẬT KÝ 5 TÁC VỤ GẦN NHẤT:</b>\n"]
        for idx, item in enumerate(logs, 1):
            raw_type = (item.get('type') or 'OTHER').upper()
            type_label = (
                "Đồng bộ Git (Pull)" if raw_type == 'GIT_SYNC_PULL' else
                ("Chuyển Nhánh" if raw_type == 'GIT_SWITCH' else
                ("Git Pull" if raw_type == 'GIT_PULL' else
                ("Tác vụ" if raw_type == 'TASK' else
                ("Fix Bug" if raw_type == 'FIX_BUG' else raw_type))))
            )
            title = item.get('title') or item.get('prompt') or 'Thao tác'
            time_str = item.get('created_at') or item.get('timestamp') or ''
            status = item.get('status', 'SUCCESS')
            status_icon = "✅" if status in ('SUCCESS', 'COMPLETED') else ("⚠️" if status == 'CONFLICT' else "❌")
            lines.append(f"{idx}. {status_icon} <b>[{type_label}]</b> {html.escape(title[:60])}")
            lines.append(f"   <i>Thời gian: {time_str}</i>")
        bot.send_message(message.chat.id, "\n".join(lines))


    @bot.message_handler(func=lambda m: m.text == "📜 Nhật ký gần nhất")
    @auth_guard
    def handle_btn_logs(message):
        handle_logs(message)


    @bot.message_handler(func=lambda m: m.text == "ℹ️ Hướng dẫn / Menu")
    @auth_guard
    def handle_btn_help(message):
        handle_start(message)


    # ──────────────────────────────────────────────────────────────────────────
    # INLINE KEYBOARD CALLBACK DISPATCHER
    # ──────────────────────────────────────────────────────────────────────────

    @bot.callback_query_handler(func=lambda call: call.data == "sync:check")
    @auth_callback_guard
    def callback_sync_check(call):
        bot.answer_callback_query(call.id, "🔄 Đang kiểm tra remote origin...")
        try:
            report_text, fe_res, be_res = fetch_and_format_sync_status(do_fetch=True)
            bot.edit_message_text(
                report_text,
                chat_id=call.message.chat.id,
                message_id=call.message.message_id,
                reply_markup=build_sync_inline_keyboard(fe_res, be_res)
            )
        except Exception as e:
            bot.send_message(call.message.chat.id, f"❌ Lỗi kiểm tra: {e}")


    @bot.callback_query_handler(func=lambda call: call.data.startswith("pull:"))
    @auth_callback_guard
    def callback_pull_action(call):
        parts = call.data.split(":")
        if len(parts) >= 3:
            target, branch = parts[1], parts[2]
            bot.answer_callback_query(call.id, f"⬇️ Bắt đầu pull {branch.upper()}...")
            threading.Thread(
                target=execute_pull_for_telegram,
                args=(target, branch, call.message.chat.id),
                daemon=True
            ).start()


def send_telegram_notification(text: str, reply_markup=None):
    """Gửi tin nhắn thông báo đến tất cả các tài khoản Telegram được phân quyền."""
    if not bot or not TELEGRAM_ENABLED or not TELEGRAM_ALLOWED_USERS:
        return
    for uid in TELEGRAM_ALLOWED_USERS:
        try:
            bot.send_message(int(uid), text, reply_markup=reply_markup)
        except Exception:
            pass


def notify_task_completed(task_id: str, title: str, task_type: str = "TASK", duration: float = 0, changed_files: list = None):
    """Gửi thông báo Telegram khi một tác vụ AI Agent hoặc Fix Bug hoàn tất."""
    if not bot or not TELEGRAM_ENABLED or not TELEGRAM_ALLOWED_USERS:
        return

    now_str = datetime.datetime.now().strftime("%H:%M:%S - %d/%m/%Y")
    dur_str = f"{duration:.1f}s" if duration and duration > 0 else "Nhanh chóng"
    files_cnt = len(changed_files) if changed_files else 0

    lines = [
        "🎉 <b>TÁC VỤ AGENT ĐÃ HOÀN TẤT!</b>",
        f"⏱ <i>Thời gian: {now_str} ({dur_str})</i>",
        "",
        f"📌 <b>Tên tác vụ:</b> <b>{html.escape(title or 'Tác vụ AI Agent')}</b>",
        f"🏷 <b>Loại:</b> <code>{html.escape(str(task_type))}</code> | <b>ID:</b> <code>{html.escape(str(task_id))}</code>",
    ]

    if files_cnt > 0:
        lines.append(f"📁 <b>Tập tin đã thay đổi:</b> {files_cnt} files")
        for ch in changed_files[:6]:
            if isinstance(ch, dict):
                p = ch.get('path', '')
                r = ch.get('repo', '')
            else:
                p = str(ch)
                r = ''
            prefix = f"[{r}] " if r else ""
            lines.append(f"  • <code>{html.escape(prefix + p)}</code>")
        if files_cnt > 6:
            lines.append(f"  <i>...và {files_cnt - 6} files khác</i>")

    lines.append("")
    lines.append("✅ <i>Tác vụ đã thực thi xong thành công trên AI Terminal.</i>")

    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.row(
        types.InlineKeyboardButton("🔄 Kiểm tra Staging / Master", callback_data="sync:check"),
        types.InlineKeyboardButton("📊 Git Status", callback_data="git:status")
    )

    msg_text = "\n".join(lines)
    send_telegram_notification(msg_text, reply_markup=markup)


def run_bot_polling(verbose: bool = True):
    """Hàm chạy polling liên tục không gián đoạn (với auto-reconnect)."""
    if not bot:
        if verbose:
            print("[Telegram Bot] Bot chưa được kích hoạt do thiếu token.")
        return

    if verbose:
        print(f"\n[Telegram Bot] Khởi chạy dịch vụ bot Telegram ({TELEGRAM_BOT_NAME})...")
    while True:
        try:
            bot.infinity_polling(timeout=15, long_polling_timeout=10)
        except Exception as e:
            if verbose:
                print(f"[Telegram Bot] Lỗi polling: {e}. Đang tự động kết nối lại sau 3s...")
            time.sleep(3)


def start_telegram_service(verbose: bool = False):
    """Khởi động Telegram Bot service trong background thread an toàn."""
    if not TELEGRAM_ENABLED:
        if verbose:
            print("[Telegram Bot] Tính năng Telegram Bot đang TẮT (TELEGRAM_ENABLED=false).")
        return None

    if not TELEGRAM_BOT_TOKEN:
        if verbose:
            print("[Telegram Bot] Chưa cấu hình TELEGRAM_BOT_TOKEN.")
        return None

    t = threading.Thread(target=run_bot_polling, args=(verbose,), name="TelegramBotWorker", daemon=True)
    t.start()
    return t


if __name__ == "__main__":
    print(f"=== EasySalon Telegram Bot Standalone Service ({TELEGRAM_BOT_NAME}) ===")
    print(f"Token: {TELEGRAM_BOT_TOKEN[:10]}... (ID allowed: {TELEGRAM_ALLOWED_USERS})")
    run_bot_polling()
