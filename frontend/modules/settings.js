let currentStudioSettings = {
  engine: 'gemini_cli',
  effort: 'high',
  model: 'gemini-3.8-flash-high',
  opencode_model: '9router/ag/gemini-3.8-flash-high'
};
let nineRouterOnline = false;
let geminiCliStatus = {
  installed: false,
  logged_in: false,
  ready: false,
  version: '',
  bin_path: '',
  scope_id: '',
  credential_path: '~/.config/antigravity/credential-user-scope',
  config_path: '~/.gemini/antigravity-cli/settings.json',
  installation_id: '',
  system_user: '',
  cli_model: '',
  agent_mode: '',
  trusted_workspaces_count: 0
};

function updateGeminiCliUI(status) {
  if (status && typeof status === 'object') {
    geminiCliStatus = Object.assign({}, geminiCliStatus, status);
  }
  const pill = document.getElementById('pageGeminiCliStatusPill');
  const statusTxt = document.getElementById('pageGeminiCliStatusText');
  if (statusTxt) {
    if (geminiCliStatus.ready) {
      statusTxt.textContent = 'Sẵn sàng (Đã đăng nhập)';
      statusTxt.className = 'engine-card-status font-semibold text-emerald-400';
    } else if (geminiCliStatus.installed) {
      statusTxt.textContent = 'Chưa đăng nhập (Chạy agy)';
      statusTxt.className = 'engine-card-status font-semibold text-amber-400';
    } else {
      statusTxt.textContent = 'Không tìm thấy file agy';
      statusTxt.className = 'engine-card-status font-semibold text-rose-400';
    }
  }

  const accTag = document.getElementById('pageAccountStatusTag');
  if (accTag) {
    if (geminiCliStatus.ready) {
      accTag.textContent = 'ĐÃ ĐĂNG NHẬP';
      accTag.className = 'text-[10px] font-sans px-2.5 py-1 rounded bg-emerald-950 text-emerald-400 border border-emerald-800 uppercase font-semibold tracking-wider';
    } else if (geminiCliStatus.installed) {
      accTag.textContent = 'CHƯA ĐĂNG NHẬP';
      accTag.className = 'text-[10px] font-sans px-2.5 py-1 rounded bg-amber-950 text-amber-400 border border-amber-800 uppercase font-semibold tracking-wider';
    } else {
      accTag.textContent = 'CHƯA CÀI ĐẶT CLI';
      accTag.className = 'text-[10px] font-sans px-2.5 py-1 rounded bg-rose-950 text-rose-400 border border-rose-800 uppercase font-semibold tracking-wider';
    }
  }

  const accVerBadge = document.getElementById('accountCliVersionBadge');
  if (accVerBadge) {
    accVerBadge.textContent = geminiCliStatus.version ? `Antigravity CLI v${geminiCliStatus.version}` : 'Antigravity Native CLI';
  }

  const accUser = document.getElementById('accountSystemUser');
  if (accUser) {
    accUser.textContent = `${geminiCliStatus.system_user || 'system'} (Linux)`;
  }

  const accLoginStatus = document.getElementById('accountLoginStatus');
  if (accLoginStatus) {
    if (geminiCliStatus.ready) {
      accLoginStatus.innerHTML = '<span class="w-2 h-2 rounded-full bg-emerald-400 inline-block"></span><span>Đã đăng nhập và sẵn sàng thực thi</span>';
      accLoginStatus.className = 'font-semibold text-emerald-400 flex items-center gap-2';
    } else if (geminiCliStatus.installed) {
      accLoginStatus.innerHTML = '<span class="w-2 h-2 rounded-full bg-amber-400 inline-block"></span><span>Chưa đăng nhập (Chạy lệnh agy để đăng nhập Google OAuth)</span>';
      accLoginStatus.className = 'font-semibold text-amber-400 flex items-center gap-2';
    } else {
      accLoginStatus.innerHTML = '<span class="w-2 h-2 rounded-full bg-rose-400 inline-block"></span><span>Không tìm thấy file thực thi agy</span>';
      accLoginStatus.className = 'font-semibold text-rose-400 flex items-center gap-2';
    }
  }

  const accScopeId = document.getElementById('accountScopeId');
  if (accScopeId) {
    accScopeId.textContent = geminiCliStatus.scope_id || '(Chưa có - Cần đăng nhập agy)';
  }

  const accScopePath = document.getElementById('accountScopePath');
  if (accScopePath) {
    accScopePath.textContent = geminiCliStatus.credential_path || '~/.config/antigravity/credential-user-scope';
  }

  const accCliPath = document.getElementById('accountCliPath');
  if (accCliPath) {
    accCliPath.textContent = geminiCliStatus.bin_path || 'agy';
  }

  const accInstId = document.getElementById('accountInstallationId');
  if (accInstId) {
    accInstId.textContent = geminiCliStatus.installation_id || 'Chưa thiết lập';
  }

  const accActiveModel = document.getElementById('accountActiveModel');
  if (accActiveModel) {
    accActiveModel.textContent = currentStudioSettings.model || geminiCliStatus.cli_model || 'Gemini 3.8 Flash (High)';
  }

  const accEffortBadge = document.getElementById('accountEffortBadge');
  if (accEffortBadge) {
    const eff = (currentStudioSettings.effort || 'high').toUpperCase();
    accEffortBadge.textContent = eff;
  }

  const accAgentMode = document.getElementById('accountAgentMode');
  if (accAgentMode) {
    accAgentMode.textContent = `mode: ${geminiCliStatus.agent_mode || 'accept-edits'}`;
  }

  const accTrustedCount = document.getElementById('accountTrustedCount');
  if (accTrustedCount) {
    const cnt = geminiCliStatus.trusted_workspaces_count || (geminiCliStatus.trusted_workspaces ? geminiCliStatus.trusted_workspaces.length : 0);
    accTrustedCount.textContent = `${cnt} workspaces`;
  }
}
window.updateGeminiCliUI = updateGeminiCliUI;

async function checkGeminiCliAuthStatus(showToastMsg = false) {
  try {
    const res = await fetch('/api/settings');
    const d = await res.json();
    if (d && d.gemini_cli_status) {
      updateGeminiCliUI(d.gemini_cli_status);
      if (showToastMsg) {
        if (d.gemini_cli_status.ready) {
          showToast(`Gemini CLI: Đã đăng nhập và sẵn sàng (v${d.gemini_cli_status.version || '1.4.10'})`);
        } else if (d.gemini_cli_status.installed) {
          showToast('Gemini CLI đã cài đặt nhưng chưa đăng nhập tài khoản!');
        } else {
          showToast('Không tìm thấy Antigravity CLI (agy) trong hệ thống!');
        }
      }
    }
  } catch (err) {
    if (showToastMsg) showToast('Lỗi kiểm tra CLI: ' + err.message);
  }
}
window.checkGeminiCliAuthStatus = checkGeminiCliAuthStatus;

async function testGeminiCliPing() {
  const btn = document.getElementById('btnTestCliPing');
  const resMsg = document.getElementById('accountTestResultMsg');
  const origText = btn ? btn.innerHTML : '';
  if (btn) {
    btn.disabled = true;
    btn.innerHTML = '<svg class="animate-spin -ml-1 mr-2 h-3.5 w-3.5 text-white inline-block" fill="none" viewBox="0 0 24 24"><circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle><path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path></svg>Đang kiểm tra...';
  }
  if (resMsg) {
    resMsg.classList.add('hidden');
  }

  try {
    const res = await fetch('/api/test-gemini-cli', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({})
    });
    const d = await res.json();
    if (d && d.status) {
      updateGeminiCliUI(d.status);
    }
    if (resMsg) {
      resMsg.classList.remove('hidden');
      if (d && d.success) {
        resMsg.className = 'px-3.5 py-2.5 rounded-lg text-xs bg-emerald-600 border border-emerald-500 text-white font-medium shadow-sm flex items-center justify-between';
        resMsg.innerHTML = `<span><strong>Phản hồi tốt:</strong> ${escapeHtml(d.message || 'Kết nối thành công!')}</span><span class="font-mono text-[10px] text-white/90">${d.elapsed ? d.elapsed + 's' : ''}</span>`;
        showToast(d.message || 'Kết nối Antigravity CLI phản hồi tốt!', 'success');
      } else {
        resMsg.className = 'px-3.5 py-2.5 rounded-lg text-xs bg-[#dc2626] border border-[#ef4444] text-white font-medium shadow-sm flex items-center justify-between';
        resMsg.innerHTML = `<span><strong>Lỗi kết nối:</strong> ${escapeHtml(d.message || 'Không thể gọi CLI.')}</span>`;
        showToast(d.message || 'Lỗi kết nối Antigravity CLI!', 'error');
      }
    }
  } catch (err) {
    if (resMsg) {
      resMsg.classList.remove('hidden');
      resMsg.className = 'px-3.5 py-2.5 rounded-lg text-xs bg-[#dc2626] border border-[#ef4444] text-white font-medium shadow-sm flex items-center justify-between';
      resMsg.innerHTML = `<span><strong>Lỗi:</strong> ${escapeHtml(err.message)}</span>`;
    }
    showToast('Lỗi kiểm tra CLI: ' + err.message, 'error');
  } finally {
    if (btn) {
      btn.disabled = false;
      btn.innerHTML = origText;
    }
  }
}
window.testGeminiCliPing = testGeminiCliPing;

function copyScopeId() {
  const el = document.getElementById('accountScopeId');
  if (!el) return;
  const val = (el.textContent || '').trim();
  if (!val || val.includes('Chưa có')) {
    showToast('Chưa có mã Credential Scope để sao chép!');
    return;
  }
  if (navigator.clipboard && navigator.clipboard.writeText) {
    navigator.clipboard.writeText(val).then(() => {
      showToast('Đã sao chép Credential Scope ID vào clipboard!');
    }).catch(() => {
      prompt('Sao chép Credential Scope ID:', val);
    });
  } else {
    prompt('Sao chép Credential Scope ID:', val);
  }
}
window.copyScopeId = copyScopeId;

function updateEngineUI(engine, isOnline) {
  const eng = String(engine || currentStudioSettings.engine || 'gemini_cli').toLowerCase();
  currentStudioSettings.engine = eng;
  if (typeof isOnline === 'boolean') {
    nineRouterOnline = isOnline;
  }

  const tag = document.getElementById('pageCurrentEngineTag');
  if (tag) {
    if (eng === 'opencode') {
      tag.textContent = 'OPENCODE (9ROUTER)';
      tag.className = 'text-[10px] font-sans px-2.5 py-1 rounded bg-cyan-950 text-cyan-400 border border-cyan-800 uppercase font-semibold tracking-wider';
    } else {
      tag.textContent = 'GEMINI CLI';
      tag.className = 'text-[10px] font-sans px-2.5 py-1 rounded bg-emerald-950 text-emerald-400 border border-emerald-800 uppercase font-semibold tracking-wider';
    }
  }

  const pill = document.getElementById('pageNineRouterStatusPill');
  const statusTxt = document.getElementById('pageNineRouterStatusText');
  if (pill) {
    if (nineRouterOnline) {
      pill.textContent = '9router: Online';
      pill.className = 'text-[10px] text-emerald-400 font-sans font-medium px-2 py-0.5 rounded bg-emerald-950 border border-emerald-800 uppercase';
    } else {
      pill.textContent = '9router: Offline';
      pill.className = 'text-[10px] text-rose-400 font-sans font-medium px-2 py-0.5 rounded bg-rose-950 border border-rose-800 uppercase';
    }
  }
  if (statusTxt) {
    if (nineRouterOnline) {
      statusTxt.textContent = 'Online (Port 20128)';
      statusTxt.className = 'text-emerald-400 font-semibold';
    } else {
      statusTxt.textContent = 'Offline (Không kết nối)';
      statusTxt.className = 'text-rose-400 font-semibold';
    }
  }

  ['gemini_cli', 'opencode'].forEach(eid => {
    const card = document.getElementById('page_card_engine_' + eid);
    const radio = document.querySelector(`input[name="page_engine"][value="${eid}"]`);
    if (card && radio) {
      if (eid === eng) {
        radio.checked = true;
        card.classList.add('is-active');
      } else {
        radio.checked = false;
        card.classList.remove('is-active');
      }
    }
  });

  const geminiSection = document.getElementById('page_section_gemini_cli');
  const opencodeSection = document.getElementById('page_section_opencode');
  if (geminiSection && opencodeSection) {
    if (eng === 'opencode') {
      geminiSection.classList.add('hidden');
      opencodeSection.classList.remove('hidden');
    } else {
      geminiSection.classList.remove('hidden');
      opencodeSection.classList.add('hidden');
    }
  }
}

function onPageEngineChange(newEngine) {
  currentStudioSettings.engine = newEngine;
  updateEngineUI(newEngine, nineRouterOnline);
  markSettingsDirty(true);
}

let currentModelFamily = 'gemini';

function switchModelFamilyTab(family) {
  if (!['gemini', 'claude', 'openai'].includes(family)) family = 'gemini';
  currentModelFamily = family;

  if (family === 'gemini') {
    if (!currentStudioSettings.model || !currentStudioSettings.model.startsWith('gemini')) {
      currentStudioSettings.model = 'gemini-3.8-flash-' + (['low', 'medium', 'high'].includes(currentStudioSettings.effort) ? currentStudioSettings.effort : 'high');
    }
    if (['xhigh', 'max'].includes(currentStudioSettings.effort)) {
      currentStudioSettings.effort = 'high';
    }
  } else if (family === 'claude') {
    if (!currentStudioSettings.model || !currentStudioSettings.model.startsWith('claude')) {
      currentStudioSettings.model = 'claude-sonnet-4-6';
    }
  } else if (family === 'openai') {
    if (!currentStudioSettings.model || (!currentStudioSettings.model.startsWith('gpt') && !currentStudioSettings.model.startsWith('o3') && !currentStudioSettings.model.startsWith('o1'))) {
      currentStudioSettings.model = 'gpt-oss-120b-medium';
    }
    if (['xhigh', 'max'].includes(currentStudioSettings.effort)) {
      currentStudioSettings.effort = 'high';
    }
  }

  updateEffortUI(currentStudioSettings.effort);
  markSettingsDirty(true);
}
window.switchModelFamilyTab = switchModelFamilyTab;

function onModelFamilySubModelChange(family, newModel) {
  currentStudioSettings.model = newModel;
  const masterSelect = document.getElementById('pageSettingsModelSelect');
  if (masterSelect) {
    masterSelect.value = newModel;
  }
  updateEffortUI(currentStudioSettings.effort);
  markSettingsDirty(true);
}
window.onModelFamilySubModelChange = onModelFamilySubModelChange;

function updateEffortUI(effort) {
  const eff = String(effort || currentStudioSettings.effort || 'high').toLowerCase();
  currentStudioSettings.effort = eff;

  if (!currentModelFamily) {
    const curModel = String(currentStudioSettings.model || 'gemini-3.8-flash-high').toLowerCase();
    if (curModel.startsWith('claude')) {
      currentModelFamily = 'claude';
    } else if (curModel.startsWith('gpt') || curModel.startsWith('o3') || curModel.startsWith('o1')) {
      currentModelFamily = 'openai';
    } else {
      currentModelFamily = 'gemini';
    }
  }

  ['gemini', 'claude', 'openai'].forEach(f => {
    const btn = document.getElementById('tab_btn_model_' + f);
    const panel = document.getElementById('tab_panel_model_' + f);
    if (btn) {
      if (f === currentModelFamily) btn.classList.add('is-active');
      else btn.classList.remove('is-active');
    }
    if (panel) {
      if (f === currentModelFamily) panel.classList.remove('hidden');
      else panel.classList.add('hidden');
    }
  });

  const accEffortBadge = document.getElementById('accountEffortBadge');
  if (accEffortBadge) {
    accEffortBadge.textContent = eff.toUpperCase();
  }

  const accActiveModel = document.getElementById('accountActiveModel');
  if (accActiveModel) {
    accActiveModel.textContent = currentStudioSettings.model || geminiCliStatus.cli_model || 'Gemini 3.8 Flash (High)';
  }

  ['low', 'medium', 'high'].forEach(lvl => {
    const card = document.getElementById('page_card_effort_' + lvl);
    const radio = card ? card.querySelector('input[type="radio"]') : null;
    if (card) {
      if (lvl === eff && currentModelFamily === 'gemini') {
        if (radio) radio.checked = true;
        card.classList.add('is-active');
      } else {
        if (radio) radio.checked = false;
        card.classList.remove('is-active');
      }
    }
  });

  ['low', 'medium', 'high', 'xhigh', 'max'].forEach(lvl => {
    const card = document.getElementById('page_card_effort_claude_' + lvl);
    const radio = card ? card.querySelector('input[type="radio"]') : null;
    if (card) {
      if (lvl === eff && currentModelFamily === 'claude') {
        if (radio) radio.checked = true;
        card.classList.add('is-active');
      } else {
        if (radio) radio.checked = false;
        card.classList.remove('is-active');
      }
    }
  });

  ['low', 'medium', 'high'].forEach(lvl => {
    const card = document.getElementById('page_card_effort_openai_' + lvl);
    const radio = card ? card.querySelector('input[type="radio"]') : null;
    if (card) {
      if (lvl === eff && currentModelFamily === 'openai') {
        if (radio) radio.checked = true;
        card.classList.add('is-active');
      } else {
        if (radio) radio.checked = false;
        card.classList.remove('is-active');
      }
    }
  });

  const modelSelect = document.getElementById('pageSettingsModelSelect');
  if (modelSelect && currentStudioSettings.model) {
    modelSelect.value = currentStudioSettings.model;
  }
  const opencodeModelSelect = document.getElementById('pageSettingsOpencodeModelSelect');
  if (opencodeModelSelect && currentStudioSettings.opencode_model) {
    opencodeModelSelect.value = currentStudioSettings.opencode_model;
  }
}
window.updateEffortUI = updateEffortUI;

function onPageEffortChange(newEffort) {

  if (currentModelFamily === 'gemini') {
    if (currentStudioSettings.model && currentStudioSettings.model.startsWith('gemini-3.8-flash')) {
      currentStudioSettings.model = `gemini-3.8-flash-${newEffort}`;
    }
  }
  currentStudioSettings.effort = newEffort;
  updateEffortUI(newEffort);
  markSettingsDirty(true);
}
window.onPageEffortChange = onPageEffortChange;

let pendingEffortSelection = null;

document.addEventListener('keydown', (e) => {
  if (activeTab !== 'settings' || activeSettingsSubTab !== 'effort') return;
  const tag = (document.activeElement && document.activeElement.tagName) || '';
  if (tag === 'INPUT' || tag === 'TEXTAREA' || tag === 'SELECT') return;
  const levels = currentModelFamily === 'claude'
    ? ['low', 'medium', 'high', 'xhigh', 'max']
    : ['low', 'medium', 'high'];
  const curEff = pendingEffortSelection || currentStudioSettings.effort || 'high';
  const curIdx = levels.indexOf(curEff);

  if (e.key === 'ArrowRight' || e.key === 'ArrowDown') {
    e.preventDefault();
    const nextIdx = (curIdx + 1) % levels.length;
    pendingEffortSelection = levels[nextIdx];
    updateEffortUI(pendingEffortSelection);
    markSettingsDirty(true);
  } else if (e.key === 'ArrowLeft' || e.key === 'ArrowUp') {
    e.preventDefault();
    const prevIdx = (curIdx - 1 + levels.length) % levels.length;
    pendingEffortSelection = levels[prevIdx];
    updateEffortUI(pendingEffortSelection);
    markSettingsDirty(true);
  } else if (e.key === 'Enter') {
    e.preventDefault();
    const targetEffort = pendingEffortSelection || currentStudioSettings.effort || 'high';
    onPageEffortChange(targetEffort);
    pendingEffortSelection = null;
  }
});

document.addEventListener('keydown', (e) => {
  if ((e.ctrlKey || e.metaKey) && (e.key === 'o' || e.key === 'O')) {
    const tag = (document.activeElement && document.activeElement.tagName) || '';
    if (tag === 'INPUT' || tag === 'TEXTAREA' || tag === 'SELECT') return;
    e.preventDefault();
    const visibleStepOutputs = document.querySelectorAll('[id^="step_out_"]');
    if (visibleStepOutputs.length > 0) {
      const lastOutput = visibleStepOutputs[visibleStepOutputs.length - 1];
      lastOutput.classList.toggle('hidden');
    }
  }
});

let isSettingsDirty = false;

function markSettingsDirty(dirty = true) {
  isSettingsDirty = dirty;
  const btn = document.getElementById('btnSaveSettingsPage');
  if (!btn) return;
  if (dirty) {
    btn.classList.add('is-dirty');
    btn.classList.remove('cursor-not-allowed', 'bg-slate-700/60', 'text-slate-400');
    btn.removeAttribute('disabled');
  } else {
    btn.classList.remove('is-dirty');
    btn.classList.add('cursor-not-allowed', 'bg-slate-700/60', 'text-slate-400');
  }
}
window.markSettingsDirty = markSettingsDirty;

function onSettingsOptionChanged() {
  markSettingsDirty(true);
}
window.onSettingsOptionChanged = onSettingsOptionChanged;

let activeSettingsSubTab = 'effort';

function switchSettingsSidebarTab(tab, updateHistory = true) {
  if (!['effort', 'engine', 'account', 'api', 'env'].includes(tab)) tab = 'effort';
  activeSettingsSubTab = tab;
  window.initSettingsSubTab = tab;
  try {
    localStorage.setItem('activeSettingsSubTab', tab);
  } catch (e) { }

  const initStyle = document.getElementById('initialSettingsSubTabStyle');
  if (initStyle) initStyle.remove();

  const subRoutes = window.SETTINGS_SUBTAB_ROUTES || {
    'effort': '/settings/effort',
    'engine': '/settings/engine',
    'account': '/settings/account',
    'api': '/settings/api',
    'env': '/settings/env'
  };
  const targetPath = subRoutes[tab] || '/settings/effort';
  if (updateHistory && activeTab === 'settings' && window.location.pathname !== targetPath) {
    try {
      window.history.pushState({ tab: 'settings', settingsSubTab: tab }, '', targetPath);
    } catch (e) { }
  }

  const tabs = ['effort', 'engine', 'account', 'api', 'env'];
  tabs.forEach(t => {
    const navBtn = document.getElementById('settingsNav_' + t);
    const panel = document.getElementById('settingsPanel_' + t);
    if (navBtn) {
      if (t === tab) {
        navBtn.classList.add('is-active', 'bg-blue-600', 'border-blue-500', 'text-white', 'shadow-md');
        navBtn.classList.remove('bg-[#0c1628]', 'border-[#244170]/40', 'text-slate-400', 'bg-cyan-950/50', 'border-cyan-500/70', 'text-slate-300');
      } else {
        navBtn.classList.remove('is-active', 'bg-blue-600', 'border-blue-500', 'bg-cyan-950/50', 'border-cyan-500/70', 'text-white', 'shadow-md');
        navBtn.classList.add('bg-[#0c1628]', 'border-[#244170]/40', 'text-slate-400');
      }
    }
    if (panel) {
      if (t === tab) {
        panel.classList.remove('hidden');
      } else {
        panel.classList.add('hidden');
      }
    }
  });
}
window.switchSettingsSidebarTab = switchSettingsSidebarTab;

function selectActiveApiProvider(provider) {
  if (!['gemini', 'claude', 'openai', 'custom'].includes(provider)) provider = 'gemini';
  currentStudioSettings.api_provider = provider;

  ['gemini', 'claude', 'openai', 'custom'].forEach(p => {
    const btn = document.getElementById('btn_provider_' + p);
    if (btn) {
      if (p === provider) btn.classList.add('is-active');
      else btn.classList.remove('is-active');
    }
  });

  const tag = document.getElementById('pageCurrentApiProviderTag');
  if (tag) {
    const labels = {
      'gemini': 'GOOGLE GEMINI',
      'claude': 'ANTHROPIC CLAUDE',
      'openai': 'OPENAI / GPT',
      'custom': 'CUSTOM / 9ROUTER'
    };
    tag.textContent = labels[provider] || provider.toUpperCase();
  }

  markSettingsDirty(true);
}
window.selectActiveApiProvider = selectActiveApiProvider;

function togglePasswordVisibility(inputId) {
  const el = document.getElementById(inputId);
  if (!el) return;
  el.type = el.type === 'password' ? 'text' : 'password';
}
window.togglePasswordVisibility = togglePasswordVisibility;

async function testApiKey(provider) {
  let key = '';
  let endpoint = '';
  if (provider === 'gemini') {
    key = document.getElementById('input_gemini_api_key')?.value?.trim() || '';
  } else if (provider === 'claude') {
    key = document.getElementById('input_claude_api_key')?.value?.trim() || '';
  } else if (provider === 'openai') {
    key = document.getElementById('input_openai_api_key')?.value?.trim() || '';
  } else if (provider === 'custom') {
    key = document.getElementById('input_custom_api_key')?.value?.trim() || '';
    endpoint = document.getElementById('input_custom_endpoint')?.value?.trim() || '';
  }

  if (!key && provider !== 'custom') {
    showToast('Vui lòng nhập API Key trước khi kiểm tra.', 'warning');
    return;
  }

  showToast(`Đang kiểm tra kết nối tới ${provider.toUpperCase()}...`, 'info');

  try {
    const res = await fetch('/api/test-api-key', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ provider, api_key: key, endpoint })
    });
    const d = await res.json();
    if (d.success) {
      showToast(d.message || `Kết nối ${provider.toUpperCase()} thành công!`, 'success');
      const badge = document.getElementById(`badge_${provider}_key_status`);
      if (badge) {
        badge.textContent = 'Kết nối OK';
        badge.className = 'text-[10px] font-sans px-2 py-0.5 rounded bg-emerald-950 text-emerald-400 border border-emerald-700 font-medium';
      }
    } else {
      showToast(d.message || `Kiểm tra ${provider.toUpperCase()} thất bại`, 'error');
      const badge = document.getElementById(`badge_${provider}_key_status`);
      if (badge) {
        badge.textContent = 'Thất bại';
        badge.className = 'text-[10px] font-sans px-2 py-0.5 rounded bg-rose-950 text-rose-400 border border-rose-700 font-medium';
      }
    }
  } catch (err) {
    showToast('Lỗi kiểm tra API: ' + err.message, 'error');
  }
}
window.testApiKey = testApiKey;

function updateApiUI(settings) {
  if (!settings) settings = currentStudioSettings;
  const prov = settings.api_provider || 'gemini';
  ['gemini', 'claude', 'openai', 'custom'].forEach(p => {
    const btn = document.getElementById('btn_provider_' + p);
    if (btn) {
      if (p === prov) btn.classList.add('is-active');
      else btn.classList.remove('is-active');
    }
  });

  const tag = document.getElementById('pageCurrentApiProviderTag');
  if (tag) {
    const labels = {
      'gemini': 'GOOGLE GEMINI',
      'claude': 'ANTHROPIC CLAUDE',
      'openai': 'OPENAI / GPT',
      'custom': 'CUSTOM / 9ROUTER'
    };
    tag.textContent = labels[prov] || prov.toUpperCase();
  }

  if (settings.gemini_api_key !== undefined) {
    const el = document.getElementById('input_gemini_api_key');
    if (el && !el.matches(':focus')) el.value = settings.gemini_api_key || '';
  }
  if (settings.claude_api_key !== undefined) {
    const el = document.getElementById('input_claude_api_key');
    if (el && !el.matches(':focus')) el.value = settings.claude_api_key || '';
  }
  if (settings.openai_api_key !== undefined) {
    const el = document.getElementById('input_openai_api_key');
    if (el && !el.matches(':focus')) el.value = settings.openai_api_key || '';
  }
  if (settings.custom_api_key !== undefined) {
    const el = document.getElementById('input_custom_api_key');
    if (el && !el.matches(':focus')) el.value = settings.custom_api_key || '';
  }
  if (settings.custom_endpoint !== undefined) {
    const el = document.getElementById('input_custom_endpoint');
    if (el && !el.matches(':focus')) el.value = settings.custom_endpoint || '';
  }

  updateApiKeyBadges(settings);
}
window.updateApiUI = updateApiUI;

function updateApiKeyBadges(settings) {
  if (!settings) settings = currentStudioSettings;
  const setBadge = (id, hasVal, opt = false) => {
    const b = document.getElementById(id);
    if (!b) return;
    if (hasVal) {
      b.textContent = 'Đã lưu';
      b.className = 'text-[10px] font-sans px-2 py-0.5 rounded bg-emerald-950 text-emerald-400 border border-emerald-700 font-medium';
    } else {
      b.textContent = opt ? 'Tùy chọn' : 'Chưa lưu';
      b.className = 'text-[10px] font-sans px-2 py-0.5 rounded bg-slate-800 text-slate-400 border border-slate-700 font-medium';
    }
  };
  setBadge('badge_gemini_key_status', !!settings.gemini_api_key);
  setBadge('badge_claude_key_status', !!settings.claude_api_key);
  setBadge('badge_openai_key_status', !!settings.openai_api_key);
  setBadge('badge_custom_key_status', !!(settings.custom_endpoint || settings.custom_api_key), true);
}

async function handleSaveSettingsClick() {
  await saveSettingsFromPage();
}
window.handleSaveSettingsClick = handleSaveSettingsClick;

async function saveSettingsFromPage() {
  const selectedEngineRadio = document.querySelector('input[name="page_engine"]:checked');
  const engine = selectedEngineRadio ? selectedEngineRadio.value : (currentStudioSettings.engine || 'gemini_cli');
  const effort = currentStudioSettings.effort || 'high';
  const model = currentStudioSettings.model || 'gemini-3.8-flash-high';
  const opencodeModelSelect = document.getElementById('pageSettingsOpencodeModelSelect');
  const opencode_model = opencodeModelSelect ? opencodeModelSelect.value : (currentStudioSettings.opencode_model || '9router/ag/gemini-3.8-flash-high');
  const api_provider = currentStudioSettings.api_provider || 'gemini';

  const gemini_api_key = document.getElementById('input_gemini_api_key')?.value?.trim() ?? (currentStudioSettings.gemini_api_key || '');
  const claude_api_key = document.getElementById('input_claude_api_key')?.value?.trim() ?? (currentStudioSettings.claude_api_key || '');
  const openai_api_key = document.getElementById('input_openai_api_key')?.value?.trim() ?? (currentStudioSettings.openai_api_key || '');
  const custom_api_key = document.getElementById('input_custom_api_key')?.value?.trim() ?? (currentStudioSettings.custom_api_key || '');
  const custom_endpoint = document.getElementById('input_custom_endpoint')?.value?.trim() ?? (currentStudioSettings.custom_endpoint || '');

  const fe_workspace = document.getElementById('input_fe_workspace')?.value?.trim() ?? (currentStudioSettings.fe_workspace || '');
  const be_workspace = document.getElementById('input_be_workspace')?.value?.trim() ?? (currentStudioSettings.be_workspace || '');
  const agy_bin = document.getElementById('input_agy_bin')?.value?.trim() ?? (currentStudioSettings.agy_bin || '');
  const opencode_bin = document.getElementById('input_opencode_bin')?.value?.trim() ?? (currentStudioSettings.opencode_bin || '');

  currentStudioSettings = Object.assign({}, currentStudioSettings, {
    engine,
    effort,
    model,
    opencode_model,
    api_provider,
    gemini_api_key,
    claude_api_key,
    openai_api_key,
    custom_api_key,
    custom_endpoint,
    fe_workspace,
    be_workspace,
    agy_bin,
    opencode_bin
  });

  updateEngineUI(engine, nineRouterOnline);
  updateEffortUI(effort);
  updateApiUI(currentStudioSettings);
  updateEnvUI(currentStudioSettings);

  const saveBtnText = document.getElementById('btnSaveSettingsPageText');
  const saveBtnIcon = document.getElementById('btnSaveSettingsPageIcon');
  if (saveBtnText) saveBtnText.textContent = 'Đang lưu...';

  try {
    const res = await fetch('/api/settings', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        settings: {
          engine,
          effort,
          model,
          opencode_model,
          api_provider,
          gemini_api_key,
          claude_api_key,
          openai_api_key,
          custom_api_key,
          custom_endpoint,
          fe_workspace,
          be_workspace,
          agy_bin,
          opencode_bin
        }
      })
    });
    const d = await res.json();
    if (d.nine_router_online !== undefined) {
      nineRouterOnline = !!d.nine_router_online;
      updateEngineUI(engine, nineRouterOnline);
    }
    if (d.gemini_cli_status) {
      updateGeminiCliUI(d.gemini_cli_status);
    }
    if (d.success) {
      markSettingsDirty(false);
      showToast(d.message || 'Đã lưu cấu hình thành công!');
      updateApiKeyBadges(currentStudioSettings);
      updateEnvUI(currentStudioSettings, d.env_info);
    } else {
      showToast(d.message || 'Lỗi khi lưu cài đặt', 'error');
    }
  } catch (err) {
    showToast('Lỗi kết nối khi lưu cài đặt: ' + err.message, 'error');
  } finally {
    if (saveBtnText) saveBtnText.textContent = 'Lưu cài đặt';
    if (saveBtnIcon) saveBtnIcon.textContent = '✓';
  }
}
window.saveSettingsFromPage = saveSettingsFromPage;

function updateEnvUI(settings, envInfo) {
  if (!settings) settings = currentStudioSettings;
  const feInput = document.getElementById('input_fe_workspace');
  if (feInput && !feInput.matches(':focus')) {
    feInput.value = settings.fe_workspace || (envInfo && envInfo.fe_workspace) || '/run/media/thietnv/Data/Project/easysalon-webapp';
  }
  const beInput = document.getElementById('input_be_workspace');
  if (beInput && !beInput.matches(':focus')) {
    beInput.value = settings.be_workspace || (envInfo && envInfo.be_workspace) || '/run/media/thietnv/Data/Project/easysalon-api';
  }
  const agyInput = document.getElementById('input_agy_bin');
  if (agyInput && !agyInput.matches(':focus')) {
    agyInput.value = settings.agy_bin || (envInfo && envInfo.agy_bin) || '';
  }
  const openInput = document.getElementById('input_opencode_bin');
  if (openInput && !openInput.matches(':focus')) {
    openInput.value = settings.opencode_bin || (envInfo && envInfo.opencode_bin) || '';
  }

  if (envInfo) {
    const setStatusBadge = (id, exists, labelOk, labelMissing) => {
      const b = document.getElementById(id);
      if (!b) return;
      if (exists) {
        b.textContent = labelOk;
        b.className = 'text-[10px] font-sans px-2 py-0.5 rounded bg-emerald-950 text-emerald-400 border border-emerald-700 font-medium';
      } else {
        b.textContent = labelMissing;
        b.className = 'text-[10px] font-sans px-2 py-0.5 rounded bg-amber-950 text-amber-400 border border-amber-700 font-medium';
      }
    };
    setStatusBadge('badge_fe_workspace_status', envInfo.fe_exists, 'Tồn tại', 'Không tìm thấy');
    setStatusBadge('badge_be_workspace_status', envInfo.be_exists, 'Tồn tại', 'Không tìm thấy');
    setStatusBadge('badge_agy_bin_status', envInfo.agy_exists, 'Sẵn sàng', 'Chưa cài CLI');
    setStatusBadge('badge_opencode_bin_status', envInfo.opencode_exists, 'Sẵn sàng', 'Chưa cài CLI');
  }
}
window.updateEnvUI = updateEnvUI;

function openSettingsModal() {
  switchTab('settings');
}
function closeSettingsModal() {}
function onModalEngineChange(e) { onPageEngineChange(e); }
function onModalEffortChange(e) { onPageEffortChange(e); }
function saveSettingsFromModal() { saveSettingsFromPage(); }

function switchTab(tab, updateHistory = true) {
  if (tab === 'live' || tab === 'fixbug') {
    const actionType = tab === 'fixbug' ? 'fixbug' : 'task';
    tab = 'task';
    if (typeof setTaskActionType === 'function') setTaskActionType(actionType);
  }
  if (!TABS.includes(tab)) tab = 'task';
  activeTab = tab;
  try { localStorage.setItem('activeAgentStudioTab', tab); } catch (e) { }

  const initStyle = document.getElementById('initialTabStyle');
  if (initStyle) initStyle.remove();
  const initGitSubStyle = document.getElementById('initialGitSubTabStyle');
  if (initGitSubStyle) initGitSubStyle.remove();

  let targetPath = (window.TAB_ROUTES && window.TAB_ROUTES[tab]) || ('/' + tab);
  if (tab === 'branch') {
    const currentPath = (window.location.pathname || '/').replace(/\/+$/, '') || '/';
    const urlSub = window.ROUTE_TO_GIT_SUBTAB && window.ROUTE_TO_GIT_SUBTAB[currentPath];
    const sub = window.initGitSubTab || urlSub || activeGitSubTab || 'pull_sync';
    const subRoutes = window.GIT_SUBTAB_ROUTES || {
      'pull_sync': '/git-control',
      'branch': '/git-control/checkout-branch',
      'cherry_pick': '/git-control/cherry-pick',
      'merge': '/git-control/merge'
    };
    targetPath = subRoutes[sub] || '/git-control';
  } else if (tab === 'settings') {
    const currentPath = (window.location.pathname || '/').replace(/\/+$/, '') || '/';
    const urlSub = window.ROUTE_TO_SETTINGS_SUBTAB && window.ROUTE_TO_SETTINGS_SUBTAB[currentPath];
    const sub = window.initSettingsSubTab || urlSub || activeSettingsSubTab || 'effort';
    const subRoutes = window.SETTINGS_SUBTAB_ROUTES || {
      'effort': '/settings/effort',
      'engine': '/settings/engine',
      'account': '/settings/account',
      'api': '/settings/api',
      'env': '/settings/env'
    };
    targetPath = subRoutes[sub] || '/settings/effort';
  }
  if (updateHistory && window.location.pathname !== targetPath) {
    try {
      const gitSub = window.initGitSubTab || activeGitSubTab || 'pull_sync';
      const settingsSub = window.initSettingsSubTab || activeSettingsSubTab || 'effort';
      window.history.pushState({
        tab: tab,
        subTab: tab === 'branch' ? gitSub : null,
        settingsSubTab: tab === 'settings' ? settingsSub : null
      }, '', targetPath);
    } catch (e) { }
  }

  TABS.forEach(t => {
    const viewEl = document.getElementById('view_' + t);
    const btnEl = document.getElementById('tabBtn_' + t);
    if (viewEl) {
      viewEl.classList.add('hidden');
      viewEl.style.setProperty('display', 'none', 'important');
    }
    if (btnEl) {
      btnEl.className = 'px-3.5 py-1.5 rounded-md text-slate-200 hover:text-white hover:bg-white/10 font-medium transition text-xs cursor-pointer select-none';
    }
  });

  const activeView = document.getElementById('view_' + tab);
  const activeBtn = document.getElementById('tabBtn_' + tab);
  if (activeView) {
    activeView.classList.remove('hidden');
    if (tab === 'task') {
      activeView.style.setProperty('display', 'grid', 'important');
    } else {
      activeView.style.setProperty('display', 'block', 'important');
    }
  }
  if (activeBtn) {
    activeBtn.className = 'px-3.5 py-1.5 rounded-md bg-[#ffffff] text-[#182c4f] font-bold shadow-sm transition text-xs cursor-pointer select-none';
  }

  window.scrollTo({ top: 0, behavior: 'instant' });

  try {
    if (tab === 'task') {
      if (typeof pollStatus === 'function') pollStatus();
    } else if (tab === 'branch') {
      const currentPath = (window.location.pathname || '/').replace(/\/+$/, '') || '/';
      const urlSub = window.ROUTE_TO_GIT_SUBTAB && window.ROUTE_TO_GIT_SUBTAB[currentPath];
      const sub = window.initGitSubTab || urlSub || activeGitSubTab || 'pull_sync';
      activeGitSubTab = sub;
      window.initGitSubTab = sub;
      if (typeof switchGitSubTab === 'function') {
        switchGitSubTab(sub, false);
      } else if (typeof loadPullSyncInfo === 'function') {
        loadPullSyncInfo();
      }
    } else if (tab === 'log') {
      if (typeof loadWorkLogs === 'function') loadWorkLogs();
    } else if (tab === 'diagram') {
      if (typeof renderDiagram === 'function') renderDiagram();
    } else if (tab === 'settings') {
      const currentPath = (window.location.pathname || '/').replace(/\/+$/, '') || '/';
      const urlSub = window.ROUTE_TO_SETTINGS_SUBTAB && window.ROUTE_TO_SETTINGS_SUBTAB[currentPath];
      const sub = window.initSettingsSubTab || urlSub || activeSettingsSubTab || 'effort';
      window.initSettingsSubTab = null;
      switchSettingsSidebarTab(sub, false);
      fetch('/api/settings')
        .then(r => r.json())
        .then(d => {
          if (d && d.settings) {
            currentStudioSettings = Object.assign({}, currentStudioSettings, d.settings);
          }
          if (d && d.nine_router_online !== undefined) {
            nineRouterOnline = !!d.nine_router_online;
          }
          if (d && d.gemini_cli_status) {
            updateGeminiCliUI(d.gemini_cli_status);
          }
          updateEngineUI(currentStudioSettings.engine, nineRouterOnline);
          updateEffortUI(currentStudioSettings.effort);
          updateApiUI(currentStudioSettings);
          updateEnvUI(currentStudioSettings, d.env_info);
          markSettingsDirty(false);
        })
        .catch(() => {});
    }
  } catch (err) {
    console.error('Lỗi khi kích hoạt callback của tab:', tab, err);
  }
}
window.switchTab = switchTab;

let activeGitSubTab = 'pull_sync';

function switchGitSubTab(subTab, updateHistory = true) {
  if (!['branch', 'cherry_pick', 'pull_sync', 'merge'].includes(subTab)) subTab = 'pull_sync';
  activeGitSubTab = subTab;
  window.initGitSubTab = subTab;

  const initGitSubStyle = document.getElementById('initialGitSubTabStyle');
  if (initGitSubStyle) initGitSubStyle.remove();

  const subRoutes = window.GIT_SUBTAB_ROUTES || {
    'pull_sync': '/git-control',
    'branch': '/git-control/checkout-branch',
    'cherry_pick': '/git-control/cherry-pick',
    'merge': '/git-control/merge'
  };
  const targetPath = subRoutes[subTab] || '/git-control';
  if (updateHistory && activeTab === 'branch' && window.location.pathname !== targetPath) {
    try {
      window.history.pushState({ tab: 'branch', subTab: subTab }, '', targetPath);
    } catch (e) { }
  }
  try { localStorage.setItem('activeGitSubTab', subTab); } catch(e) {}

  const btnBranch = document.getElementById('gitSubTabBtn_branch');
  const btnCherry = document.getElementById('gitSubTabBtn_cherry_pick');
  const btnSync = document.getElementById('gitSubTabBtn_pull_sync');
  const btnMerge = document.getElementById('gitSubTabBtn_merge');

  const viewBranch = document.getElementById('gitSubView_branch');
  const viewCherry = document.getElementById('gitSubView_cherry_pick');
  const viewSync = document.getElementById('gitSubView_pull_sync');
  const viewMerge = document.getElementById('gitSubView_merge');

  const isLight = document.body.classList.contains('light-mode');
  const activeCls = 'active-git-subtab px-3.5 py-1.5 rounded-md bg-[rgb(25,156,255)] text-white font-bold text-xs shadow-sm transition cursor-pointer select-none';
  const inactiveCls = isLight
    ? 'px-3.5 py-1.5 rounded-md text-[#334155] hover:text-[#0f172a] hover:bg-slate-200/60 font-medium text-xs transition cursor-pointer select-none'
    : 'px-3.5 py-1.5 rounded-md text-slate-300 hover:text-white hover:bg-white/10 font-medium text-xs transition cursor-pointer select-none';

  if (viewBranch) viewBranch.classList.add('hidden');
  if (viewCherry) viewCherry.classList.add('hidden');
  if (viewSync) viewSync.classList.add('hidden');
  if (viewMerge) viewMerge.classList.add('hidden');

  if (btnBranch) btnBranch.className = inactiveCls;
  if (btnCherry) btnCherry.className = inactiveCls;
  if (btnSync) btnSync.className = inactiveCls;
  if (btnMerge) btnMerge.className = inactiveCls;

  if (subTab === 'branch') {
    if (viewBranch) viewBranch.classList.remove('hidden');
    if (btnBranch) btnBranch.className = activeCls;
    if (typeof loadGitBranchInfo === 'function') loadGitBranchInfo();
  } else if (subTab === 'cherry_pick') {
    if (viewCherry) viewCherry.classList.remove('hidden');
    if (btnCherry) btnCherry.className = activeCls;
    if (typeof loadCherryPickInfo === 'function') loadCherryPickInfo();
  } else if (subTab === 'merge') {
    if (viewMerge) viewMerge.classList.remove('hidden');
    if (btnMerge) btnMerge.className = activeCls;
    if (typeof loadMergeInfo === 'function') loadMergeInfo();
  } else {
    if (viewSync) viewSync.classList.remove('hidden');
    if (btnSync) btnSync.className = activeCls;
    if (typeof loadPullSyncInfo === 'function') loadPullSyncInfo();
  }
}
window.switchGitSubTab = switchGitSubTab;

async function refreshCurrentGitView() {
  const btn = document.getElementById('btnRefreshGit');
  const spinner = document.getElementById('refreshGitSpinner');
  const text = document.getElementById('refreshGitText');
  if (btn) btn.disabled = true;
  if (spinner) spinner.classList.remove('hidden');
  if (text) text.textContent = 'Đang tải...';

  try {
    if (activeGitSubTab === 'cherry_pick') {
      if (typeof loadCherryPickInfo === 'function') await loadCherryPickInfo();
    } else if (activeGitSubTab === 'pull_sync') {
      if (typeof loadPullSyncInfo === 'function') await loadPullSyncInfo();
    } else if (activeGitSubTab === 'merge') {
      if (typeof loadMergeInfo === 'function') await loadMergeInfo();
    } else {
      if (typeof loadGitBranchInfo === 'function') await loadGitBranchInfo();
    }
    showToast('Đã làm mới dữ liệu Git.');
  } catch (err) {
    showToast('Lỗi khi làm mới: ' + err.message);
  } finally {
    if (btn) btn.disabled = false;
    if (spinner) spinner.classList.add('hidden');
    if (text) text.textContent = 'Làm mới';
  }
}
window.refreshCurrentGitView = refreshCurrentGitView;

window.addEventListener('popstate', (e) => {
  const currentPath = (window.location.pathname || '/').replace(/\/+$/, '') || '/';
  let targetTab = (e.state && e.state.tab) || (typeof window.getTabFromUrl === 'function' ? window.getTabFromUrl() : null) || 'task';
  let targetSubTab = (e.state && e.state.subTab) || (window.ROUTE_TO_GIT_SUBTAB && window.ROUTE_TO_GIT_SUBTAB[currentPath]) || window.initGitSubTab;
  switchTab(targetTab, false);
  if (targetTab === 'branch') {
    if (!targetSubTab) targetSubTab = 'pull_sync';
    if (typeof switchGitSubTab === 'function') {
      window.initGitSubTab = null;
      switchGitSubTab(targetSubTab, false);
    }
  }
});

const DIAGRAM_MODULES = [
  {
    id: 'booking-bedroom',
    title: 'Phòng & Sơ đồ giường (BedRoom)',
    skill: 'skill-booking-bedroom',
    api: {
      route: '/bed-room-position',
      endpoints: [
        { method: 'GET', path: '/bed-room-position', note: 'Lấy sơ đồ danh sách phòng & giường' },
        { method: 'POST', path: '/bed-room-position/change-bed', note: 'Chuyển đổi giường / di dời dịch vụ' },
        { method: 'PUT', path: '/bed-room-position/{id}/status', note: 'Đổi trạng thái giường (trống/bận)' }
      ]
    },
    fe: {
      path: 'src/scripts/business/bed-room',
      resource: 'src/scripts/restful/resources/bedRoomPosition.ts',
      desc: 'Quản lý bản đồ sơ đồ giường, trạng thái ghế bận/trống realtime, modal chuyển đổi giường khách đang làm dịch vụ.',
      imports: [
        '@/business/booking',
        '@/business/customer',
        '@/scripts/restful/resources/bedRoomPosition',
        '@/scripts/helpers/formatHelper'
      ],
      exports: [
        'BedRoomMapContainer',
        'BedItemCard',
        'ChangeBedModal',
        'useBedRoomState'
      ]
    },
    be: {
      path: 'Controllers/BedRoomPositionController.cs',
      controller: 'BedRoomPositionController : BaseApiController',
      desc: 'Xử lý truy vấn trạng thái phòng/giường đa chi nhánh, giao dịch atomic đổi giường an toàn cho KTV.',
      injections: [
        'IBedRoomPositionService',
        'IBookingService',
        'IUnitOfWork',
        'ISalonBranchContext'
      ],
      exports: [
        'GetBedRoomPositions() -> ApiResponse<List<BedRoomPositionDto>>',
        'ChangeBed(ChangeBedRequestDto) -> ApiResponse<bool>',
        'UpdateStatus(int id, UpdateStatusDto) -> ApiResponse'
      ],
      links: ['Booking (Ràng buộc lịch hẹn)', 'SalonBranchId (Filter phòng)']
    }
  },
  {
    id: 'pos-cashier',
    title: 'Thu ngân & Bán hàng (POS / Invoice)',
    skill: 'skill-pos-cashier',
    api: {
      route: '/api/v1/invoices',
      endpoints: [
        { method: 'POST', path: '/api/v1/invoices', note: 'Tạo hóa đơn bán lẻ / dịch vụ' },
        { method: 'GET', path: '/api/v1/invoices/{id}', note: 'Lấy chi tiết đơn hàng & thanh toán' },
        { method: 'POST', path: '/api/v1/invoices/{id}/pay', note: 'Xác nhận thanh toán đa phương thức' }
      ]
    },
    fe: {
      path: 'src/scripts/business/invoice',
      resource: 'src/scripts/restful/resources/invoice.ts',
      desc: 'Màn hình thu ngân POS, chọn dịch vụ/sản phẩm/combo, áp khuyến mãi, chia bill, in phiếu hóa đơn.',
      imports: [
        '@/business/customer',
        '@/business/invoice-detail',
        '@/business/commission',
        '@/business/cashbook-transaction',
        '@/scripts/restful/resources/invoice'
      ],
      exports: [
        'InvoiceContainer',
        'InvoiceItemTable',
        'PaymentModal',
        'useInvoiceStore'
      ]
    },
    be: {
      path: 'Controllers/InvoiceController.cs',
      controller: 'InvoiceController : BaseApiController',
      desc: 'Trọng tâm đơn hàng POS: Điều phối thanh toán, tự động trừ kho nguyên phụ liệu, tính hoa hồng KTV và ghi nhận sổ quỹ.',
      injections: [
        'IInvoiceLocalService',
        'ProductInventoryService',
        'CommissionService',
        'PaymentReceiptService',
        'IUnitOfWork'
      ],
      exports: [
        'CreateInvoiceAsync(InvoiceRequestDto) -> ApiResponse<InvoiceDto>',
        'PayInvoiceAsync(int id, PaymentRequestDto) -> ApiResponse',
        'CancelInvoiceAsync(int id, CancelReasonDto) -> ApiResponse'
      ],
      links: ['Kho hàng (Trừ tồn kho)', 'Hoa hồng (Ghi nhận KTV)', 'Sổ quỹ (Phiếu thu)', 'HĐĐT (Phát hành)']
    }
  },
  {
    id: 'calendar-schedule',
    title: 'Lịch hẹn & Ca làm việc (Booking / Calendar)',
    skill: 'skill-calendar-schedule',
    api: {
      route: '/api/v1/bookings',
      endpoints: [
        { method: 'GET', path: '/api/v1/bookings', note: 'Lấy lịch đặt hẹn theo ngày/chi nhánh' },
        { method: 'POST', path: '/api/v1/bookings', note: 'Đặt lịch hẹn mới cho khách' },
        { method: 'PUT', path: '/api/v1/bookings/{id}/checkin', note: 'Check-in khách vào giường' }
      ]
    },
    fe: {
      path: 'src/scripts/business/booking',
      resource: 'src/scripts/restful/resources/booking.ts',
      desc: 'Lịch biểu đặt hẹn theo nhân viên, khung giờ, check-in khách đến salon và đẩy vào danh sách chờ.',
      imports: [
        '@/business/customer',
        '@/business/bed-room',
        '@/scripts/restful/resources/booking',
        '@/scripts/helpers/dateHelper'
      ],
      exports: [
        'BookingCalendarContainer',
        'BookingCreateModal',
        'BookingCardItem',
        'useBookingCalendar'
      ]
    },
    be: {
      path: 'Controllers/BookingController.cs',
      controller: 'BookingController : BaseApiController',
      desc: 'Quản lý lịch hẹn, kiểm tra trùng khung giờ KTV, thông báo nhắc hẹn Zalo/SMS và luồng check-in.',
      injections: [
        'IBookingService',
        'ICustomerService',
        'IStaffScheduleService',
        'IUnitOfWork'
      ],
      exports: [
        'GetBookingsAsync(BookingFilterDto) -> ApiResponse<List<BookingDto>>',
        'CreateBookingAsync(BookingCreateDto) -> ApiResponse<BookingDto>',
        'CheckinBookingAsync(int id) -> ApiResponse<bool>'
      ],
      links: ['Customer (Hồ sơ khách)', 'BedRoomPosition (Gán giường)', 'Staff (Ca làm việc)']
    }
  },
  {
    id: 'customer-crm',
    title: 'Khách hàng & Hạng thẻ VIP (Customer CRM)',
    skill: 'skill-customer-crm',
    api: {
      route: '/api/v1/customers',
      endpoints: [
        { method: 'GET', path: '/api/v1/customers', note: 'Tra cứu danh sách & phân hạng thẻ khách' },
        { method: 'POST', path: '/api/v1/customers', note: 'Thêm mới hồ sơ khách hàng' },
        { method: 'GET', path: '/api/v1/customers/{id}/debts', note: 'Tra cứu sổ công nợ khách hàng' }
      ]
    },
    fe: {
      path: 'src/scripts/business/customer',
      resource: 'src/scripts/restful/resources/customer.ts',
      desc: 'Quản lý thông tin khách, lịch sử trị liệu, điểm tích lũy thành viên, hạn mức công nợ và sinh nhật.',
      imports: [
        '@/scripts/restful/resources/customer',
        '@/business/customer-group',
        '@/business/customer-debt',
        '@/components/common/AvatarUploader'
      ],
      exports: [
        'CustomerListTable',
        'CustomerDetailDrawer',
        'CustomerDebtHistory',
        'useCustomerStore'
      ]
    },
    be: {
      path: 'Controllers/CustomerController.cs',
      controller: 'CustomerController : BaseApiController',
      desc: 'Hồ sơ 360 độ khách hàng, xếp hạng thẻ tự động theo doanh số, kiểm soát hạn mức công nợ tối đa.',
      injections: [
        'ICustomerService',
        'ICustomerDebtService',
        'ICustomerRankService',
        'IUnitOfWork'
      ],
      exports: [
        'GetCustomersAsync(CustomerFilterDto) -> ApiResponse<PagedList<CustomerDto>>',
        'CreateCustomerAsync(CustomerCreateDto) -> ApiResponse<CustomerDto>',
        'GetCustomerDebtsAsync(int id) -> ApiResponse<DebtSummaryDto>'
      ],
      links: ['Invoice (Lịch sử chi tiêu)', 'Booking (Lịch hẹn)', 'Package (Liệu trình đã mua)']
    }
  },
  {
    id: 'warehouse-inventory',
    title: 'Kho hàng & Nhập xuất tồn (Warehouse)',
    skill: 'skill-warehouse-inventory',
    api: {
      route: '/api/v1/warehouse-transactions',
      endpoints: [
        { method: 'GET', path: '/api/v1/warehouse-transactions', note: 'Danh sách phiếu nhập / xuất kho' },
        { method: 'POST', path: '/api/v1/warehouse-transactions/import', note: 'Tạo phiếu nhập hàng nhà cung cấp' },
        { method: 'POST', path: '/api/v1/warehouse-transactions/deduct', note: 'Trừ kho hao phí nguyên vật liệu làm dịch vụ' }
      ]
    },
    fe: {
      path: 'src/scripts/business/warehouse-transaction',
      resource: 'src/scripts/restful/resources/warehouseTransaction.ts',
      desc: 'Phiếu nhập xuất kho, kiểm kê định kỳ, cấu hình định mức tiêu hao nguyên vật liệu trên từng gói dịch vụ.',
      imports: [
        '@/scripts/restful/resources/warehouseTransaction',
        '@/business/product',
        '@/business/supplier',
        '@/components/common/BarcodeScanner'
      ],
      exports: [
        'WarehouseTransactionTable',
        'CreateImportNoteModal',
        'InventoryCheckForm',
        'useWarehouseStore'
      ]
    },
    be: {
      path: 'Controllers/WarehouseTransactionController.cs',
      controller: 'WarehouseTransactionController : BaseApiController',
      desc: 'Tính giá vốn bình quân gia quyền, quản lý tồn kho theo lô/hạn dùng, tự động trừ kho khi POS chốt bill.',
      injections: [
        'IProductInventoryService',
        'IWarehouseTransactionService',
        'ISupplierService',
        'IUnitOfWork'
      ],
      exports: [
        'GetTransactionsAsync(FilterDto) -> ApiResponse<PagedList<WarehouseDto>>',
        'CreateImportNoteAsync(ImportNoteDto) -> ApiResponse<int>',
        'DeductConsumptionAsync(DeductDto) -> ApiResponse<bool>'
      ],
      links: ['Invoice (Trừ kho bán lẻ & tiêu hao)', 'Cashbook (Phiếu chi trả NCC)']
    }
  },
  {
    id: 'commission-setup',
    title: 'Hoa hồng & Chiết khấu KTV (Commission)',
    skill: 'skill-commission-setup',
    api: {
      route: '/api/v1/commissions',
      endpoints: [
        { method: 'GET', path: '/api/v1/commissions/policies', note: 'Lấy chính sách hoa hồng KTV' },
        { method: 'POST', path: '/api/v1/commissions/calculate', note: 'Tính toán hoa hồng theo hóa đơn' },
        { method: 'GET', path: '/api/v1/commissions/report-staff', note: 'Báo cáo tổng hợp hoa hồng theo nhân viên' }
      ]
    },
    fe: {
      path: 'src/scripts/business/commission-setup',
      resource: 'src/scripts/restful/resources/commission.ts',
      desc: 'Cấu hình công thức hoa hồng theo % hoặc tiền cố định, chia hoa hồng nhiều KTV làm chung 1 bill.',
      imports: [
        '@/scripts/restful/resources/commission',
        '@/business/staff',
        '@/business/service-category'
      ],
      exports: [
        'CommissionPolicySetting',
        'StaffCommissionTable',
        'useCommissionStore'
      ]
    },
    be: {
      path: 'Controllers/CommissionController.cs',
      controller: 'CommissionController : BaseApiController',
      desc: 'Engine tính toán hoa hồng: phân bổ tỷ lệ KTV chính, phụ, tư vấn viên; bảo lưu doanh số tính lương.',
      injections: [
        'ICommissionService',
        'IStaffService',
        'ISalaryService',
        'IUnitOfWork'
      ],
      exports: [
        'GetPoliciesAsync() -> ApiResponse<List<CommissionPolicyDto>>',
        'CalculateBillCommissionAsync(int invoiceId) -> ApiResponse<CommissionResultDto>',
        'GetStaffCommissionSummaryAsync(DateRangeDto) -> ApiResponse<SummaryDto>'
      ],
      links: ['Invoice (Hóa đơn phát sinh)', 'TimeSheet/Salary (Đẩy vào bảng lương)']
    }
  },
  {
    id: 'revenue-expenditure',
    title: 'Thu chi & Sổ quỹ tiền mặt (Cashbook)',
    skill: 'skill-revenue-expenditure',
    api: {
      route: '/api/v1/cashbook-transactions',
      endpoints: [
        { method: 'GET', path: '/api/v1/cashbook-transactions', note: 'Tra cứu danh sách phiếu thu/chi' },
        { method: 'POST', path: '/api/v1/cashbook-transactions/receipt', note: 'Tạo phiếu thu tiền mặt / chuyển khoản' },
        { method: 'POST', path: '/api/v1/cashbook-transactions/payment', note: 'Tạo phiếu chi tiền' }
      ]
    },
    fe: {
      path: 'src/scripts/business/cashbook-transaction',
      resource: 'src/scripts/restful/resources/cashbookTransaction.ts',
      desc: 'Sổ thu chi salon, quản lý dòng tiền mặt, chuyển khoản, ví điện tử, đối soát đầu ca & kết ca.',
      imports: [
        '@/scripts/restful/resources/cashbookTransaction',
        '@/business/invoice',
        '@/components/common/PaymentMethodSelector'
      ],
      exports: [
        'CashbookTransactionTable',
        'ReceiptPaymentModal',
        'ShiftEndReport',
        'useCashbookStore'
      ]
    },
    be: {
      path: 'Controllers/CashbookTransactionController.cs',
      controller: 'CashbookTransactionController : BaseApiController',
      desc: 'Quản lý sổ quỹ tiền, hạch toán phiếu thu khi thanh toán đơn hàng, hạch toán phiếu chi mua hàng và chi lương.',
      injections: [
        'IPaymentReceiptService',
        'ICashbookBalanceService',
        'IUnitOfWork'
      ],
      exports: [
        'GetTransactionsAsync(CashbookFilterDto) -> ApiResponse<PagedList<CashbookDto>>',
        'CreateReceiptAsync(CreateReceiptDto) -> ApiResponse<int>',
        'CreatePaymentAsync(CreatePaymentDto) -> ApiResponse<int>'
      ],
      links: ['Invoice (Phiếu thu bán hàng)', 'Warehouse (Phiếu chi nhập hàng)', 'Salary (Phiếu chi lương)']
    }
  },
  {
    id: 'service-package-combo',
    title: 'Gói liệu trình & Thẻ combo (Package)',
    skill: 'skill-service-package-combo',
    api: {
      route: '/api/v1/packages',
      endpoints: [
        { method: 'GET', path: '/api/v1/packages', note: 'Lấy danh mục gói liệu trình & combo' },
        { method: 'POST', path: '/api/v1/packages/treatment-history', note: 'Trừ buổi liệu trình khi khách làm dịch vụ' },
        { method: 'GET', path: '/api/v1/packages/customer/{customerId}', note: 'Gói liệu trình đang sở hữu của khách' }
      ]
    },
    fe: {
      path: 'src/scripts/business/package',
      resource: 'src/scripts/restful/resources/package.ts',
      desc: 'Cấu hình combo nhiều buổi, quản lý thẻ làm đẹp của khách, check-in trừ số buổi còn lại và hạn dùng thẻ.',
      imports: [
        '@/scripts/restful/resources/package',
        '@/business/customer',
        '@/business/treatment'
      ],
      exports: [
        'PackageManagementTable',
        'CustomerTreatmentCard',
        'DeductTreatmentSessionModal',
        'usePackageStore'
      ]
    },
    be: {
      path: 'Controllers/PackageController.cs',
      controller: 'PackageController : BaseApiController',
      desc: 'Kiểm soát hạn mức số buổi liệu trình, ghi nhật ký hình ảnh trước/sau điều trị, bảo lưu thẻ khách.',
      injections: [
        'IPackageService',
        'ITreatmentHistoryService',
        'ICustomerService',
        'IUnitOfWork'
      ],
      exports: [
        'GetPackagesAsync() -> ApiResponse<List<PackageDto>>',
        'DeductTreatmentAsync(DeductSessionDto) -> ApiResponse<bool>',
        'GetCustomerTreatmentsAsync(int customerId) -> ApiResponse<List<CustomerPackageDto>>'
      ],
      links: ['Customer (Thẻ sở hữu)', 'BedRoom (Trừ buổi tại giường)', 'Invoice (Bán gói combo)']
    }
  },
  {
    id: 'tax-einvoice',
    title: 'Hóa đơn điện tử (E-Invoice)',
    skill: 'skill-tax-einvoice',
    api: {
      route: '/api/v1/e-invoices',
      endpoints: [
        { method: 'POST', path: '/api/v1/e-invoices/issue', note: 'Phát hành HĐĐT kết nối Tổng cục Thuế' },
        { method: 'GET', path: '/api/v1/e-invoices/{invoiceId}/status', note: 'Tra cứu trạng thái cấp mã CQT' },
        { method: 'POST', path: '/api/v1/e-invoices/cancel', note: 'Hủy hoặc lập hóa đơn điều chỉnh' }
      ]
    },
    fe: {
      path: 'src/scripts/business/electronic-invoice',
      resource: 'src/scripts/restful/resources/electronicInvoice.ts',
      desc: 'Quản lý phát hành hóa đơn điện tử máy tính tiền (VNPT / Viettel / MISA), ký số và gửi email hóa đơn khách.',
      imports: [
        '@/scripts/restful/resources/electronicInvoice',
        '@/business/invoice'
      ],
      exports: [
        'ElectronicInvoiceTable',
        'IssueInvoiceModal',
        'InvoiceStatusBadge',
        'useEInvoiceStore'
      ]
    },
    be: {
      path: 'Controllers/ElectronicInvoiceController.cs',
      controller: 'ElectronicInvoiceController : BaseApiController',
      desc: 'Tích hợp API đối tác Thuế, xử lý XML/JSON ký số điện tử, đồng bộ mã xác thực của Cơ quan Thuế.',
      injections: [
        'IElectronicInvoiceProviderService',
        'IInvoiceService',
        'IUnitOfWork'
      ],
      exports: [
        'IssueInvoiceAsync(IssueEInvoiceDto) -> ApiResponse<EInvoiceResultDto>',
        'CheckCqtStatusAsync(int id) -> ApiResponse<EInvoiceStatusDto>',
        'CancelEInvoiceAsync(CancelEInvoiceDto) -> ApiResponse<bool>'
      ],
      links: ['Invoice (Dữ liệu đơn hàng gốc POS)']
    }
  },
  {
    id: 'payroll-timesheet',
    title: 'Chấm công & Bảng lương (Payroll)',
    skill: 'skill-payroll-timesheet',
    api: {
      route: '/api/v1/time-sheets',
      endpoints: [
        { method: 'GET', path: '/api/v1/time-sheets', note: 'Dữ liệu chấm công ca kíp nhân viên' },
        { method: 'POST', path: '/api/v1/time-sheets/checkin', note: 'Check-in vân tay / wifi chi nhánh' },
        { method: 'POST', path: '/api/v1/salaries/calculate', note: 'Chốt bảng lương & hoa hồng tháng' }
      ]
    },
    fe: {
      path: 'src/scripts/business/time-sheet',
      resource: 'src/scripts/restful/resources/timeSheet.ts',
      desc: 'Bảng theo dõi công chuẩn, đi muộn về sớm, phê duyệt nghỉ phép và tổng hợp phiếu lương từng KTV.',
      imports: [
        '@/scripts/restful/resources/timeSheet',
        '@/business/staff',
        '@/business/commission'
      ],
      exports: [
        'TimeSheetCalendar',
        'SalarySummaryTable',
        'StaffPayslipModal',
        'useTimeSheetStore'
      ]
    },
    be: {
      path: 'Controllers/TimeSheetController.cs',
      controller: 'TimeSheetController : BaseApiController',
      desc: 'Tổng hợp công từ máy chấm công, tính lương cứng + phụ cấp + hoa hồng dịch vụ - các khoản phạt.',
      injections: [
        'ITimeSheetService',
        'ISalaryCalculationService',
        'ICommissionService',
        'IUnitOfWork'
      ],
      exports: [
        'GetTimeSheetsAsync(TimeSheetFilterDto) -> ApiResponse<List<TimeSheetDto>>',
        'CalculateMonthlySalaryAsync(int month, int year) -> ApiResponse<SalaryReportDto>'
      ],
      links: ['Commission (Hoa hồng tháng)', 'Cashbook (Sinh phiếu chi lương)']
    }
  },
  {
    id: 'report-analytics',
    title: 'Báo cáo & Thống kê (Analytics)',
    skill: 'skill-report-analytics',
    api: {
      route: '/api/v1/reports',
      endpoints: [
        { method: 'GET', path: '/api/v1/reports/revenue-overview', note: 'Tổng quan doanh thu, lợi nhuận gộp' },
        { method: 'GET', path: '/api/v1/reports/staff-performance', note: 'Hiệu suất làm việc & phục vụ của KTV' },
        { method: 'GET', path: '/api/v1/reports/inventory-depletion', note: 'Báo cáo tiêu hao nguyên vật liệu' }
      ]
    },
    fe: {
      path: 'src/scripts/business/report',
      resource: 'src/scripts/restful/resources/report.ts',
      desc: 'Biểu đồ trực quan doanh thu theo giờ, tỷ lệ lấp đầy ghế/giường salon, top dịch vụ bán chạy nhất.',
      imports: [
        '@/scripts/restful/resources/report',
        '@/business/invoice',
        '@/business/warehouse-transaction',
        '@/components/common/Charts'
      ],
      exports: [
        'RevenueOverviewChart',
        'StaffPerformanceRanking',
        'InventoryDepletionReport',
        'useReportStore'
      ]
    },
    be: {
      path: 'Controllers/ReportController.cs',
      controller: 'ReportController : BaseApiController',
      desc: 'Tối ưu hóa các query tổng hợp lớn (Aggregation queries), cache kết quả phân tích theo chi nhánh.',
      injections: [
        'IReportService',
        'IAnalyticsEngine',
        'ISalonBranchContext'
      ],
      exports: [
        'GetRevenueOverviewAsync(ReportDateRangeDto) -> ApiResponse<RevenueOverviewDto>',
        'GetStaffPerformanceAsync(ReportDateRangeDto) -> ApiResponse<List<StaffPerformanceDto>>'
      ],
      links: ['Invoice', 'Cashbook', 'WarehouseTransaction', 'BedRoomPosition']
    }
  }
];

function scrollToBottom(role) {
  const container = document.getElementById(role === 'fe' ? 'feTerminalStream' : 'beTerminalStream');
  const btn = document.getElementById(role === 'fe' ? 'feScrollBottomBtn' : 'beScrollBottomBtn');
  if (container) {
    container.scrollTo({ top: container.scrollHeight, behavior: 'smooth' });
  }
  if (btn) btn.classList.add('hidden');
}

function setupScrollListeners() {
  ['fe', 'be'].forEach(role => {
    const container = document.getElementById(role === 'fe' ? 'feTerminalStream' : 'beTerminalStream');
    const btn = document.getElementById(role === 'fe' ? 'feScrollBottomBtn' : 'beScrollBottomBtn');
    if (!container) return;

    container.addEventListener('scroll', () => {
      const isAtBottom = (container.scrollHeight - container.scrollTop - container.clientHeight) <= 80;
      if (btn) {
        if (isAtBottom) {
          btn.classList.add('hidden');
        } else {
          btn.classList.remove('hidden');
        }
      }
    });
  });
}

async function fetchTerminals() {
  try {
    const res = await fetch('/api/terminals');
    const data = await res.json();
    renderTerminalFeed('fe', data.fe);
    renderTerminalFeed('be', data.be);
  } catch (err) { }
}

const LANG_MAP = {
  json: { label: 'JSON', file: 'payload.json', icon: '{}', color: '#cbcb41' },
  javascript: { label: 'JavaScript', file: 'script.js', icon: 'JS', color: '#f7df1e' },
  js: { label: 'JavaScript', file: 'script.js', icon: 'JS', color: '#f7df1e' },
  typescript: { label: 'TypeScript', file: 'snippet.ts', icon: 'TS', color: '#3178c6' },
  ts: { label: 'TypeScript', file: 'snippet.ts', icon: 'TS', color: '#3178c6' },
  tsx: { label: 'React TSX', file: 'Component.tsx', icon: 'TSX', color: '#3178c6' },
  jsx: { label: 'React JSX', file: 'Component.jsx', icon: 'JSX', color: '#61dafb' },
  csharp: { label: 'C# .NET', file: 'snippet.cs', icon: 'C#', color: '#239120' },
  cs: { label: 'C# .NET', file: 'snippet.cs', icon: 'C#', color: '#239120' },
  dotnet: { label: 'C# .NET', file: 'Program.cs', icon: 'C#', color: '#512bd4' },
  sql: { label: 'SQL', file: 'query.sql', icon: 'SQL', color: '#e38c00' },
  mysql: { label: 'MySQL', file: 'query.sql', icon: 'SQL', color: '#00758f' },
  bash: { label: 'Bash', file: 'terminal.sh', icon: '$', color: '#4eaa25' },
  sh: { label: 'Shell', file: 'script.sh', icon: '$', color: '#4eaa25' },
  shell: { label: 'Shell', file: 'script.sh', icon: '$', color: '#4eaa25' },
  zsh: { label: 'Zsh', file: 'script.zsh', icon: '$', color: '#4eaa25' },
  python: { label: 'Python', file: 'main.py', icon: 'PY', color: '#3572a5' },
  py: { label: 'Python', file: 'main.py', icon: 'PY', color: '#3572a5' },
  html: { label: 'HTML', file: 'index.html', icon: '<>', color: '#e34c26' },
  xml: { label: 'XML', file: 'config.xml', icon: '<>', color: '#e34c26' },
  css: { label: 'CSS', file: 'styles.css', icon: '#', color: '#563d7c' },
  scss: { label: 'SCSS', file: 'styles.scss', icon: '#', color: '#c6538c' },
  diff: { label: 'Git Diff', file: 'changes.diff', icon: '±', color: '#40c463' },
  patch: { label: 'Patch', file: 'patch.diff', icon: '±', color: '#40c463' },
  yaml: { label: 'YAML', file: 'config.yaml', icon: 'YML', color: '#cb171e' },
  yml: { label: 'YAML', file: 'config.yml', icon: 'YML', color: '#cb171e' }
};

function escapeBasic(str) {
  if (!str) return '';
  return String(str)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;');
}

function highlightVsCode(code, lang) {
  if (!code) return '';
  lang = (lang || '').toLowerCase().trim();
  const trimmed = code.trim();

  if (!lang || lang === 'json' || lang === 'js' || lang === 'ts') {
    if ((trimmed.startsWith('{') && trimmed.endsWith('}')) || (trimmed.startsWith('[') && trimmed.endsWith(']'))) {
      lang = 'json';
    }
  }

  if (lang === 'json') {
    const jsonRegex = /("(?:\\u[\da-fA-F]{4}|\\[^u]|[^\\"])*")(\s*:)?|\b(true|false|null)\b|-?\d+(?:\.\d*)?(?:[eE][+\-]?\d+)?|(\.\.\.)|([{}[\],:])/g;
    return code.replace(jsonRegex, (match, strVal, colon, boolVal, ellipsis, bracket) => {
      if (strVal) {
        if (colon) {
          return `<span class="vsc-key">${escapeBasic(strVal)}</span><span class="vsc-punct">:</span>`;
        } else {
          return `<span class="vsc-string">${escapeBasic(strVal)}</span>`;
        }
      } else if (boolVal) {
        return `<span class="vsc-keyword">${boolVal}</span>`;
      } else if (ellipsis) {
        return `<span class="vsc-comment">${ellipsis}</span>`;
      } else if (bracket) {
        if (bracket === '{' || bracket === '}') return `<span class="vsc-bracket-1">${bracket}</span>`;
        if (bracket === '[' || bracket === ']') return `<span class="vsc-bracket-2">${bracket}</span>`;
        return `<span class="vsc-punct">${bracket}</span>`;
      } else {
        return `<span class="vsc-number">${match}</span>`;
      }
    });
  }

  const tokenRegex = /("(?:\\.|[^"\\])*"|'(?:\\.|[^'\\])*'|`(?:\\.|[^`\\])*`)|(\/\/.*$|\/\*[\s\S]*?\*\/|#.*$)|(\b(?:const|let|var|function|return|if|else|for|while|switch|case|break|continue|try|catch|finally|throw|class|interface|type|extends|implements|import|export|from|default|async|await|new|this|super|public|private|protected|static|readonly|get|set|void|string|number|boolean|any|true|false|null|undefined|namespace|using|in|is|of|typeof|instanceof|select|from|where|insert|into|update|delete|join|inner|left|right|on|group|by|order|asc|desc|limit)\b)|(\b-?\d+(?:\.\d+)?\b)|(\b[a-zA-Z_$][a-zA-Z0-9_$]*(?=\s*\())|([{}()[\];,])/gm;

  let lastIdx = 0;
  let out = '';
  let match;
  while ((match = tokenRegex.exec(code)) !== null) {
    if (match.index > lastIdx) {
      out += escapeBasic(code.substring(lastIdx, match.index));
    }
    const [full, str, comment, keyword, num, fn, punct] = match;
    if (str) {
      out += `<span class="vsc-string">${escapeBasic(str)}</span>`;
    } else if (comment) {
      out += `<span class="vsc-comment">${escapeBasic(comment)}</span>`;
    } else if (keyword) {
      if (/^(if|else|for|while|switch|case|return|break|continue|try|catch|finally|throw|import|export|from)$/.test(keyword)) {
        out += `<span class="vsc-control">${escapeBasic(keyword)}</span>`;
      } else {
        out += `<span class="vsc-keyword">${escapeBasic(keyword)}</span>`;
      }
    } else if (num) {
      out += `<span class="vsc-number">${escapeBasic(num)}</span>`;
    } else if (fn) {
      out += `<span class="vsc-func">${escapeBasic(fn)}</span>`;
    } else if (punct) {
      if (punct === '{' || punct === '}') out += `<span class="vsc-bracket-1">${punct}</span>`;
      else if (punct === '[' || punct === ']') out += `<span class="vsc-bracket-2">${punct}</span>`;
      else if (punct === '(' || punct === ')') out += `<span class="vsc-bracket-3">${punct}</span>`;
      else out += `<span class="vsc-punct">${punct}</span>`;
    } else {
      out += escapeBasic(full);
    }
    lastIdx = tokenRegex.lastIndex;
  }
  if (lastIdx < code.length) {
    out += escapeBasic(code.substring(lastIdx));
  }
  return out;
}

let _currentMarkdownContextFiles = [];
let _currentMarkdownRawText = '';

function resolveVsCodeFilename(code, normLang, customFilename) {
  if (customFilename) return customFilename;

  let contextFiles = _currentMarkdownContextFiles || [];
  if (!contextFiles || contextFiles.length === 0) {
    if (typeof parallelTasks !== 'undefined' && Array.isArray(parallelTasks)) {
      const curTask = parallelTasks.find(t => t.id === activeTaskId);
      if (curTask && curTask.changed_files && curTask.changed_files.length > 0) {
        contextFiles = curTask.changed_files;
      }
    }
  }

  if (Array.isArray(contextFiles) && contextFiles.length > 0) {
    const fileObjs = contextFiles.map(f => {
      const p = (typeof f === 'string' ? f : (f.path || f.name || f.file || '')).trim();
      const base = p.split('/').pop() || p;
      const ext = base.includes('.') ? base.split('.').pop().toLowerCase() : '';
      return { path: p, base, ext };
    }).filter(o => o.base);

    for (const f of fileObjs) {
      const stem = f.base.replace(/\.[^.]+$/, '');
      if (stem.length > 2 && code.includes(stem)) {
        return f.base;
      }
    }

    const langExtMap = {
      typescript: ['ts', 'tsx'],
      ts: ['ts', 'tsx'],
      tsx: ['tsx'],
      javascript: ['js', 'jsx', 'mjs', 'cjs'],
      js: ['js', 'jsx'],
      jsx: ['jsx'],
      csharp: ['cs'],
      cs: ['cs'],
      dotnet: ['cs'],
      python: ['py'],
      py: ['py'],
      json: ['json'],
      html: ['html', 'htm'],
      css: ['css'],
      scss: ['scss'],
      sql: ['sql'],
      mysql: ['sql'],
      bash: ['sh', 'bash'],
      sh: ['sh'],
      shell: ['sh'],
      yaml: ['yaml', 'yml'],
      yml: ['yaml', 'yml']
    };
    const validExts = langExtMap[normLang] || [normLang];
    const matchExt = fileObjs.find(f => validExts.includes(f.ext));
    if (matchExt) {
      return matchExt.base;
    }

    if (fileObjs.length === 1) {
      return fileObjs[0].base;
    }
  }

  if (_currentMarkdownRawText) {
    const matches = _currentMarkdownRawText.match(/[\w\-./\\]+\.(?:tsx|ts|jsx|js|cs|json|sql|py|html|css|scss|sh|ya?ml)\b/gi);
    if (matches && matches.length > 0) {
      for (const m of matches) {
        const base = m.split('/').pop();
        if (base && !base.startsWith('http')) {
          const ext = base.split('.').pop().toLowerCase();
          const langExtMap = {
            typescript: ['ts', 'tsx'],
            ts: ['ts', 'tsx'],
            tsx: ['tsx'],
            javascript: ['js', 'jsx'],
            js: ['js'],
            csharp: ['cs'],
            cs: ['cs'],
            dotnet: ['cs']
          };
          const validExts = langExtMap[normLang] || [normLang];
          if (validExts.includes(ext) || code.includes(base.replace(/\.[^.]+$/, ''))) {
            return base;
          }
        }
      }
    }
  }

  const defaultExt = (normLang === 'typescript' ? 'ts' : (normLang === 'csharp' ? 'cs' : (normLang || 'txt')));
  return `snippet.${defaultExt}`;
}

function renderVsCodeBlock(code, lang) {
  const cleanCode = (code || '').trimEnd();
  const lines = cleanCode.split('\n');
  let normLang = (lang || '').toLowerCase().trim();
  let customFilename = '';

  if (normLang && (normLang.includes(':') || normLang.includes(' '))) {
    const parts = normLang.split(/[:\s]+/);
    normLang = (parts[0] || '').toLowerCase().trim();
    customFilename = parts[1] || '';
  }

  if (!normLang) {
    const trimmed = cleanCode.trim();
    if ((trimmed.startsWith('{') && trimmed.endsWith('}')) || (trimmed.startsWith('[') && trimmed.endsWith(']'))) {
      normLang = 'json';
    }
  }

  const activeFilename = customFilename || resolveVsCodeFilename(cleanCode, normLang, customFilename);
  const fileExt = activeFilename.includes('.') ? activeFilename.split('.').pop().toLowerCase() : normLang;
  const meta = Object.assign({}, LANG_MAP[fileExt] || LANG_MAP[normLang] || {
    label: (fileExt || normLang || 'CODE').toUpperCase(),
    file: activeFilename,
    icon: '</>',
    color: '#007acc'
  });
  meta.file = activeFilename;

  const highlightedHtml = highlightVsCode(cleanCode, normLang);

  return `
<div class="vscode-editor-card my-3 rounded-lg overflow-hidden border border-[#2d2d2d] bg-[#1e1e1e] shadow-xl font-mono text-[12px] text-[#d4d4d4]" data-code="${encodeURIComponent(cleanCode)}">
  <div class="vscode-editor-header flex items-center justify-between px-3 py-1.5 bg-[#252526] border-b border-[#2d2d2d] select-none text-[11px]">
    <div class="flex items-center gap-2">
      <div class="vscode-mac-dots flex items-center gap-1.5 mr-2">
        <span class="vscode-dot vscode-dot-red"></span>
        <span class="vscode-dot vscode-dot-yellow"></span>
        <span class="vscode-dot vscode-dot-green"></span>
      </div>
      <div class="vscode-tab flex items-center gap-1.5 px-2.5 py-0.5 rounded-t bg-[#1e1e1e] border-t-2 border-t-[#007acc] text-[#cccccc] font-mono text-[11px] shadow-sm">
        <span style="color: ${meta.color}; font-weight: bold; font-size: 11px;">${meta.icon}</span>
        <span class="text-[#cccccc] font-medium truncate max-w-[220px]">${meta.file}</span>
      </div>
    </div>
    <div class="flex items-center gap-2">
      <span class="text-[10px] uppercase font-semibold text-slate-400 font-mono tracking-wider">${meta.label}</span>
      <button type="button" onclick="copyVsCodeSnippet(this)"
        class="vscode-copy-btn flex items-center gap-1 px-2.5 py-0.5 rounded bg-[#2d2d2d] hover:bg-[#3e3e42] text-slate-300 hover:text-white transition text-[11px] cursor-pointer border border-[#3c3c3c] shadow-sm select-none"
        title="Sao chép toàn bộ code">
        <svg class="w-3.5 h-3.5 fill-none stroke-current" viewBox="0 0 24 24" stroke-width="2">
          <path stroke-linecap="round" stroke-linejoin="round" d="M8 16H6a2 2 0 01-2-2V6a2 2 0 012-2h8a2 2 0 012 2v2m-6 12h8a2 2 0 002-2v-8a2 2 0 00-2-2h-8a2 2 0 00-2 2v8a2 2 0 002 2z"/>
        </svg>
        <span>Copy</span>
      </button>
    </div>
  </div>
  <div class="vscode-editor-body p-3 overflow-x-auto text-[12px] leading-[1.65] bg-[#1e1e1e] text-[#d4d4d4]">
    <div class="vscode-code-wrap flex font-mono text-[12px] leading-[1.65]">
      <div class="vscode-line-numbers select-none text-right pr-3.5 pl-1 text-[#858585] border-r border-[#333333] shrink-0 font-mono text-[12px] leading-[1.65]">
        ${lines.map((_, idx) => `<div>${idx + 1}</div>`).join('')}
      </div>
      <div class="vscode-code-content pl-3.5 flex-1 overflow-x-auto font-mono text-[12px] leading-[1.65] whitespace-pre">
        <pre class="m-0 p-0 bg-transparent border-0 font-mono text-[12px] leading-[1.65] whitespace-pre"><code class="p-0 bg-transparent border-0 font-mono text-[12px] leading-[1.65] whitespace-pre text-[#d4d4d4]">${highlightedHtml}</code></pre>
      </div>
    </div>
  </div>
</div>
  `.trim();
}

function copyVsCodeSnippet(btn) {
  if (!btn) return;
  const card = btn.closest('.vscode-editor-card');
  if (!card) return;
  const rawCode = decodeURIComponent(card.getAttribute('data-code') || '');
  if (!rawCode) return;

  const originalHtml = btn.innerHTML;
  const doFeedback = () => {
    btn.innerHTML = `
      <svg class="w-3.5 h-3.5 fill-none stroke-emerald-400" viewBox="0 0 24 24" stroke-width="2">
        <path stroke-linecap="round" stroke-linejoin="round" d="M5 13l4 4L19 7"/>
      </svg>
      <span class="text-emerald-400 font-semibold">Đã chép!</span>
    `;
    setTimeout(() => {
      btn.innerHTML = originalHtml;
    }, 2000);
  };

  if (navigator.clipboard && navigator.clipboard.writeText) {
    navigator.clipboard.writeText(rawCode).then(doFeedback).catch(() => {
      fallbackCopySnippet(rawCode);
      doFeedback();
    });
  } else {
    fallbackCopySnippet(rawCode);
    doFeedback();
  }
}

function fallbackCopySnippet(text) {
  const textarea = document.createElement('textarea');
  textarea.value = text;
  textarea.style.position = 'fixed';
  textarea.style.left = '-9999px';
  textarea.style.top = '0';
  document.body.appendChild(textarea);
  textarea.focus();
  textarea.select();
  try {
    document.execCommand('copy');
  } catch (err) {}
  document.body.removeChild(textarea);
}

function isJsonLike(str) {
  const t = (str || '').trim();
  if (!((t.startsWith('{') && t.endsWith('}')) || (t.startsWith('[') && t.endsWith(']')))) {
    return false;
  }
  try {
    JSON.parse(t);
    return true;
  } catch (e) {}
  const hasKeys = /"[^"]+"\s*:|([a-zA-Z_$][a-zA-Z0-9_$]*\s*:)/.test(t);
  const hasPunct = /[,{}[\]]/.test(t);
  return hasKeys && hasPunct;
}

function wrapRawJsonBlocks(text) {
  if (!text) return '';
  const codeBlockRegex = /```[\s\S]*?```/g;
  const blocks = [];
  let masked = text.replace(codeBlockRegex, (m) => {
    blocks.push(m);
    return `__CODE_BLOCK_${blocks.length - 1}__`;
  });

  masked = masked.replace(/(^|\n)([ \t]*\{[\s\S]*?\n[ \t]*\}|[ \t]*\[[\s\S]*?\n[ \t]*\])(?=\n|$)/g, (match, prefix, candidate) => {
    if (isJsonLike(candidate)) {
      return prefix + '```json\n' + candidate.trim() + '\n```';
    }
    return match;
  });

  return masked.replace(/__CODE_BLOCK_(\d+)__/g, (m, idx) => blocks[Number(idx)]);
}

let _markedVsCodeInitialized = false;
function initMarkedVsCodeRenderer() {
  if (_markedVsCodeInitialized || typeof marked === 'undefined') return;
  try {
    const renderer = new marked.Renderer();
    renderer.code = function(code, lang) {
      if (typeof code === 'object' && code !== null) {
        lang = code.lang;
        code = code.text;
      }
      return renderVsCodeBlock(code, lang);
    };
    if (marked.use) {
      marked.use({ renderer });
    } else if (marked.setOptions) {
      marked.setOptions({ renderer });
    }
    _markedVsCodeInitialized = true;
  } catch (err) {
    console.error('Failed to init marked VS Code renderer', err);
  }
}

window.copyVsCodeSnippet = copyVsCodeSnippet;

function safeMarkdown(text, contextFiles) {
  if (!text) return '';
  _currentMarkdownContextFiles = Array.isArray(contextFiles) ? contextFiles : [];
  _currentMarkdownRawText = typeof text === 'string' ? text : '';
  initMarkedVsCodeRenderer();
  try {
    const preprocessed = wrapRawJsonBlocks(text);
    if (typeof marked !== 'undefined' && marked.parse) {
      return marked.parse(preprocessed);
    }
  } catch (e) { }
  return escapeHtml(text).split('\n').join('<br/>');
}

function renderTerminalFeed(role, feed) {
  const isFe = role === 'fe';
  const container = document.getElementById(isFe ? 'feTerminalStream' : 'beTerminalStream');
  const conclusionCard = document.getElementById(isFe ? 'feCompletedCard' : 'beCompletedCard');
  const conclusionText = document.getElementById(isFe ? 'feCompletedText' : 'beCompletedText');
  const conclusionTime = document.getElementById(isFe ? 'feCompletedTime' : 'beCompletedTime');

  if (!container) return;

  if (feed && feed.completed_result && feed.completed_result.content) {
    if (conclusionCard && conclusionText) {
      conclusionCard.classList.remove('hidden');
      if (conclusionTime) {
        const rawTime = feed.completed_result.timestamp || '';
        conclusionTime.textContent = rawTime.length > 8 ? rawTime.slice(11, 19) : rawTime;
      }
      conclusionText.innerHTML = safeMarkdown(feed.completed_result.content, (feed && feed.changed_files) || []);
    }
  }

  if (!feed || !feed.cid) {
    if (container.dataset.hasSession !== 'false') {
      container.innerHTML = '<div class="text-slate-500 text-center py-12">Chưa phát hiện phiên làm việc nào của Terminal này.</div>';
      container.dataset.hasSession = 'false';
    }
    return;
  }
  container.dataset.hasSession = 'true';

  const messages = feed.messages || [];
  if (messages.length === 0) {
    if (container.dataset.hasMessages !== 'false') {
      container.innerHTML = '<div class="text-slate-500 text-center py-12">Terminal đang mở, chưa có dữ liệu mới.</div>';
      container.dataset.hasMessages = 'false';
    }
    return;
  }
  container.dataset.hasMessages = 'true';

  const lastSignature = container.dataset.lastSignature || '';
  const currentSignature = (feed.cid || '') + '_' + messages.length + '_' + (messages[messages.length - 1]?.timestamp || '');
  if (lastSignature === currentSignature) {
    return;
  }

  const isAtBottom = (container.scrollHeight - container.scrollTop - container.clientHeight) <= 80;

  container.innerHTML = messages.map(m => {
    if (m.role === 'user') {
      return `
            <div class="bg-[#0b0f19] border border-[#1e293b] rounded-md p-3 font-mono">
              <div class="flex items-center justify-between text-[11px] text-slate-400 mb-1">
                <span class="text-amber-400 font-semibold font-mono">Input:</span>
                <span class="text-slate-500">${m.timestamp ? m.timestamp.slice(11, 19) : ''}</span>
              </div>
              <div class="text-slate-200 text-xs font-mono leading-relaxed whitespace-pre-wrap pl-2.5 border-l-2 border-amber-500/60">${escapeHtml(m.content)}</div>
            </div>
          `;
    } else {
      const toolsHtml = m.tools && m.tools.length > 0 ? `
            <div class="flex flex-wrap gap-1.5 mb-2">
              ${m.tools.map(t => `<span class="px-2 py-0.5 rounded bg-slate-800 text-[11px] text-slate-300 border border-slate-700/60 font-mono font-medium">${escapeHtml(t)}</span>`).join('')}
            </div>
          ` : '';

      return `
            <div class="rounded-md border border-[#1e293b] p-3.5 bg-[#050811]">
              <div class="flex items-center justify-between text-[11px] text-slate-400 mb-2">
                <span class="${isFe ? 'text-cyan-400' : 'text-emerald-400'} font-semibold font-mono">
                  Output (${isFe ? 'webapp' : 'api'}):
                </span>
                <span class="text-slate-500 font-mono">${m.timestamp ? m.timestamp.slice(11, 19) : ''}</span>
              </div>
              ${toolsHtml}
              <div class="markdown-body text-[13px] text-slate-200 leading-[1.8] tracking-wide overflow-x-auto">
                ${safeMarkdown(m.content || '', (feed && feed.changed_files) || [])}
              </div>
            </div>
          `;
    }
  }).join('');

  container.dataset.lastSignature = currentSignature;

  if (isAtBottom) {
    container.scrollTop = container.scrollHeight;
  }
}

const FRIENDLY_SKILL_DESCRIPTIONS = {

  'skill-auth': 'Phân quyền 8 Host, JWT & lọc CurrentSalonId',
  'skill-base': 'Cây kế thừa Base (Controller, Service, UnitOfWork)',
  'skill-bridge-frontend': 'Cầu nối liên agent Backend <-> Frontend qua bridge.py',
  'skill-business-flow': 'Luồng nghiệp vụ cốt lõi: PayInvoice, CheckIn, Hủy/Xóa đơn',
  'skill-catalog': 'Tra cứu CATALOG.md, chống tạo symbol ảo',
  'skill-commission': 'Tính hoa hồng nhân viên (Thế hệ Cũ vs Mới)',
  'skill-controller': 'Chuẩn Controller, OkList, ActionBaseValue, DTO vs Entity',
  'skill-debug': 'Quy trình 5 bước điều tra lỗi EF ChangeTracker & HTTP',
  'skill-entity': 'EF Core Model, Mapping snake/Pascal, Migration MySQL',
  'skill-export-excel': 'Xuất file Excel ClosedXML & OpenXML streaming',
  'skill-import-excel': 'Import Excel: Preview & Submit',
  'skill-integration': 'Tích hợp HDĐT (MISA, Viettel, VNPT), SMS Vihat, QR MB',
  'skill-kafka': 'Kafka Producer, Consumer topic, Background worker QUEUE',
  'skill-mimic': 'Mô phỏng file lân cận, nghiêm cấm viết comment',
  'skill-report': 'Báo cáo Dapper raw SQL nhiều bảng, ValidDateRange',
  'skill-schedule': 'Quartz Job định kỳ (IJob) trong SALON_HAIR_SCHEDULE',
  'skill-service': 'Chuẩn tầng Service, DomainService (Manager), UnitOfWork',
  'skill-shared': 'Tiện ích chung: sinh mã tự tăng, SettingAdvance',
  'skill-warehouse': 'Quản lý kho hàng NK/XK/CK, tồn kho, giá vốn',

  'skill-api': 'Cấu hình RESTful API Client & RequestParameter',
  'skill-booking-bedroom': 'Phòng & Vị trí giường / Đổi giường',
  'skill-calendar-schedule': 'Lịch hẹn & Ca làm việc',
  'skill-call-backend': 'Cầu nối gọi Backend API & tra cứu DTO',
  'skill-commission-setup': 'Hoa hồng & Chiết khấu KTV',
  'skill-crud': 'Quy chuẩn hoàn thiện luồng CRUD',
  'skill-customer-crm': 'Khách hàng & Hạng thẻ VIP / Tích điểm',
  'skill-debug-fixbug': 'Quy trình 5 bước điều tra & vá lỗi Frontend',
  'skill-excel-import': 'Đọc và xuất file Excel dữ liệu lớn',
  'skill-form': 'Quy chuẩn Formik & Yup validation schema',
  'skill-layer-flow': 'Event Bus, Redux, Context, subGlobalModal tầng 1 & 2',
  'skill-lint-verify': 'Kiểm tra TypeScript & ESLint',
  'skill-online-booking-portal': 'Cổng đặt hẹn trực tuyến Online',
  'skill-payroll-timesheet': 'Chấm công & Bảng lương',
  'skill-pos-cashier': 'Thu ngân & Bán hàng / Hóa đơn',
  'skill-print-template': 'Mẫu in bill, hóa đơn, barcode',
  'skill-realtime-hardware': 'Máy in bill, két tiền, máy quét mã',
  'skill-refactor-mimic': 'Mô phỏng component lân cận & cấm comment',
  'skill-report-analytics': 'Báo cáo & Thống kê kinh doanh',
  'skill-revenue-expenditure': 'Thu chi & Sổ quỹ tiền mặt',
  'skill-routing-permission': 'Định tuyến RoutePage & phân quyền chi nhánh',
  'skill-service-package-combo': 'Gói liệu trình & Thẻ combo',
  'skill-table': 'Bảng dữ liệu Antd Table, phân trang, sort, filter',
  'skill-tax-einvoice': 'Thuế & Hóa đơn điện tử',
  'skill-warehouse-inventory': 'Kho hàng & Nhập xuất tồn'
};

const SKILLS_DICTIONARY = {

  'skill-auth': 'Phân quyền 8 Host (API, STAFF, PORTAL...), Claims JWT, xác thực và cô lập dữ liệu theo CurrentSalonId.',
  'skill-base': 'Cây kế thừa Base chuẩn: SharedApiControllerBase, SalonControllerBase, ApplicationService, DomainService, UnitOfWork.',
  'skill-bridge-frontend': 'Cầu nối liên agent Backend <-> Frontend qua công cụ bridge.py để đối chiếu model, DTO và Formik.',
  'skill-business-flow': 'Luồng nghiệp vụ chuyển đổi trạng thái cốt lõi: PayInvoice, EditAsPay, CheckIn, hủy/xóa hóa đơn, dùng gói.',
  'skill-catalog': 'Tra cứu ai-boundary/CATALOG.md trước khi viết code, nghiêm cấm tự bịa class, hàm hay hằng status ngoài catalog.',
  'skill-commission': 'Tính toán hoa hồng nhân viên: Rẽ nhánh hệ thống cũ vs mới (CheckUseNewCommission), hook khi Pay/Debt.',
  'skill-controller': 'Chuẩn Web API Controller: Action result Ok, OkList, BadRequest, NotFound, ActionBaseValue, tách DTO vs Entity.',
  'skill-debug': 'Quy trình 5 bước điều tra bug, bẫy lỗi EF Core ChangeTracker, AsNoTracking, transaction commit, lệch múi giờ.',
  'skill-entity': 'Cấu hình EF Core Model, Fluent API mapping snake/Pascal case, Query Filter, Migration MySQL.',
  'skill-export-excel': 'Xuất file Excel ClosedXML và OpenXML streaming, trả trực tiếp FileStreamResult không bọc Ok().',
  'skill-import-excel': 'Import Excel qua ImportHttpHelper: 2 giai đoạn preview (kiểm tra dòng lỗi) và submit (lưu dữ liệu).',
  'skill-integration': 'Tích hợp dịch vụ bên thứ 3: Hóa đơn điện tử (MISA, Viettel, VNPT), SMS Vihat, QR MB Bank, loa TingTing.',
  'skill-kafka': 'Event streaming Kafka Producer (KafkaProducerService), Consumer topic, Background worker trong SALON_HAIR_QUEUE.',
  'skill-mimic': 'Nguyên tắc viết code mô phỏng file lân cận trong cùng thư mục, nghiêm cấm viết comment thừa (//, /* */).',
  'skill-report': 'Báo cáo tổng hợp Dapper raw SQL nhiều bảng hiệu năng cao, validate khoảng ngày GetValidDateRangeQuery.',
  'skill-schedule': 'Quartz Job định kỳ (IJob) trong SALON_HAIR_SCHEDULE, BackgroundWorker và các task chờ.',
  'skill-service': 'Chuẩn tầng ApplicationService (tự saveChange) và DomainService/Manager (dùng lại query, validation).',
  'skill-shared': 'Tiện ích chung: sinh mã tự tăng SysObjectAutoIncrement, SettingAdvance, DefinedException, ngày tháng.',
  'skill-warehouse': 'Quản lý kho hàng: Nhập/xuất/chuyển kho (mã NK, XK, CK), tính giá vốn bình quân và tồn kho.',

  'skill-api': 'Cấu hình RESTful API Client, xử lý mảng RequestParameter, headers và lỗi mạng.',
  'skill-booking-bedroom': 'Bản đồ phòng & giường realtime, cập nhật trạng thái bận/trống, đổi giường, gán KTV làm dịch vụ.',
  'skill-calendar-schedule': 'Đặt lịch hẹn khách hàng, điều phối KTV, xếp ca làm việc và liên kết gán phòng/giường.',
  'skill-call-backend': 'Cầu nối gọi trực tiếp Backend API, tra cứu DTO và đối chiếu payload hợp đồng.',
  'skill-commission-setup': 'Cấu hình hoa hồng KTV theo bậc, dịch vụ, bán sản phẩm, làm tour; tính thưởng tức thì theo bill.',
  'skill-crud': 'Quy chuẩn hoàn thiện luồng CRUD gồm Form + Table + Modal + Event Bus reload.',
  'skill-customer-crm': 'Hồ sơ khách hàng, phân hạng thẻ VIP, tích lũy điểm thưởng, quản lý công nợ và lịch sử dịch vụ.',
  'skill-debug-fixbug': 'Quy trình 5 bước: Phân loại tầng lỗi → Truy vết log/payload → Nạp schema/rule → Vá lỗi vi phẫu → Kiểm chứng.',
  'skill-excel-import': 'Đọc và xuất file Excel dữ liệu lớn, kiểm tra validation dòng lỗi trước khi import.',
  'skill-form': 'Quy chuẩn Formik & Yup validation schema, xử lý submit form, tránh lỗi undefined initialValues.',
  'skill-layer-flow': 'Luồng dữ liệu Event Bus, Redux, Context, quản lý modal tầng 1 và popup tầng 2 (subGlobalModal).',
  'skill-lint-verify': 'Kiểm tra cú pháp TypeScript, quy tắc ESLint và build bundle dự án.',
  'skill-online-booking-portal': 'Cổng đặt hẹn trực tuyến cho khách hàng tự book lịch qua Web / App.',
  'skill-payroll-timesheet': 'Tổng hợp ngày công, ca kíp, phạt đi muộn và tiền hoa hồng trong tháng để chốt bảng lương.',
  'skill-pos-cashier': 'Order dịch vụ, combo, áp mã giảm giá, thanh toán đa phương thức và in phiếu thu hóa đơn.',
  'skill-print-template': 'Thiết kế mẫu in bill nhiệt (K80, K57), phiếu thanh toán và tem nhãn barcode.',
  'skill-realtime-hardware': 'Kết nối phần cứng bán hàng: Máy in bill LAN/USB, két đựng tiền, máy quét mã vạch.',
  'skill-refactor-mimic': 'Mô phỏng component lân cận, tuân thủ kiến trúc hiện hành và không viết comment thừa.',
  'skill-report-analytics': 'Dashboard doanh thu bán lẻ, tỷ lệ lấp đầy giường, hiệu suất KTV và báo cáo lãi lỗ.',
  'skill-revenue-expenditure': 'Tổng hợp phiếu thu bán lẻ, phiếu chi mua kho, chi lương; theo dõi sổ quỹ tiền mặt & ngân hàng.',
  'skill-routing-permission': 'Định tuyến RoutePage, phân quyền chi nhánh (withContext) và bảo vệ route.',
  'skill-service-package-combo': 'Bán thẻ liệu trình nhiều buổi, trừ buổi tự động khi khách làm tại giường, gia hạn thẻ.',
  'skill-table': 'Bảng dữ liệu Antd Table, phân trang, sort, filter, tối ưu render danh sách lớn.',
  'skill-tax-einvoice': 'Kết nối VNPT, Viettel, MISA phát hành hóa đơn điện tử hợp lệ theo quy định Tổng cục Thuế.',
  'skill-warehouse-inventory': 'Quản lý kho xuất nhập tồn, trừ kho hàng bán & định mức tiêu hao nguyên vật liệu làm dịch vụ.'
};

let ALL_CUSTOM_SKILLS = { fe: [], be: [] };

function getSkillShortDesc(name, rawDesc) {
  if (FRIENDLY_SKILL_DESCRIPTIONS[name]) {
    return FRIENDLY_SKILL_DESCRIPTIONS[name];
  }
  if (rawDesc) {
    const clean = rawDesc.replace(/^Use this skill when /i, '').replace(/^Use this skill to /i, '');
    return clean.slice(0, 50) + (clean.length > 50 ? '...' : '');
  }
  return 'Skill nội bộ';
}

function getSkillDesc(skillName) {
  if (SKILLS_DICTIONARY[skillName]) return SKILLS_DICTIONARY[skillName];
  const all = [...(ALL_CUSTOM_SKILLS.fe || []), ...(ALL_CUSTOM_SKILLS.be || [])];
  const item = all.find(s => s.name === skillName);
  return item?.desc || FRIENDLY_SKILL_DESCRIPTIONS[skillName] || '';
}

async function loadCustomSkills() {
  try {
    const res = await fetch('/api/skills');
    ALL_CUSTOM_SKILLS = await res.json();
  } catch (err) { }
  updateSkillDropdowns();
}

let selectedTaskSkills = (() => {
  try {
    const raw = localStorage.getItem('easysalon_selected_skills');
    if (raw) {
      const arr = JSON.parse(raw);
      if (Array.isArray(arr) && arr.length > 0) return arr;
    }
    const draftRaw = localStorage.getItem('easySalon_studio_drafts');
    if (draftRaw) {
      const draft = JSON.parse(draftRaw);
      if (draft && Array.isArray(draft.taskSkills) && draft.taskSkills.length > 0) {
        return draft.taskSkills;
      }
    }
  } catch (e) { }
  return [];
})();
let selectedFixBugSkills = [];

function getAvailableSkills(mode) {
  const scope = mode === 'task'
    ? (document.getElementById('taskTargetSelect')?.value || 'both')
    : (document.getElementById('fixbugScopeSelect')?.value || 'both');

  const feList = ALL_CUSTOM_SKILLS.fe || [];
  const beList = ALL_CUSTOM_SKILLS.be || [];

  if (scope === 'fe') return feList.map(s => ({ ...s, group: 'Frontend' }));
  if (scope === 'be') return beList.map(s => ({ ...s, group: 'Backend' }));
  return [
    ...feList.map(s => ({ ...s, group: 'Frontend' })),
    ...beList.map(s => ({ ...s, group: 'Backend' }))
  ];
}

function toggleSkillDropdown(mode) {
  const dropdown = document.getElementById(mode + 'SkillDropdown');
  const otherMode = mode === 'task' ? 'fixbug' : 'task';
  const otherDropdown = document.getElementById(otherMode + 'SkillDropdown');
  if (otherDropdown) otherDropdown.classList.add('hidden');

  if (!dropdown) return;
  const isHidden = dropdown.classList.contains('hidden');
  if (isHidden) {
    dropdown.classList.remove('hidden');
    renderSkillOptions(mode);
    const searchInput = document.getElementById(mode + 'SkillSearch');
    if (searchInput) {
      searchInput.value = '';
      searchInput.focus();
    }
  } else {
    dropdown.classList.add('hidden');
  }
}

function renderSkillPicker(mode) {
  renderSkillTags(mode);
  renderSkillOptions(mode);
  updateFixBugPromptPreview();
  if (typeof syncFormToCurrentTask === 'function') syncFormToCurrentTask();
  if (mode === 'task') {
    try {
      localStorage.setItem('easysalon_selected_skills', JSON.stringify(selectedTaskSkills));
    } catch (e) { }
    if (typeof saveDraft === 'function') saveDraft(false);
    if (typeof scheduleQueueSync === 'function') scheduleQueueSync();
  }
}

function renderSkillTags(mode) {
  const container = document.getElementById(mode + 'SelectedTags');
  const countEl = document.getElementById(mode + 'SkillCount');
  const selected = mode === 'task' ? selectedTaskSkills : selectedFixBugSkills;

  if (countEl) {
    countEl.textContent = `${selected.length} đã chọn`;
  }

  if (!container) return;

  if (selected.length === 0) {
    container.innerHTML = `<span class="text-slate-400 text-xs px-1 italic">${mode === 'task' ? '-- Tự động quét theo chủ đề --' : '-- Chọn một hoặc nhiều skill kiểm tra --'}</span>`;
    return;
  }

  container.innerHTML = selected.map(s => `
        <span class="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-lg bg-[#199cff] border border-[#199cff] text-white font-mono text-[11px] font-medium shadow-sm transition">
          <span>${escapeHtml(s)}</span>
          <button type="button" onclick="removeSkill('${mode}', '${escapeHtml(s)}', event)" class="text-white/80 hover:text-white font-bold text-xs ml-0.5 leading-none transition-colors">×</button>
        </span>
      `).join('');
}

function renderSkillOptions(mode) {
  const listEl = document.getElementById(mode + 'SkillOptionList');
  if (!listEl) return;

  const searchInput = document.getElementById(mode + 'SkillSearch');
  const q = (searchInput?.value || '').toLowerCase().trim();
  const skills = getAvailableSkills(mode);
  const selected = mode === 'task' ? selectedTaskSkills : selectedFixBugSkills;

  const filtered = skills.filter(s => {
    if (!q) return true;
    return s.name.toLowerCase().includes(q) || (s.desc && s.desc.toLowerCase().includes(q));
  });

  if (filtered.length === 0) {
    listEl.innerHTML = `<div class="text-center py-6 text-slate-400 text-xs">Không có skill nào khớp "${escapeHtml(q)}"</div>`;
    return;
  }

  listEl.innerHTML = filtered.map(s => {
    const isChecked = selected.includes(s.name);
    const shortDesc = getSkillShortDesc(s.name, s.desc);
    return `
          <div onclick="toggleSkillSelection('${mode}', '${escapeHtml(s.name)}')"
            class="skill-option-item ${isChecked ? 'is-selected bg-[#199cff] border border-[#199cff] text-white' : 'border border-transparent'} flex items-start gap-2.5 p-2 rounded-lg cursor-pointer transition">
            <input type="checkbox" ${isChecked ? 'checked' : ''} class="mt-0.5 rounded text-white pointer-events-none accent-[#199cff]" />
            <div class="flex-1 min-w-0">
              <div class="flex items-center gap-2">
                <span class="skill-name font-mono text-xs font-semibold ${isChecked ? 'text-white' : 'text-slate-200'}">${escapeHtml(s.name)}</span>
                <span class="skill-group text-[10px] font-mono px-1.5 py-0.2 rounded ${isChecked ? 'bg-white/20 text-white border border-white/40' : (s.group === 'Frontend' ? 'bg-cyan-950 text-cyan-400 border border-cyan-800' : 'bg-emerald-950 text-emerald-400 border border-emerald-800')}">${s.group}</span>
              </div>
              <div class="skill-desc text-[11px] ${isChecked ? 'text-white/85' : 'text-slate-400'} truncate mt-0.5">${escapeHtml(shortDesc)}</div>
            </div>
          </div>
        `;
  }).join('');
}

function filterSkillOptions(mode) {
  renderSkillOptions(mode);
}

function toggleSkillSelection(mode, skillName) {
  if (mode === 'task') {
    const idx = selectedTaskSkills.indexOf(skillName);
    if (idx >= 0) selectedTaskSkills.splice(idx, 1);
    else selectedTaskSkills.push(skillName);
  } else {
    const idx = selectedFixBugSkills.indexOf(skillName);
    if (idx >= 0) selectedFixBugSkills.splice(idx, 1);
    else selectedFixBugSkills.push(skillName);
  }
  renderSkillPicker(mode);
}

function removeSkill(mode, skillName, event) {
  if (event) event.stopPropagation();
  if (mode === 'task') {
    selectedTaskSkills = selectedTaskSkills.filter(s => s !== skillName);
  } else {
    selectedFixBugSkills = selectedFixBugSkills.filter(s => s !== skillName);
  }
  renderSkillPicker(mode);
}

function selectAllSkills(mode) {
  const skills = getAvailableSkills(mode);
  const names = skills.map(s => s.name);
  if (mode === 'task') {
    selectedTaskSkills = Array.from(new Set([...selectedTaskSkills, ...names]));
  } else {
    selectedFixBugSkills = Array.from(new Set([...selectedFixBugSkills, ...names]));
  }
  renderSkillPicker(mode);
}

function clearAllSkills(mode) {
  if (mode === 'task') {
    selectedTaskSkills = [];
  } else {
    selectedFixBugSkills = [];
  }
  renderSkillPicker(mode);
}

function getActionOpeningPhrase(actionType) {
  if (actionType === 'fixbug') return 'Fix bug:';
  if (actionType === 'refactor') return 'Refactor code:';
  return 'Làm task:';
}
window.getActionOpeningPhrase = getActionOpeningPhrase;

function formatFullPromptWithAction(actionType, slashSkills, desc, log) {
  const opening = getActionOpeningPhrase(actionType);
  const cleanDesc = (desc || '').trim();

  const prefixRegex = /^(?:làm\s*task|thực\s*hiện\s*task|fix\s*bug|sửa\s*lỗi|refactor\s*code|tái\s*cấu\s*trúc(?:\s*mã\s*nguồn)?)(?:\s*[:\-]\s*|\s+)/i;
  let textWithOpening = cleanDesc;
  if (cleanDesc) {
    if (!prefixRegex.test(cleanDesc)) {
      textWithOpening = `${opening} ${cleanDesc}`;
    }
  } else {
    textWithOpening = opening;
  }

  const parts = [];
  const head = [slashSkills, textWithOpening].filter(Boolean).join(' ').trim();
  if (head) parts.push(head);
  if (actionType === 'fixbug' && log && log.trim()) {
    parts.push('Log lỗi:\n' + log.trim());
  }
  return parts.join('\n\n');
}
window.formatFullPromptWithAction = formatFullPromptWithAction;

function updateFixBugPromptPreview() {
  const previewEl = document.getElementById('fixbugPromptPreview');
  const scopeBadge = document.getElementById('fixbugScopeBadge');
  const scope = document.getElementById('taskTargetSelect')?.value || 'both';
  const desc = document.getElementById('taskPromptInput')?.value?.trim() || '';
  const log = document.getElementById('taskLogInput')?.value?.trim() || '';

  if (scopeBadge) {
    if (scope === 'fe') {
      scopeBadge.className = 'font-mono text-[10px] text-cyan-300 bg-cyan-950/80 px-2 py-0.5 rounded border border-cyan-800/80';
      scopeBadge.textContent = 'Frontend (webapp)';
    } else if (scope === 'be') {
      scopeBadge.className = 'font-mono text-[10px] text-emerald-300 bg-emerald-950/80 px-2 py-0.5 rounded border border-emerald-800/80';
      scopeBadge.textContent = 'Backend (api)';
    } else {
      scopeBadge.className = 'font-mono text-[10px] text-indigo-300 bg-indigo-950/80 px-2 py-0.5 rounded border border-indigo-800/80';
      scopeBadge.textContent = 'FE & BE';
    }
  }

  const slashSkills = selectedTaskSkills.map(s => s.startsWith('/') ? s : '/' + s).join(' ');
  const fullPrompt = formatFullPromptWithAction(currentTaskActionType, slashSkills, desc, log);

  if (previewEl) {
    if (desc || slashSkills) {
      previewEl.textContent = fullPrompt;
      previewEl.classList.remove('text-slate-500', 'italic');
      previewEl.classList.add('text-cyan-300');
    } else {
      const openText = getActionOpeningPhrase(currentTaskActionType);
      previewEl.textContent = `-- Chọn skill và nhập nội dung để xem lệnh ${slashSkills ? slashSkills + ' ' : ''}${openText} [mô tả yêu cầu] --`;
      previewEl.classList.add('text-slate-500', 'italic');
      previewEl.classList.remove('text-cyan-300');
    }
  }
}

function onFixBugScopeChange() {
  onTaskTargetChange();
}

function onTaskTargetChange() {
  const val = document.getElementById('taskTargetSelect')?.value || 'both';
  const available = getAvailableSkills('task').map(s => s.name);
  if (available.length > 0) {
    selectedTaskSkills = selectedTaskSkills.filter(s => available.includes(s));
  }
  renderSkillPicker('task');
  updateFixBugPromptPreview();
}

function updateSkillDropdowns() {
  renderSkillPicker('task');
}

document.addEventListener('click', (e) => {
  const taskTrigger = document.getElementById('taskSkillPickerTrigger');
  const taskDropdown = document.getElementById('taskSkillDropdown');
  if (taskDropdown && !taskDropdown.classList.contains('hidden')) {
    if (taskTrigger && !taskTrigger.contains(e.target) && !taskDropdown.contains(e.target)) {
      taskDropdown.classList.add('hidden');
    }
  }
});
