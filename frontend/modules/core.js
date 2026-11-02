const TABS = ['task', 'branch', 'log', 'diagram', 'settings'];
let activeTab = 'task';
let renderedTurnCount = 0;
let mermaidRendered = false;

function antdConfirm({ title = 'Xác nhận', content = '', okText = 'Xác nhận', cancelText = 'Hủy', danger = false }) {
  return new Promise((resolve) => {
    const root = document.getElementById('antdModalRoot');
    const card = document.getElementById('antdModalCard');
    const titleEl = document.getElementById('antdModalTitle');
    const contentEl = document.getElementById('antdModalContent');
    const iconEl = document.getElementById('antdModalIcon');
    const cancelBtn = document.getElementById('antdModalCancelBtn');
    const okBtn = document.getElementById('antdModalOkBtn');

    if (!root || !card) {
      const plainContent = String(content || '').replace(/<[^>]+>/g, '');
      resolve(window.confirm(plainContent ? `${title}\n\n${plainContent}` : title));
      return;
    }

    titleEl.textContent = title;
    if (typeof content === 'string' && /<[a-z][\s\S]*>/i.test(content)) {
      contentEl.innerHTML = content;
    } else {
      contentEl.textContent = content;
    }
    okBtn.textContent = okText;
    cancelBtn.textContent = cancelText;
    cancelBtn.style.display = 'inline-flex';

    if (danger) {
      okBtn.className = 'ant-btn text-xs h-[32px] px-3.5 bg-rose-600 hover:bg-rose-500 border border-rose-500 text-white font-medium';
    } else {
      okBtn.className = 'ant-btn ant-btn-primary text-xs h-[32px] px-3.5 font-medium';
    }

    iconEl.innerHTML = `
          <svg class="w-5 h-5 ${danger ? 'text-rose-400' : 'text-blue-400'}" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8.228 9c.549-1.165 2.03-2 3.772-2 2.21 0 4 1.343 4 3 0 1.4-1.278 2.575-3.006 2.907-.542.104-.994.54-.994 1.093m0 3h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
          </svg>
        `;

    function cleanup(result) {
      card.classList.remove('scale-100', 'opacity-100');
      card.classList.add('scale-95', 'opacity-0');
      setTimeout(() => {
        root.classList.add('hidden');
        okBtn.onclick = null;
        cancelBtn.onclick = null;
        root.onclick = null;
        document.removeEventListener('keydown', keyHandler);
        resolve(result);
      }, 120);
    }

    function keyHandler(e) {
      if (e.key === 'Escape') cleanup(false);
      if (e.key === 'Enter') cleanup(true);
    }

    okBtn.onclick = (e) => {
      if (e && e.stopPropagation) e.stopPropagation();
      cleanup(true);
    };
    cancelBtn.onclick = (e) => {
      if (e && e.stopPropagation) e.stopPropagation();
      cleanup(false);
    };
    card.onclick = (e) => {
      if (e && e.stopPropagation) e.stopPropagation();
    };
    root.onclick = (e) => {
      if (e.target === root) cleanup(false);
    };
    document.addEventListener('keydown', keyHandler);

    root.classList.remove('hidden');
    requestAnimationFrame(() => {
      card.classList.remove('scale-95', 'opacity-0');
      card.classList.add('scale-100', 'opacity-100');
    });
  });
}

function antdAlert({ title = 'Thông báo', content = '', okText = 'Đã hiểu', type = 'info' }) {
  return new Promise((resolve) => {
    const root = document.getElementById('antdModalRoot');
    const card = document.getElementById('antdModalCard');
    const titleEl = document.getElementById('antdModalTitle');
    const contentEl = document.getElementById('antdModalContent');
    const iconEl = document.getElementById('antdModalIcon');
    const cancelBtn = document.getElementById('antdModalCancelBtn');
    const okBtn = document.getElementById('antdModalOkBtn');

    if (!root || !card) {
      window.alert(content ? `${title}\n\n${content}` : title);
      resolve(true);
      return;
    }

    titleEl.textContent = title;
    contentEl.textContent = content;
    okBtn.textContent = okText;
    cancelBtn.style.display = 'none';

    const isError = type === 'error';
    const isSuccess = type === 'success';

    okBtn.className = 'ant-btn ant-btn-primary text-xs h-[32px] px-3.5 font-medium';

    if (isError) {
      iconEl.innerHTML = `
            <svg class="w-5 h-5 text-rose-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
          `;
    } else if (isSuccess) {
      iconEl.innerHTML = `
            <svg class="w-5 h-5 text-emerald-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
          `;
    } else {
      iconEl.innerHTML = `
            <svg class="w-5 h-5 text-blue-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
          `;
    }

    function cleanup() {
      card.classList.remove('scale-100', 'opacity-100');
      card.classList.add('scale-95', 'opacity-0');
      setTimeout(() => {
        root.classList.add('hidden');
        okBtn.onclick = null;
        root.onclick = null;
        document.removeEventListener('keydown', keyHandler);
        resolve(true);
      }, 120);
    }

    function keyHandler(e) {
      if (e.key === 'Escape' || e.key === 'Enter') cleanup();
    }

    okBtn.onclick = (e) => {
      if (e && e.stopPropagation) e.stopPropagation();
      cleanup();
    };
    card.onclick = (e) => {
      if (e && e.stopPropagation) e.stopPropagation();
    };
    root.onclick = (e) => {
      if (e.target === root) cleanup();
    };
    document.addEventListener('keydown', keyHandler);

    root.classList.remove('hidden');
    requestAnimationFrame(() => {
      card.classList.remove('scale-95', 'opacity-0');
      card.classList.add('scale-100', 'opacity-100');
    });
  });
}

function antdPromptStash({ title = 'Lỗi Pull nhánh', content = '', okText = 'Git stash nó', cancelText = 'Đã hiểu' }) {
  return new Promise((resolve) => {
    const root = document.getElementById('antdModalRoot');
    const card = document.getElementById('antdModalCard');
    const titleEl = document.getElementById('antdModalTitle');
    const contentEl = document.getElementById('antdModalContent');
    const iconEl = document.getElementById('antdModalIcon');
    const cancelBtn = document.getElementById('antdModalCancelBtn');
    const okBtn = document.getElementById('antdModalOkBtn');

    if (!root || !card) {
      if (window.confirm(`${title}\n\n${content}\n\nBạn có muốn Git Stash các thay đổi dở dang để tiếp tục pull không?`)) {
        resolve('stash');
      } else {
        resolve('close');
      }
      return;
    }

    titleEl.textContent = title;
    contentEl.textContent = content;
    cancelBtn.textContent = cancelText;
    cancelBtn.style.display = 'inline-flex';
    cancelBtn.className = 'ant-btn text-xs h-[32px] px-3.5 text-slate-300 hover:text-white bg-slate-800 hover:bg-slate-700 border border-slate-600';

    okBtn.textContent = okText;
    okBtn.className = 'ant-btn text-xs h-[32px] px-3.5 bg-amber-600 hover:bg-amber-500 border border-amber-500 text-white font-semibold shadow-md';

    iconEl.innerHTML = `
      <svg class="w-5 h-5 text-amber-400 shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor">
        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
      </svg>
    `;

    function cleanup(action) {
      card.classList.remove('scale-100', 'opacity-100');
      card.classList.add('scale-95', 'opacity-0');
      setTimeout(() => {
        root.classList.add('hidden');
        okBtn.onclick = null;
        cancelBtn.onclick = null;
        root.onclick = null;
        document.removeEventListener('keydown', keyHandler);
        resolve(action);
      }, 120);
    }

    function keyHandler(e) {
      if (e.key === 'Escape') cleanup('close');
    }

    okBtn.onclick = () => cleanup('stash');
    cancelBtn.onclick = () => cleanup('close');
    root.onclick = (e) => {
      if (e.target === root) cleanup('close');
    };
    document.addEventListener('keydown', keyHandler);

    root.classList.remove('hidden');
    requestAnimationFrame(() => {
      card.classList.remove('scale-95', 'opacity-0');
      card.classList.add('scale-100', 'opacity-100');
    });
  });
}
window.antdPromptStash = antdPromptStash;

function isAuthorMe(author, isMe) {
  if (isMe === true) return true;
  if (!author || typeof author !== 'string') return false;
  const s = author.trim().toLowerCase();
  if (!s) return false;
  if (s.includes('thiết') || s.includes('thiet') || s.includes('thietnv')) {
    return true;
  }
  if (window._currentGitUser && typeof window._currentGitUser === 'string') {
    const cur = window._currentGitUser.trim().toLowerCase();
    if (cur && (s.includes(cur) || cur.includes(s))) {
      return true;
    }
  }
  return false;
}
window.isAuthorMe = isAuthorMe;

function formatCommitAuthor(author, isMe) {
  if (!author) return '';
  const isMine = isAuthorMe(author, isMe);
  if (isMine) {
    return `${escapeHtml(author)} <span class="text-blue-400 font-medium font-sans">(Tôi)</span>`;
  }
  return escapeHtml(author);
}
window.formatCommitAuthor = formatCommitAuthor;

function formatRelativeDate(raw, timestamp) {
  if (!raw && !timestamp) return '';
  let ts = Number(timestamp);
  if (!ts && raw) {
    if (typeof raw === 'number') {
      ts = raw;
    } else if (typeof raw === 'string') {
      const sTrim = raw.trim();
      if (/^\d{10,13}$/.test(sTrim)) {
        ts = parseInt(sTrim, 10);
        if (ts < 1e11) ts *= 1000;
      } else if (sTrim.includes('T') && (sTrim.includes('+') || sTrim.includes('Z') || sTrim.includes('-'))) {
        const parsed = Date.parse(sTrim);
        if (!isNaN(parsed)) ts = parsed;
      }
    }
  }

  if (ts && !isNaN(ts) && ts > 0) {
    const diffSec = Math.max(0, Math.floor((Date.now() - ts) / 1000));
    if (diffSec < 45) return 'vừa xong';
    if (diffSec < 3600) {
      const m = Math.floor(diffSec / 60);
      return `${m}p trước`;
    }
    if (diffSec < 86400) {
      const h = Math.floor(diffSec / 3600);
      const m = Math.floor((diffSec % 3600) / 60);
      return m > 0 ? `${h}h${m < 10 ? '0' + m : m} trước` : `${h}h trước`;
    }
    const days = Math.floor(diffSec / 86400);
    if (days === 1) return 'hôm qua';
    if (days < 7) return `${days} ngày trước`;
    if (days < 30) {
      const weeks = Math.floor(days / 7);
      return `${weeks} tuần trước`;
    }
    if (days < 365) {
      const months = Math.floor(days / 30);
      return `${months} tháng trước`;
    }
    const years = Math.floor(days / 365);
    return `${years} năm trước`;
  }

  const s = String(raw).trim();
  if (!s) return '';

  const isAgo = /\bago\b/i.test(s) || /trước/i.test(s);
  let clean = s.replace(/\bago\b/gi, '').replace(/\btrước\b/gi, '').trim();

  const mHm = clean.match(/(\d+)\s*(?:hours?|giờ|hrs?|h)\s*(?:,?\s*and\s*)?,?\s*(\d+)\s*(?:minutes?|phút|mins?|min|m|p)?(?:$|\s|[.,!])/i);
  if (mHm) {
    let h = parseInt(mHm[1], 10);
    let m = parseInt(mHm[2], 10);
    h += Math.floor(m / 60);
    m = m % 60;
    const res = m > 0 ? `${h}h${m < 10 ? '0' + m : m}` : `${h}h`;
    return isAgo ? `${res} trước` : res;
  }

  const mH = clean.match(/(\d+)\s*(?:hours?|giờ|hrs?|h)(?:$|\s|[.,!])/i);
  if (mH) {
    const h = parseInt(mH[1], 10);
    return isAgo ? `${h}h trước` : `${h}h`;
  }

  const mM = clean.match(/(\d+)\s*(?:minutes?|phút|mins?|min|m|p)(?:$|\s|[.,!])/i);
  if (mM) {
    const m = parseInt(mM[1], 10);
    let res = '';
    if (m >= 60) {
      const h = Math.floor(m / 60);
      const remM = m % 60;
      res = remM > 0 ? `${h}h${remM < 10 ? '0' + remM : remM}p` : `${h}h`;
    } else {
      res = `${m}p`;
    }
    return isAgo ? `${res} trước` : res;
  }

  const mS = clean.match(/(\d+)\s*(?:seconds?|giây|secs?|s)(?:$|\s|[.,!])/i);
  if (mS) {
    const sec = parseInt(mS[1], 10);
    let res = '';
    if (sec >= 60) {
      const m = Math.floor(sec / 60);
      const remS = sec % 60;
      res = remS > 0 ? `${m}p${remS}s` : `${m}p`;
    } else {
      res = `${sec}s`;
    }
    return isAgo ? `${res} trước` : res;
  }

  const mD = clean.match(/(\d+)\s*(?:days?|ngày)(?:$|\s|[.,!])/i);
  if (mD) {
    const d = parseInt(mD[1], 10);
    return isAgo ? `${d} ngày trước` : `${d} ngày`;
  }

  const mW = clean.match(/(\d+)\s*(?:weeks?|tuần)(?:$|\s|[.,!])/i);
  if (mW) {
    const w = parseInt(mW[1], 10);
    return isAgo ? `${w} tuần trước` : `${w} tuần`;
  }

  const mMo = clean.match(/(\d+)\s*(?:months?|tháng)(?:$|\s|[.,!])/i);
  if (mMo) {
    const mo = parseInt(mMo[1], 10);
    return isAgo ? `${mo} tháng trước` : `${mo} tháng`;
  }

  const mY = clean.match(/(\d+)\s*(?:years?|năm)(?:$|\s|[.,!])/i);
  if (mY) {
    const y = parseInt(mY[1], 10);
    return isAgo ? `${y} năm trước` : `${y} năm`;
  }

  const lower = clean.toLowerCase();
  if (lower.includes('just now') || lower.includes('moment ago')) return 'vừa xong';
  if (lower.includes('yesterday')) return 'hôm qua';

  return s;
}

function formatDuration(sec) {
  if (sec === null || sec === undefined || isNaN(sec)) return '';
  const totalSec = Number(sec);
  if (totalSec < 60) {
    return `${Math.round(totalSec * 10) / 10}s`;
  }
  const totalMin = Math.floor(totalSec / 60);
  const remSec = Math.round(totalSec % 60);

  if (totalMin >= 60) {
    const h = Math.floor(totalMin / 60);
    const m = totalMin % 60;
    return m > 0 ? `${h}h${m < 10 ? '0' + m : m}` : `${h}h`;
  }

  return remSec > 0 ? `${totalMin}p${remSec < 10 ? '0' + remSec : remSec}s` : `${totalMin}p`;
}

function escapeHtml(str) {
  if (!str) return '';
  return String(str).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
}

function copyToClipboard(text) {
  if (!text) return;
  if (navigator.clipboard && navigator.clipboard.writeText) {
    navigator.clipboard.writeText(text).then(() => {
      showToast('Đã sao chép: ' + text);
    }).catch(() => {
      showToast(text);
    });
  } else {
    showToast(text);
  }
}

function updateThemeUI(theme) {
  const btn = document.getElementById('themeToggleBtn');
  const icon = document.getElementById('themeToggleIcon');
  const text = document.getElementById('themeToggleText');
  if (theme === 'dark') {
    document.body.classList.remove('light-mode');
    document.body.classList.add('dark-mode');
    if (icon) icon.innerHTML = '🌙';
    if (text) text.textContent = 'Tối';
    if (btn) btn.title = 'Đang là chế độ Tối (Dark Mode). Nhấn để chuyển sang Sáng (Light Mode)';
  } else {
    document.body.classList.remove('dark-mode');
    document.body.classList.add('light-mode');
    if (icon) icon.innerHTML = '☀️';
    if (text) text.textContent = 'Sáng';
    if (btn) btn.title = 'Đang là chế độ Sáng (Light Mode). Nhấn để chuyển sang Tối (Dark Mode)';
  }
  if (typeof switchGitSubTab === 'function') {
    switchGitSubTab(activeGitSubTab, false);
  }
}

function toggleTheme() {
  const current = localStorage.getItem('easysalon_theme') || 'light';
  const nextTheme = current === 'light' ? 'dark' : 'light';
  localStorage.setItem('easysalon_theme', nextTheme);
  updateThemeUI(nextTheme);
  showToast(`Đã chuyển sang chế độ ${nextTheme === 'dark' ? 'Tối (Dark Mode)' : 'Sáng (Light Mode)'}.`);
}

function initTheme() {
  const savedTheme = localStorage.getItem('easysalon_theme') || 'light';
  updateThemeUI(savedTheme);
}

const DRAFT_STORAGE_KEY = 'easySalon_studio_drafts';

let _devWatchState = null;
let _devWatchReloading = false;

async function checkDevWatch() {
  if (_devWatchReloading) return;
  try {
    const res = await fetch('/api/dev-watch', { cache: 'no-store' });
    if (!res.ok) return;
    const data = await res.json();
    if (!data || !data.version) return;

    if (!_devWatchState) {
      _devWatchState = data;
      return;
    }

    if (data.version !== _devWatchState.version) {
      const prev = _devWatchState;
      _devWatchState = data;

      saveDraft(false);

      if (data.css_hash !== prev.css_hash && data.dom_js_hash === prev.dom_js_hash && data.py_hash === prev.py_hash) {
        const htmlRes = await fetch(window.location.pathname, { cache: 'no-store' });
        if (htmlRes.ok) {
          const htmlText = await htmlRes.text();
          const doc = new DOMParser().parseFromString(htmlText, 'text/html');
          const newStyles = doc.querySelectorAll('head style');
          const oldStyles = document.querySelectorAll('head style');
          if (newStyles.length > 0 && newStyles.length === oldStyles.length) {
            newStyles.forEach((st, idx) => {
              oldStyles[idx].textContent = st.textContent;
            });
            showToast('Đã tự động cập nhật CSS mới (Hot Reload)');
            return;
          }
        }
      }

      _devWatchReloading = true;
      try {
        sessionStorage.setItem('easysalon_hot_reload_scroll', String(window.scrollY || 0));
        sessionStorage.setItem('easysalon_hot_reload_git_subtab', String(activeGitSubTab || 'switch'));
        const activeEl = document.activeElement;
        if (activeEl && activeEl.id && (activeEl.tagName === 'TEXTAREA' || activeEl.tagName === 'INPUT')) {
          sessionStorage.setItem('easysalon_hot_reload_focus', JSON.stringify({
            id: activeEl.id,
            start: activeEl.selectionStart || 0,
            end: activeEl.selectionEnd || 0
          }));
        }
        sessionStorage.setItem('easysalon_hot_reloaded', '1');
      } catch (e) { }
      window.location.reload();
    }
  } catch (err) {

  }
}

function setupDevHotReload() {
  try {
    if (sessionStorage.getItem('easysalon_hot_reloaded') === '1') {
      sessionStorage.removeItem('easysalon_hot_reloaded');
      const currentPath = (window.location.pathname || '/').replace(/\/+$/, '') || '/';
      const urlSubTab = window.ROUTE_TO_GIT_SUBTAB && window.ROUTE_TO_GIT_SUBTAB[currentPath];
      const savedSubTab = urlSubTab || sessionStorage.getItem('easysalon_hot_reload_git_subtab');
      sessionStorage.removeItem('easysalon_hot_reload_git_subtab');
      if (savedSubTab && activeTab === 'branch' && typeof switchGitSubTab === 'function') {
        switchGitSubTab(savedSubTab, false);
      }
      const savedScroll = parseInt(sessionStorage.getItem('easysalon_hot_reload_scroll') || '0', 10);
      if (savedScroll > 0) {
        setTimeout(() => window.scrollTo(0, savedScroll), 60);
      }
      const focusRaw = sessionStorage.getItem('easysalon_hot_reload_focus');
      if (focusRaw) {
        sessionStorage.removeItem('easysalon_hot_reload_focus');
        const fInfo = JSON.parse(focusRaw);
        const el = fInfo && fInfo.id ? document.getElementById(fInfo.id) : null;
        if (el) {
          setTimeout(() => {
            el.focus();
            if (typeof el.setSelectionRange === 'function') {
              el.setSelectionRange(fInfo.start, fInfo.end);
            }
          }, 80);
        }
      }
      setTimeout(() => showToast('Đã tự động cập nhật code mới'), 150);
    }
  } catch (e) { }

  checkDevWatch();
  setInterval(checkDevWatch, 1500);
}
