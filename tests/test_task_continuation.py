#!/usr/bin/env python3
"""
Regression test suite for the "Tiếp tục task trên AI Terminal ngầm" flow.

Bug context
-----------
1. Bấm "Tiếp tục task" trước đây gọi lại `startSingleTaskById()` -> POST `/api/task`
   với `rounds: 4`, `target: 'both'` nên worker chạy lại tới 4 lượt FE/BE.
2. `run_task_worker()` luôn ghép `/skill-...` (slash prefix) và
   `build_skill_directive(skill)` vào MỌI lượt, kể cả lượt tiếp theo, làm prompt
   phình to và agent tưởng phải làm lại task từ đầu.
3. `enqueue_task_item()` cũng luôn thêm `/skill` + nhãn "Làm task:" vào
   `converted_prompt` của lượt tiếp theo.
4. Câu hỏi thuần túy như "giải thích đoạn code này" bị nhận nhầm là lệnh sửa code
   vì hàm `is_explanation_only_request()` coi từ "code" là hành động mạnh.
5. Mỗi lần tiếp tục, một bản ghi log mới chứa LẶP toàn bộ lịch sử được thêm vào
   `messages.json`.

Test strategy
-------------
- Pure unit tests for the intent classifier.
- In-process simulation of `run_task_worker()` with mocked CLI streaming, so we can
  inspect the exact prompt sent to the AI Terminal without spawning processes.
- In-process tests for `enqueue_task_item()` queue/converted_prompt behaviour.
- Static contract tests on `frontend/modules/task.js`, `frontend/app.js` and
  `studio/handler.py` to ensure the wiring does not regress.
"""

import os
import re
import sys
import unittest

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from studio.services import terminal_service as ts  # noqa: E402


SKILL = 'easysalon-task'


def _make_session_turns():
    return [
        {
            'round': 1,
            'speaker': 'fe',
            'label': 'Frontend Agent',
            'content': 'Đã sửa src/pages/Booking.tsx và thêm DTO BookingCreateRequest.',
            'step_logs': [{'params': {'Path': 'src/pages/Booking.tsx'}}],
            'changed_files': [{'repo': 'fe', 'path': 'src/pages/Booking.tsx'}],
        },
        {
            'round': 2,
            'speaker': 'be',
            'label': 'Backend Agent',
            'content': 'Đã cập nhật BookingController.cs, không cần thay đổi thêm.',
            'step_logs': [{'params': {'Path': 'Controllers/BookingController.cs'}}],
            'changed_files': [{'repo': 'be', 'path': 'Controllers/BookingController.cs'}],
        },
    ]


def _make_app_state(turns=None, extra_tasks=None):
    turns = list(turns or [])
    state = {
        'settings': {
            'engine': 'gemini_cli',
            'effort': 'high',
            'model': 'gemini-3.8-flash-high',
            'opencode_model': '9router/ag/gemini-3.8-flash',
        },
        'active_tasks': {},
        'task_queue': [],
        'is_running': False,
        'current_session': None,
        'status_text': '',
    }
    if extra_tasks:
        state['active_tasks'].update(extra_tasks)
    return state


class _WorkerHarness:
    """Mock the CLI streaming layer so run_task_worker can be exercised in-process."""

    def __init__(self):
        self.prompts = []
        self.workspaces = []
        self.timeouts = []
        self.turn_data = []
        self.messages = []
        self._orig = {}

    def __enter__(self):
        self._orig = {
            'app_state': ts.app_state,
            'build_fallback_cli_cmd': ts.build_fallback_cli_cmd,
            'stream_process_turn': ts.stream_process_turn,
            'save_queue_state_unlocked': ts.save_queue_state_unlocked,
            'load_messages': ts.load_messages,
            'save_messages': ts.save_messages,
        }
        self.state = _make_app_state()
        ts.app_state = self.state
        ts.save_queue_state_unlocked = lambda: None
        ts.load_messages = lambda: list(self.messages)
        ts.save_messages = lambda msgs: self.messages.__setitem__(slice(None), list(msgs))

        def fake_build(prompt_str, conversation_id=None):
            self.prompts.append(prompt_str)
            return ['fake-cli', prompt_str]

        def fake_stream(cmd, workspace, turn_data, timeout=300, task_state=None, repo_label=''):
            self.workspaces.append(workspace)
            self.timeouts.append(timeout)
            self.turn_data.append(dict(turn_data))
            turn_data['content'] = 'Phản hồi giả lập từ agent.'
            turn_data['elapsed_sec'] = 0.01
            return ('Phản hồi giả lập từ agent.', 0.01)

        ts.build_fallback_cli_cmd = fake_build
        ts.stream_process_turn = fake_stream
        return self

    def __exit__(self, exc_type, exc, tb):
        ts.app_state = self._orig['app_state']
        ts.build_fallback_cli_cmd = self._orig['build_fallback_cli_cmd']
        ts.stream_process_turn = self._orig['stream_process_turn']
        ts.save_queue_state_unlocked = self._orig['save_queue_state_unlocked']
        ts.load_messages = self._orig['load_messages']
        ts.save_messages = self._orig['save_messages']
        return False

    def seed_task(self, task_id='task_cont_1', prompt='Làm task gốc', skill=SKILL):
        turns = _make_session_turns()
        self.state['active_tasks'][task_id] = {
            'task_id': task_id,
            'title': 'Task gốc',
            'mode': 'task',
            'queue_status': 'done',
            'is_running': False,
            'engine': 'gemini_cli',
            'engine_label': 'Gemini CLI',
            'model': 'gemini-3.8-flash-high',
            'effort': 'high',
            'current_process': None,
            'active_round': len(turns),
            'total_rounds': len(turns),
            'active_speaker': '',
            'status_text': '',
            'session': {
                'id': 'sess_original',
                'task_id': task_id,
                'type': 'TASK',
                'prompt': prompt,
                'converted_prompt': f'/{skill} {prompt}',
                'skill': skill,
                'turns': turns,
                'changed_files': [],
                'status': 'COMPLETED',
                'created_at': '10:00:00',
            },
        }
        return task_id


# ---------------------------------------------------------------------------
# 1. Intent classifier: question vs. action
# ---------------------------------------------------------------------------
class TestExplanationIntentClassifier(unittest.TestCase):
    def test_pure_question_why_is_explain_only(self):
        self.assertTrue(ts.is_explanation_only_request('Tại sao lỗi này vẫn còn?'))

    def test_explain_code_phrase_is_explain_only(self):
        # Regression: từ "code" trước đây bị coi là hành động mạnh.
        self.assertTrue(ts.is_explanation_only_request('Giải thích giúp tôi đoạn code này'))

    def test_explain_english(self):
        self.assertTrue(ts.is_explanation_only_request('Explain why the request fails here'))

    def test_analyze_root_cause(self):
        self.assertTrue(ts.is_explanation_only_request('Phân tích nguyên nhân gây lỗi giúp tôi'))

    def test_check_root_cause(self):
        self.assertTrue(ts.is_explanation_only_request('Kiểm tra nguyên nhân lỗi này'))

    def test_negated_code_is_explain_only(self):
        self.assertTrue(ts.is_explanation_only_request('Không cần sửa code, chỉ giải thích thôi'))

    def test_what_is_question(self):
        self.assertTrue(ts.is_explanation_only_request('DTO này là gì?'))

    def test_how_does_work(self):
        self.assertTrue(ts.is_explanation_only_request('How does the booking flow work?'))

    def test_action_verb_fix(self):
        self.assertFalse(ts.is_explanation_only_request('Sửa lỗi này giúp tôi'))

    def test_action_verb_update(self):
        self.assertFalse(ts.is_explanation_only_request('Cập nhật API DTO cho booking'))

    def test_action_verb_write(self):
        self.assertFalse(ts.is_explanation_only_request('Viết thêm unit test cho module này'))

    def test_action_verb_refactor(self):
        self.assertFalse(ts.is_explanation_only_request('Refactor module booking'))

    def test_question_plus_fix_is_action(self):
        self.assertFalse(ts.is_explanation_only_request('Tại sao lỗi này vẫn còn? Sửa luôn giúp tôi'))

    def test_explain_and_fix_is_action(self):
        self.assertFalse(ts.is_explanation_only_request('Giải thích và sửa lỗi này'))

    def test_debug_is_action(self):
        self.assertFalse(ts.is_explanation_only_request('Debug lỗi này'))

    def test_delete_is_action(self):
        self.assertFalse(ts.is_explanation_only_request('Xóa file cấu hình cũ'))

    def test_explain_why_refactor_still_action(self):
        self.assertFalse(ts.is_explanation_only_request('Giải thích tại sao cần refactor đoạn này'))

    def test_empty_prompt(self):
        self.assertFalse(ts.is_explanation_only_request(''))
        self.assertFalse(ts.is_explanation_only_request(None))

    def test_plain_question_mark(self):
        self.assertTrue(ts.is_explanation_only_request('Bước tiếp theo nên làm gì?'))


# ---------------------------------------------------------------------------
# 2. Skill prefix / directive helpers
# ---------------------------------------------------------------------------
class TestSkillHelpers(unittest.TestCase):
    def test_slash_prefix_from_string(self):
        self.assertEqual(ts.format_slash_skills_prefix('easysalon-task'), '/easysalon-task')

    def test_slash_prefix_from_list(self):
        self.assertEqual(
            ts.format_slash_skills_prefix(['/fe-task', 'be-task']),
            '/fe-task /be-task',
        )

    def test_slash_prefix_empty(self):
        self.assertEqual(ts.format_slash_skills_prefix([]), '')
        self.assertEqual(ts.format_slash_skills_prefix(''), '')

    def test_skill_directive_mentions_skill_md(self):
        directive = ts.build_skill_directive(SKILL)
        self.assertIn('[HƯỚNG DẪN SKILL TRỌNG TÂM]', directive)
        self.assertIn(f'.agents/skills/{SKILL}/SKILL.md', directive)

    def test_skill_directive_empty_for_no_skill(self):
        self.assertEqual(ts.build_skill_directive(''), '')


# ---------------------------------------------------------------------------
# 3. run_task_worker: continuation must be a single conversational turn
# ---------------------------------------------------------------------------
class TestRunTaskWorkerContinuation(unittest.TestCase):
    def test_continuation_runs_exactly_one_turn_even_with_rounds_4(self):
        with _WorkerHarness() as h:
            tid = h.seed_task()
            ts.run_task_worker(
                tid,
                'Tại sao lỗi này vẫn còn?',
                'both',
                'fe',
                4,
                SKILL,
                original_prompt='Làm task gốc',
                continuation=True,
            )
            self.assertEqual(len(h.prompts), 1, 'Continuation phải chỉ chạy 1 lượt')
            self.assertEqual(len(h.turn_data), 1)

    def test_continuation_does_not_reinject_slash_skill(self):
        with _WorkerHarness() as h:
            tid = h.seed_task()
            ts.run_task_worker(tid, 'Giải thích giúp tôi', 'both', 'fe', 4, SKILL,
                               original_prompt='Làm task gốc', continuation=True)
            prompt = h.prompts[0]
            self.assertNotIn(f'/{SKILL}', prompt)
            self.assertNotIn('/easysalon-task', prompt)

    def test_continuation_does_not_reinject_skill_directive(self):
        with _WorkerHarness() as h:
            tid = h.seed_task()
            ts.run_task_worker(tid, 'Giải thích giúp tôi', 'both', 'fe', 4, SKILL,
                               original_prompt='Làm task gốc', continuation=True)
            self.assertNotIn('[HƯỚNG DẪN SKILL TRỌNG TÂM]', h.prompts[0])
            self.assertNotIn('.agents/skills/', h.prompts[0])

    def test_continuation_includes_conversation_context(self):
        with _WorkerHarness() as h:
            tid = h.seed_task()
            ts.run_task_worker(tid, 'Tại sao vậy?', 'both', 'fe', 4, SKILL,
                               original_prompt='Làm task gốc', continuation=True)
            prompt = h.prompts[0]
            self.assertIn('[NGỮ CẢNH ĐOẠN CHAT', prompt)
            self.assertIn('Booking.tsx', prompt)
            self.assertIn('BookingController.cs', prompt)

    def test_continuation_includes_followup_text(self):
        with _WorkerHarness() as h:
            tid = h.seed_task()
            ts.run_task_worker(tid, 'Tại sao BookingController lại lỗi?', 'both', 'fe', 4, SKILL,
                               original_prompt='Làm task gốc', continuation=True)
            self.assertIn('[YÊU CẦU TIẾP THEO CỦA NGƯỜI DÙNG]', h.prompts[0])
            self.assertIn('Tại sao BookingController lại lỗi?', h.prompts[0])

    def test_continuation_has_anti_rerun_note(self):
        with _WorkerHarness() as h:
            tid = h.seed_task()
            ts.run_task_worker(tid, 'Hỏi tiếp', 'both', 'fe', 4, SKILL,
                               original_prompt='Làm task gốc', continuation=True)
            self.assertIn('[LƯU Ý QUAN TRỌNG]', h.prompts[0])
            self.assertIn('KHÔNG làm lại toàn bộ task', h.prompts[0])

    def test_continuation_question_uses_explain_only_directive(self):
        with _WorkerHarness() as h:
            tid = h.seed_task()
            ts.run_task_worker(tid, 'Giải thích giúp tôi đoạn code này', 'both', 'fe', 4, SKILL,
                               original_prompt='Làm task gốc', continuation=True)
            self.assertIn('[YÊU CẦU GIẢI THÍCH - EXPLAIN ONLY]', h.prompts[0])
            self.assertNotIn('[YÊU CẦU BẮT BUỘC VỀ HÀNH ĐỘNG CODE', h.prompts[0])

    def test_continuation_action_request_uses_action_directive(self):
        with _WorkerHarness() as h:
            tid = h.seed_task()
            ts.run_task_worker(tid, 'Sửa nốt lỗi validation giúp tôi', 'both', 'fe', 4, SKILL,
                               original_prompt='Làm task gốc', continuation=True)
            self.assertIn('[YÊU CẦU BẮT BUỘC VỀ HÀNH ĐỘNG CODE', h.prompts[0])
            self.assertNotIn('[YÊU CẦU GIẢI THÍCH - EXPLAIN ONLY]', h.prompts[0])

    def test_continuation_does_not_use_action_phrase(self):
        with _WorkerHarness() as h:
            tid = h.seed_task()
            ts.run_task_worker(tid, 'Tại sao lỗi này vẫn còn?', 'both', 'fe', 4, SKILL,
                               original_prompt='Làm task gốc', continuation=True)
            self.assertNotIn('Làm task:', h.prompts[0])

    def test_continuation_keeps_original_session_prompt_and_skill(self):
        with _WorkerHarness() as h:
            tid = h.seed_task(prompt='Làm task gốc', skill=SKILL)
            ts.run_task_worker(tid, 'Hỏi thêm', 'both', 'fe', 4, SKILL,
                               original_prompt='Làm task gốc', continuation=True)
            session = h.state['active_tasks'][tid]['session']
            self.assertEqual(session['prompt'], 'Làm task gốc')
            self.assertEqual(session['skill'], SKILL)
            self.assertEqual(len(session['turns']), 3)  # 2 lượt cũ + 1 lượt tiếp theo

    def test_continuation_uses_last_speaker_workspace(self):
        with _WorkerHarness() as h:
            tid = h.seed_task()
            # Lượt cuối là BE -> phải chạy ở workspace BE.
            ts.run_task_worker(tid, 'Hỏi tiếp', 'both', 'fe', 4, SKILL,
                               original_prompt='Làm task gốc', continuation=True)
            self.assertEqual(h.workspaces[0], ts.get_be_workspace())

    def test_continuation_does_not_duplicate_message_history(self):
        with _WorkerHarness() as h:
            tid = h.seed_task()
            ts.run_task_worker(tid, 'Hỏi lần 1', 'both', 'fe', 4, SKILL,
                               original_prompt='Làm task gốc', continuation=True)
            self.assertEqual(len(h.messages), 1)
            first_id = h.messages[0]['id']
            ts.run_task_worker(tid, 'Hỏi lần 2', 'both', 'fe', 4, SKILL,
                               original_prompt='Làm task gốc', continuation=True)
            self.assertEqual(len(h.messages), 1, 'Tiếp tục không được tạo thêm bản ghi log')
            self.assertEqual(h.messages[0]['id'], first_id)
            self.assertEqual(len(h.messages[0]['turns']), 4)  # 2 cũ + 2 lượt tiếp theo

    def test_continuation_is_flagged_on_turn(self):
        with _WorkerHarness() as h:
            tid = h.seed_task()
            ts.run_task_worker(tid, 'Hỏi tiếp', 'both', 'fe', 4, SKILL,
                               original_prompt='Làm task gốc', continuation=True)
            self.assertTrue(h.turn_data[0].get('is_continuation'))


# ---------------------------------------------------------------------------
# 4. run_task_worker: initial task still injects skill (no regression)
# ---------------------------------------------------------------------------
class TestRunTaskWorkerInitialTask(unittest.TestCase):
    def test_initial_single_target_injects_slash_and_skill_directive(self):
        with _WorkerHarness() as h:
            ts.run_task_worker('task_new_1', 'Thêm màn hình booking', 'fe', 'fe', 4, SKILL,
                               original_prompt='Thêm màn hình booking', continuation=False)
            prompt = h.prompts[0]
            self.assertIn(f'/{SKILL}', prompt)
            self.assertIn('[HƯỚNG DẪN SKILL TRỌNG TÂM]', prompt)

    def test_initial_both_runs_multiple_rounds(self):
        with _WorkerHarness() as h:
            ts.run_task_worker('task_new_2', 'Thêm màn hình booking', 'both', 'fe', 4, SKILL,
                               original_prompt='Thêm màn hình booking', continuation=False)
            self.assertEqual(len(h.prompts), 4, 'Task khởi tạo target=both vẫn chạy đủ số vòng')
            for p in h.prompts:
                self.assertIn('[HƯỚNG DẪN SKILL TRỌNG TÂM]', p)

    def test_initial_action_prompt_contains_action_phrase(self):
        with _WorkerHarness() as h:
            ts.run_task_worker('task_new_3', 'Thêm màn hình booking', 'fe', 'fe', 4, SKILL,
                               original_prompt='Thêm màn hình booking', continuation=False)
            self.assertIn('Làm task:', h.prompts[0])

    def test_initial_message_is_created(self):
        with _WorkerHarness() as h:
            ts.run_task_worker('task_new_4', 'Thêm màn hình booking', 'fe', 'fe', 4, SKILL,
                               original_prompt='Thêm màn hình booking', continuation=False)
            self.assertEqual(len(h.messages), 1)
            self.assertEqual(h.messages[0]['task_id'], 'task_new_4')


# ---------------------------------------------------------------------------
# 5. enqueue_task_item: converted_prompt contract
# ---------------------------------------------------------------------------
class _QueueHarness:
    def __init__(self):
        self._orig = {}

    def __enter__(self):
        self._orig = {
            'app_state': ts.app_state,
            'save_queue_state_unlocked': ts.save_queue_state_unlocked,
        }
        ts.app_state = _make_app_state()
        ts.save_queue_state_unlocked = lambda: None
        return self

    def __exit__(self, exc_type, exc, tb):
        ts.app_state = self._orig['app_state']
        ts.save_queue_state_unlocked = self._orig['save_queue_state_unlocked']
        return False


class TestEnqueueTaskItem(unittest.TestCase):
    def test_initial_enqueue_adds_slash_and_action_phrase(self):
        with _QueueHarness() as h:
            res = ts.enqueue_task_item({
                'id': 'q1', 'mode': 'task', 'title': 'Task 1',
                'prompt': 'Thêm màn hình booking', 'skills': [SKILL],
            })
            self.assertTrue(res['converted_prompt'].startswith(f'/{SKILL} '))
            self.assertIn('Làm task:', res['converted_prompt'])

    def test_continuation_enqueue_has_no_slash_prefix(self):
        with _QueueHarness() as h:
            res = ts.enqueue_task_item({
                'id': 'q2', 'mode': 'task', 'title': 'Task 1',
                'prompt': 'Tại sao lỗi này vẫn còn?', 'skills': [SKILL],
                'continuation': True,
            })
            self.assertNotIn('/easysalon-task', res['converted_prompt'])

    def test_continuation_enqueue_has_no_action_phrase(self):
        with _QueueHarness() as h:
            res = ts.enqueue_task_item({
                'id': 'q3', 'mode': 'task', 'title': 'Task 1',
                'prompt': 'Tại sao lỗi này vẫn còn?', 'skills': [SKILL],
                'continuation': True,
            })
            self.assertNotIn('Làm task:', res['converted_prompt'])
            self.assertIn('Tại sao lỗi này vẫn còn?', res['converted_prompt'])

    def test_continuation_enqueue_marks_queue_item(self):
        with _QueueHarness() as h:
            ts.enqueue_task_item({
                'id': 'q4', 'mode': 'task', 'title': 'Task 1',
                'prompt': 'Hỏi tiếp', 'skills': [SKILL], 'continuation': True,
            })
            q = ts.app_state['task_queue'][0]
            self.assertTrue(q.get('continuation'))

    def test_continuation_enqueue_forces_single_round_contract(self):
        with _QueueHarness() as h:
            ts.enqueue_task_item({
                'id': 'q5', 'mode': 'task', 'title': 'Task 1',
                'prompt': 'Hỏi tiếp', 'skills': [SKILL], 'continuation': True, 'rounds': 1,
            })
            self.assertEqual(ts.app_state['task_queue'][0].get('rounds'), 1)


# ---------------------------------------------------------------------------
# 6. run_fixbug_worker: continuation behaviour
# ---------------------------------------------------------------------------
class TestRunFixbugWorkerContinuation(unittest.TestCase):
    def _seed_fix_task(self, h, task_id='task_fix_1'):
        turns = _make_session_turns()
        h.state['active_tasks'][task_id] = {
            'task_id': task_id,
            'title': 'Fix bug gốc',
            'mode': 'fixbug',
            'queue_status': 'done',
            'is_running': False,
            'engine': 'gemini_cli',
            'engine_label': 'Gemini CLI',
            'model': 'gemini-3.8-flash-high',
            'effort': 'high',
            'current_process': None,
            'active_round': len(turns),
            'total_rounds': len(turns),
            'active_speaker': '',
            'status_text': '',
            'session': {
                'id': 'sess_fix_original',
                'task_id': task_id,
                'type': 'FIX_BUG',
                'description': 'Lỗi validation form booking',
                'skill': SKILL,
                'turns': turns,
                'changed_files': [],
                'status': 'COMPLETED',
                'created_at': '10:00:00',
            },
        }
        return task_id

    def test_fixbug_continuation_runs_one_turn_for_both_scope(self):
        with _WorkerHarness() as h:
            tid = self._seed_fix_task(h)
            ts.run_fixbug_worker(tid, SKILL, 'both', 'Tại sao vẫn lỗi?', '',
                                 original_prompt='Lỗi validation form booking', continuation=True)
            self.assertEqual(len(h.prompts), 1)

    def test_fixbug_continuation_does_not_reinject_skill(self):
        with _WorkerHarness() as h:
            tid = self._seed_fix_task(h)
            ts.run_fixbug_worker(tid, SKILL, 'both', 'Giải thích giúp tôi', '',
                                 original_prompt='Lỗi validation form booking', continuation=True)
            prompt = h.prompts[0]
            self.assertNotIn(f'/{SKILL}', prompt)
            self.assertNotIn('[HƯỚNG DẪN SKILL TRỌNG TÂM]', prompt)

    def test_fixbug_continuation_includes_context_and_question(self):
        with _WorkerHarness() as h:
            tid = self._seed_fix_task(h)
            ts.run_fixbug_worker(tid, SKILL, 'both', 'Vì sao controller lỗi?', '',
                                 original_prompt='Lỗi validation form booking', continuation=True)
            prompt = h.prompts[0]
            self.assertIn('[NGỮ CẢNH ĐOẠN CHAT', prompt)
            self.assertIn('Vì sao controller lỗi?', prompt)
            self.assertIn('[YÊU CẦU GIẢI THÍCH - EXPLAIN ONLY]', prompt)

    def test_fixbug_continuation_keeps_original_description(self):
        with _WorkerHarness() as h:
            tid = self._seed_fix_task(h)
            ts.run_fixbug_worker(tid, SKILL, 'both', 'Hỏi thêm', '',
                                 original_prompt='Lỗi validation form booking', continuation=True)
            session = h.state['active_tasks'][tid]['session']
            self.assertEqual(session['description'], 'Lỗi validation form booking')

    def test_fixbug_continuation_does_not_duplicate_messages(self):
        with _WorkerHarness() as h:
            tid = self._seed_fix_task(h)
            ts.run_fixbug_worker(tid, SKILL, 'both', 'Hỏi 1', '',
                                 original_prompt='Lỗi gốc', continuation=True)
            ts.run_fixbug_worker(tid, SKILL, 'both', 'Hỏi 2', '',
                                 original_prompt='Lỗi gốc', continuation=True)
            self.assertEqual(len(h.messages), 1)
            self.assertEqual(len(h.messages[0]['turns']), 4)

    def test_fixbug_continuation_does_not_resend_original_error_log(self):
        with _WorkerHarness() as h:
            tid = self._seed_fix_task(h)
            # Gắn log lỗi gốc vào session để kiểm tra nó không bị gửi lại.
            h.state['active_tasks'][tid]['session']['error_log'] = 'STACK_TRACE_ORIGINAL_SHOULD_NOT_REPEAT'
            ts.run_fixbug_worker(tid, SKILL, 'both', 'Hỏi tiếp', '',
                                 original_prompt='Lỗi gốc', continuation=True)
            self.assertNotIn('STACK_TRACE_ORIGINAL_SHOULD_NOT_REPEAT', h.prompts[0])

    def test_initial_fixbug_both_scope_runs_two_turns_with_skill(self):
        with _WorkerHarness() as h:
            ts.run_fixbug_worker('task_fix_new', SKILL, 'both', 'Lỗi validation', 'stack...',
                                 original_prompt='Lỗi validation', continuation=False)
            self.assertEqual(len(h.prompts), 2)
            for p in h.prompts:
                self.assertIn('[HƯỚNG DẪN SKILL TRỌNG TÂM]', p)
            self.assertIn(f'/{SKILL}', h.prompts[0])


# ---------------------------------------------------------------------------
# 7. Static wiring contract (frontend + handler)
# ---------------------------------------------------------------------------
class TestContinuationWiringContract(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        with open(os.path.join(BASE_DIR, 'frontend', 'modules', 'task.js'), 'r', encoding='utf-8') as f:
            cls.task_js = f.read()
        app_js_path = os.path.join(BASE_DIR, 'frontend', 'app.js')
        cls.app_js = ''
        if os.path.exists(app_js_path):
            with open(app_js_path, 'r', encoding='utf-8') as f:
                cls.app_js = f.read()
        with open(os.path.join(BASE_DIR, 'studio', 'handler.py'), 'r', encoding='utf-8') as f:
            cls.handler_py = f.read()
        with open(os.path.join(BASE_DIR, 'studio', 'services', 'terminal_service.py'), 'r', encoding='utf-8') as f:
            cls.terminal_py = f.read()

    def test_frontend_sends_continuation_flag(self):
        self.assertIn('continuation: true', self.task_js)

    def test_frontend_continuation_sends_rounds_1(self):
        self.assertIn('rounds: 1', self.task_js)

    def test_frontend_continue_does_not_call_full_task_start(self):
        match = re.search(r'async function continueTaskFromFeed\([^)]*\)\s*\{([\s\S]*?)\n\}', self.task_js)
        self.assertIsNotNone(match)
        body = match.group(1)
        self.assertNotIn('startSingleTaskById', body)
        self.assertIn('startContinuationTask', body)

    def test_frontend_continue_does_not_mutate_task_prompt(self):
        match = re.search(r'async function continueTaskFromFeed\([^)]*\)\s*\{([\s\S]*?)\n\}', self.task_js)
        body = match.group(1)
        self.assertNotIn('task.prompt = followUp', body)

    def test_frontend_continue_does_not_reload_form_with_followup(self):
        match = re.search(r'async function continueTaskFromFeed\([^)]*\)\s*\{([\s\S]*?)\n\}', self.task_js)
        body = match.group(1)
        self.assertNotIn('loadTaskToForm', body)

    def test_app_bundle_contains_continuation_flag(self):
        self.assertIn('continuation: true', self.app_js)

    def test_handler_parses_continuation_flag(self):
        self.assertIn("is_continuation = bool(body.get('continuation')", self.handler_py)

    def test_handler_forces_single_round_for_continuation(self):
        self.assertIn('rounds = 1', self.handler_py)

    def test_handler_passes_continuation_to_queue(self):
        self.assertIn("'continuation': is_continuation", self.handler_py)

    def test_worker_accepts_continuation_parameter(self):
        self.assertIn('continuation: bool = False', self.terminal_py)

    def test_worker_guards_skill_prefix_for_continuation(self):
        self.assertIn("slash_prefix = '' if is_continuation else format_slash_skills_prefix(skill)", self.terminal_py)

    def test_worker_has_dedicated_continuation_branch(self):
        self.assertIn('if is_continuation:', self.terminal_py)

    def test_worker_does_not_reinject_skill_directive_in_continuation_branch(self):
        match = re.search(r'if is_continuation:\n([\s\S]*?)\n    elif target in', self.terminal_py)
        self.assertIsNotNone(match)
        branch = match.group(1)
        self.assertNotIn('build_skill_directive(skill)', branch)

    def test_queue_worker_forwards_continuation(self):
        self.assertIn('continuation=bool(next_item.get(', self.terminal_py)

    def test_messages_are_updated_not_duplicated(self):
        self.assertIn('prev_idx', self.terminal_py)

    def test_settings_api_deeplink_uses_existing_dom_id(self):
        self.assertNotIn("getElementById('settingsSubTab_api')", self.task_js)
        self.assertIn('settingsNav_api', self.task_js)

    def test_frontend_fixbug_continuation_uses_fixbug_endpoint(self):
        self.assertIn("'/api/fixbug'", self.task_js)

    def test_handler_fixbug_parses_continuation(self):
        match = re.search(r"elif path == '/api/fixbug':([\s\S]*?)\n        elif ", self.handler_py)
        self.assertIsNotNone(match)
        self.assertIn('is_continuation', match.group(1))
        self.assertIn("'continuation': is_continuation", match.group(1))

    def test_fixbug_worker_accepts_continuation_parameter(self):
        self.assertIn(
            'def run_fixbug_worker(task_id: str, skill, scope: str, description: str, error_log: str, original_prompt: str = \'\', continuation: bool = False)',
            self.terminal_py,
        )


if __name__ == '__main__':
    unittest.main(verbosity=2)
