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

/**
 * Mở modal xem trước ảnh phóng to (Lightbox Modal)
 */
function openImagePreviewModal(url, title = '') {
  if (!url) return;
  const root = document.getElementById('imagePreviewModalRoot');
  const img = document.getElementById('imagePreviewModalImg');
  const titleEl = document.getElementById('imagePreviewModalTitle');
  const link = document.getElementById('imagePreviewModalLink');
  if (!root || !img) return;

  img.src = url;
  if (titleEl) titleEl.textContent = title || 'Ảnh minh chứng';
  if (link) link.href = url;
  root.classList.remove('hidden');
}
window.openImagePreviewModal = openImagePreviewModal;

/**
 * Đóng modal xem trước ảnh
 */
function closeImagePreviewModal() {
  const root = document.getElementById('imagePreviewModalRoot');
  const img = document.getElementById('imagePreviewModalImg');
  if (!root) return;
  root.classList.add('hidden');
  if (img) img.src = '';
}
window.closeImagePreviewModal = closeImagePreviewModal;

document.addEventListener('keydown', (e) => {
  if (e.key === 'Escape') {
    closeImagePreviewModal();
  }
});
