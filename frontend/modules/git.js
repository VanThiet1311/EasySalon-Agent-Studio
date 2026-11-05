let gitInfoData = { fe: null, be: null };

function selectBranchChip(role, branchName) {
  const select = document.getElementById(role + 'BranchSelect');
  const filterInput = document.getElementById(role + 'BranchFilter');
  if (filterInput) filterInput.value = branchName;
  filterBranchList(role);
  if (select) select.value = branchName;
}

function populateBaseBranchSelect(feBranches = [], beBranches = []) {
  const sel = document.getElementById('bothBaseBranchSelect');
  if (!sel) return;
  const currentVal = sel.value;

  const allBranches = new Set();
  feBranches.forEach(b => { if (b.name) allBranches.add(b.name); });
  beBranches.forEach(b => { if (b.name) allBranches.add(b.name); });

  const standardBases = ['master', 'staging', 'beta', 'main'];
  const orderedList = [];
  standardBases.forEach(b => {
    if (allBranches.has(b)) {
      orderedList.push(b);
      allBranches.delete(b);
    }
  });

  const otherBranches = Array.from(allBranches).sort();
  orderedList.push(...otherBranches);

  sel.innerHTML = '';
  orderedList.forEach(b => {
    const opt = document.createElement('option');
    opt.value = b;
    const tag = (b === 'master') ? ' (khuyên dùng)' : '';
    opt.textContent = `${b}${tag}`;
    sel.appendChild(opt);
  });

  // Mặc định checkout từ master (nhánh gốc phổ biến nhất)
  if (currentVal && orderedList.includes(currentVal)) {
    sel.value = currentVal;
  } else if (orderedList.includes('master')) {
    sel.value = 'master';
  } else if (orderedList.includes('main')) {
    sel.value = 'main';
  } else if (orderedList.includes('staging')) {
    sel.value = 'staging';
  } else if (orderedList.includes('beta')) {
    sel.value = 'beta';
  }
}

async function doCreateNewBranchBoth() {
  const branchInp = document.getElementById('bothBranchInput');
  const baseSel = document.getElementById('bothBaseBranchSelect');
  const targetSel = document.getElementById('bothTargetWorkspaceSelect');
  const switchCheckbox = document.getElementById('bothSwitchAfterCreateCheckbox');
  const newBranch = (branchInp?.value || '').trim();
  const baseBranch = (baseSel?.value || 'master').trim();
  const targetWorkspace = (targetSel?.value || 'both').trim();
  const switchAfterCreate = switchCheckbox ? switchCheckbox.checked : true;

  if (!newBranch) {
    await antdAlert({
      title: 'Thiếu tên nhánh mới',
      content: 'Vui lòng nhập tên nhánh mới muốn tạo (ví dụ: feat/nvt/EAS-12373/booking-bed-room-management).',
      type: 'error'
    });
    return;
  }

  const targetLabel = targetWorkspace === 'fe'
    ? 'Frontend (easysalon-webapp)'
    : (targetWorkspace === 'be' ? 'Backend (easysalon-api)' : 'cả Frontend & Backend');

  const confirmMsg = switchAfterCreate
    ? `Bạn có chắc muốn tạo nhánh mới ${newBranch} từ nhánh ${baseBranch} và switch sang nhánh này cho ${targetLabel}?`
    : `Bạn có chắc muốn tạo nhánh mới ${newBranch} từ nhánh ${baseBranch} cho ${targetLabel} (không switch nhánh)?`;

  const confirmed = await antdConfirm({
    title: 'Xác nhận tạo nhánh',
    content: confirmMsg
  });
  if (!confirmed) return;

  const btn = document.getElementById('btnSwitchBoth');
  const origText = btn ? btn.innerHTML : '';
  if (btn) {
    btn.disabled = true;
    btn.innerHTML = `
          <svg class="animate-spin -ml-1 mr-2 h-4 w-4 text-white inline-block" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
            <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
            <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
          </svg>
          <span>Đang tạo nhánh...</span>
        `;
  }

  try {
    const res = await fetch('/api/git/checkout', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        target: targetWorkspace,
        branch: newBranch,
        create_new: true,
        base_branch: baseBranch,
        switch_branch: switchAfterCreate
      })
    });
    const data = await res.json();
    showToast(data.message || (data.success ? 'Tạo nhánh thành công.' : 'Lỗi khi tạo nhánh.'));

    await loadGitBranchInfo();
    await fetchDiagramData(true);
    if (activeTab === 'log') loadWorkLogs();

    if (data.success && branchInp) {
      branchInp.value = '';
    }
  } catch (err) {
    showToast('Lỗi kết nối khi tạo nhánh: ' + err.message);
  } finally {
    if (btn) {
      btn.disabled = false;
      btn.innerHTML = origText;
    }
  }
}

function populateRenameBranchSelect(feBranches = [], beBranches = []) {
  const sel = document.getElementById('renameOldBranchSelect');
  const targetSel = document.getElementById('renameTargetWorkspaceSelect');
  if (!sel) return;
  const target = targetSel ? targetSel.value : 'both';
  const currentVal = sel.value;

  const branchSet = new Set();
  if (target === 'fe' || target === 'both') {
    feBranches.forEach(b => { if (b.name) branchSet.add(b.name); });
  }
  if (target === 'be' || target === 'both') {
    beBranches.forEach(b => { if (b.name) branchSet.add(b.name); });
  }

  const sortedBranches = Array.from(branchSet).sort();

  sel.innerHTML = '<option value="">Nhánh hiện tại (HEAD)</option>';
  sortedBranches.forEach(b => {
    const opt = document.createElement('option');
    opt.value = b;
    opt.textContent = b;
    sel.appendChild(opt);
  });

  if (currentVal && branchSet.has(currentVal)) {
    sel.value = currentVal;
  }
}
window.populateRenameBranchSelect = populateRenameBranchSelect;

function onRenameTargetWorkspaceChange() {
  const feBranches = gitInfoData?.fe?.branches || [];
  const beBranches = gitInfoData?.be?.branches || [];
  populateRenameBranchSelect(feBranches, beBranches);
}
window.onRenameTargetWorkspaceChange = onRenameTargetWorkspaceChange;

function onRenameOldBranchChange() {
  const oldBranchSel = document.getElementById('renameOldBranchSelect');
  const newBranchInp = document.getElementById('renameNewBranchInput');
  const targetSel = document.getElementById('renameTargetWorkspaceSelect');
  if (!oldBranchSel || !newBranchInp) return;

  const oldBranch = oldBranchSel.value;
  if (oldBranch) {
    newBranchInp.value = oldBranch;
    newBranchInp.focus();
    newBranchInp.select();
  } else {
    const target = targetSel ? targetSel.value : 'both';
    let current = '';
    if (target === 'fe') current = gitInfoData?.fe?.current_branch || '';
    else if (target === 'be') current = gitInfoData?.be?.current_branch || '';
    else current = gitInfoData?.fe?.current_branch || gitInfoData?.be?.current_branch || '';
    if (current) {
      newBranchInp.value = current;
      newBranchInp.focus();
      newBranchInp.select();
    }
  }
}
window.onRenameOldBranchChange = onRenameOldBranchChange;

async function doRenameBranch() {
  const targetSel = document.getElementById('renameTargetWorkspaceSelect');
  const oldBranchSel = document.getElementById('renameOldBranchSelect');
  const newBranchInp = document.getElementById('renameNewBranchInput');

  const target = targetSel ? targetSel.value : 'both';
  const oldBranch = (oldBranchSel ? oldBranchSel.value : '').trim();
  const newBranch = (newBranchInp ? newBranchInp.value : '').trim();

  if (!newBranch) {
    await antdAlert({
      title: 'Thiếu tên nhánh mới',
      content: 'Vui lòng nhập tên nhánh mới muốn đổi (ví dụ: feat/nvt/EAS-12373/booking-bed-room-management).',
      type: 'error'
    });
    return;
  }

  if (oldBranch && oldBranch === newBranch) {
    await antdAlert({
      title: 'Tên nhánh trùng nhau',
      content: 'Tên nhánh mới phải khác tên nhánh hiện tại.',
      type: 'warning'
    });
    return;
  }

  const targetLabel = target === 'fe'
    ? 'Frontend (easysalon-webapp)'
    : (target === 'be' ? 'Backend (easysalon-api)' : 'cả Frontend & Backend');

  const oldBranchDisplay = oldBranch ? `nhánh <strong>${escapeHtml(oldBranch)}</strong>` : '<strong>nhánh hiện tại (HEAD)</strong>';

  const confirmed = await antdConfirm({
    title: 'Xác nhận đổi tên nhánh',
    content: `Bạn có chắc muốn đổi tên ${oldBranchDisplay} thành <strong class="text-cyan-300 font-mono">${escapeHtml(newBranch)}</strong> cho ${targetLabel}?`
  });
  if (!confirmed) return;

  const btn = document.getElementById('btnRenameBranch');
  const origText = btn ? btn.innerHTML : '';
  if (btn) {
    btn.disabled = true;
    btn.innerHTML = `
      <svg class="animate-spin -ml-1 mr-2 h-4 w-4 text-white inline-block" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
        <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
        <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
      </svg>
      <span>Đang đổi tên...</span>
    `;
  }

  try {
    const res = await fetch('/api/git/rename-branch', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        target,
        old_branch: oldBranch,
        new_branch: newBranch
      })
    });
    const data = await res.json();
    if (data.success) {
      showToast(data.message || 'Đã đổi tên nhánh thành công.', 'success');
      if (newBranchInp) newBranchInp.value = '';
      await loadGitBranchInfo();
    } else {
      await antdAlert({
        title: 'Lỗi đổi tên nhánh',
        content: data.message || 'Không thể đổi tên nhánh.',
        type: 'error'
      });
    }
  } catch (err) {
    showToast('Lỗi kết nối khi đổi tên nhánh: ' + err.message, 'error');
  } finally {
    if (btn) {
      btn.disabled = false;
      btn.innerHTML = origText;
    }
  }
}
window.doRenameBranch = doRenameBranch;

function quickFillRename(role) {
  const currentBranch = gitInfoData && gitInfoData[role] && gitInfoData[role].current_branch;
  const targetSel = document.getElementById('renameTargetWorkspaceSelect');
  const oldBranchSel = document.getElementById('renameOldBranchSelect');
  const newBranchInp = document.getElementById('renameNewBranchInput');

  if (targetSel) {
    targetSel.value = role;
    onRenameTargetWorkspaceChange();
  }
  if (oldBranchSel) {
    oldBranchSel.value = ''; // HEAD / hiện tại
  }
  if (newBranchInp && currentBranch) {
    newBranchInp.value = currentBranch;
    newBranchInp.focus();
    newBranchInp.select();
  }
  newBranchInp?.scrollIntoView({ behavior: 'smooth', block: 'center' });
  showToast(`Đã chọn đổi tên nhánh ${role.toUpperCase()}: ${currentBranch || 'hiện tại'}`, 'info');
}
window.quickFillRename = quickFillRename;

function quickFillRenameSelected(role) {
  const select = document.getElementById(role + 'BranchSelect');
  const inp = document.getElementById(role + 'BranchInput');
  const selectedBranch = (select?.value || inp?.value || '').trim();

  if (!selectedBranch) {
    showToast('Vui lòng chọn nhánh trong danh sách trước.', 'warning');
    return;
  }

  const targetSel = document.getElementById('renameTargetWorkspaceSelect');
  const oldBranchSel = document.getElementById('renameOldBranchSelect');
  const newBranchInp = document.getElementById('renameNewBranchInput');

  if (targetSel) {
    targetSel.value = role;
    onRenameTargetWorkspaceChange();
  }
  if (oldBranchSel) {
    oldBranchSel.value = selectedBranch;
  }
  if (newBranchInp) {
    newBranchInp.value = selectedBranch;
    newBranchInp.focus();
    newBranchInp.select();
  }
  newBranchInp?.scrollIntoView({ behavior: 'smooth', block: 'center' });
  showToast(`Đã chọn đổi tên nhánh ${role.toUpperCase()}: ${selectedBranch}`, 'info');
}
window.quickFillRenameSelected = quickFillRenameSelected;

async function loadGitBranchInfo() {
  try {
    const res = await fetch('/api/git/info');
    const data = await res.json();
    gitInfoData = data;
    renderGitBranchCard('fe', data.fe);
    renderGitBranchCard('be', data.be);
    populateBaseBranchSelect(data.fe?.branches || [], data.be?.branches || []);
    populateRenameBranchSelect(data.fe?.branches || [], data.be?.branches || []);
  } catch (err) {
    showGitAlert('Lỗi tải thông tin Git: ' + err.message, false);
  }
}

function renderGitBranchCard(role, info) {
  if (!info) return;
  const isFe = role === 'fe';
  const branchBadge = document.getElementById(isFe ? 'feCurrentBranch' : 'beCurrentBranch');
  const commitInfo = document.getElementById(isFe ? 'feCommitInfo' : 'beCommitInfo');
  const statusInfo = document.getElementById(isFe ? 'feStatusInfo' : 'beStatusInfo');
  const workingStatus = document.getElementById(isFe ? 'feWorkingStatus' : 'beWorkingStatus');
  const syncBadge = document.getElementById(isFe ? 'feSyncBadge' : 'beSyncBadge');
  const btnPull = document.getElementById(isFe ? 'btnPullFe' : 'btnPullBe');
  const pullBtnText = document.getElementById(isFe ? 'fePullBtnText' : 'bePullBtnText');

  if (branchBadge) {
    branchBadge.textContent = info.current_branch || 'unknown';
  }
  if (commitInfo) {
    if (info.commit_hash) {
      commitInfo.textContent = `${info.commit_hash} - ${info.commit_message} (${formatRelativeDate(info.commit_date)})`;
      commitInfo.title = `${info.commit_hash} - ${info.commit_message}`;
    } else {
      commitInfo.textContent = 'Không có thông tin commit';
    }
  }
  if (statusInfo) {
    if (info.dirty_count > 0) {
      statusInfo.innerHTML = `<span class="text-amber-400 font-medium">Có ${info.dirty_count} thay đổi chưa commit</span>`;
      if (workingStatus) workingStatus.innerHTML = `<span class="text-amber-400">Có thay đổi</span>`;
    } else {
      statusInfo.innerHTML = `<span class="text-emerald-400 font-medium">Working tree sạch (clean)</span>`;
      if (workingStatus) workingStatus.innerHTML = `<span class="text-emerald-400">Sạch</span>`;
    }
  }

  const needsPull = Boolean(info.needs_pull || (info.behind_count && info.behind_count > 0));
  if (syncBadge) {
    if (needsPull) {
      syncBadge.innerHTML = `<span class="text-amber-400 font-semibold bg-amber-950/70 px-2 py-0.5 rounded border border-amber-800">Chậm hơn remote ${info.behind_count} commit (Cần Pull)</span>`;
    } else if (info.ahead_count && info.ahead_count > 0) {
      syncBadge.innerHTML = `<span class="text-cyan-400 font-mono bg-cyan-950/70 px-2 py-0.5 rounded border border-cyan-800">Nhanh hơn remote ${info.ahead_count} commit</span>`;
    } else if (info.upstream) {
      syncBadge.innerHTML = `<span class="text-emerald-400 font-mono bg-emerald-950/70 px-2 py-0.5 rounded border border-emerald-800">Đã đồng bộ mới nhất</span>`;
    } else {
      syncBadge.innerHTML = `<span class="text-slate-400 font-mono text-[11px]">Chưa gắn remote upstream</span>`;
    }
  }

  if (btnPull) {
    if (needsPull) {
      btnPull.classList.remove('hidden');
      btnPull.style.display = 'inline-flex';
      btnPull.className = 'ant-btn text-xs h-[28px] px-3 inline-flex items-center gap-1.5 bg-amber-600 hover:bg-amber-500 text-white font-semibold border-amber-500 shadow-sm';
      if (pullBtnText) {
        pullBtnText.textContent = `Pull ngay (${info.behind_count} commit)`;
      }
    } else {
      btnPull.classList.add('hidden');
      btnPull.style.display = 'none';
    }
  }

  const prevBtn = document.getElementById(isFe ? 'btnPrevFe' : 'btnPrevBe');
  if (prevBtn) {
    if (info.prev_branch && info.prev_branch !== info.current_branch) {
      prevBtn.classList.remove('hidden');
      prevBtn.classList.add('inline-flex');
      prevBtn.innerHTML = `
            <svg class="w-3 h-3 fill-none stroke-current" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M3 10h10a8 8 0 018 8v2M3 10l6 6m-6-6l6-6"/></svg>
            <span>Quay về: <b id="${isFe ? 'fePrevBranchLabel' : 'bePrevBranchLabel'}" class="font-mono ${isFe ? 'text-cyan-200' : 'text-emerald-200'}">${escapeHtml(info.prev_branch)}</b></span>
          `;
      prevBtn.title = `Quay về nhánh trước đó: "${info.prev_branch}" (git checkout -)`;
    } else {
      prevBtn.classList.add('hidden');
      prevBtn.classList.remove('inline-flex');
    }
  }

  // Hiển thị khu vực Stash và nút Lấy code từ stash nếu nhánh hiện tại có stash
  const stashSection = document.getElementById(isFe ? 'feStashSection' : 'beStashSection');
  const stashBadge = document.getElementById(isFe ? 'feStashBadge' : 'beStashBadge');
  const popStashBtnText = document.getElementById(isFe ? 'fePopStashBtnText' : 'bePopStashBtnText');

  const branchStashes = info.branch_stashes || [];
  const hasBranchStash = Boolean(info.has_branch_stash && branchStashes.length > 0);

  if (stashSection) {
    if (hasBranchStash) {
      const topStash = branchStashes[0];
      const count = branchStashes.length;
      stashSection.classList.remove('hidden');
      stashSection.style.display = 'flex';
      stashSection.dataset.stashRef = topStash.index;

      if (stashBadge) {
        const timeAgo = topStash.date ? ` (${formatRelativeDate(topStash.date)})` : '';
        const desc = topStash.message || topStash.raw_subject || 'Bản cất code';
        if (count > 1) {
          stashBadge.textContent = `${topStash.index}: ${desc}${timeAgo} (+${count - 1} bản khác)`;
          stashBadge.title = `Nhánh này có ${count} bản stash:\n` + branchStashes.map(s => `${s.index}: ${s.message || s.raw_subject} (${s.date})`).join('\n');
        } else {
          stashBadge.textContent = `${topStash.index}: ${desc}${timeAgo}`;
          stashBadge.title = `${topStash.index}: ${desc} (${topStash.date})`;
        }
      }

      if (popStashBtnText) {
        popStashBtnText.textContent = count > 1 ? `Lấy code từ stash (${topStash.index})` : 'Lấy code từ stash';
      }
    } else {
      stashSection.classList.add('hidden');
      stashSection.style.display = 'none';
      if (stashBadge) {
        stashBadge.textContent = '';
        stashBadge.title = '';
      }
    }
  }

  filterBranchList(role);
}

function filterBranchList(role) {
  const isFe = role === 'fe';
  const select = document.getElementById(isFe ? 'feBranchSelect' : 'beBranchSelect');
  const input = document.getElementById(isFe ? 'feBranchInput' : 'beBranchInput');
  if (!select || !gitInfoData || !gitInfoData[role]) return;

  const filterText = (input?.value || '').toLowerCase().trim();
  const branches = gitInfoData[role].branches || [];
  const currentBranch = gitInfoData[role].current_branch;
  const stashList = gitInfoData[role].stash_list || [];
  const branchesWithStash = new Set(stashList.map(s => s.branch).filter(Boolean));

  select.innerHTML = '';
  const filtered = branches.filter(b => b.name.toLowerCase().includes(filterText));

  if (filtered.length === 0) {
    const opt = document.createElement('option');
    opt.disabled = true;
    opt.textContent = filterText ? `Nhánh mới: "${filterText}" (tích chọn tạo mới nếu cần)` : 'Không có nhánh nào';
    select.appendChild(opt);
    return;
  }

  filtered.forEach(b => {
    const opt = document.createElement('option');
    opt.value = b.name;
    const prefix = b.name === currentBranch ? '[Hiện tại] ' : '';
    const dateStr = b.date ? ` [${formatRelativeDate(b.date)}]` : '';
    const stashStr = branchesWithStash.has(b.name) ? ' [Có stash]' : '';
    opt.textContent = `${prefix}${b.name}${dateStr}${stashStr}`;
    if (b.name === currentBranch) {
      opt.className = 'font-bold text-cyan-300 bg-cyan-950/40';
    }
    select.appendChild(opt);
  });
}

function selectBranchChip(role, branchName) {
  if (role === 'fe' || role === 'both') {
    const inp = document.getElementById('feBranchInput');
    if (inp) inp.value = branchName;
    filterBranchList('fe');
  }
  if (role === 'be' || role === 'both') {
    const inp = document.getElementById('beBranchInput');
    if (inp) inp.value = branchName;
    filterBranchList('be');
  }
  const bothInp = document.getElementById('bothBranchInput');
  if (bothInp) bothInp.value = branchName;
}

function handleBranchInputKeyDown(e, role) {
  const isFe = role === 'fe';
  const select = document.getElementById(isFe ? 'feBranchSelect' : 'beBranchSelect');
  if (!select) return;

  if (e.key === 'ArrowDown' || e.key === 'ArrowUp') {
    e.preventDefault();
    const validOptions = Array.from(select.options).filter(opt => !opt.disabled);
    if (validOptions.length === 0) return;

    select.focus();
    if (select.selectedIndex < 0 || select.options[select.selectedIndex]?.disabled) {
      select.value = validOptions[0].value;
    } else {
      let curIdx = validOptions.findIndex(o => o.value === select.value);
      if (e.key === 'ArrowDown') {
        curIdx = Math.min(validOptions.length - 1, curIdx + 1);
      } else {
        curIdx = Math.max(0, curIdx - 1);
      }
      select.value = validOptions[curIdx].value;
    }
    onSelectBranchOption(role);
  } else if (e.key === 'Enter') {
    e.preventDefault();
    doCheckout(role);
  }
}

function handleBranchSelectKeyDown(e, role) {
  if (e.key === 'Enter') {
    e.preventDefault();
    doCheckout(role);
  } else if (e.key === 'Escape') {
    const isFe = role === 'fe';
    const input = document.getElementById(isFe ? 'feBranchInput' : 'beBranchInput');
    if (input) input.focus();
  }
}

function onSelectBranchOption(role) {
  const isFe = role === 'fe';
  const select = document.getElementById(isFe ? 'feBranchSelect' : 'beBranchSelect');
  const input = document.getElementById(isFe ? 'feBranchInput' : 'beBranchInput');
  if (select && input && select.value) {
    input.value = select.value;
  }
}

async function doCheckout(target) {
  let selectedBranch = '';
  let isCreateNew = false;
  let btn = null;

  if (target === 'both') {
    const inp = document.getElementById('bothBranchInput');
    const chk = document.getElementById('bothCreateNewBranch');
    selectedBranch = (inp?.value || '').trim();
    isCreateNew = Boolean(chk?.checked);
    btn = document.getElementById('btnSwitchBoth');
  } else if (target === 'fe') {
    const inp = document.getElementById('feBranchInput');
    const sel = document.getElementById('feBranchSelect');
    selectedBranch = (inp?.value || sel?.value || '').trim();
    isCreateNew = false;
    btn = document.getElementById('btnSwitchFe');
  } else if (target === 'be') {
    const inp = document.getElementById('beBranchInput');
    const sel = document.getElementById('beBranchSelect');
    selectedBranch = (inp?.value || sel?.value || '').trim();
    isCreateNew = false;
    btn = document.getElementById('btnSwitchBe');
  }

  if (!selectedBranch) {
    await antdAlert({
      title: 'Thiếu thông tin',
      content: 'Vui lòng nhập tên nhánh (ví dụ: feat/abc) hoặc chọn trong danh sách bên dưới.',
      type: 'error'
    });
    return;
  }

  const confirmMsg = isCreateNew
    ? `Bạn có chắc muốn tạo và chuyển sang nhánh ${selectedBranch}`
    : `Bạn có chắc muốn thực hiện chuyển sang nhánh ${selectedBranch}`;

  const confirmed = await antdConfirm({
    title: isCreateNew ? 'Xác nhận tạo nhánh' : 'Xác nhận chuyển nhánh',
    content: confirmMsg
  });
  if (!confirmed) return;

  const origText = btn ? btn.innerHTML : '';
  if (btn) {
    btn.disabled = true;
    btn.innerHTML = `
          <svg class="animate-spin -ml-1 mr-2 h-4 w-4 text-white inline-block" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
            <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
            <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
          </svg>
          <span>Đang checkout...</span>
        `;
  }

  try {
    const res = await fetch('/api/git/checkout', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        target: target,
        branch: selectedBranch,
        create_new: isCreateNew
      })
    });
    const data = await res.json();
    showToast(data.message || (data.success ? 'Chuyển nhánh thành công.' : 'Lỗi chuyển nhánh.'));

    await loadGitBranchInfo();

    const roleInfo = gitInfoData?.[target];
    if (roleInfo && roleInfo.has_branch_stash && roleInfo.branch_stashes?.length > 0) {
      const topStash = roleInfo.branch_stashes[0];
      showToast(`Nhánh "${selectedBranch}" có code đã cất trong ${topStash.index}. Bấm "Lấy code từ stash" để khôi phục.`);
    }

    await fetchDiagramData(true);

    if (activeTab === 'log') loadWorkLogs();
  } catch (err) {
    showToast('Lỗi kết nối khi chuyển nhánh: ' + err.message);
  } finally {
    if (btn) {
      btn.disabled = false;
      btn.innerHTML = origText;
    }
  }
}

async function doCheckoutPrevious(target) {
  let prevBranch = '';
  let label = '';
  let btn = null;

  if (target === 'fe') {
    prevBranch = gitInfoData?.fe?.prev_branch || '';
    label = `Frontend (nhánh "${prevBranch || 'trước đó'}")`;
    btn = document.getElementById('btnPrevFe');
  } else if (target === 'be') {
    prevBranch = gitInfoData?.be?.prev_branch || '';
    label = `Backend (nhánh "${prevBranch || 'trước đó'}")`;
    btn = document.getElementById('btnPrevBe');
  } else {
    return;
  }

  if (target === 'fe' && !prevBranch) {
    await antdAlert({ title: 'Không thể quay lại', content: 'Frontend chưa có nhánh trước đó trong lịch sử reflog.', type: 'error' });
    return;
  }
  if (target === 'be' && !prevBranch) {
    await antdAlert({ title: 'Không thể quay lại', content: 'Backend chưa có nhánh trước đó trong lịch sử reflog.', type: 'error' });
    return;
  }

  const confirmed = await antdConfirm({
    title: 'Quay về nhánh trước',
    content: `Bạn có chắc muốn thực hiện chuyển sang nhánh ${prevBranch || 'trước đó'}`
  });
  if (!confirmed) return;

  const origText = btn ? btn.innerHTML : '';
  if (btn) {
    btn.disabled = true;
    btn.innerHTML = `
          <svg class="animate-spin h-3.5 w-3.5 text-white inline-block mr-1" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
            <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
            <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
          </svg>
          <span>Đang quay lại...</span>
        `;
  }

  try {
    const res = await fetch('/api/git/checkout', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        target: target,
        branch: prevBranch || '-',
        create_new: false
      })
    });
    const data = await res.json();
    showToast(data.message || (data.success ? 'Đã quay về nhánh trước đó.' : 'Lỗi khi quay lại nhánh trước.'));

    await loadGitBranchInfo();

    const roleInfo = gitInfoData?.[target];
    if (roleInfo && roleInfo.has_branch_stash && roleInfo.branch_stashes?.length > 0) {
      const topStash = roleInfo.branch_stashes[0];
      showToast(`Nhánh "${roleInfo.current_branch || prevBranch}" có code đã cất trong ${topStash.index}. Bấm "Lấy code từ stash" để khôi phục.`);
    }

    await fetchDiagramData(true);
    if (activeTab === 'log') loadWorkLogs();
  } catch (err) {
    showToast('Lỗi kết nối khi quay về nhánh trước đó: ' + err.message);
    if (btn && origText) {
      btn.innerHTML = origText;
    }
  } finally {
    if (btn) {
      btn.disabled = false;
    }
  }
}

async function doPopStash(role) {
  const isFe = role === 'fe';
  const repoName = isFe ? 'Frontend' : 'Backend';
  const roleInfo = gitInfoData?.[role];
  const branchStashes = roleInfo?.branch_stashes || [];
  const stash = branchStashes[0] || roleInfo?.stash_list?.[0];
  const stashRef = stash?.index || 'stash@{0}';
  const stashMsg = stash?.message || stash?.raw_subject || '';
  const currentBranch = roleInfo?.current_branch || 'nhánh hiện tại';

  const confirmed = await antdConfirm({
    title: 'Xác nhận lấy code từ Git Stash',
    content: `Bạn có muốn lấy và áp dụng mã nguồn từ ${stashRef}${stashMsg ? ` ("${stashMsg}")` : ''} vào nhánh "${currentBranch}" (${repoName}) không?`
  });
  if (!confirmed) return;

  const btn = document.getElementById(isFe ? 'btnPopStashFe' : 'btnPopStashBe');
  const origHtml = btn ? btn.innerHTML : '';
  if (btn) {
    btn.disabled = true;
    btn.innerHTML = `
      <svg class="animate-spin -ml-1 mr-1.5 h-3.5 w-3.5 text-white inline-block" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
        <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
        <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
      </svg>
      <span>Đang lấy code...</span>
    `;
  }

  try {
    const res = await fetch('/api/git/stash/pop', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        target: role,
        stash_index: stashRef
      })
    });
    const data = await res.json();
    if (data.success) {
      showToast(data.message || `Đã lấy code từ ${stashRef} thành công.`);
    } else {
      if (data.conflict) {
        await antdAlert({
          title: 'Xảy ra xung đột khi lấy code từ Stash',
          content: `${data.message}\n\nCác file xung đột đã được giữ lại trên working tree. Bạn có thể mở tab Xung đột Git để xử lý.`,
          type: 'warning'
        });
      } else {
        await antdAlert({
          title: 'Không thể lấy code từ Stash',
          content: data.message || 'Lỗi không xác định khi thực hiện git stash pop.',
          type: 'error'
        });
      }
    }
    await loadGitBranchInfo();
    if (typeof activeTab !== 'undefined' && activeTab === 'log' && typeof loadWorkLogs === 'function') {
      loadWorkLogs();
    }
  } catch (err) {
    showToast('Lỗi kết nối khi lấy code từ stash: ' + err.message);
  } finally {
    if (btn) {
      btn.disabled = false;
      btn.innerHTML = origHtml;
    }
  }
}

async function doPullBranch(target) {
  let label = 'cả hai phía (Frontend & Backend)';
  let branchName = '';
  let btn = null;

  if (target === 'fe') {
    branchName = gitInfoData?.fe?.current_branch || 'hiện tại';
    label = `Frontend (nhánh "${branchName}")`;
    btn = document.getElementById('btnPullFe');
  } else if (target === 'be') {
    branchName = gitInfoData?.be?.current_branch || 'hiện tại';
    label = `Backend (nhánh "${branchName}")`;
    btn = document.getElementById('btnPullBe');
  } else {
    btn = document.getElementById('btnPullBoth');
  }

  const confirmed = await antdConfirm({
    title: 'Xác nhận Git Pull',
    content: `Bạn có chắc muốn thực hiện 'git pull' để kéo mã nguồn mới nhất từ remote cho ${label}?`
  });
  if (!confirmed) return;

  const origText = btn ? btn.innerHTML : '';
  if (btn) {
    btn.disabled = true;
    btn.innerHTML = `
          <svg class="animate-spin h-3.5 w-3.5 text-white inline-block mr-1" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
            <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
            <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
          </svg>
          <span>Đang pull...</span>
        `;
  }

  try {
    const res = await fetch('/api/git/pull', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ target })
    });
    const data = await res.json();
    showToast(data.message || (data.success ? 'Đã pull cập nhật thành công.' : 'Lỗi git pull.'));
    await loadGitBranchInfo();
    await fetchDiagramData(true);
    if (activeTab === 'log') loadWorkLogs();
  } catch (err) {
    showToast('Lỗi kết nối khi git pull: ' + err.message);
  } finally {
    if (btn) {
      btn.disabled = false;
      btn.innerHTML = origText;
    }
  }
}

function showGitAlert(message, isSuccess) {
  if (message) showToast(message);
}

let cherryPickState = {
  fe: { in_progress: false, current_branch: '', source_branch: 'staging', branches: [], commits: [] },
  be: { in_progress: false, current_branch: '', source_branch: 'staging', branches: [], commits: [] }
};

function toggleCherryBranchDropdown(role) {
  const menu = document.getElementById(role === 'fe' ? 'feCherryBranchDropdownMenu' : 'beCherryBranchDropdownMenu');
  const otherMenu = document.getElementById(role === 'fe' ? 'beCherryBranchDropdownMenu' : 'feCherryBranchDropdownMenu');
  const sourceFe = document.getElementById('feCherrySourceBranchDropdownMenu');
  const sourceBe = document.getElementById('beCherrySourceBranchDropdownMenu');
  if (otherMenu) otherMenu.classList.add('hidden');
  if (sourceFe) sourceFe.classList.add('hidden');
  if (sourceBe) sourceBe.classList.add('hidden');
  if (!menu) return;

  const isHidden = menu.classList.contains('hidden');
  if (isHidden) {
    menu.classList.remove('hidden');
    const searchInput = document.getElementById(role === 'fe' ? 'feCherryBranchSearchInput' : 'beCherryBranchSearchInput');
    if (searchInput) {
      searchInput.value = '';
      setTimeout(() => searchInput.focus(), 60);
    }
    filterCherryBranches(role);
  } else {
    menu.classList.add('hidden');
  }
}
window.toggleCherryBranchDropdown = toggleCherryBranchDropdown;

function filterCherryBranches(role) {
  const listEl = document.getElementById(role === 'fe' ? 'feCherryBranchOptionsList' : 'beCherryBranchOptionsList');
  const searchInput = document.getElementById(role === 'fe' ? 'feCherryBranchSearchInput' : 'beCherryBranchSearchInput');
  if (!listEl) return;

  const keyword = (searchInput?.value || '').toLowerCase().trim();
  const branches = cherryPickState[role]?.branches || [];
  const currentBranch = cherryPickState[role]?.current_branch || '';

  const filtered = branches.filter(b => b.name.toLowerCase().includes(keyword));

  if (filtered.length === 0) {
    listEl.innerHTML = `<div class="p-3 text-center text-slate-400 text-xs">Không tìm thấy nhánh phù hợp</div>`;
    return;
  }

  listEl.innerHTML = filtered.map(b => {
    const isCurrent = b.name === currentBranch;
    const activeClass = isCurrent ? 'active-branch' : '';
    const currentBadge = isCurrent
      ? `<span class="text-[10px] px-1.5 py-0.5 rounded font-semibold ${role === 'fe' ? 'bg-cyan-950 text-cyan-300 border border-cyan-800' : 'bg-emerald-950 text-emerald-300 border border-emerald-800'}">Hiện tại</span>`
      : '';

    return `
          <div onclick="selectCherryBranch('${role}', '${escapeHtml(b.name).replace(/'/g, "\\'")}')"
            class="cherry-branch-opt ${activeClass} px-2.5 py-1.5 rounded transition cursor-pointer flex items-center justify-between gap-2 text-xs">
            <span class="truncate font-mono">${escapeHtml(b.name)}</span>
            ${currentBadge}
          </div>
        `;
  }).join('');
}
window.filterCherryBranches = filterCherryBranches;

function selectCherryBranch(role, branchName) {
  const menu = document.getElementById(role === 'fe' ? 'feCherryBranchDropdownMenu' : 'beCherryBranchDropdownMenu');
  if (menu) menu.classList.add('hidden');
  onCherryBranchSwitch(role, branchName);
}
window.selectCherryBranch = selectCherryBranch;

function selectFirstFilteredCherryBranch(role) {
  const searchInput = document.getElementById(role === 'fe' ? 'feCherryBranchSearchInput' : 'beCherryBranchSearchInput');
  const keyword = (searchInput?.value || '').toLowerCase().trim();
  const branches = cherryPickState[role]?.branches || [];
  const match = branches.find(b => b.name.toLowerCase().includes(keyword));
  if (match) {
    selectCherryBranch(role, match.name);
  }
}
window.selectFirstFilteredCherryBranch = selectFirstFilteredCherryBranch;

function toggleCherrySourceBranchDropdown(role) {
  const menu = document.getElementById(role === 'fe' ? 'feCherrySourceBranchDropdownMenu' : 'beCherrySourceBranchDropdownMenu');
  const otherMenu = document.getElementById(role === 'fe' ? 'beCherrySourceBranchDropdownMenu' : 'feCherrySourceBranchDropdownMenu');
  const topFe = document.getElementById('feCherryBranchDropdownMenu');
  const topBe = document.getElementById('beCherryBranchDropdownMenu');
  if (otherMenu) otherMenu.classList.add('hidden');
  if (topFe) topFe.classList.add('hidden');
  if (topBe) topBe.classList.add('hidden');
  if (!menu) return;

  const isHidden = menu.classList.contains('hidden');
  if (isHidden) {
    menu.classList.remove('hidden');
    const searchInput = document.getElementById(role === 'fe' ? 'feCherrySourceBranchSearchInput' : 'beCherrySourceBranchSearchInput');
    if (searchInput) {
      searchInput.value = '';
      setTimeout(() => searchInput.focus(), 60);
    }
    filterCherrySourceBranches(role);
  } else {
    menu.classList.add('hidden');
  }
}
window.toggleCherrySourceBranchDropdown = toggleCherrySourceBranchDropdown;

function filterCherrySourceBranches(role) {
  const listEl = document.getElementById(role === 'fe' ? 'feCherrySourceBranchOptionsList' : 'beCherrySourceBranchOptionsList');
  const searchInput = document.getElementById(role === 'fe' ? 'feCherrySourceBranchSearchInput' : 'beCherrySourceBranchSearchInput');
  if (!listEl) return;

  const keyword = (searchInput?.value || '').toLowerCase().trim();
  const branches = cherryPickState[role]?.branches || [];
  const currentBranch = cherryPickState[role]?.current_branch || '';
  const selectedSource = cherryPickState[role]?.source_branch || document.getElementById(role === 'fe' ? 'feCherrySourceBranchSelect' : 'beCherrySourceBranchSelect')?.value || 'staging';

  const filtered = branches.filter(b => b.name.toLowerCase().includes(keyword));

  if (filtered.length === 0) {
    listEl.innerHTML = `<div class="p-3 text-center text-slate-400 text-xs">Không tìm thấy nhánh phù hợp</div>`;
    return;
  }

  listEl.innerHTML = filtered.map(b => {
    const isSelected = b.name === selectedSource;
    const isCurrent = b.name === currentBranch;
    const activeClass = isSelected ? 'active-branch' : '';
    const currentBadge = isCurrent
      ? `<span class="text-[10px] px-1.5 py-0.5 rounded font-semibold ${role === 'fe' ? 'bg-cyan-950 text-cyan-300 border border-cyan-800' : 'bg-emerald-950 text-emerald-300 border border-emerald-800'}">Đang đứng</span>`
      : (isSelected ? `<span class="text-[10px] px-1.5 py-0.5 rounded font-semibold ${role === 'fe' ? 'bg-sky-950 text-sky-300 border border-sky-800' : 'bg-emerald-950 text-emerald-300 border border-emerald-800'}">Đang chọn</span>` : '');

    return `
          <div onclick="selectCherrySourceBranch('${role}', '${escapeHtml(b.name).replace(/'/g, "\\'")}')"
            class="cherry-branch-opt ${activeClass} px-2.5 py-1.5 rounded transition cursor-pointer flex items-center justify-between gap-2 text-xs">
            <span class="truncate font-mono">${escapeHtml(b.name)}</span>
            ${currentBadge}
          </div>
        `;
  }).join('');
}
window.filterCherrySourceBranches = filterCherrySourceBranches;

function selectCherrySourceBranch(role, branchName) {
  const menu = document.getElementById(role === 'fe' ? 'feCherrySourceBranchDropdownMenu' : 'beCherrySourceBranchDropdownMenu');
  if (menu) menu.classList.add('hidden');

  cherryPickState[role].source_branch = branchName;

  const select = document.getElementById(role === 'fe' ? 'feCherrySourceBranchSelect' : 'beCherrySourceBranchSelect');
  if (select) select.value = branchName;

  const textEl = document.getElementById(role === 'fe' ? 'feCherrySelectedSourceBranchText' : 'beCherrySelectedSourceBranchText');
  if (textEl) {
    textEl.textContent = branchName;
    textEl.title = `Nhánh nguồn: ${branchName}`;
  }

  loadBranchCommits(role);
}
window.selectCherrySourceBranch = selectCherrySourceBranch;

function selectFirstFilteredCherrySourceBranch(role) {
  const searchInput = document.getElementById(role === 'fe' ? 'feCherrySourceBranchSearchInput' : 'beCherrySourceBranchSearchInput');
  const keyword = (searchInput?.value || '').toLowerCase().trim();
  const branches = cherryPickState[role]?.branches || [];
  const match = branches.find(b => b.name.toLowerCase().includes(keyword));
  if (match) {
    selectCherrySourceBranch(role, match.name);
  }
}
window.selectFirstFilteredCherrySourceBranch = selectFirstFilteredCherrySourceBranch;

const NOTIF_STORAGE_KEY = 'easysalon_notifications_history_v2';
let _savedNotifications = [];
try {
  _savedNotifications = JSON.parse(localStorage.getItem(NOTIF_STORAGE_KEY) || '[]');
  if (!Array.isArray(_savedNotifications)) _savedNotifications = [];
} catch (e) {
  _savedNotifications = [];
}

let _notifActiveTag = 'all';
let _readNotifIds = new Set(JSON.parse(localStorage.getItem('easysalon_read_notifs') || '[]'));
let _isNotifBellRingingDismissed = false;

function savePersistentNotifications() {
  try {
    if (_savedNotifications.length > 50) {
      _savedNotifications = _savedNotifications.slice(0, 50);
    }
    localStorage.setItem(NOTIF_STORAGE_KEY, JSON.stringify(_savedNotifications));
  } catch (e) {
    console.warn('Lỗi khi lưu thông báo:', e);
  }
}

function addOrUpdateNotification(notif) {
  if (!notif || !notif.id) return;
  const idx = _savedNotifications.findIndex(n => n.id === notif.id);
  if (idx >= 0) {
    _savedNotifications[idx] = { ..._savedNotifications[idx], ...notif };
  } else {
    _savedNotifications.unshift({
      timestamp: Date.now(),
      date: notif.date || new Date().toLocaleTimeString('vi-VN', { hour: '2-digit', minute: '2-digit' }),
      ...notif
    });

    _isNotifBellRingingDismissed = false;
  }
  savePersistentNotifications();
}

function getAllCombinedNotifications() {
  // Chỉ tạo thông báo cho Tác vụ Agent khi tác vụ ĐÃ HOÀN TẤT (completed / done)
  // Không thông báo các trạng thái trung gian: "đang thực thi", "đã dừng / tạm dừng" hay "hàng đợi"
  (parallelTasks || []).forEach(t => {
    const isDone = (t.status === 'completed' || t.status === 'done');
    if (isDone) {
      const statusTitle = 'Tác vụ đã hoàn tất';
      const statusDesc = `[${t.name}] đã thực thi xong thành công trên AI Terminal.`;
      const notifId = `agent_${t.id}_completed`;
      const exists = _savedNotifications.some(n => n.id === notifId);
      if (!exists) {
        addOrUpdateNotification({
          id: notifId,
          tag: 'agent',
          tagLabel: 'Tác vụ Agent',
          title: statusTitle,
          desc: statusDesc,
          taskId: t.id,
          taskStatus: 'completed',
          date: new Date().toLocaleTimeString('vi-VN', { hour: '2-digit', minute: '2-digit' })
        });
      }
    }
  });

  // Tự động dọn dẹp các thông báo Agent trung gian cũ (đang thực thi, đã dừng, hàng đợi) khỏi danh sách đã lưu
  const beforeLen = _savedNotifications.length;
  _savedNotifications = _savedNotifications.filter(n => {
    if (n.tag === 'agent') {
      const st = (n.taskStatus || n.status || '').toLowerCase();
      const titleLower = (n.title || '').toLowerCase();
      if (st === 'running' || st === 'stopped' || st === 'queued' ||
          titleLower.includes('đang thực thi') || titleLower.includes('đã dừng') || titleLower.includes('hàng đợi')) {
        return false;
      }
    }
    return true;
  });
  if (_savedNotifications.length !== beforeLen) {
    savePersistentNotifications();
  }

  return _savedNotifications;
}

function updateNotifBadgeUI() {
  const all = getAllCombinedNotifications();
  const unreadCount = all.filter(n => !_readNotifIds.has(n.id)).length;

  const badge = document.getElementById('notifBadge');
  const dropdownBadge = document.getElementById('notifDropdownBadge');
  const bellIcon = document.getElementById('notifBellIcon');

  if (badge) {
    if (unreadCount > 0) {
      badge.classList.remove('hidden');
      badge.textContent = unreadCount > 99 ? '99+' : unreadCount;
    } else {
      badge.classList.add('hidden');
      badge.textContent = '0';
    }
  }

  if (bellIcon) {
    if (unreadCount > 0 && !_isNotifBellRingingDismissed) {
      bellIcon.classList.add('animate-bell-ring');
    } else {
      bellIcon.classList.remove('animate-bell-ring');
    }
  }

  if (dropdownBadge) {
    dropdownBadge.classList.remove('hidden');
    if (unreadCount > 0) {
      dropdownBadge.textContent = `${unreadCount} chưa đọc`;
      dropdownBadge.className = 'text-xs text-blue-600 font-semibold';
    } else {
      dropdownBadge.textContent = '0 chưa đọc';
      dropdownBadge.className = 'text-xs text-slate-400 font-normal';
    }
  }

  const btnMarkAll = document.getElementById('btnMarkAllNotifsAsRead');
  if (btnMarkAll) {
    if (unreadCount > 0) {
      btnMarkAll.className = 'text-[11px] font-semibold text-[#199cff] hover:text-blue-700 transition cursor-pointer';
      btnMarkAll.style.color = '#199cff';
      btnMarkAll.disabled = false;
      btnMarkAll.title = 'Đánh dấu tất cả thông báo là đã đọc';
    } else {
      btnMarkAll.className = 'text-[11px] font-semibold text-slate-400 cursor-default select-none transition';
      btnMarkAll.style.color = '#94a3b8';
      btnMarkAll.disabled = true;
      btnMarkAll.title = 'Đã đọc tất cả thông báo';
    }
  }
}
window.updateNotifBadgeUI = updateNotifBadgeUI;

function renderNotifFilterTabs() {
  const container = document.getElementById('notifFilterTabs');
  if (!container) return;

  const all = getAllCombinedNotifications();
  const allUnread = all.filter(n => !_readNotifIds.has(n.id)).length;

  const gitItems = all.filter(n => n.tag === 'git');
  const gitUnread = gitItems.filter(n => !_readNotifIds.has(n.id)).length;

  const agentItems = all.filter(n => n.tag === 'agent');
  const agentUnread = agentItems.filter(n => !_readNotifIds.has(n.id)).length;

  const jiraItems = all.filter(n => n.tag === 'jira');
  const jiraUnread = jiraItems.filter(n => !_readNotifIds.has(n.id)).length;

  const tags = [
    { id: 'all', label: 'Tất cả', count: all.length, unread: allUnread },
    { id: 'git', label: 'Git', count: gitItems.length, unread: gitUnread },
    { id: 'agent', label: 'Tác vụ Agent', count: agentItems.length, unread: agentUnread },
    { id: 'jira', label: 'Jira', count: jiraItems.length, unread: jiraUnread }
  ];

  container.innerHTML = tags.map(t => {
    const isActive = _notifActiveTag === t.id;
    return `
      <button type="button" onclick="setNotifTagFilter('${t.id}', event)"
        class="px-3 py-1 rounded text-[11px] font-medium transition flex items-center gap-1.5 shrink-0 select-none cursor-pointer ${isActive
        ? 'bg-[#199cff] text-white font-bold shadow-sm'
        : 'text-slate-700 hover:text-black hover:bg-slate-100'
      }">
        <span>${escapeHtml(t.label)}</span>
        <span class="text-[10px] font-mono opacity-80">(${t.count})</span>
        ${t.unread > 0 ? `<span class="w-1.5 h-1.5 rounded-full ${isActive ? 'bg-white' : 'bg-blue-600'} animate-pulse"></span>` : ''}
      </button>
    `;
  }).join('');
}
window.renderNotifFilterTabs = renderNotifFilterTabs;

function setNotifTagFilter(tag, event) {
  if (event) {
    event.stopPropagation();
    event.preventDefault();
  }
  _notifActiveTag = tag;
  renderNotificationList();
}
window.setNotifTagFilter = setNotifTagFilter;

function renderNotificationList() {
  renderNotifFilterTabs();
  updateNotifBadgeUI();

  const listEl = document.getElementById('notifItemsList');
  if (!listEl) return;

  const all = getAllCombinedNotifications();
  const filtered = _notifActiveTag === 'all'
    ? all
    : all.filter(n => n.tag === _notifActiveTag);

  if (filtered.length === 0) {
    const emptyMsg = _notifActiveTag === 'git'
      ? 'Không có thông báo Git nào.'
      : (_notifActiveTag === 'agent'
        ? 'Không có thông báo Tác vụ Agent nào.'
        : (_notifActiveTag === 'jira' ? 'Không có thông báo Jira nào.' : 'Không có thông báo nào.'));
    listEl.innerHTML = `
      <div class="p-6 text-center text-slate-500 space-y-2 bg-white">
        <svg class="w-8 h-8 text-emerald-500 mx-auto" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
        </svg>
        <p class="text-xs font-semibold text-slate-800">${emptyMsg}</p>
      </div>
    `;
    return;
  }

  listEl.innerHTML = filtered.map(item => {
    const isUnread = !_readNotifIds.has(item.id);

    const st = (item.taskStatus || item.status || '').toLowerCase();
    const titleLower = (item.title || '').toLowerCase();
    const isDone = st === 'completed' || st === 'done' || st === 'success' || titleLower.includes('hoàn tất') || titleLower.includes('thành công');
    const isRunning = st === 'running' || titleLower.includes('đang thực thi') || titleLower.includes('đang chạy');
    const isStopped = st === 'stopped' || titleLower.includes('đã dừng') || titleLower.includes('dừng');

    let tagBadge = '';
    let titleClass = 'notif-title-default';
    let titleStyle = 'color: #0f172a;';

    if (item.tag === 'git') {
      if (item.status === 'completed' || item.status === 'success') {
        tagBadge = '<span class="notif-tag-badge notif-tag-git-done">Git · Đã pull</span>';
        titleClass = 'notif-title-done';
        titleStyle = 'color: #389e0d;';
      } else {
        tagBadge = '<span onclick="setNotifTagFilter(\'git\', event)" class="notif-tag-badge notif-tag-git-pull" title="Nhấp để lọc theo Git">Git cần pull</span>';
        titleClass = 'notif-title-running';
        titleStyle = 'color: #d48806;';
      }
    } else if (item.tag === 'jira') {
      if (item.notifType === 'comment_added') {
        tagBadge = '<span onclick="setNotifTagFilter(\'jira\', event)" class="notif-tag-badge notif-tag-jira-comment" title="Nhấp để lọc theo Jira">Jira · Bình luận</span>';
        titleClass = 'notif-title-running';
        titleStyle = 'color: #d48806;';
      } else {
        tagBadge = '<span onclick="setNotifTagFilter(\'jira\', event)" class="notif-tag-badge notif-tag-jira-task" title="Nhấp để lọc theo Jira">Jira · Task mới</span>';
        titleClass = 'notif-title-done';
        titleStyle = 'color: #389e0d;';
      }
    } else {
      if (isDone) {
        tagBadge = '<span onclick="setNotifTagFilter(\'agent\', event)" class="notif-tag-badge notif-tag-done" title="Nhấp để lọc theo Tác vụ Agent">Tác vụ Agent</span>';
        titleClass = 'notif-title-done';
        titleStyle = 'color: #389e0d;';
      } else if (isRunning) {
        tagBadge = '<span onclick="setNotifTagFilter(\'agent\', event)" class="notif-tag-badge notif-tag-running" title="Nhấp để lọc theo Tác vụ Agent">Tác vụ Agent</span>';
        titleClass = 'notif-title-running';
        titleStyle = 'color: #d48806;';
      } else if (isStopped) {
        tagBadge = '<span onclick="setNotifTagFilter(\'agent\', event)" class="notif-tag-badge notif-tag-stopped" title="Nhấp để lọc theo Tác vụ Agent">Tác vụ Agent</span>';
        titleClass = 'notif-title-stopped';
        titleStyle = 'color: #1677ff;';
      } else {
        tagBadge = '<span onclick="setNotifTagFilter(\'agent\', event)" class="notif-tag-badge notif-tag-default" title="Nhấp để lọc theo Tác vụ Agent">Tác vụ Agent</span>';
        titleClass = 'notif-title-default';
        titleStyle = 'color: #475569;';
      }
    }

    return `
      <div onclick="onNotifItemClick('${escapeHtml(item.id)}', event)"
        class="notif-item p-3 transition duration-150 cursor-pointer flex flex-col gap-1 select-none border-b border-slate-100 ${isUnread
        ? 'is-unread bg-blue-50/60 hover:bg-blue-100/70 border-l-4 border-l-[#199cff]'
        : 'bg-white hover:bg-slate-50 border-l-4 border-l-transparent'
      }">
        <div class="flex items-center justify-between gap-2">
          <div class="flex items-center gap-2 flex-wrap min-w-0 flex-1">
            ${tagBadge}
            <span class="font-bold text-xs ${titleClass} notif-item-title transition truncate" style="${isUnread ? 'color: #1677ff !important;' : titleStyle + ' !important;'}">
              ${escapeHtml(item.title)}
            </span>
          </div>
          ${isUnread ? '<span class="w-2 h-2 rounded-full bg-[#199cff] shrink-0" title="Chưa đọc"></span>' : ''}
        </div>
        <p class="text-[11.5px] ${isUnread ? 'text-slate-700' : 'text-slate-600'} leading-relaxed truncate" title="${escapeHtml(item.desc)}">
          ${item.hash ? `<span class="font-mono text-blue-600 font-bold">${escapeHtml(item.hash)}: </span>` : ''}${escapeHtml(item.desc)}
        </p>
        ${(item.author || item.date || item.timestamp) ? `
          <div class="text-[10px] text-slate-500 font-medium">
            ${item.author ? `Bởi ${escapeHtml(item.author)}${isAuthorMe(item.author, item.is_me) ? ' <span class="font-semibold text-[#1677ff] font-sans">(Tôi)</span>' : ''}` : ''} ${(item.date || item.timestamp) ? `• ${escapeHtml(formatRelativeDate(item.date, item.timestamp))}` : ''}
          </div>
        ` : ''}
      </div>
    `;
  }).join('');
}
window.renderNotificationList = renderNotificationList;

function onNotifItemClick(notifId, event) {
  if (event) {
    event.stopPropagation();
  }
  _readNotifIds.add(notifId);
  try {
    localStorage.setItem('easysalon_read_notifs', JSON.stringify([..._readNotifIds]));
  } catch (e) { }

  updateNotifBadgeUI();
  renderNotificationList();

  const all = getAllCombinedNotifications();
  const notif = all.find(n => n.id === notifId);
  if (!notif) return;

  if (notif.tag === 'git') {
    if (notif.role && notif.branch) {
      goToPullScreen(notif.role, notif.branch);
    }
  } else if (notif.tag === 'jira') {
    const menu = document.getElementById('notifDropdownMenu');
    if (menu) menu.classList.add('hidden');
    if (typeof onJiraNotificationClick === 'function') {
      onJiraNotificationClick(notif.issueKey, notif.notifType);
    } else if (typeof switchTab === 'function') {
      switchTab('jira');
    }
  } else if (notif.tag === 'agent') {
    const menu = document.getElementById('notifDropdownMenu');
    if (menu) menu.classList.add('hidden');
    if (typeof switchTab === 'function') switchTab('task');
    if (notif.taskId) {
      selectParallelTask(notif.taskId);
      setFeedFilter(notif.taskId);
    }
  }
}
window.onNotifItemClick = onNotifItemClick;

function markAllNotificationsAsRead() {
  const all = getAllCombinedNotifications();
  all.forEach(n => _readNotifIds.add(n.id));
  try {
    localStorage.setItem('easysalon_read_notifs', JSON.stringify([..._readNotifIds]));
  } catch (e) { }

  _isNotifBellRingingDismissed = true;
  const bellIcon = document.getElementById('notifBellIcon');
  if (bellIcon) {
    bellIcon.classList.remove('animate-bell-ring');
  }

  updateNotifBadgeUI();
  renderNotificationList();
  showToast('Đã đánh dấu tất cả thông báo là đã đọc.');
}
window.markAllNotificationsAsRead = markAllNotificationsAsRead;

async function clearAllNotifications() {
  if (!_savedNotifications || _savedNotifications.length === 0) {
    showToast('Danh sách thông báo hiện đang trống.');
    return;
  }
  const confirmed = await antdConfirm({
    title: 'Xóa toàn bộ lịch sử thông báo?',
    content: 'Tất cả các thông báo Git, Tác vụ Agent và Jira đã lưu sẽ bị xóa vĩnh viễn. Bạn có chắc chắn muốn xóa?',
    okText: 'Xóa tất cả lịch sử',
    cancelText: 'Hủy',
    danger: true
  });
  if (!confirmed) {
    const menu = document.getElementById('notifDropdownMenu');
    if (menu) menu.classList.remove('hidden');
    return;
  }

  _savedNotifications = [];
  savePersistentNotifications();
  _readNotifIds.clear();
  try {
    localStorage.removeItem('easysalon_read_notifs');
  } catch (e) {}
  _isNotifBellRingingDismissed = true;
  const bellIcon = document.getElementById('notifBellIcon');
  if (bellIcon) {
    bellIcon.classList.remove('animate-bell-ring');
  }
  updateNotifBadgeUI();
  renderNotificationList();
  showToast('Đã xóa toàn bộ lịch sử thông báo.');
}
window.clearAllNotifications = clearAllNotifications;

function updateGitNotifications(notifs) {
  (notifs || []).forEach(item => {
    const commitHash = item.latest ? (item.latest.hash || '') : (item.commits && item.commits[0] ? item.commits[0].hash : '');
    const notifId = commitHash ? `git_${item.role}_${item.branch}_${commitHash}` : `git_${item.role}_${item.branch}_count_${item.behind_count}`;
    const authorVal = item.latest ? item.latest.author : (item.commits && item.commits[0] ? item.commits[0].author : '');
    const isMeVal = item.latest ? !!item.latest.is_me : (item.commits && item.commits[0] ? !!item.commits[0].is_me : isAuthorMe(authorVal));

    addOrUpdateNotification({
      id: notifId,
      tag: 'git',
      tagLabel: 'Git',
      title: `${item.role.toUpperCase()} ${item.branch}: Có ${item.behind_count} commit mới`,
      desc: item.latest ? (item.latest.subject || '') : 'Có bản cập nhật remote cần pull về local.',
      author: authorVal,
      is_me: isMeVal,
      date: item.latest ? (item.latest.iso_date || item.latest.date) : (new Date().toISOString()),
      timestamp: item.latest ? (item.latest.timestamp || null) : (item.commits && item.commits[0] ? item.commits[0].timestamp : Date.now()),
      hash: commitHash,
      role: item.role,
      branch: item.branch,
      behind_count: item.behind_count,
      status: 'pending'
    });
  });

  updateNotifBadgeUI();
  renderNotificationList();
}
window.updateGitNotifications = updateGitNotifications;

function markPullSuccess(role, branch) {

  if (typeof renderBranchSyncStatus === 'function') {
    renderBranchSyncStatus(role, branch, { needs_pull: false, behind_count: 0 });
  }

  _savedNotifications.forEach(n => {
    if (n.tag === 'git' && n.role === role && n.branch === branch && n.status === 'pending') {
      n.status = 'completed';
      n.title = `${role.toUpperCase()} ${branch}: Đã pull thành công`;
      n.desc = 'Mã nguồn đã được pull về local thành công.';
      _readNotifIds.add(n.id);
    }
  });

  const successId = `git_success_${role}_${branch}_${Date.now()}`;
  addOrUpdateNotification({
    id: successId,
    tag: 'git',
    tagLabel: 'Git',
    title: `${role.toUpperCase()} ${branch}: Đã pull thành công`,
    desc: `Đã đồng bộ mã nguồn nhánh ${branch.toUpperCase()} của ${role === 'fe' ? 'Frontend' : 'Backend'} về local thành công.`,
    date: new Date().toLocaleTimeString('vi-VN', { hour: '2-digit', minute: '2-digit' }),
    role: role,
    branch: branch,
    status: 'success'
  });
  _readNotifIds.add(successId);
  try {
    localStorage.setItem('easysalon_read_notifs', JSON.stringify([..._readNotifIds]));
  } catch (e) {}

  savePersistentNotifications();
  updateNotifBadgeUI();
  renderNotificationList();
}
window.markPullSuccess = markPullSuccess;

function toggleNotifDropdown() {
  const menu = document.getElementById('notifDropdownMenu');
  if (!menu) return;
  const isHidden = menu.classList.contains('hidden');
  if (isHidden) {
    menu.classList.remove('hidden');

    _isNotifBellRingingDismissed = true;
    const bellIcon = document.getElementById('notifBellIcon');
    if (bellIcon) {
      bellIcon.classList.remove('animate-bell-ring');
    }

    renderNotificationList();
  } else {
    menu.classList.add('hidden');
  }
}
window.toggleNotifDropdown = toggleNotifDropdown;

function goToPullScreen(role, branch) {
  const menu = document.getElementById('notifDropdownMenu');
  if (menu) menu.classList.add('hidden');

  if (typeof switchTab === 'function') switchTab('branch');
  if (typeof switchGitSubTab === 'function') switchGitSubTab('pull_sync');

  setTimeout(() => {
    const upperRole = role === 'fe' ? 'Fe' : 'Be';
    const upperBranch = branch.charAt(0).toUpperCase() + branch.slice(1);
    const btnId = `btn${upperRole}Pull${upperBranch}`;
    const btn = document.getElementById(btnId);
    const card = btn?.closest('.bg-\\[\\#0e192c\\]') || btn;

    if (card) {
      card.scrollIntoView({ behavior: 'smooth', block: 'center' });
      card.classList.add('ring-2', role === 'fe' ? 'ring-cyan-400/80' : 'ring-emerald-400/80', 'transition-all', 'duration-300');
      setTimeout(() => {
        card.classList.remove('ring-2', 'ring-cyan-400/80', 'ring-emerald-400/80');
      }, 2000);
    }
  }, 150);

  showToast(`Đã chuyển tới phần Pull nhánh ${branch.toUpperCase()} của ${role === 'fe' ? 'Frontend' : 'Backend'}.`);
}
window.goToPullScreen = goToPullScreen;

document.addEventListener('click', (e) => {
  const modalRoot = document.getElementById('antdModalRoot');
  if (modalRoot && (!modalRoot.classList.contains('hidden') || modalRoot.contains(e.target))) {
    return;
  }
  const feWrap = document.getElementById('feCherryBranchDropdownWrap');
  const beWrap = document.getElementById('beCherryBranchDropdownWrap');
  const feSourceWrap = document.getElementById('feCherrySourceBranchDropdownWrap');
  const beSourceWrap = document.getElementById('beCherrySourceBranchDropdownWrap');
  const feMergeTargetWrap = document.getElementById('feMergeTargetDropdownWrap');
  const feMergeSourceWrap = document.getElementById('feMergeSourceDropdownWrap');
  const beMergeTargetWrap = document.getElementById('beMergeTargetDropdownWrap');
  const beMergeSourceWrap = document.getElementById('beMergeSourceDropdownWrap');
  const notifWrap = document.getElementById('notifWrap');

  const path = (typeof e.composedPath === 'function') ? e.composedPath() : [];
  const isInside = (el) => el && (el.contains(e.target) || path.includes(el));

  if (feWrap && !isInside(feWrap)) {
    const feMenu = document.getElementById('feCherryBranchDropdownMenu');
    if (feMenu) feMenu.classList.add('hidden');
  }
  if (beWrap && !isInside(beWrap)) {
    const beMenu = document.getElementById('beCherryBranchDropdownMenu');
    if (beMenu) beMenu.classList.add('hidden');
  }
  if (feSourceWrap && !isInside(feSourceWrap)) {
    const feSourceMenu = document.getElementById('feCherrySourceBranchDropdownMenu');
    if (feSourceMenu) feSourceMenu.classList.add('hidden');
  }
  if (beSourceWrap && !isInside(beSourceWrap)) {
    const beSourceMenu = document.getElementById('beCherrySourceBranchDropdownMenu');
    if (beSourceMenu) beSourceMenu.classList.add('hidden');
  }
  if (feMergeTargetWrap && !isInside(feMergeTargetWrap)) {
    const m = document.getElementById('feMergeTargetDropdownMenu');
    if (m) m.classList.add('hidden');
  }
  if (feMergeSourceWrap && !isInside(feMergeSourceWrap)) {
    const m = document.getElementById('feMergeSourceDropdownMenu');
    if (m) m.classList.add('hidden');
  }
  if (beMergeTargetWrap && !isInside(beMergeTargetWrap)) {
    const m = document.getElementById('beMergeTargetDropdownMenu');
    if (m) m.classList.add('hidden');
  }
  if (beMergeSourceWrap && !isInside(beMergeSourceWrap)) {
    const m = document.getElementById('beMergeSourceDropdownMenu');
    if (m) m.classList.add('hidden');
  }
  if (notifWrap && !isInside(notifWrap)) {
    const notifMenu = document.getElementById('notifDropdownMenu');
    if (notifMenu) notifMenu.classList.add('hidden');
  }
});

document.addEventListener('keydown', (e) => {
  if (e.key === 'Escape') {
    const modalRoot = document.getElementById('antdModalRoot');
    if (modalRoot && !modalRoot.classList.contains('hidden')) {
      return;
    }
    const menus = [
      'feCherryBranchDropdownMenu',
      'beCherryBranchDropdownMenu',
      'feCherrySourceBranchDropdownMenu',
      'beCherrySourceBranchDropdownMenu',
      'feMergeTargetDropdownMenu',
      'feMergeSourceDropdownMenu',
      'beMergeTargetDropdownMenu',
      'beMergeSourceDropdownMenu',
      'notifDropdownMenu'
    ];
    menus.forEach(id => {
      const el = document.getElementById(id);
      if (el && !el.classList.contains('hidden')) el.classList.add('hidden');
    });
  }
});

async function loadCherryPickInfo() {
  try {
    const [infoRes, statusRes] = await Promise.all([
      fetch('/api/git/info').then(r => r.json()).catch(() => null),
      fetch('/api/git/cherry-pick/status').then(r => r.json()).catch(() => null)
    ]);

    if (infoRes) {
      gitInfoData = infoRes;
      ['fe', 'be'].forEach(role => {
        const roleInfo = infoRes[role];
        if (!roleInfo) return;
        cherryPickState[role].current_branch = roleInfo.current_branch || '';
        cherryPickState[role].branches = roleInfo.branches || [];

        const branchTextEl = document.getElementById(role === 'fe' ? 'feCherrySelectedBranchText' : 'beCherrySelectedBranchText');
        if (branchTextEl) {
          branchTextEl.textContent = roleInfo.current_branch || 'unknown';
          branchTextEl.title = `Đang ở nhánh: ${roleInfo.current_branch || 'unknown'}`;
        }
        filterCherryBranches(role);

        const topBranchEl = document.getElementById(role === 'fe' ? 'feCherryTopBranch' : 'beCherryTopBranch');
        if (topBranchEl) {
          topBranchEl.textContent = roleInfo.current_branch || 'unknown';
        }

        const select = document.getElementById(role === 'fe' ? 'feCherrySourceBranchSelect' : 'beCherrySourceBranchSelect');
        if (select && roleInfo.branches) {
          const currentVal = select.value || cherryPickState[role]?.source_branch;
          if (select.tagName === 'SELECT') {
            select.innerHTML = '';
            roleInfo.branches.forEach(b => {
              const opt = document.createElement('option');
              opt.value = b.name;
              opt.textContent = b.name + (b.name === roleInfo.current_branch ? ' [Đang đứng]' : '');
              select.appendChild(opt);
            });
          }

          const branchNames = roleInfo.branches.map(b => b.name);
          let chosen = 'staging';
          if (currentVal && branchNames.includes(currentVal)) {
            chosen = currentVal;
          } else if (branchNames.includes('staging')) {
            chosen = 'staging';
          } else if (branchNames.includes('master')) {
            chosen = 'master';
          } else if (branchNames.length > 0) {
            chosen = branchNames[0];
          }

          select.value = chosen;
          cherryPickState[role].source_branch = chosen;

          const sourceTextEl = document.getElementById(role === 'fe' ? 'feCherrySelectedSourceBranchText' : 'beCherrySelectedSourceBranchText');
          if (sourceTextEl) {
            sourceTextEl.textContent = chosen;
            sourceTextEl.title = `Nhánh nguồn: ${chosen}`;
          }
          filterCherrySourceBranches(role);
        }
      });
    }

    if (statusRes) {
      ['fe', 'be'].forEach(role => {
        const st = statusRes[role];
        const box = document.getElementById(role === 'fe' ? 'feCherryConflictBox' : 'beCherryConflictBox');
        const filesBox = document.getElementById(role === 'fe' ? 'feCherryConflictFiles' : 'beCherryConflictFiles');
        if (!box) return;

        if (st && st.in_progress) {
          box.classList.remove('hidden');
          mountGitConflictResolver(role, role === 'fe' ? 'feCherryConflictTerminal' : 'beCherryConflictTerminal');
          if (filesBox) {
            if (st.conflicted_files && st.conflicted_files.length > 0) {
              filesBox.innerHTML = '<div class="text-amber-300 font-bold mb-1">Các file đang xung đột:</div>' +
                st.conflicted_files.map(f => `<div class="text-rose-300 font-mono text-[11px]">• ${escapeHtml(f)}</div>`).join('');
            } else if (st.status_raw) {
              filesBox.innerHTML = `<pre class="text-[11px] whitespace-pre-wrap">${escapeHtml(st.status_raw)}</pre>`;
            } else {
              filesBox.innerHTML = '<div>Đang trong trạng thái cherry-pick chưa hoàn tất.</div>';
            }
          }
        } else {
          box.classList.add('hidden');
        }
      });
    }

    loadBranchCommits('fe');
    loadBranchCommits('be');
  } catch (err) {
    console.error('Lỗi khi tải thông tin Cherry-Pick:', err);
  }
}

let cherryPickCommitsData = { fe: [], be: [] };
let cherryPickCurrentPage = { fe: 1, be: 1 };
const CHERRY_PAGE_SIZE = 10;

function changeCherryPage(role, targetPage) {
  const commits = cherryPickCommitsData[role] || [];
  const totalPages = Math.max(1, Math.ceil(commits.length / CHERRY_PAGE_SIZE));
  const newPage = Math.max(1, Math.min(totalPages, targetPage));
  cherryPickCurrentPage[role] = newPage;
  renderCommitsList(role);
}
window.changeCherryPage = changeCherryPage;

async function loadBranchCommits(role) {
  const select = document.getElementById(role === 'fe' ? 'feCherrySourceBranchSelect' : 'beCherrySourceBranchSelect');
  const listEl = document.getElementById(role === 'fe' ? 'feCherryCommitsList' : 'beCherryCommitsList');
  const countEl = document.getElementById(role === 'fe' ? 'feCherryCommitsCount' : 'beCherryCommitsCount');
  if (!select || !listEl) return;

  const branch = select.value || cherryPickState[role]?.source_branch || 'staging';
  listEl.innerHTML = `
        <div class="text-center text-xs text-slate-400 py-6 flex items-center justify-center gap-2">
          <svg class="animate-spin h-4 w-4 text-cyan-400" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
            <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
            <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
          </svg>
          <span>Đang tải danh sách commit của nhánh <b>${escapeHtml(branch)}</b>...</span>
        </div>
      `;

  try {
    const res = await fetch(`/api/git/commits?target=${role}&branch=${encodeURIComponent(branch)}&limit=300`);
    const data = await res.json();
    if (data && data.commits) {
      cherryPickCommitsData[role] = data.commits;
      cherryPickCurrentPage[role] = 1;
      renderCommitsList(role);
    } else {
      cherryPickCommitsData[role] = [];
      listEl.innerHTML = `<div class="text-center text-xs text-slate-400 py-6">Không tìm thấy commit nào hoặc nhánh không tồn tại.</div>`;
      if (countEl) countEl.textContent = '';
    }
  } catch (err) {
    cherryPickCommitsData[role] = [];
    listEl.innerHTML = `<div class="text-center text-xs text-rose-400 py-6">Lỗi tải commit: ${escapeHtml(err.message)}</div>`;
    if (countEl) countEl.textContent = '';
  }
}

function renderCommitsList(role, commitsArg) {
  const listEl = document.getElementById(role === 'fe' ? 'feCherryCommitsList' : 'beCherryCommitsList');
  const countEl = document.getElementById(role === 'fe' ? 'feCherryCommitsCount' : 'beCherryCommitsCount');
  if (!listEl) return;

  if (Array.isArray(commitsArg)) {
    cherryPickCommitsData[role] = commitsArg;
  }
  const allCommits = cherryPickCommitsData[role] || [];

  if (allCommits.length === 0) {
    listEl.innerHTML = `<div class="text-center text-xs text-slate-400 py-6">Không có commit nào trong nhánh này.</div>`;
    if (countEl) countEl.textContent = '';
    return;
  }

  const page = cherryPickCurrentPage[role] || 1;
  const totalPages = Math.max(1, Math.ceil(allCommits.length / CHERRY_PAGE_SIZE));
  const safePage = Math.max(1, Math.min(totalPages, page));
  const startIdx = (safePage - 1) * CHERRY_PAGE_SIZE;
  const pageCommits = allCommits.slice(startIdx, startIdx + CHERRY_PAGE_SIZE);

  if (countEl) {
    countEl.textContent = `(${allCommits.length} commit - Trang ${safePage}/${totalPages})`;
  }

  const isFe = role === 'fe';
  const accentBg = isFe ? 'bg-cyan-950/70 border-cyan-800/60 text-cyan-300' : 'bg-emerald-950/70 border-emerald-800/60 text-emerald-300';
  const hoverBorder = isFe ? 'hover:border-cyan-500' : 'hover:border-emerald-500';

  const commitsHtml = pageCommits.map(c => {
    const shortHash = c.short_hash || (c.hash ? c.hash.substring(0, 8) : 'unknown');
    const safeSubject = escapeHtml(c.subject || '');
    const authorHtml = formatCommitAuthor(c.author, c.is_me);
    const safeDate = escapeHtml(formatRelativeDate(c.date || ''));
    const fullHash = c.hash || '';

    return `
          <div class="group bg-[#101e38] border border-[#244170] ${hoverBorder} rounded p-2 transition flex items-center justify-between gap-2.5 text-xs">
            <div class="flex-1 min-w-0 space-y-1">
              <div class="flex items-center gap-2">
                <span class="font-mono text-[11px] font-semibold px-1.5 py-0.5 rounded border ${accentBg} select-all" title="${fullHash}">
                  ${shortHash}
                </span>
                <span class="font-medium text-slate-100 truncate" title="${safeSubject}">${safeSubject}</span>
              </div>
              <div class="flex items-center gap-2 text-[10px] text-slate-400">
                <span class="truncate max-w-[170px]">${authorHtml}</span>
                <span>•</span>
                <span>${safeDate}</span>
              </div>
            </div>
            <div class="flex items-center gap-1.5 shrink-0">
              <button type="button" onclick="executeCherryPickDirect('${role}', '${fullHash}', '${safeSubject.replace(/'/g, "\\'")}')" class="ant-btn ant-btn-primary text-[11px] h-[26px] px-2.5 flex items-center gap-1 font-medium whitespace-nowrap shadow-sm rounded-[4px]">
                <span>Cherry-pick</span>
              </button>
            </div>
          </div>
        `;
  }).join('');

  const paginationHtml = totalPages > 1 ? `
    <div class="flex items-center justify-between pt-2 px-1 border-t border-[#244170] text-xs mt-1">
      <div class="text-[11px] text-slate-400 font-mono">
        Trang <b class="text-cyan-300">${safePage}</b> / <b>${totalPages}</b> <span class="text-slate-500">(${allCommits.length} commit)</span>
      </div>
      <div class="flex items-center gap-1">
        <button type="button" onclick="changeCherryPage('${role}', 1)" ${safePage <= 1 ? 'disabled' : ''} class="px-2 py-0.5 rounded bg-[#101e38] border border-[#244170] hover:bg-[#152747] text-slate-300 disabled:opacity-30 disabled:cursor-not-allowed text-[11px] font-mono transition cursor-pointer" title="Trang đầu">«</button>
        <button type="button" onclick="changeCherryPage('${role}', ${safePage - 1})" ${safePage <= 1 ? 'disabled' : ''} class="px-2 py-0.5 rounded bg-[#101e38] border border-[#244170] hover:bg-[#152747] text-slate-300 disabled:opacity-30 disabled:cursor-not-allowed text-[11px] transition cursor-pointer">‹ Trước</button>
        <span class="px-2 py-0.5 rounded bg-cyan-950/80 border border-cyan-800 text-cyan-300 font-mono text-[11px] font-bold">${safePage}</span>
        <button type="button" onclick="changeCherryPage('${role}', ${safePage + 1})" ${safePage >= totalPages ? 'disabled' : ''} class="px-2 py-0.5 rounded bg-[#101e38] border border-[#244170] hover:bg-[#152747] text-slate-300 disabled:opacity-30 disabled:cursor-not-allowed text-[11px] transition cursor-pointer">Sau ›</button>
        <button type="button" onclick="changeCherryPage('${role}', ${totalPages})" ${safePage >= totalPages ? 'disabled' : ''} class="px-2 py-0.5 rounded bg-[#101e38] border border-[#244170] hover:bg-[#152747] text-slate-300 disabled:opacity-30 disabled:cursor-not-allowed text-[11px] font-mono transition cursor-pointer" title="Trang cuối">»</button>
      </div>
    </div>
  ` : '';

  listEl.innerHTML = commitsHtml + paginationHtml;
}

async function onCherryBranchSwitch(role, targetBranch) {
  if (!targetBranch) return;
  const current = cherryPickState[role]?.current_branch;
  if (targetBranch === current) return;

  if (!cherryPickState[role]) cherryPickState[role] = {};
  if (current) {
    cherryPickState[role].previous_branch = current;
  }

  const roleName = role === 'fe' ? 'Frontend (easysalon-webapp)' : 'Backend (easysalon-api)';

  const confirmed = await antdConfirm({
    title: 'Xác nhận chuyển nhánh',
    content: `Bạn có chắc muốn thực hiện chuyển sang nhánh "${targetBranch}" cho ${roleName}?`,
    okText: 'Chuyển nhánh'
  });

  if (!confirmed) return;

  showToast(`Đang chuyển ${role === 'fe' ? 'Frontend' : 'Backend'} sang nhánh '${targetBranch}'...`);

  try {
    const res = await fetch('/api/git/checkout', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        target: role,
        branch: targetBranch,
        create_new: false
      })
    });
    const data = await res.json();
    if (data.success) {
      showToast(`${role === 'fe' ? 'Frontend' : 'Backend'}: Đã chuyển sang nhánh '${targetBranch}' thành công.`);
      clearCherrySuccessBox(role);
    } else {
      showToast(data.message || 'Lỗi khi chuyển nhánh.');
      await antdAlert({
        title: 'Lỗi chuyển nhánh',
        content: data.message || 'Không thể chuyển nhánh.',
        type: 'error'
      });
    }
  } catch (err) {
    showToast('Lỗi kết nối khi chuyển nhánh: ' + err.message);
  } finally {
    await loadGitBranchInfo();
    await loadCherryPickInfo();
  }
}
window.onCherryBranchSwitch = onCherryBranchSwitch;

async function executeCherryPickDirect(role, hash, subject) {
  if (!hash) return;
  const currentBranch = cherryPickState[role]?.current_branch || (document.getElementById(role === 'fe' ? 'feCherrySelectedBranchText' : 'beCherrySelectedBranchText')?.textContent.trim() || 'nhánh hiện tại');
  const shortHash = hash.length > 8 ? hash.substring(0, 8) : hash;

  const confirmed = await antdConfirm({
    title: 'Xác nhận Cherry-Pick',
    content: `Bạn có chắc muốn cherry-pick commit ${shortHash} vào nhánh "${currentBranch}"?`,
    okText: 'Cherry-Pick'
  });
  if (!confirmed) return;

  showToast(`Đang cherry-pick commit ${shortHash} vào nhánh ${currentBranch}...`);

  try {
    const res = await fetch('/api/git/cherry-pick', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        target: role,
        commits: hash,
        record_origin: true,
        no_commit: false
      })
    });
    const data = await res.json();

    const successBox = document.getElementById(role === 'fe' ? 'feCherrySuccessBox' : 'beCherrySuccessBox');
    const errorBox = document.getElementById(role === 'fe' ? 'feCherryErrorBox' : 'beCherryErrorBox');
    const commitMsgInput = document.getElementById(role === 'fe' ? 'feCherryCommitMsgInput' : 'beCherryCommitMsgInput');
    const successTitle = document.getElementById(role === 'fe' ? 'feCherrySuccessTitle' : 'beCherrySuccessTitle');

    if (data.success) {
      const msg = data.message || `Đã cherry-pick commit ${shortHash} vào nhánh '${currentBranch}' thành công!`;
      showToast(msg);
      if (errorBox) errorBox.classList.add('hidden');
      if (successBox) {
        successBox.classList.remove('hidden');
        if (successTitle) successTitle.textContent = `Đã cherry-pick commit ${shortHash} vào nhánh '${currentBranch}' thành công!`;
        if (commitMsgInput) {
          commitMsgInput.value = data.commit_message || subject || '';
          commitMsgInput.disabled = false;
        }
        const commitMsgSection = document.getElementById(role === 'fe' ? 'feCherryCommitMsgSection' : 'beCherryCommitMsgSection');
        if (commitMsgSection) commitMsgSection.classList.remove('hidden');
        const promptText = document.getElementById(role === 'fe' ? 'feCherryPushPromptText' : 'beCherryPushPromptText');
        if (promptText) promptText.textContent = 'Đẩy commit này lên nhánh remote:';
        const pushBtn = document.getElementById(role === 'fe' ? 'btnFeCherryPush' : 'btnBeCherryPush');
        const pushBtnText = document.getElementById(role === 'fe' ? 'btnFeCherryPushText' : 'btnBeCherryPushText');
        const closeBtn = document.getElementById(role === 'fe' ? 'btnFeCherryCloseSuccess' : 'btnBeCherryCloseSuccess');
        if (pushBtn) {
          pushBtn.dataset.pushed = 'false';
          pushBtn.disabled = false;
          pushBtn.classList.remove('opacity-60', 'cursor-not-allowed', 'pointer-events-none');
          if (pushBtnText) pushBtnText.textContent = 'Push code lên nhánh';
        }
        if (closeBtn) closeBtn.classList.add('hidden');
        const returnWrap = document.getElementById(role === 'fe' ? 'feCherryReturnBranchWrap' : 'beCherryReturnBranchWrap');
        if (returnWrap) returnWrap.classList.add('hidden');
      }
    } else if (data.conflict) {
      showToast('Xung đột (conflict) khi cherry-pick commit!');
      if (successBox) successBox.classList.add('hidden');
      if (errorBox) errorBox.classList.add('hidden');
      await antdAlert({
        title: 'Xảy ra xung đột (Conflict)',
        content: `Quá trình cherry-pick commit ${shortHash} gặp xung đột mã nguồn.\n\nVui lòng kiểm tra các file xung đột hiển thị trên giao diện, giải quyết và bấm "Tiếp tục (--continue)", hoặc bấm "Hủy bỏ (--abort)" để quay lại trạng thái ban đầu.`,
        type: 'error'
      });
    } else {
      showToast(data.message || 'Thao tác cherry-pick thất bại.');
      if (successBox) successBox.classList.add('hidden');
      if (errorBox) {
        errorBox.classList.remove('hidden');
        const errorDetail = document.getElementById(role === 'fe' ? 'feCherryErrorDetail' : 'beCherryErrorDetail');
        if (errorDetail) errorDetail.textContent = data.message || data.output || 'Không thể thực hiện cherry-pick.';
      }
      await antdAlert({
        title: 'Lỗi Cherry-Pick',
        content: data.message || 'Không thể thực hiện cherry-pick.',
        type: 'error'
      });
    }

    await loadCherryPickInfo();
    if (typeof loadGitBranchInfo === 'function') loadGitBranchInfo();
    if (activeTab === 'log' && typeof loadWorkLogs === 'function') loadWorkLogs();
  } catch (err) {
    showToast('Lỗi kết nối khi cherry-pick: ' + err.message);
  }
}
window.executeCherryPickDirect = executeCherryPickDirect;
window.quickCherryPick = executeCherryPickDirect;

function clearCherrySuccessBox(role) {
  const successBox = document.getElementById(role === 'fe' ? 'feCherrySuccessBox' : 'beCherrySuccessBox');
  const commitMsgInput = document.getElementById(role === 'fe' ? 'feCherryCommitMsgInput' : 'beCherryCommitMsgInput');
  const commitMsgSection = document.getElementById(role === 'fe' ? 'feCherryCommitMsgSection' : 'beCherryCommitMsgSection');
  const promptText = document.getElementById(role === 'fe' ? 'feCherryPushPromptText' : 'beCherryPushPromptText');
  const btn = document.getElementById(role === 'fe' ? 'btnFeCherryPush' : 'btnBeCherryPush');
  const btnText = document.getElementById(role === 'fe' ? 'btnFeCherryPushText' : 'btnBeCherryPushText');
  const closeBtn = document.getElementById(role === 'fe' ? 'btnFeCherryCloseSuccess' : 'btnBeCherryCloseSuccess');
  const returnWrap = document.getElementById(role === 'fe' ? 'feCherryReturnBranchWrap' : 'beCherryReturnBranchWrap');
  const successTitle = document.getElementById(role === 'fe' ? 'feCherrySuccessTitle' : 'beCherrySuccessTitle');

  if (successBox) successBox.classList.add('hidden');
  if (commitMsgInput) {
    commitMsgInput.value = '';
    commitMsgInput.disabled = false;
  }
  if (commitMsgSection) commitMsgSection.classList.remove('hidden');
  if (promptText) promptText.textContent = 'Đẩy commit này lên nhánh remote:';
  if (successTitle) successTitle.textContent = 'Cherry-pick commit thành công!';
  if (closeBtn) closeBtn.classList.add('hidden');

  if (btn) {
    btn.dataset.pushed = 'false';
    btn.disabled = false;
    btn.classList.remove('opacity-60', 'cursor-not-allowed', 'pointer-events-none');
    if (btnText) btnText.textContent = 'Push code lên nhánh';
  }
  if (returnWrap) returnWrap.classList.add('hidden');
}
window.clearCherrySuccessBox = clearCherrySuccessBox;

async function doCherryPush(role) {
  const roleName = role === 'fe' ? 'Frontend (easysalon-webapp)' : 'Backend (easysalon-api)';
  const currentBranch = cherryPickState[role]?.current_branch || (document.getElementById(role === 'fe' ? 'feCherrySelectedBranchText' : 'beCherrySelectedBranchText')?.textContent.trim() || '');
  const msgInput = document.getElementById(role === 'fe' ? 'feCherryCommitMsgInput' : 'beCherryCommitMsgInput');
  const btn = document.getElementById(role === 'fe' ? 'btnFeCherryPush' : 'btnBeCherryPush');
  const btnText = document.getElementById(role === 'fe' ? 'btnFeCherryPushText' : 'btnBeCherryPushText');
  const spinner = document.getElementById(role === 'fe' ? 'feCherryPushSpinner' : 'beCherryPushSpinner');
  const closeBtn = document.getElementById(role === 'fe' ? 'btnFeCherryCloseSuccess' : 'btnBeCherryCloseSuccess');

  if (btn && btn.dataset.pushed === 'true') {
    await antdAlert({
      title: 'Đã hoàn tất Push',
      content: `Commit trên nhánh "${currentBranch}" (${roleName}) đã được đẩy lên remote hoàn tất rồi. Không cần push lần nữa!`,
      type: 'info'
    });
    return;
  }

  const commitMsg = msgInput ? msgInput.value.trim() : '';

  const confirmed = await antdConfirm({
    title: 'Xác nhận Push code',
    content: `Bạn có chắc muốn đẩy (git push) commit lên nhánh "${currentBranch}" của ${roleName}?`,
    okText: 'Push code'
  });
  if (!confirmed) return;

  if (btn) btn.disabled = true;
  if (spinner) spinner.classList.remove('hidden');
  showToast(`Đang push code lên nhánh '${currentBranch}'...`);

  let pushSuccess = false;
  try {
    const res = await fetch('/api/git/push', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        target: role,
        branch: currentBranch,
        commit_message: commitMsg
      })
    });
    const data = await res.json();
    if (data.success) {
      pushSuccess = true;
      if (data.already_pushed) {
        showToast(data.message || `Nhánh '${currentBranch}' đã đồng bộ với remote.`);
        await antdAlert({
          title: 'Đã đồng bộ remote',
          content: data.message || `Nhánh "${currentBranch}" đã ở trạng thái mới nhất trên remote (Everything up-to-date). Không có commit mới nào cần push lại!`,
          type: 'info'
        });
      } else {
        showToast(`Đã push code lên nhánh '${currentBranch}' thành công!`);
      }

      if (msgInput) {
        msgInput.value = '';
        msgInput.disabled = true;
      }
      const commitMsgSection = document.getElementById(role === 'fe' ? 'feCherryCommitMsgSection' : 'beCherryCommitMsgSection');
      if (commitMsgSection) commitMsgSection.classList.add('hidden');

      const promptText = document.getElementById(role === 'fe' ? 'feCherryPushPromptText' : 'beCherryPushPromptText');
      if (promptText) promptText.textContent = 'Trạng thái trên remote:';

      const successTitle = document.getElementById(role === 'fe' ? 'feCherrySuccessTitle' : 'beCherrySuccessTitle');
      if (successTitle) {
        successTitle.textContent = `Đã đẩy commit lên nhánh '${currentBranch}' thành công!`;
      }

      if (btn) {
        btn.dataset.pushed = 'true';
        btn.disabled = true;
        btn.classList.add('opacity-60', 'cursor-not-allowed', 'pointer-events-none');
        if (btnText) btnText.textContent = 'Đã push lên remote';
      }
      if (closeBtn) closeBtn.classList.remove('hidden');

      const returnWrap = document.getElementById(role === 'fe' ? 'feCherryReturnBranchWrap' : 'beCherryReturnBranchWrap');
      const prevBranch = (cherryPickState[role]?.previous_branch || cherryPickState[role]?.source_branch || '').trim();
      if (returnWrap && prevBranch && prevBranch !== currentBranch) {
        returnWrap.classList.remove('hidden');
        const returnText = document.getElementById(role === 'fe' ? 'btnFeCherryReturnPrevBranchText' : 'btnBeCherryReturnPrevBranchText');
        if (returnText) {
          returnText.textContent = `Quay về lại nhánh lúc nãy (${prevBranch})`;
          returnText.title = `Quay về lại nhánh ${prevBranch}`;
        }
      }
    } else {
      showToast(`Push thất bại: ${data.message || 'Lỗi khi push code.'}`);
      await antdAlert({
        title: 'Lỗi Push code',
        content: data.message || 'Không thể push code lên remote.',
        type: 'error'
      });
    }
  } catch (err) {
    showToast('Lỗi kết nối khi push: ' + err.message);
  } finally {
    if (spinner) spinner.classList.add('hidden');

    if (!pushSuccess && btn) {
      btn.disabled = false;
    }
    await loadCherryPickInfo();
    if (typeof loadGitBranchInfo === 'function') loadGitBranchInfo();
  }
}
window.doCherryPush = doCherryPush;

async function doReturnToPrevCherryBranch(role) {
  const prevBranch = (cherryPickState[role]?.previous_branch || cherryPickState[role]?.source_branch || '').trim();
  if (!prevBranch) {
    showToast('Không tìm thấy thông tin nhánh lúc nãy để quay về.');
    return;
  }
  const roleName = role === 'fe' ? 'Frontend' : 'Backend';
  const confirmed = await antdConfirm({
    title: `Quay về lại nhánh lúc nãy (${prevBranch})`,
    content: `Bạn có muốn checkout quay lại nhánh cũ "${prevBranch}" trên ${roleName}?`,
    okText: 'Quay về nhánh'
  });
  if (!confirmed) return;

  const btn = document.getElementById(role === 'fe' ? 'btnFeCherryReturnPrevBranch' : 'btnBeCherryReturnPrevBranch');
  if (btn) btn.disabled = true;

  showToast(`Đang chuyển về nhánh '${prevBranch}'...`);

  try {
    const res = await fetch('/api/git/checkout', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ target: role, branch: prevBranch, create_new: false })
    });
    const data = await res.json();
    if (data.success) {
      showToast(`Đã quay về nhánh '${prevBranch}' thành công!`);
      clearCherrySuccessBox(role);
      const returnWrap = document.getElementById(role === 'fe' ? 'feCherryReturnBranchWrap' : 'beCherryReturnBranchWrap');
      if (returnWrap) returnWrap.classList.add('hidden');
      await loadCherryPickInfo();
      if (typeof loadGitBranchInfo === 'function') loadGitBranchInfo();
      if (typeof loadPullSyncInfo === 'function') loadPullSyncInfo();
    } else {
      showToast(`Không thể quay về nhánh: ${data.message || 'Lỗi checkout.'}`);
    }
  } catch (err) {
    showToast('Lỗi khi checkout nhánh: ' + err.message);
  } finally {
    if (btn) btn.disabled = false;
  }
}
window.doReturnToPrevCherryBranch = doReturnToPrevCherryBranch;

async function doCherryPickAbort(role) {
  const roleName = role === 'fe' ? 'Frontend' : 'Backend';
  const confirmed = await antdConfirm({
    title: 'Hủy bỏ Cherry-Pick',
    content: `Bạn có chắc muốn hủy bỏ quá trình cherry-pick đang dở dang trên ${roleName}? Tất cả thay đổi chưa lưu của commit này sẽ được hoàn tác.`,
    okText: 'Hủy bỏ cherry-pick',
    danger: true
  });
  if (!confirmed) return;

  try {
    const res = await fetch('/api/git/cherry-pick/abort', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ target: role })
    });
    const data = await res.json();
    showToast(data.message || (data.success ? 'Đã hủy bỏ cherry-pick thành công.' : 'Lỗi khi hủy bỏ cherry-pick.'));
    clearCherrySuccessBox(role);
    await loadCherryPickInfo();
    if (typeof loadGitBranchInfo === 'function') loadGitBranchInfo();
    if (activeTab === 'log' && typeof loadWorkLogs === 'function') loadWorkLogs();
  } catch (err) {
    showToast('Lỗi kết nối khi hủy bỏ cherry-pick: ' + err.message);
  }
}

async function doCherryPickContinue(role) {
  const roleName = role === 'fe' ? 'Frontend' : 'Backend';
  const confirmed = await antdConfirm({
    title: 'Tiếp tục Cherry-Pick',
    content: `Bạn đã xử lý xong các file xung đột (conflict) trên ${roleName} và muốn tiếp tục hoàn tất commit?`,
    okText: 'Tiếp tục'
  });
  if (!confirmed) return;

  try {
    const res = await fetch('/api/git/cherry-pick/continue', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ target: role })
    });
    const data = await res.json();
    showToast(data.message || (data.success ? 'Đã hoàn tất cherry-pick tiếp tục.' : 'Lỗi khi tiếp tục cherry-pick.'));
    await loadCherryPickInfo();
    if (typeof loadGitBranchInfo === 'function') loadGitBranchInfo();
    if (activeTab === 'log' && typeof loadWorkLogs === 'function') loadWorkLogs();
  } catch (err) {
    showToast('Lỗi kết nối khi tiếp tục cherry-pick: ' + err.message);
  }
}

let _isCheckingSync = false;
const _expandedSyncPullDiffs = new Set();
const _expandedCommitDiffs = new Set();

function toggleCommitDiff(role, branch, commitHash, event) {
  if (event) event.stopPropagation();
  const key = `${role}_${branch}_${commitHash}`;
  const detailEl = document.getElementById(`commitDetail_${key}`);
  const arrowEl = document.getElementById(`commitArrow_${key}`);
  if (!detailEl) return;
  const isHidden = detailEl.classList.contains('hidden');
  if (isHidden) {
    detailEl.classList.remove('hidden');
    _expandedCommitDiffs.add(key);
    if (arrowEl) arrowEl.classList.add('rotate-180');
  } else {
    detailEl.classList.add('hidden');
    _expandedCommitDiffs.delete(key);
    if (arrowEl) arrowEl.classList.remove('rotate-180');
  }
}
window.toggleCommitDiff = toggleCommitDiff;

function toggleSyncPullDiff(role, branch, event) {
  if (event) event.stopPropagation();
  const key = `${role}_${branch}`;
  const detailEl = document.getElementById(`syncPullDetail_${key}`);
  const arrowEl = document.getElementById(`syncPullArrow_${key}`);
  if (!detailEl) return;
  const isHidden = detailEl.classList.contains('hidden');
  if (isHidden) {
    detailEl.classList.remove('hidden');
    _expandedSyncPullDiffs.add(key);
    if (arrowEl) arrowEl.classList.add('rotate-180');
  } else {
    detailEl.classList.add('hidden');
    _expandedSyncPullDiffs.delete(key);
    if (arrowEl) arrowEl.classList.remove('rotate-180');
  }
}
window.toggleSyncPullDiff = toggleSyncPullDiff;

function renderBranchSyncStatus(role, branch, info) {
  const badgeEl = document.getElementById(`${role}_${branch}_statusBadge`);
  const boxEl = document.getElementById(`${role}_${branch}_commitsBox`);
  const upperRole = role.charAt(0).toUpperCase() + role.slice(1);
  const upperBranch = branch.charAt(0).toUpperCase() + branch.slice(1);
  const btnTextEl = document.getElementById(`btn${upperRole}Pull${upperBranch}Text`);
  const btnEl = document.getElementById(`btn${upperRole}Pull${upperBranch}`);

  if (!info) return;

  if (info.needs_pull) {
    if (badgeEl) {
      badgeEl.classList.remove('hidden');
      badgeEl.innerHTML = `
            <span class="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded text-[11px] font-bold bg-amber-500/20 text-amber-300 border border-amber-500/40 shadow-sm">
              <span class="w-2 h-2 rounded-full bg-amber-400"></span>
              <span>Có ${info.behind_count} commit mới</span>
            </span>
          `;
    }

    if (btnTextEl) {
      btnTextEl.textContent = `Pull ${upperBranch} (${info.behind_count} mới)`;
    }
    if (btnEl) {
      btnEl.disabled = false;
      btnEl.classList.remove('opacity-50', 'cursor-not-allowed');
      btnEl.classList.add('ring-2', 'ring-amber-400/50');
      btnEl.title = `Có ${info.behind_count} commit mới từ origin/${branch}`;
    }

    if (boxEl) {
      const syncKey = `${role}_${branch}`;
      const isExpanded = _expandedSyncPullDiffs.has(syncKey);
      const commitsHtml = (info.commits || []).map(c => {
        const commitKey = `${role}_${branch}_${c.hash}`;
        const isCommitExpanded = _expandedCommitDiffs.has(commitKey);
        const commitFiles = c.files || [];
        const commitAdds = commitFiles.reduce((acc, f) => acc + (Number(f.additions) || 0), 0);
        const commitDels = commitFiles.reduce((acc, f) => acc + (Number(f.deletions) || 0), 0);

        const commitFilesHtml = commitFiles.length > 0 ? `
          <div class="space-y-1 max-h-60 overflow-y-auto pr-1">
            ${commitFiles.map(f => `
              <div class="sync-file-item flex items-center justify-between gap-2 py-1 px-2.5 rounded bg-black/40 border border-white/5 text-[10.5px]">
                <span class="sync-file-path truncate text-[#0958d9] dark:text-sky-300 font-mono font-medium hover:underline cursor-pointer"
                      title="Xem toàn bộ mã nguồn file: ${escapeHtml(f.path)}"
                      onclick="event.stopPropagation(); openFileEditor('${escapeHtml(f.path)}', '${escapeHtml(role)}')">
                  ${escapeHtml(f.path)}
                </span>
                <div class="flex items-center gap-1.5 shrink-0 font-mono">
                  <span class="text-[#73c991] font-bold">+${f.additions || 0}</span>
                  <span class="text-[#f14c4c] font-bold">-${f.deletions || 0}</span>
                  <button type="button"
                    onclick="event.stopPropagation(); openFileEditor('${escapeHtml(f.path)}', '${escapeHtml(role)}')"
                    class="sync-file-view-btn p-1 rounded hover:bg-sky-500/15 text-sky-400 hover:text-sky-300 transition flex items-center justify-center cursor-pointer"
                    title="Xem toàn bộ mã nguồn file (${escapeHtml(f.path)}) (Full code)">
                    <svg class="w-3.5 h-3.5 fill-none stroke-current" viewBox="0 0 24 24" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                      <path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z" />
                      <circle cx="12" cy="12" r="3" />
                    </svg>
                  </button>
                </div>
              </div>
            `).join('')}
          </div>
        ` : '<div class="text-slate-400 text-xs py-1">Không có file thay đổi riêng</div>';

        const commitDiffHtml = c.diff ? `
          <div class="mt-2.5">
            <div class="flex items-center justify-between text-[11px] text-slate-300 mb-1.5 px-0.5">
              <span class="sync-commit-header font-bold text-amber-300 flex items-center gap-1.5">
                <svg class="w-3.5 h-3.5 text-amber-400 shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
                  <path stroke-linecap="round" stroke-linejoin="round" d="M10 20l4-16m4 4l4 4-4 4M6 16l-4-4 4-4" />
                </svg>
                <span>Diff của commit ${escapeHtml(c.hash)}:</span>
              </span>
              ${commitFiles.length > 0 ? `
                <button type="button"
                  onclick="event.stopPropagation(); openFileEditor('${escapeHtml(commitFiles[0].path)}', '${escapeHtml(role)}')"
                  class="sync-diff-view-full-btn inline-flex items-center gap-1.5 px-2 py-0.5 rounded text-[10.5px] font-sans font-medium text-sky-400 hover:text-sky-300 hover:bg-sky-500/15 border border-sky-500/30 transition cursor-pointer"
                  title="Xem toàn bộ mã nguồn file (${escapeHtml(commitFiles[0].path)}) (Full code)">
                  <svg class="w-3.5 h-3.5 fill-none stroke-current" viewBox="0 0 24 24" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                    <path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z" />
                    <circle cx="12" cy="12" r="3" />
                  </svg>
                  <span>Xem file</span>
                </button>
              ` : ''}
            </div>
            <div class="sync-diff-wrapper rounded-md bg-[#1e1e1e] border border-[#333333] max-h-[500px] min-h-[140px] overflow-auto text-[11.5px] font-mono leading-relaxed shadow-inner">
              ${typeof formatDiffColoredHtml === 'function' ? formatDiffColoredHtml(c.diff) : `<pre class="text-[#d4d4d4] p-3 whitespace-pre-wrap">${escapeHtml(c.diff)}</pre>`}
            </div>
          </div>
        ` : '';

        return `
          <div class="commit-item-card rounded-md border border-white/10 bg-white/[0.03] hover:bg-white/[0.06] transition overflow-hidden">
            <div class="flex items-center justify-between gap-2 py-1.5 px-2.5 cursor-pointer select-none text-[11px]"
                 onclick="toggleCommitDiff('${role}', '${branch}', '${escapeHtml(c.hash)}', event)"
                 title="Nhấp để xem các file và diff của commit ${escapeHtml(c.hash)}">
              <div class="flex items-center gap-2 min-w-0 flex-1">
                <span class="text-cyan-400 font-bold shrink-0 font-mono">${escapeHtml(c.hash)}</span>
                <span class="text-slate-200 truncate font-sans font-medium" title="${escapeHtml(c.subject)}">${escapeHtml(c.subject)}</span>
              </div>
              <div class="flex items-center gap-2 shrink-0">
                <span class="text-slate-400 text-[10px] shrink-0 font-sans">${formatCommitAuthor(c.author, c.is_me)} • ${escapeHtml(formatRelativeDate(c.date))}</span>
                ${commitFiles.length > 0 ? `
                  <span class="px-1.5 py-0.5 rounded text-[9.5px] font-mono bg-cyan-950/80 text-cyan-300 border border-cyan-800/80" title="${commitFiles.length} file thay đổi (+${commitAdds} -${commitDels})">
                    ${commitFiles.length} file
                  </span>
                ` : ''}
                <button type="button" onclick="toggleCommitDiff('${role}', '${branch}', '${escapeHtml(c.hash)}', event)"
                  class="p-0.5 rounded hover:bg-white/10 text-slate-400 hover:text-white transition flex items-center justify-center cursor-pointer"
                  title="${isCommitExpanded ? 'Thu gọn chi tiết commit' : 'Xem các file thay đổi của commit này'}">
                  <svg id="commitArrow_${commitKey}" class="w-3.5 h-3.5 fill-none stroke-current transition-transform duration-200 ${isCommitExpanded ? 'rotate-180' : ''}" viewBox="0 0 24 24" stroke-width="2.5">
                    <path stroke-linecap="round" stroke-linejoin="round" d="M19 9l-7 7-7-7" />
                  </svg>
                </button>
              </div>
            </div>
            <div id="commitDetail_${commitKey}" class="${isCommitExpanded ? '' : 'hidden'} commit-detail-box p-2.5 pt-1.5 border-t border-white/5 bg-black/25 space-y-2">
              <div class="sync-commit-header text-[10.5px] font-semibold text-amber-300 flex items-center justify-between">
                <span>Các file đã sửa trong commit ${escapeHtml(c.hash)} (${commitFiles.length} file):</span>
                <span class="font-mono text-[10px] text-slate-300">+${commitAdds} / -${commitDels}</span>
              </div>
              ${commitFilesHtml}
              ${commitDiffHtml}
            </div>
          </div>
        `;
      }).join('');

      const totalFilesList = info.files || [];
      const globalDiffHtml = totalFilesList.length > 0 ? `
        <div class="pt-1.5 border-t border-amber-500/20">
          <div class="flex items-center justify-between text-[11px] text-amber-300 font-semibold cursor-pointer select-none hover:text-amber-200 py-1"
               onclick="toggleSyncPullDiff('${role}', '${branch}', event)">
            <span class="flex items-center gap-1.5">
              <svg class="w-3 h-3 text-amber-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 6h16M4 12h16M4 18h7"/>
              </svg>
              <span>Xem toàn bộ thay đổi gộp (${totalFilesList.length} file)</span>
            </span>
            <button type="button" class="p-0.5 text-amber-400 hover:text-white transition cursor-pointer"
                    title="${isExpanded ? 'Thu gọn toàn bộ thay đổi gộp' : 'Xem toàn bộ thay đổi gộp'}">
              <svg id="syncPullArrow_${syncKey}" class="w-3.5 h-3.5 fill-none stroke-current transition-transform duration-200 ${isExpanded ? 'rotate-180' : ''}" viewBox="0 0 24 24" stroke-width="2.5">
                <path stroke-linecap="round" stroke-linejoin="round" d="M19 9l-7 7-7-7" />
              </svg>
            </button>
          </div>
          <div id="syncPullDetail_${syncKey}" class="${isExpanded ? '' : 'hidden'} pt-2 space-y-2">
            <div class="space-y-1 max-h-64 overflow-y-auto pr-1">
              ${totalFilesList.map(f => `
                <div class="sync-file-item flex items-center justify-between gap-2 py-1 px-2.5 rounded bg-black/30 border border-white/5 text-[10.5px]">
                  <span class="sync-file-path truncate text-[#0958d9] dark:text-sky-300 font-mono font-medium hover:underline cursor-pointer"
                        title="Xem toàn bộ mã nguồn file: ${escapeHtml(f.path)}"
                        onclick="event.stopPropagation(); openFileEditor('${escapeHtml(f.path)}', '${escapeHtml(role)}')">
                    ${escapeHtml(f.path)}
                  </span>
                  <div class="flex items-center gap-1.5 shrink-0 font-mono">
                    <span class="text-[#73c991] font-bold">+${f.additions || 0}</span>
                    <span class="text-[#f14c4c] font-bold">-${f.deletions || 0}</span>
                    <button type="button"
                      onclick="event.stopPropagation(); openFileEditor('${escapeHtml(f.path)}', '${escapeHtml(role)}')"
                      class="sync-file-view-btn p-1 rounded hover:bg-sky-500/15 text-sky-400 hover:text-sky-300 transition flex items-center justify-center cursor-pointer"
                      title="Xem toàn bộ mã nguồn file (${escapeHtml(f.path)}) (Full code)">
                      <svg class="w-3.5 h-3.5 fill-none stroke-current" viewBox="0 0 24 24" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                        <path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z" />
                        <circle cx="12" cy="12" r="3" />
                      </svg>
                    </button>
                  </div>
                </div>
              `).join('')}
            </div>
            ${info.diff ? `
              <div class="mt-2.5">
                <div class="flex items-center justify-between text-[11px] text-amber-300 font-semibold mb-1.5 px-0.5">
                  <span class="sync-commit-header flex items-center gap-1.5">
                    <svg class="w-3.5 h-3.5 text-amber-400 shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
                      <path stroke-linecap="round" stroke-linejoin="round" d="M10 20l4-16m4 4l4 4-4 4M6 16l-4-4 4-4" />
                    </svg>
                    <span>Diff gộp tất cả commit:</span>
                  </span>
                  ${totalFilesList.length > 0 ? `
                    <button type="button"
                      onclick="event.stopPropagation(); openFileEditor('${escapeHtml(totalFilesList[0].path)}', '${escapeHtml(role)}')"
                      class="sync-diff-view-full-btn inline-flex items-center gap-1.5 px-2 py-0.5 rounded text-[10.5px] font-sans font-medium text-sky-400 hover:text-sky-300 hover:bg-sky-500/15 border border-sky-500/30 transition cursor-pointer"
                      title="Xem toàn bộ mã nguồn file (${escapeHtml(totalFilesList[0].path)}) (Full code)">
                      <svg class="w-3.5 h-3.5 fill-none stroke-current" viewBox="0 0 24 24" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                        <path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z" />
                        <circle cx="12" cy="12" r="3" />
                      </svg>
                      <span>Xem file</span>
                    </button>
                  ` : ''}
                </div>
                <div class="sync-diff-wrapper rounded-md bg-[#1e1e1e] border border-[#333333] max-h-[500px] min-h-[160px] overflow-auto text-[11.5px] font-mono leading-relaxed shadow-inner">
                  ${typeof formatDiffColoredHtml === 'function' ? formatDiffColoredHtml(info.diff) : `<pre class="text-[#d4d4d4] p-3 whitespace-pre-wrap">${escapeHtml(info.diff)}</pre>`}
                </div>
              </div>
            ` : ''}
          </div>
        </div>
      ` : '';

      boxEl.innerHTML = `
            <div class="sync-commits-box bg-[#091220] border border-amber-500/30 rounded-lg p-2.5 space-y-2 text-xs font-mono">
              <div class="flex items-center justify-between text-[11px] text-amber-300 font-semibold pb-1 border-b border-amber-500/20">
                <span class="flex items-center gap-1.5">
                  <svg class="w-3.5 h-3.5 text-amber-400 shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 14l-7 7m0 0l-7-7m7 7V3"/>
                  </svg>
                  <span>Các commit mới cần pull về:</span>
                </span>
                ${info.diff_stat ? `<span class="text-[10px] text-slate-400 font-normal truncate max-w-[280px]">${escapeHtml(info.diff_stat)}</span>` : ''}
              </div>
              <div class="space-y-1.5 max-h-[720px] overflow-y-auto pr-1">
                ${commitsHtml || '<div class="text-slate-400 text-xs py-1">Không có chi tiết commit</div>'}
              </div>
              ${globalDiffHtml}
            </div>
          `;
      boxEl.classList.remove('hidden');
    }
  } else {
    if (badgeEl) {
      badgeEl.classList.remove('hidden');
      badgeEl.innerHTML = `
            <span class="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded text-[11px] font-medium bg-emerald-950/70 text-emerald-400 border border-emerald-700/60 shadow-sm">
              <svg class="w-3.5 h-3.5 text-emerald-400 shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2.5" d="M5 13l4 4L19 7"/>
              </svg>
              <span>Đã mới nhất (0 commit)</span>
            </span>
          `;
    }

    if (btnTextEl) {
      btnTextEl.textContent = `Pull ${upperBranch}`;
    }
    if (btnEl) {
      btnEl.disabled = true;
      btnEl.classList.add('opacity-50', 'cursor-not-allowed');
      btnEl.classList.remove('ring-2', 'ring-amber-400/50');
      btnEl.title = `Nhánh origin/${branch} đã đồng bộ mới nhất (0 commit)`;
    }

    if (boxEl) {
      const latest = info.latest_commit;
      boxEl.innerHTML = `
            <div class="sync-commits-box bg-[#091220]/60 border border-emerald-700/30 rounded-lg px-2.5 py-1.5 text-xs font-mono flex items-center justify-between text-slate-300">
              <span class="flex items-center gap-1.5 text-emerald-400 text-[11px] shrink-0">
                <svg class="w-3.5 h-3.5 shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2.5" d="M5 13l4 4L19 7"/>
                </svg>
                <span>Đã đồng bộ với origin/${escapeHtml(branch)}</span>
              </span>
              ${latest ? `
                <span class="text-[10px] text-slate-400 truncate ml-2 text-right" title="${escapeHtml(latest.subject)}">
                  <span class="text-cyan-400 font-bold">${escapeHtml(latest.hash)}</span> • ${formatCommitAuthor(latest.author, latest.is_me)} (${escapeHtml(formatRelativeDate(latest.date))})
                </span>
              ` : ''}
            </div>
          `;
      boxEl.classList.remove('hidden');
    }
  }
}

let _lastSyncRemoteFetch = 0;

async function checkSyncPullUpdates(doFetch = true) {
  if (_isCheckingSync) return;
  const now = Date.now();
  if (doFetch && (now - _lastSyncRemoteFetch < 45000)) {
    doFetch = false;
  }
  _isCheckingSync = true;

  const btn = document.getElementById('btnCheckSyncUpdates');
  const spinner = document.getElementById('syncCheckSpinner');
  const icon = document.getElementById('syncCheckIcon');
  const summaryBadge = document.getElementById('syncCheckSummaryBadge');
  const timeEl = document.getElementById('syncCheckLastTime');

  if (btn) btn.disabled = true;
  if (spinner) spinner.classList.remove('hidden');
  if (icon) icon.classList.add('hidden');
  if (summaryBadge) {
    summaryBadge.textContent = 'Đang kiểm tra remote...';
    summaryBadge.className = 'text-xs font-mono px-2.5 py-0.5 rounded bg-cyan-950/70 text-cyan-300 border border-cyan-800';
  }

  try {
    const res = await fetch(`/api/git/sync-check?fetch=${doFetch ? '1' : '0'}`);
    const data = await res.json();
    if (data && data.success) {
      if (doFetch) {
        _lastSyncRemoteFetch = Date.now();
      }
      if (timeEl && data.last_checked) {
        timeEl.textContent = `(lúc ${data.last_checked})`;
      }

      if (data.fe) {
        renderBranchSyncStatus('fe', 'staging', data.fe.staging);
        renderBranchSyncStatus('fe', 'master', data.fe.master);
        renderBranchSyncStatus('fe', 'beta', data.fe.beta);
      }
      if (data.be) {
        renderBranchSyncStatus('be', 'staging', data.be.staging);
        renderBranchSyncStatus('be', 'master', data.be.master);
        renderBranchSyncStatus('be', 'beta', data.be.beta);
      }

      let totalBehind = 0;
      const needingBranches = [];
      const notifs = [];

      ['fe', 'be'].forEach(r => {
        ['staging', 'master', 'beta'].forEach(b => {
          const info = data[r] && data[r][b];
          if (info && info.needs_pull) {
            totalBehind += info.behind_count || 1;
            needingBranches.push(`${r.toUpperCase()} ${b}`);
            notifs.push({
              id: `${r}_${b}`,
              role: r,
              roleName: r === 'fe' ? 'Frontend (easysalon-webapp)' : 'Backend (easysalon-api)',
              branch: b,
              behind_count: info.behind_count || 1,
              diff_stat: info.diff_stat || '',
              latest: info.latest_commit || (info.commits && info.commits[0]) || null,
              commits: info.commits || []
            });
          }
        });
      });

      ['fe', 'be'].forEach(r => {
        ['staging', 'master', 'beta'].forEach(b => {
          const info = data[r] && data[r][b];
          if (info && !info.needs_pull) {
            _savedNotifications.forEach(n => {
              if (n.tag === 'git' && n.role === r && n.branch === b && n.status === 'pending') {
                n.status = 'completed';
                n.title = `${r.toUpperCase()} ${b}: Đã đồng bộ với remote`;
                n.desc = 'Nhánh đã đồng bộ phiên bản mới nhất từ remote.';
                _readNotifIds.add(n.id);
              }
            });
          }
        });
      });

      updateGitNotifications(notifs);

      if (summaryBadge) {
        if (totalBehind > 0) {
          summaryBadge.textContent = `Có ${totalBehind} commit mới cần pull (${needingBranches.join(', ')})`;
          summaryBadge.className = 'text-xs font-mono px-2.5 py-0.5 rounded bg-amber-500/20 text-amber-300 border border-amber-500/40 font-bold';
        } else {
          summaryBadge.textContent = 'Tất cả nhánh Staging, Master & Beta đã đồng bộ mới nhất';
          summaryBadge.className = 'text-xs font-mono px-2.5 py-0.5 rounded bg-emerald-950/70 text-emerald-300 border border-emerald-700/60 font-semibold';
        }
      }
    }
  } catch (err) {
    console.error('Lỗi khi kiểm tra sync pull:', err);
    if (summaryBadge) {
      summaryBadge.textContent = 'Lỗi kết nối kiểm tra';
      summaryBadge.className = 'text-xs font-mono px-2.5 py-0.5 rounded bg-rose-950/70 text-rose-300 border border-rose-800';
    }
  } finally {
    _isCheckingSync = false;
    if (btn) btn.disabled = false;
    if (spinner) spinner.classList.add('hidden');
    if (icon) icon.classList.remove('hidden');
  }
}
window.checkSyncPullUpdates = checkSyncPullUpdates;

async function loadPullSyncInfo() {
  try {
    const res = await fetch('/api/git/info');
    const data = await res.json();
    if (data) {
      const feBranchEl = document.getElementById('feSyncCurrBranch');
      const beBranchEl = document.getElementById('beSyncCurrBranch');
      if (feBranchEl && data.fe) feBranchEl.textContent = data.fe.current_branch || 'unknown';
      if (beBranchEl && data.be) beBranchEl.textContent = data.be.current_branch || 'unknown';
    }
  } catch (err) {
    console.error('Lỗi khi tải thông tin Pull Sync:', err);
  }
  checkSyncPullUpdates(true);
}
window.loadPullSyncInfo = loadPullSyncInfo;

async function doSyncPull(target, branch) {
  const targetLabel = target === 'both' ? 'Cả Frontend & Backend' : (target === 'fe' ? 'Frontend (easysalon-webapp)' : 'Backend (easysalon-api)');

  const isReturn = target === 'fe'
    ? (branch === 'staging' ? document.getElementById('feReturnStaging')?.checked : (branch === 'beta' ? document.getElementById('feReturnBeta')?.checked : document.getElementById('feReturnMaster')?.checked))
    : (branch === 'staging' ? document.getElementById('beReturnStaging')?.checked : (branch === 'beta' ? document.getElementById('beReturnBeta')?.checked : document.getElementById('beReturnMaster')?.checked));

  const currBranch = document.getElementById(target === 'fe' ? 'feSyncCurrBranch' : 'beSyncCurrBranch')?.textContent.trim() || '';
  let returnNote = '';
  if (isReturn && currBranch && currBranch !== branch) {
    returnNote = `\n\n(Hệ thống sẽ chuyển sang "${branch}", pull code mới nhất, sau đó tự động quay về lại nhánh "${currBranch}")`;
  } else {
    returnNote = `\n\n(Hệ thống sẽ chuyển sang "${branch}", pull code mới nhất và ở lại nhánh "${branch}")`;
  }

  const confirmed = await antdConfirm({
    title: `Xác nhận Pull ${branch.toUpperCase()}`,
    content: `Bạn có chắc muốn tự động checkout và pull nhánh "${branch}" cho ${targetLabel}?${returnNote}`,
    okText: `Pull ${branch}`
  });
  if (!confirmed) return;

  const upperRole = target === 'fe' ? 'Fe' : 'Be';
  const upperBranch = branch.charAt(0).toUpperCase() + branch.slice(1);
  const btnId = `btn${upperRole}Pull${upperBranch}`;
  const spinnerId = `${target}Pull${upperBranch}Spinner`;
  const btn = document.getElementById(btnId);
  const spinner = document.getElementById(spinnerId);

  if (btn) btn.disabled = true;
  if (spinner) spinner.classList.remove('hidden');

  showToast(`Đang checkout và pull nhánh '${branch}' cho ${targetLabel}...`);

  try {
    const res = await fetch('/api/git/sync-pull', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ target: target, branch: branch, return_to_current: !!isReturn })
    });
    const data = await res.json();

    ['fe', 'be'].forEach(role => {
      if (target !== 'both' && target !== role) return;
      const roleResult = data.results && data.results[role];
      if (!roleResult) return;

      const conflictBox = document.getElementById(role === 'fe' ? 'feSyncConflictBox' : 'beSyncConflictBox');
      const conflictFiles = document.getElementById(role === 'fe' ? 'feSyncConflictFiles' : 'beSyncConflictFiles');
      const conflictTitle = document.getElementById(role === 'fe' ? 'feSyncConflictTitle' : 'beSyncConflictTitle');
      const resultBox = document.getElementById(role === 'fe' ? 'feSyncResultBox' : 'beSyncResultBox');
      const resultOutput = document.getElementById(role === 'fe' ? 'feSyncResultOutput' : 'beSyncResultOutput');
      const resultTitle = document.getElementById(role === 'fe' ? 'feSyncResultTitle' : 'beSyncResultTitle');

      if (roleResult.conflict) {
        if (conflictBox) {
          conflictBox.classList.remove('hidden');
          mountGitConflictResolver(role, role === 'fe' ? 'feSyncConflictTerminal' : 'beSyncConflictTerminal');
        }
        if (conflictTitle) conflictTitle.textContent = `Xung đột (Conflict) khi pull nhánh '${branch}' trên ${role === 'fe' ? 'Frontend' : 'Backend'}!`;
        if (conflictFiles) {
          if (roleResult.conflicted_files && roleResult.conflicted_files.length > 0) {
            conflictFiles.innerHTML = roleResult.conflicted_files.map(f => `<div class="text-rose-300 font-mono text-[11px]">• ${escapeHtml(f)}</div>`).join('');
          } else {
            conflictFiles.textContent = roleResult.output || 'Có xung đột mã nguồn khi merge.';
          }
        }
        if (resultBox) resultBox.classList.add('hidden');
      } else if (roleResult.success) {
        if (conflictBox) conflictBox.classList.add('hidden');
        markPullSuccess(role, branch);
        if (resultBox) {
          resultBox.classList.remove('hidden');
          const finalMsg = roleResult.returned_to_initial
            ? `Đã pull thành công (${branch}) & quay về '${roleResult.final_branch}'`
            : `Đã pull thành công (${branch})`;
          if (resultTitle) {
            resultTitle.innerHTML = `<svg class="w-4 h-4 text-emerald-400 shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7"/></svg><span>${escapeHtml(finalMsg)}</span>`;
          }
          if (resultOutput) resultOutput.textContent = roleResult.output || 'Already up to date.';
        }
        if (roleResult.final_branch) {
          const currEl = document.getElementById(role === 'fe' ? 'feSyncCurrBranch' : 'beSyncCurrBranch');
          if (currEl) currEl.textContent = roleResult.final_branch;
        }
      } else {
        if (resultBox) {
          resultBox.classList.remove('hidden');
          if (resultTitle) resultTitle.textContent = `Thất bại khi pull '${branch}'`;
          if (resultOutput) resultOutput.textContent = roleResult.message || 'Lỗi không xác định.';
        }
      }
    });

    const hasUncommitted = Boolean(
      data.needs_stash ||
      (data.message && (
        data.message.includes('commit hoặc stash') ||
        data.message.includes('overwritten by checkout') ||
        data.message.includes('Please commit your changes or stash them')
      ))
    );

    if (data.conflict) {
      showToast(`Phát hiện xung đột khi pull nhánh '${branch}'!`);
      await antdAlert({
        title: 'Xảy ra xung đột (Conflict)',
        content: `Quá trình pull nhánh '${branch}' gặp xung đột mã nguồn.\n\nVui lòng kiểm tra danh sách file xung đột hiển thị trên giao diện, giải quyết và commit hoặc bấm "Hủy bỏ Merge (git merge --abort)" để quay lại an toàn.`,
        type: 'error'
      });
    } else if (data.success) {
      showToast('Đã pull thành công');
    } else if (hasUncommitted) {
      showToast('Phát hiện có thay đổi dở dang cản trở pull!');
      const action = await antdPromptStash({
        title: 'Lỗi Pull nhánh',
        content: data.message || 'Không thể chuyển sang nhánh đích do có thay đổi dở dang chưa commit/stash.',
        okText: 'Git stash nó',
        cancelText: 'Đã hiểu'
      });

      if (action === 'stash') {
        showToast('Đang thực hiện git stash để cất code dở dang...');
        try {
          const stashRes = await fetch('/api/git/stash', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ target })
          });
          const stashData = await stashRes.json();
          if (stashData.success) {
            showToast('Đã Git Stash thành công! Đang tự động thử pull lại...');
            setTimeout(() => doSyncPull(target, branch, isReturn), 600);
            return;
          } else {
            await antdAlert({
              title: 'Lỗi Git Stash',
              content: stashData.message || 'Không thể thực hiện git stash.',
              type: 'error'
            });
          }
        } catch (err) {
          showToast('Lỗi khi gọi git stash: ' + err.message);
        }
      }
    } else {
      showToast(data.message || 'Thao tác pull gặp lỗi.');
      await antdAlert({
        title: 'Lỗi Pull nhánh',
        content: data.message || 'Không thể pull nhánh.',
        type: 'error'
      });
    }

    await loadPullSyncInfo();
    if (typeof loadGitBranchInfo === 'function') loadGitBranchInfo();
    if (typeof loadCherryPickInfo === 'function') loadCherryPickInfo();
    if (activeTab === 'log' && typeof loadWorkLogs === 'function') loadWorkLogs();
  } catch (err) {
    showToast('Lỗi kết nối khi pull nhánh: ' + err.message);
  } finally {
    if (btn) btn.disabled = false;
    if (spinner) spinner.classList.add('hidden');
  }
}
window.doSyncPull = doSyncPull;

async function doAbortMerge(role) {
  const roleName = role === 'fe' ? 'Frontend' : 'Backend';
  const confirmed = await antdConfirm({
    title: 'Hủy bỏ Merge',
    content: `Bạn có chắc muốn hủy bỏ merge (git merge --abort) trên ${roleName}? Trạng thái repo sẽ được hoàn tác an toàn về trước lúc pull.`,
    okText: 'Hủy bỏ merge',
    danger: true
  });
  if (!confirmed) return;

  try {
    const res = await fetch('/api/git/merge/abort', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ target: role })
    });
    const data = await res.json();
    showToast(data.message || (data.success ? 'Đã hủy bỏ merge thành công.' : 'Lỗi khi hủy merge.'));

    const conflictBox = document.getElementById(role === 'fe' ? 'feSyncConflictBox' : 'beSyncConflictBox');
    if (conflictBox) conflictBox.classList.add('hidden');

    await loadPullSyncInfo();
    if (typeof loadGitBranchInfo === 'function') loadGitBranchInfo();
    if (typeof loadCherryPickInfo === 'function') loadCherryPickInfo();
  } catch (err) {
    showToast('Lỗi kết nối khi hủy merge: ' + err.message);
  }
}
window.doAbortMerge = doAbortMerge;

let mergeBranchState = {
  fe: { current_branch: '', selected_target: '', selected_source: '', branches: [], source_search: '', target_search: '' },
  be: { current_branch: '', selected_target: '', selected_source: '', branches: [], source_search: '', target_search: '' }
};

function toggleMergeDropdown(role, type) {
  const targetId = role === 'fe' ? (type === 'target' ? 'feMergeTargetDropdownMenu' : 'feMergeSourceDropdownMenu') : (type === 'target' ? 'beMergeTargetDropdownMenu' : 'beMergeSourceDropdownMenu');
  const menu = document.getElementById(targetId);

  ['fe', 'be'].forEach(r => {
    ['target', 'source'].forEach(t => {
      const id = r === 'fe' ? (t === 'target' ? 'feMergeTargetDropdownMenu' : 'feMergeSourceDropdownMenu') : (t === 'target' ? 'beMergeTargetDropdownMenu' : 'beMergeSourceDropdownMenu');
      if (id !== targetId) {
        const other = document.getElementById(id);
        if (other) other.classList.add('hidden');
      }
    });
  });

  if (!menu) return;
  const isHidden = menu.classList.contains('hidden');
  if (isHidden) {
    menu.classList.remove('hidden');
    const searchId = role === 'fe' ? (type === 'target' ? 'feMergeTargetSearchInput' : 'feMergeSourceSearchInput') : (type === 'target' ? 'beMergeTargetSearchInput' : 'beMergeSourceSearchInput');
    const searchInput = document.getElementById(searchId);
    if (searchInput) {
      searchInput.value = '';
      setTimeout(() => searchInput.focus(), 60);
    }
    filterMergeDropdown(role, type);
  } else {
    menu.classList.add('hidden');
  }
}
window.toggleMergeDropdown = toggleMergeDropdown;

function filterMergeDropdown(role, type) {
  const listId = role === 'fe' ? (type === 'target' ? 'feMergeTargetOptionsList' : 'feMergeSourceOptionsList') : (type === 'target' ? 'beMergeTargetOptionsList' : 'beMergeSourceOptionsList');
  const searchId = role === 'fe' ? (type === 'target' ? 'feMergeTargetSearchInput' : 'feMergeSourceSearchInput') : (type === 'target' ? 'beMergeTargetSearchInput' : 'beMergeSourceSearchInput');
  const listEl = document.getElementById(listId);
  const searchInput = document.getElementById(searchId);
  if (!listEl) return;

  const keyword = (searchInput?.value || '').toLowerCase().trim();
  const branches = mergeBranchState[role]?.branches || [];
  const currentBranch = mergeBranchState[role]?.current_branch || '';
  const selectedBranch = type === 'target' ? mergeBranchState[role]?.selected_target : mergeBranchState[role]?.selected_source;

  const filtered = branches.filter(b => b.name.toLowerCase().includes(keyword));

  if (type === 'source') {
    const countEl = document.getElementById(role === 'fe' ? 'feMergeSourceCount' : 'beMergeSourceCount');
    if (countEl) countEl.textContent = `(${filtered.length} nhánh)`;
  }

  if (filtered.length === 0) {
    listEl.innerHTML = '<div class="p-3 text-center text-slate-400 text-xs">Không tìm thấy nhánh phù hợp</div>';
    return;
  }

  listEl.innerHTML = filtered.map(b => {
    const isSelected = b.name === selectedBranch;
    const isCurrent = b.name === currentBranch;
    const activeClass = isSelected ? 'active-branch' : '';
    const currentBadge = isCurrent
      ? `<span class="text-[10px] px-1.5 py-0.5 rounded font-semibold ${role === 'fe' ? 'bg-cyan-950 text-cyan-300 border border-cyan-800' : 'bg-emerald-950 text-emerald-300 border border-emerald-800'}">Đang đứng</span>`
      : '';

    return `
      <div onclick="selectMergeBranch('${role}', '${type}', '${escapeHtml(b.name).replace(/'/g, "\\'")}')"
        class="merge-branch-opt ${activeClass} px-2.5 py-1.5 rounded transition cursor-pointer flex items-center justify-between gap-2 text-xs">
        <span class="truncate font-mono">${escapeHtml(b.name)}</span>
        ${currentBadge}
      </div>
    `;
  }).join('');
}
window.filterMergeDropdown = filterMergeDropdown;

function selectMergeBranch(role, type, branchName) {
  const menuId = role === 'fe' ? (type === 'target' ? 'feMergeTargetDropdownMenu' : 'feMergeSourceDropdownMenu') : (type === 'target' ? 'beMergeTargetDropdownMenu' : 'beMergeSourceDropdownMenu');
  const menu = document.getElementById(menuId);
  if (menu) menu.classList.add('hidden');

  if (type === 'target') {
    mergeBranchState[role].selected_target = branchName;
  } else {
    mergeBranchState[role].selected_source = branchName;
  }

  const selectId = role === 'fe' ? (type === 'target' ? 'feMergeTargetSelect' : 'feMergeSourceSelect') : (type === 'target' ? 'beMergeTargetSelect' : 'beMergeSourceSelect');
  const textId = role === 'fe' ? (type === 'target' ? 'feMergeSelectedTargetText' : 'feMergeSelectedSourceText') : (type === 'target' ? 'beMergeSelectedTargetText' : 'beMergeSelectedSourceText');

  const inputEl = document.getElementById(selectId);
  const textEl = document.getElementById(textId);
  if (inputEl) inputEl.value = branchName;
  if (textEl) textEl.textContent = branchName || 'Chọn nhánh...';
}
window.selectMergeBranch = selectMergeBranch;

function setMergeSourceToCurrent(role) {
  const current = mergeBranchState[role].current_branch;
  if (!current) return;
  selectMergeBranch(role, 'source', current);
  showToast(`Đã chọn nhánh merge là nhánh hiện tại: ${current}`);
}
window.setMergeSourceToCurrent = setMergeSourceToCurrent;

function setMergeTargetToCurrent(role) {
  const current = mergeBranchState[role].current_branch;
  if (!current) return;
  selectMergeBranch(role, 'target', current);
  showToast(`Đã chọn nhánh cần merge là nhánh hiện tại: ${current}`);
}
window.setMergeTargetToCurrent = setMergeTargetToCurrent;

async function loadMergeInfo() {
  try {
    const [infoRes, statusRes] = await Promise.all([
      fetch('/api/git/info').then(r => r.json()).catch(() => null),
      fetch('/api/git/merge/status').then(r => r.json()).catch(() => null)
    ]);

    if (infoRes) {
      ['fe', 'be'].forEach(role => {
        const roleInfo = infoRes[role];
        if (!roleInfo) return;
        mergeBranchState[role].current_branch = roleInfo.current_branch || '';
        mergeBranchState[role].branches = roleInfo.branches || [];

        const topEl = document.getElementById(role === 'fe' ? 'feMergeTopBranch' : 'beMergeTopBranch');
        if (topEl) topEl.textContent = roleInfo.current_branch || 'unknown';

        const branchNames = (roleInfo.branches || []).map(b => b.name);
        const currBranch = roleInfo.current_branch || '';
        const isBaseBranch = ['staging', 'master', 'main', 'beta'].includes(currBranch.toLowerCase());

        let defaultSource = mergeBranchState[role].selected_source;
        if (!defaultSource || !branchNames.includes(defaultSource)) {
          if (!isBaseBranch && currBranch && branchNames.includes(currBranch)) {
            defaultSource = currBranch;
          } else {
            const featureBranch = branchNames.find(n => !['staging', 'master', 'main', 'beta'].includes(n.toLowerCase()));
            defaultSource = featureBranch || (currBranch ? currBranch : branchNames[0] || '');
          }
        }
        selectMergeBranch(role, 'source', defaultSource);

        let defaultTarget = mergeBranchState[role].selected_target;
        if (!defaultTarget || !branchNames.includes(defaultTarget) || defaultTarget === defaultSource) {
          if (isBaseBranch && currBranch && defaultSource !== currBranch) {
            defaultTarget = currBranch;
          } else if (branchNames.includes('staging') && defaultSource !== 'staging') {
            defaultTarget = 'staging';
          } else if (branchNames.includes('master') && defaultSource !== 'master') {
            defaultTarget = 'master';
          } else {
            const other = branchNames.find(n => n !== defaultSource);
            defaultTarget = other || branchNames[0] || '';
          }
        }
        selectMergeBranch(role, 'target', defaultTarget);
      });
    }

    if (statusRes) {
      ['fe', 'be'].forEach(role => {
        const s = statusRes[role];
        if (!s) return;
        const conflictBox = document.getElementById(role === 'fe' ? 'feMergeConflictBox' : 'beMergeConflictBox');
        const conflictFiles = document.getElementById(role === 'fe' ? 'feMergeConflictFiles' : 'beMergeConflictFiles');
        const conflictLogText = document.getElementById(role === 'fe' ? 'feMergeConflictLogText' : 'beMergeConflictLogText');

        if (s.in_progress || s.has_conflicts) {
          if (conflictBox) {
            conflictBox.classList.remove('hidden');
            mountGitConflictResolver(role, role === 'fe' ? 'feMergeConflictTerminal' : 'beMergeConflictTerminal');
          }
          if (conflictFiles) {
            if (s.conflicted_files && s.conflicted_files.length > 0) {
              conflictFiles.innerHTML = s.conflicted_files.map(f => `
                <div class="text-amber-200 font-mono text-[11px] flex items-center justify-between gap-2 py-0.5 border-b border-amber-900/40 last:border-0">
                  <span class="flex items-center gap-1.5 truncate">
                    <span class="w-1.5 h-1.5 rounded-full bg-rose-500 shrink-0"></span>
                    <span class="text-rose-400 font-bold shrink-0">[CONFLICT]</span>
                    <span class="truncate" title="${escapeHtml(f)}">${escapeHtml(f)}</span>
                  </span>
                  <button type="button" onclick="copyToClipboard('${escapeHtml(f)}')" class="text-[10px] text-amber-400/80 hover:text-white px-1.5 py-0.5 rounded hover:bg-amber-800/40 shrink-0">Sao chép</button>
                </div>
              `).join('');
            } else {
              conflictFiles.innerHTML = '<div class="text-amber-300">Đang trong tiến trình merge chưa hoàn tất.</div>';
            }
          }
          if (conflictLogText) {
            conflictLogText.textContent = s.status_raw || s.merge_msg || 'Merge in progress. Vui lòng giải quyết xung đột.';
          }
        }
      });
    }
  } catch (err) {
    console.error('Lỗi khi tải thông tin Merge:', err);
  }
}
window.loadMergeInfo = loadMergeInfo;

function formatGitOutputVsCode(rawText) {
  if (!rawText || !rawText.trim()) {
    return '<span class="vscode-git-muted">Không có log chi tiết.</span>';
  }

  const lines = rawText.split('\n');
  const formatted = lines.map(line => {

    const diffStatMatch = line.match(/^(\s*)(.+?)\s*\|\s*(\d+)\s*([+-]*)\s*$/);
    if (diffStatMatch) {
      const indent = diffStatMatch[1];
      const filePath = escapeHtml(diffStatMatch[2]);
      const count = diffStatMatch[3];
      const signs = diffStatMatch[4];

      let signsHtml = '';
      if (signs) {
        const plusCount = (signs.match(/\+/g) || []).length;
        const minusCount = (signs.match(/-/g) || []).length;
        if (plusCount > 0) signsHtml += `<span class="vscode-git-add font-bold">${'+'.repeat(plusCount)}</span>`;
        if (minusCount > 0) signsHtml += `<span class="vscode-git-del font-bold">${'-'.repeat(minusCount)}</span>`;
      }

      return `${indent}<span class="vscode-git-file">${filePath}</span> <span class="vscode-git-pipe">|</span> <span class="vscode-git-num">${count}</span> ${signsHtml}`;
    }

    const summaryMatch = line.match(/^(\s*)(\d+\s+files?\s+changed)(?:,\s*(\d+\s+insertions?\(\+\)))?(?:,\s*(\d+\s+deletions?\(-\)))?(.*)$/);
    if (summaryMatch) {
      const indent = summaryMatch[1];
      const filesPart = `<span class="vscode-git-files font-semibold">${escapeHtml(summaryMatch[2])}</span>`;
      let insPart = '';
      let delPart = '';
      if (summaryMatch[3]) {
        insPart = `, <span class="vscode-git-add font-semibold">${escapeHtml(summaryMatch[3])}</span>`;
      }
      if (summaryMatch[4]) {
        delPart = `, <span class="vscode-git-del font-semibold">${escapeHtml(summaryMatch[4])}</span>`;
      }
      const rest = summaryMatch[5] ? escapeHtml(summaryMatch[5]) : '';
      return `${indent}${filesPart}${insPart}${delPart}${rest}`;
    }

    if (line.includes("Merge made by the '") || line.includes("Merge made by the ")) {
      return line.replace(/(Merge made by the\s+['"]?)([^'"]+)(['"]?\s+strategy\.)/g, (m, p1, p2, p3) => {
        return `<span class="vscode-git-info">${escapeHtml(p1)}</span><span class="vscode-git-strategy font-bold">${escapeHtml(p2)}</span><span class="vscode-git-info">${escapeHtml(p3)}</span>`;
      });
    }

    if (line.trim() === 'Fast-forward') {
      return `<span class="vscode-git-add font-bold">Fast-forward</span>`;
    }

    if (line.match(/^(\s*)Updating\s+([0-9a-fA-F]+)\.\.([0-9a-fA-F]+)/)) {
      return line.replace(/Updating\s+([0-9a-fA-F]+)\.\.([0-9a-fA-F]+)/, (m, h1, h2) => {
        return `<span class="vscode-git-muted">Updating </span><span class="vscode-git-hash">${h1}</span><span class="vscode-git-muted">..</span><span class="vscode-git-hash">${h2}</span>`;
      });
    }

    if (line.startsWith('Auto-merging ')) {
      return `<span class="vscode-git-keyword font-semibold">Auto-merging</span> <span class="vscode-git-file">${escapeHtml(line.slice(13))}</span>`;
    }

    if (line.includes('CONFLICT')) {
      return `<span class="vscode-git-conflict font-bold">${escapeHtml(line)}</span>`;
    }

    if (line.includes('Automatic merge failed')) {
      return `<span class="vscode-git-del font-semibold">${escapeHtml(line)}</span>`;
    }

    if (line.includes('Already up to date')) {
      return `<span class="vscode-git-add font-semibold">${escapeHtml(line)}</span>`;
    }

    return escapeHtml(line);
  });

  return formatted.join('\n');
}
window.formatGitOutputVsCode = formatGitOutputVsCode;

async function doExecuteMerge(role) {
  const roleName = role === 'fe' ? 'Frontend (easysalon-webapp)' : 'Backend (easysalon-api)';
  const sourceSelect = document.getElementById(role === 'fe' ? 'feMergeSourceSelect' : 'beMergeSourceSelect');
  const targetSelect = document.getElementById(role === 'fe' ? 'feMergeTargetSelect' : 'beMergeTargetSelect');
  const noFFCheckbox = document.getElementById(role === 'fe' ? 'feMergeNoFF' : 'beMergeNoFF');
  const returnCheckbox = document.getElementById(role === 'fe' ? 'feMergeReturnCurrent' : 'beMergeReturnCurrent');
  const commitMsgInput = document.getElementById(role === 'fe' ? 'feMergeCommitMsg' : 'beMergeCommitMsg');

  const sourceBranch = (sourceSelect?.value || '').trim();
  const targetBranch = (targetSelect?.value || '').trim();
  const noFF = !!noFFCheckbox?.checked;
  const returnCurrent = !!returnCheckbox?.checked;
  const commitMsg = (commitMsgInput?.value || '').trim();

  if (!sourceBranch) {
    showToast('Vui lòng chọn nhánh merge chứa code muốn gộp.');
    return;
  }
  if (!targetBranch) {
    showToast('Vui lòng chọn nhánh cần merge nhận code.');
    return;
  }
  if (sourceBranch === targetBranch) {
    showToast('Nhánh merge và nhánh cần merge không được trùng nhau.');
    return;
  }

  const confirmed = await antdConfirm({
    title: `Xác nhận Merge ${role === 'fe' ? 'Frontend' : 'Backend'}`,
    content: `Bạn có chắc muốn hợp nhất code:\n\n• Nhánh merge (A): "${sourceBranch}"\n• Hợp nhất vào nhánh cần merge (B): "${targetBranch}"\n\n${noFF ? '• Sử dụng tùy chọn: --no-ff\n' : ''}${returnCurrent ? '• Tự động quay về nhánh cũ sau khi merge\n' : ''}Hệ thống sẽ tự động kiểm tra và hiển thị log chi tiết bên dưới nếu xảy ra conflict.`,
    okText: 'Thực hiện Merge'
  });
  if (!confirmed) return;

  const btnId = role === 'fe' ? 'btnFeDoMerge' : 'btnBeDoMerge';
  const spinnerId = role === 'fe' ? 'feMergeSpinner' : 'beMergeSpinner';
  const btnTextId = role === 'fe' ? 'feMergeBtnText' : 'beMergeBtnText';
  const btn = document.getElementById(btnId);
  const spinner = document.getElementById(spinnerId);
  const btnText = document.getElementById(btnTextId);

  const conflictBox = document.getElementById(role === 'fe' ? 'feMergeConflictBox' : 'beMergeConflictBox');
  const conflictFiles = document.getElementById(role === 'fe' ? 'feMergeConflictFiles' : 'beMergeConflictFiles');
  const conflictLogText = document.getElementById(role === 'fe' ? 'feMergeConflictLogText' : 'beMergeConflictLogText');
  const successBox = document.getElementById(role === 'fe' ? 'feMergeSuccessBox' : 'beMergeSuccessBox');
  const successText = document.getElementById(role === 'fe' ? 'feMergeSuccessText' : 'beMergeSuccessText');
  const successLogText = document.getElementById(role === 'fe' ? 'feMergeSuccessLogText' : 'beMergeSuccessLogText');
  const errorBox = document.getElementById(role === 'fe' ? 'feMergeErrorBox' : 'beMergeErrorBox');
  const errorDetail = document.getElementById(role === 'fe' ? 'feMergeErrorDetail' : 'beMergeErrorDetail');
  const returnWrap = document.getElementById(role === 'fe' ? 'feMergeReturnBranchWrap' : 'beMergeReturnBranchWrap');

  const preMergeBranch = (mergeBranchState[role]?.current_branch || '').trim();

  if (btn) btn.disabled = true;
  if (spinner) spinner.classList.remove('hidden');
  if (btnText) btnText.textContent = `Đang merge ${sourceBranch} ➔ ${targetBranch}...`;

  if (conflictBox) conflictBox.classList.add('hidden');
  if (successBox) successBox.classList.add('hidden');
  if (errorBox) errorBox.classList.add('hidden');
  if (returnWrap) returnWrap.classList.add('hidden');

  showToast(`Đang merge nhánh '${sourceBranch}' vào '${targetBranch}' trên ${roleName}...`);

  try {
    const res = await fetch('/api/git/merge', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        target: role,
        source_branch: sourceBranch,
        target_branch: targetBranch,
        no_ff: noFF,
        return_to_current: returnCurrent,
        commit_message: commitMsg
      })
    });
    const data = await res.json();

    const initialBranch = data.initial_branch || preMergeBranch || sourceBranch;
    if (initialBranch) {
      mergeBranchState[role].previous_branch = initialBranch;
    }

    if (data.conflict) {
      if (conflictBox) {
        conflictBox.classList.remove('hidden');
        mountGitConflictResolver(role, role === 'fe' ? 'feMergeConflictTerminal' : 'beMergeConflictTerminal');
        conflictBox.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
      }
      if (conflictFiles) {
        if (data.conflicted_files && data.conflicted_files.length > 0) {
          conflictFiles.innerHTML = data.conflicted_files.map(f => `
            <div class="text-amber-200 font-mono text-[11px] flex items-center justify-between gap-2 py-0.5 border-b border-amber-900/40 last:border-0">
              <span class="flex items-center gap-1.5 truncate">
                <span class="w-1.5 h-1.5 rounded-full bg-rose-500 shrink-0"></span>
                <span class="text-rose-400 font-bold shrink-0">[CONFLICT]</span>
                <span class="truncate" title="${escapeHtml(f)}">${escapeHtml(f)}</span>
              </span>
              <button type="button" onclick="copyToClipboard('${escapeHtml(f)}')" class="text-[10px] text-amber-400/80 hover:text-white px-1.5 py-0.5 rounded hover:bg-amber-800/40 shrink-0">Sao chép</button>
            </div>
          `).join('');
        } else {
          conflictFiles.innerHTML = '<div class="text-amber-300">Có xung đột mã nguồn trong quá trình merge.</div>';
        }
      }
      if (conflictLogText) {
        conflictLogText.innerHTML = formatGitOutputVsCode(data.output || 'CONFLICT: Merge conflict in working files.');
      }
      showToast(`⚠️ Xảy ra xung đột khi merge nhánh '${sourceBranch}'!`);
      await antdAlert({
        title: 'Xảy ra xung đột (Merge Conflict)',
        content: `Quá trình merge từ nhánh "${sourceBranch}" vào "${targetBranch}" bị xung đột mã nguồn.\n\nHệ thống đã hiển thị chi tiết danh sách file bị conflict và Console Log bên dưới. Bạn có thể giải quyết conflict thủ công trong editor rồi nhấn "Đã sửa xong & Tiếp tục", hoặc nhấn "Hủy bỏ Merge (--abort)".`,
        type: 'error'
      });
    } else if (data.success) {
      if (successBox) {
        successBox.classList.remove('hidden');
        successBox.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
      }
      if (successText) {
        successText.innerHTML = `Đã hợp nhất thành công mã nguồn từ <b>${escapeHtml(sourceBranch)}</b> vào nhánh <b>${escapeHtml(targetBranch)}</b>.${data.head_commit ? ` Commit: <span class="font-mono text-cyan-300 bg-cyan-950/80 px-1.5 py-0.5 rounded border border-cyan-800 text-[11px]">${escapeHtml(data.head_commit)}</span>` : ''}`;
      }
      if (successLogText) {
        successLogText.innerHTML = formatGitOutputVsCode(data.output || 'Already up to date.');
      }
      if (data.merge_diff) {
        renderMergeDiffView(role, data.merge_diff);
      }
      const diffContainer = document.getElementById(role === 'fe' ? 'feMergeDiffContainer' : 'beMergeDiffContainer');
      if (diffContainer) diffContainer.classList.add('hidden');
      showToast(`Merge thành công nhánh '${sourceBranch}' vào '${targetBranch}'!`);
    } else {
      if (errorBox) {
        errorBox.classList.remove('hidden');
        errorBox.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
      }
      if (errorDetail) {
        errorDetail.textContent = data.message || data.output || 'Lỗi không xác định khi merge.';
      }
      showToast(data.message || 'Merge thất bại.');
      await antdAlert({
        title: 'Không thể Merge',
        content: data.message || 'Lệnh git merge thất bại. Vui lòng kiểm tra working tree và thử lại.',
        type: 'error'
      });
    }

    await loadMergeInfo();
    if (typeof loadGitBranchInfo === 'function') loadGitBranchInfo();
    if (typeof loadPullSyncInfo === 'function') loadPullSyncInfo();
    if (typeof loadCherryPickInfo === 'function') loadCherryPickInfo();
    if (activeTab === 'log' && typeof loadWorkLogs === 'function') loadWorkLogs();
  } catch (err) {
    showToast('Lỗi kết nối khi gọi lệnh merge: ' + err.message);
  } finally {
    if (btn) btn.disabled = false;
    if (spinner) spinner.classList.add('hidden');
    if (btnText) btnText.textContent = `Thực hiện Merge ${role === 'fe' ? 'Frontend' : 'Backend'}`;
  }
}
window.doExecuteMerge = doExecuteMerge;

async function doMergeAbort(role) {
  const roleName = role === 'fe' ? 'Frontend' : 'Backend';
  const confirmed = await antdConfirm({
    title: 'Hủy bỏ Merge (git merge --abort)',
    content: `Bạn có chắc muốn hủy bỏ tiến trình merge trên ${roleName}? Mọi xung đột chưa giải quyết sẽ được hoàn tác an toàn về trạng thái trước khi merge.`,
    okText: 'Hủy bỏ merge',
    danger: true
  });
  if (!confirmed) return;

  try {
    const res = await fetch('/api/git/merge/abort', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ target: role })
    });
    const data = await res.json();
    showToast(data.message || (data.success ? 'Đã hủy bỏ merge thành công.' : 'Lỗi khi hủy merge.'));

    const conflictBox = document.getElementById(role === 'fe' ? 'feMergeConflictBox' : 'beMergeConflictBox');
    if (conflictBox) conflictBox.classList.add('hidden');

    await loadMergeInfo();
    if (typeof loadGitBranchInfo === 'function') loadGitBranchInfo();
    if (typeof loadPullSyncInfo === 'function') loadPullSyncInfo();
    if (typeof loadCherryPickInfo === 'function') loadCherryPickInfo();
  } catch (err) {
    showToast('Lỗi kết nối khi hủy merge: ' + err.message);
  }
}
window.doMergeAbort = doMergeAbort;

async function doMergeContinue(role) {
  const roleName = role === 'fe' ? 'Frontend' : 'Backend';
  showToast(`Đang kiểm tra và hoàn tất merge cho ${roleName}...`);

  try {
    const res = await fetch('/api/git/merge/continue', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ target: role })
    });
    const data = await res.json();

    if (data.has_conflicts) {
      showToast(`Vẫn còn file bị xung đột chưa giải quyết!`);
      const conflictFiles = document.getElementById(role === 'fe' ? 'feMergeConflictFiles' : 'beMergeConflictFiles');
      if (conflictFiles && data.conflicted_files) {
        conflictFiles.innerHTML = data.conflicted_files.map(f => `
          <div class="text-amber-200 font-mono text-[11px] flex items-center justify-between gap-2 py-0.5 border-b border-amber-900/40 last:border-0">
            <span class="flex items-center gap-1.5 truncate">
              <span class="w-1.5 h-1.5 rounded-full bg-rose-500 shrink-0"></span>
              <span class="text-rose-400 font-bold shrink-0">[CÒN CONFLICT]</span>
              <span class="truncate" title="${escapeHtml(f)}">${escapeHtml(f)}</span>
            </span>
            <button type="button" onclick="copyToClipboard('${escapeHtml(f)}')" class="text-[10px] text-amber-400/80 hover:text-white px-1.5 py-0.5 rounded hover:bg-amber-800/40 shrink-0">Sao chép</button>
          </div>
        `).join('');
      }
      await antdAlert({
        title: 'Chưa giải quyết hết xung đột',
        content: `Vẫn còn ${data.conflicted_files?.length || 0} file đang bị xung đột.\n\nVui lòng chỉnh sửa code, xóa các conflict markers (<<<<<<, ======, >>>>>>), lưu file lại và thử lại.`,
        type: 'error'
      });
      return;
    }

    if (data.success) {
      showToast('Đã hoàn tất merge thành công!');
      const conflictBox = document.getElementById(role === 'fe' ? 'feMergeConflictBox' : 'beMergeConflictBox');
      const successBox = document.getElementById(role === 'fe' ? 'feMergeSuccessBox' : 'beMergeSuccessBox');
      const successText = document.getElementById(role === 'fe' ? 'feMergeSuccessText' : 'beMergeSuccessText');
      const successLogText = document.getElementById(role === 'fe' ? 'feMergeSuccessLogText' : 'beMergeSuccessLogText');

      if (conflictBox) conflictBox.classList.add('hidden');
      if (successBox) successBox.classList.remove('hidden');
      if (successText) successText.innerHTML = `Đã giải quyết xung đột và hoàn tất merge thành công.${data.head_commit ? ` Commit: <span class="font-mono text-cyan-300 bg-cyan-950/80 px-1.5 py-0.5 rounded border border-cyan-800 text-[11px]">${escapeHtml(data.head_commit)}</span>` : ''}`;
      if (successLogText) {
        successLogText.innerHTML = formatGitOutputVsCode(data.output || 'Merge commit created successfully.');
      }
      if (data.merge_diff) {
        renderMergeDiffView(role, data.merge_diff);
      }
      const diffContainer = document.getElementById(role === 'fe' ? 'feMergeDiffContainer' : 'beMergeDiffContainer');
      if (diffContainer) diffContainer.classList.add('hidden');

      await loadMergeInfo();
      if (typeof loadGitBranchInfo === 'function') loadGitBranchInfo();
      if (typeof loadPullSyncInfo === 'function') loadPullSyncInfo();
      if (typeof loadCherryPickInfo === 'function') loadCherryPickInfo();
    } else {
      showToast(data.message || 'Không thể tiếp tục merge.');
    }
  } catch (err) {
    showToast('Lỗi khi tiếp tục merge: ' + err.message);
  }
}
window.doMergeContinue = doMergeContinue;

async function doAbortConflictAction(role) {
  const roleName = role === 'fe' ? 'Frontend' : 'Backend';
  const confirmed = await antdConfirm({
    title: 'Trở lại trạng thái chưa merge hay cherry-pick',
    content: `Bạn có chắc muốn hủy bỏ toàn bộ xung đột và trở lại trạng thái trước khi merge/cherry-pick trên ${roleName}? Hệ thống sẽ tự động thực hiện git merge --abort hoặc git cherry-pick --abort an toàn trong background.`,
    okText: 'Trở lại trạng thái trước',
    danger: true
  });
  if (!confirmed) return;

  try {
    const res = await fetch('/api/git/conflict/abort', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ role })
    });
    const data = await res.json();
    showToast(data.message || (data.success ? 'Đã trở lại trạng thái trước khi merge/cherry-pick thành công.' : 'Lỗi khi hủy conflict.'));

    const boxIds = [
      role === 'fe' ? 'feCherryConflictBox' : 'beCherryConflictBox',
      role === 'fe' ? 'feSyncConflictBox' : 'beSyncConflictBox',
      role === 'fe' ? 'feMergeConflictBox' : 'beMergeConflictBox'
    ];
    boxIds.forEach(id => {
      const el = document.getElementById(id);
      if (el) el.classList.add('hidden');
    });

    if (typeof loadMergeInfo === 'function') await loadMergeInfo();
    if (typeof loadGitBranchInfo === 'function') await loadGitBranchInfo();
    if (typeof loadPullSyncInfo === 'function') await loadPullSyncInfo();
    if (typeof loadCherryPickInfo === 'function') await loadCherryPickInfo();
  } catch (err) {
    showToast('Lỗi kết nối khi hủy bỏ conflict: ' + err.message);
  }
}
window.doAbortConflictAction = doAbortConflictAction;

async function mountGitConflictResolver(role, containerId) {
  const container = document.getElementById(containerId);
  if (!container) return;

  container.innerHTML = `
    <div class="bg-[#1e1e1e] border border-[#3c3c3c] rounded-md shadow-2xl overflow-hidden font-mono text-xs">
      <div class="flex items-center justify-between px-3 py-1.5 bg-[#252526] border-b border-[#3c3c3c] text-[11px] text-[#cccccc]">
        <div class="flex items-center gap-2">
          <span class="w-2.5 h-2.5 rounded-full bg-rose-500 inline-block"></span>
          <span class="font-semibold text-slate-200">VS Code Conflict Resolver</span>
          <span class="text-[10px] text-slate-400">(${role.toUpperCase()})</span>
        </div>
        <div id="${containerId}_status" class="text-[10px] text-amber-400 font-sans">Đang kiểm tra xung đột...</div>
      </div>
      <div id="${containerId}_tabs" class="flex items-center gap-1 bg-[#2d2d2d] px-2 pt-1 border-b border-[#3c3c3c] overflow-x-auto text-[11px]"></div>
      <div id="${containerId}_editor" class="p-3 bg-[#1e1e1e] max-h-80 overflow-y-auto space-y-3"></div>
    </div>
  `;

  await refreshConflictResolver(role, containerId);
}
window.mountGitConflictResolver = mountGitConflictResolver;

async function refreshConflictResolver(role, containerId, targetFile = null) {
  const container = document.getElementById(containerId);
  if (!container) return;
  const statusEl = document.getElementById(`${containerId}_status`);
  const tabsEl = document.getElementById(`${containerId}_tabs`);
  const editorEl = document.getElementById(`${containerId}_editor`);

  try {
    const res = await fetch(`/api/git/conflict/status?role=${role}`);
    const data = await res.json();
    if (!data.in_conflict && (!data.conflicted_files || data.conflicted_files.length === 0)) {
      if (statusEl) statusEl.innerHTML = '<span class="text-emerald-400 font-sans">✓ Đã giải quyết hết conflict. Auto git add hoàn tất!</span>';
      if (tabsEl) tabsEl.innerHTML = '';
      if (editorEl) editorEl.innerHTML = `
        <div class="p-4 text-center text-emerald-400 font-sans">
          <div class="text-sm font-semibold mb-1">✓ Tất cả các file xung đột đã được giải quyết!</div>
          <div class="text-xs text-slate-400">Các thay đổi đã được tự động staged (git add). Bạn có thể nhấn <strong>Đã sửa xong & Tiếp tục (--continue)</strong>.</div>
        </div>
      `;
      return;
    }

    const files = data.conflicted_files || [];
    let activeFile = targetFile || (files.length > 0 ? files[0] : null);
    if (activeFile && !files.includes(activeFile) && files.length > 0) {
      activeFile = files[0];
    }

    if (statusEl) {
      statusEl.innerHTML = `<span class="text-amber-400 font-sans">Còn ${files.length} file conflict</span>`;
    }

    if (tabsEl) {
      tabsEl.innerHTML = files.map(f => {
        const isActive = f === activeFile;
        return `
          <button type="button" onclick="refreshConflictResolver('${role}', '${containerId}', '${escapeHtml(f)}')"
            class="px-3 py-1 rounded-t flex items-center gap-1.5 cursor-pointer transition select-none ${isActive ? 'bg-[#1e1e1e] text-white border-t-2 border-cyan-400 font-semibold' : 'bg-[#2d2d2d] text-slate-400 hover:text-slate-200'}">
            <span class="w-1.5 h-1.5 rounded-full ${isActive ? 'bg-amber-400' : 'bg-slate-500'}"></span>
            <span class="truncate max-w-[150px]">${escapeHtml(f.split('/').pop())}</span>
          </button>
        `;
      }).join('');
    }

    if (!activeFile) {
      if (editorEl) editorEl.innerHTML = '<div class="text-slate-400 p-2 text-center font-sans">Không có file conflict nào được chọn.</div>';
      return;
    }

    const fRes = await fetch(`/api/git/conflict/file?role=${role}&file=${encodeURIComponent(activeFile)}`);
    const fData = await fRes.json();

    if (!fData.success) {
      if (editorEl) editorEl.innerHTML = `<div class="text-rose-400 p-2 font-sans">Lỗi tải file: ${escapeHtml(fData.message || '')}</div>`;
      return;
    }

    const blocks = fData.conflict_blocks || [];
    if (blocks.length === 0) {
      if (editorEl) editorEl.innerHTML = `
        <div class="p-3 bg-emerald-950/30 border border-emerald-800/60 rounded text-emerald-300 font-sans text-xs">
          ✓ File <strong>${escapeHtml(activeFile)}</strong> đã hết xung đột và đã được git add.
        </div>
      `;
      return;
    }

    if (editorEl) {
      editorEl.innerHTML = `
        <div class="text-[11px] text-slate-400 pb-1 mb-2 border-b border-[#333333] flex items-center justify-between font-sans">
          <span>File: <strong class="text-slate-200 font-mono">${escapeHtml(activeFile)}</strong> (${blocks.length} khối xung đột)</span>
          <div class="flex items-center gap-2">
            <button type="button" onclick="resolveConflictAction('${role}', '${containerId}', '${escapeHtml(activeFile)}', 'current', null)"
              class="px-2 py-0.5 rounded bg-cyan-900/60 hover:bg-cyan-800 text-cyan-200 text-[10px] transition cursor-pointer">Accept All Current</button>
            <button type="button" onclick="resolveConflictAction('${role}', '${containerId}', '${escapeHtml(activeFile)}', 'incoming', null)"
              class="px-2 py-0.5 rounded bg-purple-900/60 hover:bg-purple-800 text-purple-200 text-[10px] transition cursor-pointer">Accept All Incoming</button>
          </div>
        </div>
      ` + blocks.map((blk, idx) => `
        <div class="border border-[#3c3c3c] rounded bg-[#181818] overflow-hidden mb-3">
          <!-- CodeLens Action Bar -->
          <div class="flex items-center gap-2 px-3 py-1 bg-[#252526] border-b border-[#333333] text-[11px] font-sans">
            <span class="text-slate-400 font-semibold">Khối #${idx + 1}:</span>
            <button type="button" onclick="resolveConflictAction('${role}', '${containerId}', '${escapeHtml(activeFile)}', 'current', ${idx})"
              class="text-cyan-400 hover:text-cyan-300 hover:underline font-medium cursor-pointer transition">Accept Current Change</button>
            <span class="text-slate-600">|</span>
            <button type="button" onclick="resolveConflictAction('${role}', '${containerId}', '${escapeHtml(activeFile)}', 'incoming', ${idx})"
              class="text-purple-400 hover:text-purple-300 hover:underline font-medium cursor-pointer transition">Accept Incoming Change</button>
            <span class="text-slate-600">|</span>
            <button type="button" onclick="resolveConflictAction('${role}', '${containerId}', '${escapeHtml(activeFile)}', 'both', ${idx})"
              class="text-emerald-400 hover:text-emerald-300 hover:underline font-medium cursor-pointer transition">Accept Both Changes</button>
          </div>

          <!-- Diff Visualization -->
          <div class="font-mono text-xs leading-5">
            <div class="bg-cyan-950/30 border-l-4 border-cyan-500 px-3 py-1">
              <div class="text-[10px] text-cyan-400 select-none font-bold">&lt;&lt;&lt;&lt;&lt;&lt;&lt; HEAD (Current Change)</div>
              <pre class="text-slate-200 whitespace-pre-wrap">${escapeHtml(blk.current || '')}</pre>
            </div>
            <div class="bg-purple-950/30 border-l-4 border-purple-500 px-3 py-1 border-t border-dashed border-[#333333]">
              <div class="text-[10px] text-purple-400 select-none font-bold">=======</div>
              <pre class="text-slate-200 whitespace-pre-wrap">${escapeHtml(blk.incoming || '')}</pre>
              <div class="text-[10px] text-purple-400 select-none font-bold">&gt;&gt;&gt;&gt;&gt;&gt;&gt; Incoming Change</div>
            </div>
          </div>
        </div>
      `).join('');
    }
  } catch (err) {
    if (editorEl) editorEl.innerHTML = `<div class="text-rose-400 p-2 font-sans">Lỗi kết nối resolver: ${escapeHtml(err.message)}</div>`;
  }
}
window.refreshConflictResolver = refreshConflictResolver;

async function resolveConflictAction(role, containerId, filePath, action, blockIndex) {
  try {
    const res = await fetch('/api/git/conflict/resolve', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        role,
        file: filePath,
        action,
        block_index: blockIndex
      })
    });
    const d = await res.json();
    if (d.success) {
      showToast(`Đã giải quyết khối conflict [${action}] và lưu file.`);
      await refreshConflictResolver(role, containerId, filePath);
    } else {
      showToast('Lỗi giải quyết conflict: ' + (d.message || 'Không thành công'));
    }
  } catch (err) {
    showToast('Lỗi mạng khi giải quyết conflict: ' + err.message);
  }
}
window.resolveConflictAction = resolveConflictAction;

async function doMergePush(role) {
  const targetSelect = document.getElementById(role === 'fe' ? 'feMergeTargetSelect' : 'beMergeTargetSelect');
  const targetBranch = (targetSelect?.value || '').trim() || mergeBranchState[role].current_branch;
  if (!targetBranch) {
    showToast('Không xác định được nhánh đích để push.');
    return;
  }

  const confirmed = await antdConfirm({
    title: `Push code nhánh ${targetBranch}`,
    content: `Bạn có chắc muốn đẩy (git push) nhánh "${targetBranch}" lên remote repository của ${role === 'fe' ? 'Frontend' : 'Backend'}?`,
    okText: 'Push code'
  });
  if (!confirmed) return;

  const btnId = role === 'fe' ? 'btnFeMergePush' : 'btnBeMergePush';
  const btn = document.getElementById(btnId);
  if (btn) btn.disabled = true;

  showToast(`Đang push nhánh '${targetBranch}' lên remote...`);

  try {
    const res = await fetch('/api/git/push', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ target: role, branch: targetBranch })
    });
    const data = await res.json();
    if (data.success) {
      showToast(`Đã push nhánh '${targetBranch}' thành công lên remote!`);

      const prevBranch = (mergeBranchState[role]?.previous_branch || mergeBranchState[role]?.source_branch || '').trim();
      if (prevBranch && prevBranch !== targetBranch) {
        showToast(`Đang tự động chuyển về lại nhánh '${prevBranch}'...`);
        try {
          const coRes = await fetch('/api/git/checkout', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ target: role, branch: prevBranch, create_new: false })
          });
          const coData = await coRes.json();
          if (coData.success) {
            showToast(`Đã tự động quay về nhánh '${prevBranch}' thành công!`);
          } else {
            showToast(`Đã push thành công nhưng không thể quay về nhánh cũ: ${coData.message}`, 'warning');
          }
        } catch (coErr) {
          showToast(`Lỗi khi quay về nhánh cũ: ${coErr.message}`, 'error');
        }
      }

      // Đóng UI Merge Success Box
      const successBox = document.getElementById(role === 'fe' ? 'feMergeSuccessBox' : 'beMergeSuccessBox');
      if (successBox) successBox.classList.add('hidden');
      const diffContainer = document.getElementById(role === 'fe' ? 'feMergeDiffContainer' : 'beMergeDiffContainer');
      if (diffContainer) diffContainer.classList.add('hidden');
      if (window.lastMergeDiff) window.lastMergeDiff[role] = null;
      const returnWrap = document.getElementById(role === 'fe' ? 'feMergeReturnBranchWrap' : 'beMergeReturnBranchWrap');
      if (returnWrap) returnWrap.classList.add('hidden');

      await loadMergeInfo();
      if (typeof loadGitBranchInfo === 'function') loadGitBranchInfo();
      if (typeof loadPullSyncInfo === 'function') loadPullSyncInfo();
    } else {
      showToast(`Push thất bại: ${data.message || 'Lỗi không xác định.'}`);
      await antdAlert({
        title: 'Push thất bại',
        content: data.message || 'Không thể push code lên remote.',
        type: 'error'
      });
    }
  } catch (err) {
    showToast('Lỗi kết nối khi push: ' + err.message);
  } finally {
    if (btn) btn.disabled = false;
  }
}
window.doMergePush = doMergePush;

async function doReturnToPrevBranch(role) {
  const prevBranch = (mergeBranchState[role]?.previous_branch || mergeBranchState[role]?.source_branch || '').trim();
  if (!prevBranch) {
    showToast('Không tìm thấy thông tin nhánh lúc nãy để quay về.');
    return;
  }
  const roleName = role === 'fe' ? 'Frontend' : 'Backend';
  const confirmed = await antdConfirm({
    title: `Quay về lại nhánh lúc nãy (${prevBranch})`,
    content: `Bạn có muốn checkout quay lại nhánh cũ "${prevBranch}" trên ${roleName}?`,
    okText: 'Quay về nhánh'
  });
  if (!confirmed) return;

  const btn = document.getElementById(role === 'fe' ? 'btnFeReturnPrevBranch' : 'btnBeReturnPrevBranch');
  if (btn) btn.disabled = true;

  showToast(`Đang chuyển về nhánh '${prevBranch}'...`);

  try {
    const res = await fetch('/api/git/checkout', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ target: role, branch: prevBranch, create_new: false })
    });
    const data = await res.json();
    if (data.success) {
      showToast(`Đã quay về nhánh '${prevBranch}' thành công!`);
      const successBox = document.getElementById(role === 'fe' ? 'feMergeSuccessBox' : 'beMergeSuccessBox');
      if (successBox) successBox.classList.add('hidden');
      const returnWrap = document.getElementById(role === 'fe' ? 'feMergeReturnBranchWrap' : 'beMergeReturnBranchWrap');
      if (returnWrap) returnWrap.classList.add('hidden');
      await loadMergeInfo();
      if (typeof loadGitBranchInfo === 'function') loadGitBranchInfo();
      if (typeof loadPullSyncInfo === 'function') loadPullSyncInfo();
    } else {
      showToast(`Không thể quay về nhánh: ${data.message || 'Lỗi checkout.'}`);
    }
  } catch (err) {
    showToast('Lỗi khi checkout nhánh: ' + err.message);
  } finally {
    if (btn) btn.disabled = false;
  }
}
window.doReturnToPrevBranch = doReturnToPrevBranch;

window.lastMergeDiff = { fe: null, be: null };

function renderMergeDiffView(role, diffData) {
  if (!diffData) return;
  if (!window.lastMergeDiff) window.lastMergeDiff = { fe: null, be: null };
  window.lastMergeDiff[role] = diffData;

  const statEl = document.getElementById(role === 'fe' ? 'feMergeDiffStat' : 'beMergeDiffStat');
  const filesEl = document.getElementById(role === 'fe' ? 'feMergeDiffFiles' : 'beMergeDiffFiles');
  const bodyEl = document.getElementById(role === 'fe' ? 'feMergeDiffBody' : 'beMergeDiffBody');

  if (statEl) {
    statEl.textContent = diffData.diff_stat || (diffData.files?.length ? `${diffData.files.length} file thay đổi` : '');
  }

  if (filesEl) {
    const files = diffData.files || [];
    if (files.length > 0) {
      filesEl.innerHTML = files.map(f => `
        <button type="button" onclick="openFileEditor('${escapeHtml(f.path)}', '${escapeHtml(role)}')"
          class="inline-flex items-center gap-1.5 px-2 py-0.5 rounded text-[10.5px] font-mono bg-white/5 hover:bg-white/10 text-slate-300 border border-white/10 hover:border-sky-500/50 transition cursor-pointer"
          title="Nhấp để xem file trong Editor (${escapeHtml(f.path)})">
          <span class="truncate max-w-[220px] text-sky-300 font-sans font-medium">${escapeHtml(f.path)}</span>
          <span class="text-emerald-400 font-semibold font-mono">+${f.adds}</span>
          <span class="text-rose-400 font-semibold font-mono">-${f.dels}</span>
        </button>
      `).join('');
    } else {
      filesEl.innerHTML = '<span class="text-[11px] text-slate-400 font-sans italic">Không có file thay đổi riêng</span>';
    }
  }

  if (bodyEl) {
    if (diffData.diff && diffData.diff.trim()) {
      bodyEl.innerHTML = typeof formatDiffColoredHtml === 'function'
        ? formatDiffColoredHtml(diffData.diff)
        : `<pre class="text-[#d4d4d4] p-3 whitespace-pre-wrap">${escapeHtml(diffData.diff)}</pre>`;
    } else {
      bodyEl.innerHTML = '<div class="text-slate-400 text-xs p-4 text-center font-sans">Không có thay đổi mã nguồn mới (Already up to date).</div>';
    }
  }
}
window.renderMergeDiffView = renderMergeDiffView;

async function toggleMergeDiffView(role) {
  const container = document.getElementById(role === 'fe' ? 'feMergeDiffContainer' : 'beMergeDiffContainer');
  if (!container) return;

  const isHidden = container.classList.contains('hidden');
  if (!isHidden) {
    container.classList.add('hidden');
    return;
  }

  container.classList.remove('hidden');

  if (!window.lastMergeDiff || !window.lastMergeDiff[role]) {
    const bodyEl = document.getElementById(role === 'fe' ? 'feMergeDiffBody' : 'beMergeDiffBody');
    if (bodyEl) {
      bodyEl.innerHTML = '<div class="p-4 text-center text-slate-400 text-xs font-sans"><div class="inline-block w-4 h-4 border-2 border-sky-400 border-t-transparent rounded-full animate-spin mr-2 align-middle"></div>Đang tải nội dung diff...</div>';
    }
    try {
      const res = await fetch(`/api/git/merge/diff?target=${role}`);
      const data = await res.json();
      if (data && data.success && data.merge_diff) {
        renderMergeDiffView(role, data.merge_diff);
      } else if (bodyEl) {
        bodyEl.innerHTML = `<div class="text-slate-400 text-xs p-4 text-center font-sans">${escapeHtml(data?.message || 'Không có dữ liệu diff cho lần merge này.')}</div>`;
      }
    } catch (err) {
      if (bodyEl) {
        bodyEl.innerHTML = `<div class="text-rose-400 text-xs p-4 text-center font-sans">Lỗi tải diff: ${escapeHtml(err.message)}</div>`;
      }
    }
  } else {
    renderMergeDiffView(role, window.lastMergeDiff[role]);
  }

  container.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
}
window.toggleMergeDiffView = toggleMergeDiffView;

function copyMergeDiff(role) {
  const diffData = window.lastMergeDiff && window.lastMergeDiff[role];
  const text = (diffData && diffData.diff) || '';
  if (!text) {
    showToast('Chưa có nội dung diff để sao chép.');
    return;
  }
  if (typeof copyToClipboard === 'function') {
    copyToClipboard(text);
    showToast('Đã sao chép nội dung diff vào clipboard!', 'success');
  }
}
window.copyMergeDiff = copyMergeDiff;
