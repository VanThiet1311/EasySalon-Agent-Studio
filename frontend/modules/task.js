let currentTaskActionType = 'task';

function setTaskActionType(type) {
  currentTaskActionType = type;
  const select = document.getElementById('taskTypeSelect');
  if (select && select.value !== type) {
    select.value = type;
  }
  const logContainer = document.getElementById('taskLogContainer');
  const promptLabel = document.getElementById('taskPromptLabel');
  const promptInput = document.getElementById('taskPromptInput');
  const btnStartText = document.getElementById('btnStartTaskText');
  const targetLabel = document.getElementById('taskTargetLabel');

  if (type === 'fixbug') {
    if (logContainer) logContainer.classList.remove('hidden');
    if (targetLabel) targetLabel.textContent = 'Phạm vi sửa lỗi:';
    if (promptLabel) promptLabel.textContent = 'Mô tả lỗi / Hiện tượng:';
    if (promptInput && !promptInput.value.trim()) {
      promptInput.placeholder = 'Ví dụ: Bấm nút lưu đổi giường nhưng báo lỗi 400 Bad Request...';
    }
    if (btnStartText) btnStartText.textContent = 'Bắt đầu sửa lỗi này';
  } else if (type === 'refactor') {
    if (logContainer) logContainer.classList.add('hidden');
    if (targetLabel) targetLabel.textContent = 'Phạm vi Refactor:';
    if (promptLabel) promptLabel.textContent = 'Yêu cầu / Mô tả Refactor:';
    if (promptInput && !promptInput.value.trim()) {
      promptInput.placeholder = 'Ví dụ: Tối ưu lại luồng state quản lý giỏ hàng, tách component con và clean code...';
    }
    if (btnStartText) btnStartText.textContent = 'Bắt đầu Refactor code';
  } else {
    if (logContainer) logContainer.classList.add('hidden');
    if (targetLabel) targetLabel.textContent = 'Nơi thực hiện:';
    if (promptLabel) promptLabel.textContent = 'Yêu cầu / Mô tả chi tiết:';
    if (promptInput && !promptInput.value.trim()) {
      promptInput.placeholder = 'Ví dụ: Thêm API và Component hiển thị trạng thái giường cho BedRoomPosition...';
    }
    if (btnStartText) btnStartText.textContent = 'Bắt đầu tác vụ này';
  }

  if (typeof parallelTasks !== 'undefined' && Array.isArray(parallelTasks)) {
    const cur = parallelTasks.find(t => t.id === activeTaskId);
    if (cur) {
      cur.type = type;
      if (!cur.isCustomName) {
        const idx = parallelTasks.findIndex(t => t.id === cur.id) + 1;
        const typeLabel = type === 'fixbug' ? 'Fix bug' : (type === 'refactor' ? 'Refactor code' : 'Tính năng mới');
        cur.name = `Task ${idx}: ${typeLabel}`;
      }
      if (typeof renderParallelTaskTabs === 'function') renderParallelTaskTabs();
      if (typeof renderFeedFilterTabs === 'function') renderFeedFilterTabs();
      if (typeof updateTaskActionButtons === 'function') updateTaskActionButtons();
    }
  }

  updateFixBugPromptPreview();
  saveDraft(false);
  scheduleQueueSync();
}

const EDIT_ICON_SVG = `<svg class="w-3.5 h-3.5 fill-none stroke-current" viewBox="0 0 24 24" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7"/><path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z"/></svg>`;

function parseTaskName(rawName, fallbackIdx) {
  const str = (rawName || '').trim();
  const match = str.match(/^Task\s*(\d+)[:\s\-]\s*(.*)$/i);
  if (match) {
    return {
      prefix: `Task ${match[1]}:`,
      subName: match[2].trim() || 'Tính năng mới'
    };
  }
  return {
    prefix: `Task ${fallbackIdx}:`,
    subName: str || 'Tính năng mới'
  };
}

let editingTaskId = null;
let isStartingEdit = false;

function startInlineEditTask(taskId, e) {
  if (e) {
    e.stopPropagation();
    e.preventDefault();
  }
  editingTaskId = taskId;
  isStartingEdit = true;
  renderParallelTaskTabs();
  setTimeout(() => {
    const input = document.getElementById(`inlineTaskInput_${taskId}`);
    if (input) {
      input.focus();
      input.select();
    }
    setTimeout(() => {
      isStartingEdit = false;
    }, 200);
  }, 50);
}

function handleInlineTaskKey(e, taskId, inputEl) {
  if (e.key === 'Enter') {
    e.preventDefault();
    saveInlineTaskName(taskId, inputEl.value);
  } else if (e.key === 'Escape') {
    e.preventDefault();
    editingTaskId = null;
    if (!editingTaskId) {
      renderParallelTaskTabs();
    }
  }
}

function saveInlineTaskName(taskId, newSubName) {
  if (isStartingEdit) return;
  if (editingTaskId !== taskId && editingTaskId !== null) return;
  const task = parallelTasks.find(t => t.id === taskId);
  if (!task) {
    editingTaskId = null;
    return;
  }
  const idx = parallelTasks.findIndex(t => t.id === taskId) + 1;
  const { prefix, subName: oldSubName } = parseTaskName(task.name, idx);
  let cleaned = (newSubName || '').trim();
  cleaned = cleaned.replace(/^Task\s*\d+[:\s\-]\s*/i, '').trim();
  const fallback = task.type === 'fixbug' ? 'Fix bug' : 'Tính năng mới';
  const finalSub = cleaned || fallback;

  editingTaskId = null;

  if (finalSub === oldSubName) {
    if (!editingTaskId) {
      renderParallelTaskTabs();
    }
    return;
  }

  task.name = `${prefix} ${finalSub}`;
  task.isCustomName = true;

  renderParallelTaskTabs();
  renderFeedFilterTabs();
  saveDraft(false);
  scheduleQueueSync();
  pollStatus();
  showToast(`Đã đổi tên tác vụ thành: ${task.name}`, 'success');
}

function promptRenameTask(taskId) {
  startInlineEditTask(taskId);
}

function extractImagesFromText(text) {
  if (!text) return [];
  const list = [];
  const seen = new Set();

  // 1. Markdown link ảnh: [filename.png](/api/jira/attachment?id=...&name=...) hoặc [alt](url)
  const mdPattern = /\[([^\]]*?\.(?:png|jpg|jpeg|gif|webp|svg))\]\(([^)]+)\)/gi;
  let m;
  while ((m = mdPattern.exec(text)) !== null) {
    const name = m[1].trim();
    const url = m[2].trim();
    if (!seen.has(url)) {
      seen.add(url);
      list.push({ url, name });
    }
  }

  // 2. Đường dẫn /api/jira/attachment?id=...
  const jiraAttPattern = /(?:https?:\/\/[^\s"'<>\)]+)?(\/api\/jira\/attachment\?[^\s"'<>\)]+)/gi;
  while ((m = jiraAttPattern.exec(text)) !== null) {
    const url = m[1];
    if (!seen.has(url)) {
      seen.add(url);
      let fn = 'image.png';
      try {
        const u = new URL(url, window.location.origin);
        fn = u.searchParams.get('name') || 'image.png';
      } catch (e) { }
      list.push({ url, name: fn });
    }
  }

  // 3. URL ảnh trực tiếp http(s)://...png|jpg...
  const rawUrlPattern = /(https?:\/\/[^\s"'<>\)]+\.(?:png|jpg|jpeg|gif|webp|svg)(?:\?[^\s"'<>\)]*)?)/gi;
  while ((m = rawUrlPattern.exec(text)) !== null) {
    const url = m[1];
    if (!seen.has(url)) {
      seen.add(url);
      const fn = url.split('/').pop().split('?')[0] || 'image.png';
      list.push({ url, name: decodeURIComponent(fn) });
    }
  }

  return list;
}
window.extractImagesFromText = extractImagesFromText;

async function uploadScreenshotFile(file) {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = async () => {
      try {
        const base64Data = reader.result;
        const res = await fetch('/api/upload-image', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            image: base64Data,
            filename: file.name || `screenshot_${Date.now()}.png`
          })
        });
        const data = await res.json();
        if (data.success) {
          resolve(data);
        } else {
          reject(new Error(data.message || 'Tải ảnh thất bại'));
        }
      } catch (err) {
        reject(err);
      }
    };
    reader.onerror = () => reject(new Error('Đọc file ảnh thất bại'));
    reader.readAsDataURL(file);
  });
}
window.uploadScreenshotFile = uploadScreenshotFile;

function removeTaskPromptImage(idx) {
  const cur = parallelTasks.find(t => t.id === activeTaskId);
  if (cur && cur.images && cur.images[idx]) {
    cur.images.splice(idx, 1);
    renderTaskPromptImages(cur.images);
    syncFormToCurrentTask();
    saveDraft(false);
  }
}
window.removeTaskPromptImage = removeTaskPromptImage;

function handleTaskPromptPaste(event) {
  const items = (event.clipboardData || event.originalEvent?.clipboardData)?.items;
  if (!items) return;
  for (let i = 0; i < items.length; i++) {
    const item = items[i];
    if (item.type && item.type.indexOf('image') !== -1) {
      event.preventDefault();
      const blob = item.getAsFile();
      if (!blob) continue;
      showToast('Đang tải ảnh chụp màn hình lên...', 'info');
      uploadScreenshotFile(blob).then(uploaded => {
        const cur = parallelTasks.find(t => t.id === activeTaskId);
        if (cur) {
          if (!cur.images) cur.images = [];
          cur.images.push(uploaded);
          renderTaskPromptImages(cur.images);
          syncFormToCurrentTask();
          saveDraft(false);
        }
        showToast('Đã đính kèm ảnh chụp màn hình vào tác vụ', 'success');
      }).catch(err => {
        showToast('Lỗi khi tải ảnh: ' + err.message, 'error');
      });
      break;
    }
  }
}
window.handleTaskPromptPaste = handleTaskPromptPaste;

async function onTaskPromptImageSelect(e) {
  const file = e.target.files && e.target.files[0];
  if (!file) return;
  try {
    showToast('Đang tải ảnh đính kèm lên...', 'info');
    const uploaded = await uploadScreenshotFile(file);
    const cur = parallelTasks.find(t => t.id === activeTaskId);
    if (cur) {
      if (!cur.images) cur.images = [];
      cur.images.push(uploaded);
      renderTaskPromptImages(cur.images);
      syncFormToCurrentTask();
      saveDraft(false);
    }
    showToast('Đã đính kèm ảnh thành công', 'success');
  } catch (err) {
    showToast('Lỗi tải ảnh: ' + err.message, 'error');
  } finally {
    e.target.value = '';
  }
}
window.onTaskPromptImageSelect = onTaskPromptImageSelect;

function renderTaskPromptImages(images) {
  const container = document.getElementById('taskPromptImagesContainer');
  const countEl = document.getElementById('taskPromptImagesCount');
  const listEl = document.getElementById('taskPromptImagesList');
  if (!container || !listEl) return;

  const cur = parallelTasks.find(t => t.id === activeTaskId);
  if (images === undefined && cur) {
    images = cur.images || [];
  }
  if (!Array.isArray(images)) images = [];

  if (cur) {
    cur.images = images;
  }

  if (images.length === 0) {
    container.classList.add('hidden');
    listEl.innerHTML = '';
    if (countEl) countEl.textContent = '0';
    return;
  }

  container.classList.remove('hidden');
  if (countEl) countEl.textContent = String(images.length);

  listEl.innerHTML = images.map((img, idx) => {
    const safeUrl = escapeHtml(img.url);
    const safeName = escapeHtml(img.name || img.filename || 'Ảnh minh chứng');
    return `
      <div class="group relative rounded-md border border-[#244170] bg-[#101e38] overflow-hidden hover:border-[#1677ff] transition shadow cursor-pointer max-w-[200px]"
           onclick="openImagePreviewModal('${safeUrl}', '${safeName}')"
           title="Bấm để phóng to ảnh: ${safeName}">
        <div class="h-28 w-44 bg-black/60 flex items-center justify-center overflow-hidden p-1">
          <img src="${safeUrl}" alt="${safeName}" class="max-h-full max-w-full object-contain group-hover:scale-105 transition duration-200" loading="lazy" />
        </div>
        <div class="p-1.5 bg-[#0c1628] border-t border-[#244170]/60 flex items-center justify-between gap-1">
          <span class="text-[10px] font-mono text-slate-300 truncate" title="${safeName}">${safeName}</span>
          <div class="flex items-center gap-1 shrink-0">
            <span class="text-[9px] text-blue-400 font-medium group-hover:underline">Phóng to</span>
            <button type="button" onclick="event.stopPropagation(); removeTaskPromptImage(${idx})"
                    class="p-0.5 text-slate-400 hover:text-rose-400 transition" title="Xóa ảnh này">
              <svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" d="M6 18L18 6M6 6l12 12" />
              </svg>
            </button>
          </div>
        </div>
      </div>
    `;
  }).join('');
}
window.renderTaskPromptImages = renderTaskPromptImages;

function onTaskPromptInput() {
  const promptVal = document.getElementById('taskPromptInput')?.value || '';
  const extracted = extractImagesFromText(promptVal);
  const cur = parallelTasks.find(t => t.id === activeTaskId);
  const existing = (cur && cur.images) || [];
  const merged = [...existing];
  extracted.forEach(img => {
    if (!merged.some(m => m.url === img.url || m.name === img.name)) {
      merged.push(img);
    }
  });
  renderTaskPromptImages(merged);

  updateFixBugPromptPreview();
  syncFormToCurrentTask();
  saveDraft(false);
  scheduleQueueSync();
}

function onTaskLogInput() {
  updateFixBugPromptPreview();
  syncFormToCurrentTask();
  saveDraft(false);
  scheduleQueueSync();
}

let parallelTasks = [
  {
    id: 'task_1',
    name: 'Task 1: Tính năng mới',
    type: 'task',
    target: 'both',
    skills: [],
    prompt: '',
    error_log: '',
    status: 'idle',
    sessionId: null
  }
];
let activeTaskId = 'task_1';
let activeFeedFilter = 'all';
let _queueSyncTimer = null;
let _initialQueueRestored = false;

function scheduleQueueSync() {
  clearTimeout(_queueSyncTimer);
  _queueSyncTimer = setTimeout(() => {
    syncQueueToServer();
  }, 400);
}

async function syncQueueToServer() {
  try {
    syncFormToCurrentTask();
    const payload = parallelTasks.map(t => ({
      id: t.id,
      title: t.name,
      name: t.name,
      mode: t.type,
      type: t.type,
      target: t.target || 'both',
      scope: t.target || 'both',
      skills: t.skills || [],
      prompt: t.prompt || '',
      error_log: t.error_log || '',
      fix_desc: t.prompt || '',
      fix_err: t.error_log || '',
      status: t.status || 'idle'
    }));
    await fetch('/api/queue/sync', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ queue: payload })
    });
  } catch (e) { }
}

function syncFormToCurrentTask() {
  const cur = parallelTasks.find(t => t.id === activeTaskId);
  if (!cur) return;
  cur.type = currentTaskActionType;
  cur.target = document.getElementById('taskTargetSelect')?.value || 'both';
  cur.skills = [...selectedTaskSkills];
  cur.prompt = (document.getElementById('taskPromptInput')?.value || '').trim();
  cur.error_log = (document.getElementById('taskLogInput')?.value || '').trim();
  const effortSelect = document.getElementById('taskEffortSelect');
  if (effortSelect) cur.effort = effortSelect.value;
}

function loadTaskToForm(taskId) {
  const task = parallelTasks.find(t => t.id === taskId);
  if (!task) return;
  setTaskActionType(task.type || 'task');
  const targetSelect = document.getElementById('taskTargetSelect');
  if (targetSelect) {
    targetSelect.value = task.target || 'both';
  }
  const effortSelect = document.getElementById('taskEffortSelect');
  if (effortSelect) {
    effortSelect.value = task.effort || currentStudioSettings.effort || 'high';
  }
  selectedTaskSkills = Array.isArray(task.skills) ? [...task.skills] : [];
  renderSkillPicker('task');

  const promptInput = document.getElementById('taskPromptInput');
  if (promptInput) promptInput.value = task.prompt || '';
  const logInput = document.getElementById('taskLogInput');
  if (logInput) logInput.value = task.error_log || '';
  renderTaskPromptImages(task.images || []);
  updateFixBugPromptPreview();
}

function selectParallelTask(taskId) {
  syncFormToCurrentTask();
  activeTaskId = taskId;
  activeFeedFilter = taskId;
  loadTaskToForm(taskId);
  renderParallelTaskTabs();
  renderFeedFilterTabs();
  updateTaskActionButtons();
  pollStatus();
}

function addNewParallelTask() {
  syncFormToCurrentTask();
  const nextNum = parallelTasks.length + 1;
  const newType = 'task';
  const newId = 'task_' + Date.now();
  const defaultName = `Task ${nextNum}: Tính năng mới`;
  const newTask = {
    id: newId,
    name: defaultName,
    isCustomName: false,
    type: newType,
    target: 'both',
    skills: [],
    prompt: '',
    error_log: '',
    status: 'idle',
    sessionId: null
  };
  parallelTasks.push(newTask);
  activeTaskId = newId;
  activeFeedFilter = newId;
  loadTaskToForm(newId);
  renderParallelTaskTabs();
  renderFeedFilterTabs();
  updateTaskActionButtons();
  syncQueueToServer();
  pollStatus();

  setTimeout(() => {
    const container = document.getElementById('parallelTaskTabs');
    if (container) {
      container.scrollTo({ left: container.scrollWidth, behavior: 'smooth' });
    }
  }, 60);

  showToast(`Đã thêm ${newTask.name}`, 'info');
}

async function removeParallelTask(taskId, e) {
  if (e) e.stopPropagation();

  let cleanId = taskId;
  let idx = parallelTasks.findIndex(t => t.id === cleanId || t.id === ('queued_' + cleanId) || String(t.id).replace(/^queued_/, '') === String(cleanId).replace(/^queued_/, ''));
  if (idx !== -1) {
    cleanId = parallelTasks[idx].id;
  }

  const t = idx !== -1 ? parallelTasks[idx] : null;
  const taskName = t ? t.name : (cleanId || 'Tác vụ');
  const isRunningOrQueued = t ? (t.status === 'running' || t.status === 'queued') : false;

  const conf = await antdConfirm({
    title: 'Xác nhận xóa tác vụ?',
    content: isRunningOrQueued
      ? `Tác vụ [${taskName}] đang chạy hoặc đang chờ. Bạn có chắc chắn muốn dừng và xóa tác vụ này? Tiến trình đang chạy sẽ bị dừng lại ngay lập tức.`
      : `Bạn có chắc chắn muốn xóa [${taskName}] khỏi danh sách và diễn biến thực thi?`,
    danger: true,
    okText: 'Xác nhận xóa',
    cancelText: 'Hủy'
  });
  if (!conf) return;

  try {
    await fetch('/api/stop', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ task_id: cleanId })
    });
  } catch (err) { }

  try {
    await fetch('/api/queue/remove', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ task_id: cleanId })
    });
  } catch (err) { }

  if (taskId && taskId !== cleanId) {
    try {
      await fetch('/api/queue/remove', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ task_id: taskId })
      });
    } catch (err) { }
  }

  const cleanBare = String(cleanId).replace(/^queued_/, '');
  [taskId, cleanId, cleanBare, 'queued_' + cleanBare].forEach(id => {
    if (id) {
      const el = document.getElementById('sessWrap_' + id);
      if (el) el.remove();
    }
  });

  if (idx !== -1) {
    if (parallelTasks.length <= 1) {
      parallelTasks = [{
        id: 'task_' + Date.now(),
        name: 'Task 1: Tính năng mới',
        type: 'task',
        target: 'both',
        skills: [],
        prompt: '',
        error_log: '',
        status: 'idle',
        sessionId: null
      }];
      activeTaskId = parallelTasks[0].id;
      loadTaskToForm(activeTaskId);
    } else {
      parallelTasks.splice(idx, 1);
      if (activeTaskId === cleanId || activeTaskId === taskId || activeTaskId === cleanBare || activeTaskId === ('queued_' + cleanBare)) {
        activeTaskId = parallelTasks[Math.max(0, idx - 1)].id;
        loadTaskToForm(activeTaskId);
      }
    }
  }

  if (activeFeedFilter === cleanId || activeFeedFilter === taskId || activeFeedFilter === cleanBare) {
    activeFeedFilter = 'all';
  }

  renderParallelTaskTabs();
  renderFeedFilterTabs();
  updateTaskActionButtons();
  await syncQueueToServer();
  if (typeof pollStatus === 'function') {
    pollStatus();
  }
  pollStatus();
  showToast(`Đã xóa ${taskName}`);
}

async function clearCompletedTasks() {
  const completedTasks = parallelTasks.filter(t => t.status === 'completed' || t.status === 'done' || t.status === 'stopped');
  if (completedTasks.length === 0) {
    showToast('Không có tác vụ đã xử lý nào để xóa.', 'info');
    return;
  }

  const conf = await antdConfirm({
    title: 'Xóa các tác vụ đã xử lý?',
    content: `Bạn có chắc muốn xóa ${completedTasks.length} tác vụ đã hoàn tất / đã dừng khỏi danh sách?`,
    danger: true,
    okText: 'Xóa tác vụ'
  });
  if (!conf) return;

  try {
    await fetch('/api/queue/remove', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ task_id: 'completed' })
    });
  } catch (e) { }

  completedTasks.forEach(t => {
    const cleanBare = String(t.id).replace(/^queued_/, '');
    [t.id, cleanBare, 'queued_' + cleanBare].forEach(id => {
      const wrapEl = document.getElementById('sessWrap_' + id);
      if (wrapEl) wrapEl.remove();
    });
  });

  parallelTasks = parallelTasks.filter(t => t.status !== 'completed' && t.status !== 'done' && t.status !== 'stopped');

  if (parallelTasks.length === 0) {
    parallelTasks = [{
      id: 'task_' + Date.now(),
      name: 'Task 1: Tính năng mới',
      type: 'task',
      target: 'both',
      skills: [],
      prompt: '',
      error_log: '',
      status: 'idle',
      sessionId: null
    }];
  }

  if (!parallelTasks.some(t => t.id === activeTaskId)) {
    activeTaskId = parallelTasks[0].id;
    loadTaskToForm(activeTaskId);
  }

  if (activeFeedFilter !== 'all' && !parallelTasks.some(t => t.id === activeFeedFilter)) {
    activeFeedFilter = 'all';
  }

  renderParallelTaskTabs();
  renderFeedFilterTabs();
  updateTaskActionButtons();
  await syncQueueToServer();
  pollStatus();
  showToast(`Đã xóa ${completedTasks.length} tác vụ đã xử lý xong.`);
}

function renderParallelTaskTabs() {
  const container = document.getElementById('parallelTaskTabs');
  if (!container) return;

  container.innerHTML = parallelTasks.map((t, idx) => {
    const isActive = t.id === activeTaskId;
    const isEditing = editingTaskId === t.id;
    const { prefix, subName } = parseTaskName(t.name, idx + 1);

    let statusDot = '';
    if (t.status === 'running') {
      statusDot = '<span class="w-1.5 h-1.5 rounded-full bg-cyan-300 animate-ping shrink-0" title="Đang chạy"></span>';
    } else if (t.status === 'queued') {
      statusDot = '<span class="px-1 py-0.2 rounded bg-amber-500/20 text-amber-300 border border-amber-500/40 text-[9px] font-mono shrink-0" title="Đang chờ trong hàng đợi">Chờ</span>';
    } else if (t.status === 'completed' || t.status === 'done') {
      statusDot = '<span class="text-emerald-400 text-[10px] font-bold shrink-0" title="Đã hoàn tất">✓</span>';
    }

    if (isEditing) {
      return `
        <div class="task-tab-editing shrink-0 flex items-center gap-1.5 px-2.5 py-1 rounded-md border text-xs font-medium select-none bg-[#101e38] border-[#38bdf8] shadow-sm">
          ${statusDot}
          <span class="text-cyan-300 font-bold shrink-0">${escapeHtml(prefix)}</span>
          <input id="inlineTaskInput_${t.id}" type="text" value="${escapeHtml(subName)}"
            class="bg-[#08101e] text-white text-xs px-1.5 py-0.5 rounded border border-[#199cff] focus:outline-none focus:ring-1 focus:ring-cyan-300 w-28 md:w-36 font-normal shadow-inner"
            onclick="event.stopPropagation()"
            onkeydown="handleInlineTaskKey(event, '${t.id}', this)"
            onblur="if (!isStartingEdit) saveInlineTaskName('${t.id}', this.value)" />
          <button type="button" onclick="saveInlineTaskName('${t.id}', document.getElementById('inlineTaskInput_${t.id}').value)"
            class="text-emerald-400 hover:text-emerald-300 p-0.5 text-xs font-bold transition cursor-pointer" title="Lưu tên">✓</button>
        </div>
      `;
    }

    return `
      <div onclick="selectParallelTask('${t.id}')" ondblclick="startInlineEditTask('${t.id}', event)"
        title="Bấm để chọn, nhấp icon cây bút để đổi tên"
        class="shrink-0 flex items-center gap-1.5 px-3 py-1.5 rounded-md cursor-pointer border text-xs font-medium transition select-none ${isActive
        ? 'active-task-tab bg-[rgb(25,156,255)] border-[rgb(25,156,255)] text-white shadow-sm font-bold'
        : 'bg-[#0e192c] border-[#244170] text-slate-300 hover:text-white hover:border-[#199cff]/60'
      }">
        ${statusDot}
        <span class="max-w-[130px] truncate"><span class="opacity-80">${escapeHtml(prefix)}</span> ${escapeHtml(subName)}</span>
        <button type="button" onclick="startInlineEditTask('${t.id}', event)" title="Đổi tên tác vụ"
          class="shrink-0 p-1 opacity-80 hover:opacity-100 hover:bg-white/20 rounded transition cursor-pointer flex items-center justify-center">
          ${EDIT_ICON_SVG}
        </button>
        <button type="button" onclick="removeParallelTask('${t.id}', event)" title="Xóa tác vụ này"
          class="ml-0.5 opacity-80 hover:opacity-100 hover:text-rose-400 p-0.5 rounded leading-none text-xs font-bold transition hover:bg-rose-500/20">×</button>
      </div>
    `;
  }).join('');
}

function updateTaskActionButtons() {
  const cur = parallelTasks.find(t => t.id === activeTaskId);
  const btnStart = document.getElementById('btnStartTask');
  const btnStop = document.getElementById('btnStopTask');
  const btnStopAll = document.getElementById('btnStopAllParallel');
  const startText = document.getElementById('btnStartTaskText');

  const isCurrentActive = cur && (cur.status === 'running' || cur.status === 'queued');
  const activeCount = parallelTasks.filter(t => t.status === 'running' || t.status === 'queued').length;
  const anyRunning = parallelTasks.some(t => t.status === 'running');

  if (btnStart && btnStop) {
    if (isCurrentActive) {
      btnStart.classList.add('hidden');
      btnStop.classList.remove('hidden');
    } else {
      btnStart.classList.remove('hidden');
      btnStop.classList.add('hidden');
      if (startText) {
        if (anyRunning) {
          startText.textContent = 'Đưa vào hàng đợi (Queue)';
        } else if (cur && (cur.status === 'completed' || cur.status === 'done' || cur.status === 'stopped')) {
          startText.textContent = 'Tiếp tục task này trên AI Terminal';
        } else if (cur && cur.type === 'fixbug') {
          startText.textContent = 'Bắt đầu sửa lỗi này';
        } else if (cur && cur.type === 'refactor') {
          startText.textContent = 'Bắt đầu Refactor code';
        } else {
          startText.textContent = 'Bắt đầu tác vụ này';
        }
      }
    }
  }

  if (btnStopAll) {
    if (activeCount > 1) {
      btnStopAll.classList.remove('hidden');
    } else {
      btnStopAll.classList.add('hidden');
    }
  }
}

async function startSingleTaskById(taskId) {
  const task = parallelTasks.find(t => t.id === taskId);
  if (!task) return;
  if (taskId === activeTaskId) syncFormToCurrentTask();

  if (!task.prompt && !task.error_log) {
    await antdAlert({ title: 'Thiếu thông tin', content: `Tác vụ [${task.name}] chưa có nội dung yêu cầu hoặc mô tả lỗi!`, type: 'error' });
    return;
  }

  const anyRunning = parallelTasks.some(t => t.status === 'running' && t.id !== task.id);
  task.status = anyRunning ? 'queued' : 'running';
  renderParallelTaskTabs();
  updateTaskActionButtons();
  await syncQueueToServer();

  const mode = task.type || 'task';
  const slashSkills = (task.skills || []).map(s => s.startsWith('/') ? s : '/' + s).join(' ');
  const formattedPrompt = formatFullPromptWithAction(mode, slashSkills, task.prompt, task.error_log);

  try {
    if (task.type === 'fixbug') {
      const res = await fetch('/api/fixbug', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          task_id: task.id,
          title: task.name,
          mode: 'fixbug',
          engine: currentStudioSettings.engine || 'gemini_cli',
          effort: task.effort || currentStudioSettings.effort || 'high',
          skills: task.skills,
          skill: task.skills.join(', '),
          scope: task.target || 'both',
          description: task.prompt || formattedPrompt,
          original_prompt: task.original_prompt || task.prompt || '',
          error_log: task.error_log,
          images: task.images || []
        })
      });
      const d = await res.json();
      if (!d.success) {
        task.status = 'idle';
        await antdAlert({ title: 'Lỗi', content: d.message, type: 'error' });
      } else {
        task.status = d.queue_status === 'queued' ? 'queued' : 'running';
        showToast(d.message || `Đã đưa ${task.name} vào hàng đợi`, 'success');
      }
    } else {
      const res = await fetch('/api/task', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          task_id: task.id,
          title: task.name,
          mode: mode,
          engine: currentStudioSettings.engine || 'gemini_cli',
          effort: task.effort || currentStudioSettings.effort || 'high',
          prompt: task.prompt || formattedPrompt,
          original_prompt: task.original_prompt || task.prompt || '',
          error_log: task.error_log,
          target: task.target || 'both',
          starter: 'fe',
          rounds: 4,
          skills: task.skills,
          skill: task.skills.join(', '),
          images: task.images || []
        })
      });
      const d = await res.json();
      if (!d.success) {
        task.status = 'idle';
        await antdAlert({ title: 'Lỗi', content: d.message, type: 'error' });
      } else {
        task.status = d.queue_status === 'queued' ? 'queued' : 'running';
        showToast(d.message || `Đã đưa ${task.name} vào hàng đợi`, 'success');
      }
    }
  } catch (e) {
    task.status = 'idle';
    await antdAlert({ title: 'Lỗi kết nối', content: e.message, type: 'error' });
  }
  if (task.status === 'idle') {
    await syncQueueToServer();
  }
  renderParallelTaskTabs();
  updateTaskActionButtons();
  pollStatus();
}

function startCurrentTask() {
  return startSingleTaskById(activeTaskId);
}

function startUnifiedTask() {
  return startCurrentTask();
}

function startTask() {
  return startCurrentTask();
}

function startFixBug() {
  return startCurrentTask();
}

async function startAllParallelTasks() {
  syncFormToCurrentTask();
  const idleTasks = parallelTasks.filter(t => t.status !== 'running' && t.status !== 'queued');
  if (idleTasks.length === 0) {
    showToast('Tất cả tác vụ đều đã nằm trong hàng đợi hoặc đang chạy!', 'info');
    return;
  }
  for (const t of idleTasks) {
    if (!t.prompt && !t.error_log) {
      await antdAlert({ title: 'Thiếu thông tin', content: `[${t.name}] chưa có nội dung yêu cầu hoặc mô tả lỗi. Vui lòng nhập trước khi chạy!`, type: 'error' });
      return;
    }
  }
  showToast(`Đang xếp ${idleTasks.length} tác vụ vào hàng đợi thực thi tuần tự...`, 'info');
  for (const t of idleTasks) {
    await startSingleTaskById(t.id);
  }
}

async function stopCurrentTask() {
  const cur = parallelTasks.find(t => t.id === activeTaskId);
  const taskName = cur ? cur.name : 'tác vụ này';
  const confirmed = await antdConfirm({
    title: 'Dừng tác vụ',
    content: `Bạn có chắc muốn dừng <strong>${escapeHtml(taskName)}</strong>?`,
    danger: true,
    okText: 'Dừng ngay'
  });
  if (confirmed) {
    await fetch('/api/stop', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ task_id: activeTaskId })
    });
    if (cur) cur.status = 'stopped';
    if (!editingTaskId) {
      renderParallelTaskTabs();
    }
    updateTaskActionButtons();
    pollStatus();
  }
}

async function stopAllTasks() {
  const confirmed = await antdConfirm({
    title: 'Dừng toàn bộ hàng đợi',
    content: 'Bạn có chắc chắn muốn dừng toàn bộ các tác vụ đang chạy và đang chờ trong hàng đợi?',
    danger: true,
    okText: 'Dừng tất cả'
  });
  if (confirmed) {
    await fetch('/api/stop', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ task_id: 'all' })
    });
    parallelTasks.forEach(t => { if (t.status === 'running' || t.status === 'queued') t.status = 'stopped'; });
    if (!editingTaskId) {
      renderParallelTaskTabs();
    }
    updateTaskActionButtons();
    pollStatus();
  }
}

function stopProcess() {
  return stopCurrentTask();
}

function setTaskPrompt(text, skill, target) {
  setTaskActionType('task');
  const promptInput = document.getElementById('taskPromptInput');
  if (promptInput) promptInput.value = text;
  if (target) {
    const targetSelect = document.getElementById('taskTargetSelect');
    if (targetSelect) {
      targetSelect.value = target;
      onTaskTargetChange();
    }
  }
  if (skill) {
    const sClean = skill.startsWith('skill-') ? skill : 'skill-' + skill;
    selectedTaskSkills = [sClean];
    renderSkillPicker('task');
  }
  updateFixBugPromptPreview();
  syncFormToCurrentTask();
  scheduleQueueSync();
}

function setFixBugSample(desc, log, skill, scope) {
  setTaskActionType('fixbug');
  const promptInput = document.getElementById('taskPromptInput');
  if (promptInput) promptInput.value = desc;
  const logInput = document.getElementById('taskLogInput');
  if (logInput) logInput.value = log || '';
  if (scope) {
    const targetSelect = document.getElementById('taskTargetSelect');
    if (targetSelect) {
      targetSelect.value = scope;
      onTaskTargetChange();
    }
  }
  if (skill) {
    const sClean = skill.startsWith('skill-') ? skill : 'skill-' + skill;
    selectedTaskSkills = [sClean];
    renderSkillPicker('task');
  }
  updateFixBugPromptPreview();
  syncFormToCurrentTask();
  scheduleQueueSync();
}

function setFixBug(desc, log, skill, scope) {
  setFixBugSample(desc, log, skill, scope);
}

function getToolBadgeClass(toolName) {
  if (toolName === 'run_command') return 'bg-amber-500/20 text-amber-300 border border-amber-500/30';
  if (toolName === 'read_file' || toolName === 'view_file') return 'bg-sky-500/20 text-sky-300 border border-sky-500/30';
  if (toolName === 'edit_file' || toolName === 'replace_file_content' || toolName === 'write_to_file' || toolName === 'write_file') return 'bg-emerald-500/20 text-emerald-300 border border-emerald-500/30';
  if (toolName === 'grep_search' || toolName === 'find_by_name') return 'bg-purple-500/20 text-purple-300 border border-purple-500/30';
  return 'bg-slate-500/20 text-slate-300 border border-slate-500/30';
}

function toggleStepOutput(outId) {
  const el = document.getElementById(outId);
  if (el) {
    el.classList.toggle('hidden');
    const isHidden = el.classList.contains('hidden');
    const arrowEl = document.getElementById('arrow_' + outId);
    if (arrowEl) {
      arrowEl.classList.toggle('rotate-180', !isHidden);
    }
  }
}

function formatDiffColoredHtml(diffText) {
  if (!diffText) return '<div class="text-slate-500 italic p-2">Không có nội dung diff chi tiết.</div>';
  const lines = diffText.replace(/\r\n/g, '\n').split('\n');
  let oldLn = null;
  let newLn = null;
  const rows = [];

  for (let i = 0; i < lines.length; i++) {
    const line = lines[i];

    if (
      line.startsWith('diff --git ') ||
      line.startsWith('index ') ||
      line.startsWith('--- ') ||
      line.startsWith('+++ ') ||
      line.startsWith('new file mode ') ||
      line.startsWith('deleted file mode ')
    ) {
      continue;
    }

    if (line.startsWith('@@')) {
      const m = line.match(/@@\s*-(\d+)(?:,\d+)?\s*\+(\d+)(?:,\d+)?\s*@@/);
      if (m) {
        oldLn = parseInt(m[1], 10);
        newLn = parseInt(m[2], 10);
      }
      rows.push(`<div class="git-diff-hunk">${escapeHtml(line)}</div>`);
      continue;
    }

    if (line.startsWith('+')) {
      const code = escapeHtml(line.slice(1));
      const lnStr = newLn !== null ? newLn++ : '';
      rows.push(
        `<div class="git-diff-row git-diff-add">` +
        `<span class="git-diff-ln git-diff-ln-old"></span>` +
        `<span class="git-diff-ln git-diff-ln-new">${lnStr}</span>` +
        `<span class="git-diff-sign">+</span>` +
        `<span class="git-diff-code">${code || ' '}</span>` +
        `</div>`
      );
    } else if (line.startsWith('-')) {
      const code = escapeHtml(line.slice(1));
      const lnStr = oldLn !== null ? oldLn++ : '';
      rows.push(
        `<div class="git-diff-row git-diff-del">` +
        `<span class="git-diff-ln git-diff-ln-old">${lnStr}</span>` +
        `<span class="git-diff-ln git-diff-ln-new"></span>` +
        `<span class="git-diff-sign">-</span>` +
        `<span class="git-diff-code">${code || ' '}</span>` +
        `</div>`
      );
    } else if (line.startsWith('\\ No newline')) {
      continue;
    } else {
      const rawCode = line.startsWith(' ') ? line.slice(1) : line;
      const oStr = oldLn !== null ? oldLn++ : '';
      const nStr = newLn !== null ? newLn++ : '';
      rows.push(
        `<div class="git-diff-row git-diff-ctx">` +
        `<span class="git-diff-ln git-diff-ln-old">${oStr}</span>` +
        `<span class="git-diff-ln git-diff-ln-new">${nStr}</span>` +
        `<span class="git-diff-sign"> </span>` +
        `<span class="git-diff-code">${escapeHtml(rawCode) || ' '}</span>` +
        `</div>`
      );
    }
  }

  return `<div class="git-diff-container vscode-diff-editor">${rows.join('')}</div>`;
}
window.formatDiffColoredHtml = formatDiffColoredHtml;

function extractExitStatusAndClean(text) {
  let statusHtml = '';
  let remaining = (text || '').trim();

  const exitMatch = remaining.match(/^Command exited with code (\d+)\.?\s*/i);
  if (exitMatch) {
    const code = parseInt(exitMatch[1], 10);
    const isSuccess = (code === 0);
    statusHtml = `
      <div class="step-out-header flex items-center justify-between pb-1.5 mb-1.5 border-b border-slate-100 dark:border-slate-800 text-[11px] font-sans select-none">
        <div class="flex items-center gap-2">
          <span class="inline-flex items-center gap-1 px-1.5 py-0.5 rounded text-[10px] font-bold ${
            isSuccess
              ? 'bg-emerald-50 text-emerald-700 border border-emerald-200'
              : 'bg-rose-50 text-rose-700 border border-rose-200'
          }">
            ${isSuccess ? '✓ Hoàn thành (code 0)' : `✕ Thoát mã lỗi (code ${code})`}
          </span>
          <span class="text-slate-400 text-[10.5px]">Kết quả thực thi lệnh</span>
        </div>
      </div>
    `.trim();
    remaining = remaining.slice(exitMatch[0].length).trim();
  }

  if (remaining.startsWith('Command output:\n')) {
    remaining = remaining.slice('Command output:\n'.length).trim();
  } else if (remaining.startsWith('Command output:')) {
    remaining = remaining.slice('Command output:'.length).trim();
  }

  return { statusHtml, remaining };
}

function formatCommandOutputLines(lines) {
  const grepWithLineRegex = /^([^\s:]+\.[a-zA-Z0-9_-]+):(\d+):(.*)$/;
  const grepNoLineRegex = /^([^\s:]+\.[a-zA-Z0-9_-]+):(.*)$/;
  const gitStatusModRegex = /^(\s*)(modified|new file|deleted|renamed):\s+(.*)$/;
  const gitBranchRegex = /^On branch (.+)$/;

  const rows = [];
  let grepCount = 0;
  for (const l of lines) {
    const cleanL = l.replace(/\r/g, '').trim();
    if (grepWithLineRegex.test(cleanL) || (grepNoLineRegex.test(cleanL) && cleanL.includes('/'))) {
      grepCount++;
    }
  }

  if (grepCount > 0) {
    rows.push(`<div class="text-[10.5px] font-sans font-medium text-slate-400 dark:text-slate-500 mb-1 flex items-center justify-between select-none"><span>Kết quả tìm kiếm (${grepCount} vị trí):</span></div>`);
  }

  for (const rawLine of lines) {
    const line = rawLine.replace(/\r/g, '');
    if (!line.trim()) {
      rows.push('<div class="h-1"></div>');
      continue;
    }

    const grepM = line.trim().match(grepWithLineRegex);
    if (grepM) {
      const file = grepM[1];
      const lineNum = grepM[2];
      const code = (grepM[3] || '').trim();
      rows.push(`
        <div class="step-grep-row flex items-baseline gap-2 py-1 px-1.5 rounded hover:bg-[#f0f7ff] dark:hover:bg-slate-800/60 border-b border-slate-100 dark:border-slate-800/40 last:border-0 font-mono text-[11px] leading-relaxed transition select-text">
          <div class="shrink-0 flex items-center gap-1.5 select-all">
            <span class="step-grep-file font-semibold text-[#1677ff] dark:text-sky-400 hover:underline cursor-pointer" title="${escapeHtml(file)}" onclick="openFileEditor('${escapeHtml(file)}')">${escapeHtml(file)}</span>
            <span class="step-grep-line font-bold text-[10px] px-1.5 py-0.5 rounded bg-amber-50 dark:bg-amber-950/40 text-amber-700 dark:text-amber-400 border border-amber-200 dark:border-amber-800 shrink-0" title="Dòng ${lineNum}">:${lineNum}:</span>
          </div>
          <div class="step-grep-code text-slate-800 dark:text-slate-200 min-w-0 flex-1 whitespace-pre-wrap break-all">
            ${escapeHtml(code)}
          </div>
        </div>
      `.trim());
      continue;
    }

    const grepNoLineM = line.trim().match(grepNoLineRegex);
    if (grepNoLineM && (grepNoLineM[1].includes('/') || grepCount > 0)) {
      const file = grepNoLineM[1];
      const code = (grepNoLineM[2] || '').trim();
      rows.push(`
        <div class="step-grep-row flex items-baseline gap-2 py-1 px-1.5 rounded hover:bg-[#f0f7ff] dark:hover:bg-slate-800/60 border-b border-slate-100 dark:border-slate-800/40 last:border-0 font-mono text-[11px] leading-relaxed transition select-text">
          <div class="shrink-0 flex items-center gap-1.5 select-all">
            <span class="step-grep-file font-semibold text-[#1677ff] dark:text-sky-400 hover:underline cursor-pointer" title="${escapeHtml(file)}" onclick="openFileEditor('${escapeHtml(file)}')">${escapeHtml(file)}</span>
          </div>
          <div class="step-grep-code text-slate-800 dark:text-slate-200 min-w-0 flex-1 whitespace-pre-wrap break-all">
            ${escapeHtml(code)}
          </div>
        </div>
      `.trim());
      continue;
    }

    const modM = line.match(gitStatusModRegex);
    if (modM) {
      const type = modM[2];
      const path = modM[3];
      const colorClass = type === 'modified' ? 'text-amber-600' : (type === 'new file' ? 'text-emerald-600' : 'text-rose-600');
      rows.push(`
        <div class="px-1.5 py-1 font-mono text-[11px] whitespace-pre overflow-x-auto flex items-center gap-2 hover:bg-slate-50 dark:hover:bg-slate-800/40 rounded transition">
          <span class="${colorClass} font-semibold font-mono w-20 shrink-0 select-none">${escapeHtml(type)}:</span>
          <span class="text-blue-600 dark:text-sky-400 font-medium select-all">${escapeHtml(path)}</span>
        </div>
      `.trim());
      continue;
    }

    const branchM = line.match(gitBranchRegex);
    if (branchM) {
      rows.push(`
        <div class="px-1.5 py-0.5 font-mono text-[11px] whitespace-pre overflow-x-auto text-slate-500">
          Nhánh: <span class="text-[#1677ff] font-bold select-all">${escapeHtml(branchM[1])}</span>
        </div>
      `.trim());
      continue;
    }

    if (/^(WARNING|Warning):/.test(line.trim())) {
      rows.push(`<div class="px-1.5 py-0.5 font-mono text-[11px] text-amber-600 whitespace-pre overflow-x-auto leading-relaxed">${escapeHtml(line)}</div>`);
      continue;
    }
    if (/^(ERROR|Error):/.test(line.trim())) {
      rows.push(`<div class="px-1.5 py-0.5 font-mono text-[11px] text-rose-600 whitespace-pre overflow-x-auto leading-relaxed">${escapeHtml(line)}</div>`);
      continue;
    }

    rows.push(`<div class="px-1.5 py-0.5 font-mono text-[11px] text-slate-700 dark:text-slate-300 whitespace-pre overflow-x-auto leading-relaxed select-text">${escapeHtml(line)}</div>`);
  }

  return rows.join('\n');
}

function formatStepOutputWithDiff(outputText) {
  if (!outputText) return '';
  const normalized = String(outputText).replace(/\r\n/g, '\n').replace(/\r/g, '\n');

  const diffIdx = normalized.indexOf('diff --git ');
  if (diffIdx !== -1) {
    const beforeDiff = normalized.slice(0, diffIdx).trim();
    const diffPart = normalized.slice(diffIdx);
    const { statusHtml, remaining } = extractExitStatusAndClean(beforeDiff);
    const remainingLines = remaining ? remaining.split('\n') : [];
    return `
      ${statusHtml}
      ${remainingLines.length > 0 ? `<div class="mb-2">${formatCommandOutputLines(remainingLines)}</div>` : ''}
      ${formatDiffColoredHtml(diffPart)}
    `.trim();
  }

  if (normalized.includes('\n@@ -') || normalized.startsWith('@@ -')) {
    return formatDiffColoredHtml(normalized);
  }

  const { statusHtml, remaining } = extractExitStatusAndClean(normalized);
  if (!remaining.trim() || remaining.trim() === 'No output from the command.') {
    return `
      ${statusHtml}
      <div class="text-slate-400 italic text-[11px] py-1 font-sans">Không có dữ liệu đầu ra từ câu lệnh.</div>
    `.trim();
  }

  const lines = remaining.trim().split('\n');
  return `
    ${statusHtml}
    <div class="step-out-lines flex flex-col gap-0.5 mt-1">
      ${formatCommandOutputLines(lines)}
    </div>
  `.trim();
}

let _collapsedTurnCards = new Set();
let _userInteractedTurnCards = new Map();
let _collapsedStepBoxes = new Set();
let _collapsedDiffBoxes = new Set();
const _continuationImages = {};

function renderContinuationImages(taskIdKey) {
  const container = document.getElementById('continueImagesContainer_' + taskIdKey);
  if (!container) return;
  const images = _continuationImages[taskIdKey] || [];
  if (images.length === 0) {
    container.classList.add('hidden');
    container.innerHTML = '';
    return;
  }
  container.classList.remove('hidden');
  container.innerHTML = images.map((img, idx) => {
    const safeUrl = escapeHtml(img.url);
    const safeName = escapeHtml(img.name || img.filename || 'Ảnh minh chứng');
    return `
      <div class="continue-image-item group relative rounded-md border border-[#244170] bg-[#101e38] overflow-hidden hover:border-[#1677ff] transition shadow cursor-pointer max-w-[180px]"
           onclick="openImagePreviewModal('${safeUrl}', '${safeName}')"
           title="Bấm để phóng to ảnh: ${safeName}">
        <div class="h-20 w-36 bg-black/60 flex items-center justify-center overflow-hidden p-1">
          <img src="${safeUrl}" alt="${safeName}" class="max-h-full max-w-full object-contain group-hover:scale-105 transition duration-200" loading="lazy" />
        </div>
        <div class="p-1.5 bg-[#0c1628] border-t border-[#244170]/60 flex items-center justify-between gap-1">
          <span class="continue-image-name text-[10px] font-mono text-slate-300 truncate" title="${safeName}">${safeName}</span>
          <button type="button" onclick="event.stopPropagation(); removeContinuationImage('${taskIdKey}', ${idx})"
                  class="p-0.5 text-slate-400 hover:text-rose-400 transition" title="Xóa ảnh này">
            <svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>
      </div>
    `;
  }).join('');
}
window.renderContinuationImages = renderContinuationImages;

function removeContinuationImage(taskIdKey, idx) {
  if (_continuationImages[taskIdKey] && _continuationImages[taskIdKey][idx]) {
    _continuationImages[taskIdKey].splice(idx, 1);
    renderContinuationImages(taskIdKey);
  }
}
window.removeContinuationImage = removeContinuationImage;

function handleContinuePaste(event, taskIdKey) {
  const items = (event.clipboardData || event.originalEvent?.clipboardData)?.items;
  if (!items) return;
  for (let i = 0; i < items.length; i++) {
    const item = items[i];
    if (item.type && item.type.indexOf('image') !== -1) {
      event.preventDefault();
      const blob = item.getAsFile();
      if (!blob) continue;
      showToast('Đang tải ảnh chụp màn hình lên...', 'info');
      uploadScreenshotFile(blob).then(uploaded => {
        if (!_continuationImages[taskIdKey]) {
          _continuationImages[taskIdKey] = [];
        }
        _continuationImages[taskIdKey].push(uploaded);
        renderContinuationImages(taskIdKey);
        showToast('Đã đính kèm ảnh chụp màn hình vào lượt tiếp theo', 'success');
      }).catch(err => {
        showToast('Lỗi khi tải ảnh: ' + err.message, 'error');
      });
      break;
    }
  }
}
window.handleContinuePaste = handleContinuePaste;

async function onContinueFileSelect(e, taskIdKey) {
  const file = e.target.files && e.target.files[0];
  if (!file) return;
  try {
    showToast('Đang tải ảnh đính kèm lên...', 'info');
    const uploaded = await uploadScreenshotFile(file);
    if (!_continuationImages[taskIdKey]) {
      _continuationImages[taskIdKey] = [];
    }
    _continuationImages[taskIdKey].push(uploaded);
    renderContinuationImages(taskIdKey);
    showToast('Đã đính kèm ảnh thành công', 'success');
  } catch (err) {
    showToast('Lỗi tải ảnh: ' + err.message, 'error');
  } finally {
    e.target.value = '';
  }
}
window.onContinueFileSelect = onContinueFileSelect;

function toggleTurnCollapse(cardId, event) {
  if (event) {
    event.stopPropagation();
  }
  const card = document.getElementById(cardId);
  const bodyEl = document.getElementById('turnBody_' + cardId);
  const chevronEl = document.getElementById('turnChevron_' + cardId);
  const badgeEl = document.getElementById('turnCollapsedBadge_' + cardId);

  if (!bodyEl) return;
  const isHidden = bodyEl.classList.contains('hidden');
  if (isHidden) {
    bodyEl.classList.remove('hidden');
    _collapsedTurnCards.delete(cardId);
    _userInteractedTurnCards.set(cardId, false);
    if (chevronEl) chevronEl.classList.remove('-rotate-90');
    if (badgeEl) badgeEl.classList.add('hidden');
  } else {
    bodyEl.classList.add('hidden');
    _collapsedTurnCards.add(cardId);
    _userInteractedTurnCards.set(cardId, true);
    if (chevronEl) chevronEl.classList.add('-rotate-90');
    if (badgeEl) badgeEl.classList.remove('hidden');
  }

  if (card && card.dataset.sig) {
    const parts = card.dataset.sig.split('_');
    if (parts.length >= 3) {
      parts[parts.length - 3] = String(_collapsedTurnCards.has(cardId));
      card.dataset.sig = parts.join('_');
    }
  }
}
window.toggleTurnCollapse = toggleTurnCollapse;

function toggleStepLogsCollapse(boxId, event) {
  if (event) {
    event.stopPropagation();
  }
  const bodyEl = document.getElementById('stepLogsBody_' + boxId);
  const arrowEl = document.getElementById('stepArrow_' + boxId);
  const headerEl = document.getElementById('stepHeader_' + boxId);

  if (!bodyEl) return;
  const isHidden = bodyEl.classList.contains('hidden');
  if (isHidden) {
    bodyEl.classList.remove('hidden');
    _collapsedStepBoxes.delete(boxId);
    if (arrowEl) arrowEl.classList.add('rotate-180');
    if (headerEl) {
      headerEl.classList.add('border-b');
    }
  } else {
    bodyEl.classList.add('hidden');
    _collapsedStepBoxes.add(boxId);
    if (arrowEl) arrowEl.classList.remove('rotate-180');
    if (headerEl) {
      headerEl.classList.remove('border-b');
    }
  }

  const cardId = 'turnCard_' + boxId.replace(/^stepBox_/, '');
  const card = document.getElementById(cardId);
  if (card && card.dataset.sig) {
    const parts = card.dataset.sig.split('_');
    if (parts.length >= 3) {
      parts[parts.length - 2] = String(_collapsedStepBoxes.has(boxId));
      card.dataset.sig = parts.join('_');
    }
  }
}
window.toggleStepLogsCollapse = toggleStepLogsCollapse;

function toggleDiffBoxCollapse(boxId, event) {
  if (event) {
    event.stopPropagation();
  }
  const bodyEl = document.getElementById('diffBoxBody_' + boxId);
  const arrowEl = document.getElementById('diffArrow_' + boxId);
  const headerEl = document.getElementById('diffHeader_' + boxId);

  if (!bodyEl) return;
  const isHidden = bodyEl.classList.contains('hidden');
  if (isHidden) {
    bodyEl.classList.remove('hidden');
    _collapsedDiffBoxes.delete(boxId);
    if (arrowEl) arrowEl.classList.add('rotate-180');
    if (headerEl) {
      headerEl.classList.add('border-b');
    }
  } else {
    bodyEl.classList.add('hidden');
    _collapsedDiffBoxes.add(boxId);
    if (arrowEl) arrowEl.classList.remove('rotate-180');
    if (headerEl) {
      headerEl.classList.remove('border-b');
    }
  }

  const cardId = 'turnCard_' + boxId.replace(/^diffBox_/, '');
  const card = document.getElementById(cardId);
  if (card && card.dataset.sig) {
    const parts = card.dataset.sig.split('_');
    if (parts.length >= 3) {
      parts[parts.length - 1] = String(_collapsedDiffBoxes.has(boxId));
      card.dataset.sig = parts.join('_');
    }
  }
}
window.toggleDiffBoxCollapse = toggleDiffBoxCollapse;

function renderChangedFilesHtml(changedFiles, sessId, turnIdx) {
  if (!changedFiles || changedFiles.length === 0) return '';

  // Sắp xếp: file do AI trực tiếp chỉnh sửa lên đầu, các file đã thay đổi trước đó ở sau
  const displayFiles = [...changedFiles].sort((a, b) => (b.touched_by_ai ? 1 : 0) - (a.touched_by_ai ? 1 : 0));
  if (displayFiles.length === 0) return '';

  const totalAdds = displayFiles.reduce((acc, f) => acc + (Number(f.additions) || 0), 0);
  const totalDels = displayFiles.reduce((acc, f) => acc + (Number(f.deletions) || 0), 0);
  const diffBoxId = `diffBox_${sessId}_${turnIdx}`;
  const isDiffCollapsed = _collapsedDiffBoxes.has(diffBoxId);

  return `
        <div class="changed-files-box mb-3 rounded-lg border border-[#333333] bg-[#181818] overflow-hidden shadow-sm">
          <div id="diffHeader_${diffBoxId}"
               onclick="toggleDiffBoxCollapse('${diffBoxId}', event)"
               class="changed-files-header px-3 py-2 bg-[#252526] ${isDiffCollapsed ? '' : 'border-b border-[#333333]'} flex items-center justify-between text-[11px] font-semibold text-slate-200 cursor-pointer select-none hover:bg-[#2d2d30] transition"
               title="${isDiffCollapsed ? 'Nhấp để hiển thị thay đổi mã nguồn' : 'Nhấp để thu gọn thay đổi mã nguồn'}">
            <div class="flex items-center gap-2">
              <svg class="w-3.5 h-3.5 text-emerald-400 shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"/>
              </svg>
              <span class="font-sans font-semibold">Thay đổi mã nguồn (${displayFiles.length} file)</span>
              <span class="git-stat-add px-1.5 py-0.5 rounded text-[10px] font-mono font-bold text-[#73c991] bg-[#73c991]/15">+${totalAdds}</span>
              <span class="git-stat-del px-1.5 py-0.5 rounded text-[10px] font-mono font-bold text-[#f14c4c] bg-[#f14c4c]/15">-${totalDels}</span>
            </div>
            <div class="flex items-center gap-2">
              <button type="button" onclick="toggleDiffBoxCollapse('${diffBoxId}', event)"
                class="p-1 rounded hover:bg-white/10 text-slate-400 hover:text-white transition flex items-center justify-center cursor-pointer"
                title="${isDiffCollapsed ? 'Nhấp để hiển thị thay đổi mã nguồn' : 'Nhấp để thu gọn thay đổi mã nguồn'}">
                <svg id="diffArrow_${diffBoxId}" class="w-3.5 h-3.5 fill-none stroke-current transition-transform duration-200 ${isDiffCollapsed ? '' : 'rotate-180'}" viewBox="0 0 24 24" stroke-width="2.5">
                  <path stroke-linecap="round" stroke-linejoin="round" d="M19 9l-7 7-7-7" />
                </svg>
              </button>
            </div>
          </div>
          <div id="diffBoxBody_${diffBoxId}" class="${isDiffCollapsed ? 'hidden' : ''} p-2.5 space-y-3 max-h-[500px] overflow-y-auto font-mono text-[11px]">
            ${displayFiles.map((f, fIdx) => {
    const diffId = `file_diff_${sessId}_${turnIdx}_${fIdx}`;
    const st = (f.status || 'M').toUpperCase();
    const isAdded = st.includes('A');
    const isDeleted = st.includes('D');
    const stBadgeClass = isAdded
      ? 'bg-emerald-500/15 text-[#73c991] border-emerald-500/40'
      : (isDeleted ? 'bg-rose-500/15 text-[#f14c4c] border-rose-500/40' : 'bg-amber-500/15 text-[#cca700] border-amber-500/40');
    const isPre = Boolean(f.is_preexisting || (!f.touched_by_ai && f.touched_by_ai !== undefined));
    const autoExpand = Boolean(f.touched_by_ai || (!isPre && fIdx < 3));

    const filePath = f.path || '';
    const lastSlash = filePath.lastIndexOf('/');
    const dirPart = lastSlash !== -1 ? filePath.slice(0, lastSlash + 1) : '';
    const filePart = lastSlash !== -1 ? filePath.slice(lastSlash + 1) : filePath;

    return `
                <div class="changed-file-card rounded-md border border-[#333333] bg-[#1e1e1e] overflow-hidden shadow-sm">
                  <div class="changed-file-header px-3 py-1.5 bg-[#252526] border-b border-[#333333] flex items-center justify-between gap-2 cursor-pointer select-none hover:bg-[#2d2d30] transition" onclick="toggleStepOutput('${diffId}')">
                    <div class="flex items-center gap-2 min-w-0 flex-1">
                      <span class="px-1.5 py-0.5 rounded text-[9.5px] font-bold border font-mono ${stBadgeClass}">${escapeHtml(st)}</span>
                      <span class="truncate font-mono text-[11.5px]" title="${escapeHtml(filePath)}">
                        <span class="text-slate-400">${escapeHtml(dirPart)}</span><span class="text-slate-100 font-bold">${escapeHtml(filePart)}</span>
                      </span>
                      ${isPre ? `
                        <span class="file-tag-preexisting px-1.5 py-0.5 rounded text-[10px] font-sans font-medium text-amber-300 bg-amber-500/15 border border-amber-500/35 shrink-0" title="Tập tin này đã có thay đổi từ trước khi chạy tác vụ, không phải do AI chỉnh sửa trong phiên này">
                          Thay đổi trước đó
                        </span>
                      ` : `
                        <span class="file-tag-ai px-1.5 py-0.5 rounded text-[10px] font-sans font-medium text-blue-300 bg-blue-500/20 border border-blue-400/35 shrink-0" title="Tập tin do AI trực tiếp chỉnh sửa">
                          Do AI chỉnh sửa
                        </span>
                      `}
                    </div>
                    <div class="flex items-center gap-2 shrink-0">
                      <span class="px-1.5 py-0.5 rounded text-[10px] font-mono font-bold text-[#73c991] bg-[#73c991]/15">+${f.additions || 0}</span>
                      <span class="px-1.5 py-0.5 rounded text-[10px] font-mono font-bold text-[#f14c4c] bg-[#f14c4c]/15">-${f.deletions || 0}</span>
                      <button type="button" onclick="event.stopPropagation(); openFileEditor('${escapeHtml(f.path)}', '${escapeHtml(f.repo || 'fe')}')"
                        class="file-edit-btn p-1 rounded hover:bg-sky-500/15 text-sky-400 hover:text-sky-300 transition flex items-center justify-center cursor-pointer"
                        title="Chỉnh sửa file (${escapeHtml(filePart)}) (Ctrl+S để lưu)">
                        <svg class="w-3.5 h-3.5 fill-none stroke-current" viewBox="0 0 24 24" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                          <path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7" />
                          <path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z" />
                        </svg>
                      </button>
                      ${f.diff ? `
                        <button type="button" onclick="event.stopPropagation(); toggleStepOutput('${diffId}')"
                          class="p-1 rounded hover:bg-white/10 text-slate-400 hover:text-white transition flex items-center justify-center cursor-pointer"
                          title="${autoExpand ? 'Thu gọn Diff' : 'Mở rộng Diff'}">
                          <svg id="arrow_${diffId}" class="w-3.5 h-3.5 fill-none stroke-current transition-transform duration-200 ${autoExpand ? 'rotate-180' : ''}" viewBox="0 0 24 24" stroke-width="2.5">
                            <path stroke-linecap="round" stroke-linejoin="round" d="M19 9l-7 7-7-7" />
                          </svg>
                        </button>
                      ` : ''}
                    </div>
                  </div>
                  ${f.diff ? `
                    <div id="${diffId}" class="${autoExpand ? '' : 'hidden'} max-h-96 overflow-y-auto">
                      ${formatDiffColoredHtml(f.diff)}
                    </div>
                  ` : ''}
                </div>
              `;
  }).join('')}
          </div>
        </div>
      `;
}

function formatStepTitle(step) {
  if (step.display_title) return step.display_title;
  const tname = (step.tool_name || '').toLowerCase();
  const cmd = (step.params && (step.params.CommandLine || step.params.command)) || step.param_summary || '';
  const path = (step.params && (step.params.Path || step.params.path || step.params.TargetFile)) || '';
  const fname = step.file_name || (path ? path.split('/').pop() : '');
  const pattern = (step.params && (step.params.query || step.params.pattern)) || '';

  if (['run_command', 'command', 'bash', 'sh'].includes(tname) || cmd) {
    const shortCmd = cmd.length > 120 ? cmd.slice(0, 120) + '...' : cmd;
    return `Ran (${shortCmd})`;
  }
  if (['read_file', 'view_file', 'read'].includes(tname)) {
    return `Explored 1 file (${fname || 'file'})`;
  }
  if (['grep_search', 'search', 'grep'].includes(tname)) {
    return `Ran (grep "${pattern || 'text'}")`;
  }
  if (['find_by_name', 'list_dir', 'ls', 'explore'].includes(tname)) {
    return `Explored (${fname || path || 'directory'})`;
  }
  if (['replace_file_content', 'multi_replace_file_content', 'edit_file', 'write_file', 'edit', 'write'].includes(tname)) {
    return `Edited ${fname || 'file'}`;
  }
  return `Ran ${step.tool_name} (${step.param_summary || ''})`;
}

function renderStepLogsHtml(stepLogs, sessId, turnIdx, isStreaming = false, streamingPreview = '') {
  const logs = stepLogs || [];
  if (logs.length === 0 && !isStreaming) return '';

  const stepBoxId = `stepBox_${sessId}_${turnIdx}`;
  const isStepCollapsed = _collapsedStepBoxes.has(stepBoxId);
  const hasActiveSteps = Boolean(isStreaming) && (logs.length === 0 || logs.some(s => s.state !== 'DONE'));

  if (logs.length === 0 && isStreaming) {
    return `
      <div class="tool-step-box mb-3 rounded-lg border border-[#244170] bg-[#070d18] overflow-hidden shadow-inner">
        <div id="stepHeader_${stepBoxId}"
             class="tool-step-header px-3 py-2 bg-[#0d182b] flex items-center justify-between text-[11px] font-sans font-semibold text-slate-300">
          <div class="flex items-center gap-2.5">
            <div class="wave-dots">
              <span class="wave-dot"></span>
              <span class="wave-dot"></span>
              <span class="wave-dot"></span>
            </div>
            <span class="text-white font-medium font-sans">Tiến trình AI Terminal ngầm</span>
          </div>
          <span class="text-cyan-400 font-mono text-[10.5px]">Đang khởi tạo...</span>
        </div>
        <div id="stepLogsBody_${stepBoxId}" class="p-3 font-mono text-[11.5px] bg-[#050912] flex items-center gap-2.5 text-cyan-300">
          <div class="wave-dots">
            <span class="wave-dot"></span>
            <span class="wave-dot"></span>
            <span class="wave-dot"></span>
          </div>
          <span class="truncate text-slate-200">${escapeHtml(streamingPreview || 'Đang khởi chạy tiến trình AI Terminal ngầm...')}</span>
        </div>
      </div>
    `;
  }

  return `
        <div class="tool-step-box mb-3 rounded-lg border border-[#244170] bg-[#070d18] overflow-hidden shadow-inner">
          <div id="stepHeader_${stepBoxId}"
               onclick="toggleStepLogsCollapse('${stepBoxId}', event)"
               class="tool-step-header px-3 py-2 bg-[#0d182b] ${isStepCollapsed ? '' : 'border-b border-[#1e3458]'} flex items-center justify-between text-[11px] font-sans font-semibold text-slate-300 cursor-pointer select-none hover:bg-[#14233e] transition"
               title="${isStepCollapsed ? 'Nhấp để hiển thị tiến trình AI Terminal ngầm' : 'Nhấp để thu gọn tiến trình AI Terminal ngầm'}">
            <div class="flex items-center gap-2.5">
              ${hasActiveSteps || isStreaming ? `
                <div class="wave-dots">
                  <span class="wave-dot"></span>
                  <span class="wave-dot"></span>
                  <span class="wave-dot"></span>
                </div>
              ` : '<span class="w-2 h-2 rounded-full bg-emerald-400"></span>'}
              <span class="text-white font-medium font-sans">Tiến trình AI Terminal ngầm (${logs.length} thao tác)</span>
            </div>
            <div class="flex items-center gap-1.5 text-slate-400">
              <button type="button" onclick="toggleStepLogsCollapse('${stepBoxId}', event)"
                class="p-1 rounded hover:bg-white/10 text-slate-400 hover:text-white transition flex items-center justify-center cursor-pointer"
                title="${isStepCollapsed ? 'Nhấp để hiển thị tiến trình AI Terminal ngầm' : 'Nhấp để thu gọn tiến trình AI Terminal ngầm'}">
                <svg id="stepArrow_${stepBoxId}" class="w-3.5 h-3.5 fill-none stroke-current transition-transform duration-200 ${isStepCollapsed ? '' : 'rotate-180'}" viewBox="0 0 24 24" stroke-width="2.5">
                  <path stroke-linecap="round" stroke-linejoin="round" d="M19 9l-7 7-7-7" />
                </svg>
              </button>
            </div>
          </div>
          <div id="stepLogsBody_${stepBoxId}" class="${isStepCollapsed ? 'hidden' : ''} p-2 font-mono text-[11.5px] space-y-1 bg-[#050912] max-h-72 overflow-y-auto">
            ${logs.map((step, sIdx) => {
    const outId = `step_out_${sessId}_${turnIdx}_${sIdx}`;
    const isDone = (step.state === 'DONE');
    const durationStr = step.duration ? formatDuration(step.duration) : (isDone ? 'xong' : '');
    const stepTitle = formatStepTitle(step);
    const autoShowOutput = Boolean(!isDone || (sIdx === logs.length - 1 && step.output));
    return `
                <div class="terminal-step-item rounded px-2 py-1.5 hover:bg-[#0f1d36] transition flex flex-col gap-1 border border-transparent hover:border-[#1e3458]">
                  <div class="flex items-center justify-between gap-2 cursor-pointer select-none group" onclick="toggleStepOutput('${outId}')">
                    <div class="flex items-center gap-2 min-w-0 flex-1">
                      <span class="${isDone ? 'text-emerald-400' : 'text-cyan-400 animate-pulse'} font-bold select-none text-[13px] leading-none shrink-0">●</span>
                      <span class="text-slate-100 font-mono text-[11.5px] truncate" title="${escapeHtml(stepTitle)}">${escapeHtml(stepTitle)}</span>
                      <span class="text-slate-500 text-[10px] group-hover:text-cyan-300 font-sans shrink-0">(${step.output ? 'ctrl+o' : (isDone ? 'xong' : 'đang chạy...')})</span>
                    </div>
                    <div class="flex items-center gap-2 shrink-0 text-[10.5px]">
                      ${isDone ? `<span class="text-emerald-400 font-mono text-[10px]">${durationStr}</span>` : '<span class="text-cyan-400 font-mono text-[10px] animate-pulse">Running</span>'}
                      <span class="text-slate-500 text-[10px] font-mono">${step.timestamp || ''}</span>
                    </div>
                  </div>
                  ${step.output ? `
                    <div id="${outId}" class="${autoShowOutput ? '' : 'hidden'} mt-1.5 p-2 rounded-lg bg-white dark:bg-[#060a12] border border-slate-200 dark:border-[#1e3458] text-[11px] font-mono max-h-64 overflow-y-auto shadow-sm">
                      ${formatStepOutputWithDiff(step.output)}
                    </div>
                  ` : ''}
                </div>
              `;
  }).join('')}
            ${isStreaming ? `
              <div class="streaming-step-preview flex items-center gap-2.5 px-2.5 py-1.5 font-mono text-[11.5px] text-cyan-300 mt-1 border-t border-[#1e3458]/60 bg-[#081326]/50 rounded">
                <div class="wave-dots">
                  <span class="wave-dot"></span>
                  <span class="wave-dot"></span>
                  <span class="wave-dot"></span>
                </div>
                <span class="truncate text-slate-200">${escapeHtml(streamingPreview || 'Đang thực thi các thao tác trên AI Terminal...')}</span>
              </div>
            ` : ''}
          </div>
        </div>
      `;
}

function renderFeedFilterTabs() {
  const container = document.getElementById('feedTaskFilterTabs');
  if (!container) return;

  const tabs = [
    { id: 'all', label: `Tất cả (${parallelTasks.length})` },
    ...parallelTasks.map((t, idx) => ({ id: t.id, name: t.name, status: t.status, type: t.type, idx: idx + 1 }))
  ];

  container.innerHTML = tabs.map(tab => {
    if (tab.id === 'all') {
      const isActive = activeFeedFilter === 'all';
      return `
        <button type="button" onclick="setFeedFilter('all')" title="Hiển thị tất cả"
          class="px-2.5 py-1 text-[11px] rounded font-medium transition flex items-center gap-1 shrink-0 select-none ${isActive
          ? 'active-feed-filter bg-[#199cff] text-white shadow-sm font-bold'
          : 'text-slate-300 hover:text-white hover:bg-white/5'
        }">
          <span>${escapeHtml(tab.label)}</span>
        </button>
      `;
    }

    const isActive = activeFeedFilter === tab.id;
    const isEditing = editingTaskId === tab.id;
    const { prefix, subName } = parseTaskName(tab.name, tab.idx);
    const isRunning = tab.status === 'running';
    const isQueued = tab.status === 'queued';
    const isDone = tab.status === 'completed' || tab.status === 'done';
    const isStopped = tab.status === 'stopped';

    let badge = '';
    if (isRunning) {
      badge = '<span class="w-1.5 h-1.5 rounded-full bg-cyan-400 animate-ping ml-0.5" title="Đang chạy"></span>';
    } else if (isQueued) {
      badge = '<span class="w-1.5 h-1.5 rounded-full bg-amber-400 ml-0.5" title="Đang chờ trong hàng đợi"></span>';
    } else if (isDone) {
      badge = '<span class="text-emerald-400 text-[10px] font-bold ml-0.5" title="Đã hoàn tất">✓</span>';
    } else if (isStopped) {
      badge = '<span class="text-rose-400 text-[9px] font-bold ml-0.5" title="Đã dừng">■</span>';
    }

    return `
      <button type="button" onclick="setFeedFilter('${tab.id}')"
        title="Bấm để lọc theo tác vụ này"
        class="px-2.5 py-1 text-[11px] rounded font-medium transition flex items-center gap-1 shrink-0 select-none ${isActive
        ? 'active-feed-filter bg-[#199cff] text-white shadow-sm font-bold'
        : 'text-slate-300 hover:text-white hover:bg-white/5'
      }">
        <span class="max-w-[150px] truncate"><span class="opacity-80">${escapeHtml(prefix)}</span> ${escapeHtml(subName)}</span>
        ${badge}
      </button>
    `;
  }).join('');
}

function setFeedFilter(filterId) {
  activeFeedFilter = filterId;
  if (filterId !== 'all') {
    activeTaskId = filterId;
    loadTaskToForm(filterId);
    if (!editingTaskId) {
      renderParallelTaskTabs();
    }
    updateTaskActionButtons();
  }
  renderFeedFilterTabs();
  pollStatus();
}

function renderFeedView(data) {
  const feed = document.getElementById('taskFeed');
  if (!feed) return;

  const serverTasks = data.tasks || {};
  const taskEntries = Object.entries(serverTasks);

  let sessionsToRender = [];

  const validTaskIds = new Set();
  parallelTasks.forEach(t => {
    validTaskIds.add(t.id);
    validTaskIds.add('queued_' + t.id);
    if (String(t.id).startsWith('queued_')) {
      validTaskIds.add(String(t.id).replace('queued_', ''));
    }
  });

  if (activeFeedFilter === 'all') {
    if (taskEntries.length > 0) {
      sessionsToRender = taskEntries
        .filter(([tid, t]) => {
          if (!t.session) return false;
          const sTid = t.session.task_id || t.session.id || tid;
          const cleanSTid = String(sTid).replace(/^queued_/, '');
          return validTaskIds.has(tid) || validTaskIds.has(sTid) || validTaskIds.has(cleanSTid);
        })
        .map(([tid, t]) => ({
          ...t.session,
          _taskTitle: t.title,
          _taskId: tid,
          _mode: t.mode,
          _statusText: t.status_text
        }));
    }
    
    // Only fall back to current_session if sessionsToRender is empty AND current_session belongs to a non-idle task in parallelTasks
    if (sessionsToRender.length === 0 && data.current_session) {
      const curTid = data.current_session.task_id || data.current_session.id;
      const cleanCurTid = curTid ? String(curTid).replace(/^queued_/, '') : '';
      const matchingTask = parallelTasks.find(t =>
        t.id === curTid ||
        t.id === cleanCurTid ||
        t.id === ('queued_' + cleanCurTid) ||
        ('queued_' + t.id) === curTid
      );

      if (matchingTask && matchingTask.status !== 'idle') {
        sessionsToRender = [{
          ...data.current_session,
          _taskTitle: data.current_session.title || matchingTask.name || (data.mode === 'fixbug' ? 'Fix bug' : 'Làm task'),
          _taskId: matchingTask.id,
          _mode: data.mode,
          _statusText: data.status_text
        }];
      }
    }
  } else {
    const found = serverTasks[activeFeedFilter];
    if (found && found.session && (validTaskIds.has(activeFeedFilter) || validTaskIds.has(String(activeFeedFilter).replace(/^queued_/, '')))) {
      sessionsToRender = [{
        ...found.session,
        _taskTitle: found.title,
        _taskId: activeFeedFilter,
        _mode: found.mode,
        _statusText: found.status_text
      }];
    }
  }

  const allowedWrapIds = new Set();
  sessionsToRender.forEach(s => allowedWrapIds.add('sessWrap_' + (s._taskId || s.id)));

  Array.from(feed.querySelectorAll('[id^="sessWrap_"]')).forEach(el => {
    if (!allowedWrapIds.has(el.id)) {
      el.remove();
    }
  });

  if (sessionsToRender.length === 0) {
    if (!document.getElementById('taskEmptyState')) {
      feed.innerHTML = `
        <div id="taskEmptyState" class="h-full flex flex-col items-center justify-center text-center p-8 text-slate-400">
          <h3 id="taskEmptyTitle" class="text-xs font-semibold text-slate-300">Chưa có tác vụ nào đang chạy</h3>
          <p id="taskEmptySubtitle" class="text-xs text-slate-400 max-w-sm mt-1">Cấu hình thông tin bên trái và nhấn "Bắt đầu tác vụ".</p>
        </div>
      `;
    }
    return;
  }

  const empty = document.getElementById('taskEmptyState');
  if (empty) empty.remove();

  sessionsToRender.forEach(sess => {
    const sessWrapId = 'sessWrap_' + (sess._taskId || sess.id);
    let sessWrap = document.getElementById(sessWrapId);
    if (!sessWrap) {
      sessWrap = document.createElement('div');
      sessWrap.id = sessWrapId;
      sessWrap.className = 'space-y-3 mb-6';
      feed.appendChild(sessWrap);
    }

    const sessHeaderId = 'sessHeader_' + (sess._taskId || sess.id);
    let sessHeader = document.getElementById(sessHeaderId);
    if (!sessHeader) {
      sessHeader = document.createElement('div');
      sessHeader.id = sessHeaderId;
      sessHeader.className = 'rounded-lg p-3.5 shadow-sm text-white border border-[#1677ff]';
      sessHeader.style.background = 'linear-gradient(135deg, #1677ff 0%, #0958d9 100%)';
      sessWrap.appendChild(sessHeader);
    } else {
      sessHeader.className = 'rounded-lg p-3.5 shadow-sm text-white border border-[#1677ff]';
      sessHeader.style.background = 'linear-gradient(135deg, #1677ff 0%, #0958d9 100%)';
    }

    const isFix = (sess.type === 'FIX_BUG' || sess._mode === 'fixbug');
    const isRefactor = (sess.type === 'REFACTOR' || sess._mode === 'refactor' || (sess._taskTitle && sess._taskTitle.toLowerCase().includes('refactor')));
    let badgeClass = 'bg-white/20 text-white border border-white/30';
    let badgeLabel = 'TASK';
    if (isFix) {
      badgeClass = 'bg-white/20 text-white border border-white/30';
      badgeLabel = 'FIX BUG';
    } else if (isRefactor) {
      badgeClass = 'bg-white/20 text-white border border-white/30';
      badgeLabel = 'REFACTOR';
    }
    const titleBadge = sess._taskTitle || (isFix ? 'Fix Bug' : (isRefactor ? 'Refactor Code' : 'Làm Task'));
    const rawScope = String(sess.scope || sess.target || 'both').toLowerCase();
    let scopeBadge = 'Cả hai (FE & BE)';
    if (rawScope === 'fe') scopeBadge = 'FE (Frontend)';
    else if (rawScope === 'be') scopeBadge = 'BE (Backend)';
    const skillBadge = sess.skill || 'Tự động';
    const isCompleted = sess.status === 'COMPLETED';
    const isQueued = sess.status === 'QUEUED';
    const isStopped = sess.status === 'STOPPED';
    const convertedCmd = sess.converted_prompt || '';

    const sessEngine = sess.engine || (currentStudioSettings && currentStudioSettings.engine) || 'gemini_cli';
    const isOpenCode = (sessEngine === 'opencode');
    const engineBadgeLabel = sess.engine_label || (isOpenCode ? 'OpenCode CLI' : 'Gemini CLI');
    const sessModel = sess.model || (isOpenCode ? (currentStudioSettings.opencode_model || '') : (currentStudioSettings.model || '')) || '';

    let statusHtml = '<span class="text-white flex items-center gap-1 font-sans bg-white/15 px-1.5 py-0.5 rounded border border-white/25"><span class="w-1.5 h-1.5 rounded-full bg-cyan-300 animate-ping"></span>Đang chạy</span>';
    if (isCompleted) {
      statusHtml = '<span class="text-emerald-200 font-bold font-sans bg-emerald-500/20 px-1.5 py-0.5 rounded border border-emerald-400/30">✓ Hoàn tất</span>';
    } else if (isQueued) {
      statusHtml = `<span class="text-amber-200 font-bold flex items-center gap-1 font-sans bg-amber-500/20 px-1.5 py-0.5 rounded border border-amber-400/30"><span class="w-1.5 h-1.5 rounded-full bg-amber-300"></span>${escapeHtml(sess._statusText || 'Đang chờ trong hàng đợi')}</span>`;
    } else if (isStopped) {
      statusHtml = '<span class="text-rose-200 font-bold font-sans bg-rose-500/20 px-1.5 py-0.5 rounded border border-rose-400/30">■ Đã dừng</span>';
    }

    sessHeader.innerHTML = `
          <div class="flex items-center justify-between gap-2 mb-1.5">
            <div class="flex items-center gap-2 min-w-0">
              <span class="px-2 py-0.5 rounded text-[10px] font-bold shrink-0 ${badgeClass}">${badgeLabel}</span>
              <span class="text-xs font-bold text-white truncate">${escapeHtml(titleBadge)}</span>
            </div>
            <div class="flex items-center gap-2 text-[10px] font-sans text-white/90 shrink-0">
              ${statusHtml}
              <button type="button" onclick="removeParallelTask('${sess._taskId || sess.task_id || sess.id}', event)" class="p-1 rounded bg-white/15 hover:bg-white/25 text-white border border-white/25 text-[10px] flex items-center justify-center transition cursor-pointer" title="Xóa tác vụ này khỏi Diễn biến thực thi">
                <svg class="w-3.5 h-3.5 fill-current text-white" viewBox="0 0 24 24"><path d="M6 19c0 1.1.9 2 2 2h8c1.1 0 2-.9 2-2V7H6v12zM19 4h-3.5l-1-1h-5l-1 1H5v2h14V4z"/></svg>
              </button>
            </div>
          </div>
          ${(sess.prompt || sess.description) ? `
            <div class="text-xs text-white/95 font-medium mt-1 leading-relaxed">${escapeHtml(sess.prompt || sess.description)}</div>
          ` : ''}
          ${sess.error_log ? `<pre class="mt-2 bg-black/40 p-2 rounded text-[11px] text-white/90 font-mono overflow-x-auto border border-white/20 max-h-32">${escapeHtml(sess.error_log)}</pre>` : ''}
        `;

    const turns = sess.turns || [];
    const isRunning = (!isCompleted && !isQueued && !isStopped);
    const activeRunningCardId = 'turnCard_' + (sess._taskId || sess.id) + '_running';
    let runningCard = document.getElementById(activeRunningCardId);

    if (isRunning && turns.length === 0) {
      if (!runningCard) {
        runningCard = document.createElement('div');
        runningCard.id = activeRunningCardId;
        runningCard.className = 'rounded-lg border border-[#1677ff] bg-[#0c1628] p-3.5 shadow-sm text-xs font-sans space-y-2.5';
        sessWrap.appendChild(runningCard);
      }
      runningCard.innerHTML = `
        <div class="flex items-center justify-between text-xs font-semibold text-cyan-400">
          <span class="flex items-center gap-2">
            <span class="w-2 h-2 rounded-full bg-cyan-400 animate-ping"></span>
            <span class="font-bold">${isOpenCode ? 'OpenCode CLI đang thực thi ngầm...' : 'AI Terminal đang thực thi ngầm...'}</span>
          </span>
          <span class="text-slate-400 text-[10px] font-sans">Đang xử lý</span>
        </div>
        <div class="p-2.5 rounded bg-[#060a12] border border-[#1e3458] text-[11px] space-y-1">
          <div class="flex items-center gap-1.5 text-slate-400 text-[10px] font-sans">
            <span>Tiến trình thực thi:</span>
          </div>
          <div class="font-mono text-cyan-300 flex items-center gap-1.5">
            <span class="text-cyan-400 select-none">$</span>
            <span class="break-all">${escapeHtml(sess._statusText || (isOpenCode ? 'Đang gọi OpenCode CLI và chạy lệnh trên workspace...' : 'Đang chuẩn bị workspace và chạy lệnh trên AI Terminal...'))}</span>
          </div>
        </div>
      `;
    } else if (runningCard) {
      runningCard.remove();
    }

    const isSessRunning = isRunning || Boolean(sess._isRunning) || sess.status === 'RUNNING' || sess.status === 'STARTING' || sess.status === 'IN_PROGRESS';
    turns.forEach((t, i) => {
      const cardId = 'turnCard_' + (sess._taskId || sess.id) + '_' + i;
      let card = document.getElementById(cardId);
      const isFe = t.speaker === 'fe';
      const isLatestTurn = (i === turns.length - 1);
      const isStreaming = Boolean(t.is_streaming) || (isSessRunning && isLatestTurn);
      const streamingIndicator = isStreaming ? '<span class="inline-flex items-center gap-1.5 text-[11px] text-cyan-400 font-mono"><span class="w-1.5 h-1.5 rounded-full bg-cyan-400 animate-ping"></span>Đang xử lý trên AI Terminal...</span>' : '';
      const turnFiles = (t.changed_files && t.changed_files.length > 0) ? t.changed_files : (sess.changed_files || []);
      const bodyContent = t.content ? safeMarkdown(t.content, turnFiles) : '';
      const streamingPreviewText = t.content ? (t.content.slice(-70).trim().replace(/\n+/g, ' ')) : (sess._statusText || t.status_text || 'Đang thực thi lệnh trên AI Terminal...');
      const stepLogsHtml = renderStepLogsHtml(t.step_logs, sess._taskId || sess.id, i, isStreaming, streamingPreviewText);
      const changedFilesHtml = renderChangedFilesHtml(t.changed_files, sess._taskId || sess.id, i);

      const hasStepLogs = Boolean(t.step_logs && t.step_logs.length > 0);
      const hasContent = Boolean(t.content && t.content.trim().length > 0);
      let loadingPlaceholderHtml = '';
      if (isSessRunning && isLatestTurn && !hasContent && !hasStepLogs) {
        loadingPlaceholderHtml = `
          <div class="thinking-card-box my-2.5 rounded-lg border border-[#1677ff]/40 bg-[#070d18] overflow-hidden shadow-inner p-3.5 space-y-2.5">
            <div class="thinking-card-header flex items-center justify-between">
              <div class="flex items-center gap-2.5">
                <div class="wave-dots">
                  <span class="wave-dot"></span>
                  <span class="wave-dot"></span>
                  <span class="wave-dot"></span>
                </div>
                <span class="thinking-card-title text-xs font-semibold text-cyan-300 font-sans">AI Agent đang suy nghĩ &amp; chuẩn bị tiến trình ngầm...</span>
              </div>
              <span class="thinking-card-badge text-[10.5px] font-mono text-cyan-400 bg-cyan-950/80 px-2 py-0.5 rounded border border-cyan-800 animate-pulse">Đang xử lý</span>
            </div>
            <div class="thinking-card-cmd p-2.5 rounded bg-[#040810] border border-[#1e3458] text-[11px] font-mono text-slate-300 flex items-center gap-2">
              <span class="text-cyan-400 select-none font-bold">$</span>
              <span class="thinking-card-cmd-text truncate text-slate-200">${escapeHtml(sess._statusText || t.status_text || 'Đang chuẩn bị workspace và chạy lệnh trên AI Terminal...')}</span>
            </div>
            <div class="thinking-card-bars space-y-1.5 pt-1">
              <div class="h-1.5 bg-gradient-to-r from-cyan-500/30 via-cyan-400/10 to-transparent rounded animate-pulse w-4/5"></div>
              <div class="h-1.5 bg-gradient-to-r from-cyan-500/20 via-cyan-400/5 to-transparent rounded animate-pulse w-1/2"></div>
            </div>
          </div>
        `;
      }

      if (!card) {
        card = document.createElement('div');
        card.id = cardId;
        card.className = `rounded-lg border p-3.5 shadow-sm transition ${isFe ? 'bg-[#0f172a] border-cyan-800/60' : 'bg-[#091518] border-emerald-800/60'}`;
        sessWrap.appendChild(card);
      }

      let isCollapsed;
      if (_userInteractedTurnCards.has(cardId)) {
        isCollapsed = _userInteractedTurnCards.get(cardId);
      } else {
        isCollapsed = !isLatestTurn;
      }

      if (isCollapsed) {
        _collapsedTurnCards.add(cardId);
      } else {
        _collapsedTurnCards.delete(cardId);
      }

      const stepBoxId = `stepBox_${sess._taskId || sess.id}_${i}`;
      const diffBoxId = `diffBox_${sess._taskId || sess.id}_${i}`;
      const isStepCollapsed = _collapsedStepBoxes.has(stepBoxId);
      const isDiffCollapsed = _collapsedDiffBoxes.has(diffBoxId);

      const turnEngine = t.engine || sessEngine;
      const isTurnOpenCode = (turnEngine === 'opencode');
      const turnEngineLabel = t.engine_label || (isTurnOpenCode ? 'OpenCode CLI' : 'Gemini CLI');

      const turnImagesHtml = (t.images && t.images.length > 0) ? `
        <div class="turn-images-strip mb-2.5 p-2 rounded-lg border border-[#244170]/70 bg-[#091426] flex flex-wrap gap-2">
          ${t.images.map(img => {
            const sUrl = escapeHtml(img.url);
            const sName = escapeHtml(img.name || img.filename || 'Ảnh minh chứng');
            return `
              <div class="cursor-pointer group flex items-center gap-1.5 px-2 py-1 rounded bg-[#0d1c33] border border-[#1e3860] hover:border-[#1677ff] transition"
                   onclick="openImagePreviewModal('${sUrl}', '${sName}')" title="Phóng to ảnh: ${sName}">
                <svg class="w-3.5 h-3.5 text-sky-400 shrink-0" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" d="M4 16l4.586-4.586a2 2 0 012.828 0L16 16m-2-2l1.586-1.586a2 2 0 012.828 0L20 14m-6-6h.01M6 20h12a2 2 0 002-2V6a2 2 0 00-2-2H6a2 2 0 00-2 2v12a2 2 0 002 2z" />
                </svg>
                <span class="text-[11px] font-mono text-slate-200 group-hover:text-sky-300 max-w-[160px] truncate">${sName}</span>
              </div>
            `;
          }).join('')}
        </div>
      ` : '';

      const changesSig = (t.changed_files || []).map(cf => `${cf.path}:${cf.status}:${cf.additions}:${cf.deletions}`).join('|');
      const currentSig = `${(t.content || '').length}_${(t.step_logs || []).length}_${t.elapsed_sec}_${isStreaming}_${Boolean(loadingPlaceholderHtml)}_${(t.step_logs || []).map(s => s.state + (s.output ? s.output.length : 0)).join(',')}_${changesSig}_${isCollapsed}_${isStepCollapsed}_${isDiffCollapsed}_${turnEngine}_${(t.images || []).length}`;
      if (card.dataset.sig !== currentSig) {
        card.dataset.sig = currentSig;
        card.innerHTML = `
              <div onclick="toggleTurnCollapse('${cardId}', event)"
                class="flex items-center justify-between text-xs font-semibold cursor-pointer select-none py-1 px-1.5 -mx-1.5 rounded hover:bg-white/5 transition ${isFe ? 'text-cyan-400' : 'text-emerald-400'}">
                <span class="flex items-center gap-2 min-w-0">
                  <button type="button" onclick="toggleTurnCollapse('${cardId}', event)"
                    class="p-1 rounded hover:bg-white/10 text-slate-400 hover:text-white transition flex items-center justify-center cursor-pointer shrink-0"
                    title="${isCollapsed ? 'Nhấp để mở rộng lượt này' : 'Nhấp để thu gọn lượt này'}">
                    <svg id="turnChevron_${cardId}" class="w-3.5 h-3.5 fill-none stroke-current transition-transform duration-200 ${isCollapsed ? '-rotate-90' : ''}" viewBox="0 0 24 24" stroke-width="2.5">
                      <path stroke-linecap="round" stroke-linejoin="round" d="M19 9l-7 7-7-7" />
                    </svg>
                  </button>
                  <span class="font-bold truncate">${escapeHtml(t.label || (isFe ? 'Frontend Agent' : 'Backend Agent'))} • Lượt ${t.round}/${sess.total_rounds || 1}</span>
                  <span class="turn-engine-badge px-1.5 py-0.5 rounded text-[9.5px] font-sans border ${isTurnOpenCode ? 'bg-blue-500/15 text-blue-300 border-blue-500/30' : 'bg-emerald-500/15 text-emerald-300 border-emerald-500/30'}">${escapeHtml(turnEngineLabel)}</span>
                  ${streamingIndicator}
                </span>
                <span class="text-slate-400 text-[10px] font-mono shrink-0 ml-2">${t.timestamp || ''} (${formatDuration(t.elapsed_sec || 0)})</span>
              </div>
              <div id="turnBody_${cardId}" class="turn-body-content mt-2.5 ${isCollapsed ? 'hidden' : ''}">
                ${turnImagesHtml}
                ${stepLogsHtml}
                ${changedFilesHtml}
                ${loadingPlaceholderHtml}
                ${bodyContent ? `<div class="markdown-body text-[13px] text-slate-200 leading-[1.82] tracking-wide overflow-x-auto">${bodyContent}</div>` : ''}
              </div>
            `;
      }
    });

    const taskIdKey = sess._taskId || sess.task_id || sess.id;
    const contBoxId = 'sessContinueBox_' + taskIdKey;
    let contBox = document.getElementById(contBoxId);
    if (isCompleted || isStopped) {
      if (!contBox) {
        contBox = document.createElement('div');
        contBox.id = contBoxId;
        contBox.className = 'mt-3 pt-3 border-t border-[#244170] flex flex-col gap-2';
        const curEff = currentStudioSettings.effort || 'high';
        contBox.innerHTML = `
              <div class="flex items-center justify-between text-[11px] font-semibold text-cyan-300">
                <span class="flex items-center gap-1.5">
                  <span>Tiếp tục task trên AI Terminal ngầm</span>
                  <span class="text-[10px] font-normal text-slate-400">• Giữ nguyên ngữ cảnh</span>
                </span>
                <div class="flex items-center gap-2">
                  <label for="continueFileInput_${taskIdKey}"
                    class="text-[11px] font-sans text-sky-400 hover:text-sky-300 flex items-center gap-1 cursor-pointer select-none transition hover:underline"
                    title="Đính kèm ảnh minh chứng hoặc dán trực tiếp (Ctrl+V) vào ô nhập liệu">
                    <svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24">
                      <path stroke-linecap="round" stroke-linejoin="round" d="M4 16l4.586-4.586a2 2 0 012.828 0L16 16m-2-2l1.586-1.586a2 2 0 012.828 0L20 14m-6-6h.01M6 20h12a2 2 0 002-2V6a2 2 0 00-2-2H6a2 2 0 00-2 2v12a2 2 0 002 2z" />
                    </svg>
                    <span>Đính kèm ảnh</span>
                    <input id="continueFileInput_${taskIdKey}" type="file" accept="image/*" class="hidden" onchange="onContinueFileSelect(event, '${taskIdKey}')" />
                  </label>
                </div>
              </div>
              <div class="flex items-center gap-2">
                <input id="continueInput_${taskIdKey}" type="text"
                  placeholder="Nhập yêu cầu tiếp theo (hoặc để trống để AI hoàn thiện task, có thể dán Ctrl+V ảnh)..."
                  onpaste="handleContinuePaste(event, '${taskIdKey}')"
                  onkeydown="if(event.key==='Enter'){event.preventDefault();continueTaskFromFeed('${taskIdKey}');}"
                  class="flex-1 bg-[#0b1322] border border-[#244170] rounded px-3 py-1.5 text-xs text-slate-100 focus:outline-none focus:border-[#1677ff]" />
                <button type="button" onclick="continueTaskFromFeed('${taskIdKey}')"
                  class="ant-btn ant-btn-primary px-3.5 py-1.5 rounded text-white text-xs font-bold shrink-0 flex items-center gap-1.5 shadow-sm transition" style="color: #ffffff !important; background: linear-gradient(135deg, #1677ff 0%, #0958d9 100%) !important;">
                  <span class="text-white font-bold" style="color: #ffffff !important;">▶ Tiếp tục task</span>
                </button>
              </div>
              <div id="continueImagesContainer_${taskIdKey}" class="continue-images-container hidden p-2 rounded-lg border border-[#244170] bg-[#0c1628] flex flex-wrap gap-2"></div>
            `;
        sessWrap.appendChild(contBox);
      } else if (contBox.parentElement === sessWrap && sessWrap.lastElementChild !== contBox) {
        sessWrap.appendChild(contBox);
      }
      renderContinuationImages(taskIdKey);
    } else if (contBox) {
      contBox.remove();
    }
  });
}

async function startContinuationTask(task, followUp, attachedImages = []) {
  if (!task) return;
  const anyRunning = parallelTasks.some(t => t.status === 'running' && t.id !== task.id);
  task.status = anyRunning ? 'queued' : 'running';
  renderParallelTaskTabs();
  updateTaskActionButtons();

  const followText = (followUp || '').trim() || (attachedImages && attachedImages.length > 0 ? 'Xem ảnh minh chứng đính kèm và kiểm tra/sửa lỗi.' : 'Tiếp tục kiểm tra và hoàn thiện task này.');
  const goal = (task.original_prompt || task.prompt || '').trim();
  const isFix = task.type === 'fixbug';
  const common = {
    task_id: task.id,
    title: task.name,
    engine: currentStudioSettings.engine || 'gemini_cli',
    effort: task.effort || currentStudioSettings.effort || 'high',
    skills: task.skills || [],
    skill: (task.skills || []).join(', '),
    original_prompt: goal,
    error_log: '',
    continuation: true,
    images: attachedImages || []
  };

  try {
    const res = await fetch(isFix ? '/api/fixbug' : '/api/task', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(isFix ? Object.assign({}, common, {
        mode: 'fixbug',
        scope: task.target || 'both',
        description: followText
      }) : Object.assign({}, common, {
        mode: task.type || 'task',
        prompt: followText,
        target: task.target || 'both',
        starter: 'fe',
        rounds: 1
      }))
    });
    const d = await res.json();
    if (!d.success) {
      task.status = 'idle';
      await antdAlert({ title: 'Lỗi', content: d.message, type: 'error' });
    } else {
      task.status = d.queue_status === 'queued' ? 'queued' : 'running';
      showToast(d.message || 'Đã gửi yêu cầu tiếp theo xuống AI Terminal', 'success');
    }
  } catch (e) {
    task.status = 'idle';
    await antdAlert({ title: 'Lỗi kết nối', content: e.message, type: 'error' });
  }
  if (task.status === 'idle') {
    await syncQueueToServer();
  }
  renderParallelTaskTabs();
  updateTaskActionButtons();
  pollStatus();
}

async function continueTaskFromFeed(taskId) {
  let task = parallelTasks.find(t => t.id === taskId);
  if (!task) {
    activeTaskId = taskId;
    task = parallelTasks[0];
  }
  if (!task) return;

  const inputEl = document.getElementById('continueInput_' + taskId);
  const followUp = inputEl ? inputEl.value.trim() : '';
  const attachedImages = _continuationImages[taskId] ? [..._continuationImages[taskId]] : [];

  if (!followUp && attachedImages.length === 0 && !task.prompt && !task.error_log) {
    showToast('Vui lòng nhập nội dung cần hỏi hoặc tiếp tục.', 'warning');
    return;
  }
  if (!task.original_prompt) {
    task.original_prompt = task.prompt || '';
  }
  if (inputEl) inputEl.value = '';
  _continuationImages[taskId] = [];
  renderContinuationImages(taskId);

  activeTaskId = task.id;
  // Tiếp tục = một lượt hội thoại tiếp theo trong cùng phiên, KHÔNG chạy lại toàn bộ task
  // và KHÔNG nạp lại skill tác vụ ban đầu.
  await startContinuationTask(task, followUp, attachedImages);
}

let _lastShownApiErrorId = null;

async function triggerApiErrorModal(err) {
  if (!err) return;
  showToast(`${err.title}: ${err.message}`, 'error');

  const isQuota = err.error_type === 'quota_exceeded';
  const rawHtml = err.raw_error ? `
    <div class="mt-2.5 p-2.5 rounded-lg bg-[#160b13] border border-rose-800/60 text-rose-300 font-mono text-[11px] leading-relaxed break-all max-h-32 overflow-y-auto">
      ${escapeHtml(err.raw_error)}
    </div>` : '';

  const contentHtml = `
    <div class="space-y-2.5 text-left font-sans">
      <div class="text-sm text-slate-100 font-medium leading-relaxed">${escapeHtml(err.message)}</div>
      ${rawHtml}
      <div class="text-xs text-amber-300/90 flex items-center gap-1.5 pt-1">
        <span>💡 ${escapeHtml(err.action_hint || 'Vui lòng kiểm tra lại cấu hình API Key trong tab Cài đặt.')}</span>
      </div>
    </div>
  `;

  const conf = await antdConfirm({
    title: err.title || 'Cảnh báo API Key',
    content: contentHtml,
    okText: 'Đến Cài đặt (Settings)',
    cancelText: 'Đóng',
    danger: isQuota
  });

  fetch('/api/dismiss-api-error', { method: 'POST' }).catch(() => {});

  if (conf) {
    if (typeof switchTab === 'function') switchTab('settings');
    setTimeout(() => {
      const navBtn = document.getElementById('settingsNav_api');
      if (navBtn) {
        navBtn.click();
      } else if (typeof switchSettingsSidebarTab === 'function') {
        switchSettingsSidebarTab('api');
      }
      const input = document.getElementById('input_gemini_api_key')
        || document.getElementById('input_deepseek_api_key')
        || document.getElementById('input_custom_api_key');
      if (input) {
        input.scrollIntoView({ behavior: 'smooth', block: 'center' });
        input.focus();
      }
    }, 120);
  }
}
window.triggerApiErrorModal = triggerApiErrorModal;

async function pollStatus() {
  try {
    const res = await fetch('/api/status');
    const data = await res.json();

    if (data.latest_api_error && data.latest_api_error.id !== _lastShownApiErrorId) {
      _lastShownApiErrorId = data.latest_api_error.id;
      triggerApiErrorModal(data.latest_api_error);
    }

    if (data.settings) {
      currentStudioSettings = Object.assign({}, currentStudioSettings, data.settings);
      updateEffortUI(currentStudioSettings.effort);
      updateEngineUI(currentStudioSettings.engine, nineRouterOnline);
    }

    if (!_initialQueueRestored && Array.isArray(data.queue) && data.queue.length > 0) {
      _initialQueueRestored = true;
      parallelTasks = data.queue.map((q, idx) => ({
        id: q.id || ('task_' + (idx + 1)),
        name: q.title || q.name || `Task ${idx + 1}: ${(q.mode || q.type) === 'fixbug' ? 'Fix bug' : 'Tính năng mới'}`,
        type: q.mode || q.type || 'task',
        target: q.target || q.scope || 'both',
        skills: Array.isArray(q.skills) ? q.skills : (q.skills ? String(q.skills).split(',').map(s => s.trim()).filter(Boolean) : []),
        prompt: q.prompt || q.fix_desc || '',
        error_log: q.error_log || q.fix_err || '',
        status: q.status === 'done' ? 'completed' : (q.status || 'idle'),
        sessionId: null
      }));
      const runningOrQueued = parallelTasks.find(t => t.status === 'running' || t.status === 'queued');
      activeTaskId = runningOrQueued ? runningOrQueued.id : parallelTasks[0].id;
      loadTaskToForm(activeTaskId);
    } else {
      _initialQueueRestored = true;
    }

    if (data.tasks) {
      const serverTaskIds = new Set(Object.keys(data.tasks));
      const serverQueueIds = new Set((data.queue || []).map(q => q.id));

      parallelTasks = parallelTasks.filter(t => {
        if (!t.sessionId && t.status === 'idle') return true;
        return serverTaskIds.has(t.id) || serverQueueIds.has(t.id);
      });

      if (parallelTasks.length === 0) {
        parallelTasks = [{
          id: 'task_' + Date.now(),
          name: 'Task 1: Tính năng mới',
          type: 'task',
          target: 'both',
          skills: [],
          prompt: '',
          error_log: '',
          status: 'idle',
          sessionId: null
        }];
        activeTaskId = parallelTasks[0].id;
        loadTaskToForm(activeTaskId);
      }

      Object.entries(data.tasks).forEach(([tid, tinfo]) => {
        let task = parallelTasks.find(t => t.id === tid);
        const qStat = tinfo.queue_status || (tinfo.is_running ? 'running' : 'done');
        const mappedStatus = tinfo.is_running
          ? 'running'
          : (qStat === 'queued'
            ? 'queued'
            : (tinfo.session && tinfo.session.status === 'COMPLETED'
              ? 'completed'
              : (tinfo.session && tinfo.session.status === 'STOPPED' ? 'stopped' : 'idle')));

        if (!task) {
          const rawSkill = (tinfo.session && tinfo.session.skill) || '';
          task = {
            id: tid,
            name: tinfo.title || `Task (${tinfo.mode})`,
            type: tinfo.mode || 'task',
            target: (tinfo.session && (tinfo.session.target || tinfo.session.scope)) || 'both',
            skills: rawSkill ? rawSkill.split(',').map(s => s.trim()).filter(Boolean) : [],
            prompt: (tinfo.session && (tinfo.session.prompt || tinfo.session.description)) || '',
            error_log: (tinfo.session && tinfo.session.error_log) || '',
            status: mappedStatus,
            sessionId: tinfo.session ? tinfo.session.id : null
          };
          parallelTasks.push(task);
        } else {
          task.status = mappedStatus;
          if (tinfo.session) task.sessionId = tinfo.session.id;
        }
      });
    }

    if (!editingTaskId) {
      renderParallelTaskTabs();
    }
    renderFeedFilterTabs();
    updateTaskActionButtons();

    const taskTyping = document.getElementById('taskTypingIndicator');
    if (taskTyping) taskTyping.classList.add('hidden');

    renderFeedView(data);
    if (typeof updateNotifBadgeUI === 'function') updateNotifBadgeUI();
    const isRunning = Boolean(data && (data.is_running || (data.tasks && Object.values(data.tasks).some(t => t.is_running))));
    clearTimeout(_adaptivePollTimer);
    _adaptivePollTimer = setTimeout(runAdaptivePollLoop, isRunning ? 600 : 2500);
    return isRunning;

  } catch (e) {
    console.warn('pollStatus error:', e);
    return false;
  }
}

function getDraftData() {
  return {
    taskActionType: currentTaskActionType,
    taskTarget: document.getElementById('taskTargetSelect')?.value || 'both',
    taskPrompt: document.getElementById('taskPromptInput')?.value || '',
    taskLog: document.getElementById('taskLogInput')?.value || '',
    taskSkills: selectedTaskSkills,
    activeTab: activeTab || 'task',
    savedAt: new Date().toLocaleTimeString('vi-VN')
  };
}

function saveDraft(manual = false) {
  try {
    const data = getDraftData();
    localStorage.setItem(DRAFT_STORAGE_KEY, JSON.stringify(data));
    if (manual) showToast('Đã lưu dữ liệu nháp vào trình duyệt.');
  } catch (err) {
    console.warn('Lỗi khi lưu nháp:', err);
  }
}

function restoreDraft() {
  try {
    const raw = localStorage.getItem(DRAFT_STORAGE_KEY);
    if (!raw) {
      if (!editingTaskId) {
        renderParallelTaskTabs();
      }
      renderFeedFilterTabs();
      updateTaskActionButtons();
      return;
    }
    const draft = JSON.parse(raw);
    if (!draft) {
      if (!editingTaskId) {
        renderParallelTaskTabs();
      }
      renderFeedFilterTabs();
      updateTaskActionButtons();
      return;
    }

    if (draft.taskActionType) {
      setTaskActionType(draft.taskActionType);
    }
    if (draft.taskPrompt) {
      const el = document.getElementById('taskPromptInput');
      if (el && !el.value) el.value = draft.taskPrompt;
    }
    if (draft.taskLog) {
      const el = document.getElementById('taskLogInput');
      if (el && !el.value) el.value = draft.taskLog;
    }
    if (draft.taskTarget) {
      const el = document.getElementById('taskTargetSelect');
      if (el) {
        el.value = draft.taskTarget;
      }
    }
    if (draft.taskSkills && Array.isArray(draft.taskSkills) && draft.taskSkills.length > 0) {
      selectedTaskSkills = draft.taskSkills;
      try {
        localStorage.setItem('easysalon_selected_skills', JSON.stringify(selectedTaskSkills));
      } catch (e) { }
    } else {
      try {
        const savedSkills = localStorage.getItem('easysalon_selected_skills');
        if (savedSkills) {
          const arr = JSON.parse(savedSkills);
          if (Array.isArray(arr) && arr.length > 0) {
            selectedTaskSkills = arr;
          }
        }
      } catch (e) { }
    }
    renderSkillPicker('task');
    updateFixBugPromptPreview();
    syncFormToCurrentTask();
    if (!editingTaskId) {
      renderParallelTaskTabs();
    }
    renderFeedFilterTabs();
    updateTaskActionButtons();
  } catch (err) {
    console.warn('Lỗi phục hồi bản nháp:', err);
    if (!editingTaskId) {
      renderParallelTaskTabs();
    }
    renderFeedFilterTabs();
    updateTaskActionButtons();
  }
}

let _isEditorDirty = false;
let _fileEditorListenersSetup = false;
let _currentEditorFile = null;
let _currentEditorRepo = 'fe';
let _currentEditorMtime = 0;
let _currentEditorContent = '';
let _currentEditorBlame = null;
let _gitLensHideTimer = null;
let _currentActiveLineNumber = 1;
let _fileEditorSyncTimer = null;
let _isCheckingFileStat = false;
let _editorCharWidth = 7.22;
let _currentEditorAbsPath = '';
let _minimapClickListenerSetup = false;

function formatGitLensRelativeTime(timestamp) {
  if (!timestamp) return '';
  const now = Math.floor(Date.now() / 1000);
  const diff = Math.max(0, now - timestamp);
  if (diff < 60) return 'vừa xong';
  const mins = Math.floor(diff / 60);
  if (mins < 60) return `${mins} phút trước`;
  const hours = Math.floor(mins / 60);
  if (hours < 24) return `${hours} giờ trước`;
  const days = Math.floor(hours / 24);
  if (days < 30) return `${days} ngày trước`;
  const months = Math.floor(days / 30);
  if (months < 12) return `${months} tháng trước`;
  const years = Math.floor(months / 12);
  return `${years} năm trước`;
}

function formatGitLensFullDate(timestamp) {
  if (!timestamp) return '';
  const d = new Date(timestamp * 1000);
  const pad = (n) => String(n).padStart(2, '0');
  const day = pad(d.getDate());
  const month = pad(d.getMonth() + 1);
  const year = d.getFullYear();
  const hours = pad(d.getHours());
  const mins = pad(d.getMinutes());
  const secs = pad(d.getSeconds());
  return `${day}/${month}/${year}, ${hours}:${mins}:${secs}`;
}

async function loadFileBlameData(filePath, repo) {
  _currentEditorBlame = null;
  const authorInfoEl = document.getElementById('fileEditorAuthorInfo');
  const inlineBlameEl = document.getElementById('fileEditorInlineBlame');
  if (authorInfoEl) authorInfoEl.innerHTML = '<span class="text-slate-400 font-sans">Đang đọc tác giả...</span>';
  if (inlineBlameEl) inlineBlameEl.textContent = '';

  try {
    const res = await fetch(`/api/file/blame?path=${encodeURIComponent(filePath)}&target=${encodeURIComponent(repo)}`);
    const data = await res.json();
    if (data && data.success) {
      _currentEditorBlame = data;
      renderEditorAuthorInfo();
      updateActiveLineBlame(_currentActiveLineNumber);
    } else {
      if (authorInfoEl) authorInfoEl.innerHTML = '';
    }
  } catch (e) {
    if (authorInfoEl) authorInfoEl.innerHTML = '';
  }
}

function renderEditorAuthorInfo() {
  const authorInfoEl = document.getElementById('fileEditorAuthorInfo');
  if (!authorInfoEl) return;
  if (!_currentEditorBlame) {
    authorInfoEl.innerHTML = '';
    return;
  }

  const { creator, last_modifier } = _currentEditorBlame;
  if (!creator && !last_modifier) {
    authorInfoEl.innerHTML = '<span class="text-slate-400 font-sans">Chưa có lịch sử Git</span>';
    return;
  }

  let html = '';
  if (creator) {
    const cTime = formatGitLensRelativeTime(creator.time);
    const cAuthor = escapeHtml(creator.author || 'Tác giả');
    html += `
      <span class="inline-flex items-center gap-1 cursor-pointer hover:text-sky-300 transition" onclick="showGitLensCommitCard('creator', event)" title="Nhấn xem commit tạo file">
        <svg class="w-3.5 h-3.5 text-sky-400 shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z"/>
        </svg>
        <span>Tạo bởi: <strong class="text-white font-medium">${cAuthor}</strong> <span class="text-slate-400 font-sans">(${cTime})</span></span>
      </span>
    `;
  }

  if (last_modifier) {
    if (creator) {
      html += '<span class="text-slate-500 font-sans">•</span>';
    }
    const mTime = formatGitLensRelativeTime(last_modifier.time);
    const mAuthor = escapeHtml(last_modifier.author || 'Người sửa');
    html += `
      <span class="inline-flex items-center gap-1 cursor-pointer hover:text-sky-300 transition" onclick="showGitLensCommitCard('last_mod', event)" title="Nhấn xem commit sửa gần nhất">
        <span class="text-slate-400 font-sans">Sửa gần nhất:</span>
        <strong class="text-emerald-400 font-medium">${mAuthor}</strong> <span class="text-slate-400 font-sans">(${mTime})</span>
      </span>
    `;
  }

  authorInfoEl.innerHTML = html;
}

function updateActiveLineBlame(lineIndex) {
  const inlineBlameEl = document.getElementById('fileEditorInlineBlame');
  if (!inlineBlameEl) return;

  _currentActiveLineNumber = lineIndex;

  if (!_currentEditorBlame || !_currentEditorBlame.lines || !_currentEditorBlame.lines[lineIndex]) {
    inlineBlameEl.textContent = '';
    return;
  }

  const blame = _currentEditorBlame.lines[lineIndex];
  const author = blame.author || 'You';
  const relTime = formatGitLensRelativeTime(blame.time);
  const summary = blame.summary || 'Uncommitted changes';

  const timePart = relTime ? `, ${relTime}` : '';
  inlineBlameEl.innerHTML = `
    <svg class="w-3 h-3 text-sky-400 shrink-0 inline mr-0.5 opacity-80" fill="none" viewBox="0 0 24 24" stroke="currentColor">
      <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 10V3L4 14h7v7l9-11h-7z" />
    </svg>
    <span>${escapeHtml(author)}${escapeHtml(timePart)} • ${escapeHtml(summary)}</span>
  `;
}

function showGitLensCommitCard(commitKey, event) {
  if (event) {
    event.stopPropagation();
    event.preventDefault();
  }
  cancelHideGitLensCard();

  if (!_currentEditorBlame) return;

  let commit = null;
  if (commitKey === 'creator') {
    commit = _currentEditorBlame.creator;
  } else if (commitKey === 'last_mod') {
    commit = _currentEditorBlame.last_modifier;
  } else if (_currentEditorBlame.commits && _currentEditorBlame.commits[commitKey]) {
    commit = _currentEditorBlame.commits[commitKey];
  } else if (_currentEditorBlame.lines && _currentEditorBlame.lines[commitKey]) {
    const lineObj = _currentEditorBlame.lines[commitKey];
    if (lineObj && lineObj.hash && _currentEditorBlame.commits && _currentEditorBlame.commits[lineObj.hash]) {
      commit = _currentEditorBlame.commits[lineObj.hash];
    } else {
      commit = lineObj;
    }
  }

  if (!commit) return;

  const card = document.getElementById('fileEditorGitLensCard');
  const authorEl = document.getElementById('gitLensCardAuthor');
  const timeEl = document.getElementById('gitLensCardTime');
  const dateEl = document.getElementById('gitLensCardDate');
  const hashEl = document.getElementById('gitLensCardHash');
  const titleEl = document.getElementById('gitLensCardTitle');
  const bodyEl = document.getElementById('gitLensCardBody');
  const emailEl = document.getElementById('gitLensCardEmail');

  if (!card) return;

  const authorName = commit.author || commit.raw_author || 'You';
  const relTime = formatGitLensRelativeTime(commit.time);
  const fullDate = formatGitLensFullDate(commit.time);
  const shortHash = (commit.hash || '').substring(0, 8);

  if (authorEl) authorEl.textContent = authorName;
  if (timeEl) timeEl.textContent = relTime ? `, ${relTime}` : '';
  if (dateEl) dateEl.textContent = fullDate ? ` (${fullDate})` : '';
  if (hashEl) hashEl.textContent = shortHash;
  if (titleEl) titleEl.textContent = commit.summary || commit.title || 'No commit title';
  if (emailEl) emailEl.textContent = commit.email ? `Tác giả: ${commit.email}` : '';

  if (bodyEl) {
    const bodyText = (commit.body || '').trim();
    if (!bodyText) {
      bodyEl.innerHTML = '';
      bodyEl.classList.add('hidden');
    } else {
      bodyEl.classList.remove('hidden');
      const lines = bodyText.split('\n');
      let bodyHtml = '';
      for (const line of lines) {
        const trimmed = line.trim();
        if (!trimmed) continue;
        if (trimmed.startsWith('- ') || trimmed.startsWith('* ') || trimmed.startsWith('• ')) {
          const content = trimmed.replace(/^[-*•]\s*/, '');
          bodyHtml += `<div class="gitlens-bullet-item leading-snug">${escapeHtml(content)}</div>`;
        } else {
          bodyHtml += `<div class="leading-snug">${escapeHtml(trimmed)}</div>`;
        }
      }
      bodyEl.innerHTML = bodyHtml;
    }
  }

  const modalCard = document.getElementById('fileEditorModalCard');
  if (modalCard) {
    const modalRect = modalCard.getBoundingClientRect();
    let left = 20;
    let top = 60;

    if (event && event.currentTarget) {
      const targetRect = event.currentTarget.getBoundingClientRect();
      left = Math.max(10, Math.min(targetRect.left - modalRect.left - 20, modalRect.width - 540));
      top = targetRect.bottom - modalRect.top + 8;
      if (top + 250 > modalRect.height) {
        top = Math.max(10, targetRect.top - modalRect.top - 240);
      }
    } else {
      const activeLine = document.getElementById('fileEditorActiveLineHighlight');
      if (activeLine) {
        const lineRect = activeLine.getBoundingClientRect();
        left = Math.max(10, Math.min(lineRect.right - modalRect.left - 530, modalRect.width - 540));
        top = lineRect.bottom - modalRect.top + 6;
        if (top + 250 > modalRect.height) {
          top = Math.max(10, lineRect.top - modalRect.top - 240);
        }
      }
    }

    card.style.left = `${left}px`;
    card.style.top = `${top}px`;
  }

  card.classList.remove('hidden');
}

function showGitLensForActiveLine(event) {
  showGitLensCommitCard(_currentActiveLineNumber, event);
}

function hideGitLensCard() {
  const card = document.getElementById('fileEditorGitLensCard');
  if (card) card.classList.add('hidden');
}

function scheduleHideGitLensCard() {
  clearTimeout(_gitLensHideTimer);
  _gitLensHideTimer = setTimeout(() => {
    hideGitLensCard();
  }, 300);
}

function cancelHideGitLensCard() {
  clearTimeout(_gitLensHideTimer);
}

window.showGitLensCommitCard = showGitLensCommitCard;
window.showGitLensForActiveLine = showGitLensForActiveLine;
window.hideGitLensCard = hideGitLensCard;

function normalizeRepoRole(r) {
  if (!r) return 'fe';
  const str = String(r).toLowerCase();
  if (str.includes('be') || str.includes('backend') || str.includes('api')) return 'be';
  return 'fe';
}

function getRepoDisplayName(repo) {
  const norm = normalizeRepoRole(repo);
  return norm === 'be' ? 'BACKEND (EASYSALON-API)' : 'FRONTEND (EASYSALON-WEBAPP)';
}

function measureEditorCharWidth() {
  try {
    const span = document.createElement('span');
    span.style.fontFamily = "'JetBrains Mono', Consolas, 'Fira Code', 'Courier New', monospace";
    span.style.fontSize = "12px";
    span.style.visibility = "hidden";
    span.style.position = "absolute";
    span.style.whiteSpace = "pre";
    span.textContent = "1234567890";
    document.body.appendChild(span);
    const rect = span.getBoundingClientRect();
    if (rect.width > 0) {
      _editorCharWidth = rect.width / 10;
    }
    document.body.removeChild(span);
  } catch (e) {
    _editorCharWidth = 7.22;
  }
}

function updateActiveLineHighlight() {
  const textarea = document.getElementById('fileEditorTextarea');
  const highlight = document.getElementById('fileEditorActiveLineHighlight');
  const lineNumbers = document.getElementById('fileEditorLineNumbers');
  if (!textarea || !highlight) return;

  const textBefore = textarea.value.substring(0, textarea.selectionStart);
  const lineIndex = textBefore.split('\n').length - 1;
  const lineHeight = 20;
  const paddingTop = 12; // py-3

  const top = paddingTop + (lineIndex * lineHeight) - textarea.scrollTop;
  highlight.style.top = `${top}px`;
  highlight.style.height = `${lineHeight}px`;

  if (lineNumbers && lineNumbers.children.length > 0) {
    const prevActive = lineNumbers.querySelector('.active-line-num');
    if (prevActive) prevActive.classList.remove('active-line-num');
    const curLineEl = lineNumbers.children[lineIndex];
    if (curLineEl) curLineEl.classList.add('active-line-num');
  }

  updateActiveLineBlame(lineIndex + 1);
}

function updateIndentGuides() {
  const textarea = document.getElementById('fileEditorTextarea');
  const indentLayer = document.getElementById('fileEditorIndentGuides');
  if (!textarea || !indentLayer) return;

  const text = textarea.value;
  const lines = text.split('\n');

  // Detect indent unit (2 or 4 spaces)
  let indentUnit = 2;
  for (let i = 0; i < Math.min(lines.length, 100); i++) {
    const m = lines[i].match(/^([ ]+)[^ ]/);
    if (m) {
      const len = m[1].length;
      if (len === 4 || len === 8) {
        indentUnit = 4;
        break;
      }
    }
  }

  const guideUnit = indentUnit === 4 ? '│   ' : '│ ';
  let html = '';

  for (let i = 0; i < lines.length; i++) {
    const line = lines[i];
    const match = line.match(/^([ \t]*)/);
    const leading = match ? match[1] : '';
    if (!leading) {
      html += '<div class="indent-row"></div>';
      continue;
    }

    let spaceCount = 0;
    for (let c of leading) {
      if (c === '\t') spaceCount += indentUnit;
      else spaceCount += 1;
    }

    const depth = Math.floor(spaceCount / indentUnit);
    if (depth <= 0) {
      html += '<div class="indent-row"></div>';
    } else {
      let rowGuides = '';
      for (let d = 0; d < depth; d++) {
        rowGuides += `<span class="indent-guide">${guideUnit}</span>`;
      }
      html += `<div class="indent-row">${rowGuides}</div>`;
    }
  }

  indentLayer.innerHTML = html;
  indentLayer.scrollTop = textarea.scrollTop;
  indentLayer.scrollLeft = textarea.scrollLeft;
}

function detectFileLanguage(filePath) {
  if (!filePath) return 'text';
  const ext = (filePath.split('.').pop() || '').toLowerCase();
  if (['json', 'jsonc'].includes(ext)) return 'json';
  if (['ts', 'tsx'].includes(ext)) return 'typescript';
  if (['js', 'jsx', 'mjs', 'cjs'].includes(ext)) return 'javascript';
  if (['py'].includes(ext)) return 'python';
  if (['css', 'scss', 'less'].includes(ext)) return 'css';
  if (['html', 'htm', 'vue', 'xml', 'svg'].includes(ext)) return 'html';
  if (['md', 'markdown'].includes(ext)) return 'markdown';
  if (['sh', 'bash', 'env'].includes(ext)) return 'shell';
  if (['sql'].includes(ext)) return 'sql';
  return 'text';
}

function getLanguageDisplayName(filePath) {
  const lang = detectFileLanguage(filePath);
  const map = {
    json: '{ } JSON',
    typescript: 'TypeScript',
    javascript: 'JavaScript',
    python: 'Python',
    css: 'CSS',
    html: 'HTML',
    markdown: 'Markdown',
    shell: 'Shell Script',
    sql: 'SQL',
    text: 'Plain Text'
  };
  return map[lang] || 'Plain Text';
}

function getFileTabIconHtml(filePath) {
  const lang = detectFileLanguage(filePath);
  if (lang === 'json') return '<span class="text-[#e5a00d] font-bold text-xs">{ }</span>';
  if (lang === 'typescript') return '<span class="text-[#3178c6] font-bold text-[11px]">TS</span>';
  if (lang === 'javascript') return '<span class="text-[#f7df1e] font-bold text-[11px]">JS</span>';
  if (lang === 'python') return '<span class="text-[#3572A5] font-bold text-[11px]">Py</span>';
  if (lang === 'css') return '<span class="text-[#38bdf8] font-bold text-xs">#</span>';
  if (lang === 'html') return '<span class="text-[#e34c26] font-bold text-xs">&lt;&gt;</span>';
  if (lang === 'markdown') return '<span class="text-[#38bdf8] font-bold text-xs">M↓</span>';
  return '<span class="text-slate-400 font-bold text-xs">📄</span>';
}

function highlightCode(code, lang) {
  if (!code) return '';
  const lines = code.split('\n');
  return lines.map(line => highlightLine(line, lang)).join('\n');
}

function highlightLine(line, lang) {
  if (!line) return '';
  if (lang === 'json') {
    const regex = /(\/\/[^\n]*)|("(?:\\.|[^"\\])*"(?=\s*:))|("(?:\\.|[^"\\])*")|(\b(?:true|false|null)\b)|(-?\b\d+(?:\.\d+)?(?:[eE][+-]?\d+)?\b)|([{}[\],:])|([^"/\b{}\[\],:\s]+)/g;
    return line.replace(regex, (m, comment, key, str, bool, num, punc) => {
      if (comment) return `<span class="token-comment">${escapeHtml(comment)}</span>`;
      if (key) return `<span class="token-key">${escapeHtml(key)}</span>`;
      if (str) return `<span class="token-string">${escapeHtml(str)}</span>`;
      if (bool) return `<span class="token-boolean">${escapeHtml(bool)}</span>`;
      if (num) return `<span class="token-number">${escapeHtml(num)}</span>`;
      if (punc) {
        if (punc === '{' || punc === '}') return `<span class="token-bracket-gold">${escapeHtml(punc)}</span>`;
        if (punc === '[' || punc === ']') return `<span class="token-bracket-purple">${escapeHtml(punc)}</span>`;
        return `<span class="token-punc">${escapeHtml(punc)}</span>`;
      }
      return escapeHtml(m);
    });
  }

  if (lang === 'typescript' || lang === 'javascript') {
    const regex = /(\/\/[^\n]*)|("(?:\\.|[^"\\])*"|'(?:\\.|[^'\\])*'|`(?:\\.|[^`\\])*`)|(\b(?:import|export|from|as|default|const|let|var|function|return|if|else|switch|case|default|break|continue|for|while|do|try|catch|finally|throw|class|extends|implements|interface|type|enum|new|typeof|instanceof|void|async|await|yield|this|super|public|private|protected|readonly|static)\b)|(\b(?:string|number|boolean|any|unknown|never|symbol|bigint|object|Array|Record|Promise|Map|Set|HTMLElement)\b)|(\b(?:true|false|null|undefined|NaN)\b)|(-?\b\d+(?:\.\d+)?\b)|(\b[a-zA-Z_$][a-zA-Z0-9_$]*(?=\s*\())|([{}()[\]])|([.,;:])|([^"'`/\b{}()[\].,;:\s]+)/g;
    return line.replace(regex, (m, comment, str, kw, type, bool, num, fn, bracket, punc) => {
      if (comment) return `<span class="token-comment">${escapeHtml(comment)}</span>`;
      if (str) return `<span class="token-string">${escapeHtml(str)}</span>`;
      if (kw) return `<span class="token-keyword">${escapeHtml(kw)}</span>`;
      if (type) return `<span class="token-type">${escapeHtml(type)}</span>`;
      if (bool) return `<span class="token-boolean">${escapeHtml(bool)}</span>`;
      if (num) return `<span class="token-number">${escapeHtml(num)}</span>`;
      if (fn) return `<span class="token-function">${escapeHtml(fn)}</span>`;
      if (bracket) {
        if (bracket === '{' || bracket === '}') return `<span class="token-bracket-gold">${escapeHtml(bracket)}</span>`;
        if (bracket === '[' || bracket === ']') return `<span class="token-bracket-purple">${escapeHtml(bracket)}</span>`;
        if (bracket === '(' || bracket === ')') return `<span class="token-bracket-cyan">${escapeHtml(bracket)}</span>`;
      }
      if (punc) return `<span class="token-punc">${escapeHtml(punc)}</span>`;
      return escapeHtml(m);
    });
  }

  if (lang === 'python') {
    const regex = /(#[^\n]*)|("""[\s\S]*?"""|'''[\s\S]*?'''|"(?:\\.|[^"\\])*"|'(?:\\.|[^'\\])*')|(\b(?:def|class|return|if|elif|else|while|for|in|is|not|and|or|import|from|as|try|except|finally|raise|with|lambda|pass|yield|global|nonlocal|assert|async|await)\b)|(\b(?:True|False|None|self|cls)\b)|(@[a-zA-Z0-9_.]+)|(-?\b\d+(?:\.\d+)?\b)|(\b[a-zA-Z_][a-zA-Z0-9_]*(?=\s*\())|([{}()[\]])|([.,;:])|([^"'#\b{}()[\].,;:\s]+)/g;
    return line.replace(regex, (m, comment, str, kw, bool, deco, num, fn, bracket, punc) => {
      if (comment) return `<span class="token-comment">${escapeHtml(comment)}</span>`;
      if (str) return `<span class="token-string">${escapeHtml(str)}</span>`;
      if (kw) return `<span class="token-keyword">${escapeHtml(kw)}</span>`;
      if (bool) return `<span class="token-boolean">${escapeHtml(bool)}</span>`;
      if (deco) return `<span class="token-function">${escapeHtml(deco)}</span>`;
      if (num) return `<span class="token-number">${escapeHtml(num)}</span>`;
      if (fn) return `<span class="token-function">${escapeHtml(fn)}</span>`;
      if (bracket) {
        if (bracket === '{' || bracket === '}') return `<span class="token-bracket-gold">${escapeHtml(bracket)}</span>`;
        if (bracket === '[' || bracket === ']') return `<span class="token-bracket-purple">${escapeHtml(bracket)}</span>`;
        if (bracket === '(' || bracket === ')') return `<span class="token-bracket-cyan">${escapeHtml(bracket)}</span>`;
      }
      if (punc) return `<span class="token-punc">${escapeHtml(punc)}</span>`;
      return escapeHtml(m);
    });
  }

  if (lang === 'css') {
    const regex = /(\/\*[\s\S]*?\*\/)|("(?:\\.|[^"\\])*"|'(?:\\.|[^'\\])*')|(!important|\binherit\b|\binitial\b|\bnone\b|\bblock\b|\bflex\b|\bgrid\b)|(-?\b\d+(?:\.\d+)?(?:px|em|rem|%|vh|vw|ms|s|fr|deg)?\b)|([.#]?[a-zA-Z0-9_-]+(?=\s*[{,]))|([a-zA-Z0-9_-]+(?=\s*:))|([{}()[\];,:])/g;
    return line.replace(regex, (m, comment, str, kw, num, sel, prop, punc) => {
      if (comment) return `<span class="token-comment">${escapeHtml(comment)}</span>`;
      if (str) return `<span class="token-string">${escapeHtml(str)}</span>`;
      if (kw) return `<span class="token-keyword">${escapeHtml(kw)}</span>`;
      if (num) return `<span class="token-number">${escapeHtml(num)}</span>`;
      if (sel) return `<span class="token-function">${escapeHtml(sel)}</span>`;
      if (prop) return `<span class="token-key">${escapeHtml(prop)}</span>`;
      if (punc) return `<span class="token-punc">${escapeHtml(punc)}</span>`;
      return escapeHtml(m);
    });
  }

  if (lang === 'html') {
    const regex = /(<!--[\s\S]*?-->)|(<\/?[a-zA-Z0-9_-]+)|(\s+[a-zA-Z0-9_-]+(?=\s*=))|("(?:\\.|[^"\\])*"|'(?:\\.|[^'\\])*')|([<>/=])/g;
    return line.replace(regex, (m, comment, tag, attr, str, punc) => {
      if (comment) return `<span class="token-comment">${escapeHtml(comment)}</span>`;
      if (tag) return `<span class="token-keyword">${escapeHtml(tag)}</span>`;
      if (attr) return `<span class="token-key">${escapeHtml(attr)}</span>`;
      if (str) return `<span class="token-string">${escapeHtml(str)}</span>`;
      if (punc) return `<span class="token-punc">${escapeHtml(punc)}</span>`;
      return escapeHtml(m);
    });
  }

  const genericRegex = /(\/\/[^\n]*|#[^\n]*)|("(?:\\.|[^"\\])*"|'(?:\\.|[^'\\])*')|(\b(?:true|false|null)\b)|(-?\b\d+(?:\.\d+)?\b)|([{}()[\].,;:])|([^"'#\b{}()[\].,;:\s]+)/g;
  return line.replace(genericRegex, (m, comment, str, bool, num, punc) => {
    if (comment) return `<span class="token-comment">${escapeHtml(comment)}</span>`;
    if (str) return `<span class="token-string">${escapeHtml(str)}</span>`;
    if (bool) return `<span class="token-boolean">${escapeHtml(bool)}</span>`;
    if (num) return `<span class="token-number">${escapeHtml(num)}</span>`;
    if (punc) return `<span class="token-punc">${escapeHtml(punc)}</span>`;
    return escapeHtml(m);
  });
}

function renderSyntaxHighlighting() {
  const textarea = document.getElementById('fileEditorTextarea');
  const codeEl = document.getElementById('fileEditorSyntaxCode');
  const preEl = document.getElementById('fileEditorSyntaxPre');
  if (!textarea || !codeEl) return;

  const code = textarea.value;
  const lang = detectFileLanguage(_currentEditorFile || '');
  codeEl.innerHTML = highlightCode(code, lang) + '\n';
  if (preEl) {
    preEl.scrollTop = textarea.scrollTop;
    preEl.scrollLeft = textarea.scrollLeft;
  }
}

function renderMinimap() {
  const minimapCanvas = document.getElementById('fileEditorMinimapCanvas');
  const textarea = document.getElementById('fileEditorTextarea');
  if (!minimapCanvas || !textarea) return;

  const lines = textarea.value.split('\n');
  const total = Math.min(lines.length, 600);
  let html = '';
  for (let i = 0; i < total; i++) {
    const line = lines[i];
    const trimmed = line.trim();
    if (!trimmed) {
      html += '<div class="minimap-line h-[3px]"></div>';
      continue;
    }
    const indent = line.length - line.trimStart().length;
    const width = Math.min(Math.max(trimmed.length * 1.6, 6), 72);
    let barColor = '#64748b';
    if (trimmed.startsWith('//') || trimmed.startsWith('#') || trimmed.startsWith('/*')) {
      barColor = '#6a9955';
    } else if (trimmed.includes(':') && trimmed.startsWith('"')) {
      barColor = '#9cdcfe';
    } else if (trimmed.includes('import') || trimmed.includes('export') || trimmed.includes('function') || trimmed.includes('def ')) {
      barColor = '#c586c0';
    } else if (trimmed.includes('"') || trimmed.includes("'")) {
      barColor = '#ce9178';
    }
    html += `<div class="minimap-line h-[3px] flex items-center" style="padding-left: ${Math.min(indent * 1.2, 26)}px;">
      <div style="width: ${width}px; background-color: ${barColor};" class="h-[2px] rounded-xs opacity-75"></div>
    </div>`;
  }
  minimapCanvas.innerHTML = html;
  updateMinimapSlider();
}

function updateMinimapSlider() {
  const textarea = document.getElementById('fileEditorTextarea');
  const slider = document.getElementById('fileEditorMinimapSlider');
  const minimap = document.getElementById('fileEditorMinimap');
  if (!textarea || !slider || !minimap) return;

  const scrollHeight = textarea.scrollHeight;
  const clientHeight = textarea.clientHeight;
  if (scrollHeight <= clientHeight) {
    slider.style.display = 'none';
    return;
  }
  slider.style.display = 'block';
  const minimapHeight = minimap.clientHeight;
  const sliderHeight = Math.max((clientHeight / scrollHeight) * minimapHeight, 18);
  const sliderTop = (textarea.scrollTop / (scrollHeight - clientHeight)) * (minimapHeight - sliderHeight);
  slider.style.height = `${sliderHeight}px`;
  slider.style.top = `${sliderTop}px`;
}

function updateCursorPosition() {
  const textarea = document.getElementById('fileEditorTextarea');
  const posEl = document.getElementById('fileEditorCursorPos');
  if (!textarea || !posEl) return;

  const selStart = textarea.selectionStart || 0;
  const textBefore = textarea.value.substring(0, selStart);
  const lines = textBefore.split('\n');
  const lineNum = lines.length;
  const colNum = lines[lines.length - 1].length + 1;
  posEl.textContent = `Ln ${lineNum}, Col ${colNum}`;
}

function setEditorDirty(dirty) {
  _isEditorDirty = Boolean(dirty);
  const statusEl = document.getElementById('fileEditorStatus');
  const statusDirtyEl = document.getElementById('fileEditorDirtyStatus');
  const tabDot = document.getElementById('fileEditorTabDirtyDot');
  const saveBtn = document.getElementById('fileEditorSaveBtn');

  if (dirty) {
    if (statusEl) {
      statusEl.innerHTML = '<span class="text-amber-400 font-semibold font-sans flex items-center gap-1.5"><span class="w-1.5 h-1.5 rounded-full bg-amber-400 animate-pulse"></span>Có thay đổi chưa lưu</span>';
    }
    if (statusDirtyEl) statusDirtyEl.classList.remove('hidden');
    if (tabDot) tabDot.classList.remove('hidden');
    if (saveBtn) {
      saveBtn.classList.remove('bg-[#0e639c]', 'hover:bg-[#1177bb]');
      saveBtn.classList.add('bg-[#1677ff]', 'hover:bg-[#4096ff]', 'ring-2', 'ring-sky-400/50');
    }
  } else {
    if (statusEl) {
      statusEl.innerHTML = '';
    }
    if (statusDirtyEl) statusDirtyEl.classList.add('hidden');
    if (tabDot) tabDot.classList.add('hidden');
    if (saveBtn) {
      saveBtn.classList.add('bg-[#0e639c]', 'hover:bg-[#1177bb]');
      saveBtn.classList.remove('bg-[#1677ff]', 'hover:bg-[#4096ff]', 'ring-2', 'ring-sky-400/50');
    }
  }
}

function checkEditorDirtyState() {
  const textarea = document.getElementById('fileEditorTextarea');
  if (!textarea) return;
  const isChanged = textarea.value !== _currentEditorContent;
  setEditorDirty(isChanged);
}

function openInNativeVSCode() {
  if (_currentEditorAbsPath) {
    window.location.href = `vscode://file/${encodeURI(_currentEditorAbsPath)}`;
  } else if (_currentEditorFile) {
    showToast(`Đường dẫn file: ${_currentEditorFile}`);
  }
}
window.openInNativeVSCode = openInNativeVSCode;

function updateEditorLineNumbers() {
  const textarea = document.getElementById('fileEditorTextarea');
  const lineNumbers = document.getElementById('fileEditorLineNumbers');
  const lineCountEl = document.getElementById('fileEditorLineCount');
  if (!textarea || !lineNumbers) return;

  const lines = textarea.value.split('\n');
  const count = lines.length;
  if (lineCountEl) lineCountEl.textContent = `${count} dòng`;

  let html = '';
  for (let i = 1; i <= count; i++) {
    html += `<span class="line-num" data-line="${i}">${i}</span>`;
  }
  lineNumbers.innerHTML = html;
  lineNumbers.scrollTop = textarea.scrollTop;
  updateIndentGuides();
  updateActiveLineHighlight();
  renderSyntaxHighlighting();
  renderMinimap();
}

function startFileEditorWatch() {
  stopFileEditorWatch();
  _fileEditorSyncTimer = setInterval(() => {
    checkFileExternalChanges();
  }, 1200);
}

function stopFileEditorWatch() {
  if (_fileEditorSyncTimer) {
    clearInterval(_fileEditorSyncTimer);
    _fileEditorSyncTimer = null;
  }
}

async function checkFileExternalChanges() {
  if (!_currentEditorFile || _isCheckingFileStat) return;
  const modal = document.getElementById('fileEditorModalRoot');
  if (!modal || modal.classList.contains('hidden')) return;

  _isCheckingFileStat = true;
  try {
    const res = await fetch(`/api/file/stat?path=${encodeURIComponent(_currentEditorFile)}&target=${encodeURIComponent(_currentEditorRepo)}`);
    const data = await res.json();
    if (!data || !data.success) return;

    if (_currentEditorMtime && data.mtime && Math.abs(data.mtime - _currentEditorMtime) > 0.05) {
      if (!_isEditorDirty) {
        const contentRes = await fetch(`/api/file/content?path=${encodeURIComponent(_currentEditorFile)}&target=${encodeURIComponent(_currentEditorRepo)}`);
        const contentData = await contentRes.json();
        if (contentData && contentData.success) {
          const textarea = document.getElementById('fileEditorTextarea');
          const statusEl = document.getElementById('fileEditorStatus');
          if (textarea) {
            const curSelStart = textarea.selectionStart;
            const curSelEnd = textarea.selectionEnd;
            const curScrollTop = textarea.scrollTop;

            _currentEditorMtime = contentData.mtime || data.mtime;
            _currentEditorContent = contentData.content != null ? contentData.content : '';
            textarea.value = _currentEditorContent;
            _isEditorDirty = false;

            updateEditorLineNumbers();
            loadFileBlameData(_currentEditorFile, _currentEditorRepo);

            textarea.scrollTop = curScrollTop;
            textarea.selectionStart = Math.min(curSelStart, textarea.value.length);
            textarea.selectionEnd = Math.min(curSelEnd, textarea.value.length);

            const nowTime = new Date().toLocaleTimeString('vi-VN');
            if (statusEl) {
              statusEl.innerHTML = `<span class="text-emerald-400 font-semibold font-sans">⚡ Đã tự động cập nhật từ VS Code (${nowTime})</span>`;
              setTimeout(() => {
                if (!_isEditorDirty && statusEl) {
                  statusEl.innerHTML = '<span class="text-slate-300 font-sans">Sẵn sàng sửa code (Ctrl+S để lưu)</span>';
                }
              }, 3000);
            }
          }
        }
      } else {
        const statusEl = document.getElementById('fileEditorStatus');
        if (statusEl) {
          statusEl.innerHTML = `
            <span class="text-amber-400 font-semibold font-sans">⚠️ File trên đĩa đã đổi ngoài VS Code!</span>
            <button type="button" onclick="reloadFileFromDisk()" class="ml-1 underline text-sky-400 hover:text-sky-300 font-sans text-[11px] cursor-pointer">Tải lại từ đĩa</button>
          `;
        }
      }
    }
  } catch (e) {
    // ignore
  } finally {
    _isCheckingFileStat = false;
  }
}

async function reloadFileFromDisk() {
  if (!_currentEditorFile) return;
  try {
    const res = await fetch(`/api/file/content?path=${encodeURIComponent(_currentEditorFile)}&target=${encodeURIComponent(_currentEditorRepo)}`);
    const data = await res.json();
    if (data && data.success) {
      const textarea = document.getElementById('fileEditorTextarea');
      const statusEl = document.getElementById('fileEditorStatus');
      if (textarea) {
        _currentEditorMtime = data.mtime || Date.now();
        _currentEditorContent = data.content != null ? data.content : '';
        textarea.value = _currentEditorContent;
        _isEditorDirty = false;
        updateEditorLineNumbers();
        loadFileBlameData(_currentEditorFile, _currentEditorRepo);
        if (statusEl) {
          statusEl.innerHTML = '<span class="text-emerald-400 font-semibold font-sans">✓ Đã tải lại nội dung mới nhất từ đĩa</span>';
          setTimeout(() => {
            if (!_isEditorDirty && statusEl) {
              statusEl.innerHTML = '<span class="text-slate-300 font-sans">Sẵn sàng sửa code (Ctrl+S để lưu)</span>';
            }
          }, 2500);
        }
      }
    }
  } catch (err) {
    showToast(`Không thể tải lại: ${err.message}`, 'error');
  }
}
window.reloadFileFromDisk = reloadFileFromDisk;

function setupFileEditorListeners() {
  if (_fileEditorListenersSetup) return;
  const textarea = document.getElementById('fileEditorTextarea');
  const lineNumbers = document.getElementById('fileEditorLineNumbers');
  const modalRoot = document.getElementById('fileEditorModalRoot');

  if (textarea) {
    _fileEditorListenersSetup = true;

    measureEditorCharWidth();
    textarea.style.setProperty('--char-w', `${_editorCharWidth}px`);

    textarea.addEventListener('scroll', () => {
      if (lineNumbers) {
        lineNumbers.scrollTop = textarea.scrollTop;
      }
      const indentLayer = document.getElementById('fileEditorIndentGuides');
      if (indentLayer) {
        indentLayer.scrollTop = textarea.scrollTop;
        indentLayer.scrollLeft = textarea.scrollLeft;
      }
      const syntaxPre = document.getElementById('fileEditorSyntaxPre');
      if (syntaxPre) {
        syntaxPre.scrollTop = textarea.scrollTop;
        syntaxPre.scrollLeft = textarea.scrollLeft;
      }
      hideGitLensCard();
      updateActiveLineHighlight();
      updateMinimapSlider();
    });

    textarea.addEventListener('click', () => {
      hideGitLensCard();
      updateActiveLineHighlight();
      updateCursorPosition();
    });

    textarea.addEventListener('keyup', (e) => {
      if (['ArrowUp', 'ArrowDown', 'ArrowLeft', 'ArrowRight', 'Home', 'End', 'PageUp', 'PageDown'].includes(e.key)) {
        updateActiveLineHighlight();
      }
      updateCursorPosition();
    });

    textarea.addEventListener('input', () => {
      updateEditorLineNumbers();
      checkEditorDirtyState();
      renderSyntaxHighlighting();
      renderMinimap();
      updateActiveLineHighlight();
      updateCursorPosition();
    });

    textarea.addEventListener('keydown', (e) => {
      if (e.key === 'Escape') {
        e.preventDefault();
        closeFileEditor();
        return;
      }
      if ((e.ctrlKey || e.metaKey) && (e.key === 's' || e.key === 'S')) {
        e.preventDefault();
        saveActiveFileEditor();
        return;
      }
      if (e.key === 'Tab') {
        e.preventDefault();
        const start = textarea.selectionStart;
        const end = textarea.selectionEnd;
        const val = textarea.value;

        if (!e.shiftKey) {
          textarea.value = val.substring(0, start) + '  ' + val.substring(end);
          textarea.selectionStart = textarea.selectionEnd = start + 2;
        } else {
          const lineStart = val.lastIndexOf('\n', start - 1) + 1;
          if (val.substring(lineStart, lineStart + 2) === '  ') {
            textarea.value = val.substring(0, lineStart) + val.substring(lineStart + 2);
            textarea.selectionStart = textarea.selectionEnd = Math.max(lineStart, start - 2);
          }
        }
        updateEditorLineNumbers();
        checkEditorDirtyState();
        renderSyntaxHighlighting();
        renderMinimap();
        updateActiveLineHighlight();
        updateCursorPosition();
      }
    });

    const minimap = document.getElementById('fileEditorMinimap');
    if (minimap && !_minimapClickListenerSetup) {
      _minimapClickListenerSetup = true;
      minimap.addEventListener('click', (e) => {
        const rect = minimap.getBoundingClientRect();
        const clickY = e.clientY - rect.top;
        const ratio = Math.max(0, Math.min(1, clickY / rect.height));
        textarea.scrollTop = ratio * (textarea.scrollHeight - textarea.clientHeight);
      });
    }

    const inlineBlameEl = document.getElementById('fileEditorInlineBlame');
    if (inlineBlameEl) {
      inlineBlameEl.addEventListener('mouseenter', (e) => {
        showGitLensForActiveLine(e);
      });
      inlineBlameEl.addEventListener('mouseleave', () => {
        scheduleHideGitLensCard();
      });
      inlineBlameEl.addEventListener('click', (e) => {
        showGitLensForActiveLine(e);
      });
    }

    const gitLensCard = document.getElementById('fileEditorGitLensCard');
    if (gitLensCard) {
      gitLensCard.addEventListener('mouseenter', () => {
        cancelHideGitLensCard();
      });
      gitLensCard.addEventListener('mouseleave', () => {
        scheduleHideGitLensCard();
      });
    }
  }

  if (modalRoot) {
    modalRoot.addEventListener('click', (e) => {
      if (e.target === modalRoot) {
        closeFileEditor();
      }
    });
  }
}

function setupAutoSaveAndKeybindings() {
  setupFileEditorListeners();

  window.addEventListener('focus', () => {
    const fileModal = document.getElementById('fileEditorModalRoot');
    if (fileModal && !fileModal.classList.contains('hidden')) {
      checkFileExternalChanges();
    }
    if (typeof activeTab !== 'undefined' && activeTab === 'branch') {
      if (typeof checkSyncPullUpdates === 'function') {
        checkSyncPullUpdates(false);
      }
    }
  });

  window.addEventListener('keydown', (e) => {
    const fileModal = document.getElementById('fileEditorModalRoot');
    if (fileModal && !fileModal.classList.contains('hidden')) {
      if (e.key === 'Escape') {
        e.preventDefault();
        closeFileEditor();
        return;
      }
      if ((e.ctrlKey || e.metaKey) && (e.key === 's' || e.key === 'S')) {
        e.preventDefault();
        saveActiveFileEditor();
        return;
      }
    }
    if ((e.ctrlKey || e.metaKey) && (e.key === 's' || e.key === 'S')) {
      e.preventDefault();
      saveDraft(true);
    }
  });

  const watchSelectors = [
    '#taskPromptInput', '#taskTargetSelect', '#taskLogInput'
  ];
  watchSelectors.forEach(sel => {
    const el = document.querySelector(sel);
    if (el) {
      el.addEventListener('input', () => saveDraft(false));
      el.addEventListener('change', () => saveDraft(false));
    }
  });
}

async function openFileEditor(filePath, repo = 'fe') {
  if (!filePath) return;
  setupFileEditorListeners();
  _currentEditorFile = filePath;
  _currentEditorRepo = normalizeRepoRole(repo);
  _isEditorDirty = false;
  _currentEditorAbsPath = '';

  const modal = document.getElementById('fileEditorModalRoot');
  const pathEl = document.getElementById('fileEditorFilePath');
  const badgeEl = document.getElementById('fileEditorRepoBadge');
  const lineCountEl = document.getElementById('fileEditorLineCount');
  const statusEl = document.getElementById('fileEditorStatus');
  const textarea = document.getElementById('fileEditorTextarea');
  const windowTitleEl = document.getElementById('fileEditorWindowTitle');
  const tabIconEl = document.getElementById('fileEditorTabIcon');
  const tabFileNameEl = document.getElementById('fileEditorTabFileName');
  const breadcrumbEl = document.getElementById('fileEditorBreadcrumbPath');
  const statusRepoEl = document.getElementById('fileEditorStatusRepo');
  const statusBranchEl = document.getElementById('fileEditorStatusBranch');
  const langBadgeEl = document.getElementById('fileEditorLangBadge');

  if (!modal || !textarea) return;

  const fileName = filePath.split('/').pop() || filePath;
  if (windowTitleEl) {
    windowTitleEl.textContent = `${fileName} - ${getRepoDisplayName(_currentEditorRepo)} - EasySalon Studio`;
  }
  if (tabIconEl) {
    tabIconEl.innerHTML = getFileTabIconHtml(filePath);
  }
  if (tabFileNameEl) {
    tabFileNameEl.textContent = fileName;
  }
  if (breadcrumbEl) {
    const parts = filePath.split('/');
    breadcrumbEl.innerHTML = parts.map((p, idx) => {
      const isLast = idx === parts.length - 1;
      return `<span class="${isLast ? 'text-slate-100 font-medium' : 'text-slate-400'}">${escapeHtml(p)}</span>`;
    }).join(' <span class="text-[#555555] mx-0.5">›</span> ');
  }
  if (statusRepoEl) {
    statusRepoEl.textContent = getRepoDisplayName(_currentEditorRepo);
  }
  if (statusBranchEl) {
    const branch = (_currentEditorRepo === 'fe' ? (window.gitFeStatus?.branch || 'HEAD') : (window.gitBeStatus?.branch || 'HEAD'));
    statusBranchEl.textContent = branch;
  }
  if (langBadgeEl) {
    langBadgeEl.textContent = getLanguageDisplayName(filePath);
  }

  setEditorDirty(false);

  measureEditorCharWidth();
  textarea.style.setProperty('--char-w', `${_editorCharWidth}px`);

  if (pathEl) pathEl.textContent = filePath;
  if (badgeEl) badgeEl.textContent = getRepoDisplayName(_currentEditorRepo);
  if (lineCountEl) lineCountEl.textContent = 'Đang đọc...';
  if (statusEl) statusEl.textContent = 'Đang tải file từ máy chủ...';
  textarea.value = 'Đang tải toàn bộ nội dung file...';
  textarea.disabled = true;

  modal.classList.remove('hidden');

  try {
    const res = await fetch(`/api/file/content?path=${encodeURIComponent(filePath)}&target=${encodeURIComponent(_currentEditorRepo)}`);
    const data = await res.json();

    if (!data.success) {
      textarea.value = `// Không thể tải file: ${data.message || 'Lỗi không xác định'}\n// Đường dẫn: ${filePath}`;
      textarea.disabled = false;
      if (statusEl) statusEl.textContent = 'Lỗi tải file';
      if (lineCountEl) lineCountEl.textContent = '0 dòng';
      updateEditorLineNumbers();
      return;
    }

    const content = (data.content != null ? data.content : '').replace(/\r\n/g, '\n');
    _currentEditorAbsPath = data.abs_path || '';
    textarea.value = content;
    textarea.disabled = false;
    _isEditorDirty = false;
    _currentEditorContent = content;
    _currentEditorMtime = data.mtime || 0;

    if (data.target) {
      _currentEditorRepo = normalizeRepoRole(data.target);
      if (badgeEl) badgeEl.textContent = getRepoDisplayName(_currentEditorRepo);
      if (statusRepoEl) statusRepoEl.textContent = getRepoDisplayName(_currentEditorRepo);
    }
    setEditorDirty(false);
    updateEditorLineNumbers();
    updateCursorPosition();
    if (statusEl) statusEl.innerHTML = '';

    loadFileBlameData(filePath, _currentEditorRepo);
    startFileEditorWatch();

    setTimeout(() => {
      textarea.focus();
      updateActiveLineHighlight();
    }, 50);
  } catch (err) {
    textarea.value = `// Lỗi mạng: ${err.message}\n// Đường dẫn: ${filePath}`;
    textarea.disabled = false;
    if (statusEl) statusEl.textContent = 'Lỗi kết nối';
    updateEditorLineNumbers();
  }
}

async function saveActiveFileEditor() {
  if (!_currentEditorFile) return;

  const textarea = document.getElementById('fileEditorTextarea');
  const statusEl = document.getElementById('fileEditorStatus');
  const saveBtn = document.getElementById('fileEditorSaveBtn');

  if (!textarea) return;

  const content = textarea.value;
  if (statusEl) statusEl.innerHTML = '<span class="text-cyan-400 font-sans">Đang lưu vào máy chủ...</span>';
  if (saveBtn) {
    saveBtn.disabled = true;
    saveBtn.classList.add('opacity-70');
  }

  try {
    const res = await fetch('/api/file/save', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        path: _currentEditorFile,
        target: normalizeRepoRole(_currentEditorRepo),
        content: content
      })
    });
    const data = await res.json();

    if (data.success) {
      _isEditorDirty = false;
      _currentEditorContent = content;
      if (data.mtime) {
        _currentEditorMtime = data.mtime;
      }
      setEditorDirty(false);
      loadFileBlameData(_currentEditorFile, _currentEditorRepo);
      if (statusEl) statusEl.innerHTML = '<span class="text-emerald-400 font-semibold font-sans">✓ Đã lưu thành công</span>';
      showToast(`Đã lưu file ${_currentEditorFile}`, 'success');
      setTimeout(() => {
        if (!_isEditorDirty && statusEl) {
          statusEl.innerHTML = '';
        }
      }, 2500);
    } else {
      if (statusEl) statusEl.innerHTML = `<span class="text-rose-400 font-semibold font-sans">✕ Lỗi: ${escapeHtml(data.message || 'Lỗi khi lưu')}</span>`;
      showToast(`Lỗi khi lưu file: ${data.message}`, 'error');
    }
  } catch (err) {
    if (statusEl) statusEl.innerHTML = `<span class="text-rose-400 font-semibold font-sans">✕ Lỗi mạng: ${escapeHtml(err.message)}</span>`;
    showToast(`Lỗi kết nối khi lưu: ${err.message}`, 'error');
  } finally {
    if (saveBtn) {
      saveBtn.disabled = false;
      saveBtn.classList.remove('opacity-70');
    }
  }
}

async function closeFileEditor() {
  if (_isEditorDirty) {
    const conf = await antdConfirm({
      title: 'Đóng trình chỉnh sửa?',
      content: 'Bạn có thay đổi chưa lưu trên file này. Bạn có chắc chắn muốn đóng mà không lưu?',
      danger: true,
      okText: 'Đóng không lưu',
      cancelText: 'Tiếp tục sửa'
    });
    if (!conf) return;
  }
  hideGitLensCard();
  stopFileEditorWatch();
  const modal = document.getElementById('fileEditorModalRoot');
  if (modal) modal.classList.add('hidden');
  _currentEditorFile = null;
  _currentEditorContent = '';
  _currentEditorMtime = 0;
  _currentEditorBlame = null;
  _currentEditorAbsPath = '';
  setEditorDirty(false);
}

window.openFileEditor = openFileEditor;
window.saveActiveFileEditor = saveActiveFileEditor;
window.closeFileEditor = closeFileEditor;

let _adaptivePollTimer = null;
let _isPollingInProgress = false;

async function runAdaptivePollLoop() {
  if (_isPollingInProgress) return;
  _isPollingInProgress = true;
  let isRunning = false;
  try {
    if (activeTab === 'task') {
      isRunning = await pollStatus();
    } else if (activeTab === 'log') {
      await loadWorkLogs(false);
    }
  } catch (err) {
    console.warn('adaptive poll loop error:', err);
  } finally {
    _isPollingInProgress = false;
    clearTimeout(_adaptivePollTimer);
    const interval = isRunning ? 600 : 2500;
    _adaptivePollTimer = setTimeout(runAdaptivePollLoop, interval);
  }
}

function triggerImmediatePoll() {
  clearTimeout(_adaptivePollTimer);
  runAdaptivePollLoop();
}
