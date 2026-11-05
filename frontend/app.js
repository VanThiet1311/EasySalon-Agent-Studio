// ============================================================
// COMMON UTILITIES & JIRA GIT BRANCH FORMATTER
// Quy tắc format nhánh Git: <type>/<initials>/<ticket-id>/<english-slug>
// Ví dụ: feat/nvt/eas-1002/log-account
// ============================================================

/**
 * Lấy tên viết tắt của người dùng (mặc định nvt - Nguyễn Văn Thiết)
 */
function getUserInitials() {
  if (window.currentUserInitials) return window.currentUserInitials;
  const email = (window.jiraStatus && window.jiraStatus.email) || '';
  const displayName = (window.jiraStatus && window.jiraStatus.user && window.jiraStatus.user.displayName) || '';

  // Ưu tiên phát hiện từ email hoặc tên
  if (email.toLowerCase().includes('thiet') || displayName.toLowerCase().includes('thiết') || displayName.toLowerCase().includes('thiet')) {
    return 'nvt';
  }

  // Tách từ lấy chữ cái đầu
  if (displayName) {
    const words = displayName.trim().split(/\s+/);
    if (words.length >= 2) {
      const inits = words.map(w => w[0].toLowerCase()).join('');
      if (inits.length >= 2 && inits.length <= 4) return inits;
    }
  }

  return 'nvt';
}
window.getUserInitials = getUserInitials;

/**
 * Xóa bỏ các tiền tố quản lý dự án (WQL, AQL, ACV, CS - Nghĩa - ..., CS-Thi- ...)
 */
function cleanJiraSummary(raw) {
  let s = (raw || '').trim();
  // Xóa tiền tố CS chăm sóc khách hàng: CS - Nghĩa - Báo cáo - ...
  s = s.replace(/^CS\s*[-_]\s*[^-_]+[-_]\s*[^-_]+[-_]\s*/gi, '');
  s = s.replace(/^CS\s*[-_]\s*[^-_]+[-_]\s*/gi, '');
  // Xóa tiền tố WQL_, AQL_, ACV_, FE_, BE_, API_...
  s = s.replace(/^(WQL|AQL|ACV|WEB|APP|API|BE|FE)[_\s-]+/gi, '');
  // Xóa ngoặc đơn ghi chú chi tiết cuối tiêu đề: (Cập nhật dropdown...)
  s = s.replace(/\([^)]*\)/g, ' ');
  // Xóa ký tự đặc biệt ở đầu và cuối
  s = s.replace(/^[-_\s:.]+|[-_\s:.]+$/g, '');
  return s.trim();
}
window.cleanJiraSummary = cleanJiraSummary;

/**
 * Từ điển cụm từ & thuật ngữ kỹ thuật / nghiệp vụ EasySalon (Tiếng Việt -> Tiếng Anh)
 */
const VIETNAMESE_ENGLISH_DICTIONARY = [
  // Cụm 4-5 từ (ưu tiên match trước)
  { vi: 'hạng khách hàng không ăn setting', en: 'customer-rank-setting-not-apply' },
  { vi: 'không tạo bill trong quá khứ', en: 'cannot-create-bill-in-past' },
  { vi: 'báo cáo năng suất làm việc', en: 'work-performance-report' },
  { vi: 'lịch sử nạp thẻ tiền mặt', en: 'cash-card-recharge-history' },
  { vi: 'báo cáo thẻ tiền mặt', en: 'cash-card-report' },
  { vi: 'báo cáo thu chi', en: 'revenue-expenditure-report' },
  { vi: 'lịch sử nạp thẻ', en: 'card-recharge-history' },
  { vi: 'năng suất làm việc', en: 'work-performance' },
  { vi: 'đăng nhập tài khoản', en: 'log-account' },
  { vi: 'đăng ký tài khoản', en: 'register-account' },
  { vi: 'quên mật khẩu', en: 'forgot-password' },
  { vi: 'đổi mật khẩu', en: 'change-password' },
  { vi: 'phân quyền tài khoản', en: 'account-permission' },
  { vi: 'sổ kế toán', en: 'accounting-book' },
  { vi: 'hạng khách hàng', en: 'customer-rank' },
  { vi: 'cài đặt hạng khách hàng', en: 'customer-rank-setting' },
  { vi: 'thẻ tiền mặt', en: 'cash-card' },
  { vi: 'tiền tip', en: 'tip-amount' },
  { vi: 'số tiền tip', en: 'tip-amount' },
  { vi: 'số tiền', en: 'amount' },
  { vi: 'số dư', en: 'balance' },
  { vi: 'số dự', en: 'balance' },
  { vi: 'ca làm việc', en: 'work-shift' },
  { vi: 'xoá ca làm việc', en: 'delete-work-shift' },
  { vi: 'xóa ca làm việc', en: 'delete-work-shift' },
  { vi: 'lịch làm việc', en: 'work-schedule' },
  { vi: 'lịch hẹn', en: 'booking' },
  { vi: 'quản lý lịch hẹn', en: 'booking-management' },
  { vi: 'chế độ xem', en: 'view-mode' },
  { vi: 'khung giờ', en: 'time-slot' },
  { vi: 'thời lượng', en: 'duration' },
  { vi: 'tổng thời gian', en: 'total-time' },
  { vi: 'gói đã mua', en: 'purchased-package' },
  { vi: 'trạng thái gói', en: 'package-status' },
  { vi: 'ngày kích hoạt', en: 'activation-date' },
  { vi: 'bỏ bắt buộc', en: 'remove-required' },
  { vi: 'bắt buộc', en: 'required' },
  { vi: 'cải tiến form', en: 'improve-form' },
  { vi: 'cải tiến', en: 'improve' },
  { vi: 'tối ưu hiển thị', en: 'optimize-display' },
  { vi: 'tối ưu', en: 'optimize' },
  { vi: 'chuyển đổi tab', en: 'switch-tab' },
  { vi: 'thanh tab', en: 'tab-bar' },
  { vi: 'xuất excel', en: 'export-excel' },
  { vi: 'nhập excel', en: 'import-excel' },
  { vi: 'in hóa đơn', en: 'print-invoice' },
  { vi: 'in hoá đơn', en: 'print-invoice' },
  { vi: 'in bill', en: 'print-bill' },
  { vi: 'tạo bill', en: 'create-bill' },
  { vi: 'hóa đơn', en: 'invoice' },
  { vi: 'hoá đơn', en: 'invoice' },
  { vi: 'đơn hàng', en: 'order' },
  { vi: 'thu ngân', en: 'cashier' },
  { vi: 'đánh giá', en: 'rating' },
  { vi: 'app quản lý', en: 'manager-app' },
  { vi: 'app quản lí', en: 'manager-app' },
  { vi: 'app chuyên viên', en: 'specialist-app' },
  { vi: 'app mobile', en: 'mobile-app' },
  { vi: 'web admin', en: 'admin-web' },
  { vi: 'khách hàng', en: 'customer' },
  { vi: 'nhân viên', en: 'employee' },
  { vi: 'chi nhánh', en: 'branch' },
  { vi: 'dịch vụ', en: 'service' },
  { vi: 'sản phẩm', en: 'product' },
  { vi: 'kho hàng', en: 'inventory' },
  { vi: 'xuất kho', en: 'export-inventory' },
  { vi: 'nhập kho', en: 'import-inventory' },
  { vi: 'cài đặt', en: 'setting' },
  { vi: 'hiển thị', en: 'display' },
  { vi: 'hiện thị', en: 'display' },
  { vi: 'lỗi khi', en: 'error' },
  { vi: 'bị lỗi', en: 'error' },
  { vi: 'lỗi', en: 'error' },
  { vi: 'không hiện', en: 'not-showing' },
  { vi: 'không nhận', en: 'not-apply' },
  { vi: 'không ăn', en: 'not-apply' },
  { vi: 'mất nhân viên', en: 'missing-staff' },
  { vi: 'bị mất', en: 'missing' },
  { vi: 'nguyên nhân', en: 'root-cause' },
  { vi: 'kiểm tra', en: 'check' },
  { vi: 'xác thực', en: 'verify' },
  { vi: 'xoá', en: 'delete' },
  { vi: 'xóa', en: 'delete' },
  { vi: 'thêm mới', en: 'create' },
  { vi: 'thêm', en: 'add' },
  { vi: 'sửa', en: 'update' },
  { vi: 'lưu', en: 'save' },
  { vi: 'gán', en: 'assign' },
  { vi: 'đã gán', en: 'assigned' },
  { vi: 'tài khoản', en: 'account' },
  { vi: 'đăng nhập', en: 'login' },
  { vi: 'đăng xuất', en: 'logout' },
  { vi: 'thanh toán', en: 'payment' },
  { vi: 'tiền mặt', en: 'cash' },
  { vi: 'chuyển khoản', en: 'bank-transfer' },
  { vi: 'giảm giá', en: 'discount' },
  { vi: 'khuyến mãi', en: 'promotion' },
  { vi: 'hoa hồng', en: 'commission' },
  { vi: 'báo cáo', en: 'report' },
  { vi: 'thu chi', en: 'revenue-expenditure' },
  { vi: 'doanh thu', en: 'revenue' },
  { vi: 'lợi nhuận', en: 'profit' },
  { vi: 'phòng', en: 'room' },
  { vi: 'giường', en: 'bed' },
  { vi: 'ghế', en: 'chair' },
  { vi: 'vị trí', en: 'position' },
  { vi: 'theo vị trí', en: 'by-position' },
  { vi: 'theo', en: 'by' },
  { vi: 'bởi', en: 'by' }
];

/**
 * Chuyển tiêu đề tiếng Việt sang slug tiếng Anh chuẩn SEO / Git branch
 */
function vietnameseToEnglishSlug(rawTitle) {
  let cleaned = cleanJiraSummary(rawTitle);
  if (!cleaned) return 'task';

  let text = cleaned.toLowerCase();

  // 1. Quét từ điển cụm từ (dài nhất trước) và thay thế bằng tiếng Anh
  const sortedDict = VIETNAMESE_ENGLISH_DICTIONARY.slice().sort((a, b) => b.vi.length - a.vi.length);
  sortedDict.forEach(item => {
    const escapedVi = item.vi.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
    const regex = new RegExp('(\\b|\\s|^)' + escapedVi + '(\\b|\\s|$)', 'gi');
    text = text.replace(regex, ` ${item.en} `);
  });

  // 2. Loại bỏ dấu tiếng Việt cho các từ còn lại
  text = text
    .normalize('NFD')
    .replace(/[\u0300-\u036f]/g, '')
    .replace(/đ/g, 'd')
    .replace(/Đ/g, 'd');

  // 3. Chuẩn hóa ký tự chỉ giữ a-z 0-9 và khoảng trắng
  text = text.replace(/[^a-z0-9\s-]/g, ' ');

  // 4. Lọc các từ dừng (stop words) không mang ý nghĩa
  const stopWords = new Set([
    'la', 'va', 'cho', 'cua', 'o', 'tai', 'tren', 'trong', 'khi', 'de', 'voi', 'duoc',
    'ben', 'nha', 'bi', 'hay', 'da', 'dang', 'nay', 'cac', 'nhung', 'giup', 'nho', 'team'
  ]);

  const tokens = text.split(/\s+/).filter(t => t && !stopWords.has(t));

  // Ghép thành kebab-case và giới hạn độ dài hợp lý
  let slug = tokens.join('-');
  slug = slug.replace(/-+/g, '-').replace(/^-+|-+$/g, '');

  if (slug.length > 40) {
    slug = slug.slice(0, 40).replace(/-[^-]*$/, '');
  }

  return slug || 'update';
}
window.vietnameseToEnglishSlug = vietnameseToEnglishSlug;

/**
 * Format tên nhánh Git theo quy tắc:
 * <type>/<initials>/<ticket-id>/<english-slug>
 * Ví dụ: feat/nvt/eas-1002/log-account
 */
function formatJiraBranchName(issue, customInitials = null) {
  if (!issue) return 'feat/nvt/eas-task/update';

  const rawType = (issue.issuetype || '').toLowerCase();
  const rawSummary = (issue.summary || '').toLowerCase();

  // Tag tính năng: fix nếu là bug, ngược lại là feat
  const isBug = rawType.includes('bug') || rawSummary.includes('lỗi') || rawSummary.includes('error') || rawSummary.includes('hotfix');
  const typeTag = isBug ? 'fix' : 'feat';

  // Tên viết tắt
  const initials = customInitials || getUserInitials();

  // ID ticket viết thường
  const ticketId = (issue.key || 'task').toLowerCase();

  // Tên nhánh tiếng Anh
  const englishSlug = vietnameseToEnglishSlug(issue.summary || '');

  return `${typeTag}/${initials}/${ticketId}/${englishSlug}`;
}
window.formatJiraBranchName = formatJiraBranchName;

/**
 * Điều hướng trực tiếp sang tab Git Control subtab checkout-branch
 * và điền sẵn tên nhánh vào #bothBranchInput
 */
function navigateToGitCheckoutBranch(branchName) {
  if (!branchName) return;

  // Điền tên nhánh vào ô input cả 2 repo
  const inputEl = document.getElementById('bothBranchInput');
  if (inputEl) {
    inputEl.value = branchName;
  }

  // Chuyển tab chính sang 'branch' (Điều khiển Git)
  if (typeof switchTab === 'function') {
    switchTab('branch');
  }

  // Chuyển subtab sang 'branch' (Tạo & Chuyển nhánh -> /git-control/checkout-branch)
  if (typeof switchGitSubTab === 'function') {
    switchGitSubTab('branch');
  }

  // Focus và highlight ô input để người dùng tiện bấm tạo nhánh
  setTimeout(() => {
    const el = document.getElementById('bothBranchInput');
    if (el) {
      el.focus();
      el.select();
      el.scrollIntoView({ behavior: 'smooth', block: 'center' });
      // Hiệu ứng nhấp nháy xanh nhẹ để người dùng dễ nhận diện
      el.classList.add('ring-2', 'ring-[#1677ff]');
      setTimeout(() => el.classList.remove('ring-2', 'ring-[#1677ff]'), 1500);
    }
  }, 120);

  if (typeof showToast === 'function') {
    showToast(`Đã tạo mẫu nhánh [${branchName}] và chuyển sang Checkout Branch!`, 'success');
  }
}
window.navigateToGitCheckoutBranch = navigateToGitCheckoutBranch;


const TABS = ['task', 'jira', 'branch', 'log', 'notes', 'diagram', 'settings'];
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


let currentStudioSettings = {
  engine: 'gemini_cli',
  effort: 'high',
  model: 'gemini-3.8-flash-high',
  opencode_model: '9router/ag/gemini-3.8-flash'
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
  if (pill) {
    if (geminiCliStatus.ready) {
      pill.textContent = 'Gemini CLI: Sẵn sàng';
      pill.className = 'engine-card-badge text-[10px] text-emerald-400 font-sans font-medium px-2 py-0.5 rounded bg-emerald-950 border border-emerald-800 uppercase';
    } else if (geminiCliStatus.installed) {
      pill.textContent = 'Gemini CLI: Chưa đăng nhập';
      pill.className = 'engine-card-badge text-[10px] text-amber-400 font-sans font-medium px-2 py-0.5 rounded bg-amber-950 border border-amber-800 uppercase';
    } else {
      pill.textContent = 'Gemini CLI: Chưa cài đặt';
      pill.className = 'engine-card-badge text-[10px] text-rose-400 font-sans font-medium px-2 py-0.5 rounded bg-rose-950 border border-rose-800 uppercase';
    }
  }
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

  const btnGemini = document.getElementById('btnPageStartGeminiCli');
  if (btnGemini) {
    if (geminiCliStatus && (geminiCliStatus.ready || geminiCliStatus.daemon_active)) {
      btnGemini.innerHTML = '<span>● Đang chạy</span>';
      btnGemini.className = 'text-[10px] font-sans font-medium px-2.5 py-1 rounded bg-emerald-700/80 text-white shadow-sm transition flex items-center gap-1 cursor-pointer';
      btnGemini.title = 'Antigravity CLI native daemon đang chạy ngầm';
    } else {
      btnGemini.innerHTML = '<span>▶ Chạy ngầm</span>';
      btnGemini.className = 'text-[10px] font-sans font-medium px-2.5 py-1 rounded bg-emerald-600 hover:bg-emerald-500 text-white shadow-sm transition flex items-center gap-1 cursor-pointer';
      btnGemini.title = 'Antigravity CLI native daemon chạy ngầm (agy remote-control start)';
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

  // 1. Tag in Panel 2 (AI Execution Engine tab)
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

  // 2. Tag in Panel 1 (Effort tab)
  const quickTag = document.getElementById('quickEngineTag');
  if (quickTag) {
    if (eng === 'opencode') {
      quickTag.textContent = 'OPENCODE (9ROUTER)';
      quickTag.className = 'text-[10px] font-sans px-2.5 py-1 rounded bg-cyan-950 text-cyan-400 border border-cyan-800 uppercase font-semibold tracking-wider';
    } else {
      quickTag.textContent = 'GEMINI CLI';
      quickTag.className = 'text-[10px] font-sans px-2.5 py-1 rounded bg-emerald-950 text-emerald-400 border border-emerald-800 uppercase font-semibold tracking-wider';
    }
  }

  // 2b. Feed Header Engine Badge (Diễn biến thực thi)
  const feedEngineBadge = document.getElementById('taskFeedEngineBadge');
  if (feedEngineBadge) {
    if (eng === 'opencode') {
      feedEngineBadge.textContent = 'OpenCode CLI';
      feedEngineBadge.className = 'text-[10px] px-2 py-0.5 rounded font-sans font-medium border bg-[#1677ff]/20 text-[#69b1ff] border-[#1677ff]/40';
      feedEngineBadge.title = 'Bộ máy thực thi hiện tại: OpenCode CLI (9router)';
    } else {
      feedEngineBadge.textContent = 'Gemini CLI';
      feedEngineBadge.className = 'text-[10px] px-2 py-0.5 rounded font-sans font-medium border bg-[#52c41a]/20 text-[#95de64] border-[#52c41a]/40';
      feedEngineBadge.title = 'Bộ máy thực thi hiện tại: Google Gemini CLI (Antigravity Native)';
    }
  }

  // 3. Status pills and texts for 9router & Gemini CLI
  const pill = document.getElementById('pageNineRouterStatusPill');
  const statusTxt = document.getElementById('pageNineRouterStatusText');
  if (pill) {
    if (nineRouterOnline) {
      pill.textContent = '9router: Online';
      pill.className = 'engine-card-badge text-[10px] text-emerald-400 font-sans font-medium px-2 py-0.5 rounded bg-emerald-950 border border-emerald-800 uppercase';
    } else {
      pill.textContent = '9router: Offline';
      pill.className = 'engine-card-badge text-[10px] text-rose-400 font-sans font-medium px-2 py-0.5 rounded bg-rose-950 border border-rose-800 uppercase';
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

  const geminiPill = document.getElementById('pageGeminiCliStatusPill');
  if (geminiPill) {
    if (geminiCliStatus.ready) {
      geminiPill.textContent = 'Gemini CLI: Sẵn sàng';
      geminiPill.className = 'engine-card-badge text-[10px] text-emerald-400 font-sans font-medium px-2 py-0.5 rounded bg-emerald-950 border border-emerald-800 uppercase';
    } else if (geminiCliStatus.installed) {
      geminiPill.textContent = 'Gemini CLI: Chưa đăng nhập';
      geminiPill.className = 'engine-card-badge text-[10px] text-amber-400 font-sans font-medium px-2 py-0.5 rounded bg-amber-950 border border-amber-800 uppercase';
    } else {
      geminiPill.textContent = 'Gemini CLI: Chưa cài đặt';
      geminiPill.className = 'engine-card-badge text-[10px] text-rose-400 font-sans font-medium px-2 py-0.5 rounded bg-rose-950 border border-rose-800 uppercase';
    }
  }

  // 4. Synchronize BOTH Panel 2 Engine Cards AND Panel 1 (Effort) Quick Engine Cards
  ['gemini_cli', 'opencode'].forEach(eid => {
    // Panel 2 Engine Cards
    const pageCard = document.getElementById('page_card_engine_' + eid);
    const pageRadio = document.querySelector(`input[name="page_engine"][value="${eid}"]`);
    if (pageCard) {
      if (eid === eng) {
        if (pageRadio) pageRadio.checked = true;
        pageCard.classList.add('is-active');
      } else {
        if (pageRadio) pageRadio.checked = false;
        pageCard.classList.remove('is-active');
      }
    }

    // Panel 1 Quick Engine Cards (Effort tab - Read-only display of currently active engine)
    const quickCard = document.getElementById('quick_card_engine_' + eid);
    const quickRadio = document.querySelector(`input[name="quick_engine"][value="${eid}"]`);
    if (quickCard) {
      if (eid === eng) {
        if (quickRadio) {
          quickRadio.checked = true;
          quickRadio.disabled = true;
        }
        quickCard.classList.add('is-active');
        quickCard.classList.remove('opacity-50', 'cursor-not-allowed');
      } else {
        if (quickRadio) {
          quickRadio.checked = false;
          quickRadio.disabled = true;
        }
        quickCard.classList.remove('is-active');
        quickCard.classList.add('opacity-50', 'cursor-not-allowed');
      }
    }
  });

  // 5. Sections visibility
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

  const quickOpencodeSec = document.getElementById('quickOpencodeSection');
  if (quickOpencodeSec) {
    if (eng === 'opencode') {
      quickOpencodeSec.classList.remove('hidden');
    } else {
      quickOpencodeSec.classList.add('hidden');
    }
  }

  // 6. Dynamic background run buttons in Panel 2
  const btnGemini = document.getElementById('btnPageStartGeminiCli');
  if (btnGemini) {
    if (geminiCliStatus && (geminiCliStatus.ready || geminiCliStatus.daemon_active)) {
      btnGemini.innerHTML = '<span>● Đang chạy</span>';
      btnGemini.className = 'text-[10px] font-sans font-medium px-2.5 py-1 rounded bg-emerald-700/80 text-white shadow-sm transition flex items-center gap-1 cursor-pointer';
      btnGemini.title = 'Antigravity CLI native daemon đang chạy ngầm';
    } else {
      btnGemini.innerHTML = '<span>▶ Chạy ngầm</span>';
      btnGemini.className = 'text-[10px] font-sans font-medium px-2.5 py-1 rounded bg-emerald-600 hover:bg-emerald-500 text-white shadow-sm transition flex items-center gap-1 cursor-pointer';
      btnGemini.title = 'Antigravity CLI native daemon chạy ngầm (agy remote-control start)';
    }
  }

  const btnNineRouter = document.getElementById('btnPageStartNineRouter');
  if (btnNineRouter) {
    if (nineRouterOnline) {
      btnNineRouter.innerHTML = '<span>● Đang chạy</span>';
      btnNineRouter.className = 'text-[10px] font-sans font-medium px-2.5 py-1 rounded bg-emerald-700/80 text-white shadow-sm transition flex items-center gap-1 cursor-pointer';
      btnNineRouter.title = '9router proxy đang chạy ngầm trên cổng 20128';
    } else {
      btnNineRouter.innerHTML = '<span>▶ Chạy ngầm</span>';
      btnNineRouter.className = 'text-[10px] font-sans font-medium px-2.5 py-1 rounded bg-emerald-600 hover:bg-emerald-500 text-white shadow-sm transition flex items-center gap-1 cursor-pointer';
      btnNineRouter.title = 'Khởi động 9router proxy chạy ngầm trên cổng 20128';
    }
  }

  if (eng === 'opencode') {
    fetchOpenCodeModels(false);
  }
  updateQuickOpencodeDisplay(currentStudioSettings.effort);
}

function onPageEngineChange(newEngine) {
  currentStudioSettings.engine = newEngine;
  updateEngineUI(newEngine, nineRouterOnline);
  renderModelSelectForCurrentEngine();
  updateEffortUI(currentStudioSettings.effort);
  markSettingsDirty(true, 'engine');
}

let _loadedOpenCodeModels = false;
let _cachedOpenCodeModels = [];

let _loadedGeminiCliModels = false;
let _cachedGeminiCliModels = [];

async function fetchGeminiCliModels(forceRefresh = false) {
  if (_loadedGeminiCliModels && !forceRefresh) return;
  try {
    const res = await fetch('/api/gemini/models');
    const data = await res.json();
    if (data && Array.isArray(data.models)) {
      _loadedGeminiCliModels = true;
      _cachedGeminiCliModels = data.models;
      if (data.current_model && !currentStudioSettings.model) {
        currentStudioSettings.model = data.current_model;
      }
      if (currentStudioSettings.engine === 'gemini_cli') {
        renderModelSelectForCurrentEngine();
      }
    }
  } catch (err) {
    console.error('Lỗi khi tải danh sách mô hình Gemini CLI:', err);
  }
}
window.fetchGeminiCliModels = fetchGeminiCliModels;

async function fetchOpenCodeModels(forceRefresh = false) {
  if (_loadedOpenCodeModels && !forceRefresh) return;
  const quickSelect = document.getElementById('quickOpencodeModelSelect');
  const pageSelect = document.getElementById('pageSettingsOpencodeModelSelect');

  if (quickSelect && (!quickSelect.options.length || quickSelect.options[0].value === '')) {
    quickSelect.innerHTML = '<option value="">Đang tải danh sách mô hình từ 9router...</option>';
  }
  if (pageSelect && (!pageSelect.options.length || pageSelect.options[0].value === '')) {
    pageSelect.innerHTML = '<option value="">Đang tải danh sách mô hình từ 9router...</option>';
  }

  try {
    const res = await fetch('/api/opencode/models');
    const data = await res.json();
    if (data && Array.isArray(data.models)) {
      _loadedOpenCodeModels = true;
      _cachedOpenCodeModels = data.models;
      if (data.nine_router_online !== undefined) {
        nineRouterOnline = !!data.nine_router_online;
        updateEngineUI(currentStudioSettings.engine, nineRouterOnline);
      }
      const modelFromServer = data.detected_model || data.current_model;
      if (modelFromServer) {
        const isFree = /free/i.test(modelFromServer);
        const cleanDetected = isFree ? modelFromServer : modelFromServer.replace(/-(low|medium|high|xhigh|max)$/i, '');
        if (cleanDetected && (!currentStudioSettings.opencode_model || cleanDetected !== currentStudioSettings.opencode_model)) {
          currentStudioSettings.opencode_model = cleanDetected;
        }
      }
      if (currentStudioSettings.engine === 'opencode') {
        renderModelSelectForCurrentEngine();
      } else {
        populateOpenCodeModelSelects(data.models);
      }
      updateQuickOpencodeDisplay(currentStudioSettings.effort);
    }
  } catch (err) {
    console.error('Lỗi khi tải danh sách mô hình OpenCode:', err);
  }
}
window.fetchOpenCodeModels = fetchOpenCodeModels;

async function refreshCurrentEngineModels() {
  if (currentStudioSettings.engine === 'opencode') {
    await fetchOpenCodeModels(true);
    showToast('Đã làm mới danh sách mô hình từ 9router proxy', 'success');
  } else {
    await fetchGeminiCliModels(true);
    showToast('Đã làm mới danh sách mô hình từ Gemini CLI', 'success');
  }
}
window.refreshCurrentEngineModels = refreshCurrentEngineModels;

function formatOpenCodeModelTitle(id, name) {
  const clean = String(id || '').replace(/^(9router|opencode)\//i, '');
  if (clean === 'ag/gemini-3.8-flash') return 'Gemini 3.8 Flash (ag/gemini-3.8-flash)';
  if (clean === 'ag/gemini-3.7-flash') return 'Gemini 3.7 Flash (ag/gemini-3.7-flash)';
  if (clean === 'ag/gemini-3.6-flash') return 'Gemini 3.6 Flash (ag/gemini-3.6-flash)';
  if (clean === 'ag/gemini-4-argon') return 'Gemini 4 Argon (ag/gemini-4-argon)';
  if (clean === 'ag/gemini-3.1-pro') return 'Gemini 3.1 Pro (ag/gemini-3.1-pro)';
  if (clean === 'ag/gemini-pro-agent') return 'Gemini Pro Agent (ag/gemini-pro-agent)';
  if (clean === 'ag/claude-sonnet-5-5') return 'Claude Sonnet 5.5 (ag/claude-sonnet-5-5)';
  if (clean === 'ag/claude-opus-5-5') return 'Claude Opus 5.5 (ag/claude-opus-5-5)';
  if (clean === 'ag/claude-sonnet-4-6') return 'Claude Sonnet 4.6 (ag/claude-sonnet-4-6)';
  if (clean === 'ag/claude-opus-4-6-thinking') return 'Claude Opus 4.6 Thinking (ag/claude-opus-4-6-thinking)';
  if (clean === 'ag/gpt-oss-120b') return 'GPT OSS 120B (ag/gpt-oss-120b)';
  if (clean === 'mmf/mimo-auto') return 'Mimo Auto (mmf/mimo-auto)';
  if (clean === 'oc/deepseek-v4.1-flash-free') return 'DeepSeek v4.1 Flash Free (oc/deepseek-v4.1-flash-free)';
  if (clean === 'oc/jev-1.13-free') return 'JEV 1.13 Free (oc/jev-1.13-free)';
  return name || clean || id;
}

function populateOpenCodeModelSelects(models) {
  const quickSelect = document.getElementById('quickOpencodeModelSelect');
  const pageSelect = document.getElementById('pageSettingsOpencodeModelSelect');
  if (!quickSelect && !pageSelect) return;

  let currentVal = currentStudioSettings.opencode_model || '9router/ag/gemini-3.8-flash';
  if (!/free/i.test(currentVal)) {
    currentVal = currentVal.replace(/-(low|medium|high|xhigh|max)$/i, '');
  }
  currentStudioSettings.opencode_model = currentVal;

  const geminiModels = [];
  const claudeModels = [];
  const freeModels = [];
  const otherModels = [];
  const seenIds = new Set();
  const variantMap = {};

  (models || []).forEach(m => {
    const rawId = m.id || '';
    const isFree = /free/i.test(rawId) || Boolean(m.is_free);
    const cleanId = isFree ? rawId : rawId.replace(/-(low|medium|high|xhigh|max)$/i, '');
    if (!cleanId) return;
    if (Array.isArray(m.raw_variants) && m.raw_variants.length) {
      variantMap[cleanId] = m.raw_variants;
    }
  });
  window._openCodeVariantMap = variantMap;

  (models || []).forEach(m => {
    const rawId = m.id || '';
    const isFree = /free/i.test(rawId) || Boolean(m.is_free);
    const cleanId = isFree ? rawId : rawId.replace(/-(low|medium|high|xhigh|max)$/i, '');
    const cleanName = isFree ? (m.name || cleanId) : (m.name || cleanId).replace(/-(low|medium|high|xhigh|max)$/i, '');
    if (!cleanId || seenIds.has(cleanId)) return;
    seenIds.add(cleanId);

    const isGemini = Boolean(m.is_gemini || cleanId.toLowerCase().includes('gemini') || cleanId.toLowerCase().includes('argon')) && !isFree;
    const isClaude = cleanId.toLowerCase().includes('claude') && !isFree;

    const normModel = {
      id: cleanId,
      name: cleanName,
      is_free: isFree,
      is_gemini: isGemini,
      is_claude: isClaude
    };

    if (normModel.is_free) {
      freeModels.push(normModel);
    } else if (normModel.is_gemini) {
      geminiModels.push(normModel);
    } else if (normModel.is_claude) {
      claudeModels.push(normModel);
    } else {
      otherModels.push(normModel);
    }
  });

  const isModelSelected = (id, target) => {
    if (!id || !target) return false;
    if (id === target) return true;
    const strip = s => s.replace(/^(9router|opencode)\//i, '').replace(/-(low|medium|high|xhigh|max)$/i, '');
    return strip(id) === strip(target);
  };

  let matchedVal = currentVal;
  for (const m of [...geminiModels, ...claudeModels, ...freeModels, ...otherModels]) {
    if (isModelSelected(m.id, currentVal)) {
      matchedVal = m.id;
      break;
    }
  }

  if (matchedVal && !seenIds.has(matchedVal)) {
    const isFree = /free/i.test(matchedVal);
    const isGem = (matchedVal.toLowerCase().includes('gemini') || matchedVal.toLowerCase().includes('argon')) && !isFree;
    const isClaude = matchedVal.toLowerCase().includes('claude') && !isFree;
    const item = {
      id: matchedVal,
      name: matchedVal,
      is_free: isFree,
      is_gemini: isGem,
      is_claude: isClaude
    };
    if (isFree) {
      freeModels.unshift(item);
    } else if (isGem) {
      geminiModels.unshift(item);
    } else if (isClaude) {
      claudeModels.unshift(item);
    } else {
      otherModels.unshift(item);
    }
    seenIds.add(matchedVal);
  }
  currentStudioSettings.opencode_model = matchedVal;

  let html = '';
  if (geminiModels.length > 0) {
    html += '<optgroup label="Google Gemini qua 9router (Khuyên dùng)">';
    geminiModels.forEach(m => {
      const isSel = (m.id === matchedVal) ? 'selected' : '';
      html += `<option value="${escapeHtml(m.id)}" ${isSel}>${escapeHtml(formatOpenCodeModelTitle(m.id, m.name))}</option>`;
    });
    html += '</optgroup>';
  }
  if (claudeModels.length > 0) {
    html += '<optgroup label="Anthropic Claude qua 9router">';
    claudeModels.forEach(m => {
      const isSel = (m.id === matchedVal) ? 'selected' : '';
      html += `<option value="${escapeHtml(m.id)}" ${isSel}>${escapeHtml(formatOpenCodeModelTitle(m.id, m.name))}</option>`;
    });
    html += '</optgroup>';
  }
  if (freeModels.length > 0) {
    html += '<optgroup label="Mô hình Miễn phí / Free qua 9router">';
    freeModels.forEach(m => {
      const isSel = (m.id === matchedVal) ? 'selected' : '';
      html += `<option value="${escapeHtml(m.id)}" ${isSel}>${escapeHtml(formatOpenCodeModelTitle(m.id, m.name))}</option>`;
    });
    html += '</optgroup>';
  }
  if (otherModels.length > 0) {
    html += '<optgroup label="Các mô hình khác qua 9router">';
    otherModels.forEach(m => {
      const isSel = (m.id === matchedVal) ? 'selected' : '';
      html += `<option value="${escapeHtml(m.id)}" ${isSel}>${escapeHtml(formatOpenCodeModelTitle(m.id, m.name))}</option>`;
    });
    html += '</optgroup>';
  }

  if (quickSelect) {
    quickSelect.innerHTML = html;
    quickSelect.value = matchedVal;
  }
  if (pageSelect && currentStudioSettings.engine === 'opencode') {
    pageSelect.innerHTML = html;
    pageSelect.value = matchedVal;
  }
  updateQuickOpencodeDisplay(currentStudioSettings.effort);
}

function populateGeminiCliModelSelect(models) {
  const pageSelect = document.getElementById('pageSettingsOpencodeModelSelect');
  if (!pageSelect) return;

  const list = (Array.isArray(models) && models.length > 0) ? models : [
    { id: 'gemini-3.8-flash-high', name: 'Gemini 3.8 Flash (High)', is_gemini: true },
    { id: 'gemini-3.8-flash-medium', name: 'Gemini 3.8 Flash (Medium)', is_gemini: true },
    { id: 'gemini-3.8-flash-low', name: 'Gemini 3.8 Flash (Low)', is_gemini: true },
    { id: 'claude-sonnet-4-6', name: 'Claude Sonnet 4.6 (Thinking)', is_claude: true },
    { id: 'claude-opus-4-6-thinking', name: 'Claude Opus 4.6 (Thinking)', is_claude: true },
    { id: 'gpt-oss-120b-medium', name: 'GPT-OSS 120B (Medium)', is_openai: true }
  ];

  let currentVal = currentStudioSettings.model || 'gemini-3.8-flash-high';

  const geminiModels = [];
  const claudeModels = [];
  const otherModels = [];

  list.forEach(m => {
    const isGemini = Boolean(m.is_gemini || (m.id && m.id.toLowerCase().includes('gemini')));
    const isClaude = Boolean(m.is_claude || (m.id && m.id.toLowerCase().includes('claude')));
    if (isGemini) geminiModels.push(m);
    else if (isClaude) claudeModels.push(m);
    else otherModels.push(m);
  });

  let html = '';
  if (geminiModels.length > 0) {
    html += '<optgroup label="Google Gemini (Gemini CLI - Khuyên dùng)">';
    geminiModels.forEach(m => {
      const isSel = (m.id === currentVal) ? 'selected' : '';
      html += `<option value="${escapeHtml(m.id)}" ${isSel}>${escapeHtml(m.name || m.id)}</option>`;
    });
    html += '</optgroup>';
  }
  if (claudeModels.length > 0) {
    html += '<optgroup label="Anthropic Claude (Gemini CLI)">';
    claudeModels.forEach(m => {
      const isSel = (m.id === currentVal) ? 'selected' : '';
      html += `<option value="${escapeHtml(m.id)}" ${isSel}>${escapeHtml(m.name || m.id)}</option>`;
    });
    html += '</optgroup>';
  }
  if (otherModels.length > 0) {
    html += '<optgroup label="OpenAI & Khác (Gemini CLI)">';
    otherModels.forEach(m => {
      const isSel = (m.id === currentVal) ? 'selected' : '';
      html += `<option value="${escapeHtml(m.id)}" ${isSel}>${escapeHtml(m.name || m.id)}</option>`;
    });
    html += '</optgroup>';
  }

  pageSelect.innerHTML = html;
  pageSelect.value = currentVal;
}

function renderModelSelectForCurrentEngine() {
  const isOpencode = (currentStudioSettings.engine === 'opencode');

  const pageLabel = document.getElementById('pageModelSelectLabel');
  if (pageLabel) {
    pageLabel.textContent = 'Chọn mô hình:';
  }

  const subHeader = document.getElementById('pageModelTabSubHeader');
  if (subHeader) {
    subHeader.textContent = isOpencode
      ? 'Chọn mô hình AI kết nối qua proxy 9router nội bộ (127.0.0.1:20128) để thực thi lập trình qua OpenCode.'
      : 'Chọn mô hình AI thực thi qua Gemini CLI (Antigravity CLI).';
  }

  const epText = document.getElementById('pageModelEndpointText');
  if (epText) {
    epText.textContent = isOpencode ? '127.0.0.1:20128' : 'Gemini CLI';
  }

  const epBadge = document.getElementById('pageModelEndpointBadge');
  if (epBadge) {
    epBadge.className = isOpencode
      ? 'inline-flex items-center gap-1.5 text-[11px] font-mono px-2.5 py-1 rounded-md bg-[#0c1628] border border-[#244170] text-emerald-400 font-medium'
      : 'inline-flex items-center gap-1.5 text-[11px] font-sans px-2.5 py-1 rounded-md bg-[#0c1628] border border-[#244170] text-sky-400 font-medium';
  }

  const engineBadge = document.getElementById('activeModelEngineBadge');
  if (engineBadge) {
    engineBadge.textContent = isOpencode ? 'OpenCode (9router)' : 'Gemini CLI';
  }

  const pageHint = document.getElementById('pageModelSelectHint');
  if (pageHint) {
    pageHint.textContent = isOpencode
      ? 'Mức độ suy luận (Reasoning Effort: Low / Medium / High) sẽ tự động chuyển đổi sang biến thể mô hình tương ứng (ví dụ: ag/gemini-3.8-flash-medium) ở tab Mức độ suy luận.'
      : 'Trên Gemini CLI, cờ tham số --model và --effort (hoặc lệnh tương tác /model và /effort) sẽ được tự động áp dụng khi thực thi tác vụ.';
  }

  if (isOpencode) {
    if (_cachedOpenCodeModels && _cachedOpenCodeModels.length > 0) {
      populateOpenCodeModelSelects(_cachedOpenCodeModels);
    } else {
      fetchOpenCodeModels(false);
    }
    updateQuickOpencodeDisplay(currentStudioSettings.effort);
  } else {
    // gemini_cli
    if (_cachedGeminiCliModels && _cachedGeminiCliModels.length > 0) {
      populateGeminiCliModelSelect(_cachedGeminiCliModels);
    } else {
      populateGeminiCliModelSelect([]);
      fetchGeminiCliModels(false);
    }

    const curModel = currentStudioSettings.model || 'gemini-3.8-flash-high';
    const curEff = String(currentStudioSettings.effort || 'high').toUpperCase();

    const displayBadge = document.getElementById('activeModelDisplayBadge');
    if (displayBadge) {
      displayBadge.textContent = curModel;
    }

    const effortBadge = document.getElementById('activeModelEffortBadge');
    if (effortBadge) {
      effortBadge.textContent = `Suy luận: ${curEff}`;
      effortBadge.className = 'text-[10px] font-sans font-medium px-2.5 py-0.5 rounded bg-blue-900/60 text-blue-200 border border-blue-700/60';
    }

    const fullIdEl = document.getElementById('activeModelOpencodeFullId');
    if (fullIdEl) {
      fullIdEl.textContent = 'gemini-cli';
    }

    const descEl = document.getElementById('pageModelActiveDesc');
    if (descEl) {
      descEl.textContent = `Thực thi qua Gemini CLI (Antigravity CLI) • Cờ tham số: --model ${curModel} --effort ${currentStudioSettings.effort || 'high'} • Trong phiên tương tác: /effort ${currentStudioSettings.effort || 'high'} và /model ${curModel}`;
    }

    const masterSelect = document.getElementById('pageSettingsModelSelect');
    if (masterSelect) {
      masterSelect.value = curModel;
    }

    updateDynamicEffortPanel({ supportsEffort: true, isFree: false, baseModel: curModel });
  }
}
window.renderModelSelectForCurrentEngine = renderModelSelectForCurrentEngine;

function resolveEffectiveOpenCodeModel(baseModel, effort) {
  let raw = String(baseModel || currentStudioSettings.opencode_model || '9router/ag/gemini-3.8-flash').trim();
  const eff = String(effort || currentStudioSettings.effort || 'high').trim().toLowerCase();

  const isFree = /free/i.test(raw);
  const isAgent = /-agent$/i.test(raw);

  if (isAgent || isFree) {
    const cleanRaw = raw.replace(/-(low|medium|high|xhigh|max)$/i, '');
    return {
      effective: cleanRaw,
      supportsEffort: false,
      isFree: isFree,
      baseModel: cleanRaw
    };
  }

  const prefixMatch = raw.match(/^(9router\/|opencode\/)/i);
  const prefix = prefixMatch ? prefixMatch[0] : '';
  const rawId = prefix ? raw.slice(prefix.length) : raw;

  const baseId = rawId.replace(/-(low|medium|high|xhigh|max)$/i, '');
  const lower = baseId.toLowerCase();
  const heuristics = (lower.includes('gemini') || lower.includes('argon') || lower.includes('claude') || lower.includes('gpt-') || lower.includes('grok')) && !lower.includes('free');

  // Đối chiếu với danh sách biến thể thật do /api/opencode/models trả về (raw_variants)
  const variantMap = window._openCodeVariantMap || {};
  const variants = variantMap[prefix + baseId] || variantMap[baseId] || variantMap['9router/ag/' + baseId] || variantMap['ag/' + baseId] || null;

  let effectiveId = `${baseId}-${eff}`;
  let supportsEffort = heuristics;

  if (Array.isArray(variants) && variants.length) {
    const hasEffortVariant = variants.some(v => v !== baseId && /-(low|medium|high|xhigh|max)$/i.test(v));
    supportsEffort = heuristics || hasEffortVariant;
    if (variants.includes(`${baseId}-${eff}`)) {
      effectiveId = `${baseId}-${eff}`;
    } else if (variants.includes(`ag/${baseId}-${eff}`)) {
      effectiveId = `ag/${baseId}-${eff}`;
    } else if (variants.includes(baseId)) {
      effectiveId = supportsEffort ? `${baseId}-${eff}` : baseId;
    } else {
      effectiveId = ['high', 'medium', 'low', 'xhigh', 'max']
        .map(e => `${baseId}-${e}`)
        .find(v => variants.includes(v)) || (supportsEffort ? `${baseId}-${eff}` : baseId);
    }
  } else if (!heuristics) {
    effectiveId = baseId;
  }

  return {
    effective: prefix + effectiveId,
    supportsEffort,
    isFree: false,
    baseModel: prefix + baseId
  };
}
window.resolveEffectiveOpenCodeModel = resolveEffectiveOpenCodeModel;

function updateDynamicEffortPanel(res) {
  const titleEl = document.getElementById('pageEffortSectionTitle');
  const cardsGrid = document.getElementById('pageEffortCardsGrid');
  const noticeEl = document.getElementById('pageEffortNotSupportedNotice');
  const noticeTitle = document.getElementById('pageEffortNoticeTitle');
  const noticeDesc = document.getElementById('pageEffortNoticeDesc');

  const isOpencode = (currentStudioSettings.engine === 'opencode');

  if (isOpencode) {
    if (res && res.supportsEffort) {
      if (titleEl) {
        const isGemini = (res.baseModel || '').toLowerCase().includes('gemini') || (res.baseModel || '').toLowerCase().includes('argon');
        titleEl.textContent = isGemini ? 'Mức độ suy luận cho Gemini (OpenCode):' : `Mức độ suy luận cho ${escapeHtml(res.baseModel)}:`;
      }
      if (cardsGrid) cardsGrid.classList.remove('hidden');
      if (noticeEl) noticeEl.classList.add('hidden');
    } else {
      const modelName = (res && res.baseModel) || currentStudioSettings.opencode_model || 'Mô hình cố định';
      const isFree = (res && res.isFree) || (/free/i.test(modelName));
      if (titleEl) {
        titleEl.textContent = isFree
          ? `Mô hình Miễn phí (${modelName}): Tiêu chuẩn (Không áp dụng mức suy luận)`
          : `Mô hình tiêu chuẩn (${modelName}): Không áp dụng mức suy luận`;
      }
      if (cardsGrid) cardsGrid.classList.add('hidden');
      if (noticeEl) {
        noticeEl.classList.remove('hidden');
        if (noticeTitle) {
          noticeTitle.textContent = isFree
            ? `Mô hình Miễn phí ${modelName} (Free - Không tốn token)`
            : `Mô hình ${modelName} hoạt động ở chế độ tiêu chuẩn`;
        }
        if (noticeDesc) {
          noticeDesc.textContent = isFree
            ? `Mô hình này là mô hình miễn phí (Free model) từ OpenCode / 9router, hoạt động cố định ở mức suy luận tiêu chuẩn và không hỗ trợ chọn Low / Medium / High. Mọi tác vụ được xử lý phản hồi trực tiếp nhanh nhất.`
            : `Mô hình này hoạt động ở chế độ tiêu chuẩn mặc định, không hỗ trợ phân mức suy luận Low / Medium / High.`;
        }
      }
    }
  } else {
    // gemini_cli
    if (titleEl) titleEl.textContent = 'Mức độ suy luận cho Gemini CLI:';
    if (cardsGrid) cardsGrid.classList.remove('hidden');
    if (noticeEl) noticeEl.classList.add('hidden');
  }
}
window.updateDynamicEffortPanel = updateDynamicEffortPanel;

function updateQuickOpencodeDisplay(effort) {
  const eff = String(effort || currentStudioSettings.effort || 'high').trim().toLowerCase();
  const res = resolveEffectiveOpenCodeModel(currentStudioSettings.opencode_model, eff);

  // Hiển thị model ID tinh gọn rõ ràng cho người dùng (ví dụ: ag/gemini-3.8-flash-high)
  const displayModelId = (res.effective || '').replace(/^9router\//i, '');

  const activeModelEl = document.getElementById('quickOpencodeActiveModel');
  if (activeModelEl) {
    activeModelEl.textContent = displayModelId;
  }

  const activeModelDisplayBadge = document.getElementById('activeModelDisplayBadge');
  if (activeModelDisplayBadge) {
    activeModelDisplayBadge.textContent = displayModelId;
  }

  const activeModelOpencodeFullId = document.getElementById('activeModelOpencodeFullId');
  if (activeModelOpencodeFullId) {
    activeModelOpencodeFullId.textContent = res.effective;
  }

  const activeModelEffortBadge = document.getElementById('activeModelEffortBadge');
  if (activeModelEffortBadge) {
    if (res.isFree) {
      activeModelEffortBadge.textContent = 'Mô hình Miễn phí / Tiêu chuẩn';
      activeModelEffortBadge.className = 'text-[10px] font-sans font-medium px-2 py-0.5 rounded bg-emerald-950 text-emerald-300 border border-emerald-700/60';
    } else if (res.supportsEffort) {
      activeModelEffortBadge.textContent = `Suy luận: ${eff.toUpperCase()}`;
      activeModelEffortBadge.className = 'text-[10px] font-sans font-medium px-2 py-0.5 rounded bg-blue-900/60 text-blue-200 border border-blue-700/60';
    } else {
      activeModelEffortBadge.textContent = 'Mô hình Tiêu chuẩn';
      activeModelEffortBadge.className = 'text-[10px] font-sans font-medium px-2 py-0.5 rounded bg-slate-800 text-slate-300 border border-slate-700';
    }
  }

  const badgeEl = document.getElementById('quickOpencodeEffortBadge');
  if (badgeEl) {
    if (res.isFree) {
      badgeEl.textContent = 'Mô hình Miễn phí / Tiêu chuẩn (Không tốn token)';
      badgeEl.className = 'text-[10px] font-sans font-medium px-2 py-0.5 rounded bg-emerald-950 text-emerald-300 border border-emerald-700/60';
    } else if (res.supportsEffort) {
      const effLabels = {
        'low': 'Suy luận: Low (Tốc độ cao)',
        'medium': 'Suy luận: Medium (Cân bằng)',
        'high': 'Suy luận: High (Sâu)',
        'xhigh': 'Suy luận: Extra High',
        'max': 'Suy luận: Maximum'
      };
      badgeEl.textContent = effLabels[eff] || `Suy luận: ${eff.toUpperCase()}`;
      badgeEl.className = 'text-[10px] font-sans font-medium px-2 py-0.5 rounded bg-blue-900/60 text-blue-200 border border-blue-700/60';
    } else {
      badgeEl.textContent = 'Mô hình Tiêu chuẩn (Không áp dụng suy luận)';
      badgeEl.className = 'text-[10px] font-sans font-medium px-2 py-0.5 rounded bg-slate-800 text-slate-300 border border-slate-700';
    }
  }

  const descEl = document.getElementById('quickOpencodeActiveDesc');
  if (descEl) {
    if (res.isFree) {
      descEl.textContent = 'Mô hình miễn phí (Free) không tốn token và hoạt động ở chế độ tiêu chuẩn, không chia mức suy luận.';
    } else if (res.supportsEffort) {
      descEl.textContent = 'Mô hình thực thi tự động áp dụng mức suy luận đã chọn (Low / Medium / High) bên dưới.';
    } else {
      descEl.textContent = 'Mô hình cố định không hỗ trợ chia mức suy luận.';
    }
  }

  const pageDescEl = document.getElementById('pageModelActiveDesc');
  if (pageDescEl) {
    if (res.isFree) {
      pageDescEl.textContent = 'Mô hình miễn phí (Free) không tốn token và hoạt động ở chế độ tiêu chuẩn, không chia mức suy luận.';
    } else if (res.supportsEffort) {
      pageDescEl.textContent = `Mô hình thực thi tự động áp dụng mức suy luận đã chọn (${eff.toUpperCase()}) trong tab Effort.`;
    } else {
      pageDescEl.textContent = 'Mô hình cố định không hỗ trợ chia mức suy luận.';
    }
  }

  const quickSelect = document.getElementById('quickOpencodeModelSelect');
  if (quickSelect && res.baseModel) {
    quickSelect.value = res.baseModel;
  }

  const pageSelect = document.getElementById('pageSettingsOpencodeModelSelect');
  if (pageSelect && res.baseModel) {
    pageSelect.value = res.baseModel;
  }

  updateDynamicEffortPanel(res);
}
window.updateQuickOpencodeDisplay = updateQuickOpencodeDisplay;

async function onOpenCodeModelChange(newModel) {
  if (!newModel) return;
  const isFree = /free/i.test(newModel);
  const cleanModel = isFree ? newModel : newModel.replace(/-(low|medium|high|xhigh|max)$/i, '');
  currentStudioSettings.opencode_model = cleanModel;
  const quickSelect = document.getElementById('quickOpencodeModelSelect');
  const pageSelect = document.getElementById('pageSettingsOpencodeModelSelect');
  if (quickSelect && quickSelect.value !== cleanModel) quickSelect.value = cleanModel;
  if (pageSelect && pageSelect.value !== cleanModel) pageSelect.value = cleanModel;
  updateQuickOpencodeDisplay(currentStudioSettings.effort);
  renderModelSelectForCurrentEngine();
  const tab = (activeSettingsSubTab === 'effort') ? 'effort' : 'model';
  markSettingsDirty(true, tab);
}
window.onOpenCodeModelChange = onOpenCodeModelChange;

async function onModelDropdownChange(newVal) {
  if (!newVal) return;
  if (currentStudioSettings.engine === 'opencode') {
    await onOpenCodeModelChange(newVal);
  } else {
    currentStudioSettings.model = newVal;
    const masterSelect = document.getElementById('pageSettingsModelSelect');
    if (masterSelect) masterSelect.value = newVal;

    const effMatch = newVal.match(/-(low|medium|high|xhigh|max)$/i);
    if (effMatch) {
      currentStudioSettings.effort = effMatch[1].toLowerCase();
      updateEffortUI(currentStudioSettings.effort);
    }
    renderModelSelectForCurrentEngine();
    markSettingsDirty(true, 'model');
  }
}
window.onModelDropdownChange = onModelDropdownChange;

function selectModelPreset(presetKey) {
  const pageSelect = document.getElementById('pageSettingsOpencodeModelSelect');
  if (!pageSelect || !pageSelect.options.length) {
    showToast('Danh sách mô hình chưa sẵn sàng. Đang tải lại...', 'info');
    refreshCurrentEngineModels();
    return;
  }

  let targetVal = '';
  const opts = Array.from(pageSelect.options);

  if (presetKey === 'flash') {
    const opt = opts.find(o => /gemini-3\.8-flash/i.test(o.value)) || opts.find(o => /flash/i.test(o.value) && !/free/i.test(o.value));
    if (opt) targetVal = opt.value;
  } else if (presetKey === 'pro') {
    const opt = opts.find(o => /gemini-3\.8-pro/i.test(o.value)) || opts.find(o => /pro/i.test(o.value) && !/free/i.test(o.value));
    if (opt) targetVal = opt.value;
  } else if (presetKey === 'free') {
    const opt = opts.find(o => /free/i.test(o.value));
    if (opt) targetVal = opt.value;
  }

  if (targetVal) {
    pageSelect.value = targetVal;
    onModelDropdownChange(targetVal);
    markSettingsDirty(true, 'model');
    showToast(`Đã chuyển nhanh sang mô hình: ${targetVal}`, 'success');
  } else {
    showToast(`Không tìm thấy mô hình phù hợp cho gợi ý "${presetKey}".`, 'warning');
  }
}
window.selectModelPreset = selectModelPreset;

async function startGeminiCliBackground(btn) {
  if (btn) {
    btn.disabled = true;
    btn.innerHTML = '<span class="inline-block animate-spin mr-1">↻</span> <span>Đang khởi động...</span>';
  }
  try {
    const res = await fetch('/api/gemini/start', { method: 'POST' });
    const data = await res.json();
    if (data && data.success) {
      showToast(data.message || 'Gemini CLI đã được kích hoạt chạy ngầm thành công!');
      if (geminiCliStatus) {
        geminiCliStatus.daemon_active = true;
        geminiCliStatus.ready = true;
      }
    } else {
      showToast((data && data.message) || 'Không thể khởi chạy Gemini CLI ngầm', 'error');
    }
    if (typeof checkGeminiCliAuthStatus === 'function') {
      await checkGeminiCliAuthStatus(false);
    } else {
      updateEngineUI(currentStudioSettings.engine, nineRouterOnline);
    }
  } catch (err) {
    showToast('Lỗi kết nối khi khởi động Gemini CLI ngầm: ' + err.message, 'error');
  } finally {
    if (btn) btn.disabled = false;
  }
}

async function startNineRouterBackground(btn) {
  if (btn) {
    btn.disabled = true;
    btn.innerHTML = '<span class="inline-block animate-spin mr-1">↻</span> <span>Đang khởi động...</span>';
  }
  try {
    const res = await fetch('/api/9router/start', { method: 'POST' });
    const data = await res.json();
    if (data && data.success) {
      nineRouterOnline = true;
      showToast(data.message || '9router proxy đã khởi động ngầm thành công trên cổng 20128!');
      updateEngineUI(currentStudioSettings.engine, true);
      fetchOpenCodeModels(true);
    } else {
      showToast((data && data.message) || 'Không thể khởi động 9router proxy ngầm', 'error');
      updateEngineUI(currentStudioSettings.engine, false);
    }
  } catch (err) {
    showToast('Lỗi kết nối khi khởi động 9router ngầm: ' + err.message, 'error');
  } finally {
    if (btn) btn.disabled = false;
  }
}

window.updateEngineUI = updateEngineUI;
window.onPageEngineChange = onPageEngineChange;
window.fetchOpenCodeModels = fetchOpenCodeModels;
window.onOpenCodeModelChange = onOpenCodeModelChange;
window.startGeminiCliBackground = startGeminiCliBackground;
window.startNineRouterBackground = startNineRouterBackground;

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
  markSettingsDirty(true, 'effort');
}
window.switchModelFamilyTab = switchModelFamilyTab;

function onModelFamilySubModelChange(family, newModel) {
  currentStudioSettings.model = newModel;
  const masterSelect = document.getElementById('pageSettingsModelSelect');
  if (masterSelect) {
    masterSelect.value = newModel;
  }
  updateEffortUI(currentStudioSettings.effort);
  markSettingsDirty(true, 'effort');
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
  const cleanOpencodeModel = (currentStudioSettings.opencode_model || '').replace(/-(low|medium|high|xhigh|max)$/i, '');
  if (opencodeModelSelect) {
    if (currentStudioSettings.engine === 'opencode' && cleanOpencodeModel) {
      opencodeModelSelect.value = cleanOpencodeModel;
    } else if (currentStudioSettings.engine === 'gemini_cli' && currentStudioSettings.model) {
      opencodeModelSelect.value = currentStudioSettings.model;
    }
  }
  const quickOpencodeSelect = document.getElementById('quickOpencodeModelSelect');
  if (quickOpencodeSelect && cleanOpencodeModel) {
    quickOpencodeSelect.value = cleanOpencodeModel;
  }
  updateQuickOpencodeDisplay(eff);
}
window.updateEffortUI = updateEffortUI;

function onPageEffortChange(newEffort) {
  currentStudioSettings.effort = newEffort;

  if (currentStudioSettings.engine === 'gemini_cli') {
    if (currentModelFamily === 'gemini' || !currentModelFamily) {
      if (currentStudioSettings.model && currentStudioSettings.model.startsWith('gemini-3.8-flash')) {
        currentStudioSettings.model = `gemini-3.8-flash-${newEffort}`;
      }
    }
    renderModelSelectForCurrentEngine();
  } else {
    // OpenCode: auto switch effective model variant to reflect the selected reasoning effort
    updateQuickOpencodeDisplay(newEffort);
    renderModelSelectForCurrentEngine();
  }

  updateEffortUI(newEffort);
  markSettingsDirty(true, 'effort');
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
    markSettingsDirty(true, 'effort');
  } else if (e.key === 'ArrowLeft' || e.key === 'ArrowUp') {
    e.preventDefault();
    const prevIdx = (curIdx - 1 + levels.length) % levels.length;
    pendingEffortSelection = levels[prevIdx];
    updateEffortUI(pendingEffortSelection);
    markSettingsDirty(true, 'effort');
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

const dirtySubTabs = {
  engine: false,
  model: false,
  effort: false,
  mcp: false,
  api: false,
  env: false,
  account: false
};

function updateSaveButtonState() {
  const btn = document.getElementById('btnSaveSettingsPage');
  const isCurrentTabDirty = Boolean(dirtySubTabs[activeSettingsSubTab]);
  if (btn) {
    if (isCurrentTabDirty) {
      btn.classList.add('is-dirty');
      btn.classList.remove('cursor-not-allowed', 'bg-slate-700/60', 'text-slate-400');
      btn.removeAttribute('disabled');
      btn.disabled = false;
    } else {
      btn.classList.remove('is-dirty');
      btn.classList.add('cursor-not-allowed', 'bg-slate-700/60', 'text-slate-400');
      btn.setAttribute('disabled', 'true');
      btn.disabled = true;
    }
  }

  // Cập nhật chấm tròn vàng hiển thị tab có thay đổi chưa lưu
  ['engine', 'model', 'effort', 'api', 'env'].forEach(t => {
    const dot = document.getElementById('settingsNavDirty_' + t);
    if (dot) {
      if (dirtySubTabs[t]) dot.classList.remove('hidden');
      else dot.classList.add('hidden');
    }
  });
}
window.updateSaveButtonState = updateSaveButtonState;

function markSettingsDirty(dirty = true, tab = null) {
  const targetTab = tab || activeSettingsSubTab || 'engine';
  if (!dirty) {
    if (tab) {
      dirtySubTabs[tab] = false;
    } else {
      Object.keys(dirtySubTabs).forEach(k => { dirtySubTabs[k] = false; });
    }
    isSettingsDirty = Object.values(dirtySubTabs).some(Boolean);
  } else {
    dirtySubTabs[targetTab] = true;
    isSettingsDirty = true;
  }
  updateSaveButtonState();
}
window.markSettingsDirty = markSettingsDirty;

function onSettingsOptionChanged(tab = null) {
  markSettingsDirty(true, tab);
}
window.onSettingsOptionChanged = onSettingsOptionChanged;

let activeSettingsSubTab = 'engine';

function switchSettingsSidebarTab(tab, updateHistory = true) {
  if (!['engine', 'model', 'effort', 'mcp', 'api', 'env', 'account'].includes(tab)) tab = 'engine';
  activeSettingsSubTab = tab;
  window.initSettingsSubTab = tab;
  try {
    localStorage.setItem('activeSettingsSubTab', tab);
  } catch (e) { }

  const initStyle = document.getElementById('initialSettingsSubTabStyle');
  if (initStyle) initStyle.remove();

  const subRoutes = window.SETTINGS_SUBTAB_ROUTES || {
    'engine': '/settings/engine',
    'model': '/settings/model',
    'effort': '/settings/effort',
    'mcp': '/settings/mcp',
    'account': '/settings/account',
    'api': '/settings/api',
    'env': '/settings/env'
  };
  const targetPath = subRoutes[tab] || '/settings/engine';
  if (updateHistory && activeTab === 'settings' && window.location.pathname !== targetPath) {
    try {
      window.history.pushState({ tab: 'settings', settingsSubTab: tab }, '', targetPath);
    } catch (e) { }
  }

  const tabs = ['engine', 'model', 'effort', 'mcp', 'api', 'env'];
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

  if (tab === 'mcp') {
    reorderMcpPresetCards(_cachedMcpServers || window.currentMcpServers || []);
    fetchMcpServers(false);
  }
  if (tab === 'effort' || tab === 'model' || tab === 'engine') {
    if (currentStudioSettings.engine === 'opencode') {
      fetchOpenCodeModels(true);
    } else {
      fetchGeminiCliModels(true);
    }
    renderModelSelectForCurrentEngine();
    updateQuickOpencodeDisplay(currentStudioSettings.effort);
  }
  updateSaveButtonState();
}
window.switchSettingsSidebarTab = switchSettingsSidebarTab;
window.switchSettingsTab = switchSettingsSidebarTab;

/* ============================================================
   MCP (MODEL CONTEXT PROTOCOL) MANAGEMENT
   ============================================================ */
let _cachedMcpServers = [];
let _isFetchingMcpServers = false;

async function fetchMcpServers(forceRefresh = false) {
  if (_isFetchingMcpServers) return;
  _isFetchingMcpServers = true;
  try {
    const res = await fetch('/api/mcp/list');
    const data = await res.json();
    if (data && Array.isArray(data.servers)) {
      _cachedMcpServers = data.servers;
      renderMcpServers(data.servers);
    }
  } catch (err) {
    console.error('Lỗi khi tải danh sách MCP servers:', err);
    const container = document.getElementById('mcpServersContainer');
    if (container) {
      container.innerHTML = `<div class="p-4 text-center text-xs text-rose-400 font-sans">Lỗi tải MCP servers: ${escapeHtml(err.message)}</div>`;
    }
  } finally {
    _isFetchingMcpServers = false;
  }
}

function renderMcpServers(servers) {
  window.currentMcpServers = servers || [];
  const container = document.getElementById('mcpServersContainer');
  const countBadge = document.getElementById('mcpServerCountBadge');
  const activeCountTag = document.getElementById('mcpServerActiveCountTag');
  const jiraBadge = document.getElementById('jiraSyncStatusBadge');

  const count = servers ? servers.length : 0;
  const activeCount = servers ? servers.filter(s => !s.disabled).length : 0;

  if (countBadge) countBadge.textContent = String(count);
  if (activeCountTag) activeCountTag.textContent = `${activeCount} đang hoạt động`;

  // 1. Jira
  const jiraServer = (servers || []).find(s => s.name === 'jira' || s.preset === 'jira');
  const cardPresetJira = document.getElementById('cardPreset_jira');
  const badgePresetJira = document.getElementById('badgePreset_jira');
  const btnToggle = document.getElementById('btnToggleJira');
  const btnRemove = document.getElementById('btnRemoveJira');
  const btnToggleFooter = document.getElementById('btnToggleJiraFooter');
  const btnRemoveFooter = document.getElementById('btnRemoveJiraFooter');

  if (jiraServer) {
    const isStopped = !!jiraServer.disabled;
    const toggleLabel = isStopped ? 'Bật' : 'Tắt';
    const toggleFooterLabel = isStopped ? 'Bật Jira MCP' : 'Tắt MCP';

    if (btnToggle) {
      btnToggle.textContent = toggleLabel;
      btnToggle.classList.remove('hidden');
    }
    if (btnRemove) {
      btnRemove.classList.remove('hidden');
    }
    if (btnToggleFooter) {
      btnToggleFooter.textContent = toggleFooterLabel;
      btnToggleFooter.classList.remove('hidden');
    }
    if (btnRemoveFooter) {
      btnRemoveFooter.classList.remove('hidden');
    }

    if (jiraBadge) {
      if (isStopped) {
        jiraBadge.textContent = 'Đã dừng';
        jiraBadge.title = '';
        jiraBadge.className = 'text-[10px] font-sans font-medium px-2 py-0.5 rounded mcp-status-stopped';
      } else if (jiraServer.live_status === 'failed') {
        jiraBadge.textContent = 'Lỗi kết nối';
        jiraBadge.title = jiraServer.live_detail || 'MCP kết nối thất bại';
        jiraBadge.className = 'text-[10px] font-sans font-medium px-2 py-0.5 rounded mcp-status-stopped';
      } else {
        jiraBadge.textContent = 'Đã kết nối';
        jiraBadge.title = '';
        jiraBadge.className = 'text-[10px] font-sans font-medium px-2 py-0.5 rounded bg-emerald-950 text-emerald-400 border border-emerald-800';
      }
    }
    if (badgePresetJira) {
      if (isStopped) {
        badgePresetJira.textContent = 'Đã dừng';
        badgePresetJira.className = 'text-[9.5px] font-sans font-medium px-2 py-0.5 rounded mcp-status-stopped';
      } else {
        badgePresetJira.textContent = 'Đã kết nối';
        badgePresetJira.className = 'text-[9.5px] font-sans font-medium px-2 py-0.5 rounded is-connected';
      }
    }
    if (cardPresetJira) cardPresetJira.classList.remove('is-unconfigured');
    const hostInput = document.getElementById('input_jira_host');
    const emailInput = document.getElementById('input_jira_email');
    const tokenInput = document.getElementById('input_jira_token');
    if (hostInput && !hostInput.value && jiraServer.env && (jiraServer.env.JIRA_HOST || jiraServer.env.JIRA_BASE_URL)) {
      hostInput.value = jiraServer.env.JIRA_HOST || jiraServer.env.JIRA_BASE_URL;
    }
    if (emailInput && !emailInput.value && jiraServer.env && (jiraServer.env.JIRA_EMAIL || jiraServer.env.JIRA_USER_EMAIL)) {
      emailInput.value = jiraServer.env.JIRA_EMAIL || jiraServer.env.JIRA_USER_EMAIL;
    }
    if (tokenInput && !tokenInput.value && jiraServer.env && jiraServer.env.JIRA_API_TOKEN) {
      tokenInput.value = jiraServer.env.JIRA_API_TOKEN;
    }
  } else {
    if (btnToggle) btnToggle.classList.add('hidden');
    if (btnRemove) btnRemove.classList.add('hidden');
    if (btnToggleFooter) btnToggleFooter.classList.add('hidden');
    if (btnRemoveFooter) btnRemoveFooter.classList.add('hidden');

    if (jiraBadge) {
      jiraBadge.textContent = 'Chưa kết nối';
      jiraBadge.title = '';
      jiraBadge.className = 'text-[10px] font-sans font-medium px-2 py-0.5 rounded bg-slate-800 text-slate-400 border border-slate-700';
    }
    if (badgePresetJira) {
      badgePresetJira.textContent = 'Chưa kết nối';
      badgePresetJira.className = 'text-[9.5px] font-sans font-medium px-2 py-0.5 rounded bg-slate-800 text-slate-400';
    }
    if (cardPresetJira) cardPresetJira.classList.add('is-unconfigured');
  }

  // 2. GitHub
  const githubServer = (servers || []).find(s => s.name === 'github' || s.preset === 'github');
  const cardPresetGithub = document.getElementById('cardPreset_github');
  const githubBadge = document.getElementById('githubSyncStatusBadge');
  const badgePresetGithub = document.getElementById('badgePreset_github');
  const btnToggleGithubFooter = document.getElementById('btnToggleGithubFooter');
  const btnRemoveGithubFooter = document.getElementById('btnRemoveGithubFooter');

  if (githubServer) {
    const isStopped = !!githubServer.disabled;
    if (btnToggleGithubFooter) {
      btnToggleGithubFooter.textContent = isStopped ? 'Bật MCP' : 'Tắt MCP';
      btnToggleGithubFooter.classList.remove('hidden');
    }
    if (btnRemoveGithubFooter) {
      btnRemoveGithubFooter.classList.remove('hidden');
    }
    if (githubBadge) {
      githubBadge.textContent = isStopped ? 'Đã dừng' : 'Đã kết nối';
      githubBadge.className = isStopped
        ? 'text-[10px] font-sans font-medium px-2.5 py-1 rounded mcp-status-stopped'
        : 'text-[10px] font-sans font-medium px-2.5 py-1 rounded bg-emerald-950 text-emerald-400 border border-emerald-800';
    }
    if (badgePresetGithub) {
      badgePresetGithub.textContent = isStopped ? 'Đã dừng' : 'Đã kết nối';
      badgePresetGithub.className = isStopped
        ? 'text-[9.5px] font-sans font-medium px-2 py-0.5 rounded mcp-status-stopped'
        : 'text-[9.5px] font-sans font-medium px-2 py-0.5 rounded is-connected';
    }
    if (cardPresetGithub) cardPresetGithub.classList.remove('is-unconfigured');
    const tokenInput = document.getElementById('input_github_token');
    if (tokenInput && !tokenInput.value && githubServer.env && githubServer.env.GITHUB_PERSONAL_ACCESS_TOKEN) {
      tokenInput.value = githubServer.env.GITHUB_PERSONAL_ACCESS_TOKEN;
    }
  } else {
    if (btnToggleGithubFooter) btnToggleGithubFooter.classList.add('hidden');
    if (btnRemoveGithubFooter) btnRemoveGithubFooter.classList.add('hidden');
    if (githubBadge) {
      githubBadge.textContent = 'Chưa cấu hình';
      githubBadge.className = 'text-[10px] font-sans font-medium px-2.5 py-1 rounded bg-slate-800 text-slate-400';
    }
    if (badgePresetGithub) {
      badgePresetGithub.textContent = 'Chưa cấu hình';
      badgePresetGithub.className = 'text-[9.5px] font-sans font-medium px-2 py-0.5 rounded bg-slate-800 text-slate-400';
    }
    if (cardPresetGithub) cardPresetGithub.classList.add('is-unconfigured');
  }

  // 3. PostgreSQL
  const postgresServer = (servers || []).find(s => s.name === 'postgres' || s.preset === 'postgres');
  const cardPresetPostgres = document.getElementById('cardPreset_postgres');
  const postgresBadge = document.getElementById('postgresSyncStatusBadge');
  const badgePresetPostgres = document.getElementById('badgePreset_postgres');
  const btnTogglePostgresFooter = document.getElementById('btnTogglePostgresFooter');
  const btnRemovePostgresFooter = document.getElementById('btnRemovePostgresFooter');

  if (postgresServer) {
    const isStopped = !!postgresServer.disabled;
    if (btnTogglePostgresFooter) {
      btnTogglePostgresFooter.textContent = isStopped ? 'Bật MCP' : 'Tắt MCP';
      btnTogglePostgresFooter.classList.remove('hidden');
    }
    if (btnRemovePostgresFooter) {
      btnRemovePostgresFooter.classList.remove('hidden');
    }
    if (postgresBadge) {
      postgresBadge.textContent = isStopped ? 'Đã dừng' : 'Đã kết nối';
      postgresBadge.className = isStopped
        ? 'text-[10px] font-sans font-medium px-2.5 py-1 rounded mcp-status-stopped'
        : 'text-[10px] font-sans font-medium px-2.5 py-1 rounded bg-emerald-950 text-emerald-400 border border-emerald-800';
    }
    if (badgePresetPostgres) {
      badgePresetPostgres.textContent = isStopped ? 'Đã dừng' : 'Đã kết nối';
      badgePresetPostgres.className = isStopped
        ? 'text-[9.5px] font-sans font-medium px-2 py-0.5 rounded mcp-status-stopped'
        : 'text-[9.5px] font-sans font-medium px-2 py-0.5 rounded is-connected';
    }
    if (cardPresetPostgres) cardPresetPostgres.classList.remove('is-unconfigured');
    const urlInput = document.getElementById('input_postgres_url');
    if (urlInput && !urlInput.value && Array.isArray(postgresServer.args) && postgresServer.args.length > 0) {
      const connStr = postgresServer.args.find(a => typeof a === 'string' && a.startsWith('postgres'));
      if (connStr) urlInput.value = connStr;
    }
  } else {
    if (btnTogglePostgresFooter) btnTogglePostgresFooter.classList.add('hidden');
    if (btnRemovePostgresFooter) btnRemovePostgresFooter.classList.add('hidden');
    if (postgresBadge) {
      postgresBadge.textContent = 'Chưa cấu hình';
      postgresBadge.className = 'text-[10px] font-sans font-medium px-2.5 py-1 rounded bg-slate-800 text-slate-400';
    }
    if (badgePresetPostgres) {
      badgePresetPostgres.textContent = 'Chưa cấu hình';
      badgePresetPostgres.className = 'text-[9.5px] font-sans font-medium px-2 py-0.5 rounded bg-slate-800 text-slate-400';
    }
    if (cardPresetPostgres) cardPresetPostgres.classList.add('is-unconfigured');
  }

  // 4. MySQL
  const mysqlServer = (servers || []).find(s => s.name === 'mysql' || s.preset === 'mysql');
  const cardPresetMysql = document.getElementById('cardPreset_mysql');
  const mysqlBadge = document.getElementById('mysqlSyncStatusBadge');
  const badgePresetMysql = document.getElementById('badgePreset_mysql');
  const btnToggleMysqlFooter = document.getElementById('btnToggleMysqlFooter');
  const btnRemoveMysqlFooter = document.getElementById('btnRemoveMysqlFooter');

  if (mysqlServer) {
    const isStopped = !!mysqlServer.disabled;
    if (btnToggleMysqlFooter) {
      btnToggleMysqlFooter.textContent = isStopped ? 'Bật MCP' : 'Tắt MCP';
      btnToggleMysqlFooter.classList.remove('hidden');
    }
    if (btnRemoveMysqlFooter) {
      btnRemoveMysqlFooter.classList.remove('hidden');
    }
    if (mysqlBadge) {
      mysqlBadge.textContent = isStopped ? 'Đã dừng' : 'Đã kết nối';
      mysqlBadge.className = isStopped
        ? 'text-[10px] font-sans font-medium px-2.5 py-1 rounded mcp-status-stopped'
        : 'text-[10px] font-sans font-medium px-2.5 py-1 rounded bg-emerald-950 text-emerald-400 border border-emerald-800';
    }
    if (badgePresetMysql) {
      badgePresetMysql.textContent = isStopped ? 'Đã dừng' : 'Đã kết nối';
      badgePresetMysql.className = isStopped
        ? 'text-[9.5px] font-sans font-medium px-2 py-0.5 rounded mcp-status-stopped'
        : 'text-[9.5px] font-sans font-medium px-2 py-0.5 rounded is-connected';
    }
    if (cardPresetMysql) cardPresetMysql.classList.remove('is-unconfigured');
    const urlInput = document.getElementById('input_mysql_url');
    if (Array.isArray(mysqlServer.args) && mysqlServer.args.length > 0) {
      const connStr = mysqlServer.args.find(a => typeof a === 'string' && a.startsWith('mysql'));
      if (connStr) {
        if (urlInput && !urlInput.value) urlInput.value = connStr;
        syncMysqlUrlToFields(connStr);
      }
    }
  } else {
    if (btnToggleMysqlFooter) btnToggleMysqlFooter.classList.add('hidden');
    if (btnRemoveMysqlFooter) btnRemoveMysqlFooter.classList.add('hidden');
    if (mysqlBadge) {
      mysqlBadge.textContent = 'Chưa cấu hình';
      mysqlBadge.className = 'text-[10px] font-sans font-medium px-2.5 py-1 rounded bg-slate-800 text-slate-400';
    }
    if (badgePresetMysql) {
      badgePresetMysql.textContent = 'Chưa cấu hình';
      badgePresetMysql.className = 'text-[9.5px] font-sans font-medium px-2 py-0.5 rounded bg-slate-800 text-slate-400';
    }
    if (cardPresetMysql) cardPresetMysql.classList.add('is-unconfigured');
  }

  // 5. GitLab
  const gitlabServer = (servers || []).find(s => s.name === 'gitlab' || s.preset === 'gitlab');
  const cardPresetGitlab = document.getElementById('cardPreset_gitlab');
  const gitlabBadge = document.getElementById('gitlabSyncStatusBadge');
  const badgePresetGitlab = document.getElementById('badgePreset_gitlab');
  const btnToggleGitlabFooter = document.getElementById('btnToggleGitlabFooter');
  const btnRemoveGitlabFooter = document.getElementById('btnRemoveGitlabFooter');

  if (gitlabServer) {
    const isStopped = !!gitlabServer.disabled;
    if (btnToggleGitlabFooter) {
      btnToggleGitlabFooter.textContent = isStopped ? 'Bật MCP' : 'Tắt MCP';
      btnToggleGitlabFooter.classList.remove('hidden');
    }
    if (btnRemoveGitlabFooter) {
      btnRemoveGitlabFooter.classList.remove('hidden');
    }
    if (gitlabBadge) {
      gitlabBadge.textContent = isStopped ? 'Đã dừng' : 'Đã kết nối';
      gitlabBadge.className = isStopped
        ? 'text-[10px] font-sans font-medium px-2.5 py-1 rounded mcp-status-stopped'
        : 'text-[10px] font-sans font-medium px-2.5 py-1 rounded bg-emerald-950 text-emerald-400 border border-emerald-800';
    }
    if (badgePresetGitlab) {
      badgePresetGitlab.textContent = isStopped ? 'Đã dừng' : 'Đã kết nối';
      badgePresetGitlab.className = isStopped
        ? 'text-[9.5px] font-sans font-medium px-2 py-0.5 rounded mcp-status-stopped'
        : 'text-[9.5px] font-sans font-medium px-2 py-0.5 rounded is-connected';
    }
    if (cardPresetGitlab) cardPresetGitlab.classList.remove('is-unconfigured');
    const hostInput = document.getElementById('input_gitlab_host');
    const tokenInput = document.getElementById('input_gitlab_token');
    if (hostInput && !hostInput.value && gitlabServer.env && gitlabServer.env.GITLAB_API_URL) {
      hostInput.value = gitlabServer.env.GITLAB_API_URL.replace(/\/api\/v4\/?$/, '');
    }
    if (tokenInput && !tokenInput.value && gitlabServer.env && gitlabServer.env.GITLAB_PERSONAL_ACCESS_TOKEN) {
      tokenInput.value = gitlabServer.env.GITLAB_PERSONAL_ACCESS_TOKEN;
    }
  } else {
    if (btnToggleGitlabFooter) btnToggleGitlabFooter.classList.add('hidden');
    if (btnRemoveGitlabFooter) btnRemoveGitlabFooter.classList.add('hidden');
    if (gitlabBadge) {
      gitlabBadge.textContent = 'Chưa cấu hình';
      gitlabBadge.className = 'text-[10px] font-sans font-medium px-2.5 py-1 rounded bg-slate-800 text-slate-400';
    }
    if (badgePresetGitlab) {
      badgePresetGitlab.textContent = 'Chưa cấu hình';
      badgePresetGitlab.className = 'text-[9.5px] font-sans font-medium px-2 py-0.5 rounded bg-slate-800 text-slate-400';
    }
    if (cardPresetGitlab) cardPresetGitlab.classList.add('is-unconfigured');
  }

  // 6. Slack
  const slackServer = (servers || []).find(s => s.name === 'slack' || s.preset === 'slack');
  const cardPresetSlack = document.getElementById('cardPreset_slack');
  const slackBadge = document.getElementById('slackSyncStatusBadge');
  const badgePresetSlack = document.getElementById('badgePreset_slack');
  const btnToggleSlackFooter = document.getElementById('btnToggleSlackFooter');
  const btnRemoveSlackFooter = document.getElementById('btnRemoveSlackFooter');

  if (slackServer) {
    const isStopped = !!slackServer.disabled;
    if (btnToggleSlackFooter) {
      btnToggleSlackFooter.textContent = isStopped ? 'Bật MCP' : 'Tắt MCP';
      btnToggleSlackFooter.classList.remove('hidden');
    }
    if (btnRemoveSlackFooter) {
      btnRemoveSlackFooter.classList.remove('hidden');
    }
    if (slackBadge) {
      slackBadge.textContent = isStopped ? 'Đã dừng' : 'Đã kết nối';
      slackBadge.className = isStopped
        ? 'text-[10px] font-sans font-medium px-2.5 py-1 rounded mcp-status-stopped'
        : 'text-[10px] font-sans font-medium px-2.5 py-1 rounded bg-emerald-950 text-emerald-400 border border-emerald-800';
    }
    if (badgePresetSlack) {
      badgePresetSlack.textContent = isStopped ? 'Đã dừng' : 'Đã kết nối';
      badgePresetSlack.className = isStopped
        ? 'text-[9.5px] font-sans font-medium px-2 py-0.5 rounded mcp-status-stopped'
        : 'text-[9.5px] font-sans font-medium px-2 py-0.5 rounded is-connected';
    }
    if (cardPresetSlack) cardPresetSlack.classList.remove('is-unconfigured');
    const tokenInput = document.getElementById('input_slack_bot_token');
    const teamInput = document.getElementById('input_slack_team_id');
    if (tokenInput && !tokenInput.value && slackServer.env && slackServer.env.SLACK_BOT_TOKEN) {
      tokenInput.value = slackServer.env.SLACK_BOT_TOKEN;
    }
    if (teamInput && !teamInput.value && slackServer.env && slackServer.env.SLACK_TEAM_ID) {
      teamInput.value = slackServer.env.SLACK_TEAM_ID;
    }
  } else {
    if (btnToggleSlackFooter) btnToggleSlackFooter.classList.add('hidden');
    if (btnRemoveSlackFooter) btnRemoveSlackFooter.classList.add('hidden');
    if (slackBadge) {
      slackBadge.textContent = 'Chưa cấu hình';
      slackBadge.className = 'text-[10px] font-sans font-medium px-2.5 py-1 rounded bg-slate-800 text-slate-400';
    }
    if (badgePresetSlack) {
      badgePresetSlack.textContent = 'Chưa cấu hình';
      badgePresetSlack.className = 'text-[9.5px] font-sans font-medium px-2 py-0.5 rounded bg-slate-800 text-slate-400';
    }
    if (cardPresetSlack) cardPresetSlack.classList.add('is-unconfigured');
  }

  // 7. Custom
  const customBadge = document.getElementById('badgePreset_custom');
  if (customBadge) {
    const customServers = (servers || []).filter(s => !['jira', 'github', 'postgres', 'mysql', 'gitlab', 'slack'].includes(s.name) && s.preset !== 'jira');
    if (customServers.length > 0) {
      customBadge.textContent = `${customServers.length} server`;
      customBadge.className = 'text-[9.5px] font-sans font-medium px-2 py-0.5 rounded is-connected';
    } else {
      customBadge.textContent = 'Tùy biến';
      customBadge.className = 'text-[9.5px] font-sans font-medium px-2 py-0.5 rounded bg-slate-800 text-slate-400';
    }
  }

  // Tự động sắp xếp đưa các thẻ dịch vụ MCP đang active/kết nối lên đầu
  reorderMcpPresetCards(servers);

  if (!container) return;

  if (!servers || servers.length === 0) {
    container.innerHTML = `
      <div class="p-6 text-center rounded-lg border border-dashed border-[#244170]/80 bg-[#0c1628]/40 space-y-2">
        <p class="text-xs text-slate-300 font-sans font-medium">Chưa có MCP server nào được đăng ký</p>
        <p class="text-[11px] text-slate-400 font-sans max-w-md mx-auto">
          Điền thông tin Jira ở form trên và bấm <strong>"Lưu &amp; Kích hoạt Jira MCP"</strong> hoặc bấm <strong>"+ Thêm MCP tùy chỉnh"</strong> để kết nối thêm các công cụ bên ngoài.
        </p>
      </div>
    `;
    return;
  }

  container.innerHTML = servers.map(s => {
    const isJira = s.preset === 'jira' || s.name === 'jira';
    const isHttp = s.type === 'http';
    const isEnabled = !s.disabled;

    let statusLabel = isEnabled ? 'Hoạt động' : 'Đã dừng';
    let statusClass = isEnabled ? 'bg-emerald-950 text-emerald-400 border border-emerald-800' : 'mcp-status-stopped';
    let statusTitle = '';
    if (s.disabled) {
      statusLabel = 'Đã dừng';
      statusClass = 'mcp-status-stopped';
    } else if (s.live_status === 'failed') {
      statusLabel = 'Lỗi kết nối';
      statusClass = 'mcp-status-stopped';
      statusTitle = s.live_detail || 'MCP kết nối thất bại';
    } else if (s.live_status === 'connected') {
      statusLabel = 'Đã kết nối';
      statusClass = 'bg-emerald-950 text-emerald-400 border border-emerald-800';
    }

    const envKeys = s.env ? Object.keys(s.env) : [];
    const envPreview = envKeys.length > 0
      ? `<div class="flex flex-wrap items-center gap-1.5 mt-2">
           <span class="text-[10px] text-slate-400">Biến môi trường:</span>
           ${envKeys.map(k => `<span class="text-[10px] font-mono px-1.5 py-0.2 rounded bg-[#081222] border border-[#244170]/70 text-slate-300">${escapeHtml(k)}</span>`).join('')}
         </div>`
      : '';

    return `
      <div class="mcp-server-card p-3.5 rounded-lg border border-[#244170] bg-[#0c1628] hover:border-slate-500 transition space-y-2.5">
        <div class="flex flex-wrap items-center justify-between gap-2">
          <div class="flex items-center gap-2">
            <span class="font-mono text-xs font-bold text-white">${escapeHtml(s.name)}</span>
            <span class="text-[10px] font-mono px-1.5 py-0.5 rounded uppercase font-semibold ${isHttp ? 'bg-purple-950 text-purple-300 border border-purple-800' : 'bg-cyan-950 text-cyan-300 border border-cyan-800'}">
              ${escapeHtml(s.type)}
            </span>
            ${isJira ? '<span class="text-[10px] font-sans px-2 py-0.5 rounded bg-blue-950 text-blue-300 border border-blue-800 font-medium">Jira Cloud</span>' : ''}
            <span class="text-[10px] font-sans px-2 py-0.5 rounded font-medium ${statusClass}" title="${escapeHtml(statusTitle)}">
              ${statusLabel}
            </span>
          </div>
          <div class="flex items-center gap-2">
            <span class="text-[10px] text-slate-400 font-sans hidden sm:inline">Đồng bộ:</span>
            <span class="text-[10px] font-sans px-1.5 py-0.5 rounded bg-emerald-950/70 text-emerald-400 border border-emerald-800/80">Gemini CLI</span>
            <span class="text-[10px] font-sans px-1.5 py-0.5 rounded bg-cyan-950/70 text-cyan-400 border border-cyan-800/80">OpenCode</span>
            <button type="button" onclick="toggleMcpServer('${escapeHtml(s.name)}', ${!isEnabled})"
              class="text-xs px-2.5 py-1 rounded border border-[#244170] text-slate-300 hover:text-white hover:bg-white/5 transition cursor-pointer">
              ${isEnabled ? 'Tắt' : 'Bật'}
            </button>
            <button type="button" onclick="removeMcpServer('${escapeHtml(s.name)}')"
              class="text-xs px-2.5 py-1 rounded border border-rose-900/60 text-rose-400 hover:bg-rose-950/50 transition cursor-pointer">
              Xóa
            </button>
          </div>
        </div>

        <div class="mcp-code-preview p-2 rounded bg-[#081222] border border-[#244170]/50 text-xs font-mono text-slate-300 break-all select-all">
          ${escapeHtml(s.command_str || s.url || '(không có lệnh)')}
        </div>

        ${envPreview}
      </div>
    `;
  }).join('');
}

function toggleJiraTokenMask() {
  const tokenInput = document.getElementById('input_jira_token');
  const btn = document.getElementById('btnToggleJiraTokenMask');
  if (!tokenInput || !btn) return;
  if (tokenInput.type === 'password') {
    tokenInput.type = 'text';
    btn.textContent = 'Ẩn';
  } else {
    tokenInput.type = 'password';
    btn.textContent = 'Hiện';
  }
}

async function testJiraConnection(btn) {
  const host = document.getElementById('input_jira_host')?.value?.trim() || '';
  const email = document.getElementById('input_jira_email')?.value?.trim() || '';
  const api_token = document.getElementById('input_jira_token')?.value?.trim() || '';
  const resultBox = document.getElementById('jiraTestStatusResult');

  if (!host) {
    showToast('Vui lòng nhập Jira Host / URL.', 'warning');
    return;
  }
  if (!email) {
    showToast('Vui lòng nhập Email tài khoản Jira.', 'warning');
    return;
  }
  if (!api_token) {
    showToast('Vui lòng nhập Jira API Token.', 'warning');
    return;
  }

  if (btn) {
    btn.disabled = true;
    btn.innerHTML = '<span class="inline-block animate-spin mr-1">↻</span> Đang kết nối...';
  }
  if (resultBox) {
    resultBox.classList.remove('hidden');
    resultBox.className = 'jira-alert-box is-loading';
    resultBox.innerHTML = `
      <div class="jira-alert-icon">↻</div>
      <div class="jira-alert-content">
        <div class="jira-alert-title">Đang kiểm tra kết nối Jira...</div>
        <div class="jira-alert-desc">Đang gửi yêu cầu xác thực tới Jira Cloud API tại ${escapeHtml(host)}...</div>
      </div>
    `;
  }

  try {
    const res = await fetch('/api/mcp/test-jira', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ host, email, api_token })
    });
    const d = await res.json();
    if (d && d.success) {
      if (resultBox) {
        resultBox.className = 'jira-alert-box is-success';
        resultBox.innerHTML = `
          <div class="jira-alert-icon">✓</div>
          <div class="jira-alert-content">
            <div class="jira-alert-title">Kết nối Jira thành công</div>
            <div class="jira-alert-desc">${escapeHtml(d.message)}<br><span class="opacity-80 text-[11px]">Xác thực tài khoản thành công với Jira Cloud REST API.</span></div>
          </div>
        `;
      }
      showToast('Kết nối Jira thành công!');
    } else {
      if (resultBox) {
        resultBox.className = 'jira-alert-box is-error';
        resultBox.innerHTML = `
          <div class="jira-alert-icon">!</div>
          <div class="jira-alert-content">
            <div class="jira-alert-title">Lỗi kết nối Jira</div>
            <div class="jira-alert-desc">${escapeHtml((d && d.message) || 'Không thể xác thực với Jira Host.')}</div>
          </div>
        `;
      }
      showToast((d && d.message) || 'Kiểm tra Jira thất bại', 'error');
    }
  } catch (err) {
    if (resultBox) {
      resultBox.className = 'jira-alert-box is-error';
      resultBox.innerHTML = `
        <div class="jira-alert-icon">!</div>
        <div class="jira-alert-content">
          <div class="jira-alert-title">Lỗi kết nối mạng</div>
          <div class="jira-alert-desc">${escapeHtml(err.message)}</div>
        </div>
      `;
    }
    showToast('Lỗi kết nối: ' + err.message, 'error');
  } finally {
    if (btn) {
      btn.disabled = false;
      btn.textContent = 'Kiểm tra kết nối Jira';
    }
  }
}

async function saveJiraMcp(btn) {
  const host = document.getElementById('input_jira_host')?.value?.trim() || '';
  const email = document.getElementById('input_jira_email')?.value?.trim() || '';
  const api_token = document.getElementById('input_jira_token')?.value?.trim() || '';

  if (!host) {
    showToast('Vui lòng nhập Jira Host / Domain URL.', 'warning');
    return;
  }
  if (!email) {
    showToast('Vui lòng nhập Email tài khoản Jira.', 'warning');
    return;
  }
  if (!api_token) {
    showToast('Vui lòng nhập Jira API Token.', 'warning');
    return;
  }

  if (btn) {
    btn.disabled = true;
    btn.innerHTML = '<span class="inline-block animate-spin mr-1">↻</span> Đang lưu...';
  }

  try {
    const res = await fetch('/api/mcp/add-jira', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ host, email, api_token, name: 'jira' })
    });
    const d = await res.json();
    if (d && d.success) {
      showToast('Đã lưu & kích hoạt Atlassian Jira MCP thành công!');
      window.jiraWorkspaceLoaded = false;
      fetchMcpServers(true);
    } else {
      showToast((d && d.message) || 'Không thể lưu Jira MCP', 'error');
    }
  } catch (err) {
    showToast('Lỗi khi lưu Jira MCP: ' + err.message, 'error');
  } finally {
    if (btn) {
      btn.disabled = false;
      btn.textContent = 'Lưu & Kích hoạt Jira MCP';
    }
  }
}

function toggleCustomMcpSection(open) {
  const sec = document.getElementById('customMcpSection');
  if (!sec) return;
  if (typeof open === 'boolean') {
    if (open) sec.classList.remove('hidden');
    else sec.classList.add('hidden');
  } else {
    sec.classList.toggle('hidden');
  }
  if (!sec.classList.contains('hidden')) {
    const nameInput = document.getElementById('input_custom_mcp_name');
    if (nameInput) nameInput.focus();
  }
}

function onCustomMcpTypeChange(val) {
  const boxCmd = document.getElementById('boxCustomMcpCommand');
  const boxArgs = document.getElementById('boxCustomMcpArgs');
  const boxUrl = document.getElementById('boxCustomMcpUrl');
  if (val === 'http') {
    if (boxCmd) boxCmd.classList.add('hidden');
    if (boxArgs) boxArgs.classList.add('hidden');
    if (boxUrl) boxUrl.classList.remove('hidden');
  } else {
    if (boxCmd) boxCmd.classList.remove('hidden');
    if (boxArgs) boxArgs.classList.remove('hidden');
    if (boxUrl) boxUrl.classList.add('hidden');
  }
}

async function saveCustomMcp(btn) {
  const name = document.getElementById('input_custom_mcp_name')?.value?.trim() || '';
  const type = document.getElementById('select_custom_mcp_type')?.value || 'stdio';
  const command = document.getElementById('input_custom_mcp_command')?.value?.trim() || '';
  const argsStr = document.getElementById('input_custom_mcp_args')?.value?.trim() || '';
  const url = document.getElementById('input_custom_mcp_url')?.value?.trim() || '';
  const envRaw = document.getElementById('textarea_custom_mcp_env')?.value?.trim() || '';

  if (!name) {
    showToast('Vui lòng nhập tên Server.', 'warning');
    return;
  }
  if (type === 'stdio' && !command) {
    showToast('Vui lòng nhập lệnh thực thi (Command).', 'warning');
    return;
  }
  if (type === 'http' && !url) {
    showToast('Vui lòng nhập Remote URL.', 'warning');
    return;
  }

  const env = {};
  if (envRaw) {
    if (envRaw.startsWith('{')) {
      try {
        const parsed = JSON.parse(envRaw);
        if (typeof parsed === 'object') Object.assign(env, parsed);
      } catch (e) { }
    }
    if (Object.keys(env).length === 0) {
      envRaw.split('\n').forEach(line => {
        const trimmed = line.trim();
        if (trimmed && !trimmed.startsWith('#') && trimmed.includes('=')) {
          const idx = trimmed.indexOf('=');
          const k = trimmed.substring(0, idx).trim();
          const v = trimmed.substring(idx + 1).trim();
          if (k) env[k] = v;
        }
      });
    }
  }

  const args = argsStr ? argsStr.split(/\s+/).filter(Boolean) : [];

  const payload = {
    name,
    type,
    command,
    args,
    url,
    env,
    disabled: false
  };

  if (btn) {
    btn.disabled = true;
    btn.textContent = 'Đang lưu...';
  }

  try {
    const res = await fetch('/api/mcp/add', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    });
    const d = await res.json();
    if (d && d.success) {
      showToast(d.message || `Đã thêm MCP server '${name}' thành công!`);
      toggleCustomMcpSection(false);
      const nameInput = document.getElementById('input_custom_mcp_name');
      if (nameInput) nameInput.value = '';
      fetchMcpServers(true);
    } else {
      showToast((d && d.message) || 'Lỗi khi lưu MCP server', 'error');
    }
  } catch (err) {
    showToast('Lỗi khi lưu MCP server: ' + err.message, 'error');
  } finally {
    if (btn) {
      btn.disabled = false;
      btn.textContent = 'Lưu MCP Server';
    }
  }
}

async function removeMcpServer(name) {
  if (!name) return;
  const conf = await antdConfirm({
    title: 'Xóa MCP Server',
    content: `Bạn có chắc chắn muốn xóa MCP server '${name}' khỏi hệ thống?`,
    okText: 'Xóa server',
    danger: true
  });
  if (!conf) return;

  try {
    const res = await fetch('/api/mcp/remove', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ name })
    });
    const d = await res.json();
    if (d && d.success) {
      showToast(d.message || `Đã xóa MCP server '${name}'.`, 'success');
      fetchMcpServers(true);
    } else {
      showToast((d && d.message) || 'Lỗi khi xóa MCP server', 'error');
    }
  } catch (err) {
    showToast('Lỗi kết nối khi xóa: ' + err.message, 'error');
  }
}

async function toggleMcpServer(name, enabled) {
  if (!name) return;
  const actionTitle = enabled ? 'Bật MCP Server' : 'Tắt MCP Server';
  const actionContent = enabled
    ? `Bạn có chắc chắn muốn kích hoạt và bật hoạt động của MCP server '${name}'?`
    : `Bạn có chắc chắn muốn tạm dừng hoạt động của MCP server '${name}'?`;
  const okText = enabled ? 'Bật MCP' : 'Tắt MCP';

  const ok = await antdConfirm({
    title: actionTitle,
    content: actionContent,
    okText: okText,
    cancelText: 'Hủy',
    danger: !enabled
  });
  if (!ok) return;

  try {
    const res = await fetch('/api/mcp/toggle', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ name, enabled })
    });
    const d = await res.json();
    if (d && d.success) {
      showToast(d.message || `Đã cập nhật trạng thái MCP server '${name}'.`, 'success');
      if (name.toLowerCase().includes('jira')) {
        window.jiraWorkspaceLoaded = false;
        window.jiraStatus = null;
        window.currentJiraIssues = [];
        window.activeJiraIssue = null;
      }
      fetchMcpServers(true);
    } else {
      showToast((d && d.message) || 'Lỗi cập nhật', 'error');
    }
  } catch (err) {
    showToast('Lỗi kết nối: ' + err.message, 'error');
  }
}

async function togglePresetMcp(preset) {
  if (!preset) return;
  const servers = window.currentMcpServers || [];
  const s = servers.find(item => item.name === preset || item.preset === preset);
  const isStopped = s ? !!s.disabled : false;
  await toggleMcpServer(preset, isStopped);
}

async function removePresetMcp(preset) {
  if (!preset) return;
  const conf = await antdConfirm({
    title: 'Xóa cấu hình MCP',
    content: `Bạn có chắc chắn muốn xóa vĩnh viễn cấu hình MCP server '${preset}' khỏi hệ thống?`,
    okText: 'Xóa cấu hình',
    danger: true
  });
  if (!conf) return;

  try {
    const res = await fetch('/api/mcp/remove', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ name: preset })
    });
    const d = await res.json();
    if (d && d.success) {
      showToast(d.message || `Đã xóa cấu hình MCP '${preset}'.`, 'success');
      if (preset === 'jira') window.jiraWorkspaceLoaded = false;
      fetchMcpServers(true);
    } else {
      showToast((d && d.message) || 'Lỗi khi xóa MCP server', 'error');
    }
  } catch (err) {
    showToast('Lỗi kết nối khi xóa: ' + err.message, 'error');
  }
}

async function toggleJiraServer() {
  const jira = (_cachedMcpServers || []).find(s => s.name === 'jira' || s.preset === 'jira');
  const name = jira ? jira.name : 'jira';
  const newEnabled = jira ? !!jira.disabled : false;
  await toggleMcpServer(name, newEnabled);
}

async function removeJiraServer() {
  const jira = (_cachedMcpServers || []).find(s => s.name === 'jira' || s.preset === 'jira');
  const name = jira ? jira.name : 'jira';
  const conf = await antdConfirm({
    title: 'Xóa cấu hình Jira MCP',
    content: 'Bạn có chắc chắn muốn xóa cấu hình Atlassian Jira MCP khỏi hệ thống?',
    okText: 'Xóa Jira MCP',
    danger: true
  });
  if (!conf) return;

  try {
    const res = await fetch('/api/mcp/remove', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ name })
    });
    const d = await res.json();
    if (d && d.success) {
      showToast(d.message || `Đã xóa cấu hình Jira MCP.`, 'success');
      window.jiraWorkspaceLoaded = false;
      const hostInput = document.getElementById('input_jira_host');
      const emailInput = document.getElementById('input_jira_email');
      const tokenInput = document.getElementById('input_jira_token');
      if (hostInput) hostInput.value = '';
      if (emailInput) emailInput.value = '';
      if (tokenInput) tokenInput.value = '';
      const resultBox = document.getElementById('jiraTestStatusResult');
      if (resultBox) resultBox.classList.add('hidden');
      fetchMcpServers(true);
    } else {
      showToast((d && d.message) || 'Lỗi khi xóa Jira MCP', 'error');
    }
  } catch (err) {
    showToast('Lỗi kết nối khi xóa: ' + err.message, 'error');
  }
}

function reorderMcpPresetCards(servers = _cachedMcpServers || window.currentMcpServers || []) {
  const grid = document.getElementById('mcpPresetCardsGrid');
  if (!grid) return;

  const defaultPresets = ['jira', 'github', 'postgres', 'mysql', 'gitlab', 'slack', 'custom'];
  const sList = Array.isArray(servers) ? servers : (_cachedMcpServers || window.currentMcpServers || []);

  const getRank = (key) => {
    // 1. Ưu tiên kiểm tra trực tiếp badge trạng thái hiển thị trên DOM
    const badge = document.getElementById(`badgePreset_${key}`);
    if (badge) {
      const text = (badge.textContent || '').trim();
      if (text === 'Đã kết nối' || badge.classList.contains('is-connected')) return 0;
      if (text === 'Đã dừng' || badge.classList.contains('mcp-status-stopped')) return 1;
      if (text === 'Chưa cấu hình' || text === 'Chưa kết nối' || text === 'Tùy biến') return 2;
    }

    // 2. Dự phòng dựa trên danh sách servers từ backend
    if (key === 'custom') {
      const customs = sList.filter(x => !['jira', 'github', 'postgres', 'postgresql', 'mysql', 'gitlab', 'slack'].includes(x.name) && x.preset !== 'jira');
      if (customs.some(x => !x.disabled && x.live_status !== 'failed')) return 0;
      if (customs.length > 0) return 1;
      return 2;
    }

    let s;
    if (key === 'jira') {
      s = sList.find(x => x.name === 'jira' || x.preset === 'jira');
    } else if (key === 'github') {
      s = sList.find(x => x.name === 'github' || x.preset === 'github');
    } else if (key === 'postgres') {
      s = sList.find(x => x.name === 'postgres' || x.name === 'postgresql' || x.preset === 'postgres');
    } else if (key === 'mysql') {
      s = sList.find(x => x.name === 'mysql' || x.preset === 'mysql');
    } else if (key === 'gitlab') {
      s = sList.find(x => x.name === 'gitlab' || x.preset === 'gitlab');
    } else if (key === 'slack') {
      s = sList.find(x => x.name === 'slack' || x.preset === 'slack');
    }

    if (!s) return 2;
    if (!s.disabled && s.live_status !== 'failed') return 0;
    return 1;
  };

  const sortedPresets = [...defaultPresets].sort((a, b) => {
    const rankA = getRank(a);
    const rankB = getRank(b);
    if (rankA !== rankB) return rankA - rankB;
    return defaultPresets.indexOf(a) - defaultPresets.indexOf(b);
  });

  sortedPresets.forEach(preset => {
    const card = document.getElementById(`cardPreset_${preset}`);
    if (card && card.parentElement === grid) {
      grid.appendChild(card);
    }
  });
}

function selectMcpPreset(preset) {
  const presets = ['jira', 'github', 'postgres', 'mysql', 'gitlab', 'slack', 'custom'];
  const target = presets.includes(preset) ? preset : 'jira';

  presets.forEach(p => {
    const card = document.getElementById(`cardPreset_${p}`);
    if (card) {
      if (p === target) {
        card.classList.add('is-selected');
      } else {
        card.classList.remove('is-selected');
      }
    }

    const frameId = p === 'custom' ? 'customMcpSection' : `mcpConfigFrame_${p}`;
    const frame = document.getElementById(frameId);
    if (frame) {
      if (p === target) {
        frame.classList.remove('hidden');
      } else {
        frame.classList.add('hidden');
      }
    }
  });

  if (target === 'custom') {
    const nameInput = document.getElementById('input_custom_mcp_name');
    if (nameInput) setTimeout(() => nameInput.focus(), 50);
  } else if (target === 'github') {
    const tokenInput = document.getElementById('input_github_token');
    if (tokenInput && !tokenInput.value) setTimeout(() => tokenInput.focus(), 50);
  } else if (target === 'postgres') {
    const urlInput = document.getElementById('input_postgres_url');
    if (urlInput && !urlInput.value) setTimeout(() => urlInput.focus(), 50);
  } else if (target === 'mysql') {
    const hostInput = document.getElementById('input_mysql_host') || document.getElementById('input_mysql_url');
    if (hostInput && !hostInput.value) setTimeout(() => hostInput.focus(), 50);
  } else if (target === 'gitlab') {
    const hostInput = document.getElementById('input_gitlab_host');
    if (hostInput && !hostInput.value) setTimeout(() => hostInput.focus(), 50);
  } else if (target === 'slack') {
    const tokenInput = document.getElementById('input_slack_bot_token');
    if (tokenInput && !tokenInput.value) setTimeout(() => tokenInput.focus(), 50);
  }
}

async function testGithubConnection(btn) {
  const token = document.getElementById('input_github_token')?.value?.trim() || '';
  const resultBox = document.getElementById('githubTestStatusResult');

  if (!token) {
    showToast('Vui lòng nhập GitHub Personal Access Token.', 'warning');
    return;
  }

  if (btn) {
    btn.disabled = true;
    btn.innerHTML = '<span class="inline-block animate-spin mr-1">↻</span> Đang kết nối...';
  }
  if (resultBox) {
    resultBox.classList.remove('hidden');
    resultBox.className = 'jira-alert-box is-loading';
    resultBox.innerHTML = `
      <div class="jira-alert-icon">↻</div>
      <div class="jira-alert-content">
        <div class="jira-alert-title">Đang xác thực với GitHub API...</div>
        <div class="jira-alert-desc">Hệ thống đang kiểm tra token và quyền hạn với https://api.github.com/user</div>
      </div>
    `;
  }

  try {
    const res = await fetch('/api/mcp/test-github', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ token })
    });
    const d = await res.json();
    if (d && d.success) {
      if (resultBox) {
        resultBox.className = 'jira-alert-box is-success';
        resultBox.innerHTML = `
          <div class="jira-alert-icon">✓</div>
          <div class="jira-alert-content">
            <div class="jira-alert-title">Kết nối GitHub thành công!</div>
            <div class="jira-alert-desc">${escapeHtml(d.message || '')}</div>
          </div>
        `;
      }
      showToast(d.message || 'Kết nối GitHub thành công!', 'success');
    } else {
      const errMsg = (d && d.message) || 'Kiểm tra kết nối thất bại.';
      if (resultBox) {
        resultBox.className = 'jira-alert-box is-error';
        resultBox.innerHTML = `
          <div class="jira-alert-icon">!</div>
          <div class="jira-alert-content">
            <div class="jira-alert-title">Lỗi kết nối GitHub</div>
            <div class="jira-alert-desc">${escapeHtml(errMsg)}</div>
          </div>
        `;
      }
      showToast(errMsg, 'error');
    }
  } catch (err) {
    if (resultBox) {
      resultBox.className = 'jira-alert-box is-error';
      resultBox.innerHTML = `
        <div class="jira-alert-icon">!</div>
        <div class="jira-alert-content">
          <div class="jira-alert-title">Lỗi kết nối mạng</div>
          <div class="jira-alert-desc">${escapeHtml(err.message)}</div>
        </div>
      `;
    }
    showToast('Lỗi kết nối: ' + err.message, 'error');
  } finally {
    if (btn) {
      btn.disabled = false;
      btn.textContent = 'Kiểm tra kết nối GitHub';
    }
  }
}

async function saveGithubMcp(btn) {
  const token = document.getElementById('input_github_token')?.value?.trim() || '';
  if (!token) {
    showToast('Vui lòng nhập GitHub Personal Access Token.', 'warning');
    return;
  }
  if (btn) {
    btn.disabled = true;
    btn.innerHTML = '<span class="inline-block animate-spin mr-1">↻</span> Đang lưu...';
  }
  try {
    const res = await fetch('/api/mcp/add-github', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ token, name: 'github' })
    });
    const d = await res.json();
    if (d && d.success) {
      showToast(d.message || 'Đã lưu & kích hoạt GitHub MCP thành công!', 'success');
      fetchMcpServers(true);
    } else {
      showToast((d && d.message) || 'Không thể lưu GitHub MCP', 'error');
    }
  } catch (err) {
    showToast('Lỗi khi lưu GitHub MCP: ' + err.message, 'error');
  } finally {
    if (btn) {
      btn.disabled = false;
      btn.textContent = 'Lưu & Kích hoạt GitHub MCP';
    }
  }
}

async function savePostgresMcp(btn) {
  const url = document.getElementById('input_postgres_url')?.value?.trim() || '';
  if (!url) {
    showToast('Vui lòng nhập PostgreSQL Connection String URL.', 'warning');
    return;
  }
  if (btn) {
    btn.disabled = true;
    btn.innerHTML = '<span class="inline-block animate-spin mr-1">↻</span> Đang lưu...';
  }
  try {
    const res = await fetch('/api/mcp/add-postgres', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ url, name: 'postgres' })
    });
    const d = await res.json();
    if (d && d.success) {
      showToast(d.message || 'Đã lưu & kích hoạt PostgreSQL MCP thành công!', 'success');
      fetchMcpServers(true);
    } else {
      showToast((d && d.message) || 'Không thể lưu PostgreSQL MCP', 'error');
    }
  } catch (err) {
    showToast('Lỗi khi lưu PostgreSQL MCP: ' + err.message, 'error');
  } finally {
    if (btn) {
      btn.disabled = false;
      btn.textContent = 'Lưu & Kích hoạt PostgreSQL MCP';
    }
  }
}

async function testGitlabConnection(btn) {
  const host = document.getElementById('input_gitlab_host')?.value?.trim() || 'https://gitlab.com';
  const token = document.getElementById('input_gitlab_token')?.value?.trim() || '';
  const resultBox = document.getElementById('gitlabTestStatusResult');

  if (!token) {
    showToast('Vui lòng nhập GitLab Personal Access Token.', 'warning');
    return;
  }

  if (btn) {
    btn.disabled = true;
    btn.innerHTML = '<span class="inline-block animate-spin mr-1">↻</span> Đang kết nối...';
  }
  if (resultBox) {
    resultBox.classList.remove('hidden');
    resultBox.className = 'jira-alert-box is-loading';
    resultBox.innerHTML = `
      <div class="jira-alert-icon">↻</div>
      <div class="jira-alert-content">
        <div class="jira-alert-title">Đang xác thực với GitLab API...</div>
        <div class="jira-alert-desc">Hệ thống đang kiểm tra token với ${escapeHtml(host)}/api/v4/user</div>
      </div>
    `;
  }

  try {
    const res = await fetch('/api/mcp/test-gitlab', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ host, token })
    });
    const d = await res.json();
    if (d && d.success) {
      if (resultBox) {
        resultBox.className = 'jira-alert-box is-success';
        resultBox.innerHTML = `
          <div class="jira-alert-icon">✓</div>
          <div class="jira-alert-content">
            <div class="jira-alert-title">Kết nối GitLab thành công!</div>
            <div class="jira-alert-desc">${escapeHtml(d.message || '')}</div>
          </div>
        `;
      }
      showToast(d.message || 'Kết nối GitLab thành công!', 'success');
    } else {
      const errMsg = (d && d.message) || 'Kiểm tra kết nối thất bại.';
      if (resultBox) {
        resultBox.className = 'jira-alert-box is-error';
        resultBox.innerHTML = `
          <div class="jira-alert-icon">!</div>
          <div class="jira-alert-content">
            <div class="jira-alert-title">Lỗi kết nối GitLab</div>
            <div class="jira-alert-desc">${escapeHtml(errMsg)}</div>
          </div>
        `;
      }
      showToast(errMsg, 'error');
    }
  } catch (err) {
    if (resultBox) {
      resultBox.className = 'jira-alert-box is-error';
      resultBox.innerHTML = `
        <div class="jira-alert-icon">!</div>
        <div class="jira-alert-content">
          <div class="jira-alert-title">Lỗi kết nối mạng</div>
          <div class="jira-alert-desc">${escapeHtml(err.message)}</div>
        </div>
      `;
    }
    showToast('Lỗi kết nối: ' + err.message, 'error');
  } finally {
    if (btn) {
      btn.disabled = false;
      btn.textContent = 'Kiểm tra kết nối GitLab';
    }
  }
}

async function saveGitlabMcp(btn) {
  const host = document.getElementById('input_gitlab_host')?.value?.trim() || 'https://gitlab.com';
  const token = document.getElementById('input_gitlab_token')?.value?.trim() || '';
  if (!token) {
    showToast('Vui lòng nhập GitLab Personal Access Token.', 'warning');
    return;
  }
  if (btn) {
    btn.disabled = true;
    btn.innerHTML = '<span class="inline-block animate-spin mr-1">↻</span> Đang lưu...';
  }
  try {
    const res = await fetch('/api/mcp/add-gitlab', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ host, token, name: 'gitlab' })
    });
    const d = await res.json();
    if (d && d.success) {
      showToast(d.message || 'Đã lưu & kích hoạt GitLab MCP thành công!', 'success');
      fetchMcpServers(true);
    } else {
      showToast((d && d.message) || 'Không thể lưu GitLab MCP', 'error');
    }
  } catch (err) {
    showToast('Lỗi khi lưu GitLab MCP: ' + err.message, 'error');
  } finally {
    if (btn) {
      btn.disabled = false;
      btn.textContent = 'Lưu & Kích hoạt GitLab MCP';
    }
  }
}

function parseMysqlUrl(urlStr) {
  if (!urlStr || typeof urlStr !== 'string') return null;
  const trimmed = urlStr.trim();
  if (!trimmed) return null;
  const m = trimmed.match(/^mysql:\/\/(?:([^:@]+)(?::([^@]*))?@)?([^:\/\?#]+)(?::(\d+))?(?:\/([^?#]*))?/i);
  if (!m) return null;
  return {
    user: m[1] ? decodeURIComponent(m[1]) : '',
    password: m[2] ? decodeURIComponent(m[2]) : '',
    host: m[3] ? m[3] : '',
    port: m[4] ? m[4] : '3306',
    database: m[5] ? decodeURIComponent(m[5]) : ''
  };
}

function buildMysqlUrl(opts) {
  if (!opts) return '';
  const host = (opts.host || '').trim();
  const port = (opts.port || '').toString().trim() || '3306';
  const user = (opts.user || '').trim();
  const password = opts.password || '';
  const database = (opts.database || '').trim();

  if (!host && !user) return '';

  const h = host || '127.0.0.1';
  const u = user || 'root';
  let auth = encodeURIComponent(u);
  if (password) {
    auth += ':' + encodeURIComponent(password);
  }
  let url = `mysql://${auth}@${h}:${port}`;
  if (database) {
    url += `/${encodeURIComponent(database)}`;
  }
  return url;
}

function handleMysqlFieldChange() {
  const host = document.getElementById('input_mysql_host')?.value?.trim() || '';
  const port = document.getElementById('input_mysql_port')?.value?.trim() || '3306';
  const user = document.getElementById('input_mysql_user')?.value?.trim() || '';
  const password = document.getElementById('input_mysql_password')?.value || '';
  const database = document.getElementById('input_mysql_database')?.value?.trim() || '';

  const urlInput = document.getElementById('input_mysql_url');
  if (urlInput) {
    urlInput.value = buildMysqlUrl({ host, port, user, password, database });
  }
}

function handleMysqlUrlChange() {
  const urlInput = document.getElementById('input_mysql_url');
  const url = urlInput?.value?.trim() || '';
  if (!url) return;
  const parsed = parseMysqlUrl(url);
  if (!parsed) return;

  const hostEl = document.getElementById('input_mysql_host');
  const portEl = document.getElementById('input_mysql_port');
  const userEl = document.getElementById('input_mysql_user');
  const passEl = document.getElementById('input_mysql_password');
  const dbEl = document.getElementById('input_mysql_database');

  if (hostEl && parsed.host) hostEl.value = parsed.host;
  if (portEl && parsed.port) portEl.value = parsed.port;
  if (userEl && parsed.user !== undefined) userEl.value = parsed.user;
  if (passEl && parsed.password !== undefined) passEl.value = parsed.password;
  if (dbEl && parsed.database !== undefined) dbEl.value = parsed.database;
}

function syncMysqlUrlToFields(connStr) {
  if (!connStr) return;
  const parsed = parseMysqlUrl(connStr);
  if (!parsed) return;

  const hostEl = document.getElementById('input_mysql_host');
  const portEl = document.getElementById('input_mysql_port');
  const userEl = document.getElementById('input_mysql_user');
  const passEl = document.getElementById('input_mysql_password');
  const dbEl = document.getElementById('input_mysql_database');

  if (hostEl && !hostEl.value) hostEl.value = parsed.host || '127.0.0.1';
  if (portEl && (!portEl.value || portEl.value === '3306')) portEl.value = parsed.port || '3306';
  if (userEl && !userEl.value) userEl.value = parsed.user || 'root';
  if (passEl && !passEl.value) passEl.value = parsed.password || '';
  if (dbEl && !dbEl.value) dbEl.value = parsed.database || '';
}

async function testMysqlConnection(btn) {
  let url = document.getElementById('input_mysql_url')?.value?.trim() || '';
  const host = document.getElementById('input_mysql_host')?.value?.trim() || '';
  const port = document.getElementById('input_mysql_port')?.value?.trim() || '3306';
  const user = document.getElementById('input_mysql_user')?.value?.trim() || '';
  const password = document.getElementById('input_mysql_password')?.value || '';
  const database = document.getElementById('input_mysql_database')?.value?.trim() || '';
  const resultBox = document.getElementById('mysqlTestStatusResult');

  if (!url && !host && !user) {
    showToast('Vui lòng nhập Hostname hoặc MySQL Connection String URL.', 'warning');
    return;
  }
  if (!url) {
    url = buildMysqlUrl({ host, port, user, password, database });
    const urlInput = document.getElementById('input_mysql_url');
    if (urlInput) urlInput.value = url;
  }

  if (btn) {
    btn.disabled = true;
    btn.innerHTML = '<span class="inline-block animate-spin mr-1">↻</span> Đang kết nối...';
  }
  if (resultBox) {
    resultBox.classList.remove('hidden');
    resultBox.className = 'jira-alert-box is-loading';
    resultBox.innerHTML = `
      <div class="jira-alert-icon">↻</div>
      <div class="jira-alert-content">
        <div class="jira-alert-title">Đang kiểm tra kết nối MySQL...</div>
        <div class="jira-alert-desc">Hệ thống đang kiểm tra kết nối tới ${escapeHtml(host || 'máy chủ MySQL')}:${escapeHtml(port || '3306')}...</div>
      </div>
    `;
  }

  try {
    const res = await fetch('/api/mcp/test-mysql', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ url, host, port, user, password, database })
    });
    const d = await res.json();
    if (d && d.success) {
      if (resultBox) {
        resultBox.className = 'jira-alert-box is-success';
        resultBox.innerHTML = `
          <div class="jira-alert-icon">✓</div>
          <div class="jira-alert-content">
            <div class="jira-alert-title">Kết nối MySQL thành công!</div>
            <div class="jira-alert-desc">${escapeHtml(d.message || '')}</div>
          </div>
        `;
      }
      showToast(d.message || 'Kết nối MySQL thành công!', 'success');
    } else {
      const errMsg = (d && d.message) || 'Kiểm tra kết nối MySQL thất bại.';
      if (resultBox) {
        resultBox.className = 'jira-alert-box is-error';
        resultBox.innerHTML = `
          <div class="jira-alert-icon">!</div>
          <div class="jira-alert-content">
            <div class="jira-alert-title">Lỗi kết nối MySQL</div>
            <div class="jira-alert-desc">${escapeHtml(errMsg)}</div>
          </div>
        `;
      }
      showToast(errMsg, 'error');
    }
  } catch (err) {
    if (resultBox) {
      resultBox.className = 'jira-alert-box is-error';
      resultBox.innerHTML = `
        <div class="jira-alert-icon">!</div>
        <div class="jira-alert-content">
          <div class="jira-alert-title">Lỗi kết nối</div>
          <div class="jira-alert-desc">${escapeHtml(err.message)}</div>
        </div>
      `;
    }
    showToast('Lỗi khi kiểm tra MySQL: ' + err.message, 'error');
  } finally {
    if (btn) {
      btn.disabled = false;
      btn.textContent = 'Kiểm tra kết nối MySQL';
    }
  }
}

async function saveMysqlMcp(btn) {
  let url = document.getElementById('input_mysql_url')?.value?.trim() || '';
  const host = document.getElementById('input_mysql_host')?.value?.trim() || '';
  const port = document.getElementById('input_mysql_port')?.value?.trim() || '3306';
  const user = document.getElementById('input_mysql_user')?.value?.trim() || '';
  const password = document.getElementById('input_mysql_password')?.value || '';
  const database = document.getElementById('input_mysql_database')?.value?.trim() || '';

  if (!url && (host || user)) {
    url = buildMysqlUrl({ host, port, user, password, database });
    const urlInput = document.getElementById('input_mysql_url');
    if (urlInput) urlInput.value = url;
  }

  if (!url) {
    showToast('Vui lòng nhập thông tin kết nối MySQL (Hostname, Port, User...) hoặc Connection String URL.', 'warning');
    return;
  }
  if (btn) {
    btn.disabled = true;
    btn.innerHTML = '<span class="inline-block animate-spin mr-1">↻</span> Đang lưu...';
  }
  try {
    const res = await fetch('/api/mcp/add-mysql', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ url, host, port, user, password, database, name: 'mysql' })
    });
    const d = await res.json();
    if (d && d.success) {
      showToast(d.message || 'Đã lưu & kích hoạt MySQL MCP thành công!', 'success');
      fetchMcpServers(true);
    } else {
      showToast((d && d.message) || 'Không thể lưu MySQL MCP', 'error');
    }
  } catch (err) {
    showToast('Lỗi khi lưu MySQL MCP: ' + err.message, 'error');
  } finally {
    if (btn) {
      btn.disabled = false;
      btn.textContent = 'Lưu & Kích hoạt MySQL MCP';
    }
  }
}

async function testSlackConnection(btn) {
  const token = document.getElementById('input_slack_bot_token')?.value?.trim() || '';
  const resultBox = document.getElementById('slackTestStatusResult');

  if (!token) {
    showToast('Vui lòng nhập Slack Bot User OAuth Token (xoxb-...).', 'warning');
    return;
  }

  if (btn) {
    btn.disabled = true;
    btn.innerHTML = '<span class="inline-block animate-spin mr-1">↻</span> Đang kết nối...';
  }
  if (resultBox) {
    resultBox.classList.remove('hidden');
    resultBox.className = 'jira-alert-box is-loading';
    resultBox.innerHTML = `
      <div class="jira-alert-icon">↻</div>
      <div class="jira-alert-content">
        <div class="jira-alert-title">Đang xác thực với Slack Web API...</div>
        <div class="jira-alert-desc">Hệ thống đang kiểm tra bot token qua api.slack.com auth.test</div>
      </div>
    `;
  }

  try {
    const res = await fetch('/api/mcp/test-slack', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ token })
    });
    const d = await res.json();
    if (d && d.success) {
      if (resultBox) {
        resultBox.className = 'jira-alert-box is-success';
        resultBox.innerHTML = `
          <div class="jira-alert-icon">✓</div>
          <div class="jira-alert-content">
            <div class="jira-alert-title">Xác thực Slack thành công!</div>
            <div class="jira-alert-desc">Đã kết nối Workspace: <strong>${escapeHtml(d.team || 'Slack')}</strong> | Bot: <strong>${escapeHtml(d.user || 'EasySalon Agent')}</strong></div>
          </div>
        `;
      }
      showToast('Xác thực Slack Web API thành công!', 'success');
    } else {
      if (resultBox) {
        resultBox.className = 'jira-alert-box is-error';
        resultBox.innerHTML = `
          <div class="jira-alert-icon">✕</div>
          <div class="jira-alert-content">
            <div class="jira-alert-title">Xác thực Slack thất bại</div>
            <div class="jira-alert-desc">${escapeHtml(d.message || 'Token không hợp lệ hoặc thiếu quyền auth.test')}</div>
          </div>
        `;
      }
      showToast(d.message || 'Xác thực Slack thất bại', 'error');
    }
  } catch (err) {
    if (resultBox) {
      resultBox.className = 'jira-alert-box is-error';
      resultBox.innerHTML = `
        <div class="jira-alert-icon">✕</div>
        <div class="jira-alert-content">
          <div class="jira-alert-title">Lỗi kết nối Slack API</div>
          <div class="jira-alert-desc">${escapeHtml(err.message)}</div>
        </div>
      `;
    }
    showToast('Lỗi khi gọi Slack API: ' + err.message, 'error');
  } finally {
    if (btn) {
      btn.disabled = false;
      btn.textContent = 'Kiểm tra kết nối Slack';
    }
  }
}

async function saveSlackMcp(btn) {
  const token = document.getElementById('input_slack_bot_token')?.value?.trim() || '';
  const teamId = document.getElementById('input_slack_team_id')?.value?.trim() || '';

  if (!token) {
    showToast('Vui lòng nhập Slack Bot User OAuth Token.', 'warning');
    return;
  }

  if (btn) {
    btn.disabled = true;
    btn.innerHTML = '<span class="inline-block animate-spin mr-1">↻</span> Đang lưu...';
  }

  try {
    const res = await fetch('/api/mcp/add-slack', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ token, team_id: teamId, name: 'slack' })
    });
    const d = await res.json();
    if (d && d.success) {
      showToast(d.message || 'Đã lưu & kích hoạt Slack MCP thành công!', 'success');
      fetchMcpServers(true);
    } else {
      showToast((d && d.message) || 'Không thể lưu Slack MCP', 'error');
    }
  } catch (err) {
    showToast('Lỗi khi lưu Slack MCP: ' + err.message, 'error');
  } finally {
    if (btn) {
      btn.disabled = false;
      btn.textContent = 'Lưu & Kích hoạt Slack MCP';
    }
  }
}

async function autoDetectWorkspace(type) {
  const inputId = type === 'fe' ? 'input_fe_workspace' : 'input_be_workspace';
  const badgeId = type === 'fe' ? 'badge_fe_workspace_status' : 'badge_be_workspace_status';
  const defaultFolder = type === 'fe' ? 'easysalon-webapp' : 'easysalon-api';
  const inputEl = document.getElementById(inputId);
  const badgeEl = document.getElementById(badgeId);

  if (badgeEl) {
    badgeEl.textContent = 'Đang dò...';
    badgeEl.className = 'text-[10px] font-sans px-2 py-0.5 rounded bg-blue-950 text-blue-300 border border-blue-800 font-medium';
  }

  try {
    const res = await fetch(`/api/workspace/detect?target=${encodeURIComponent(type)}&name=${encodeURIComponent(defaultFolder)}`);
    const d = await res.json();
    if (d && d.success && d.path) {
      if (inputEl) inputEl.value = d.path;
      if (badgeEl) {
        if (d.exists) {
          badgeEl.textContent = 'Hợp lệ';
          badgeEl.className = 'text-[10px] font-sans px-2 py-0.5 rounded bg-emerald-950 text-emerald-400 border border-emerald-800 font-medium';
        } else {
          badgeEl.textContent = 'Chưa tồn tại';
          badgeEl.className = 'text-[10px] font-sans px-2 py-0.5 rounded bg-amber-950 text-amber-400 border border-amber-800 font-medium';
        }
      }
      onSettingsOptionChanged('env');
      showToast(`Đã tự động điền đường dẫn ${type === 'fe' ? 'Frontend' : 'Backend'}: ${d.path}`, 'success');
    } else {
      showToast(`Không tự động tìm thấy thư mục '${defaultFolder}'`, 'warning');
    }
  } catch (err) {
    showToast('Lỗi khi dò đường dẫn: ' + err.message, 'error');
  }
}

function setWorkspaceValue(type, path) {
  const inputId = type === 'fe' ? 'input_fe_workspace' : 'input_be_workspace';
  const inputEl = document.getElementById(inputId);
  if (inputEl) {
    inputEl.value = path;
    onWorkspaceInputChanged(type, path);
    onSettingsOptionChanged('env');
    showToast(`Đã chọn đường dẫn: ${path}`, 'success');
  }
}

function onWorkspaceInputChanged(type, val) {
  const badgeId = type === 'fe' ? 'badge_fe_workspace_status' : 'badge_be_workspace_status';
  const badgeEl = document.getElementById(badgeId);
  if (badgeEl) {
    if (val && val.trim()) {
      badgeEl.textContent = 'Đã chỉnh sửa';
      badgeEl.className = 'text-[10px] font-sans px-2 py-0.5 rounded bg-blue-950 text-blue-300 border border-blue-800 font-medium';
    } else {
      badgeEl.textContent = 'Hệ thống';
      badgeEl.className = 'text-[10px] font-sans px-2 py-0.5 rounded bg-slate-800 text-slate-300 border border-slate-700 font-medium';
    }
  }
}

async function autoDetectCli(type) {
  const isAgy = (type === 'agy');
  const inputId = isAgy ? 'input_agy_bin' : 'input_opencode_bin';
  const badgeId = isAgy ? 'badge_agy_bin_status' : 'badge_opencode_bin_status';
  const nameLabel = isAgy ? 'Antigravity CLI (agy)' : 'OpenCode CLI (opencode)';
  const inputEl = document.getElementById(inputId);
  const badgeEl = document.getElementById(badgeId);

  if (badgeEl) {
    badgeEl.textContent = 'Đang dò...';
    badgeEl.className = 'text-[10px] font-sans px-2 py-0.5 rounded bg-blue-950 text-blue-300 border border-blue-800 font-medium';
  }

  try {
    const res = await fetch(`/api/cli/detect?target=${encodeURIComponent(type)}`);
    const d = await res.json();
    if (d && d.success && d.path) {
      if (inputEl) inputEl.value = d.path;
      if (badgeEl) {
        if (d.exists) {
          badgeEl.textContent = 'Sẵn sàng';
          badgeEl.className = 'text-[10px] font-sans px-2 py-0.5 rounded bg-emerald-950 text-emerald-400 border border-emerald-700 font-medium';
        } else {
          badgeEl.textContent = 'Chưa cài CLI';
          badgeEl.className = 'text-[10px] font-sans px-2 py-0.5 rounded bg-amber-950 text-amber-400 border border-amber-700 font-medium';
        }
      }
      const suggestBtn = document.getElementById(isAgy ? 'btn_suggest_agy_bin' : 'btn_suggest_opencode_bin');
      if (suggestBtn) suggestBtn.textContent = d.path;

      onSettingsOptionChanged('env');
      const osName = d.platform === 'windows' ? 'Windows' : 'Linux/Unix';
      if (d.exists) {
        showToast(`Đã tự động nhận diện ${nameLabel} trên ${osName}: ${d.path}`, 'success');
      } else {
        showToast(`Đã điền đường dẫn gợi ý ${nameLabel} (${osName}): ${d.path}`, 'warning');
      }
    } else {
      showToast(`Không thể tự động tìm thấy ${nameLabel}`, 'warning');
    }
  } catch (err) {
    showToast('Lỗi khi dò đường dẫn CLI: ' + err.message, 'error');
  }
}

function setCliValue(type, path) {
  if (!path) return;
  const isAgy = (type === 'agy');
  const inputId = isAgy ? 'input_agy_bin' : 'input_opencode_bin';
  const inputEl = document.getElementById(inputId);
  if (inputEl) {
    inputEl.value = path.trim();
    onCliInputChanged(type, path.trim());
    onSettingsOptionChanged('env');
    showToast(`Đã chọn đường dẫn CLI: ${path.trim()}`, 'success');
  }
}

function onCliInputChanged(type, val) {
  const badgeId = (type === 'agy') ? 'badge_agy_bin_status' : 'badge_opencode_bin_status';
  const badgeEl = document.getElementById(badgeId);
  if (badgeEl) {
    if (val && val.trim()) {
      badgeEl.textContent = 'Đã chỉnh sửa';
      badgeEl.className = 'text-[10px] font-sans px-2 py-0.5 rounded bg-blue-950 text-blue-300 border border-blue-800 font-medium';
    } else {
      badgeEl.textContent = 'Tự dò tìm';
      badgeEl.className = 'text-[10px] font-sans px-2 py-0.5 rounded bg-slate-800 text-slate-300 border border-slate-700 font-medium';
    }
  }
}

window.fetchMcpServers = fetchMcpServers;
window.renderMcpServers = renderMcpServers;
window.reorderMcpPresetCards = reorderMcpPresetCards;
window.selectMcpPreset = selectMcpPreset;
window.togglePresetMcp = togglePresetMcp;
window.removePresetMcp = removePresetMcp;
window.testGithubConnection = testGithubConnection;
window.saveGithubMcp = saveGithubMcp;
window.savePostgresMcp = savePostgresMcp;
window.saveMysqlMcp = saveMysqlMcp;
window.testMysqlConnection = testMysqlConnection;
window.handleMysqlFieldChange = handleMysqlFieldChange;
window.handleMysqlUrlChange = handleMysqlUrlChange;
window.parseMysqlUrl = parseMysqlUrl;
window.buildMysqlUrl = buildMysqlUrl;
window.syncMysqlUrlToFields = syncMysqlUrlToFields;
window.testGitlabConnection = testGitlabConnection;
window.saveGitlabMcp = saveGitlabMcp;
window.testSlackConnection = testSlackConnection;
window.saveSlackMcp = saveSlackMcp;
window.autoDetectWorkspace = autoDetectWorkspace;
window.setWorkspaceValue = setWorkspaceValue;
window.onWorkspaceInputChanged = onWorkspaceInputChanged;
window.autoDetectCli = autoDetectCli;
window.setCliValue = setCliValue;
window.onCliInputChanged = onCliInputChanged;
window.toggleJiraTokenMask = toggleJiraTokenMask;
window.testJiraConnection = testJiraConnection;
window.saveJiraMcp = saveJiraMcp;
window.toggleJiraServer = toggleJiraServer;
window.removeJiraServer = removeJiraServer;
window.toggleCustomMcpSection = toggleCustomMcpSection;
window.onCustomMcpTypeChange = onCustomMcpTypeChange;
window.saveCustomMcp = saveCustomMcp;
window.removeMcpServer = removeMcpServer;
window.toggleMcpServer = toggleMcpServer;

function selectActiveApiProvider(provider) {
  if (!['gemini', 'claude', 'openai', 'deepseek', 'custom'].includes(provider)) provider = 'gemini';
  currentStudioSettings.api_provider = provider;

  ['gemini', 'claude', 'openai', 'deepseek', 'custom'].forEach(p => {
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
      'deepseek': 'DEEPSEEK',
      'custom': 'CUSTOM / 9ROUTER'
    };
    tag.textContent = labels[provider] || provider.toUpperCase();
  }

  markSettingsDirty(true, 'api');
}
window.selectActiveApiProvider = selectActiveApiProvider;

function togglePasswordVisibility(inputId, btnEl) {
  const el = document.getElementById(inputId);
  if (!el) return;
  const isPass = el.type === 'password';
  el.type = isPass ? 'text' : 'password';
  const btn = btnEl || (typeof event !== 'undefined' && event && event.currentTarget) || el.parentElement?.querySelector('button');
  if (btn) {
    btn.textContent = isPass ? 'Ẩn' : 'Hiện';
  }
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
  } else if (provider === 'deepseek') {
    key = document.getElementById('input_deepseek_api_key')?.value?.trim() || '';
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
        badge.textContent = 'Ưu tiên kích hoạt';
        badge.className = 'text-[10px] font-sans px-2 py-0.5 rounded bg-emerald-950 text-emerald-400 border border-emerald-700 font-medium';
      }
    } else {
      showToast(d.message || `Kiểm tra ${provider.toUpperCase()} thất bại`, 'error');
      const badge = document.getElementById(`badge_${provider}_key_status`);
      if (badge) {
        badge.textContent = d.error_type === 'quota_exceeded' ? 'Hết Token' : 'Thất bại';
        badge.className = 'text-[10px] font-sans px-2 py-0.5 rounded bg-rose-950 text-rose-400 border border-rose-700 font-medium';
      }
      if (d.error_type === 'quota_exceeded') {
        antdConfirm({
          title: d.title || 'API Key Hết Token / Quota',
          content: `
            <div class="space-y-2.5 font-sans text-left">
              <div class="text-sm text-rose-300 font-medium">${escapeHtml(d.message)}</div>
              ${d.raw_error ? `<div class="p-2.5 rounded bg-[#160b13] border border-rose-800 text-[11px] font-mono text-rose-300 break-all max-h-32 overflow-y-auto">${escapeHtml(d.raw_error)}</div>` : ''}
              <div class="text-xs text-slate-300">Khóa API của bạn không còn đủ token để phục vụ các yêu cầu AI. Vui lòng nạp thêm token hoặc đổi sang khóa khác.</div>
            </div>
          `,
          okText: 'Đã hiểu',
          cancelText: 'Đóng',
          danger: true
        });
      } else if (d.error_type === 'invalid_key') {
        antdConfirm({
          title: d.title || 'API Key Không Hợp Lệ',
          content: `
            <div class="space-y-2.5 font-sans text-left">
              <div class="text-sm text-rose-300 font-medium">${escapeHtml(d.message)}</div>
              ${d.raw_error ? `<div class="p-2.5 rounded bg-[#160b13] border border-rose-800 text-[11px] font-mono text-rose-300 break-all max-h-32 overflow-y-auto">${escapeHtml(d.raw_error)}</div>` : ''}
              <div class="text-xs text-slate-300">Vui lòng kiểm tra lại API Key đã copy chính xác từ bảng điều khiển của nhà cung cấp chưa.</div>
            </div>
          `,
          okText: 'Đã hiểu',
          cancelText: 'Đóng',
          danger: true
        });
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
  ['gemini', 'claude', 'openai', 'deepseek', 'custom'].forEach(p => {
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
      'deepseek': 'DEEPSEEK',
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
  if (settings.deepseek_api_key !== undefined) {
    const el = document.getElementById('input_deepseek_api_key');
    if (el && !el.matches(':focus')) el.value = settings.deepseek_api_key || '';
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
  setBadge('badge_deepseek_key_status', !!settings.deepseek_api_key);
  setBadge('badge_custom_key_status', !!(settings.custom_endpoint || settings.custom_api_key), true);
}

async function handleSaveSettingsClick() {
  if (!dirtySubTabs[activeSettingsSubTab]) return;
  await saveSettingsFromPage();
}
window.handleSaveSettingsClick = handleSaveSettingsClick;

async function saveSettingsFromPage() {
  const selectedEngineRadio = document.querySelector('input[name="page_engine"]:checked');
  const engine = selectedEngineRadio ? selectedEngineRadio.value : (currentStudioSettings.engine || 'gemini_cli');
  const effort = currentStudioSettings.effort || 'high';
  const pageModelSelect = document.getElementById('pageSettingsOpencodeModelSelect');
  let model = currentStudioSettings.model || 'gemini-3.8-flash-high';
  if (engine === 'gemini_cli' && pageModelSelect && pageModelSelect.value) {
    model = pageModelSelect.value;
  }
  const quickOpencodeSelect = document.getElementById('quickOpencodeModelSelect');
  const rawOpencodeModel = (quickOpencodeSelect && quickOpencodeSelect.value)
    || (engine === 'opencode' && pageModelSelect && pageModelSelect.value)
    || currentStudioSettings.opencode_model
    || '9router/ag/gemini-3.8-flash';
  let opencode_model = rawOpencodeModel.replace(/-(low|medium|high|xhigh|max)$/i, '');
  if (opencode_model.startsWith('9router/') && !opencode_model.startsWith('9router/ag/') && !opencode_model.startsWith('9router/oc/') && !opencode_model.startsWith('9router/mmf/')) {
    const raw = opencode_model.replace('9router/', '');
    if (raw.startsWith('gemini-') || raw.startsWith('claude-') || raw.startsWith('gpt-oss-')) {
      opencode_model = '9router/ag/' + raw;
    }
  }
  const api_provider = currentStudioSettings.api_provider || 'gemini';

  const gemini_api_key = document.getElementById('input_gemini_api_key')?.value?.trim() ?? (currentStudioSettings.gemini_api_key || '');
  const claude_api_key = document.getElementById('input_claude_api_key')?.value?.trim() ?? (currentStudioSettings.claude_api_key || '');
  const openai_api_key = document.getElementById('input_openai_api_key')?.value?.trim() ?? (currentStudioSettings.openai_api_key || '');
  const deepseek_api_key = document.getElementById('input_deepseek_api_key')?.value?.trim() ?? (currentStudioSettings.deepseek_api_key || '');
  const custom_api_key = document.getElementById('input_custom_api_key')?.value?.trim() ?? (currentStudioSettings.custom_api_key || '');
  const custom_endpoint = document.getElementById('input_custom_endpoint')?.value?.trim() ?? (currentStudioSettings.custom_endpoint || '');

  const fe_workspace = document.getElementById('input_fe_workspace')?.value?.trim() ?? (currentStudioSettings.fe_workspace || '');
  const be_workspace = document.getElementById('input_be_workspace')?.value?.trim() ?? (currentStudioSettings.be_workspace || '');
  const agy_bin = document.getElementById('input_agy_bin')?.value?.trim() ?? (currentStudioSettings.agy_bin || '');
  const opencode_bin = document.getElementById('input_opencode_bin')?.value?.trim() ?? (currentStudioSettings.opencode_bin || '');

  const jira_host = document.getElementById('input_jira_host')?.value?.trim() ?? (currentStudioSettings.jira_host || '');
  const jira_email = document.getElementById('input_jira_email')?.value?.trim() ?? (currentStudioSettings.jira_email || '');
  const jira_api_token = document.getElementById('input_jira_token')?.value?.trim() ?? (currentStudioSettings.jira_api_token || '');

  currentStudioSettings = Object.assign({}, currentStudioSettings, {
    engine,
    effort,
    model,
    opencode_model,
    api_provider,
    gemini_api_key,
    claude_api_key,
    openai_api_key,
    deepseek_api_key,
    custom_api_key,
    custom_endpoint,
    fe_workspace,
    be_workspace,
    agy_bin,
    opencode_bin,
    jira_host,
    jira_email,
    jira_api_token
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
          deepseek_api_key,
          custom_api_key,
          custom_endpoint,
          fe_workspace,
          be_workspace,
          agy_bin,
          opencode_bin,
          jira_host,
          jira_email,
          jira_api_token
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
    const agySuggest = document.getElementById('btn_suggest_agy_bin');
    if (agySuggest && envInfo.agy_bin) {
      agySuggest.textContent = envInfo.agy_bin;
      agySuggest.title = `Nhấn để áp dụng: ${envInfo.agy_bin}`;
    }
    const openSuggest = document.getElementById('btn_suggest_opencode_bin');
    if (openSuggest && envInfo.opencode_bin) {
      openSuggest.textContent = envInfo.opencode_bin;
      openSuggest.title = `Nhấn để áp dụng: ${envInfo.opencode_bin}`;
    }

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

  // Nếu bấm vào đúng tab đang active (và không có subtab mới cần chuyển)
  if (activeTab === tab &&
      (!window.initGitSubTab || window.initGitSubTab === activeGitSubTab) &&
      (!window.initSettingsSubTab || window.initSettingsSubTab === activeSettingsSubTab)) {
    return;
  }

  activeTab = tab;
  window.activeTab = tab;
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
    const sub = window.initSettingsSubTab || urlSub || activeSettingsSubTab || 'engine';
    const subRoutes = window.SETTINGS_SUBTAB_ROUTES || {
      'engine': '/settings/engine',
      'model': '/settings/model',
      'effort': '/settings/effort',
      'mcp': '/settings/mcp',
      'account': '/settings/account',
      'api': '/settings/api',
      'env': '/settings/env'
    };
    targetPath = subRoutes[sub] || '/settings/engine';
  }
  if (updateHistory && window.location.pathname !== targetPath) {
    try {
      const gitSub = window.initGitSubTab || activeGitSubTab || 'pull_sync';
      const settingsSub = window.initSettingsSubTab || activeSettingsSubTab || 'engine';
      window.history.pushState({
        tab: tab,
        subTab: tab === 'branch' ? gitSub : null,
        settingsSubTab: tab === 'settings' ? settingsSub : null
      }, '', targetPath);
    } catch (e) { }
  }

  // Cập nhật DOM hiển thị tab ngay tức thì
  TABS.forEach(t => {
    const viewEl = document.getElementById('view_' + t);
    const btnEl = document.getElementById('tabBtn_' + t);
    if (t === tab) {
      if (viewEl) {
        viewEl.classList.remove('hidden');
        if (tab === 'task') {
          viewEl.style.setProperty('display', 'grid', 'important');
        } else if (tab === 'jira' || tab === 'notes') {
          viewEl.style.setProperty('display', 'flex', 'important');
          viewEl.style.setProperty('flex-direction', 'column', 'important');
        } else {
          viewEl.style.setProperty('display', 'block', 'important');
        }
      }
      if (btnEl) {
        btnEl.className = 'px-3.5 py-1.5 rounded-md bg-[#ffffff] text-[#182c4f] font-bold shadow-sm transition text-xs cursor-pointer select-none';
      }
    } else {
      if (viewEl && (!viewEl.classList.contains('hidden') || viewEl.style.display !== 'none')) {
        viewEl.classList.add('hidden');
        viewEl.style.setProperty('display', 'none', 'important');
      }
      if (btnEl) {
        btnEl.className = 'px-3.5 py-1.5 rounded-md text-slate-200 hover:text-white hover:bg-white/10 font-medium transition text-xs cursor-pointer select-none';
      }
    }
  });

  if (window.scrollY > 0) {
    window.scrollTo({ top: 0, behavior: 'instant' });
  }

  // Quản lý subtabs tức thì trên giao diện
  if (tab === 'branch') {
    const currentPath = (window.location.pathname || '/').replace(/\/+$/, '') || '/';
    const urlSub = window.ROUTE_TO_GIT_SUBTAB && window.ROUTE_TO_GIT_SUBTAB[currentPath];
    const sub = window.initGitSubTab || urlSub || activeGitSubTab || 'pull_sync';
    activeGitSubTab = sub;
    window.initGitSubTab = sub;
    if (typeof switchGitSubTab === 'function') {
      switchGitSubTab(sub, false);
    }
  } else if (tab === 'settings') {
    const currentPath = (window.location.pathname || '/').replace(/\/+$/, '') || '/';
    const urlSub = window.ROUTE_TO_SETTINGS_SUBTAB && window.ROUTE_TO_SETTINGS_SUBTAB[currentPath];
    const sub = window.initSettingsSubTab || urlSub || activeSettingsSubTab || 'engine';
    window.initSettingsSubTab = null;
    if (typeof switchSettingsSidebarTab === 'function') {
      switchSettingsSidebarTab(sub, false);
    }
  }

  if (tab !== 'jira' && typeof stopJiraAutoSync === 'function') {
    stopJiraAutoSync();
  }

  // Nếu tải ban đầu (updateHistory = false) chạy ngay; nếu người dùng click nhanh thì debounce tránh lag
  if (!updateHistory) {
    executeTabCallback(tab);
  } else {
    clearTimeout(window._tabCallbackTimer);
    window._tabCallbackTimer = setTimeout(() => {
      if (activeTab !== tab) return;
      executeTabCallback(tab);
    }, 40);
  }
}

function executeTabCallback(tab) {
  try {
    if (tab === 'jira') {
      if (typeof loadJiraWorkspace === 'function') loadJiraWorkspace();
      if (typeof startJiraAutoSync === 'function') startJiraAutoSync();
    } else if (tab === 'task') {
      if (typeof pollStatus === 'function') pollStatus();
    } else if (tab === 'branch') {
      const sub = activeGitSubTab || 'pull_sync';
      if (sub === 'pull_sync') {
        if (typeof loadPullSyncInfo === 'function') loadPullSyncInfo();
      } else if (sub === 'switch') {
        if (typeof loadGitBranchInfo === 'function') loadGitBranchInfo();
      } else if (sub === 'cherry_pick') {
        if (typeof loadCherryPickInfo === 'function') loadCherryPickInfo();
      } else if (sub === 'merge') {
        if (typeof loadMergeInfo === 'function') loadMergeInfo();
      }
    } else if (tab === 'log') {
      if (typeof loadWorkLogs === 'function') loadWorkLogs();
    } else if (tab === 'notes') {
      if (typeof loadNotesWorkspace === 'function') loadNotesWorkspace();
    } else if (tab === 'diagram') {
      if (typeof renderDiagram === 'function') renderDiagram();
    } else if (tab === 'settings') {
      const now = Date.now();
      if (!window._lastSettingsFetchTime || (now - window._lastSettingsFetchTime > 30000)) {
        window._lastSettingsFetchTime = now;
        fetch('/api/settings')
          .then(r => r.json())
          .then(d => {
            if (activeTab !== 'settings') return;
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
            renderModelSelectForCurrentEngine();
            updateEffortUI(currentStudioSettings.effort);
            updateQuickOpencodeDisplay(currentStudioSettings.effort);
            fetchOpenCodeModels(false);
            fetchGeminiCliModels(false);
            updateApiUI(currentStudioSettings);
            updateEnvUI(currentStudioSettings, d.env_info);
            if (currentStudioSettings.jira_host) {
              const jiHost = document.getElementById('input_jira_host');
              if (jiHost && !jiHost.value) jiHost.value = currentStudioSettings.jira_host;
            }
            if (currentStudioSettings.jira_email) {
              const jiEmail = document.getElementById('input_jira_email');
              if (jiEmail && !jiEmail.value) jiEmail.value = currentStudioSettings.jira_email;
            }
            if (currentStudioSettings.jira_api_token) {
              const jiToken = document.getElementById('input_jira_token');
              if (jiToken && !jiToken.value) jiToken.value = currentStudioSettings.jira_api_token;
            }
            fetchMcpServers(false);
            markSettingsDirty(false);
          })
          .catch(() => {});
      }
    }
  } catch (err) {
    console.error('Lỗi khi kích hoạt callback của tab:', tab, err);
  }
}
window.switchTab = switchTab;

let activeGitSubTab = 'pull_sync';

function switchGitSubTab(subTab, updateHistory = true) {
  if (!['branch', 'switch', 'cherry_pick', 'pull_sync', 'merge'].includes(subTab)) subTab = 'pull_sync';
  activeGitSubTab = subTab;
  window.initGitSubTab = subTab;

  const initGitSubStyle = document.getElementById('initialGitSubTabStyle');
  if (initGitSubStyle) initGitSubStyle.remove();

  const subRoutes = window.GIT_SUBTAB_ROUTES || {
    'pull_sync': '/git-control',
    'branch': '/git-control/checkout-branch',
    'switch': '/git-control/switch-branch',
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
  const btnSwitch = document.getElementById('gitSubTabBtn_switch');
  const btnCherry = document.getElementById('gitSubTabBtn_cherry_pick');
  const btnSync = document.getElementById('gitSubTabBtn_pull_sync');
  const btnMerge = document.getElementById('gitSubTabBtn_merge');

  const viewBranch = document.getElementById('gitSubView_branch');
  const viewSwitch = document.getElementById('gitSubView_switch');
  const viewCherry = document.getElementById('gitSubView_cherry_pick');
  const viewSync = document.getElementById('gitSubView_pull_sync');
  const viewMerge = document.getElementById('gitSubView_merge');

  const isLight = document.body.classList.contains('light-mode');
  const activeCls = 'active-git-subtab px-3.5 py-1.5 rounded-md bg-[rgb(25,156,255)] text-white font-bold text-xs shadow-sm transition cursor-pointer select-none';
  const inactiveCls = isLight
    ? 'px-3.5 py-1.5 rounded-md text-[#334155] hover:text-[#0f172a] hover:bg-slate-200/60 font-medium text-xs transition cursor-pointer select-none'
    : 'px-3.5 py-1.5 rounded-md text-slate-300 hover:text-white hover:bg-white/10 font-medium text-xs transition cursor-pointer select-none';

  if (viewBranch) viewBranch.classList.add('hidden');
  if (viewSwitch) viewSwitch.classList.add('hidden');
  if (viewCherry) viewCherry.classList.add('hidden');
  if (viewSync) viewSync.classList.add('hidden');
  if (viewMerge) viewMerge.classList.add('hidden');

  if (btnBranch) btnBranch.className = inactiveCls;
  if (btnSwitch) btnSwitch.className = inactiveCls;
  if (btnCherry) btnCherry.className = inactiveCls;
  if (btnSync) btnSync.className = inactiveCls;
  if (btnMerge) btnMerge.className = inactiveCls;

  if (subTab === 'branch') {
    if (viewBranch) viewBranch.classList.remove('hidden');
    if (btnBranch) btnBranch.className = activeCls;
  } else if (subTab === 'switch') {
    if (viewSwitch) viewSwitch.classList.remove('hidden');
    if (btnSwitch) btnSwitch.className = activeCls;
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
    } else if (activeGitSubTab === 'switch' || activeGitSubTab === 'branch') {
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

function onTaskPromptInput() {
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
          error_log: task.error_log
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
          skill: task.skills.join(', ')
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
          <div class="tool-step-box my-2.5 rounded-lg border border-[#244170] bg-[#070d18] overflow-hidden shadow-inner p-3.5 space-y-2.5">
            <div class="flex items-center justify-between">
              <div class="flex items-center gap-2.5">
                <div class="wave-dots">
                  <span class="wave-dot"></span>
                  <span class="wave-dot"></span>
                  <span class="wave-dot"></span>
                </div>
                <span class="text-xs font-semibold text-cyan-300 font-sans">AI Agent đang suy nghĩ &amp; chuẩn bị tiến trình ngầm...</span>
              </div>
              <span class="text-[10.5px] font-mono text-cyan-400 bg-cyan-950/80 px-2 py-0.5 rounded border border-cyan-800 animate-pulse">Đang xử lý</span>
            </div>
            <div class="p-2.5 rounded bg-[#040810] border border-[#1e3458] text-[11px] font-mono text-slate-300 flex items-center gap-2">
              <span class="text-cyan-400 select-none font-bold">$</span>
              <span class="truncate text-slate-200">${escapeHtml(sess._statusText || t.status_text || 'Đang chuẩn bị workspace và chạy lệnh trên AI Terminal...')}</span>
            </div>
            <div class="space-y-1.5 pt-1">
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

      const changesSig = (t.changed_files || []).map(cf => `${cf.path}:${cf.status}:${cf.additions}:${cf.deletions}`).join('|');
      const currentSig = `${(t.content || '').length}_${(t.step_logs || []).length}_${t.elapsed_sec}_${isStreaming}_${Boolean(loadingPlaceholderHtml)}_${(t.step_logs || []).map(s => s.state + (s.output ? s.output.length : 0)).join(',')}_${changesSig}_${isCollapsed}_${isStepCollapsed}_${isDiffCollapsed}_${turnEngine}`;
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
              </div>
              <div class="flex items-center gap-2">
                <input id="continueInput_${taskIdKey}" type="text"
                  placeholder="Nhập yêu cầu tiếp theo (hoặc để trống để AI tiếp tục hoàn thiện task)..."
                  onkeydown="if(event.key==='Enter'){event.preventDefault();continueTaskFromFeed('${taskIdKey}');}"
                  class="flex-1 bg-[#0b1322] border border-[#244170] rounded px-3 py-1.5 text-xs text-slate-100 focus:outline-none focus:border-[#199cff]" />
                <button type="button" onclick="continueTaskFromFeed('${taskIdKey}')"
                  class="px-3.5 py-1.5 rounded bg-[#199cff] hover:bg-[#1585d8] text-white text-xs font-bold shrink-0 flex items-center gap-1.5 shadow-sm transition" style="color: #ffffff !important;">
                  <span class="text-white font-bold" style="color: #ffffff !important;">▶ Tiếp tục task</span>
                </button>
              </div>
            `;
        sessWrap.appendChild(contBox);
      } else if (contBox.parentElement === sessWrap && sessWrap.lastElementChild !== contBox) {
        sessWrap.appendChild(contBox);
      }
    } else if (contBox) {
      contBox.remove();
    }
  });
}

async function startContinuationTask(task, followUp) {
  if (!task) return;
  const anyRunning = parallelTasks.some(t => t.status === 'running' && t.id !== task.id);
  task.status = anyRunning ? 'queued' : 'running';
  renderParallelTaskTabs();
  updateTaskActionButtons();

  const followText = (followUp || '').trim() || 'Tiếp tục kiểm tra và hoàn thiện task này.';
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
    continuation: true
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
  if (!followUp && !task.prompt && !task.error_log) {
    showToast('Vui lòng nhập nội dung cần hỏi hoặc tiếp tục.', 'warning');
    return;
  }
  if (!task.original_prompt) {
    task.original_prompt = task.prompt || '';
  }
  if (inputEl) inputEl.value = '';
  activeTaskId = task.id;
  // Tiếp tục = một lượt hội thoại tiếp theo trong cùng phiên, KHÔNG chạy lại toàn bộ task
  // và KHÔNG nạp lại skill tác vụ ban đầu.
  await startContinuationTask(task, followUp);
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
    const isTesting = /testing|test|qa|uat/i.test(item.status);
    const isInProgress = item.status_category === 'indeterminate' || /in progress|doing|review/i.test(item.status);

    let statusBadgeClass = 'jira-status-todo';
    if (isDone) {
      statusBadgeClass = 'jira-status-done';
    } else if (isTesting) {
      statusBadgeClass = 'jira-status-testing';
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
          // Reset trạng thái mở/đóng khi chuyển sang Ticket khác
          if (window.jiraAttachmentsTicketKey !== issue.key) {
            window.jiraAttachmentsTicketKey = issue.key;
            window.jiraAttachmentsCollapsed = false;
          }
          renderJiraAttachments(attachments, attList);
          toggleJiraAttachments(window.jiraAttachmentsCollapsed !== true);
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
          subtasksList.innerHTML = renderSubtasksEmptyState();
        } else {
          subtasksList.innerHTML = subtasks.map(st => {
            const isDone = st.status_category === 'done' || /done|closed|resolved/i.test(st.status);
            const isTesting = /testing|test|qa|uat/i.test(st.status);
            const isInProgress = st.status_category === 'indeterminate' || /in progress|doing|review/i.test(st.status);
            let statusClass = 'jira-status-todo';
            if (isDone) statusClass = 'jira-status-done';
            else if (isTesting) statusClass = 'jira-status-testing';
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
              <div class="jira-subtask-card p-2.5 rounded-lg border flex items-center justify-between gap-3 text-xs ${isDone ? 'is-done' : ''}" data-subtask-card-key="${escapeHtml(st.key)}">
                <div class="flex items-center gap-2.5 min-w-0">
                  <a href="${escapeHtml(st.url || '#')}" target="_blank"
                    class="jira-subtask-key-badge inline-flex items-center gap-1 font-mono text-[11px] font-bold px-2 py-0.5 rounded border shrink-0 transition"
                    title="Mở Sub-task ${escapeHtml(st.key)} trên Jira Cloud">
                    <svg class="w-3 h-3 opacity-70 shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
                      <path stroke-linecap="round" stroke-linejoin="round" d="M7 7h10M7 12h10M7 17h6" />
                    </svg>
                    <span>${escapeHtml(st.key)}</span>
                  </a>
                  <span class="jira-subtask-summary text-xs font-sans truncate font-medium ${isDone ? 'is-done line-through' : ''}"
                    title="${escapeHtml(st.summary)}">${escapeHtml(st.summary)}</span>
                </div>
                <div class="flex items-center gap-2 shrink-0">
                  <!-- Custom Assignee Trigger with Avatar & Name -->
                  <button type="button"
                    onclick="openSubtaskAssigneeMenu('${escapeHtml(st.key)}', event, this)"
                    data-subtask-key="${escapeHtml(st.key)}"
                    class="jira-subtask-assignee-trigger inline-flex items-center gap-1.5 px-2.5 py-1 rounded-lg border text-xs font-sans cursor-pointer transition select-none max-w-[185px]"
                    title="Người thực hiện: ${escapeHtml(displayLabel)}${st.assignee_email ? ' (' + escapeHtml(st.assignee_email) + ')' : ''}">
                    <span class="w-4 h-4 rounded-full overflow-hidden inline-flex items-center justify-center shrink-0 text-[9.5px] font-bold subtask-avatar-box">
                      ${st.assignee_avatar
                        ? `<img src="${escapeHtml(st.assignee_avatar)}" class="w-full h-full object-cover rounded-full" alt="" />`
                        : (initial
                            ? escapeHtml(initial)
                            : `<svg class="w-2.5 h-2.5 text-slate-400" fill="currentColor" viewBox="0 0 20 20"><path fill-rule="evenodd" d="M10 9a3 3 0 100-6 3 3 0 000 6zm-7 9a7 7 0 1114 0H3z" clip-rule="evenodd"></path></svg>`)}
                    </span>
                    <span class="truncate subtask-name-box text-[11px] font-medium">${escapeHtml(displayLabel)}</span>
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
                    class="jira-subtask-status-select text-[10.5px] font-sans font-semibold px-2.5 py-1 rounded-md border ${statusClass} cursor-pointer focus:outline-none shadow-sm"
                    title="Chuyển trạng thái Sub-task">
                    ${transOptions}
                  </select>

                  <!-- Nút Xóa Sub-task -->
                  <button type="button"
                    onclick="deleteJiraSubtask('${escapeHtml(st.key)}', '${escapeHtml(st.summary)}', this)"
                    class="jira-subtask-delete-btn w-7 h-7 inline-flex items-center justify-center rounded-md border transition cursor-pointer shrink-0"
                    title="Xóa Sub-task [${escapeHtml(st.key)}]">
                    <svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24">
                      <path stroke-linecap="round" stroke-linejoin="round" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                    </svg>
                  </button>
                </div>
              </div>
            `;
          }).join('');
        }
      }

      // Render Transitions: Jira Cloud quyết định quyền chuyển trạng thái thực tế của tài khoản
      if (transitionSelect) {
        const canTransition = issue.can_transition !== false;
        const currentOpt = `<option value="" disabled selected>${escapeHtml(issue.status)} (Hiện tại)</option>`;
        if (!canTransition) {
          transitionSelect.innerHTML = currentOpt +
            '<option value="" disabled>Không có quyền chuyển trạng thái</option>';
          transitionSelect.disabled = true;
          transitionSelect.classList.add('is-locked');
          transitionSelect.title = 'Tài khoản hiện tại không có quyền chuyển trạng thái Ticket này.';
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
 * Ẩn/Hiện phần Minh chứng video & Tệp đính kèm.
 * forceExpanded: true = mở, false = đóng, bỏ trống = đảo trạng thái hiện tại.
 */
function toggleJiraAttachments(forceExpanded) {
  const list = document.getElementById('jiraDetailAttachmentsList');
  const chevron = document.getElementById('jiraAttachmentsChevron');
  if (!list) return;

  const willExpand = (typeof forceExpanded === 'boolean')
    ? forceExpanded
    : list.classList.contains('hidden');

  list.classList.toggle('hidden', !willExpand);
  if (chevron) chevron.classList.toggle('rotate-180', willExpand);
  window.jiraAttachmentsCollapsed = !willExpand;
}
window.toggleJiraAttachments = toggleJiraAttachments;

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
  const filters = ['all', 'story', 'bug', 'my', 'inprogress', 'testing', 'todo', 'done'];
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
    'testing': 'Đang kiểm thử (Testing)',
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

  // Không chặn theo assignee/reporter ở client; Jira Cloud sẽ kiểm tra quyền thực tế.
  if (issue.can_transition === false) {
    showToast('Tài khoản hiện tại không có quyền chuyển trạng thái Ticket này.', 'error');
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

function renderSubtasksEmptyState() {
  return `
    <div class="jira-subtasks-empty py-5 px-3 rounded-lg border border-dashed flex flex-col items-center justify-center gap-1.5 text-center">
      <svg class="w-5 h-5 text-slate-400/70" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="1.8">
        <path stroke-linecap="round" stroke-linejoin="round" d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2" />
      </svg>
      <p class="text-[11.5px] font-sans text-slate-400 font-medium m-0">Chưa có Sub-task nào trên ticket này.</p>
      <span class="text-[10.5px] font-sans text-slate-500">Bấm nút <span class="text-blue-500 font-medium">"+ Tạo Sub-task"</span> ở góc phải để thêm mới.</span>
    </div>
  `;
}
window.renderSubtasksEmptyState = renderSubtasksEmptyState;

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
          <span class="w-6 h-6 rounded-full bg-slate-700 overflow-hidden inline-flex items-center justify-center shrink-0 text-[10px] font-bold text-slate-200 ring-1 ring-white/10">
            ${avatarUrl
              ? `<img src="${escapeHtml(avatarUrl)}" class="block w-full h-full object-cover rounded-full" alt="" />`
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
          <span class="w-6 h-6 rounded-full bg-slate-700 overflow-hidden inline-flex items-center justify-center shrink-0 text-[10px] font-bold text-slate-200 ring-1 ring-white/10">
            ${selectedAvatar
              ? `<img src="${escapeHtml(selectedAvatar)}" class="block w-full h-full object-cover rounded-full" alt="" />`
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
          <span class="w-6 h-6 rounded-full bg-slate-700 overflow-hidden inline-flex items-center justify-center shrink-0 text-[10px] font-bold text-slate-200 ring-1 ring-white/10">
            ${avatarUrl
              ? `<img src="${escapeHtml(avatarUrl)}" class="block w-full h-full object-cover rounded-full" alt="" />`
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
 * Xóa một Sub-task trên Jira Cloud
 */
async function deleteJiraSubtask(subtaskKey, subtaskSummary, btnEl) {
  if (!subtaskKey) return;

  const currentIssue = window.activeJiraIssue;
  const parentKey = currentIssue ? currentIssue.key : '';

  const confirmMsg = subtaskSummary
    ? `Bạn có chắc chắn muốn xóa Sub-task [${subtaskKey}] "${subtaskSummary}"? Thao tác này sẽ xóa vĩnh viễn trên Jira Cloud.`
    : `Bạn có chắc chắn muốn xóa vĩnh viễn Sub-task [${subtaskKey}] trên Jira Cloud không?`;

  const confirmed = typeof antdConfirm === 'function'
    ? await antdConfirm({
        title: 'Xóa Sub-task',
        content: confirmMsg,
        okText: 'Xác nhận xóa',
        danger: true
      })
    : window.confirm(confirmMsg);

  if (!confirmed) return;

  if (btnEl) {
    btnEl.disabled = true;
    btnEl.classList.add('opacity-50', 'cursor-not-allowed');
  }

  try {
    const res = await fetch('/api/jira/delete-subtask', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ key: subtaskKey })
    });
    const d = await res.json();
    if (d && d.success) {
      showToast(`Đã xóa Sub-task [${subtaskKey}] thành công!`, 'success');

      // Cập nhật danh sách subtasks trong memory
      if (window.activeJiraIssue && Array.isArray(window.activeJiraIssue.subtasks)) {
        window.activeJiraIssue.subtasks = window.activeJiraIssue.subtasks.filter(s => s.key !== subtaskKey);
        const subtaskCount = document.getElementById('jiraSubtaskCount');
        if (subtaskCount) subtaskCount.textContent = window.activeJiraIssue.subtasks.length;
      }

      // Xóa card khỏi DOM ngay lập tức
      const card = btnEl ? btnEl.closest('.jira-subtask-card') : document.querySelector(`.jira-subtask-card[data-subtask-card-key="${subtaskKey}"]`);
      if (card) {
        card.remove();
        const subtasksList = document.getElementById('jiraSubtasksList');
        if (subtasksList && subtasksList.querySelectorAll('.jira-subtask-card').length === 0) {
          subtasksList.innerHTML = renderSubtasksEmptyState();
        }
      } else if (parentKey) {
        selectJiraIssue(parentKey, true);
      }
    } else {
      showToast((d && d.message) || `Lỗi khi xóa Sub-task [${subtaskKey}]`, 'error');
      if (btnEl) {
        btnEl.disabled = false;
        btnEl.classList.remove('opacity-50', 'cursor-not-allowed');
      }
    }
  } catch (err) {
    showToast(`Lỗi kết nối khi xóa Sub-task: ${err.message}`, 'error');
    if (btnEl) {
      btnEl.disabled = false;
      btnEl.classList.remove('opacity-50', 'cursor-not-allowed');
    }
  }
}
window.deleteJiraSubtask = deleteJiraSubtask;

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
      data.notifications.forEach((notif, idx) => {
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

        // Hiển thị toast card trượt ra từ góc trên bên phải màn hình
        setTimeout(() => {
          showJiraToastCard(notif);
        }, idx * 160);
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
 * Hiển thị Toast card thông báo Jira trượt từ góc trên bên phải màn hình
 */
function showJiraToastCard(notif) {
  if (!notif) return;

  let container = document.getElementById('jiraToastContainer');
  if (!container) {
    container = document.createElement('div');
    container.id = 'jiraToastContainer';
    container.className = 'fixed top-5 right-5 z-[9999] flex flex-col gap-3 pointer-events-none w-full max-w-sm sm:max-w-md';
    container.setAttribute('aria-live', 'polite');
    document.body.appendChild(container);
  }

  // Giới hạn tối đa 4 toast cùng lúc để không chiếm màn hình
  while (container.children.length >= 4) {
    const oldest = container.firstElementChild;
    if (oldest) container.removeChild(oldest);
    else break;
  }

  const rawId = notif.id || notif.key || Date.now();
  const safeId = String(rawId).replace(/[^a-zA-Z0-9_-]/g, '_');
  const toastId = `jiraToast_${safeId}_${Math.random().toString(36).substring(2, 6)}`;

  const isComment = notif.type === 'comment_added';
  const issueKey = notif.key || '';
  const notifType = notif.type || (isComment ? 'comment_added' : 'issue_created');

  let badgeLabel = 'JIRA CLOUD';
  let badgeColorClass = 'bg-[#1677ff]/15 text-[#60a5fa] border-[#1677ff]/30';
  let typeIconSvg = `<svg class="w-3.5 h-3.5 fill-current" viewBox="0 0 24 24"><path d="M11.53 2c0 2.4 1.97 4.35 4.4 4.35h1.78v1.7c0 2.4 1.94 4.34 4.36 4.35V2h-10.54zm-5.76 5.86c0 2.4 1.96 4.35 4.39 4.35h1.79v1.7c0 2.4 1.94 4.35 4.36 4.35V7.86H5.77zm-5.77 5.87c0 2.4 1.97 4.34 4.4 4.34h1.78v1.71c0 2.4 1.94 4.35 4.36 4.35v-10.4H0v-.002z"/></svg>`;

  if (isComment) {
    badgeLabel = 'BÌNH LUẬN MỚI';
    badgeColorClass = 'bg-sky-500/15 text-sky-400 border-sky-500/30';
    typeIconSvg = `<svg class="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z"/></svg>`;
  } else if (notif.issuetype) {
    badgeLabel = notif.issuetype.toUpperCase();
  } else {
    badgeLabel = 'TASK MỚI';
  }

  const cardTitle = isComment
    ? (notif.author ? `${notif.author} vừa bình luận` : `Bình luận mới trên ${issueKey || 'Ticket'}`)
    : (notif.summary || notif.title || `Cập nhật Jira ${issueKey}`);

  let cardBody = '';
  if (isComment) {
    cardBody = notif.comment_body || notif.message || notif.summary || '';
  } else {
    if (notif.summary && notif.author) {
      cardBody = `${notif.author} vừa tạo: ${notif.summary}`;
    } else {
      cardBody = notif.message || notif.summary || notif.title || '';
    }
  }

  let timeStr = 'Vừa xong';
  if (notif.created) {
    try {
      const dt = new Date(notif.created);
      if (!isNaN(dt.getTime())) {
        timeStr = dt.toLocaleTimeString('vi-VN', { hour: '2-digit', minute: '2-digit' });
      }
    } catch (e) { }
  }

  const toastCard = document.createElement('div');
  toastCard.id = toastId;
  toastCard.className = 'jira-notif-toast';
  toastCard.setAttribute('role', 'alert');
  toastCard.onclick = () => {
    if (issueKey) {
      onJiraNotificationClick(issueKey, notifType);
    }
    dismissJiraNotification(toastId);
  };

  toastCard.innerHTML = `
    <div class="flex items-center justify-between gap-2 pb-2 mb-2 border-b border-[#244170] jira-toast-divider">
      <div class="flex items-center gap-1.5 min-w-0">
        <span class="inline-flex items-center justify-center w-5 h-5 rounded bg-[#1677ff]/20 text-[#1677ff] shrink-0">
          ${typeIconSvg}
        </span>
        <span class="px-1.5 py-0.5 rounded text-[10px] font-semibold border uppercase tracking-wider ${badgeColorClass}">
          ${escapeHtml(badgeLabel)}
        </span>
        ${issueKey ? `<span class="px-1.5 py-0.2 rounded text-[11px] font-mono font-bold bg-[#1677ff]/20 text-[#60a5fa] border border-[#1677ff]/30 shrink-0">${escapeHtml(issueKey)}</span>` : ''}
      </div>
      <div class="flex items-center gap-2 shrink-0">
        <span class="text-[11px] text-slate-400 jira-toast-meta font-sans">${escapeHtml(timeStr)}</span>
        <button type="button" class="jira-toast-close-btn p-1 rounded text-slate-400 hover:text-white hover:bg-white/10 transition cursor-pointer"
          title="Đóng thông báo" onclick="event.stopPropagation(); dismissJiraNotification('${toastId}');">
          <svg class="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
            <path stroke-linecap="round" stroke-linejoin="round" d="M6 18L18 6M6 6l12 12"/>
          </svg>
        </button>
      </div>
    </div>
    <div class="mb-2.5">
      <div class="text-[12.5px] font-semibold text-white jira-toast-title line-clamp-1 mb-1 font-sans leading-snug">
        ${escapeHtml(cardTitle)}
      </div>
      <div class="text-[11.5px] text-slate-300 jira-toast-body line-clamp-2 font-sans leading-relaxed">
        ${escapeHtml(cardBody)}
      </div>
    </div>
    <div class="flex items-center justify-between pt-1.5 border-t border-[#1a3055] jira-toast-divider text-[11px]">
      <span class="text-slate-400 jira-toast-meta flex items-center gap-1">
        <span class="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse"></span>
        <span>Nhấp để mở chi tiết</span>
      </span>
      <button type="button" class="px-2.5 py-1 rounded bg-[#1677ff] hover:bg-[#0958d9] text-white font-medium text-[11px] transition shadow-sm flex items-center gap-1 cursor-pointer"
        onclick="event.stopPropagation(); if ('${escapeHtml(issueKey)}') onJiraNotificationClick('${escapeHtml(issueKey)}', '${escapeHtml(notifType)}'); dismissJiraNotification('${toastId}');">
        <span>Xem Ticket</span>
        <svg class="w-3 h-3" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
          <path stroke-linecap="round" stroke-linejoin="round" d="M9 5l7 7-7 7"/>
        </svg>
      </button>
    </div>
  `;

  // Tự động đóng sau 8 giây (tạm dừng khi rê chuột)
  let autoDismissTimer = setTimeout(() => {
    dismissJiraNotification(toastId);
  }, 8000);

  toastCard.addEventListener('mouseenter', () => {
    if (autoDismissTimer) clearTimeout(autoDismissTimer);
  });
  toastCard.addEventListener('mouseleave', () => {
    autoDismissTimer = setTimeout(() => {
      dismissJiraNotification(toastId);
    }, 3500);
  });

  container.appendChild(toastCard);
}
window.showJiraToastCard = showJiraToastCard;

function showJiraInteractiveNotification(notif) {
  if (!notif || !notif.key) return;
  if (typeof addOrUpdateNotification === 'function') {
    const notifId = `jira_${notif.id || notif.key}`;
    const exists = typeof _savedNotifications !== 'undefined' && _savedNotifications.some(n => n.id === notifId);
    if (!exists) {
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
  }
  showJiraToastCard(notif);
}
window.showJiraInteractiveNotification = showJiraInteractiveNotification;

function dismissJiraNotification(elId) {
  const el = document.getElementById(elId);
  if (!el) return;
  el.style.pointerEvents = 'none';
  el.classList.add('jira-notif-toast-closing');
  el.style.opacity = '0';
  el.style.transform = 'translateX(115%)';
  setTimeout(() => {
    if (el && el.parentNode) el.parentNode.removeChild(el);
  }, 260);
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

  TABS.forEach(t => {
    const btn = document.getElementById('tabBtn_' + t);
    if (btn) {
      btn.addEventListener('click', (e) => {
        e.preventDefault();
        switchTab(t);
      });
    }
  });

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
