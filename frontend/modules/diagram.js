let currentModules = DIAGRAM_MODULES;
let diagramScale = 1.0;
let diagramPanX = 0;
let diagramPanY = 0;
let isPanning = false;
let panStartX = 0;
let panStartY = 0;
let panZoomInitialized = false;

function renderDiagram() {
  initDiagramPanZoom();
  if (window._mermaidPendingCode) {
    const code = window._mermaidPendingCode;
    window._mermaidPendingCode = null;
    renderDynamicMermaid(code);
  } else if (!window.diagramData) {
    fetchDiagramData(false);
  } else {
    requestAnimationFrame(() => {
      diagramFitView();
    });
  }
}

function updateDiagramTransform() {
  const canvas = document.getElementById('diagramCanvas');
  const zoomText = document.getElementById('diagramZoomLevel');
  if (canvas) {
    canvas.style.transform = `translate(${diagramPanX}px, ${diagramPanY}px) scale(${diagramScale})`;
  }
  if (zoomText) {
    zoomText.innerText = Math.round(diagramScale * 100) + '%';
  }
}

function diagramZoomIn() {
  diagramScale = Math.min(2.5, +(diagramScale + 0.15).toFixed(2));
  updateDiagramTransform();
}

function diagramZoomOut() {
  diagramScale = Math.max(0.35, +(diagramScale - 0.15).toFixed(2));
  updateDiagramTransform();
}

function diagramZoomReset() {
  diagramScale = 1.0;
  diagramPanX = 0;
  diagramPanY = 0;
  updateDiagramTransform();
}

function diagramFitView() {
  const viewport = document.getElementById('diagramViewport');
  const canvas = document.getElementById('diagramCanvas');
  const svg = canvas ? canvas.querySelector('svg') : null;
  if (!viewport || !canvas || !svg) return;

  const vRect = viewport.getBoundingClientRect();
  const sRect = svg.getBoundingClientRect();
  const rawWidth = sRect.width / diagramScale;
  const rawHeight = sRect.height / diagramScale;

  if (rawWidth > 0 && rawHeight > 0) {
    const fitScale = Math.min(1.1, Math.max(0.4, Math.min((vRect.width - 60) / rawWidth, (vRect.height - 60) / rawHeight)));
    diagramScale = +fitScale.toFixed(2);
    diagramPanX = 0;
    diagramPanY = 0;
    updateDiagramTransform();
  }
}

function initDiagramPanZoom() {
  if (panZoomInitialized) return;
  const viewport = document.getElementById('diagramViewport');
  if (!viewport) return;
  panZoomInitialized = true;

  viewport.addEventListener('mousedown', (e) => {
    if (e.button !== 0) return;
    if (e.target.closest('.node')) return;
    isPanning = true;
    panStartX = e.clientX - diagramPanX;
    panStartY = e.clientY - diagramPanY;
    viewport.classList.add('cursor-grabbing');
    viewport.classList.remove('cursor-grab');
  });

  window.addEventListener('mousemove', (e) => {
    if (!isPanning) return;
    diagramPanX = e.clientX - panStartX;
    diagramPanY = e.clientY - panStartY;
    updateDiagramTransform();
  });

  window.addEventListener('mouseup', () => {
    if (isPanning) {
      isPanning = false;
      const vp = document.getElementById('diagramViewport');
      if (vp) {
        vp.classList.remove('cursor-grabbing');
        vp.classList.add('cursor-grab');
      }
    }
  });

  viewport.addEventListener('wheel', (e) => {
    e.preventDefault();
    const delta = e.deltaY < 0 ? 0.12 : -0.12;
    diagramScale = Math.min(2.5, Math.max(0.35, +(diagramScale + delta).toFixed(2)));
    updateDiagramTransform();
  }, { passive: false });
}

function bindMermaidNodeClicks() {
  const nodeMap = {
    'BOOKING_BEDROOM': { id: 'booking-bedroom', name: 'Phòng & Giường (BedRoom)' },
    'BED': { id: 'booking-bedroom', name: 'Phòng & Giường (BedRoom)' },
    'POS_CASHIER': { id: 'pos-cashier', name: 'Thu ngân & Hóa đơn (POS Invoice)' },
    'INV': { id: 'pos-cashier', name: 'Thu ngân & Hóa đơn (POS Invoice)' },
    'CALENDAR_SCHEDULE': { id: 'calendar-schedule', name: 'Lịch hẹn (Booking)' },
    'CUSTOMER_CRM': { id: 'customer-crm', name: 'Khách hàng (Customer CRM)' },
    'CUST': { id: 'customer-crm', name: 'Khách hàng (Customer CRM)' },
    'WAREHOUSE_INVENTORY': { id: 'warehouse-inventory', name: 'Kho hàng (Warehouse)' },
    'WH': { id: 'warehouse-inventory', name: 'Kho hàng (Warehouse)' },
    'COMMISSION_SETUP': { id: 'commission-setup', name: 'Hoa hồng (Commission)' },
    'COMM': { id: 'commission-setup', name: 'Hoa hồng (Commission)' },
    'REVENUE_EXPENDITURE': { id: 'revenue-expenditure', name: 'Thu chi & Sổ quỹ (Cashbook)' },
    'CASH': { id: 'revenue-expenditure', name: 'Thu chi & Sổ quỹ (Cashbook)' },
    'SERVICE_PACKAGE_COMBO': { id: 'service-package-combo', name: 'Gói liệu trình (Package)' },
    'PKG': { id: 'service-package-combo', name: 'Gói liệu trình (Package)' },
    'TAX_EINVOICE': { id: 'tax-einvoice', name: 'Hóa đơn điện tử (E-Invoice)' },
    'EINV': { id: 'tax-einvoice', name: 'Hóa đơn điện tử (E-Invoice)' },
    'PAYROLL_TIMESHEET': { id: 'payroll-timesheet', name: 'Chấm công & Lương (Payroll)' },
    'TIME': { id: 'payroll-timesheet', name: 'Chấm công & Lương (Payroll)' },
    'REPORT_ANALYTICS': { id: 'report-analytics', name: 'Báo cáo & Thống kê (Analytics)' },
    'REP': { id: 'report-analytics', name: 'Báo cáo & Thống kê (Analytics)' }
  };

  const svg = document.querySelector('#mermaidDiagram svg');
  if (!svg || typeof svg.querySelectorAll !== 'function') return;

  const nodes = svg.querySelectorAll('.node');
  nodes.forEach(node => {
    node.style.cursor = 'pointer';
    node.setAttribute('title', 'Nhấn để cuộn nhanh đến chi tiết module bên dưới');

    node.onclick = (e) => {
      e.stopPropagation();
      const nodeText = (node.id + ' ' + (node.textContent || '')).toUpperCase();
      let matched = null;
      let side = 'both';

      if (nodeText.includes('FE_') || nodeText.includes('FRONTEND') || nodeText.includes('BUSINESS/')) side = 'fe';
      else if (nodeText.includes('BE_') || nodeText.includes('BACKEND') || nodeText.includes('CONTROLLER')) side = 'be';

      for (const [key, val] of Object.entries(nodeMap)) {
        if (nodeText.includes(key)) {
          matched = val;
          break;
        }
      }

      if (matched) {
        highlightAndScrollToModule(matched.id, side, matched.name);
      }
    };
  });
}

function showToast(msg, type = 'info') {
  if (!msg) return;
  msg = String(msg).replace(/⚡/g, '').trim();
  let toast = document.getElementById('studioToast');
  if (!toast) {
    toast = document.createElement('div');
    toast.id = 'studioToast';
    document.body.appendChild(toast);
  }
  const isError = type === 'error' || /^(Lỗi|Thất bại|Error|Fail)/i.test(msg) || /xung đột|thất bại/i.test(msg);

  if (isError) {
    toast.className = 'fixed top-5 left-1/2 -translate-x-1/2 z-50 bg-[#dc2626] text-white border border-[#b91c1c] shadow-2xl px-4 py-2.5 rounded-lg text-xs font-medium flex items-start gap-2.5 transition-all duration-200 transform -translate-y-6 opacity-0 pointer-events-none max-w-lg';
    toast.style.backgroundColor = '#dc2626';
    toast.style.color = '#ffffff';
    toast.innerHTML = `
        <svg class="w-4 h-4 text-white shrink-0 mt-0.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
        </svg>
        <span class="whitespace-pre-line leading-relaxed text-white font-medium">${escapeHtml(msg)}</span>
      `;
  } else {
    toast.className = 'fixed top-5 left-1/2 -translate-x-1/2 z-50 bg-white text-[#0f172a] border border-slate-300 shadow-2xl px-4 py-2.5 rounded-lg text-xs font-medium flex items-start gap-2.5 transition-all duration-200 transform -translate-y-6 opacity-0 pointer-events-none max-w-lg';
    toast.style.backgroundColor = '#ffffff';
    toast.style.color = '#0f172a';
    toast.innerHTML = `
        <svg class="w-4 h-4 text-emerald-600 shrink-0 mt-0.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7" />
        </svg>
        <span class="whitespace-pre-line leading-relaxed text-[#0f172a] font-medium">${escapeHtml(msg)}</span>
      `;
  }
  toast.classList.remove('-translate-y-6', 'opacity-0');
  toast.classList.add('translate-y-0', 'opacity-100');
  clearTimeout(toast._timeout);
  toast._timeout = setTimeout(() => {
    toast.classList.remove('translate-y-0', 'opacity-100');
    toast.classList.add('-translate-y-6', 'opacity-0');
  }, 3500);
}

async function renderDynamicMermaid(code) {
  const container = document.getElementById('mermaidDiagram');
  if (!container || !code) return;
  try {
    const renderId = 'mermaid_svg_' + Date.now();
    const { svg } = await mermaid.render(renderId, code);
    container.innerHTML = svg;
    mermaidRendered = true;
    setTimeout(bindMermaidNodeClicks, 200);
    setTimeout(diagramFitView, 250);
  } catch (err) {
    console.warn('Lỗi vẽ lại Mermaid diagram:', err);
  }
}

async function doManualRescanDiagram() {
  await fetchDiagramData(true);
  showToast('Đã quét lại Source Code và cập nhật sơ đồ.');
}

async function fetchDiagramData(force = false) {
  if (window._isFetchingDiagram && !force) return;
  window._isFetchingDiagram = true;

  const spinner = document.getElementById('rescanSpinner');
  const btn = document.getElementById('btnRescanDiagram');
  if (force && spinner) spinner.classList.add('animate-spin');
  if (force && btn) btn.disabled = true;

  try {
    const res = await fetch('/api/diagram-data' + (force ? '?force=1' : ''));
    if (res.ok) {
      const data = await res.json();
      if (data && data.modules) {
        currentModules = data.modules;
        window.diagramData = data;
        renderDiagramColumns(currentModules);
        if (data.tree_nodes) {
          renderTreeView(data.tree_nodes);
        }

        const feBadge = document.getElementById('gitFeBranchBadge');
        const beBadge = document.getElementById('gitBeBranchBadge');
        const scanTime = document.getElementById('scanTimestamp');
        if (feBadge) feBadge.innerText = `${data.fe_branch} (${data.fe_commit})`;
        if (beBadge) beBadge.innerText = `${data.be_branch} (${data.be_commit})`;
        if (scanTime) scanTime.innerText = data.scanned_at || '';

        if (data.mermaid_code) {
          if (activeTab === 'diagram' || force) {
            if (!mermaidRendered || force) {
              await renderDynamicMermaid(data.mermaid_code);
            }
          } else {
            window._mermaidPendingCode = data.mermaid_code;
          }
        }
      }
    }
  } catch (err) {
    console.error('Lỗi khi nạp dữ liệu diagram:', err);
  } finally {
    window._isFetchingDiagram = false;
    if (spinner) spinner.classList.remove('animate-spin');
    if (btn) btn.disabled = false;
    setTimeout(bindMermaidNodeClicks, 300);
  }
}

function getMethodBadgeClass(m) {
  const method = String(m || '').toUpperCase().replace('HTTP', '');
  if (method === 'GET') return 'bg-blue-950/90 text-blue-400 border-blue-700/80';
  if (method === 'POST') return 'bg-emerald-950/90 text-emerald-400 border-emerald-700/80';
  if (method === 'PUT') return 'bg-amber-950/90 text-amber-400 border-amber-700/80';
  if (method === 'DELETE') return 'bg-rose-950/90 text-rose-400 border-rose-700/80';
  return 'bg-purple-950/90 text-purple-300 border-purple-700/80';
}

function renderDiagramColumns(modules = currentModules) {
  const container = document.getElementById('moduleLookupList');
  if (!container) return;

  container.innerHTML = modules.map(m => `
        <div id="module-row-${m.id}" data-skill="${escapeHtml(m.skill)}" class="bg-[#101e38] border border-[#244170] hover:border-[#38bdf8] rounded-lg p-4 shadow-sm transition duration-150">
          <!-- Header: Module title (Đã bỏ 2 nút Làm task & Fix bug) -->
          <div class="flex items-center gap-2 pb-2.5 mb-3 border-b border-[#244170]">
            <span class="w-2 h-2 rounded-full bg-cyan-400"></span>
            <h4 class="text-xs font-semibold text-white">${escapeHtml(m.title)}</h4>
          </div>

          <!-- Sub-header 3 cột chuẩn justify-between: File Resource FE | Base Route API | Controller BE -->
          <div class="diagram-flow-grid mb-2.5 text-xs">
            <div id="fe-card-${m.id}" class="diagram-col-box bg-[#0e192c] border border-[#244170] rounded px-3 py-1.5">
              <span class="text-[11px] font-semibold text-cyan-400 shrink-0">Frontend</span>
              <span class="text-[10.5px] font-mono text-cyan-300 truncate text-right" title="${escapeHtml(m.fe.resource)}">${escapeHtml(m.fe.resource)}</span>
            </div>
            <div class="diagram-flow-spacer"></div>
            <div class="diagram-col-box bg-[#0e192c] border border-[#244170] rounded px-3 py-1.5">
              <span class="text-[11px] font-semibold text-purple-300 shrink-0">API Contract</span>
              <span class="text-[10.5px] font-mono text-purple-300 bg-purple-950/80 px-2 py-0.5 rounded border border-purple-800/60 truncate text-right">${escapeHtml(m.api.route)}</span>
            </div>
            <div class="diagram-flow-spacer"></div>
            <div id="be-card-${m.id}" class="diagram-col-box bg-[#0e192c] border border-[#244170] rounded px-3 py-1.5">
              <span class="text-[11px] font-semibold text-emerald-400 shrink-0">Backend (.NET)</span>
              <span class="text-[10.5px] font-mono text-emerald-300 truncate text-right" title="${escapeHtml(m.be.controller)}">${escapeHtml(m.be.controller)}</span>
            </div>
          </div>

          <!-- Danh sách các hàng liên kết: Hàm call API ở Frontend ──► API (GET/POST/PUT/DELETE) ──► Hàm Backend -->
          <div class="space-y-2">
            ${(m.api.endpoints || []).map(ep => {
    const methodClass = getMethodBadgeClass(ep.method);
    const feFnName = ep.fe_func || 'fetchData';
    const beFnName = ep.be_action || 'ExecuteAction';
    return `
                <div class="diagram-flow-grid text-xs">
                  <!-- Cột 1: Hàm call API thực tế ở Frontend -->
                  <div class="diagram-col-box bg-[#0b1424] border border-[#1e365d] hover:border-cyan-400/70 rounded px-3 py-2 transition shadow-sm">
                    <div class="flex items-center gap-2 min-w-0">
                      <span class="w-1.5 h-1.5 rounded-full bg-cyan-400 shrink-0"></span>
                      <span class="font-mono text-xs font-bold text-cyan-300 truncate" title="Hàm call API ở Frontend: ${escapeHtml(feFnName)}()">${escapeHtml(feFnName)}()</span>
                    </div>
                    <span class="px-1.5 py-0.2 rounded text-[8.5px] font-mono font-bold border ${methodClass} shrink-0">${escapeHtml(ep.method)}</span>
                  </div>

                  <!-- Mũi tên 1: Frontend ──► API -->
                  <div class="diagram-flow-arrow" aria-hidden="true">
                    <svg class="w-full h-6 overflow-visible" viewBox="0 0 76 24" fill="none">
                      <path d="M2 12 H66" stroke="rgba(56, 189, 248, 0.2)" stroke-width="2" stroke-linecap="round" />
                      <path d="M58 6 L68 12 L58 18" stroke="rgba(56, 189, 248, 0.25)" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" />
                      <path d="M2 12 H66" stroke="url(#flowGradFeToApi)" stroke-width="2.6" stroke-linecap="round" class="arrow-stream-line" />
                      <path d="M58 6 L68 12 L58 18" stroke="url(#flowGradFeToApi)" stroke-width="2.4" stroke-linecap="round" stroke-linejoin="round" class="arrow-head-fe-api" />
                      <circle r="2.6" cy="12" fill="#38bdf8">
                        <animate attributeName="cx" from="2" to="68" dur="1.2s" repeatCount="indefinite" />
                        <animate attributeName="opacity" values="0;1;1;0" keyTimes="0;0.12;0.88;1" dur="1.2s" repeatCount="indefinite" />
                      </circle>
                    </svg>
                  </div>

                  <!-- Cột 2: API Contract (GET / POST / PUT / DELETE) -->
                  <div class="diagram-col-box bg-[#121c33] border border-purple-800/60 hover:border-purple-400/80 rounded px-3 py-2 transition shadow-sm min-w-0">
                    <div class="flex items-center gap-2 min-w-0">
                      <span class="px-1.5 py-0.2 rounded text-[9px] font-mono font-bold border ${methodClass} shrink-0">${escapeHtml(ep.method)}</span>
                      <span class="font-mono text-xs font-semibold text-slate-100 truncate" title="${escapeHtml(ep.path)}">${escapeHtml(ep.path)}</span>
                    </div>
                    <span class="text-[10px] text-slate-400 truncate hidden sm:inline shrink-0 text-right" title="${escapeHtml(ep.note)}">${escapeHtml(ep.note)}</span>
                  </div>

                  <!-- Mũi tên 2: API ──► Backend -->
                  <div class="diagram-flow-arrow" aria-hidden="true">
                    <svg class="w-full h-6 overflow-visible" viewBox="0 0 76 24" fill="none">
                      <path d="M2 12 H66" stroke="rgba(16, 185, 129, 0.2)" stroke-width="2" stroke-linecap="round" />
                      <path d="M58 6 L68 12 L58 18" stroke="rgba(16, 185, 129, 0.25)" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" />
                      <path d="M2 12 H66" stroke="url(#flowGradApiToBe)" stroke-width="2.6" stroke-linecap="round" class="arrow-stream-line" />
                      <path d="M58 6 L68 12 L58 18" stroke="url(#flowGradApiToBe)" stroke-width="2.4" stroke-linecap="round" stroke-linejoin="round" class="arrow-head-api-be" />
                      <circle r="2.6" cy="12" fill="#10b981">
                        <animate attributeName="cx" from="2" to="68" dur="1.2s" repeatCount="indefinite" />
                        <animate attributeName="opacity" values="0;1;1;0" keyTimes="0;0.12;0.88;1" dur="1.2s" repeatCount="indefinite" />
                      </circle>
                    </svg>
                  </div>

                  <!-- Cột 3: Hàm xử lý API ở Backend (.NET) -->
                  <div class="diagram-col-box bg-[#0b1424] border border-[#1e365d] hover:border-emerald-400/70 rounded px-3 py-2 transition shadow-sm">
                    <div class="flex items-center gap-2 min-w-0">
                      <span class="w-1.5 h-1.5 rounded-full bg-emerald-400 shrink-0"></span>
                      <span class="font-mono text-xs font-bold text-emerald-300 truncate" title="Hàm Backend: ${escapeHtml(beFnName)}()">${escapeHtml(beFnName)}()</span>
                    </div>
                    <span class="text-[10px] font-mono text-emerald-400/80 shrink-0">Action</span>
                  </div>
                </div>
              `;
  }).join('')}
          </div>
        </div>
      `).join('');

  filterDiagramModules();
}

function renderTreeView(treeNodes) {
  const container = document.getElementById('treeContent');
  if (!container || !treeNodes) return;

  container.innerHTML = (treeNodes || []).map(m => `
    <details id="${m.id}" class="tree-node tree-module group bg-[#101e38] border border-[#244170] rounded-lg p-3 transition" open>
      <summary class="cursor-pointer font-bold text-xs text-white flex items-center justify-between select-none">
        <span class="flex items-center gap-2">
          <span class="w-2.5 h-2.5 rounded-full bg-[#1677ff]"></span>
          <span>${escapeHtml(m.name)}</span>
        </span>
        <span class="text-[11px] text-slate-400 font-normal">Cấp 1 • Module (${(m.children || []).length} FE)</span>
      </summary>
      <div class="mt-2.5 space-y-2.5 pl-3 border-l-2 border-slate-700/50">
        ${(m.children || []).map(fe => `
          <details id="${fe.id}" class="tree-node tree-fe bg-[#0c1628] border border-[#1e3458] rounded-md p-2.5 transition" open>
            <summary class="cursor-pointer font-semibold text-xs text-slate-200 flex items-center justify-between select-none">
              <span class="flex items-center gap-2">
                <span class="w-2 h-2 rounded-full bg-[#1677ff] shrink-0"></span>
                <span>${escapeHtml(fe.name)}</span>
              </span>
              <span class="text-[10px] text-slate-400 font-normal">Cấp 2 • Frontend (${(fe.children || []).length} API)</span>
            </summary>
            <div class="mt-2 space-y-2 pl-3 border-l-2 border-slate-700/50">
              ${(fe.children || []).map(api => `
                <details id="${api.id}" class="tree-node tree-api bg-[#0c1628] border border-[#1e3458] rounded-md p-2 transition" open>
                  <summary class="cursor-pointer font-medium text-xs text-slate-300 flex items-center justify-between select-none">
                    <span class="flex items-center gap-2">
                      <span class="w-2 h-2 rounded-full bg-slate-400 shrink-0"></span>
                      <span>${escapeHtml(api.name)}</span>
                    </span>
                    <span class="text-[10px] text-slate-400 font-normal">Cấp 3 • API Contract (${(api.children || []).length} BE)</span>
                  </summary>
                  <div class="mt-2 space-y-1.5 pl-3 border-l-2 border-slate-700/50">
                    ${(api.children || []).map(be => `
                      <div id="${be.id}" class="tree-node tree-be bg-[#0c1628] border border-[#1e3458] rounded p-2 flex items-center justify-between text-xs text-slate-300">
                        <span class="flex items-center gap-2">
                          <span class="w-2 h-2 rounded-full bg-slate-400 shrink-0"></span>
                          <span>${escapeHtml(be.name)}</span>
                        </span>
                        <span class="text-[10px] text-slate-400 font-normal">Cấp 4 • BE Stack</span>
                      </div>
                    `).join('')}
                  </div>
                </details>
              `).join('')}
            </div>
          </details>
        `).join('')}
      </div>
    </details>
  `).join('');
}

function expandAllTreeNodes() {
  const container = document.getElementById('treeViewContainer');
  if (!container) return;
  const allDetails = container.querySelectorAll('details');
  allDetails.forEach(d => { d.open = true; });
}

function collapseAllTreeNodes() {
  const container = document.getElementById('treeViewContainer');
  if (!container) return;
  const allDetails = container.querySelectorAll('details');
  allDetails.forEach(d => { d.open = false; });
}

function switchDiagramViewTab(tab) {
  const flowchartWrapper = document.getElementById('diagramContainerWrapper');
  const treeWrapper = document.getElementById('treeViewContainer');
  const treeControls = document.getElementById('treeViewControls');
  const btnFlow = document.getElementById('tabBtn_flowchart');
  const btnTree = document.getElementById('tabBtn_tree');

  if (tab === 'tree') {
    if (flowchartWrapper) flowchartWrapper.classList.add('hidden');
    if (treeWrapper) treeWrapper.classList.remove('hidden');
    if (treeControls) { treeControls.classList.remove('hidden'); treeControls.classList.add('flex'); }
    if (btnTree) { btnTree.classList.add('ant-btn-primary', 'font-bold'); btnTree.classList.remove('text-slate-300'); }
    if (btnFlow) { btnFlow.classList.remove('ant-btn-primary', 'font-bold'); btnFlow.classList.add('text-slate-300'); }
    const existingDetails = document.querySelectorAll('#treeViewContainer details');
    if (existingDetails.length === 0 && window.diagramData && window.diagramData.tree_nodes) {
      renderTreeView(window.diagramData.tree_nodes);
    } else if (window.diagramData && window.diagramData.tree_nodes) {
      const openMap = {};
      existingDetails.forEach(d => { if (d.id) openMap[d.id] = d.open; });
      renderTreeView(window.diagramData.tree_nodes);
      document.querySelectorAll('#treeViewContainer details').forEach(d => {
        if (d.id && openMap[d.id] !== undefined) d.open = openMap[d.id];
      });
    }
  } else {
    if (flowchartWrapper) flowchartWrapper.classList.remove('hidden');
    if (treeWrapper) treeWrapper.classList.add('hidden');
    if (treeControls) { treeControls.classList.add('hidden'); treeControls.classList.remove('flex'); }
    if (btnFlow) { btnFlow.classList.add('ant-btn-primary', 'font-bold'); btnFlow.classList.remove('text-slate-300'); }
    if (btnTree) { btnTree.classList.remove('ant-btn-primary', 'font-bold'); btnTree.classList.add('text-slate-300'); }
  }
    }

function filterDiagramModules() {
  const query = (document.getElementById('diagramSearchInput')?.value || '').toLowerCase().trim();
  const emptyEl = document.getElementById('diagramModuleEmpty');
  const countEl = document.getElementById('diagramMatchCount');
  let matchedCount = 0;

  currentModules.forEach(m => {
    const row = document.getElementById('module-row-' + m.id);
    if (!row) return;

    if (!query) {
      row.classList.remove('hidden');
      matchedCount++;
      return;
    }

    const text = [
      m.title,
      m.skill,
      m.fe?.path,
      m.fe?.resource,
      m.fe?.desc,
      ...(m.fe?.imports || []),
      ...(m.fe?.exports || []),
      m.api?.route,
      ...(m.api?.endpoints || []).map(ep => `${ep.method} ${ep.path} ${ep.fe_func} ${ep.be_action} ${ep.note}`),
      m.be?.path,
      m.be?.controller,
      m.be?.desc,
      ...(m.be?.injections || []),
      ...(m.be?.links || []),
      ...(m.be?.exports || [])
    ].filter(Boolean).join(' ').toLowerCase();

    if (text.includes(query)) {
      row.classList.remove('hidden');
      matchedCount++;
    } else {
      row.classList.add('hidden');
    }
  });

  if (countEl) {
    countEl.textContent = `Hiển thị ${matchedCount}/${currentModules.length} modules`;
  }
  if (emptyEl) {
    if (matchedCount === 0) emptyEl.classList.remove('hidden');
    else emptyEl.classList.add('hidden');
  }
}

function highlightAndScrollToModule(moduleId, side, moduleTitle) {
  const row = document.getElementById('module-row-' + moduleId);
  const feCard = document.getElementById('fe-card-' + moduleId);
  const beCard = document.getElementById('be-card-' + moduleId);

  if (row) {
    row.scrollIntoView({ behavior: 'smooth', block: 'center' });
    row.classList.add('ring-2', 'ring-cyan-400', 'border-cyan-400', 'shadow-2xl', 'shadow-cyan-500/20');
    setTimeout(() => {
      row.classList.remove('ring-2', 'ring-cyan-400', 'border-cyan-400', 'shadow-2xl', 'shadow-cyan-500/20');
    }, 2500);

    const targetCard = side === 'fe' ? feCard : side === 'be' ? beCard : null;
    if (targetCard) {
      targetCard.classList.add('ring-2', 'ring-cyan-400', 'bg-cyan-950/30');
      setTimeout(() => {
        targetCard.classList.remove('ring-2', 'ring-cyan-400', 'bg-cyan-950/30');
      }, 2500);
    }

    showToast(`Đã định vị module: ${moduleTitle || moduleId}`);
  }
}

function quickActionTask(role, skillKey, targetName) {
  switchTab('task');
  setTaskActionType('task');
  const targetSelect = document.getElementById('taskTargetSelect');
  if (targetSelect) {
    targetSelect.value = role;
    onTaskTargetChange();
  }
  if (skillKey) {
    selectedTaskSkills = [skillKey];
    renderSkillPicker('task');
  }
  const promptInput = document.getElementById('taskPromptInput');
  if (promptInput) {
    promptInput.value = `Thực hiện nghiệp vụ cho [${targetName}] ở phía ${role.toUpperCase()}: `;
    promptInput.focus();
  }
}

function quickActionFixBug(role, skillKey, targetName) {
  switchTab('task');
  setTaskActionType('fixbug');
  const targetSelect = document.getElementById('taskTargetSelect');
  if (targetSelect) {
    targetSelect.value = role;
    onTaskTargetChange();
  }
  if (skillKey) {
    selectedTaskSkills = [skillKey];
    renderSkillPicker('task');
  }
  const promptInput = document.getElementById('taskPromptInput');
  if (promptInput) {
    promptInput.value = `Chẩn đoán và khắc phục lỗi cho [${targetName}] ở phía ${role.toUpperCase()}: `;
    promptInput.focus();
  }
  updateFixBugPromptPreview();
}
