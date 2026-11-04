let cachedLogs = [];
let currentLogFilter = 'all';
let expandedLogIds = new Set();
let lastLogsSignature = '';

async function loadWorkLogs(force = false) {
  const container = document.getElementById('logListContainer');
  if (!container) return;
  try {
    const res = await fetch('/api/logs');
    const data = await res.json();
    const logsList = Array.isArray(data) ? data : [];
    const newSignature = logsList.length + '_' + (logsList[0]?.id || logsList[0]?.timestamp || logsList[0]?.created_at || '');

    if (!force && newSignature === lastLogsSignature) {
      return;
    }
    lastLogsSignature = newSignature;
    cachedLogs = logsList;
    if (activeTab === 'log') {
      renderFilteredLogs();
    }
  } catch (err) {
    if (!cachedLogs || cachedLogs.length === 0) {
      container.innerHTML = `<div class="p-8 text-center text-cyan-400 text-xs">Lỗi tải nhật ký: ${escapeHtml(err.message)}</div>`;
    }
  }
}

function setLogTypeFilter(filterType) {
  currentLogFilter = filterType;
  const isLight = document.body.classList.contains('light-mode');
  const activeCls = 'active-log-filter px-2.5 py-1 rounded bg-[rgb(25,156,255)] text-white font-bold text-xs shadow-sm cursor-pointer select-none';
  const inactiveCls = isLight
    ? 'px-2.5 py-1 rounded text-slate-600 hover:text-slate-900 text-xs transition cursor-pointer select-none'
    : 'px-2.5 py-1 rounded text-slate-300 hover:text-white text-xs transition cursor-pointer select-none';

  ['all', 'TASK', 'GIT'].forEach(t => {
    const btn = document.getElementById('logFilter_' + t);
    if (btn) {
      if (t === filterType) {
        btn.className = activeCls;
      } else {
        btn.className = inactiveCls;
      }
    }
  });
  renderFilteredLogs();
}

function renderFilteredLogs() {
  const container = document.getElementById('logListContainer');
  const searchInput = document.getElementById('logSearchInput');
  if (!container) return;

  const q = (searchInput?.value || '').toLowerCase().trim();

  const filtered = cachedLogs.filter(item => {
    const itemType = (item.type || (item.turns ? 'MULTI_TURN_DISCUSSION' : (item.target ? 'TASK' : 'OTHER'))).toUpperCase();
    if (currentLogFilter === 'TASK') {
      if (itemType.startsWith('GIT_')) return false;
    } else if (currentLogFilter === 'GIT') {
      if (!itemType.startsWith('GIT_')) return false;
    }

    if (!q) return true;
    const typeLabel = itemType === 'GIT_SYNC_PULL' ? 'đồng bộ git pull' : (itemType === 'GIT_SWITCH' ? 'chuyển nhánh' : (itemType.includes('MERGE') ? 'git merge gộp nhánh' : (itemType.includes('CHERRY') ? 'cherry-pick cherry pick' : '')));
    const text = `${item.title || ''} ${item.prompt || ''} ${item.topic || ''} ${item.task || ''} ${item.details || ''} ${item.result || ''} ${item.content || ''} ${item.reply || ''} ${item.target || ''} ${item.created_at || ''} ${typeLabel}`.toLowerCase();
    return text.includes(q);
  });

  if (filtered.length === 0) {
    container.innerHTML = `
          <div class="bg-[#13223f] border border-[#244170] rounded-lg p-12 text-center text-slate-400">
            <svg class="w-10 h-10 mx-auto text-slate-500 mb-3" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
            </svg>
            <div class="text-sm font-medium text-slate-300">Không tìm thấy bản ghi log nào</div>
            <p class="text-xs text-slate-500 mt-1">Các phiên làm việc hoặc thao tác Git sẽ tự động được ghi lại tại đây.</p>
          </div>
        `;
    return;
  }

  container.innerHTML = filtered.map((item, idx) => renderLogItemHtml(item, idx)).join('');
}

function formatLogTime(raw) {
  if (!raw) return '';
  if (raw.includes(' - ') && raw.length <= 25) return raw;
  try {
    const d = new Date(raw);
    if (!isNaN(d.getTime())) {
      const hh = String(d.getHours()).padStart(2, '0');
      const mm = String(d.getMinutes()).padStart(2, '0');
      const ss = String(d.getSeconds()).padStart(2, '0');
      const dd = String(d.getDate()).padStart(2, '0');
      const MM = String(d.getMonth() + 1).padStart(2, '0');
      const yyyy = d.getFullYear();
      return `${hh}:${mm}:${ss} - ${dd}/${MM}/${yyyy}`;
    }
  } catch (e) { }
  return raw;
}

function renderLogItemHtml(item, idx) {
  const id = item.id || `log_${idx}`;
  const rawType = (item.type || (item.turns ? 'MULTI_TURN_DISCUSSION' : (item.target ? 'TASK' : 'OTHER'))).toUpperCase();
  const title = item.title || item.prompt || item.topic || item.task || (item.content ? item.content.slice(0, 100) : 'Phiên làm việc');
  const rawCreatedAt = item.created_at || item.timestamp || '';
  const createdAt = formatLogTime(rawCreatedAt);
  const status = (item.status || 'SUCCESS').toUpperCase();
  const duration = item.duration_sec ? formatDuration(item.duration_sec) : '';
  const target = item.target || (item.from ? `${item.from}->${item.to}` : '');

  let typeBadge = '';
  if (rawType === 'TASK') {
    typeBadge = '<span class="px-2 py-0.5 rounded text-[11px] font-semibold bg-[#182c4f] border border-[#2e528f] text-cyan-300">Tác vụ</span>';
  } else if (rawType === 'FIX_BUG') {
    typeBadge = '<span class="px-2 py-0.5 rounded text-[11px] font-semibold bg-[#13223f] border border-cyan-800 text-cyan-300">Fix Bug</span>';
  } else if (rawType === 'GIT_SYNC_PULL') {
    typeBadge = '<span class="badge-git-sync-pull px-2 py-0.5 rounded text-[11px] font-semibold">Đồng bộ Git (Pull)</span>';
  } else if (rawType === 'GIT_SWITCH' || rawType === 'GIT_PULL') {
    typeBadge = `<span class="px-2 py-0.5 rounded text-[11px] font-semibold bg-purple-950/80 border border-purple-800 text-purple-300">${rawType === 'GIT_PULL' ? 'Git Pull' : 'Chuyển Nhánh'}</span>`;
  } else if (rawType === 'GIT_PUSH') {
    typeBadge = '<span class="px-2 py-0.5 rounded text-[11px] font-semibold bg-emerald-950/80 border border-emerald-800 text-emerald-300">Git Push</span>';
  } else if (rawType === 'GIT_MERGE') {
    typeBadge = '<span class="px-2 py-0.5 rounded text-[11px] font-semibold bg-blue-950/80 border border-blue-800 text-blue-300">Git Merge</span>';
  } else if (rawType === 'GIT_MERGE_CONTINUE') {
    typeBadge = '<span class="px-2 py-0.5 rounded text-[11px] font-semibold bg-blue-950/80 border border-blue-800 text-blue-300">Tiếp Tục Merge</span>';
  } else if (rawType === 'GIT_CHERRY_PICK') {
    typeBadge = '<span class="px-2 py-0.5 rounded text-[11px] font-semibold bg-indigo-950/80 border border-indigo-800 text-indigo-300">Cherry-Pick</span>';
  } else if (rawType === 'GIT_CHERRY_PICK_ABORT' || rawType === 'GIT_MERGE_ABORT') {
    typeBadge = '<span class="px-2 py-0.5 rounded text-[11px] font-semibold bg-rose-950/80 border border-rose-800 text-rose-300">Hủy Thao Tác</span>';
  } else if (rawType === 'GIT_CHERRY_PICK_CONTINUE') {
    typeBadge = '<span class="px-2 py-0.5 rounded text-[11px] font-semibold bg-emerald-950/80 border border-emerald-800 text-emerald-300">Tiếp Tục Cherry-Pick</span>';
  } else if (['MULTI_TURN_DISCUSSION', 'AUTONOMOUS_CALL', 'COMMUNICATION'].includes(rawType) || item.from) {
    typeBadge = '<span class="px-2 py-0.5 rounded text-[11px] font-semibold bg-[#182c4f] border border-cyan-700 text-cyan-300">Trao đổi FE ↔ BE</span>';
  } else {
    typeBadge = `<span class="px-2 py-0.5 rounded text-[11px] font-semibold bg-slate-800 text-slate-300">${escapeHtml(rawType)}</span>`;
  }

  let targetBadge = '';
  if (target === 'fe') {
    targetBadge = '<span class="px-1.5 py-0.5 rounded text-[10px] font-mono bg-cyan-950/70 border border-cyan-800 text-cyan-400">FE</span>';
  } else if (target === 'be') {
    targetBadge = '<span class="px-1.5 py-0.5 rounded text-[10px] font-mono bg-emerald-950/70 border border-emerald-800 text-emerald-400">BE</span>';
  } else if (target === 'both') {
    targetBadge = '<span class="px-1.5 py-0.5 rounded text-[10px] font-mono bg-indigo-950/70 border border-indigo-800 text-indigo-300">FE & BE</span>';
  } else if (item.from && item.to) {
    targetBadge = `<span class="px-1.5 py-0.5 rounded text-[10px] font-mono bg-indigo-950/70 border border-indigo-800 text-indigo-300">${item.from.toUpperCase()} → ${item.to.toUpperCase()}</span>`;
  }

  let statusBadge = '';
  if (status === 'SUCCESS' || status === 'COMPLETED') {
    statusBadge = '<span class="inline-flex items-center gap-1 text-[11px] text-emerald-400 font-medium"><span class="w-1.5 h-1.5 rounded-full bg-emerald-400"></span> Hoàn tất</span>';
  } else if (status === 'RUNNING') {
    statusBadge = '<span class="inline-flex items-center gap-1 text-[11px] text-cyan-400 font-medium"><span class="w-1.5 h-1.5 rounded-full bg-cyan-400 animate-ping"></span> Đang chạy</span>';
  } else {
    statusBadge = '<span class="inline-flex items-center gap-1 text-[11px] text-amber-400 font-medium"><span class="w-1.5 h-1.5 rounded-full bg-amber-400"></span> ' + escapeHtml(status) + '</span>';
  }

  const hasDetails = Boolean(item.details || item.result || item.content || item.reply || (item.turns && item.turns.length > 0));
  const isExpanded = expandedLogIds.has(String(id));

  return `
        <div id="logItemCard_${escapeHtml(id)}" class="log-item-card ${isExpanded ? 'log-item-active' : ''} bg-[#13223f] border border-[#244170] rounded-lg p-4 shadow-sm transition">
          <div class="flex items-center justify-between gap-3">
            <div class="flex-1 min-w-0 cursor-pointer" onclick="toggleLogDetails('${escapeHtml(id)}')">
              <div class="flex flex-wrap items-center gap-2 mb-1.5">
                ${typeBadge}
                ${targetBadge}
                ${statusBadge}
              </div>
              <div class="text-sm font-semibold text-white hover:text-cyan-300 transition truncate">
                ${escapeHtml(title)}
              </div>
            </div>
            <div class="flex items-center gap-2.5 shrink-0">
              <span class="text-[11px] text-slate-300 font-mono select-none">${escapeHtml(createdAt)} ${duration ? '• ' + duration : ''}</span>
              <button type="button" onclick="deleteSingleLogItem('${escapeHtml(id)}', event)"
                class="log-item-delete-btn p-1.5 bg-[#ef4444] hover:bg-red-600 text-white rounded transition cursor-pointer flex items-center justify-center shadow-sm"
                title="Xóa bản ghi lịch sử này">
                <svg class="w-3.5 h-3.5 fill-none stroke-white" viewBox="0 0 24 24" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                  <polyline points="3 6 5 6 21 6"></polyline>
                  <path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"></path>
                  <line x1="10" y1="11" x2="10" y2="17"></line>
                  <line x1="14" y1="11" x2="14" y2="17"></line>
                </svg>
              </button>
              ${hasDetails ? `
                <div class="p-1.5 text-slate-400 hover:text-white rounded text-xs cursor-pointer flex items-center justify-center" onclick="toggleLogDetails('${escapeHtml(id)}')">
                  <svg id="logIcon_${escapeHtml(id)}" class="w-4 h-4 transform transition-transform ${isExpanded ? 'rotate-180' : ''}" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 9l-7 7-7-7" />
                  </svg>
                </div>
              ` : ''}
            </div>
          </div>

          ${hasDetails ? `
            <div id="logDetail_${escapeHtml(id)}" class="${isExpanded ? '' : 'hidden'} mt-3 pt-3 border-t border-[#244170] text-xs">
              ${item.prompt && item.prompt !== title ? `<div class="mb-2 text-slate-300 font-medium"><b>Yêu cầu:</b> ${escapeHtml(item.prompt)}</div>` : ''}
              ${item.content && item.content !== title ? `<div class="mb-2 text-slate-300 font-medium"><b>Nội dung:</b> ${escapeHtml(item.content)}</div>` : ''}
              ${item.details ? `<div class="bg-[#0e192c] rounded-md p-3 text-slate-200 font-mono text-[11.5px] whitespace-pre-wrap border border-[#244170] leading-relaxed">${escapeHtml(item.details)}</div>` : ''}
              ${item.result ? `<div class="bg-[#0e192c] rounded-md p-3 border border-[#244170] mt-2 text-slate-200 markdown-body">${safeMarkdown(item.result)}</div>` : ''}
              ${item.reply ? `<div class="bg-[#0e192c] rounded-md p-3 border border-[#244170] mt-2 text-slate-200 markdown-body"><b>Phản hồi:</b><br/>${safeMarkdown(item.reply)}</div>` : ''}
              ${item.turns && item.turns.length > 0 ? `
                <div class="space-y-2 mt-2">
                  <div class="text-[11px] font-semibold text-slate-300">Diễn biến hội thoại (${item.turns.length} lượt):</div>
                  ${item.turns.map(t => `
                    <div class="bg-[#0e192c] border border-[#244170] rounded-md p-3">
                      <div class="flex items-center justify-between text-[11px] mb-1">
                        <span class="font-bold ${t.speaker === 'fe' ? 'text-cyan-400' : 'text-emerald-400'}">${t.speaker === 'fe' ? 'Frontend Agent' : 'Backend Agent'}</span>
                        <span class="text-slate-400 font-mono">${t.timestamp || ''}</span>
                      </div>
                      <div class="text-slate-200 text-xs markdown-body">${safeMarkdown(t.content)}</div>
                    </div>
                  `).join('')}
                </div>
              ` : ''}
            </div>
          ` : ''}
        </div>
      `;
}

function toggleLogDetails(id) {
  id = String(id);
  const el = document.getElementById('logDetail_' + id);
  const icon = document.getElementById('logIcon_' + id);
  const card = document.getElementById('logItemCard_' + id);
  if (!el) return;
  if (el.classList.contains('hidden')) {
    el.classList.remove('hidden');
    if (icon) icon.classList.add('rotate-180');
    if (card) card.classList.add('log-item-active');
    expandedLogIds.add(id);
  } else {
    el.classList.add('hidden');
    if (icon) icon.classList.remove('rotate-180');
    if (card) card.classList.remove('log-item-active');
    expandedLogIds.delete(id);
  }
}

async function deleteSingleLogItem(logId, e) {
  if (e) {
    e.stopPropagation();
    e.preventDefault();
  }
  const conf = await antdConfirm({
    title: 'Xóa bản ghi lịch sử?',
    content: 'Bạn có chắc chắn muốn xóa bản ghi lịch sử này? Thao tác này không thể hoàn tác.',
    danger: true,
    okText: 'Xóa',
    cancelText: 'Hủy'
  });
  if (!conf) return;

  try {
    const res = await fetch('/api/logs/delete', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ id: logId })
    });
    const d = await res.json();
    if (d.success) {
      cachedLogs = cachedLogs.filter(item => String(item.id || item.timestamp) !== String(logId));
      lastLogsSignature = '';
      renderFilteredLogs();
      showToast('Đã xóa bản ghi lịch sử.');
    } else {
      showToast(d.message || 'Lỗi khi xóa bản ghi.', 'error');
    }
  } catch (err) {
    showToast('Lỗi kết nối khi gửi yêu cầu xóa.', 'error');
  }
}
window.deleteSingleLogItem = deleteSingleLogItem;

async function clearLogs() {
  const confirmed = await antdConfirm({
    title: 'Xóa toàn bộ lịch sử',
    content: 'Bạn có chắc chắn muốn xóa toàn bộ lịch sử log? Thao tác này không thể hoàn tác.',
    danger: true,
    okText: 'Xóa vĩnh viễn'
  });
  if (!confirmed) return;

  try {
    const res = await fetch('/api/logs/clear', { method: 'POST' });
    const data = await res.json();
    if (data.success) {
      cachedLogs = [];
      lastLogsSignature = '';
      expandedLogIds.clear();
      renderFilteredLogs();
    } else {
      await antdAlert({ title: 'Lỗi', content: 'Không thể xóa log: ' + data.message, type: 'error' });
    }
  } catch (err) {
    await antdAlert({ title: 'Lỗi', content: 'Lỗi xóa log: ' + err.message, type: 'error' });
  }
}
