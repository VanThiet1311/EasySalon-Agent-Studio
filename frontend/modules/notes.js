/**
 * EasySalon Notes Module
 * Quản lý sổ tay ghi chú & kỹ thuật của hệ thống Easysalon-Tool
 */

window.notesList = [];
window.activeNoteId = null;
window.activeNoteCategoryFilter = 'all';
window._notesAutoSaveTimer = null;

function getCachedNotesList() {
  try {
    const cached = localStorage.getItem('easysalon_notes_cache');
    if (cached) {
      const parsed = JSON.parse(cached);
      if (Array.isArray(parsed)) return parsed;
    }
  } catch (e) { }
  return [];
}

/**
 * Khởi tạo & tải dữ liệu tab Ghi chú
 */
async function loadNotesWorkspace() {
  const container = document.getElementById('notesListContainer');
  if (container && (!window.notesList || window.notesList.length === 0)) {
    container.innerHTML = '<div class="text-center py-10 text-slate-400 text-xs italic font-sans">Đang nạp danh sách ghi chú...</div>';
  }

  // 1. Nạp từ localStorage trước để hiển thị giao diện tức thì
  const cached = getCachedNotesList();
  if (cached.length > 0 && (!window.notesList || window.notesList.length === 0)) {
    window.notesList = cached;
    renderNotesList();
    const savedActiveId = window.activeNoteId || localStorage.getItem('easysalon_active_note_id');
    const targetNote = window.notesList.find(n => n.id === savedActiveId) || window.notesList[0];
    if (targetNote) selectNote(targetNote.id);
  }

  // 2. Tải danh sách ghi chú từ server và đồng bộ hai chiều
  try {
    const res = await fetch('/api/notes');
    const data = await res.json();
    if (data && data.success && Array.isArray(data.notes)) {
      const serverNotes = data.notes;
      const cachedNotes = getCachedNotesList();

      // Hợp nhất: nếu có ghi chú trong localStorage mà server chưa có (do trước đây bị deadlock lỗi lưu), đẩy lên server
      const serverIds = new Set(serverNotes.map(n => n.id));
      const missingNotes = cachedNotes.filter(n => n && n.id && !serverIds.has(n.id));

      if (missingNotes.length > 0) {
        window.notesList = [...missingNotes, ...serverNotes];
        missingNotes.forEach(n => {
          fetch('/api/notes', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(n)
          }).catch(() => {});
        });
      } else if (serverNotes.length > 0) {
        window.notesList = serverNotes;
      }

      try {
        localStorage.setItem('easysalon_notes_cache', JSON.stringify(window.notesList));
      } catch (e) { }
    }
  } catch (err) {
    console.warn('Không thể tải ghi chú từ server, sử dụng bộ nhớ cục bộ:', err);
  }

  // Khởi tạo ghi chú mẫu nếu danh sách trống
  if (!window.notesList || window.notesList.length === 0) {
    const defaultNote = {
      id: 'note-welcome',
      title: 'Ghi chú công việc & Lưu ý kỹ thuật',
      content: '# Sổ tay ghi chú dự án EasySalon\n\n- Ghi chú được **tự động lưu** và đồng bộ an toàn.\n- Nhấn nút **Đưa vào Tác vụ** để chuyển nhanh nội dung sang Agent Prompt.\n- Có thể gắn kèm mã Ticket Jira để quản lý theo từng đầu việc.\n\n### Checklist mẫu:\n- [ ] Pull code mới nhất từ nhánh staging/master\n- [ ] Kiểm tra video minh chứng lỗi (mp4/webm) từ ticket Jira\n- [ ] Chạy bộ kiểm thử tự động 78 bài test',
      category: 'general',
      jira_key: '',
      created_at: formatCurrentTime(),
      updated_at: formatCurrentTime()
    };
    window.notesList = [defaultNote];
  }

  renderNotesList();

  // Chọn ghi chú đang mở hoặc ghi chú đầu tiên
  const savedActiveId = window.activeNoteId || localStorage.getItem('easysalon_active_note_id');
  const targetNote = window.notesList.find(n => n.id === savedActiveId) || window.notesList[0];
  if (targetNote) {
    selectNote(targetNote.id);
  }
}
window.loadNotesWorkspace = loadNotesWorkspace;

function loadNotesFromLocalStorage() {
  const cached = getCachedNotesList();
  if (cached.length > 0) {
    window.notesList = cached;
  }
}

function formatCurrentTime() {
  const d = new Date();
  const pad = n => String(n).padStart(2, '0');
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())} ${pad(d.getHours())}:${pad(d.getMinutes())}:${pad(d.getSeconds())}`;
}

function renderNoteJiraBadge(jiraKey) {
  if (!jiraKey) return '';
  const str = String(jiraKey).trim();
  const m = str.match(/([a-zA-Z0-9]+-\d+)/);
  const label = m ? m[1].toUpperCase() : (str.length > 22 ? str.slice(0, 20) + '...' : str);
  return `
    <span class="note-card-jira text-[9.5px] font-mono px-1.5 py-0.5 rounded border truncate" title="${escapeHtml(str)}">
      ${escapeHtml(label)}
    </span>
  `;
}
window.renderNoteJiraBadge = renderNoteJiraBadge;

function updateJiraOpenButton(jiraKeyOrUrl) {
  const btn = document.getElementById('noteJiraKeyLinkBtn');
  if (!btn) return;
  const raw = String(jiraKeyOrUrl || '').trim();
  if (!raw) {
    btn.classList.add('hidden');
    btn.classList.remove('inline-flex');
    btn.removeAttribute('href');
    return;
  }

  let url = '';
  if (/^https?:\/\//i.test(raw)) {
    url = raw;
  } else {
    const m = raw.match(/([a-zA-Z0-9]+-\d+)/);
    if (m) {
      const host = (window.jiraStatus && window.jiraStatus.host) || 'https://myeasysalon.atlassian.net';
      url = `${host.replace(/\/+$/, '')}/browse/${m[1].toUpperCase()}`;
    }
  }

  if (url) {
    btn.href = url;
    btn.classList.remove('hidden');
    btn.classList.add('inline-flex');
  } else {
    btn.classList.add('hidden');
    btn.classList.remove('inline-flex');
    btn.removeAttribute('href');
  }
}
window.updateJiraOpenButton = updateJiraOpenButton;

/**
 * Hiển thị danh sách ghi chú ở cột bên trái
 */
function renderNotesList() {
  const container = document.getElementById('notesListContainer');
  const countAll = document.getElementById('notesCountAll');
  const searchInput = document.getElementById('notesSearchInput');
  const query = (searchInput ? searchInput.value : '').trim().toLowerCase();
  const filterCat = window.activeNoteCategoryFilter || 'all';

  if (countAll) countAll.textContent = (window.notesList || []).length;

  let filtered = (window.notesList || []).filter(n => {
    // Lọc chuyên mục
    if (filterCat !== 'all') {
      if (filterCat === 'jira') {
        if (!n.jira_key && n.category !== 'jira') return false;
      } else if (filterCat === 'git') {
        if (n.category !== 'git' && n.category !== 'deploy_git') return false;
      } else if (filterCat === 'deploy') {
        if (n.category !== 'deploy' && n.category !== 'deploy_git') return false;
      } else if (n.category !== filterCat) {
        return false;
      }
    }
    // Lọc tìm kiếm
    if (query) {
      const t = (n.title || '').toLowerCase();
      const c = (n.content || '').toLowerCase();
      const j = (n.jira_key || '').toLowerCase();
      return t.includes(query) || c.includes(query) || j.includes(query);
    }
    return true;
  });

  if (!container) return;

  if (filtered.length === 0) {
    container.innerHTML = '<div class="text-center py-8 text-slate-400 text-xs italic font-sans">Không tìm thấy ghi chú nào phù hợp.</div>';
    return;
  }

  container.innerHTML = filtered.map(n => {
    const isSel = (n.id === window.activeNoteId);
    const activeClass = isSel ? 'is-active' : '';

    const snippet = (n.content || '').replace(/[#*`~>-]/g, '').trim().slice(0, 75);
    const timeDisplay = (n.updated_at || n.created_at || '').slice(5, 16);

    let catLabel = 'Chung';
    if (n.category === 'tech') catLabel = 'Kỹ thuật';
    else if (n.category === 'api') catLabel = 'API / DB';
    else if (n.category === 'deploy') catLabel = 'Deploy';
    else if (n.category === 'git') catLabel = 'Git';
    else if (n.category === 'checklist') catLabel = 'Checklist';
    else if (n.category === 'jira') catLabel = 'Jira';

    return `
      <div onclick="selectNote('${escapeHtml(n.id)}')"
        class="note-item-card p-3 rounded-lg border transition cursor-pointer select-none space-y-1.5 ${activeClass}">
        <div class="flex items-center justify-between gap-1.5 text-xs">
          <span class="note-card-title font-bold font-sans truncate">
            ${escapeHtml(n.title || 'Ghi chú không tên')}
          </span>
          <div class="flex items-center gap-1 shrink-0">
            <span class="note-card-time text-[10px] font-mono">${escapeHtml(timeDisplay)}</span>
            <button type="button" onclick="event.stopPropagation(); deleteNoteItem('${escapeHtml(n.id)}')"
              class="note-card-delete-btn p-1 rounded transition cursor-pointer"
              title="Xóa ghi chú này">
              <svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
              </svg>
            </button>
          </div>
        </div>
        <p class="note-card-snippet text-[11px] line-clamp-2 leading-relaxed font-sans">
          ${escapeHtml(snippet || '(Nội dung trống)')}
        </p>
        <div class="flex items-center gap-1.5 pt-0.5">
          <span class="note-card-badge text-[9.5px] font-sans px-1.5 py-0.5 rounded border">
            ${escapeHtml(catLabel)}
          </span>
          ${renderNoteJiraBadge(n.jira_key)}
        </div>
      </div>
    `;
  }).join('');
}
window.renderNotesList = renderNotesList;

/**
 * Chọn một ghi chú để sửa ở khung bên phải
 */
function selectNote(noteId) {
  const note = (window.notesList || []).find(n => n.id === noteId);
  if (!note) return;

  window.activeNoteId = noteId;
  try {
    localStorage.setItem('easysalon_active_note_id', noteId);
  } catch (e) { }

  const titleInput = document.getElementById('noteTitleInput');
  const catSelect = document.getElementById('noteCategorySelect');
  const jiraInput = document.getElementById('noteJiraKeyInput');
  const contentInput = document.getElementById('noteContentInput');
  const lastModEl = document.getElementById('noteLastModified');
  const badgeEl = document.getElementById('noteAutoSaveBadge');

  if (titleInput) titleInput.value = note.title || '';
  if (catSelect) catSelect.value = note.category || 'general';
  if (jiraInput) jiraInput.value = note.jira_key || '';
  if (contentInput) contentInput.value = note.content || '';
  if (lastModEl) lastModEl.textContent = note.updated_at || note.created_at || 'Mới';
  if (badgeEl) {
    badgeEl.textContent = 'Đã lưu';
    badgeEl.className = 'text-[11px] font-sans font-medium px-2 py-0.5 rounded-full bg-emerald-950/70 text-emerald-300 border border-emerald-800';
  }

  updateJiraOpenButton(note.jira_key);
  updateNoteStats();
  renderNotesList();
}
window.selectNote = selectNote;

/**
 * Tạo một ghi chú mới
 */
function createNewNote() {
  const newId = `note-${Date.now()}`;
  const nowStr = formatCurrentTime();
  const newNote = {
    id: newId,
    title: 'Ghi chú mới',
    content: '',
    category: window.activeNoteCategoryFilter !== 'all' ? window.activeNoteCategoryFilter : 'general',
    jira_key: '',
    created_at: nowStr,
    updated_at: nowStr
  };

  window.notesList.unshift(newNote);
  selectNote(newId);

  const titleInput = document.getElementById('noteTitleInput');
  if (titleInput) {
    titleInput.focus();
    titleInput.select();
  }

  triggerAutoSaveNote(true);
}
window.createNewNote = createNewNote;

function onNoteTitleInput(val) {
  const note = (window.notesList || []).find(n => n.id === window.activeNoteId);
  if (!note) return;
  note.title = val;
  note.updated_at = formatCurrentTime();
  triggerAutoSaveNote();
}
window.onNoteTitleInput = onNoteTitleInput;

function onNoteContentInput(val) {
  const note = (window.notesList || []).find(n => n.id === window.activeNoteId);
  if (!note) return;
  note.content = val;
  note.updated_at = formatCurrentTime();
  updateNoteStats();
  triggerAutoSaveNote();
}
window.onNoteContentInput = onNoteContentInput;

function onNoteCategoryChange(val) {
  const note = (window.notesList || []).find(n => n.id === window.activeNoteId);
  if (!note) return;
  note.category = val;
  note.updated_at = formatCurrentTime();
  triggerAutoSaveNote(true);
}
window.onNoteCategoryChange = onNoteCategoryChange;

function onNoteJiraKeyInput(val) {
  const note = (window.notesList || []).find(n => n.id === window.activeNoteId);
  if (!note) return;
  const raw = (val || '').trim();
  note.jira_key = /^https?:\/\//i.test(raw) ? raw : raw.toUpperCase();
  note.updated_at = formatCurrentTime();
  updateJiraOpenButton(note.jira_key);
  triggerAutoSaveNote();
}
window.onNoteJiraKeyInput = onNoteJiraKeyInput;

function updateNoteStats() {
  const contentInput = document.getElementById('noteContentInput');
  const wordEl = document.getElementById('noteWordCount');
  const charEl = document.getElementById('noteCharCount');
  const text = (contentInput ? contentInput.value : '') || '';

  const chars = text.length;
  const words = text.trim() ? text.trim().split(/\s+/).length : 0;

  if (wordEl) wordEl.textContent = `${words} từ`;
  if (charEl) charEl.textContent = `${chars} ký tự`;
}

function triggerAutoSaveNote(immediate = false) {
  const badgeEl = document.getElementById('noteAutoSaveBadge');
  if (badgeEl) {
    badgeEl.textContent = 'Đang lưu...';
    badgeEl.className = 'text-[11px] font-sans font-medium px-2 py-0.5 rounded-full bg-amber-950/70 text-amber-300 border border-amber-800';
  }

  // 1. Lưu ngay vào localStorage
  try {
    localStorage.setItem('easysalon_notes_cache', JSON.stringify(window.notesList));
  } catch (e) { }

  // 2. Cập nhật thẻ hiển thị trên danh sách ghi chú bên trái
  renderNotesList();

  clearTimeout(window._notesAutoSaveTimer);
  const delay = immediate ? 0 : 250;

  window._notesAutoSaveTimer = setTimeout(async () => {
    const note = (window.notesList || []).find(n => n.id === window.activeNoteId);
    if (!note) return;

    try {
      const res = await fetch('/api/notes', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(note)
      });
      const data = await res.json();
      if (data && data.success) {
        if (badgeEl) {
          badgeEl.textContent = 'Đã lưu';
          badgeEl.className = 'text-[11px] font-sans font-medium px-2 py-0.5 rounded-full bg-emerald-950/70 text-emerald-300 border border-emerald-800';
        }
        const lastModEl = document.getElementById('noteLastModified');
        if (lastModEl && data.note && data.note.updated_at) {
          lastModEl.textContent = data.note.updated_at;
        }
      } else {
        if (badgeEl) {
          badgeEl.textContent = 'Đã lưu cục bộ';
          badgeEl.className = 'text-[11px] font-sans font-medium px-2 py-0.5 rounded-full bg-blue-950/70 text-blue-300 border border-blue-800';
        }
      }
    } catch (err) {
      if (badgeEl) {
        badgeEl.textContent = 'Đã lưu cục bộ';
        badgeEl.className = 'text-[11px] font-sans font-medium px-2 py-0.5 rounded-full bg-blue-950/70 text-blue-300 border border-blue-800';
      }
    }
  }, delay);
}
window.triggerAutoSaveNote = triggerAutoSaveNote;

/**
 * Xóa một ghi chú theo ID
 */
async function deleteNoteItem(noteId) {
  const note = (window.notesList || []).find(n => n.id === noteId);
  if (!note) return;

  const noteTitle = note.title || 'không tên';
  let confirmed = false;

  if (typeof antdConfirm === 'function') {
    confirmed = await antdConfirm({
      title: 'Xóa ghi chú',
      content: `Bạn có chắc chắn muốn xóa ghi chú "${noteTitle}"? Thao tác này không thể hoàn tác.`,
      okText: 'Xác nhận xóa',
      danger: true
    });
  } else {
    confirmed = window.confirm(`Bạn có chắc chắn muốn xóa ghi chú "${noteTitle}"? Thao tác này không thể hoàn tác.`);
  }

  if (!confirmed) return;

  window.notesList = window.notesList.filter(n => n.id !== noteId);

  try {
    localStorage.setItem('easysalon_notes_cache', JSON.stringify(window.notesList));
    await fetch('/api/notes/delete', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ id: noteId })
    });
  } catch (err) {
    console.error('Lỗi khi xóa ghi chú trên server:', err);
  }

  showToast('Đã xóa ghi chú thành công!', 'success');

  if (window.activeNoteId === noteId) {
    if (window.notesList.length > 0) {
      selectNote(window.notesList[0].id);
    } else {
      createNewNote();
    }
  } else {
    renderNotesList();
  }
}
window.deleteNoteItem = deleteNoteItem;

/**
 * Xóa ghi chú đang kích hoạt
 */
async function deleteActiveNote() {
  if (!window.activeNoteId) return;
  await deleteNoteItem(window.activeNoteId);
}
window.deleteActiveNote = deleteActiveNote;

/**
 * Đưa nội dung ghi chú sang Prompt Agent ở trang Tác vụ
 */
function sendActiveNoteToTask() {
  const note = (window.notesList || []).find(n => n.id === window.activeNoteId);
  if (!note || !note.content.trim()) {
    showToast('Ghi chú đang trống, vui lòng viết nội dung trước khi chuyển!', 'error');
    return;
  }

  const promptInput = document.getElementById('taskPromptInput');
  if (!promptInput) {
    showToast('Không tìm thấy khung nhập tác vụ', 'error');
    return;
  }

  let formatted = `[Ghi chú: ${note.title || 'Kỹ thuật'}]\n`;
  if (note.jira_key) formatted += `Ticket Jira: ${note.jira_key}\n`;
  formatted += `\n${note.content.trim()}\n`;

  promptInput.value = promptInput.value.trim() ? (promptInput.value.trim() + '\n\n' + formatted) : formatted;

  if (typeof onTaskPromptInput === 'function') {
    onTaskPromptInput();
  } else {
    promptInput.dispatchEvent(new Event('input', { bubbles: true }));
  }

  if (typeof switchTab === 'function') switchTab('task');
  setTimeout(() => {
    promptInput.focus();
    promptInput.scrollIntoView({ behavior: 'smooth', block: 'center' });
  }, 100);

  showToast('Đã chuyển nội dung ghi chú sang Tác vụ Agent!', 'success');
}
window.sendActiveNoteToTask = sendActiveNoteToTask;

/**
 * Sao chép ghi chú vào clipboard
 */
async function copyActiveNote() {
  const contentInput = document.getElementById('noteContentInput');
  const titleInput = document.getElementById('noteTitleInput');
  const text = contentInput ? contentInput.value : '';

  if (!text.trim()) {
    showToast('Nội dung ghi chú đang trống!', 'error');
    return;
  }

  const title = (titleInput ? titleInput.value : '').trim();
  const fullText = title ? `# ${title}\n\n${text}` : text;

  try {
    if (navigator.clipboard && navigator.clipboard.writeText) {
      await navigator.clipboard.writeText(fullText);
    } else {
      const ta = document.createElement('textarea');
      ta.value = fullText;
      document.body.appendChild(ta);
      ta.select();
      document.execCommand('copy');
      document.body.removeChild(ta);
    }
    showToast('Đã sao chép nội dung ghi chú vào bộ nhớ tạm!', 'success');
  } catch (err) {
    showToast('Không thể sao chép: ' + err.message, 'error');
  }
}
window.copyActiveNote = copyActiveNote;

/**
 * Tải ghi chú dưới dạng tệp .md
 */
function exportActiveNoteMarkdown() {
  const note = (window.notesList || []).find(n => n.id === window.activeNoteId);
  const title = (note ? note.title : 'ghi-chu') || 'ghi-chu';
  const content = note ? note.content : '';

  const safeFilename = title.toLowerCase().replace(/[^a-z0-9_-]/g, '_').replace(/_+/g, '_') + '.md';
  const blob = new Blob([`# ${title}\n\n${content}`], { type: 'text/markdown;charset=utf-8' });
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = safeFilename;
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  URL.revokeObjectURL(url);

  showToast(`Đã tải xuống tệp ${safeFilename}!`, 'success');
}
window.exportActiveNoteMarkdown = exportActiveNoteMarkdown;

/**
 * Lọc chuyên mục
 */
function setNoteCategoryFilter(category) {
  window.activeNoteCategoryFilter = category;
  const categories = ['all', 'git', 'deploy', 'general', 'tech', 'jira'];
  categories.forEach(c => {
    const btn = document.getElementById('noteFilter_' + c);
    if (!btn) return;
    if (c === category) {
      btn.className = 'notes-filter-pill is-active px-2.5 py-1 rounded-full font-medium transition cursor-pointer';
    } else {
      btn.className = 'notes-filter-pill px-2.5 py-1 rounded-full font-medium transition cursor-pointer';
    }
  });
  renderNotesList();
}
window.setNoteCategoryFilter = setNoteCategoryFilter;

/**
 * Chèn thẻ định dạng Markdown tại vị trí con trỏ
 */
function insertNoteMarkdown(prefix, suffix, placeholder) {
  const ta = document.getElementById('noteContentInput');
  if (!ta) return;

  const start = ta.selectionStart;
  const end = ta.selectionEnd;
  const val = ta.value;
  const selectedText = val.substring(start, end) || placeholder;

  const replacement = prefix + selectedText + suffix;
  ta.value = val.substring(0, start) + replacement + val.substring(end);
  ta.focus();
  ta.setSelectionRange(start + prefix.length, start + prefix.length + selectedText.length);

  onNoteContentInput(ta.value);
}
window.insertNoteMarkdown = insertNoteMarkdown;
