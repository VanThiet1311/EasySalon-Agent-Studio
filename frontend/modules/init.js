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
    updateEffortUI(currentStudioSettings.effort);
    updateEngineUI(currentStudioSettings.engine, nineRouterOnline);
    updateQuickOpencodeDisplay(currentStudioSettings.effort);
    if (typeof fetchOpenCodeModels === 'function') {
      fetchOpenCodeModels(true);
    }
  })
  .catch(err => {
    updateEffortUI(currentStudioSettings.effort);
    updateEngineUI(currentStudioSettings.engine, nineRouterOnline);
    updateQuickOpencodeDisplay(currentStudioSettings.effort);
  });

runAdaptivePollLoop();

window.addEventListener('DOMContentLoaded', () => {

  let initialTab = (typeof window.getTabFromUrl === 'function') ? window.getTabFromUrl() : null;
  const currentPath = (window.location.pathname || '/').replace(/\/+$/, '') || '/';
  if (!initialTab || currentPath === '/' || currentPath === '/index.html') {
    try {
      const savedTab = localStorage.getItem('activeAgentStudioTab');
      if (savedTab && TABS.includes(savedTab)) {
        initialTab = savedTab;
      }
    } catch (e) { }
  }
  if (!initialTab || !TABS.includes(initialTab)) {
    initialTab = 'task';
  }

  const urlSubTab = window.ROUTE_TO_GIT_SUBTAB && window.ROUTE_TO_GIT_SUBTAB[currentPath];
  const targetSubTab = urlSubTab || window.initGitSubTab || 'pull_sync';
  if (initialTab === 'branch') {
    window.initGitSubTab = targetSubTab;
    activeGitSubTab = targetSubTab;
  }

  const urlSettingsSub = window.ROUTE_TO_SETTINGS_SUBTAB && window.ROUTE_TO_SETTINGS_SUBTAB[currentPath];
  let savedSettingsSub = null;
  try {
    savedSettingsSub = localStorage.getItem('activeSettingsSubTab');
  } catch (e) { }
  const targetSettingsSub = window.initSettingsSubTab || urlSettingsSub || (savedSettingsSub && ['engine', 'model', 'effort', 'mcp', 'account', 'api', 'env'].includes(savedSettingsSub) ? savedSettingsSub : null) || activeSettingsSubTab || 'engine';
  if (initialTab === 'settings') {
    window.initSettingsSubTab = targetSettingsSub;
    activeSettingsSubTab = targetSettingsSub;
  }

  let expectedPath = (window.TAB_ROUTES && window.TAB_ROUTES[initialTab]) || ('/' + initialTab);
  if (initialTab === 'branch') {
    const subRoutes = window.GIT_SUBTAB_ROUTES || {
      'pull_sync': '/git-control',
      'branch': '/git-control/checkout-branch',
      'switch': '/git-control/switch-branch',
      'cherry_pick': '/git-control/cherry-pick',
      'merge': '/git-control/merge'
    };
    expectedPath = subRoutes[targetSubTab] || '/git-control';
  } else if (initialTab === 'settings') {
    const subRoutes = window.SETTINGS_SUBTAB_ROUTES || {
      'engine': '/settings/engine',
      'model': '/settings/model',
      'effort': '/settings/effort',
      'mcp': '/settings/mcp',
      'account': '/settings/account',
      'api': '/settings/api',
      'env': '/settings/env'
    };
    expectedPath = subRoutes[targetSettingsSub] || '/settings/engine';
  }
  if (window.location.pathname !== expectedPath) {
    try {
      window.history.replaceState({
        tab: initialTab,
        subTab: initialTab === 'branch' ? targetSubTab : null,
        settingsSubTab: initialTab === 'settings' ? targetSettingsSub : null
      }, '', expectedPath);
    } catch (e) { }
  }
  switchTab(initialTab, false);
  if (initialTab === 'branch') {
    switchGitSubTab(targetSubTab, false);
  } else if (initialTab === 'settings') {
    switchSettingsSidebarTab(targetSettingsSub, false);
  }
  initTheme();
  setupScrollListeners();
  loadCustomSkills();
  renderDiagramColumns();
  fetchDiagramData(false);
  loadGitBranchInfo();
  loadCherryPickInfo();
  loadPullSyncInfo();
  loadMergeInfo();
  setupAutoSaveAndKeybindings();
  restoreDraft();
  updateFixBugPromptPreview();
  setupDevHotReload();
  if (typeof startJiraNotificationWatcher === 'function') {
    startJiraNotificationWatcher();
  }

  setInterval(() => {
    checkSyncPullUpdates(true);
  }, 60000);
});
