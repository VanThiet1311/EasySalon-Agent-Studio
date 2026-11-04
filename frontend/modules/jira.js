// ============================================================
// JIRA TASKS WORKSPACE MODULE
// Tự động đồng bộ và điều phối Ticket / Issue trực tiếp với AI Agent
// ============================================================

window.currentJiraIssues = [];
window.activeJiraIssue = null;
window.activeJiraFilter = 'all';
window.jiraWorkspaceLoaded = false;
window.jiraStatus = null;
window.jiraAutoSyncTimer = null;
window.jiraNotificationTimer = null;
window.jiraHideNonCoding = true; // Mặc định ẩn các task phi code
let jiraSearchDebounceTimer = null;
window.activeRovoAnalysisText = '';
window.jiraRovoCache = {}; // Lưu cache phân tích Rovo theo từng ticket key

// ------------------------------------------------------------
// LƯU BỀN KẾT QUẢ PHÂN TÍCH ROVO (localStorage) - reload không mất
// ------------------------------------------------------------
const JIRA_ROVO_CACHE_KEY = 'easysalon_jira_rovo_cache_v1';
const JIRA_ROVO_CACHE_MAX_ITEMS = 60;
const JIRA_ROVO_CACHE_TTL_MS = 30 * 24 * 60 * 60 * 1000; // 30 ngày

function loadRovoCacheFromStorage() {
  try {
    const raw = localStorage.getItem(JIRA_ROVO_CACHE_KEY);
    if (!raw) return {};
    const parsed = JSON.parse(raw);
    if (!parsed || typeof parsed !== 'object') return {};
    const now = Date.now();
    const cleaned = {};
    Object.keys(parsed).forEach(k => {
      const item = parsed[k];
      if (!item || typeof item.analysis !== 'string' || !item.analysis) return;
      const ts = Number(item.ts) || 0;
      if (ts && (now - ts) > JIRA_ROVO_CACHE_TTL_MS) return; // hết hạn
      cleaned[k] = {
        analysis: item.analysis,
        engine: item.engine || 'Atlassian Rovo',
        ts: ts || now
      };
    });
    return cleaned;
  } catch (e) {
    return {};
  }
}

function saveRovoCacheToStorage() {
  try {
    const cache = window.jiraRovoCache || {};
    // Giữ tối đa N ticket mới nhất để không tràn localStorage
    const keys = Object.keys(cache);
    if (keys.length > JIRA_ROVO_CACHE_MAX_ITEMS) {
      keys.sort((a, b) => (Number(cache[b]?.ts) || 0) - (Number(cache[a]?.ts) || 0));
      keys.slice(JIRA_ROVO_CACHE_MAX_ITEMS).forEach(k => { delete cache[k]; });
    }
    localStorage.setItem(JIRA_ROVO_CACHE_KEY, JSON.stringify(cache));
  } catch (e) {
    // Hết quota: xoá bớt nửa số ticket cũ rồi thử lại một lần
    try {
      const cache = window.jiraRovoCache || {};
      const keys = Object.keys(cache);
      keys.sort((a, b) => (Number(cache[b]?.ts) || 0) - (Number(cache[a]?.ts) || 0));
      keys.slice(Math.max(1, Math.floor(keys.length / 2))).forEach(k => { delete cache[k]; });
      localStorage.setItem(JIRA_ROVO_CACHE_KEY, JSON.stringify(cache));
    } catch (e2) { /* bỏ qua */ }
  }
}

window.jiraRovoCache = loadRovoCacheFromStorage();

// Ghi nhớ Ticket đang mở để reload trang vẫn quay lại đúng ticket
const JIRA_LAST_TICKET_KEY = 'easysalon_jira_last_ticket';

function rememberActiveJiraKey(key) {
  try {
    if (key) localStorage.setItem(JIRA_LAST_TICKET_KEY, String(key));
  } catch (e) { /* bỏ qua */ }
}

function getRememberedJiraKey() {
  try {
    return localStorage.getItem(JIRA_LAST_TICKET_KEY) || '';
  } catch (e) {
    return '';
  }
}

/**
 * Chuẩn hóa nhãn và kiểu badge cho loại yêu cầu (Issue Type)
 */
function getJiraTypeBadgeInfo(rawType) {
  const lower = (rawType || '').toLowerCase().trim();
  if (lower.includes('bug')) {
    return {
      label: 'Sửa lỗi',
      className: 'jira-type-bug',
      title: 'Bug - Sửa lỗi phần mềm'
    };
  }
  if (lower === 'story' || lower.includes('story')) {
    return {
      label: 'Tính năng',
      className: 'jira-type-story',
      title: 'Story - Tính năng / Yêu cầu phát triển người dùng'
    };
  }
  if (lower.includes('feature')) {
    return {
      label: 'Tính năng mới',
      className: 'jira-type-story',
      title: 'New Feature - Tính năng mới'
    };
  }
  if (lower.includes('non coding') || lower.includes('non-coding')) {
    return {
      label: 'Tác vụ ngoài',
      className: 'jira-type-noncoding',
      title: 'Non Coding Task - Nhiệm vụ dữ liệu / nghiệp vụ ngoài lề (không sửa code)'
    };
  }
  if (lower.includes('sub-task') || lower.includes('subtask')) {
    return {
      label: 'Tác vụ con',
      className: 'jira-type-subtask',
      title: 'Sub-task - Tác vụ phụ'
    };
  }
  return {
    label: rawType || 'Tác vụ',
    className: 'jira-type-task',
    title: rawType || 'Tác vụ'
  };
}
window.getJiraTypeBadgeInfo = getJiraTypeBadgeInfo;

function toggleJiraHideNonCoding() {
  const cb = document.getElementById('jiraHideNonCodingCheckbox');
  window.jiraHideNonCoding = cb ? cb.checked : false;
  fetchJiraIssues();
}
window.toggleJiraHideNonCoding = toggleJiraHideNonCoding;

// Tự động đồng bộ ngầm khi mở Workspace
async function loadJiraWorkspace(force = false, silent = false) {
  if (window.jiraWorkspaceLoaded && !force) {
    const listEl = document.getElementById('jiraIssuesList');
    if (listEl && listEl.children.length === 0 && window.currentJiraIssues && window.currentJiraIssues.length > 0) {
      renderJiraIssuesList();
    }
    return;
  }
  window.jiraWorkspaceLoaded = true;

  const fallbackEl = document.getElementById('jiraFallbackUnconfigured');
  const mainContentEl = document.getElementById('jiraWorkspaceMainContent');
  const autoSyncText = document.getElementById('jiraAutoSyncText');
  const autoSyncDot = document.getElementById('jiraAutoSyncDot');
  const fallbackBadge = document.getElementById('jiraFallbackBadge');
  const fallbackTitle = document.getElementById('jiraFallbackTitle');
  const fallbackDesc = document.getElementById('jiraFallbackDesc');
  const btnConfigText = document.getElementById('btnOpenJiraMcpConfigText');

  try {
    const res = await fetch('/api/jira/status');
    const data = await res.json();
    window.jiraStatus = data;

    if (data && data.user) {
      window.currentJiraUserProfile = {
        accountId: data.user.accountId,
        displayName: data.user.displayName,
        email: data.user.emailAddress || '',
        avatar: data.user.avatarUrl || ''
      };
      if (data.user.accountId) {
        window.currentJiraUserAccountId = data.user.accountId;
      }
    }

    if (data && (data.configured === false || data.enabled === false)) {
      // Xóa toàn bộ dữ liệu ticket cũ khỏi bộ nhớ và giao diện
      window.currentJiraIssues = [];
      window.activeJiraIssue = null;
      const listEl = document.getElementById('jiraIssuesList');
      if (listEl) listEl.innerHTML = '';
      const countBadge = document.getElementById('jiraIssueCountBadge');
      if (countBadge) countBadge.textContent = '0';

      if (fallbackEl) fallbackEl.classList.remove('hidden');
      if (mainContentEl) mainContentEl.classList.add('hidden');

      const isTurnedOff = data.enabled === false;
      if (fallbackBadge) {
        fallbackBadge.textContent = isTurnedOff ? 'Jira MCP đang tắt' : 'Chưa kết nối Jira MCP';
        fallbackBadge.className = isTurnedOff
          ? 'inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-[11px] font-sans font-medium bg-rose-500/10 text-rose-400 border border-rose-500/20'
          : 'inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-[11px] font-sans font-medium bg-amber-500/10 text-amber-400 border border-amber-500/20';
      }
      if (fallbackTitle) {
        fallbackTitle.textContent = isTurnedOff
          ? 'Jira MCP Server đang tạm dừng'
          : 'Jira Tasks Workspace chưa được kích hoạt';
      }
      if (fallbackDesc) {
        fallbackDesc.textContent = isTurnedOff
          ? 'Jira MCP Server đã được tắt trong phần Cài đặt MCP. Vui lòng bật lại để tiếp tục đồng bộ User Story, Bug và điều phối AI Agent.'
          : 'Không gian làm việc Jira cho phép AI Agent đọc danh sách User Story, Bug, cập nhật trạng thái tiến độ và tự động hóa tác vụ lập trình. Để bắt đầu, vui lòng cắm và cấu hình Jira MCP Server.';
      }
      if (btnConfigText) {
        btnConfigText.textContent = isTurnedOff
          ? 'Mở Cài đặt để bật lại Jira MCP'
          : 'Cấu hình Jira MCP ngay';
      }
      if (autoSyncText) {
        autoSyncText.textContent = 'Chưa kết nối';
      }
      if (autoSyncDot) {
        autoSyncDot.className = 'inline-block w-2 h-2 rounded-full bg-rose-500 is-disconnected';
      }
      return;
    }

    // Đã cấu hình và đang bật -> hiển thị nội dung chính
    if (fallbackEl) fallbackEl.classList.add('hidden');
    if (mainContentEl) mainContentEl.classList.remove('hidden');

    if (data && data.connected) {
      if (autoSyncText) autoSyncText.textContent = 'Tự động đồng bộ';
      if (autoSyncDot) autoSyncDot.className = 'inline-block w-2 h-2 rounded-full bg-emerald-500 animate-pulse is-connected';
    } else {
      if (autoSyncText) autoSyncText.textContent = 'Chưa kết nối';
      if (autoSyncDot) autoSyncDot.className = 'inline-block w-2 h-2 rounded-full bg-rose-500 is-error';
    }
  } catch (err) {
    if (autoSyncText) autoSyncText.textContent = 'Chưa kết nối';
    if (autoSyncDot) autoSyncDot.className = 'inline-block w-2 h-2 rounded-full bg-rose-500 is-error';
  }

  await fetchJiraIssues(null, silent);

  // Kích hoạt theo dõi thông báo Jira thời gian thực
  startJiraNotificationWatcher();
}
window.loadJiraWorkspace = loadJiraWorkspace;

function openJiraMcpSettings() {
  window.initSettingsSubTab = 'mcp';
  if (typeof switchTab === 'function') {
    switchTab('settings');
  }
  if (typeof switchSettingsSidebarTab === 'function') {
    switchSettingsSidebarTab('mcp');
  } else if (typeof switchSettingsTab === 'function') {
    switchSettingsTab('mcp');
  }
  if (typeof selectMcpPreset === 'function') {
    selectMcpPreset('jira');
  }
  const targetPath = '/settings/mcp';
  if (window.location.pathname !== targetPath) {
    try {
      window.history.pushState({ tab: 'settings', settingsSubTab: 'mcp' }, '', targetPath);
    } catch (e) { }
  }
  const jiraCard = document.getElementById('cardPreset_jira');
  if (jiraCard && typeof jiraCard.scrollIntoView === 'function') {
    setTimeout(() => {
      jiraCard.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
    }, 100);
  }
}
window.openJiraMcpSettings = openJiraMcpSettings;

function startJiraAutoSync() {
  if (window.jiraAutoSyncTimer) return;
  window.jiraAutoSyncTimer = setInterval(async () => {
    if (window.activeTab !== 'jira') return;
    if (window.jiraStatus && (window.jiraStatus.configured === false || window.jiraStatus.enabled === false)) return;
    const syncText = document.getElementById('jiraAutoSyncText');
    const syncDot = document.getElementById('jiraAutoSyncDot');
    try {
      if (syncText) syncText.textContent = 'Đang đồng bộ...';
      if (syncDot) syncDot.className = 'inline-block w-2 h-2 rounded-full bg-emerald-500 animate-pulse is-connected';
      await loadJiraWorkspace(true, true);
      if (syncText) syncText.textContent = 'Tự động đồng bộ';
      if (syncDot) syncDot.className = 'inline-block w-2 h-2 rounded-full bg-emerald-500 animate-pulse is-connected';
    } catch (e) {
      if (syncText) syncText.textContent = 'Chưa kết nối';
      if (syncDot) syncDot.className = 'inline-block w-2 h-2 rounded-full bg-rose-500 is-error';
    }
  }, 20000);
}
window.startJiraAutoSync = startJiraAutoSync;

function stopJiraAutoSync() {
  if (window.jiraAutoSyncTimer) {
    clearInterval(window.jiraAutoSyncTimer);
    window.jiraAutoSyncTimer = null;
  }
}
window.stopJiraAutoSync = stopJiraAutoSync;

async function fetchJiraIssues(customQuery = null, silent = false) {
  if (window.jiraStatus && (window.jiraStatus.configured === false || window.jiraStatus.enabled === false)) {
    window.currentJiraIssues = [];
    window.activeJiraIssue = null;
    const listEl = document.getElementById('jiraIssuesList');
    if (listEl) listEl.innerHTML = '';
    const countBadge = document.getElementById('jiraIssueCountBadge');
    if (countBadge) countBadge.textContent = '0';
    const fallbackEl = document.getElementById('jiraFallbackUnconfigured');
    const mainContentEl = document.getElementById('jiraWorkspaceMainContent');
    if (fallbackEl) fallbackEl.classList.remove('hidden');
    if (mainContentEl) mainContentEl.classList.add('hidden');
    return;
  }

  const listEl = document.getElementById('jiraIssuesList');
  const countBadge = document.getElementById('jiraIssueCountBadge');
  const projectSelect = document.getElementById('jiraProjectSelect');
  const selectedProject = projectSelect ? projectSelect.value : 'EAS';

  if (listEl && !silent) {
    listEl.innerHTML = `
      <div class="p-8 text-center text-slate-400 text-xs font-sans space-y-2">
        <div class="inline-block w-5 h-5 border-2 border-blue-500 border-t-transparent rounded-full animate-spin"></div>
        <p>Đang tải danh sách ticket từ Jira Cloud...</p>
      </div>
    `;
  }

  const queryParam = customQuery !== null ? customQuery : (document.getElementById('jiraSearchInput')?.value || '');
  const hideNonCodingParam = window.jiraHideNonCoding ? 'true' : 'false';
  const url = `/api/jira/issues?project=${encodeURIComponent(selectedProject)}&filter=${encodeURIComponent(window.activeJiraFilter)}&hide_non_coding=${hideNonCodingParam}&query=${encodeURIComponent(queryParam)}&max_results=40`;

  try {
    const res = await fetch(url);
    const data = await res.json();
    if (data && data.success) {
      window.currentJiraIssues = data.issues || [];
      const validIssues = (window.currentJiraIssues || []).filter(item => !item.is_subtask && (item.issuetype || '').toLowerCase() !== 'sub-task');
      if (countBadge) countBadge.textContent = validIssues.length;
      if (activeTab === 'jira') {
        renderJiraIssuesList();

        // Nếu đang tìm kiếm và có kết quả: tự động mở ticket đầu tiên
        if (queryParam && validIssues.length > 0) {
          selectJiraIssue(validIssues[0].key);
        } else if (validIssues.length > 0 && !window.activeJiraIssue) {
          // Ưu tiên mở lại ticket đang xem trước khi reload trang
          const rememberedKey = getRememberedJiraKey();
          const remembered = rememberedKey
            ? validIssues.find(item => item.key === rememberedKey)
            : null;
          selectJiraIssue((remembered || validIssues[0]).key);
        } else if (window.activeJiraIssue && silent) {
          selectJiraIssue(window.activeJiraIssue.key, true);
        }
      }
    } else {
      if (data && data.message && data.message.includes('Chưa cấu hình')) {
        const fallbackEl = document.getElementById('jiraFallbackUnconfigured');
        const mainContentEl = document.getElementById('jiraWorkspaceMainContent');
        if (fallbackEl) fallbackEl.classList.remove('hidden');
        if (mainContentEl) mainContentEl.classList.add('hidden');
      }
      if (listEl && !silent) {
        listEl.innerHTML = `
          <div class="p-6 text-center text-rose-400 text-xs font-sans space-y-2 border border-rose-900/40 rounded-lg bg-rose-950/20">
            <p class="font-semibold">Không thể tải danh sách ticket</p>
            <p class="text-[11px] text-slate-400">${escapeHtml((data && data.message) || 'Lỗi không xác định')}</p>
          </div>
        `;
      }
      if (countBadge) countBadge.textContent = '0';
    }
  } catch (err) {
    if (listEl && !silent) {
      listEl.innerHTML = `
        <div class="p-6 text-center text-rose-400 text-xs font-sans space-y-1">
          <p>Lỗi kết nối khi tải danh sách ticket</p>
          <p class="text-[11px] text-slate-400">${escapeHtml(err.message)}</p>
        </div>
      `;
    }
  }
}
window.fetchJiraIssues = fetchJiraIssues;

// ------------------------------------------------------------
// BỘ LỌC NHANH (checkbox dropdown): Loại ticket, Trạng thái & Ngày giờ
// ------------------------------------------------------------
const JIRA_LOCAL_FILTER_KEY = 'easysalon_jira_local_filters_v1';
window.jiraLocalFilters = {
  types: [],
  statuses: [],
  dateRange: 'all',
  dateField: 'updated',
  customFrom: '',
  customTo: ''
};

function loadJiraLocalFilters() {
  try {
    const raw = localStorage.getItem(JIRA_LOCAL_FILTER_KEY);
    if (!raw) return;
    const d = JSON.parse(raw);
    if (d && typeof d === 'object') {
      window.jiraLocalFilters = {
        types: Array.isArray(d.types) ? d.types : [],
        statuses: Array.isArray(d.statuses) ? d.statuses : [],
        dateRange: typeof d.dateRange === 'string' ? d.dateRange : 'all',
        dateField: typeof d.dateField === 'string' ? d.dateField : 'updated',
        customFrom: typeof d.customFrom === 'string' ? d.customFrom : '',
        customTo: typeof d.customTo === 'string' ? d.customTo : ''
      };
    }
  } catch (e) { /* bỏ qua */ }
}

function saveJiraLocalFilters() {
  try {
    localStorage.setItem(JIRA_LOCAL_FILTER_KEY, JSON.stringify(window.jiraLocalFilters || {}));
  } catch (e) { /* bỏ qua */ }
}

loadJiraLocalFilters();

function getJiraLocalTypeLabel(item) {
  return getJiraTypeBadgeInfo(item.issuetype).label;
}

function getJiraLocalFilterOptions() {
  const issues = (window.currentJiraIssues || [])
    .filter(i => !i.is_subtask && (i.issuetype || '').toLowerCase() !== 'sub-task');
  const typeMap = new Map();
  const statusMap = new Map();
  issues.forEach(i => {
    const tl = getJiraLocalTypeLabel(i);
    typeMap.set(tl, (typeMap.get(tl) || 0) + 1);
    const st = i.status || 'Chưa rõ';
    statusMap.set(st, (statusMap.get(st) || 0) + 1);
  });
  return {
    types: Array.from(typeMap.entries()).sort((a, b) => b[1] - a[1]),
    statuses: Array.from(statusMap.entries()).sort((a, b) => b[1] - a[1])
  };
}

function countIssuesForDateRange(issues, rangeId, field) {
  if (rangeId === 'all') return issues.length;
  const now = new Date();
  const startOfToday = new Date(now.getFullYear(), now.getMonth(), now.getDate(), 0, 0, 0, 0).getTime();
  const threeDaysAgo = Date.now() - 3 * 24 * 60 * 60 * 1000;
  const sevenDaysAgo = Date.now() - 7 * 24 * 60 * 60 * 1000;
  const thirtyDaysAgo = Date.now() - 30 * 24 * 60 * 60 * 1000;

  return issues.filter(item => {
    const val = (field === 'created' ? item.created : (item.updated || item.created));
    if (!val) return false;
    const t = new Date(val).getTime();
    if (!t || isNaN(t)) return false;
    if (rangeId === 'today') return t >= startOfToday;
    if (rangeId === '3days') return t >= threeDaysAgo;
    if (rangeId === '7days') return t >= sevenDaysAgo;
    if (rangeId === '30days') return t >= thirtyDaysAgo;
    return true;
  }).length;
}

function jiraIssueMatchesLocalFilters(item) {
  const f = window.jiraLocalFilters || { types: [], statuses: [], dateRange: 'all', dateField: 'updated' };
  const isAllTab = (!window.activeJiraFilter || window.activeJiraFilter === 'all');

  // Chỉ áp dụng lọc loại ticket khi ở tab "Tất cả"
  if (isAllTab && f.types && f.types.length && !f.types.includes(getJiraLocalTypeLabel(item))) {
    return false;
  }

  // Lọc trạng thái
  if (f.statuses && f.statuses.length && !f.statuses.includes(item.status || 'Chưa rõ')) {
    return false;
  }

  // Lọc theo ngày giờ (Cập nhật hoặc Ngày tạo)
  if (f.dateRange && f.dateRange !== 'all') {
    const field = f.dateField === 'created' ? 'created' : 'updated';
    const dateStr = (field === 'created' ? item.created : (item.updated || item.created));
    if (!dateStr) return false;
    const itemTime = new Date(dateStr).getTime();
    if (!itemTime || isNaN(itemTime)) return false;

    if (f.dateRange === 'today') {
      const now = new Date();
      const startOfToday = new Date(now.getFullYear(), now.getMonth(), now.getDate(), 0, 0, 0, 0).getTime();
      if (itemTime < startOfToday) return false;
    } else if (f.dateRange === '3days') {
      const cutoff = Date.now() - 3 * 24 * 60 * 60 * 1000;
      if (itemTime < cutoff) return false;
    } else if (f.dateRange === '7days') {
      const cutoff = Date.now() - 7 * 24 * 60 * 60 * 1000;
      if (itemTime < cutoff) return false;
    } else if (f.dateRange === '30days') {
      const cutoff = Date.now() - 30 * 24 * 60 * 60 * 1000;
      if (itemTime < cutoff) return false;
    } else if (f.dateRange === 'custom') {
      if (f.customFrom) {
        const parts = f.customFrom.split('-');
        if (parts.length === 3) {
          const fromTime = new Date(parseInt(parts[0], 10), parseInt(parts[1], 10) - 1, parseInt(parts[2], 10), 0, 0, 0, 0).getTime();
          if (itemTime < fromTime) return false;
        }
      }
      if (f.customTo) {
        const parts = f.customTo.split('-');
        if (parts.length === 3) {
          const toTime = new Date(parseInt(parts[0], 10), parseInt(parts[1], 10) - 1, parseInt(parts[2], 10), 23, 59, 59, 999).getTime();
          if (itemTime > toTime) return false;
        }
      }
    }
  }

  return true;
}

function updateJiraLocalFilterBadge() {
  const f = window.jiraLocalFilters || { types: [], statuses: [], dateRange: 'all' };
  const isAllTab = (!window.activeJiraFilter || window.activeJiraFilter === 'all');
  const typeCount = isAllTab ? (f.types ? f.types.length : 0) : 0;
  const statusCount = f.statuses ? f.statuses.length : 0;
  const dateCount = (f.dateRange && f.dateRange !== 'all') ? 1 : 0;
  const count = typeCount + statusCount + dateCount;
  const badge = document.getElementById('jiraLocalFilterCount');
  if (badge) {
    badge.textContent = String(count);
    badge.classList.toggle('hidden', count === 0);
  }
  const btn = document.getElementById('jiraLocalFilterBtn');
  if (btn) btn.classList.toggle('is-active', count > 0);
}

function renderJiraLocalFilterMenu() {
  const body = document.getElementById('jiraLocalFilterBody');
  if (!body) return;

  const { types, statuses } = getJiraLocalFilterOptions();
  const f = window.jiraLocalFilters || { types: [], statuses: [], dateRange: 'all', dateField: 'updated' };
  const validTypes = types.map(t => t[0]);
  const validStatuses = statuses.map(s => s[0]);
  const typeSel = (f.types || []).filter(v => validTypes.includes(v));
  const statusSel = (f.statuses || []).filter(v => validStatuses.includes(v));

  // Bỏ các giá trị không còn xuất hiện trong danh sách hiện tại
  if (typeSel.length !== (f.types || []).length || statusSel.length !== (f.statuses || []).length) {
    f.types = typeSel;
    f.statuses = statusSel;
    window.jiraLocalFilters = f;
    saveJiraLocalFilters();
    updateJiraLocalFilterBadge();
  }

  const isAllTab = (!window.activeJiraFilter || window.activeJiraFilter === 'all');

  const renderGroup = (title, kind, rows, selected) => `
    <div class="jira-local-filter-group">
      <div class="jira-local-filter-group-title">${title}</div>
      ${rows.length === 0
        ? '<p class="jira-local-filter-empty">Không có dữ liệu</p>'
        : rows.map(([value, count]) => `
          <label class="jira-local-filter-item">
            <input type="checkbox" class="jira-local-filter-checkbox" value="${escapeHtml(value)}"
              ${selected.includes(value) ? 'checked' : ''}
              onchange="onJiraLocalFilterToggle('${kind}', this.value, this.checked)" />
            <span class="jira-local-filter-label">${escapeHtml(value)}</span>
            <span class="jira-local-filter-count">${count}</span>
          </label>
        `).join('')}
    </div>
  `;

  const renderDateGroup = () => {
    const curRange = f.dateRange || 'all';
    const curField = f.dateField || 'updated';
    const issues = (window.currentJiraIssues || [])
      .filter(i => !i.is_subtask && (i.issuetype || '').toLowerCase() !== 'sub-task');

    const dateOptions = [
      { id: 'all', label: 'Tất cả thời gian' },
      { id: 'today', label: 'Hôm nay' },
      { id: '3days', label: '3 ngày gần đây' },
      { id: '7days', label: '7 ngày gần đây' },
      { id: '30days', label: '30 ngày gần đây' },
      { id: 'custom', label: 'Khoảng ngày tùy chọn...' }
    ];

    const isCustom = curRange === 'custom';

    return `
      <div class="jira-local-filter-group pt-2 border-t border-[#244170]/60">
        <div class="flex items-center justify-between px-1.5 pb-1.5">
          <span class="jira-local-filter-group-title p-0">Thời gian</span>
          <div class="flex items-center gap-1 text-[10px] font-sans">
            <button type="button" onclick="onJiraDateFieldToggle('updated')"
              class="jira-local-filter-date-btn ${curField === 'updated' ? 'is-active' : ''}"
              title="Lọc theo ngày giờ cập nhật gần nhất">
              Cập nhật
            </button>
            <button type="button" onclick="onJiraDateFieldToggle('created')"
              class="jira-local-filter-date-btn ${curField === 'created' ? 'is-active' : ''}"
              title="Lọc theo ngày giờ tạo ticket">
              Ngày tạo
            </button>
          </div>
        </div>
        <div class="space-y-0.5">
          ${dateOptions.map(opt => {
            const count = countIssuesForDateRange(issues, opt.id, curField);
            return `
              <label class="jira-local-filter-item">
                <input type="radio" name="jiraDateRangeOption" class="jira-local-filter-radio" value="${opt.id}"
                  ${curRange === opt.id ? 'checked' : ''}
                  onchange="onJiraDateRangeChange(this.value)" />
                <span class="jira-local-filter-label">${opt.label}</span>
                ${opt.id !== 'custom' ? `<span class="jira-local-filter-count">${count}</span>` : ''}
              </label>
            `;
          }).join('')}
        </div>
        ${isCustom ? `
          <div class="mt-2 p-2 rounded jira-date-custom-box space-y-1.5">
            <div class="flex items-center gap-1.5 text-[11px]">
              <span class="text-slate-400 w-9 shrink-0">Từ:</span>
              <input type="date" value="${escapeHtml(f.customFrom || '')}"
                onchange="onJiraCustomDateChange('customFrom', this.value)"
                class="jira-date-custom-input" />
            </div>
            <div class="flex items-center gap-1.5 text-[11px]">
              <span class="text-slate-400 w-9 shrink-0">Đến:</span>
              <input type="date" value="${escapeHtml(f.customTo || '')}"
                onchange="onJiraCustomDateChange('customTo', this.value)"
                class="jira-date-custom-input" />
            </div>
          </div>
        ` : ''}
      </div>
    `;
  };

  const typeGroupHtml = isAllTab ? renderGroup('Loại ticket', 'type', types, typeSel) : '';
  const statusGroupHtml = renderGroup('Trạng thái', 'status', statuses, statusSel);
  const dateGroupHtml = renderDateGroup();

  body.innerHTML = typeGroupHtml + statusGroupHtml + dateGroupHtml;
}

function onJiraLocalFilterToggle(kind, value, checked) {
  const f = window.jiraLocalFilters || { types: [], statuses: [] };
  const key = kind === 'type' ? 'types' : 'statuses';
  const set = new Set(f[key] || []);
  if (checked) set.add(value);
  else set.delete(value);
  f[key] = Array.from(set);
  window.jiraLocalFilters = f;
  saveJiraLocalFilters();
  updateJiraLocalFilterBadge();
  renderJiraIssuesList();
}
window.onJiraLocalFilterToggle = onJiraLocalFilterToggle;

function onJiraDateRangeChange(range) {
  const f = window.jiraLocalFilters || { types: [], statuses: [], dateRange: 'all' };
  f.dateRange = range;
  window.jiraLocalFilters = f;
  saveJiraLocalFilters();
  updateJiraLocalFilterBadge();
  renderJiraLocalFilterMenu();
  renderJiraIssuesList();
}
window.onJiraDateRangeChange = onJiraDateRangeChange;

function onJiraDateFieldToggle(field) {
  const f = window.jiraLocalFilters || { types: [], statuses: [], dateRange: 'all' };
  f.dateField = field;
  window.jiraLocalFilters = f;
  saveJiraLocalFilters();
  renderJiraLocalFilterMenu();
  renderJiraIssuesList();
}
window.onJiraDateFieldToggle = onJiraDateFieldToggle;

function onJiraCustomDateChange(key, value) {
  const f = window.jiraLocalFilters || { types: [], statuses: [], dateRange: 'all' };
  f[key] = value;
  window.jiraLocalFilters = f;
  saveJiraLocalFilters();
  updateJiraLocalFilterBadge();
  renderJiraIssuesList();
}
window.onJiraCustomDateChange = onJiraCustomDateChange;

function toggleJiraLocalFilter(event) {
  if (event) event.stopPropagation();
  const menu = document.getElementById('jiraLocalFilterMenu');
  if (!menu) return;
  if (menu.classList.contains('hidden')) {
    renderJiraLocalFilterMenu();
    menu.classList.remove('hidden');
    const chevron = document.getElementById('jiraLocalFilterChevron');
    if (chevron) chevron.style.transform = 'rotate(180deg)';
  } else {
    closeJiraLocalFilter();
  }
}
window.toggleJiraLocalFilter = toggleJiraLocalFilter;

function closeJiraLocalFilter() {
  const menu = document.getElementById('jiraLocalFilterMenu');
  if (menu) menu.classList.add('hidden');
  const chevron = document.getElementById('jiraLocalFilterChevron');
  if (chevron) chevron.style.transform = '';
}
window.closeJiraLocalFilter = closeJiraLocalFilter;

function clearJiraLocalFilters() {
  window.jiraLocalFilters = {
    types: [],
    statuses: [],
    dateRange: 'all',
    dateField: 'updated',
    customFrom: '',
    customTo: ''
  };
  saveJiraLocalFilters();
  updateJiraLocalFilterBadge();
  renderJiraLocalFilterMenu();
  renderJiraIssuesList();
}
window.clearJiraLocalFilters = clearJiraLocalFilters;

document.addEventListener('click', (e) => {
  const wrap = document.getElementById('jiraLocalFilterWrap');
  if (wrap && !wrap.contains(e.target)) closeJiraLocalFilter();
  const assigneeWrap = document.getElementById('jiraDetailAssigneeDropdownWrap');
  if (assigneeWrap && !assigneeWrap.contains(e.target)) closeJiraAssigneeDropdown();
  const subtaskFloatingMenu = document.getElementById('jiraSubtaskAssigneeFloatingMenu');
  if (subtaskFloatingMenu && !subtaskFloatingMenu.contains(e.target) && !e.target.closest('.jira-subtask-assignee-trigger')) {
    closeSubtaskAssigneeMenu();
  }
});

document.addEventListener('keydown', (e) => {
  if (e.key === 'Escape') {
    closeJiraAssigneeDropdown();
    closeSubtaskAssigneeMenu();
  }
});

function renderJiraIssuesList() {
  const listEl = document.getElementById('jiraIssuesList');
  if (!listEl) return;

  // Lọc bỏ triệt để mọi Sub-task khỏi danh sách chính bên trái
  const rawIssues = window.currentJiraIssues || [];
  const allIssues = rawIssues.filter(item => !item.is_subtask && (item.issuetype || '').toLowerCase() !== 'sub-task');
  const issues = allIssues.filter(jiraIssueMatchesLocalFilters);

  const countBadge = document.getElementById('jiraIssueCountBadge');
  if (countBadge) countBadge.textContent = issues.length;
  updateJiraLocalFilterBadge();

  if (issues.length === 0) {
    const hasFilters = allIssues.length > 0;
    listEl.innerHTML = `
      <div class="p-8 text-center text-slate-400 text-xs font-sans space-y-2">
        <p class="font-medium text-slate-300">${hasFilters ? 'Không có Ticket nào khớp bộ lọc' : 'Không tìm thấy Ticket nào phù hợp'}</p>
        <p class="text-[11px] text-slate-400">${hasFilters ? 'Bấm "Bộ lọc" để bỏ chọn bớt điều kiện.' : 'Thử đổi bộ lọc, chọn dự án khác hoặc xóa từ khóa tìm kiếm.'}</p>
      </div>
    `;
    return;
  }

  const activeKey = window.activeJiraIssue ? window.activeJiraIssue.key : null;
  const isAllTab = (!window.activeJiraFilter || window.activeJiraFilter === 'all');
  const f = window.jiraLocalFilters || {};

  listEl.innerHTML = issues.map(item => {
    const isSelected = activeKey === item.key;
    const isDone = item.status_category === 'done' || /done|closed|resolved/i.test(item.status);
    const isInProgress = item.status_category === 'indeterminate' || /in progress|doing|testing|review/i.test(item.status);

    let statusBadgeClass = 'jira-status-todo';
    if (isDone) {
      statusBadgeClass = 'jira-status-done';
    } else if (isInProgress) {
      statusBadgeClass = 'jira-status-inprogress';
    }

    const typeInfo = getJiraTypeBadgeInfo(item.issuetype);
    const selectedCardClass = isSelected ? 'jira-card-item is-selected' : 'jira-card-item';

    // Chỉ hiển thị badge loại ticket khi ở tab "Tất cả"
    const typeBadgeHtml = isAllTab ? `
      <span class="text-[9.5px] font-sans px-1.5 py-0.5 rounded font-medium border ${typeInfo.className}" title="${escapeHtml(typeInfo.title)}">
        ${escapeHtml(typeInfo.label)}
      </span>
    ` : '';

    const dateToDisplay = (f.dateField === 'created' && item.created) ? item.created : item.updated;
    const dateLabel = formatJiraDate(dateToDisplay);
    const dateTooltip = `Cập nhật: ${formatJiraDate(item.updated)}${item.created ? ` | Tạo: ${formatJiraDate(item.created)}` : ''}`;

    return `
      <div onclick="selectJiraIssue('${escapeHtml(item.key)}')"
        class="p-3 rounded-lg border transition cursor-pointer select-none space-y-2 ${selectedCardClass}">
        <div class="flex items-center justify-between gap-2">
          <div class="flex items-center gap-1.5">
            <span class="font-mono text-xs font-bold text-blue-500">${escapeHtml(item.key)}</span>
            ${typeBadgeHtml}
          </div>
          <span class="text-[9.5px] font-sans px-1.5 py-0.5 rounded font-medium border ${statusBadgeClass}">
            ${escapeHtml(item.status)}
          </span>
        </div>

        <h4 class="jira-card-title text-xs line-clamp-2 leading-snug">
          ${escapeHtml(item.summary)}
        </h4>

        <div class="jira-card-meta flex items-center justify-between text-[10.5px] pt-1 border-t">
          <div class="flex items-center gap-1 truncate max-w-[180px]">
            <svg class="w-3 h-3 text-slate-400 shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z" />
            </svg>
            <span class="truncate">${escapeHtml(item.assignee || 'Chưa gán')}</span>
          </div>
          <span class="font-mono text-[10px]" title="${escapeHtml(dateTooltip)}">${escapeHtml(dateLabel)}</span>
        </div>
      </div>
    `;
  }).join('');
}
window.renderJiraIssuesList = renderJiraIssuesList;

function formatJiraDate(dateStr) {
  if (!dateStr) return '';
  try {
    const d = new Date(dateStr);
    if (isNaN(d.getTime())) return dateStr.slice(0, 10);
    const now = new Date();
    const diffMs = now.getTime() - d.getTime();
    const diffSec = Math.floor(diffMs / 1000);
    if (diffSec < 5) return 'Vừa xong';
    if (diffSec < 60) return `${diffSec} giây trước`;
    const diffMin = Math.floor(diffSec / 60);
    if (diffMin < 60) return `${diffMin} phút trước`;
    const diffHours = Math.floor(diffMin / 60);
    if (diffHours < 24) return `${diffHours} giờ trước`;
    const diffDays = Math.floor(diffHours / 24);
    if (diffDays < 7) return `${diffDays} ngày trước`;
    return `${d.getDate().toString().padStart(2, '0')}/${(d.getMonth() + 1).toString().padStart(2, '0')}/${d.getFullYear()}`;
  } catch (e) {
    return dateStr.slice(0, 10);
  }
}

async function selectJiraIssue(key, silent = false) {
  if (!key) return;

  const placeholder = document.getElementById('jiraDetailPlaceholder');
  const content = document.getElementById('jiraDetailContent');
  if (placeholder) placeholder.classList.add('hidden');
  if (content) content.classList.remove('hidden');

  // Ghi nhớ ticket đang mở để reload trang vẫn quay lại đúng ticket này
  rememberActiveJiraKey(key);

  // Phục hồi hoặc cập nhật Rovo Box:
  // Nếu là silent sync ngầm, TUYỆT ĐỐI không tắt box Rovo
  if (!silent) {
    if (window.jiraRovoCache && window.jiraRovoCache[key]) {
      const cached = window.jiraRovoCache[key];
      window.activeRovoAnalysisText = cached.analysis;
      renderRovoAnalysisContent(cached.analysis, cached.engine);
      toggleRovoBox(true);
      // Đã có kết quả phân tích lưu sẵn -> mở khoá nút "Đưa vào Tác vụ"
      setRovoSendButtonEnabled(true);
    } else {
      window.activeRovoAnalysisText = '';
      setRovoSendButtonEnabled(false);
      toggleRovoBox(false);
    }
  }

  if (window.activeJiraIssue && window.activeJiraIssue.key !== key) {
    window.activeJiraIssue = { key, summary: 'Đang tải chi tiết...', description: '' };
    renderJiraIssuesList();
  }

  const keyEl = document.getElementById('jiraDetailKey');
  const keyLink = document.getElementById('jiraDetailKeyLink');
  const summaryEl = document.getElementById('jiraDetailSummary');
  const descEl = document.getElementById('jiraDetailDescription');
  const typeBadge = document.getElementById('jiraDetailTypeBadge');
  const prioBadge = document.getElementById('jiraDetailPriorityBadge');
  const assigneeEl = document.getElementById('jiraDetailAssignee');
  const reporterEl = document.getElementById('jiraDetailReporter');
  const updatedEl = document.getElementById('jiraDetailUpdated');
  const transitionSelect = document.getElementById('jiraDetailTransitionSelect');
  const commentsList = document.getElementById('jiraDetailCommentsList');
  const commentCount = document.getElementById('jiraCommentCount');
  const subtasksList = document.getElementById('jiraSubtasksList');
  const subtaskCount = document.getElementById('jiraSubtaskCount');

  if (!silent) {
    if (keyEl) keyEl.textContent = key;
    if (summaryEl) summaryEl.textContent = 'Đang tải thông tin ticket...';
    if (descEl) descEl.innerHTML = '<div class="py-4 text-center text-slate-400">Đang tải mô tả chi tiết...</div>';
  }

  try {
    const res = await fetch(`/api/jira/issue?key=${encodeURIComponent(key)}`);
    const data = await res.json();
    if (data && data.success && data.issue) {
      const issue = data.issue;
      window.activeJiraIssue = issue;
      renderJiraIssuesList();

      if (keyEl) keyEl.textContent = issue.key;
      if (keyLink) keyLink.href = issue.url || '#';
      if (summaryEl) summaryEl.textContent = issue.summary || '(Không có tiêu đề)';
      if (assigneeEl) assigneeEl.textContent = issue.assignee || 'Chưa gán';
      if (reporterEl) reporterEl.textContent = issue.reporter || 'Chưa rõ';
      if (updatedEl) updatedEl.textContent = formatJiraDate(issue.updated);
      if (issue.my_account_id) {
        window.currentJiraUserAccountId = issue.my_account_id;
      }
      if (issue.my_profile) {
        window.currentJiraUserProfile = issue.my_profile;
      }
      renderTicketAssignee(issue);
      loadJiraAssignableUsers(issue.key);

      if (typeBadge) {
        const typeInfo = getJiraTypeBadgeInfo(issue.issuetype);
        typeBadge.textContent = typeInfo.label;
        typeBadge.title = typeInfo.title;
        typeBadge.className = `text-[10px] font-sans font-semibold px-2 py-0.5 rounded border ${typeInfo.className}`;
      }

      if (prioBadge) {
        prioBadge.textContent = issue.priority || 'Medium';
      }

      // Render Description: phân cách dòng thoáng đãng, dễ đọc
      if (descEl) {
        if (issue.description_html) {
          descEl.classList.remove('is-plaintext');
          descEl.innerHTML = issue.description_html;
        } else if (issue.description_text) {
          descEl.classList.add('is-plaintext');
          descEl.textContent = issue.description_text;
        } else {
          descEl.classList.remove('is-plaintext');
          descEl.innerHTML = '<span class="text-slate-400 italic">Ticket này không có mô tả chi tiết.</span>';
        }
      }

      // Render Minh chứng Video & Tệp đính kèm (mp4, webm, images, docs)
      const attSection = document.getElementById('jiraDetailAttachmentsSection');
      const attCount = document.getElementById('jiraAttachmentCount');
      const attList = document.getElementById('jiraDetailAttachmentsList');
      const attachments = issue.attachments || [];
      if (attCount) attCount.textContent = attachments.length;
      if (attSection && attList) {
        if (attachments.length > 0) {
          attSection.classList.remove('hidden');
          renderJiraAttachments(attachments, attList);
        } else {
          attSection.classList.add('hidden');
          attList.innerHTML = '';
        }
      }

      // Render Sub-tasks
      const subtasks = issue.subtasks || [];
      if (subtaskCount) subtaskCount.textContent = subtasks.length;
      if (subtasksList) {
        if (subtasks.length === 0) {
          subtasksList.innerHTML = '<p class="text-[11px] text-slate-400 italic p-2.5 text-center">Chưa có Sub-task nào trên ticket này. Bấm "+ Tạo Sub-task" để thêm.</p>';
        } else {
          subtasksList.innerHTML = subtasks.map(st => {
            const isDone = st.status_category === 'done' || /done|closed|resolved/i.test(st.status);
            const isInProgress = st.status_category === 'indeterminate' || /in progress|doing|testing|review/i.test(st.status);
            let statusClass = 'jira-status-todo';
            if (isDone) statusClass = 'jira-status-done';
            else if (isInProgress) statusClass = 'jira-status-inprogress';

            // Danh sách transitions khả dụng cho sub-task như Jira
            const transitions = (Array.isArray(st.transitions) && st.transitions.length > 0)
              ? st.transitions
              : [
                  { id: '31', name: 'To Do', to_status: 'To Do' },
                  { id: '11', name: 'In Progress', to_status: 'In Progress' },
                  { id: '21', name: 'Done', to_status: 'Done' }
                ];

            const currentStatusLower = String(st.status || '').trim().toLowerCase();
            const transOptions = transitions.map(tr => {
              const trName = tr.to_status || tr.name;
              const isSelected = trName.toLowerCase() === currentStatusLower;
              const trVal = tr.id || trName;
              return `<option value="${escapeHtml(trVal)}" ${isSelected ? 'selected' : ''}>${escapeHtml(trName)}</option>`;
            }).join('');

            // Sub-task Assignee options
            const subtaskAssigneeOpts = renderSubtaskAssigneeOptions(st.assignee_account_id || '', st.assignee || '');
            const initial = (st.assignee && st.assignee !== 'Chưa gán') ? st.assignee.trim()[0].toUpperCase() : '';
            const isMe = Boolean(window.currentJiraUserAccountId && st.assignee_account_id === window.currentJiraUserAccountId);
            const displayLabel = st.assignee ? (isMe ? `${st.assignee} (Tôi)` : st.assignee) : 'Chưa gán';

            return `
              <div class="jira-subtask-card p-2.5 rounded-lg bg-[#0c1628] border border-[#244170]/70 flex items-center justify-between gap-2.5 text-xs">
                <div class="flex items-center gap-2 min-w-0">
                  <a href="${escapeHtml(st.url || '#')}" target="_blank" class="font-mono text-[11px] font-bold text-blue-400 hover:underline shrink-0" title="Mở Sub-task trên Jira Cloud">
                    ${escapeHtml(st.key)}
                  </a>
                  <span class="text-slate-200 truncate font-sans text-xs" title="${escapeHtml(st.summary)}">${escapeHtml(st.summary)}</span>
                </div>
                <div class="flex items-center gap-2 shrink-0">
                  <!-- Custom Assignee Trigger with Avatar & Name -->
                  <button type="button"
                    onclick="openSubtaskAssigneeMenu('${escapeHtml(st.key)}', event, this)"
                    data-subtask-key="${escapeHtml(st.key)}"
                    class="jira-subtask-assignee-trigger inline-flex items-center gap-1.5 px-2.5 py-1 rounded-lg bg-[#101e38] border border-[#244170] hover:border-[#1677ff] text-slate-200 text-xs font-sans cursor-pointer transition select-none max-w-[175px]"
                    title="Người thực hiện: ${escapeHtml(displayLabel)}${st.assignee_email ? ' (' + escapeHtml(st.assignee_email) + ')' : ''}">
                    <span class="w-4 h-4 rounded-full bg-slate-700 overflow-hidden inline-flex items-center justify-center shrink-0 text-[9.5px] font-bold text-slate-200 subtask-avatar-box">
                      ${st.assignee_avatar
                        ? `<img src="${escapeHtml(st.assignee_avatar)}" class="w-full h-full object-cover rounded-full" alt="" />`
                        : (initial
                            ? escapeHtml(initial)
                            : `<svg class="w-2.5 h-2.5 text-slate-400" fill="currentColor" viewBox="0 0 20 20"><path fill-rule="evenodd" d="M10 9a3 3 0 100-6 3 3 0 000 6zm-7 9a7 7 0 1114 0H3z" clip-rule="evenodd"></path></svg>`)}
                    </span>
                    <span class="truncate subtask-name-box text-[11px] font-medium text-slate-200">${escapeHtml(displayLabel)}</span>
                    <svg class="w-3 h-3 text-slate-400 shrink-0 ml-0.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                      <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 9l-7 7-7-7" />
                    </svg>
                  </button>

                  <!-- Hidden native select for form and test safety -->
                  <select onchange="onSubtaskAssigneeChange('${escapeHtml(st.key)}', this.value, this)"
                    data-subtask-key="${escapeHtml(st.key)}"
                    data-current="${escapeHtml(st.assignee_account_id || '')}"
                    class="hidden jira-subtask-assignee-select"
                    title="Người thực hiện: ${escapeHtml(st.assignee || 'Chưa gán')}">
                    ${subtaskAssigneeOpts}
                  </select>

                  <select onchange="onSubtaskTransitionChange('${escapeHtml(st.key)}', this.value, this)"
                    data-current="${escapeHtml(st.status)}"
                    class="jira-subtask-status-select text-[10px] font-sans font-semibold px-2 py-0.5 rounded border ${statusClass} cursor-pointer focus:outline-none"
                    title="Chuyển trạng thái Sub-task">
                    ${transOptions}
                  </select>
                </div>
              </div>
            `;
          }).join('');
        }
      }

      // Render Transitions: chỉ người được gán (assignee) hoặc người tạo (reporter) mới được đổi trạng thái
      if (transitionSelect) {
        const canTransition = (typeof issue.can_transition === 'boolean')
          ? issue.can_transition
          : (issue.is_mine !== false);
        const currentOpt = `<option value="" disabled selected>${escapeHtml(issue.status)} (Hiện tại)</option>`;
        if (!canTransition) {
          transitionSelect.innerHTML = currentOpt +
            '<option value="" disabled>Chỉ người được gán hoặc người tạo ticket mới được đổi trạng thái</option>';
          transitionSelect.disabled = true;
          transitionSelect.classList.add('is-locked');
          transitionSelect.title = 'Bạn không phải người được gán hoặc người tạo Ticket này nên không thể đổi trạng thái.';
        } else {
          const transOpts = (issue.transitions || []).map(t =>
            `<option value="${escapeHtml(t.id)}">→ Chuyển sang: ${escapeHtml(t.name || t.to_status)}</option>`
          ).join('');
          transitionSelect.innerHTML = currentOpt + transOpts;
          transitionSelect.disabled = false;
          transitionSelect.classList.remove('is-locked');
          transitionSelect.title = 'Chuyển trạng thái Ticket';
        }
      }

      // Render Comments
      if (commentCount) commentCount.textContent = (issue.comments || []).length;
      if (commentsList) {
        const comments = issue.comments || [];
        if (comments.length === 0) {
          commentsList.innerHTML = '<p class="text-[11px] text-slate-400 italic p-3 text-center">Chưa có bình luận nào trên ticket này.</p>';
        } else {
          commentsList.innerHTML = comments.map(c => `
            <div class="jira-comment-box p-3 rounded-lg bg-[#0c1628] border border-[#244170]/60 space-y-1.5 text-xs">
              <div class="flex items-center justify-between text-[11px]">
                <span class="font-semibold text-slate-200">${escapeHtml(c.author)}</span>
                <span class="font-mono text-[10px] text-slate-400">${formatJiraDate(c.created)}</span>
              </div>
              <div class="text-slate-300 leading-relaxed break-words font-sans">
                ${c.body_html || escapeHtml(c.body_text || '')}
              </div>
            </div>
          `).join('');
        }
      }
    } else if (!silent) {
      showToast((data && data.message) || 'Lỗi khi tải chi tiết ticket', 'error');
    }
  } catch (err) {
    if (!silent) showToast('Lỗi kết nối khi tải ticket: ' + err.message, 'error');
  }
}
window.selectJiraIssue = selectJiraIssue;

/**
 * Hiển thị video minh chứng và danh sách file đính kèm của Ticket Jira
 */
function renderJiraAttachments(attachments, container) {
  if (!container) return;
  if (!Array.isArray(attachments) || attachments.length === 0) {
    container.innerHTML = '';
    return;
  }

  const videos = attachments.filter(a => a.is_video);
  const others = attachments.filter(a => !a.is_video);

  let html = '';

  // 1. Video minh chứng lỗi (HTML5 Video Player)
  if (videos.length > 0) {
    html += videos.map(v => `
      <div class="jira-evidence-video-card p-3 rounded-lg bg-[#0c1628] border border-[#244170]/80 space-y-2">
        <div class="flex items-center justify-between text-xs text-slate-200">
          <div class="flex items-center gap-2 truncate">
            <span class="px-1.5 py-0.5 rounded bg-rose-950/80 text-rose-300 border border-rose-800 text-[10px] font-sans font-semibold">Video</span>
            <span class="font-medium truncate text-slate-100" title="${escapeHtml(v.filename)}">${escapeHtml(v.filename)}</span>
            <span class="text-slate-400 text-[11px]">(${escapeHtml(v.size_formatted || '')})</span>
          </div>
          <a href="${escapeHtml(v.url)}" download="${escapeHtml(v.filename)}" class="text-xs text-blue-400 hover:text-blue-300 font-sans flex items-center gap-1 shrink-0">
            <svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4"/></svg>
            <span>Tải video</span>
          </a>
        </div>
        <div class="relative w-full rounded overflow-hidden bg-black/90 border border-slate-700/60 max-h-[420px] flex items-center justify-center">
          <video controls playsinline preload="metadata" class="w-full max-h-[420px] object-contain" src="${escapeHtml(v.url)}">
            <source src="${escapeHtml(v.url)}" type="${escapeHtml(v.mime_type || 'video/mp4')}">
            Trình duyệt không hỗ trợ thẻ phát video HTML5.
          </video>
        </div>
      </div>
    `).join('');
  }

  // 2. Hình ảnh & Tệp đính kèm khác
  if (others.length > 0) {
    html += '<div class="grid grid-cols-2 md:grid-cols-4 gap-2 pt-1">';
    html += others.map(att => {
      if (att.is_image) {
        return `
          <a href="${escapeHtml(att.url)}" target="_blank" class="group relative rounded-lg overflow-hidden border border-[#244170] bg-[#0c1628] hover:border-[#1677ff] transition block aspect-video">
            <img src="${escapeHtml(att.url)}" alt="${escapeHtml(att.filename)}" class="w-full h-full object-cover group-hover:scale-105 transition duration-200" loading="lazy" />
            <div class="absolute inset-x-0 bottom-0 bg-gradient-to-t from-black/80 to-transparent p-1.5 text-[10px] text-white truncate">
              ${escapeHtml(att.filename)}
            </div>
          </a>
        `;
      } else {
        return `
          <a href="${escapeHtml(att.url)}" download="${escapeHtml(att.filename)}" class="flex items-center gap-2 p-2 rounded-lg border border-[#244170] bg-[#0c1628] hover:border-[#1677ff] transition text-xs text-slate-200 truncate">
            <svg class="w-4 h-4 text-slate-400 shrink-0" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" d="M7 21h10a2 2 0 002-2V9.414a1 1 0 00-.293-.707l-5.414-5.414A1 1 0 0012.586 3H7a2 2 0 00-2 2v14a2 2 0 002 2z"/></svg>
            <div class="truncate min-w-0">
              <div class="truncate font-medium text-[11px]">${escapeHtml(att.filename)}</div>
              <div class="text-[10px] text-slate-400">${escapeHtml(att.size_formatted || '')}</div>
            </div>
          </a>
        `;
      }
    }).join('');
    html += '</div>';
  }

  container.innerHTML = html;
}
window.renderJiraAttachments = renderJiraAttachments;

function setJiraFilter(filterType) {
  window.activeJiraFilter = filterType;
  const filters = ['all', 'story', 'bug', 'my', 'inprogress', 'todo', 'done'];
  filters.forEach(f => {
    const btn = document.getElementById('jiraFilterBtn_' + f);
    if (!btn) return;
    if (f === filterType) {
      btn.className = 'px-3 py-1.5 rounded bg-[#1677ff] text-white font-semibold transition cursor-pointer select-none jira-filter-btn is-active';
    } else {
      btn.className = 'px-3 py-1.5 rounded text-slate-300 hover:text-white hover:bg-white/5 font-medium transition cursor-pointer select-none jira-filter-btn';
    }
  });

  const filterNames = {
    'all': 'Tất cả tickets',
    'story': 'Tính năng (Feat)',
    'bug': 'Sửa lỗi (Bug)',
    'my': 'Task của tôi',
    'inprogress': 'Đang thực hiện',
    'todo': 'Cần làm',
    'done': 'Đã hoàn thành'
  };
  const activeLabel = document.getElementById('jiraActiveFilterName');
  if (activeLabel) activeLabel.textContent = filterNames[filterType] || 'Bộ lọc';

  updateJiraLocalFilterBadge();
  const menu = document.getElementById('jiraLocalFilterMenu');
  if (menu && !menu.classList.contains('hidden')) {
    renderJiraLocalFilterMenu();
  }

  fetchJiraIssues();
}
window.setJiraFilter = setJiraFilter;

function onJiraProjectChange() {
  fetchJiraIssues();
}
window.onJiraProjectChange = onJiraProjectChange;

// Live Debounced Search
function onJiraSearchInput() {
  const input = document.getElementById('jiraSearchInput');
  const clearBtn = document.getElementById('btnClearJiraSearch');
  const val = input ? input.value.trim() : '';

  if (clearBtn) {
    if (val) clearBtn.classList.remove('hidden');
    else clearBtn.classList.add('hidden');
  }

  if (jiraSearchDebounceTimer) {
    clearTimeout(jiraSearchDebounceTimer);
  }
  jiraSearchDebounceTimer = setTimeout(() => {
    fetchJiraIssues(val);
  }, 300);
}
window.onJiraSearchInput = onJiraSearchInput;

function searchJiraTickets() {
  if (jiraSearchDebounceTimer) {
    clearTimeout(jiraSearchDebounceTimer);
    jiraSearchDebounceTimer = null;
  }
  const input = document.getElementById('jiraSearchInput');
  const clearBtn = document.getElementById('btnClearJiraSearch');
  const val = input ? input.value.trim() : '';

  if (clearBtn) {
    if (val) clearBtn.classList.remove('hidden');
    else clearBtn.classList.add('hidden');
  }

  fetchJiraIssues(val);
}
window.searchJiraTickets = searchJiraTickets;

function clearJiraSearch() {
  if (jiraSearchDebounceTimer) {
    clearTimeout(jiraSearchDebounceTimer);
    jiraSearchDebounceTimer = null;
  }
  const input = document.getElementById('jiraSearchInput');
  const clearBtn = document.getElementById('btnClearJiraSearch');
  if (input) {
    input.value = '';
    input.focus();
  }
  if (clearBtn) clearBtn.classList.add('hidden');
  fetchJiraIssues('');
}
window.clearJiraSearch = clearJiraSearch;

// ============================================================
// AI AGENT DISPATCH ACTIONS & BDD FORMATTING
// ============================================================

/**
 * Tự động phân đoạn và định dạng văn bản Jira theo chuẩn BDD / Gherkin & Markdown rõ ràng, dễ nhìn.
 */
function formatJiraText(text) {
  if (!text) return '';
  let s = String(text).trim();

  // Chuẩn hóa ký tự xuống dòng
  s = s.replace(/\r\n/g, '\n').replace(/\r/g, '\n');

  // Format Acceptance Criteria / Tiêu chí chấp nhận headers
  s = s.replace(/(?:^|\n|\s+)(Acceptance Criteria[^\n]*?|Tiêu chí chấp nhận[^\n]*?)(?=(?:\s+(?:AC\s*\d+|Kịch bản|Scenario)|$|\n))/gi, '\n\n### $1\n');

  // Format AC1, AC2, AC3 / Kịch bản 1 / Scenario 1
  s = s.replace(/(?:^|\n|\s+)((?:AC\s*\d+|Kịch bản\s*\d+|Scenario\s*\d+)[\s:\-]+[^\n]*?)(?=(?:\s+(?:Given|When|Then|And|But)\b|$|\n))/g, '\n\n#### $1\n');

  // Format BDD Given / When / Then / And / But
  s = s.replace(/(?:^|\n|\s+)\b(Given)\b\s*[:\-]?\s*([^\n]*?)(?=(?:\s+\b(?:When|Then|And|But|AC\s*\d+|Kịch bản|Scenario)\b|$|\n))/g, '\n- **Given**: $2');
  s = s.replace(/(?:^|\n|\s+)\b(When)\b\s*[:\-]?\s*([^\n]*?)(?=(?:\s+\b(?:Then|And|But|AC\s*\d+|Given|Kịch bản|Scenario)\b|$|\n))/g, '\n- **When**: $2');
  s = s.replace(/(?:^|\n|\s+)\b(Then)\b\s*[:\-]?\s*([^\n]*?)(?=(?:\s+\b(?:And|But|AC\s*\d+|Given|When|Kịch bản|Scenario)\b|$|\n))/g, '\n- **Then**: $2');
  s = s.replace(/(?:^|\n|\s+)\b(And)\b\s*[:\-]?\s*([^\n]*?)(?=(?:\s+\b(?:And|But|AC\s*\d+|Given|When|Then|Kịch bản|Scenario)\b|$|\n))/g, '\n  - **And**: $2');
  s = s.replace(/(?:^|\n|\s+)\b(But)\b\s*[:\-]?\s*([^\n]*?)(?=(?:\s+\b(?:And|But|AC\s*\d+|Given|When|Then|Kịch bản|Scenario)\b|$|\n))/g, '\n  - **But**: $2');

  // Format các đề mục kiểm thử / Bug report thông dụng nếu dính liền
  const headings = [
    'Hiện tượng lỗi', 'Mô tả lỗi', 'Bug description',
    'Các bước tái hiện', 'Steps to reproduce',
    'Kết quả thực tế', 'Actual result',
    'Kết quả mong muốn', 'Expected result',
    'Môi trường', 'Environment',
    'Mục tiêu', 'Objective',
    'Yêu cầu chức năng', 'Functional requirements'
  ];
  headings.forEach(h => {
    const re = new RegExp(`(?:^|\\n|(?:(?<=[.!?])\\s+))(${h})\\s*:\\s*`, 'gi');
    s = s.replace(re, '\n\n### $1:\n');
  });

  // Dọn dẹp khoảng trắng dư thừa
  const lines = s.split('\n').map(line => line.replace(/[ \t]+/g, ' ').trimEnd());
  s = lines.join('\n');
  s = s.replace(/\n{3,}/g, '\n\n');
  return s.trim();
}
window.formatJiraText = formatJiraText;

function formatTaskPromptInput() {
  const promptInput = document.getElementById('taskPromptInput');
  if (!promptInput) return;
  const val = promptInput.value;
  if (!val || !val.trim()) {
    showToast('Khung yêu cầu đang trống!', 'info');
    return;
  }
  const formatted = formatJiraText(val);
  if (formatted === val) {
    showToast('Nội dung đã ở định dạng chuẩn tối ưu!', 'info');
    return;
  }
  promptInput.value = formatted;
  if (typeof onTaskPromptInput === 'function') {
    onTaskPromptInput();
  }
  showToast('Đã định dạng lại nội dung theo chuẩn BDD & đề mục!', 'success');
}
window.formatTaskPromptInput = formatTaskPromptInput;

function sendActiveJiraToTask() {
  const issue = window.activeJiraIssue;
  if (!issue || !issue.key) {
    showToast('Vui lòng chọn một Ticket để đưa vào Tác vụ!', 'error');
    return;
  }

  const promptInput = document.getElementById('taskPromptInput');
  if (!promptInput) {
    showToast('Không tìm thấy khung nhập Tác vụ!', 'error');
    return;
  }

  const key = issue.key;
  const summary = (issue.summary || '').trim();
  const rawDesc = (issue.description_text || issue.description || '').trim();
  const cleanDesc = formatJiraText(rawDesc);
  const isBug = (issue.issuetype || '').toLowerCase().includes('bug');

  if (typeof setTaskActionType === 'function') {
    setTaskActionType(isBug ? 'fixbug' : 'task');
  }

  let formattedPrompt = `[Jira ${key}] ${summary}`;
  if (cleanDesc) {
    formattedPrompt += `\n\n${cleanDesc}`;
  }
  if (issue.comments && issue.comments.length > 0) {
    const recentComments = issue.comments.slice(-3).map(c => {
      const author = c.author || 'Thành viên';
      const timeStr = c.created ? ` (${formatJiraDate(c.created)})` : '';
      const body = formatJiraText(c.body_text || '').trim();
      return `- **${author}**${timeStr}:\n  ${body.replace(/\n/g, '\n  ')}`;
    }).filter(Boolean).join('\n\n');
    if (recentComments) {
      formattedPrompt += `\n\n### Thảo luận gần nhất:\n${recentComments}`;
    }
  }

  promptInput.value = formattedPrompt.trim();

  if (typeof parallelTasks !== 'undefined' && Array.isArray(parallelTasks)) {
    const cur = parallelTasks.find(t => t.id === activeTaskId);
    if (cur) {
      cur.name = `${key}: ${summary.slice(0, 24)}`;
      cur.isCustomName = true;
      cur.prompt = formattedPrompt.trim();
      cur.type = isBug ? 'fixbug' : 'task';
      if (typeof renderParallelTaskTabs === 'function') renderParallelTaskTabs();
    }
  }

  if (typeof onTaskPromptInput === 'function') {
    onTaskPromptInput();
  } else {
    promptInput.dispatchEvent(new Event('input', { bubbles: true }));
  }

  switchTab('task');

  setTimeout(() => {
    promptInput.focus();
    promptInput.scrollIntoView({ behavior: 'smooth', block: 'center' });
  }, 100);

  showToast(`Đã đưa Ticket [${key}] sang Tác vụ Agent thành công!`, 'success');
}
window.sendActiveJiraToTask = sendActiveJiraToTask;

/**
 * Tạo nhánh mới theo quy tắc: <type>/<initials>/<ticket-id>/<english-slug>
 * và chuyển sang màn hình Checkout Branch
 */
function createGitBranchFromActiveJira() {
  const issue = window.activeJiraIssue;
  if (!issue || !issue.key) {
    showToast('Vui lòng chọn một Ticket trước!', 'error');
    return;
  }

  if (typeof formatJiraBranchName !== 'function' || typeof navigateToGitCheckoutBranch !== 'function') {
    showToast('Đang nạp mô-đun nhánh Git...', 'info');
    return;
  }

  const branchName = formatJiraBranchName(issue);
  navigateToGitCheckoutBranch(branchName);
}
window.createGitBranchFromActiveJira = createGitBranchFromActiveJira;

function copyJiraTicketPrompt() {
  const issue = window.activeJiraIssue;
  if (!issue || !issue.key) return;

  const text = `[Jira ${issue.key}] ${issue.summary}\n\n${issue.description_text || ''}`;
  if (navigator.clipboard) {
    navigator.clipboard.writeText(text).then(() => {
      showToast(`Đã sao chép nội dung Ticket [${issue.key}]!`, 'success');
    });
  }
}
window.copyJiraTicketPrompt = copyJiraTicketPrompt;

async function submitJiraComment() {
  const issue = window.activeJiraIssue;
  if (!issue || !issue.key) {
    showToast('Chưa chọn ticket nào!', 'error');
    return;
  }

  const commentInput = document.getElementById('jiraNewCommentText');
  const commentText = commentInput ? commentInput.value.trim() : '';
  if (!commentText) {
    showToast('Vui lòng nhập nội dung bình luận!', 'error');
    return;
  }

  const btn = document.getElementById('btnSubmitJiraComment');
  if (btn) btn.disabled = true;

  try {
    const res = await fetch('/api/jira/comment', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        key: issue.key,
        comment: commentText
      })
    });
    const d = await res.json();
    if (d && d.success) {
      showToast('Đã thêm bình luận lên Jira thành công!', 'success');
      if (commentInput) commentInput.value = '';
      selectJiraIssue(issue.key);
    } else {
      showToast((d && d.message) || 'Lỗi khi gửi bình luận', 'error');
    }
  } catch (err) {
    showToast('Lỗi kết nối: ' + err.message, 'error');
  } finally {
    if (btn) btn.disabled = false;
  }
}
window.submitJiraComment = submitJiraComment;

async function onJiraTransitionChange(transitionId) {
  const issue = window.activeJiraIssue;
  if (!issue || !issue.key || !transitionId) return;

  const select = document.getElementById('jiraDetailTransitionSelect');

  // Chặn đổi trạng thái ticket không liên quan đến người dùng hiện tại
  const canTransition = (typeof issue.can_transition === 'boolean')
    ? issue.can_transition
    : (issue.is_mine !== false);
  if (!canTransition) {
    showToast('Bạn chỉ có thể đổi trạng thái Ticket do mình tạo hoặc được gán cho mình.', 'error');
    if (select) select.selectedIndex = 0;
    return;
  }

  const selText = select ? select.options[select.selectedIndex]?.text : '';

  const confirmed = await antdConfirm({
    title: 'Xác nhận chuyển trạng thái',
    content: `Bạn có chắc muốn chuyển Ticket <span class="font-mono font-bold text-blue-400">${issue.key}</span> sang trạng thái mới?\n\n<strong class="text-white">${selText}</strong>`,
    okText: 'Chuyển trạng thái'
  });

  if (!confirmed) {
    if (select) select.selectedIndex = 0;
    return;
  }

  try {
    const res = await fetch('/api/jira/transition', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        key: issue.key,
        transition_id: transitionId
      })
    });
    const d = await res.json();
    if (d && d.success) {
      showToast(d.message || 'Đã chuyển trạng thái ticket thành công!', 'success');
      selectJiraIssue(issue.key);
      fetchJiraIssues();
    } else {
      showToast((d && d.message) || 'Lỗi khi chuyển trạng thái', 'error');
      if (select) select.selectedIndex = 0;
    }
  } catch (err) {
    showToast('Lỗi kết nối: ' + err.message, 'error');
    if (select) select.selectedIndex = 0;
  }
}
window.onJiraTransitionChange = onJiraTransitionChange;

// ============================================================
// ATLASSIAN ROVO AI REQUIREMENT ANALYZER
// ============================================================

function toggleRovoBox(show = true) {
  const box = document.getElementById('jiraRovoAnalysisBox');
  if (!box) return;
  if (show) box.classList.remove('hidden');
  else box.classList.add('hidden');
}
window.toggleRovoBox = toggleRovoBox;

function renderMarkdownSimple(md) {
  if (!md) return '';
  let html = escapeHtml(md);
  // Headings
  html = html.replace(/^### (.*$)/gim, '<h3 class="rovo-heading-3">$1</h3>');
  html = html.replace(/^## (.*$)/gim, '<h2 class="rovo-heading-2">$1</h2>');
  html = html.replace(/^# (.*$)/gim, '<h1 class="rovo-heading-1">$1</h1>');
  // Bold
  html = html.replace(/\*\*(.*?)\*\*/gim, '<strong>$1</strong>');
  // Checkbox items
  html = html.replace(/^- \[ \] (.*$)/gim, '<div class="rovo-checkbox-item"><span class="rovo-checkbox-box"></span><span>$1</span></div>');
  html = html.replace(/^- \[x\] (.*$)/gim, '<div class="rovo-checkbox-item is-checked"><span class="rovo-checkbox-box is-checked">✓</span><span class="line-through text-slate-400">$1</span></div>');
  // Bullets
  html = html.replace(/^- (.*$)/gim, '<li class="rovo-bullet-item">$1</li>');
  // Linebreaks
  html = html.replace(/\n\n/gim, '<br/>');
  return html;
}
window.renderMarkdownSimple = renderMarkdownSimple;

function renderRovoAnalysisContent(analysisText, engineName) {
  const contentEl = document.getElementById('jiraRovoAnalysisContent');
  const engineBadge = document.getElementById('jiraRovoEngineBadge');
  if (engineBadge) {
    // Nhãn hiển thị cố định: đây là kết quả phân tích (engine chỉ giữ trong tooltip)
    engineBadge.textContent = 'Kết quả phân tích';
    engineBadge.title = engineName ? `Nguồn phân tích: ${engineName}` : 'Kết quả phân tích của Atlassian Rovo AI';
  }
  if (!contentEl) return;

  try {
    if (typeof marked !== 'undefined' && marked.parse) {
      contentEl.innerHTML = marked.parse(analysisText);
    } else {
      contentEl.innerHTML = renderMarkdownSimple(analysisText);
    }
  } catch (e) {
    contentEl.innerHTML = renderMarkdownSimple(analysisText);
  }
}
window.renderRovoAnalysisContent = renderRovoAnalysisContent;

/**
 * Bật/tắt nút "Đưa vào Tác vụ" trong bảng Rovo.
 * Chỉ bật khi đã có bản phân tích hoàn chỉnh của Ticket hiện tại.
 */
function setRovoSendButtonEnabled(enabled) {
  const btn = document.getElementById('btnRovoSendToTask');
  if (!btn) return;
  btn.disabled = !enabled;
  if (enabled) {
    btn.classList.remove('opacity-50', 'cursor-not-allowed');
    btn.classList.add('cursor-pointer');
    btn.title = 'Đưa bản phân tích kỹ thuật này sang ô Tác vụ Agent để tiến hành code';
  } else {
    btn.classList.add('opacity-50', 'cursor-not-allowed');
    btn.classList.remove('cursor-pointer');
    btn.title = 'Vui lòng chờ Rovo AI phân tích xong để đưa bản phân tích sang Tác vụ Agent';
  }
}
window.setRovoSendButtonEnabled = setRovoSendButtonEnabled;

async function analyzeJiraDescriptionWithRovo() {
  const issue = window.activeJiraIssue;
  if (!issue || !issue.key) {
    showToast('Vui lòng chọn một Ticket trước khi phân tích!', 'error');
    return;
  }

  const box = document.getElementById('jiraRovoAnalysisBox');
  const contentEl = document.getElementById('jiraRovoAnalysisContent');
  const engineBadge = document.getElementById('jiraRovoEngineBadge');
  const btn = document.getElementById('btnRovoAnalyze');

  toggleRovoBox(true);
  if (box) {
    box.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
  }

  if (contentEl) {
    contentEl.innerHTML = `
      <div class="p-5 text-center text-slate-300 text-xs font-sans space-y-2.5">
        <div class="inline-block w-6 h-6 border-2 border-indigo-400 border-t-transparent rounded-full animate-spin"></div>
        <p class="font-semibold text-indigo-300">Atlassian Rovo AI đang phân tích chi tiết yêu cầu...</p>
        <p class="text-[11px] text-slate-400">Đang bóc tách phạm vi Frontend (easysalon-webapp) & Backend (easysalon-api)...</p>
      </div>
    `;
  }
  // Chưa có kết quả phân tích mới -> khoá nút "Đưa vào Tác vụ" cho tới khi phân tích xong
  window.activeRovoAnalysisText = '';
  setRovoSendButtonEnabled(false);
  if (btn) btn.disabled = true;

  try {
    const res = await fetch('/api/jira/rovo-analyze', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        key: issue.key,
        summary: issue.summary,
        description: issue.description_text || issue.description || '',
        issuetype: issue.issuetype || 'Task',
        comments: issue.comments || []
      })
    });
    const d = await res.json();
    if (d && d.success && d.analysis) {
      window.activeRovoAnalysisText = d.analysis;
      window.jiraRovoCache = window.jiraRovoCache || {};
      window.jiraRovoCache[issue.key] = {
        analysis: d.analysis,
        engine: d.engine || 'Atlassian Rovo',
        ts: Date.now()
      };
      // Lưu bền vào localStorage để reload trang không mất kết quả phân tích
      saveRovoCacheToStorage();

      // Đảm bảo box luôn mở và render dữ liệu
      toggleRovoBox(true);
      renderRovoAnalysisContent(d.analysis, d.engine);
      // Phân tích đã hoàn tất -> mở khoá nút "Đưa vào Tác vụ"
      setRovoSendButtonEnabled(true);
      showToast('Atlassian Rovo AI đã phân tích yêu cầu thành công!', 'success');
      if (box) {
        box.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
      }
    } else {
      setRovoSendButtonEnabled(false);
      if (contentEl) {
        contentEl.innerHTML = `<p class="text-rose-400 text-xs p-3">${escapeHtml((d && d.message) || 'Không thể hoàn thành phân tích Rovo')}</p>`;
      }
    }
  } catch (err) {
    setRovoSendButtonEnabled(false);
    if (contentEl) {
      contentEl.innerHTML = `<p class="text-rose-400 text-xs p-3">Lỗi kết nối tới Rovo AI: ${escapeHtml(err.message)}</p>`;
    }
  } finally {
    if (btn) btn.disabled = false;
  }
}
window.analyzeJiraDescriptionWithRovo = analyzeJiraDescriptionWithRovo;

function copyRovoAnalysisText() {
  if (!window.activeRovoAnalysisText) {
    showToast('Chưa có nội dung phân tích để sao chép!', 'error');
    return;
  }
  if (navigator.clipboard) {
    navigator.clipboard.writeText(window.activeRovoAnalysisText).then(() => {
      showToast('Đã sao chép toàn bộ bản phân tích Rovo AI!', 'success');
    });
  }
}
window.copyRovoAnalysisText = copyRovoAnalysisText;

function sendRovoAnalysisToTask() {
  const issue = window.activeJiraIssue;
  if (!issue || !issue.key || !window.activeRovoAnalysisText) {
    showToast('Chưa có bản phân tích Rovo nào để đưa vào tác vụ!', 'error');
    return;
  }

  const promptInput = document.getElementById('taskPromptInput');
  if (!promptInput) {
    showToast('Không tìm thấy khung nhập Tác vụ!', 'error');
    return;
  }

  const key = issue.key;
  const isBug = (issue.issuetype || '').toLowerCase().includes('bug');
  if (typeof setTaskActionType === 'function') {
    setTaskActionType(isBug ? 'fixbug' : 'task');
  }

  const fullPrompt = `[Jira ${key}] ${issue.summary}\n\n=== BẢN PHÂN TÍCH KỸ THUẬT ATLASSIAN ROVO AI ===\n${window.activeRovoAnalysisText}`;
  promptInput.value = fullPrompt.trim();

  if (typeof onTaskPromptInput === 'function') {
    onTaskPromptInput();
  } else {
    promptInput.dispatchEvent(new Event('input', { bubbles: true }));
  }

  switchTab('task');
  setTimeout(() => {
    promptInput.focus();
    promptInput.scrollIntoView({ behavior: 'smooth', block: 'center' });
  }, 100);

  showToast(`Đã đưa bản phân tích Rovo của [${key}] vào Tác vụ Agent!`, 'success');
}
window.sendRovoAnalysisToTask = sendRovoAnalysisToTask;

// ============================================================
// JIRA ASSIGNEE MANAGEMENT (TICKET & SUB-TASKS)
// ============================================================

window.jiraAssignableUsers = [];
window.currentJiraUserAccountId = '';
window.currentJiraUserProfile = null;

function getCurrentJiraUser() {
  if (window.currentJiraUserProfile && window.currentJiraUserProfile.displayName) {
    return window.currentJiraUserProfile;
  }
  const myId = window.currentJiraUserAccountId;
  if (myId && Array.isArray(window.jiraAssignableUsers)) {
    const found = window.jiraAssignableUsers.find(u => u.accountId === myId);
    if (found) {
      window.currentJiraUserProfile = {
        accountId: found.accountId,
        displayName: found.displayName,
        email: found.email || '',
        avatar: found.avatar || ''
      };
      return window.currentJiraUserProfile;
    }
  }
  if (window.jiraStatus && window.jiraStatus.user) {
    const u = window.jiraStatus.user;
    window.currentJiraUserProfile = {
      accountId: u.accountId,
      displayName: u.displayName,
      email: u.emailAddress || '',
      avatar: u.avatarUrl || ''
    };
    return window.currentJiraUserProfile;
  }
  return null;
}
window.getCurrentJiraUser = getCurrentJiraUser;

async function loadJiraAssignableUsers(issueKey) {
  if (!issueKey) return;
  try {
    const res = await fetch(`/api/jira/assignable-users?key=${encodeURIComponent(issueKey)}`);
    const data = await res.json();
    if (data && data.success && Array.isArray(data.users)) {
      window.jiraAssignableUsers = data.users;
      if (data.my_account_id) {
        window.currentJiraUserAccountId = data.my_account_id;
      }
      if (data.my_profile) {
        window.currentJiraUserProfile = data.my_profile;
      }

      // Cập nhật lại dropdown Ticket cha
      const issue = window.activeJiraIssue;
      if (issue && issue.key === issueKey) {
        renderTicketAssignee(issue);
        updateSubtaskAssigneeDropdowns(issue.subtasks || []);
      }

      // Cập nhật dropdown trong Modal tạo Sub-task
      populateSubtaskModalAssignees();
    }
  } catch (err) {
    console.error('Không thể tải danh sách assignable users:', err);
  }
}
window.loadJiraAssignableUsers = loadJiraAssignableUsers;

function renderSubtaskAssigneeOptions(currentAccountId, currentDisplayName) {
  let html = `<option value="">Chưa gán (Unassigned)</option>`;
  const users = window.jiraAssignableUsers || [];
  let foundCurrent = !currentAccountId;
  const myUser = getCurrentJiraUser();
  const myId = window.currentJiraUserAccountId || (myUser ? myUser.accountId : '');

  users.forEach(u => {
    const isSel = (u.accountId === currentAccountId);
    if (isSel) foundCurrent = true;
    const isMe = Boolean(myId && u.accountId === myId);
    const emailText = u.email ? ` (${u.email})` : '';
    const label = isMe ? `${escapeHtml(u.displayName)} (Tôi${emailText})` : `${escapeHtml(u.displayName)}${escapeHtml(emailText)}`;
    html += `<option value="${escapeHtml(u.accountId)}" ${isSel ? 'selected' : ''}>${label}</option>`;
  });

  if (!foundCurrent && currentAccountId) {
    const isMe = Boolean(myId && currentAccountId === myId);
    const label = isMe ? `${escapeHtml(currentDisplayName || 'Tôi')} (Tôi)` : escapeHtml(currentDisplayName || 'Người thực hiện');
    html += `<option value="${escapeHtml(currentAccountId)}" selected>${label}</option>`;
  }
  return html;
}
window.renderSubtaskAssigneeOptions = renderSubtaskAssigneeOptions;

function updateSubtaskAssigneeDropdowns(subtasks) {
  if (!Array.isArray(subtasks)) return;
  subtasks.forEach(st => {
    const sel = document.querySelector(`.jira-subtask-assignee-select[data-subtask-key="${st.key}"]`);
    if (sel && !sel.disabled) {
      sel.innerHTML = renderSubtaskAssigneeOptions(st.assignee_account_id || '', st.assignee || '');
      sel.value = st.assignee_account_id || '';
    }
    const triggerBtn = document.querySelector(`.jira-subtask-assignee-trigger[data-subtask-key="${st.key}"]`);
    if (triggerBtn && !triggerBtn.disabled) {
      const avatarBox = triggerBtn.querySelector('.subtask-avatar-box');
      const nameBox = triggerBtn.querySelector('.subtask-name-box');
      const isMe = Boolean(window.currentJiraUserAccountId && st.assignee_account_id === window.currentJiraUserAccountId);
      const displayLabel = st.assignee ? (isMe ? `${st.assignee} (Tôi)` : st.assignee) : 'Chưa gán';
      if (nameBox) nameBox.textContent = displayLabel;
      if (avatarBox) {
        if (st.assignee_avatar) {
          avatarBox.innerHTML = `<img src="${escapeHtml(st.assignee_avatar)}" class="w-full h-full object-cover rounded-full" alt="" />`;
        } else if (st.assignee && st.assignee !== 'Chưa gán') {
          const initial = st.assignee.trim()[0].toUpperCase();
          avatarBox.innerHTML = `<span class="text-[9.5px] font-bold text-slate-200">${escapeHtml(initial)}</span>`;
        } else {
          avatarBox.innerHTML = `<svg class="w-2.5 h-2.5 text-slate-400" fill="currentColor" viewBox="0 0 20 20"><path fill-rule="evenodd" d="M10 9a3 3 0 100-6 3 3 0 000 6zm-7 9a7 7 0 1114 0H3z" clip-rule="evenodd"></path></svg>`;
        }
      }
      triggerBtn.title = `Người thực hiện: ${displayLabel}${st.assignee_email ? ' (' + st.assignee_email + ')' : ''}`;
    }
  });
}

function updateSubtaskModalAssigneeHint(selectedId) {
  const hintEl = document.getElementById('jiraSubtaskAssigneeHint');
  if (!hintEl) return;

  const users = window.jiraAssignableUsers || [];
  const myUser = getCurrentJiraUser();
  const myId = window.currentJiraUserAccountId || (myUser ? myUser.accountId : '');

  if (!selectedId) {
    hintEl.innerHTML = `<span class="text-slate-400">Chưa gán người thực hiện</span>`;
    return;
  }

  if (selectedId === myId || selectedId === 'me') {
    const name = myUser ? (myUser.displayName || 'Tài khoản của bạn') : 'Tài khoản của bạn';
    const email = myUser ? (myUser.email || myUser.emailAddress || '') : '';
    const emailHtml = email ? ` &bull; <span class="text-slate-300 font-mono text-[10.5px]">${escapeHtml(email)}</span>` : '';
    hintEl.innerHTML = `
      <span class="inline-block w-2 h-2 rounded-full bg-emerald-400 shrink-0"></span>
      <span class="text-slate-300">Gán cho: <strong class="text-white">${escapeHtml(name)} (Tôi)</strong>${emailHtml}</span>
    `;
    return;
  }

  const found = users.find(u => u.accountId === selectedId);
  if (found) {
    hintEl.innerHTML = `
      <span class="inline-block w-2 h-2 rounded-full bg-blue-400 shrink-0"></span>
      <span class="text-slate-300">Gán cho: <strong class="text-white">${escapeHtml(found.displayName)}</strong></span>
    `;
  } else {
    hintEl.innerHTML = ``;
  }
}
window.updateSubtaskModalAssigneeHint = updateSubtaskModalAssigneeHint;

function onSubtaskModalAssigneeChange() {
  const sel = document.getElementById('jiraSubtaskAssigneeSelect');
  if (!sel) return;
  sel.setAttribute('data-selected-value', sel.value);
  updateSubtaskModalAssigneeHint(sel.value);
}
window.onSubtaskModalAssigneeChange = onSubtaskModalAssigneeChange;

function populateSubtaskModalAssignees(preferredAccountId) {
  const sel = document.getElementById('jiraSubtaskAssigneeSelect');
  if (!sel) return;

  const myUser = getCurrentJiraUser();
  const myId = window.currentJiraUserAccountId || (myUser ? myUser.accountId : '');
  const myDisplayName = myUser ? (myUser.displayName || 'Tôi') : 'Tôi';
  const myEmail = myUser ? (myUser.email || myUser.emailAddress || '') : '';

  // Cập nhật text của nút "Gán cho tôi" phía trên dropdown
  const btnAssignToMe = document.getElementById('btnSubtaskAssignToMe');
  if (btnAssignToMe) {
    if (myDisplayName && myDisplayName !== 'Tôi') {
      btnAssignToMe.textContent = `Gán cho tôi (${myDisplayName})`;
      btnAssignToMe.title = `Gán trực tiếp cho tài khoản của bạn: ${myDisplayName}${myEmail ? ' (' + myEmail + ')' : ''}`;
    } else {
      btnAssignToMe.textContent = 'Gán cho tôi';
      btnAssignToMe.title = 'Gán trực tiếp cho tài khoản của bạn';
    }
  }

  let html = `<option value="">Chưa gán (Unassigned)</option>`;

  // Tùy chọn tài khoản của chính tôi: hiển thị rõ tên và email
  const myOptionLabel = (myDisplayName && myDisplayName !== 'Tôi')
    ? `${myDisplayName} (Tôi${myEmail ? ' - ' + myEmail : ''})`
    : `Gán cho tôi (Assign to me)`;

  if (myId) {
    html += `<option value="${escapeHtml(myId)}">${escapeHtml(myOptionLabel)}</option>`;
  } else {
    html += `<option value="me">${escapeHtml(myOptionLabel)}</option>`;
  }

  // Danh sách các thành viên khác
  const users = window.jiraAssignableUsers || [];
  users.forEach(u => {
    if (u.accountId && u.accountId !== myId) {
      html += `<option value="${escapeHtml(u.accountId)}">${escapeHtml(u.displayName)}</option>`;
    }
  });

  sel.innerHTML = html;

  // Xác định option cần chọn (Ưu tiên: preferredAccountId -> data-selected-value -> mặc định gán cho chính tôi khi tạo subtask)
  let targetVal = preferredAccountId;
  if (targetVal === undefined || targetVal === null) {
    const prevVal = sel.getAttribute('data-selected-value');
    if (prevVal !== null && prevVal !== undefined) {
      targetVal = prevVal;
    } else {
      // Mặc định luôn fill tài khoản của tôi
      targetVal = myId || 'me';
    }
  }

  if (targetVal) {
    sel.value = targetVal;
    sel.setAttribute('data-selected-value', targetVal);
  }

  updateSubtaskModalAssigneeHint(sel.value);
}
window.populateSubtaskModalAssignees = populateSubtaskModalAssignees;

function renderTicketAssignee(issue) {
  if (!issue) return;
  const assigneeEl = document.getElementById('jiraDetailAssignee');
  const avatarEl = document.getElementById('jiraDetailAssigneeAvatar');
  const selectEl = document.getElementById('jiraDetailAssigneeSelect');
  const btnAssignToMe = document.getElementById('btnAssignToMe');

  const isMe = Boolean(window.currentJiraUserAccountId && issue.assignee_account_id === window.currentJiraUserAccountId);

  if (assigneeEl) {
    assigneeEl.textContent = issue.assignee ? (isMe ? `${issue.assignee} (Tôi)` : issue.assignee) : 'Chưa gán';
  }

  if (avatarEl) {
    if (issue.assignee_avatar) {
      avatarEl.innerHTML = `<img src="${escapeHtml(issue.assignee_avatar)}" class="w-full h-full object-cover rounded-full" alt="" />`;
    } else if (issue.assignee && issue.assignee !== 'Chưa gán') {
      const initial = (issue.assignee || '?').trim()[0].toUpperCase();
      avatarEl.innerHTML = `<span class="text-[10px] font-bold text-slate-200">${escapeHtml(initial)}</span>`;
    } else {
      avatarEl.innerHTML = `<svg class="w-3 h-3 text-slate-400" fill="currentColor" viewBox="0 0 20 20"><path fill-rule="evenodd" d="M10 9a3 3 0 100-6 3 3 0 000 6zm-7 9a7 7 0 1114 0H3z" clip-rule="evenodd"></path></svg>`;
    }
  }

  if (selectEl) {
    selectEl.innerHTML = renderSubtaskAssigneeOptions(issue.assignee_account_id || '', issue.assignee || '');
    selectEl.value = issue.assignee_account_id || '';
  }

  populateJiraAssigneeCustomDropdown(issue.assignee_account_id || '', issue.assignee || '', issue.assignee_avatar || '');

  if (btnAssignToMe) {
    if (!isMe && window.currentJiraUserAccountId) {
      btnAssignToMe.classList.remove('hidden');
    } else {
      btnAssignToMe.classList.add('hidden');
    }
  }
}
window.renderTicketAssignee = renderTicketAssignee;

function populateJiraAssigneeCustomDropdown(selectedAccountId, selectedDisplayName, selectedAvatar) {
  const container = document.getElementById('jiraAssigneeOptionsList');
  if (!container) return;

  const users = window.jiraAssignableUsers || [];
  let html = '';

  // 1. Option: Chưa gán (Unassigned)
  const isUnassigned = !selectedAccountId;
  html += `
    <div onclick="selectJiraAssigneeOption('', 'Chưa gán', '', '')"
      data-name="chua gan unassigned"
      class="jira-assignee-option flex items-center justify-between px-2.5 py-1.5 rounded-lg cursor-pointer transition select-none ${isUnassigned ? 'is-selected' : ''}">
      <div class="flex items-center gap-2.5 min-w-0">
        <span class="w-6 h-6 rounded-full bg-slate-700/60 border border-slate-600/50 text-slate-400 inline-flex items-center justify-center shrink-0">
          <svg class="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z" />
          </svg>
        </span>
        <span class="text-xs font-medium truncate jira-assignee-option-name text-slate-300">Chưa gán (Unassigned)</span>
      </div>
      ${isUnassigned ? '<svg class="w-4 h-4 text-[#1677ff] shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2.5" d="M5 13l4 4L19 7" /></svg>' : ''}
    </div>
  `;

  // 2. Options từng thành viên (hiển thị Avatar + Tên + Email)
  let foundSelected = isUnassigned;
  users.forEach(u => {
    const isSelected = (u.accountId === selectedAccountId);
    if (isSelected) foundSelected = true;
    const isMe = Boolean(window.currentJiraUserAccountId && u.accountId === window.currentJiraUserAccountId);
    const avatarUrl = u.avatar || u.avatarUrl || '';
    const initial = (u.displayName || '?').trim()[0].toUpperCase();
    const emailStr = u.email || '';

    html += `
      <div onclick="selectJiraAssigneeOption('${escapeHtml(u.accountId)}', '${escapeHtml(u.displayName)}', '${escapeHtml(avatarUrl)}', '${escapeHtml(emailStr)}')"
        data-name="${escapeHtml((u.displayName || '').toLowerCase())} ${escapeHtml(emailStr.toLowerCase())}"
        class="jira-assignee-option flex items-center justify-between px-2.5 py-1.5 rounded-lg cursor-pointer transition select-none ${isSelected ? 'is-selected' : ''}">
        <div class="flex items-center gap-2.5 min-w-0">
          <span class="w-6 h-6 rounded-full bg-slate-700 overflow-hidden inline-flex items-center justify-center shrink-0 text-[10px] font-bold text-slate-200 border border-slate-600/40">
            ${avatarUrl
              ? `<img src="${escapeHtml(avatarUrl)}" class="w-full h-full object-cover rounded-full" alt="" />`
              : escapeHtml(initial)}
          </span>
          <div class="min-w-0 flex-1">
            <div class="flex items-center gap-1.5">
              <span class="text-xs font-medium truncate jira-assignee-option-name text-slate-200">${escapeHtml(u.displayName)}</span>
              ${isMe ? '<span class="text-[9.5px] font-medium font-sans px-1.5 py-0.2 rounded bg-blue-500/20 text-blue-400 border border-blue-500/30 shrink-0">Tôi</span>' : ''}
            </div>
            ${emailStr ? `<div class="text-[10.5px] text-slate-400 font-sans truncate jira-assignee-option-email">${escapeHtml(emailStr)}</div>` : ''}
          </div>
        </div>
        ${isSelected ? '<svg class="w-4 h-4 text-[#1677ff] shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2.5" d="M5 13l4 4L19 7" /></svg>' : ''}
      </div>
    `;
  });

  // 3. Nếu người thực hiện hiện tại không nằm trong users list
  if (!foundSelected && selectedAccountId) {
    const initial = (selectedDisplayName || '?').trim()[0].toUpperCase();
    html += `
      <div onclick="selectJiraAssigneeOption('${escapeHtml(selectedAccountId)}', '${escapeHtml(selectedDisplayName || 'Người thực hiện')}', '${escapeHtml(selectedAvatar || '')}', '')"
        data-name="${escapeHtml((selectedDisplayName || '').toLowerCase())}"
        class="jira-assignee-option is-selected flex items-center justify-between px-2.5 py-1.5 rounded-lg cursor-pointer transition select-none">
        <div class="flex items-center gap-2.5 min-w-0">
          <span class="w-6 h-6 rounded-full bg-slate-700 overflow-hidden inline-flex items-center justify-center shrink-0 text-[10px] font-bold text-slate-200 border border-slate-600/40">
            ${selectedAvatar
              ? `<img src="${escapeHtml(selectedAvatar)}" class="w-full h-full object-cover rounded-full" alt="" />`
              : escapeHtml(initial)}
          </span>
          <div class="min-w-0 flex-1">
            <span class="text-xs font-medium truncate jira-assignee-option-name text-slate-200">${escapeHtml(selectedDisplayName || 'Người thực hiện')}</span>
          </div>
        </div>
        <svg class="w-4 h-4 text-[#1677ff] shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2.5" d="M5 13l4 4L19 7" /></svg>
      </div>
    `;
  }

  container.innerHTML = html;
}
window.populateJiraAssigneeCustomDropdown = populateJiraAssigneeCustomDropdown;

function toggleJiraAssigneeDropdown(e) {
  if (e) {
    e.stopPropagation();
    e.preventDefault();
  }
  const menu = document.getElementById('jiraDetailAssigneeDropdownMenu');
  const chevron = document.getElementById('jiraDetailAssigneeChevron');
  if (!menu) return;

  const isHidden = menu.classList.contains('hidden');
  if (isHidden) {
    closeSubtaskAssigneeMenu();
    menu.classList.remove('hidden');
    if (chevron) chevron.classList.add('rotate-180');
    const searchInput = document.getElementById('jiraAssigneeSearchInput');
    if (searchInput) {
      searchInput.value = '';
      filterJiraAssigneeDropdown('');
      setTimeout(() => searchInput.focus(), 50);
    }
  } else {
    closeJiraAssigneeDropdown();
  }
}
window.toggleJiraAssigneeDropdown = toggleJiraAssigneeDropdown;

function closeJiraAssigneeDropdown() {
  const menu = document.getElementById('jiraDetailAssigneeDropdownMenu');
  const chevron = document.getElementById('jiraDetailAssigneeChevron');
  if (menu && !menu.classList.contains('hidden')) {
    menu.classList.add('hidden');
    if (chevron) chevron.classList.remove('rotate-180');
  }
}
window.closeJiraAssigneeDropdown = closeJiraAssigneeDropdown;

function filterJiraAssigneeDropdown(query) {
  const container = document.getElementById('jiraAssigneeOptionsList');
  if (!container) return;

  const q = (query || '').trim().toLowerCase();
  const cleanQ = q.normalize('NFD').replace(/[\u0300-\u036f]/g, '').toLowerCase();

  const options = container.querySelectorAll('.jira-assignee-option');
  let matchCount = 0;

  options.forEach(opt => {
    const name = opt.getAttribute('data-name') || '';
    const cleanName = name.normalize('NFD').replace(/[\u0300-\u036f]/g, '').toLowerCase();
    if (!q || name.includes(q) || cleanName.includes(cleanQ)) {
      opt.classList.remove('hidden');
      matchCount++;
    } else {
      opt.classList.add('hidden');
    }
  });

  const emptyEl = document.getElementById('jiraAssigneeEmptyMsg');
  if (emptyEl) {
    if (matchCount === 0) {
      emptyEl.classList.remove('hidden');
    } else {
      emptyEl.classList.add('hidden');
    }
  }
}
window.filterJiraAssigneeDropdown = filterJiraAssigneeDropdown;

async function selectJiraAssigneeOption(accountId, displayName, avatarUrl, email) {
  closeJiraAssigneeDropdown();

  const assigneeEl = document.getElementById('jiraDetailAssignee');
  const avatarEl = document.getElementById('jiraDetailAssigneeAvatar');
  const triggerEl = document.getElementById('jiraDetailAssigneeTrigger');
  const isMe = Boolean(window.currentJiraUserAccountId && accountId === window.currentJiraUserAccountId);

  if (assigneeEl) {
    assigneeEl.textContent = accountId ? (isMe ? `${displayName} (Tôi)` : displayName) : 'Chưa gán';
  }
  if (triggerEl) {
    triggerEl.title = `Người thực hiện: ${accountId ? (isMe ? `${displayName} (Tôi)` : displayName) : 'Chưa gán'}${email ? ' (' + email + ')' : ''}`;
  }
  if (avatarEl) {
    if (avatarUrl) {
      avatarEl.innerHTML = `<img src="${escapeHtml(avatarUrl)}" class="w-full h-full object-cover rounded-full" alt="" />`;
    } else if (accountId) {
      const initial = (displayName || '?').trim()[0].toUpperCase();
      avatarEl.innerHTML = `<span class="text-[10px] font-bold text-slate-200">${escapeHtml(initial)}</span>`;
    } else {
      avatarEl.innerHTML = `<svg class="w-3 h-3 text-slate-400" fill="currentColor" viewBox="0 0 20 20"><path fill-rule="evenodd" d="M10 9a3 3 0 100-6 3 3 0 000 6zm-7 9a7 7 0 1114 0H3z" clip-rule="evenodd"></path></svg>`;
    }
  }

  const selectEl = document.getElementById('jiraDetailAssigneeSelect');
  if (selectEl) {
    selectEl.value = accountId || '';
  }

  await onJiraAssigneeChange(accountId);
}
window.selectJiraAssigneeOption = selectJiraAssigneeOption;

// ============================================================
// FLOATING DROPDOWN CHO NGƯỜI THỰC HIỆN SUB-TASK
// ============================================================
window.activeSubtaskDropdownKey = null;

function openSubtaskAssigneeMenu(subtaskKey, e, triggerEl) {
  if (e) {
    e.stopPropagation();
    e.preventDefault();
  }

  const menu = document.getElementById('jiraSubtaskAssigneeFloatingMenu');
  if (!menu) return;

  if (window.activeSubtaskDropdownKey === subtaskKey && !menu.classList.contains('hidden')) {
    closeSubtaskAssigneeMenu();
    return;
  }

  closeJiraAssigneeDropdown();
  window.activeSubtaskDropdownKey = subtaskKey;

  // Lấy dữ liệu subtask hiện tại
  const issue = window.activeJiraIssue;
  const subtasks = (issue && issue.subtasks) || [];
  const st = subtasks.find(s => s.key === subtaskKey) || {};
  const currentAccountId = st.assignee_account_id || '';

  renderSubtaskFloatingOptions(subtaskKey, currentAccountId);

  menu.classList.remove('hidden');
  const rect = triggerEl.getBoundingClientRect();
  const menuWidth = 288;
  let left = rect.right - menuWidth;
  if (left < 10) left = Math.max(10, rect.left);
  if (left + menuWidth > window.innerWidth - 10) {
    left = window.innerWidth - menuWidth - 10;
  }

  let top = rect.bottom + 4;
  const menuHeight = 310;
  if (top + menuHeight > window.innerHeight && rect.top > menuHeight) {
    top = rect.top - menuHeight - 4;
  }

  menu.style.top = `${top}px`;
  menu.style.left = `${left}px`;

  const searchInput = document.getElementById('jiraSubtaskAssigneeSearchInput');
  if (searchInput) {
    searchInput.value = '';
    filterSubtaskFloatingDropdown('');
    setTimeout(() => searchInput.focus(), 50);
  }
}
window.openSubtaskAssigneeMenu = openSubtaskAssigneeMenu;

function closeSubtaskAssigneeMenu() {
  const menu = document.getElementById('jiraSubtaskAssigneeFloatingMenu');
  if (menu && !menu.classList.contains('hidden')) {
    menu.classList.add('hidden');
    window.activeSubtaskDropdownKey = null;
  }
}
window.closeSubtaskAssigneeMenu = closeSubtaskAssigneeMenu;

function renderSubtaskFloatingOptions(subtaskKey, selectedAccountId) {
  const container = document.getElementById('jiraSubtaskAssigneeFloatingOptions');
  if (!container) return;

  const users = window.jiraAssignableUsers || [];
  let html = '';

  // 1. Option Chưa gán
  const isUnassigned = !selectedAccountId;
  html += `
    <div onclick="selectSubtaskFloatingOption('${escapeHtml(subtaskKey)}', '', 'Chưa gán', '', '')"
      data-name="chua gan unassigned"
      class="jira-assignee-option flex items-center justify-between px-2.5 py-1.5 rounded-lg cursor-pointer transition select-none ${isUnassigned ? 'is-selected' : ''}">
      <div class="flex items-center gap-2.5 min-w-0">
        <span class="w-6 h-6 rounded-full bg-slate-700/60 border border-slate-600/50 text-slate-400 inline-flex items-center justify-center shrink-0">
          <svg class="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z" />
          </svg>
        </span>
        <span class="text-xs font-medium truncate jira-assignee-option-name text-slate-300">Chưa gán (Unassigned)</span>
      </div>
      ${isUnassigned ? '<svg class="w-4 h-4 text-[#1677ff] shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2.5" d="M5 13l4 4L19 7" /></svg>' : ''}
    </div>
  `;

  // 2. Options từng thành viên (kèm Avatar, Tên, Email)
  users.forEach(u => {
    const isSelected = (u.accountId === selectedAccountId);
    const isMe = Boolean(window.currentJiraUserAccountId && u.accountId === window.currentJiraUserAccountId);
    const avatarUrl = u.avatar || u.avatarUrl || '';
    const initial = (u.displayName || '?').trim()[0].toUpperCase();
    const emailStr = u.email || '';

    html += `
      <div onclick="selectSubtaskFloatingOption('${escapeHtml(subtaskKey)}', '${escapeHtml(u.accountId)}', '${escapeHtml(u.displayName)}', '${escapeHtml(avatarUrl)}', '${escapeHtml(emailStr)}')"
        data-name="${escapeHtml((u.displayName || '').toLowerCase())} ${escapeHtml(emailStr.toLowerCase())}"
        class="jira-assignee-option flex items-center justify-between px-2.5 py-1.5 rounded-lg cursor-pointer transition select-none ${isSelected ? 'is-selected' : ''}">
        <div class="flex items-center gap-2.5 min-w-0">
          <span class="w-6 h-6 rounded-full bg-slate-700 overflow-hidden inline-flex items-center justify-center shrink-0 text-[10px] font-bold text-slate-200 border border-slate-600/40">
            ${avatarUrl
              ? `<img src="${escapeHtml(avatarUrl)}" class="w-full h-full object-cover rounded-full" alt="" />`
              : escapeHtml(initial)}
          </span>
          <div class="min-w-0 flex-1">
            <div class="flex items-center gap-1.5">
              <span class="text-xs font-medium truncate jira-assignee-option-name text-slate-200">${escapeHtml(u.displayName)}</span>
              ${isMe ? '<span class="text-[9.5px] font-medium font-sans px-1.5 py-0.2 rounded bg-blue-500/20 text-blue-400 border border-blue-500/30 shrink-0">Tôi</span>' : ''}
            </div>
            ${emailStr ? `<div class="text-[10.5px] text-slate-400 font-sans truncate jira-assignee-option-email">${escapeHtml(emailStr)}</div>` : ''}
          </div>
        </div>
        ${isSelected ? '<svg class="w-4 h-4 text-[#1677ff] shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2.5" d="M5 13l4 4L19 7" /></svg>' : ''}
      </div>
    `;
  });

  container.innerHTML = html;
}
window.renderSubtaskFloatingOptions = renderSubtaskFloatingOptions;

function filterSubtaskFloatingDropdown(query) {
  const container = document.getElementById('jiraSubtaskAssigneeFloatingOptions');
  if (!container) return;

  const q = (query || '').trim().toLowerCase();
  const cleanQ = q.normalize('NFD').replace(/[\u0300-\u036f]/g, '').toLowerCase();

  const options = container.querySelectorAll('.jira-assignee-option');
  let matchCount = 0;

  options.forEach(opt => {
    const name = opt.getAttribute('data-name') || '';
    const cleanName = name.normalize('NFD').replace(/[\u0300-\u036f]/g, '').toLowerCase();
    if (!q || name.includes(q) || cleanName.includes(cleanQ)) {
      opt.classList.remove('hidden');
      matchCount++;
    } else {
      opt.classList.add('hidden');
    }
  });

  const emptyEl = document.getElementById('jiraSubtaskAssigneeFloatingEmpty');
  if (emptyEl) {
    if (matchCount === 0) {
      emptyEl.classList.remove('hidden');
    } else {
      emptyEl.classList.add('hidden');
    }
  }
}
window.filterSubtaskFloatingDropdown = filterSubtaskFloatingDropdown;

async function selectSubtaskFloatingOption(subtaskKey, accountId, displayName, avatarUrl, email) {
  closeSubtaskAssigneeMenu();

  const triggerBtn = document.querySelector(`.jira-subtask-assignee-trigger[data-subtask-key="${subtaskKey}"]`);
  const isMe = Boolean(window.currentJiraUserAccountId && accountId === window.currentJiraUserAccountId);
  const displayLabel = accountId ? (isMe ? `${displayName} (Tôi)` : displayName) : 'Chưa gán';

  if (triggerBtn) {
    const avatarBox = triggerBtn.querySelector('.subtask-avatar-box');
    const nameBox = triggerBtn.querySelector('.subtask-name-box');

    if (nameBox) {
      nameBox.textContent = displayLabel;
    }
    if (avatarBox) {
      if (avatarUrl) {
        avatarBox.innerHTML = `<img src="${escapeHtml(avatarUrl)}" class="w-full h-full object-cover rounded-full" alt="" />`;
      } else if (accountId && displayName && displayName !== 'Chưa gán') {
        const initial = displayName.trim()[0].toUpperCase();
        avatarBox.innerHTML = `<span class="text-[9.5px] font-bold text-slate-200">${escapeHtml(initial)}</span>`;
      } else {
        avatarBox.innerHTML = `<svg class="w-2.5 h-2.5 text-slate-400" fill="currentColor" viewBox="0 0 20 20"><path fill-rule="evenodd" d="M10 9a3 3 0 100-6 3 3 0 000 6zm-7 9a7 7 0 1114 0H3z" clip-rule="evenodd"></path></svg>`;
      }
    }
    triggerBtn.title = `Người thực hiện: ${displayLabel}${email ? ' (' + email + ')' : ''}`;
  }

  const selectEl = document.querySelector(`.jira-subtask-assignee-select[data-subtask-key="${subtaskKey}"]`);
  if (selectEl) {
    selectEl.value = accountId || '';
  }

  // Cập nhật bộ nhớ cục bộ window.activeJiraIssue
  if (window.activeJiraIssue && Array.isArray(window.activeJiraIssue.subtasks)) {
    const st = window.activeJiraIssue.subtasks.find(s => s.key === subtaskKey);
    if (st) {
      st.assignee = displayLabel;
      st.assignee_account_id = accountId || '';
      st.assignee_avatar = avatarUrl || '';
      st.assignee_email = email || '';
    }
  }

  await onSubtaskAssigneeChange(subtaskKey, accountId, selectEl, triggerBtn);
}
window.selectSubtaskFloatingOption = selectSubtaskFloatingOption;

/**
 * Gán người thực hiện trực tiếp cho một Sub-task
 */
async function onSubtaskAssigneeChange(subtaskKey, accountId, selectEl, triggerBtn) {
  if (!subtaskKey) return;

  if (selectEl) {
    selectEl.disabled = true;
    selectEl.classList.add('opacity-60');
  }
  if (!triggerBtn) {
    triggerBtn = document.querySelector(`.jira-subtask-assignee-trigger[data-subtask-key="${subtaskKey}"]`);
  }
  if (triggerBtn) {
    triggerBtn.disabled = true;
    triggerBtn.classList.add('opacity-60', 'pointer-events-none');
  }

  try {
    const res = await fetch('/api/jira/assign', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        key: subtaskKey,
        account_id: accountId || null
      })
    });
    const d = await res.json();
    if (d && d.success) {
      showToast(`Đã gán người thực hiện cho Sub-task [${subtaskKey}] thành công!`, 'success');
      if (window.activeJiraIssue && window.activeJiraIssue.key) {
        selectJiraIssue(window.activeJiraIssue.key, true);
      }
    } else {
      showToast((d && d.message) || 'Lỗi khi gán người thực hiện cho Sub-task', 'error');
      if (window.activeJiraIssue && window.activeJiraIssue.key) {
        selectJiraIssue(window.activeJiraIssue.key, true);
      }
    }
  } catch (err) {
    showToast('Lỗi kết nối khi gán Sub-task: ' + err.message, 'error');
    if (window.activeJiraIssue && window.activeJiraIssue.key) {
      selectJiraIssue(window.activeJiraIssue.key, true);
    }
  } finally {
    if (selectEl) {
      selectEl.disabled = false;
      selectEl.classList.remove('opacity-60');
    }
    if (triggerBtn) {
      triggerBtn.disabled = false;
      triggerBtn.classList.remove('opacity-60', 'pointer-events-none');
    }
  }
}
window.onSubtaskAssigneeChange = onSubtaskAssigneeChange;

/**
 * Gán người thực hiện cho Ticket cha
 */
async function onJiraAssigneeChange(accountId) {
  const issue = window.activeJiraIssue;
  if (!issue || !issue.key) return;

  const selectEl = document.getElementById('jiraDetailAssigneeSelect');
  const triggerEl = document.getElementById('jiraDetailAssigneeTrigger');
  if (selectEl) {
    selectEl.disabled = true;
    selectEl.classList.add('opacity-60');
  }
  if (triggerEl) {
    triggerEl.disabled = true;
    triggerEl.classList.add('opacity-60', 'pointer-events-none');
  }

  try {
    const res = await fetch('/api/jira/assign', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        key: issue.key,
        account_id: accountId || null
      })
    });
    const d = await res.json();
    if (d && d.success) {
      showToast(`Đã gán người thực hiện cho [${issue.key}] thành công!`, 'success');
      selectJiraIssue(issue.key, true);
    } else {
      showToast((d && d.message) || 'Lỗi khi gán người thực hiện cho Ticket', 'error');
      if (selectEl) {
        selectEl.value = issue.assignee_account_id || '';
      }
      renderTicketAssignee(issue);
    }
  } catch (err) {
    showToast('Lỗi kết nối khi gán Ticket: ' + err.message, 'error');
    if (selectEl) {
      selectEl.value = issue.assignee_account_id || '';
    }
    renderTicketAssignee(issue);
  } finally {
    if (selectEl) {
      selectEl.disabled = false;
      selectEl.classList.remove('opacity-60');
    }
    if (triggerEl) {
      triggerEl.disabled = false;
      triggerEl.classList.remove('opacity-60', 'pointer-events-none');
    }
  }
}
window.onJiraAssigneeChange = onJiraAssigneeChange;

function assignActiveJiraToMe() {
  const myUser = getCurrentJiraUser();
  const myId = window.currentJiraUserAccountId || (myUser ? myUser.accountId : 'me');
  const selectEl = document.getElementById('jiraDetailAssigneeSelect');
  if (selectEl) selectEl.value = myId;
  onJiraAssigneeChange(myId);
}
window.assignActiveJiraToMe = assignActiveJiraToMe;

function setSubtaskModalAssignToMe() {
  const sel = document.getElementById('jiraSubtaskAssigneeSelect');
  if (!sel) return;
  const myUser = getCurrentJiraUser();
  const myId = window.currentJiraUserAccountId || (myUser ? myUser.accountId : 'me');

  let found = false;
  for (let i = 0; i < sel.options.length; i++) {
    if (sel.options[i].value === myId || (myId && sel.options[i].value === myId) || sel.options[i].value === 'me') {
      sel.selectedIndex = i;
      sel.setAttribute('data-selected-value', sel.options[i].value);
      found = true;
      break;
    }
  }
  if (!found && myId) {
    sel.value = myId;
    sel.setAttribute('data-selected-value', myId);
  }
  updateSubtaskModalAssigneeHint(sel.value);
}
window.setSubtaskModalAssignToMe = setSubtaskModalAssignToMe;

// ============================================================
// SUB-TASK CREATION (JIRA CLOUD)
// ============================================================

function openCreateSubtaskModal() {
  const issue = window.activeJiraIssue;
  if (!issue || !issue.key) {
    showToast('Vui lòng chọn Ticket cha trước khi tạo Sub-task!', 'error');
    return;
  }

  const modal = document.getElementById('jiraCreateSubtaskModal');
  const parentKeyEl = document.getElementById('jiraSubtaskParentKey');
  const summaryInput = document.getElementById('jiraSubtaskSummaryInput');
  const descInput = document.getElementById('jiraSubtaskDescInput');
  const statusSelect = document.getElementById('jiraSubtaskStatusSelect');
  const assigneeSelect = document.getElementById('jiraSubtaskAssigneeSelect');

  if (parentKeyEl) parentKeyEl.textContent = issue.key;
  if (summaryInput) {
    summaryInput.value = '';
    setTimeout(() => summaryInput.focus(), 150);
  }
  if (descInput) descInput.value = '';
  if (statusSelect) statusSelect.value = 'To Do';

  // Khi mở modal tạo subtask, luôn mặc định fill tài khoản của chính tôi
  const myUser = getCurrentJiraUser();
  const myId = window.currentJiraUserAccountId || (myUser ? myUser.accountId : 'me');
  if (assigneeSelect) {
    assigneeSelect.removeAttribute('data-selected-value');
  }
  populateSubtaskModalAssignees(myId);

  // Đảm bảo có danh sách assignable users đầy đủ
  if (issue.key && (!window.jiraAssignableUsers || window.jiraAssignableUsers.length === 0)) {
    loadJiraAssignableUsers(issue.key);
  }

  if (modal) modal.classList.remove('hidden');
}
window.openCreateSubtaskModal = openCreateSubtaskModal;

function closeCreateSubtaskModal() {
  const modal = document.getElementById('jiraCreateSubtaskModal');
  if (modal) modal.classList.add('hidden');
}
window.closeCreateSubtaskModal = closeCreateSubtaskModal;

async function submitCreateSubtask() {
  const issue = window.activeJiraIssue;
  if (!issue || !issue.key) return;

  const summaryInput = document.getElementById('jiraSubtaskSummaryInput');
  const descInput = document.getElementById('jiraSubtaskDescInput');
  const statusSelect = document.getElementById('jiraSubtaskStatusSelect');
  const assigneeSelect = document.getElementById('jiraSubtaskAssigneeSelect');

  const summary = summaryInput ? summaryInput.value.trim() : '';
  const desc = descInput ? descInput.value.trim() : '';
  const targetStatus = statusSelect ? statusSelect.value : 'To Do';
  const assigneeId = assigneeSelect ? assigneeSelect.value : '';

  if (!summary) {
    showToast('Vui lòng nhập tiêu đề cho Sub-task!', 'error');
    if (summaryInput) summaryInput.focus();
    return;
  }

  setSubtaskSubmitting(true);

  try {
    const res = await fetch('/api/jira/create-subtask', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        parent_key: issue.key,
        summary: summary,
        description: desc,
        status: targetStatus,
        assignee_id: assigneeId
      })
    });
    const d = await res.json();
    if (d && d.success) {
      if (d.key) {
        window._selfCreatedSubtaskKeys = window._selfCreatedSubtaskKeys || new Set();
        window._selfCreatedSubtaskKeys.add(d.key);
      }
      closeCreateSubtaskModal();
      // Làm mới chi tiết ticket cha ngay lập tức (không cần thông báo rườm rà)
      selectJiraIssue(issue.key, true);
    } else {
      showToast((d && d.message) || 'Lỗi khi tạo Sub-task trên Jira', 'error');
    }
  } catch (err) {
    showToast('Lỗi kết nối khi tạo Sub-task: ' + err.message, 'error');
  } finally {
    setSubtaskSubmitting(false);
  }
}
window.submitCreateSubtask = submitCreateSubtask;

/**
 * Chuyển trạng thái của Sub-task trực tiếp tương tự Jira
 */
async function onSubtaskTransitionChange(subtaskKey, transitionVal, selectEl) {
  if (!subtaskKey || !transitionVal) return;

  const prevStatus = selectEl ? (selectEl.getAttribute('data-current') || '') : '';
  if (selectEl) {
    selectEl.disabled = true;
    selectEl.classList.add('opacity-60');
  }

  try {
    const isNumericId = /^\d+$/.test(String(transitionVal).trim());
    const payload = {
      key: subtaskKey,
      transition_id: isNumericId ? String(transitionVal).trim() : '',
      status: isNumericId ? '' : String(transitionVal).trim()
    };

    const res = await fetch('/api/jira/transition', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    });
    const d = await res.json();
    if (d && d.success) {
      if (window.activeJiraIssue && window.activeJiraIssue.key) {
        selectJiraIssue(window.activeJiraIssue.key, true);
      }
    } else {
      showToast((d && d.message) || 'Không thể chuyển trạng thái Sub-task', 'error');
      if (selectEl && prevStatus) {
        for (let i = 0; i < selectEl.options.length; i++) {
          if (selectEl.options[i].text.toLowerCase() === prevStatus.toLowerCase()) {
            selectEl.selectedIndex = i;
            break;
          }
        }
      }
    }
  } catch (err) {
    showToast('Lỗi khi chuyển trạng thái Sub-task: ' + err.message, 'error');
    if (selectEl && prevStatus) {
      for (let i = 0; i < selectEl.options.length; i++) {
        if (selectEl.options[i].text.toLowerCase() === prevStatus.toLowerCase()) {
          selectEl.selectedIndex = i;
          break;
        }
      }
    }
  } finally {
    if (selectEl) {
      selectEl.disabled = false;
      selectEl.classList.remove('opacity-60');
    }
  }
}
window.onSubtaskTransitionChange = onSubtaskTransitionChange;

/**
 * Bật/tắt trạng thái đang gửi của nút xác nhận Tạo Sub-task (spinner + đổi nhãn).
 */
function setSubtaskSubmitting(loading) {
  const btn = document.getElementById('btnSubmitCreateSubtask');
  if (!btn) return;
  btn.disabled = !!loading;
  const txt = document.getElementById('btnSubmitCreateSubtaskText');
  if (txt) txt.textContent = loading ? 'Đang tạo...' : 'Tạo Sub-task';
  const icon = document.getElementById('btnSubmitCreateSubtaskIcon');
  if (icon) icon.classList.toggle('hidden', !!loading);
  const spinner = document.getElementById('btnSubmitCreateSubtaskSpinner');
  if (spinner) spinner.classList.toggle('hidden', !loading);
}
window.setSubtaskSubmitting = setSubtaskSubmitting;

// ============================================================
// REAL-TIME NOTIFICATION WATCHER (NEW TASKS & COMMENTS)
// ============================================================

function playJiraNotificationChime() {
  try {
    const ctx = new (window.AudioContext || window.webkitAudioContext)();
    const osc = ctx.createOscillator();
    const gain = ctx.createGain();
    osc.type = 'sine';
    osc.frequency.setValueAtTime(587.33, ctx.currentTime); // D5
    osc.frequency.setValueAtTime(880, ctx.currentTime + 0.1); // A5
    gain.gain.setValueAtTime(0.12, ctx.currentTime);
    gain.gain.exponentialRampToValueAtTime(0.001, ctx.currentTime + 0.35);
    osc.connect(gain);
    gain.connect(ctx.destination);
    osc.start();
    osc.stop(ctx.currentTime + 0.35);
  } catch (e) {
    // Audio context may require prior user interaction
  }
}

function startJiraNotificationWatcher() {
  if (window.jiraNotificationTimer) return;
  // Kiểm tra lần đầu ngay lập tức để khởi tạo cache
  checkJiraRealtimeUpdates();
  window.jiraNotificationTimer = setInterval(checkJiraRealtimeUpdates, 18000);
}
window.startJiraNotificationWatcher = startJiraNotificationWatcher;

async function checkJiraRealtimeUpdates() {
  try {
    const res = await fetch('/api/jira/updates');
    const data = await res.json();
    if (data && data.success && Array.isArray(data.notifications) && data.notifications.length > 0) {
      let addedCount = 0;
      data.notifications.forEach(notif => {
        if (!notif || !notif.id) return;
        // Bỏ qua nếu là subtask do chính bản thân tạo (không cần thông báo)
        if (notif.key && window._selfCreatedSubtaskKeys && window._selfCreatedSubtaskKeys.has(notif.key)) {
          return;
        }
        const notifId = `jira_${notif.id}`;
        const exists = (typeof _savedNotifications !== 'undefined') &&
          _savedNotifications.some(n => n.id === notifId);
        if (exists) return;

        const isComment = notif.type === 'comment_added';
        if (typeof addOrUpdateNotification === 'function') {
          addOrUpdateNotification({
            id: notifId,
            tag: 'jira',
            tagLabel: 'Jira',
            title: notif.title || `Cập nhật Jira ${notif.key || ''}`,
            desc: notif.message || notif.summary || '',
            issueKey: notif.key,
            notifType: isComment ? 'comment_added' : 'issue_created',
            author: notif.author,
            date: notif.created || new Date().toISOString(),
            timestamp: notif.created ? (Date.parse(notif.created) || Date.now()) : Date.now()
          });
          addedCount++;
        }
      });

      if (addedCount > 0) {
        playJiraNotificationChime();
        if (typeof renderNotificationList === 'function') {
          renderNotificationList();
        } else if (typeof updateNotifBadgeUI === 'function') {
          updateNotifBadgeUI();
        }
      }
    }
  } catch (e) {
    // Silent polling error
  }
}
window.checkJiraRealtimeUpdates = checkJiraRealtimeUpdates;

/**
 * @deprecated Thông báo Jira giờ được gộp vào Chuông thông báo (tab Jira),
 * không còn hiển thị toast nổi trên màn hình. Hàm giữ lại để tương thích ngược.
 */
function showJiraInteractiveNotification(notif) {
  if (!notif || !notif.key) return;
  if (typeof addOrUpdateNotification !== 'function') return;
  const notifId = `jira_${notif.id || notif.key}`;
  if (typeof _savedNotifications !== 'undefined' && _savedNotifications.some(n => n.id === notifId)) return;
  addOrUpdateNotification({
    id: notifId,
    tag: 'jira',
    tagLabel: 'Jira',
    title: notif.title || `Cập nhật Jira ${notif.key}`,
    desc: notif.message || notif.summary || '',
    issueKey: notif.key,
    notifType: notif.type,
    author: notif.author,
    date: notif.created || new Date().toISOString(),
    timestamp: notif.created ? (Date.parse(notif.created) || Date.now()) : Date.now()
  });
  if (typeof renderNotificationList === 'function') renderNotificationList();
}
window.showJiraInteractiveNotification = showJiraInteractiveNotification;

function dismissJiraNotification(elId) {
  const el = document.getElementById(elId);
  if (!el) return;
  el.style.opacity = '0';
  el.style.transform = 'translateX(40px)';
  setTimeout(() => {
    if (el && el.parentNode) el.parentNode.removeChild(el);
  }, 250);
}
window.dismissJiraNotification = dismissJiraNotification;

/**
 * Khi bấm vào thông báo: Chuyển sang Tab Jira và mở đúng ticket đó
 */
function onJiraNotificationClick(issueKey, notifType) {
  if (!issueKey) return;

  // 1. Chuyển sang Tab Jira
  if (typeof switchTab === 'function') {
    switchTab('jira');
  }

  // 2. Tải và chọn đúng Ticket
  selectJiraIssue(issueKey);

  // 3. Nếu là bình luận mới, cuộn xuống phần thảo luận
  if (notifType === 'comment_added') {
    setTimeout(() => {
      const commBox = document.getElementById('jiraDetailCommentsList');
      if (commBox) {
        commBox.scrollIntoView({ behavior: 'smooth', block: 'center' });
        commBox.classList.add('ring-2', 'ring-blue-500');
        setTimeout(() => commBox.classList.remove('ring-2', 'ring-blue-500'), 1500);
      }
    }, 400);
  }

  showToast(`Đã mở Ticket [${issueKey}] từ thông báo!`, 'info');
}
window.onJiraNotificationClick = onJiraNotificationClick;
