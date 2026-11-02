#!/usr/bin/env python3
"""Quét mã nguồn Frontend & Backend và dựng sơ đồ kiến trúc liên kết Module ↔ API ↔ Controller."""

import datetime
import glob
import os
import re

from config import FE_WORKSPACE, BE_WORKSPACE, get_fe_workspace, get_be_workspace
from studio.state import app_state, state_lock
from studio.git_ops import get_git_info

def get_custom_skills():
    """Quét thư mục .agents/skills/ của cả Frontend và Backend để lấy các skill thực tế."""
    def scan_skills_dir(workspace, role):
        skills_dir = os.path.join(workspace, '.agents', 'skills')
        results = []
        if os.path.isdir(skills_dir):
            for name in sorted(os.listdir(skills_dir)):
                full_path = os.path.join(skills_dir, name)
                if os.path.isdir(full_path):
                    skill_md = os.path.join(full_path, 'SKILL.md')
                    desc = ''
                    if os.path.isfile(skill_md):
                        try:
                            with open(skill_md, 'r', encoding='utf-8') as f:
                                content = f.read()
                                if 'description:' in content:
                                    part = content.split('description:', 1)[1]
                                    if part.strip().startswith('>-') or part.strip().startswith('>'):
                                        d_lines = []
                                        for line in part.splitlines()[1:]:
                                            if line.strip() == '---':
                                                break
                                            d_lines.append(line.strip())
                                        desc = ' '.join(d_lines)
                                    else:
                                        desc = part.splitlines()[0].strip()
                        except Exception:
                            pass
                    results.append({
                        'name': name,
                        'desc': desc,
                        'role': role
                    })
        return results

    fe_skills = scan_skills_dir(get_fe_workspace(), 'fe')
    be_skills = scan_skills_dir(get_be_workspace(), 'be')
    return {
        'fe': fe_skills,
        'be': be_skills
    }



CORE_MODULE_CONFIGS = [
    {
        'id': 'booking-bedroom',
        'title': 'Phòng & Sơ đồ giường (BedRoom)',
        'name': 'Phòng & Sơ đồ giường (BedRoom)',
        'category': 'core',
        'skill': 'skill-booking-bedroom',
        'primary_route': '/bed-room-position',
        'primary_resource': 'src/scripts/restful/resources/bed-room/bedRoomPosition.ts',
        'fe_routes': [
            'src/scripts/routes/setting/bed-room',
            'src/scripts/routes/setting/bed-room-manager'
        ],
        'fe_forms': [
            'src/scripts/forms/bed-room',
            'src/scripts/forms/bed-room-manager'
        ],
        'fe_resources': [
            'src/scripts/restful/resources/bed-room/bedRoomPosition.ts',
            'src/scripts/restful/resources/bed-room/bedRoomManager.ts'
        ],
        'fe_dirs': ['bed-room'],
        'be_controllers': ['BedRoomPositionController', 'BedRoomManagerController'],
        'default_desc': 'Quản lý bản đồ sơ đồ giường, trạng thái ghế bận/trống realtime, phân bổ dịch vụ và cấu hình vị trí giường.'
    },
    {
        'id': 'pos-cashier',
        'title': 'Thu ngân & Bán hàng (POS / Invoice)',
        'name': 'Thu ngân & Bán hàng (POS / Invoice)',
        'category': 'core',
        'skill': 'skill-pos-cashier',
        'primary_route': '/invoices',
        'primary_resource': 'src/scripts/restful/resources/invoice.ts',
        'fe_routes': [
            'src/scripts/routes/cashier',
            'src/scripts/routes/invoice'
        ],
        'fe_forms': [
            'src/scripts/forms/invoice'
        ],
        'fe_resources': [
            'src/scripts/restful/resources/invoice.ts',
            'src/scripts/restful/resources/invoiceDetail.ts',
            'src/scripts/restful/resources/invoiceDetailProductUsage.ts'
        ],
        'fe_dirs': ['invoice', 'invoice-detail'],
        'be_controllers': ['InvoicesController', 'CashiersController', 'InvoiceStaffArrangementsController'],
        'default_desc': 'Màn hình thu ngân POS, chọn dịch vụ/sản phẩm/combo, áp khuyến mãi, chia bill, in phiếu hóa đơn.'
    },
    {
        'id': 'calendar-schedule',
        'title': 'Lịch hẹn & Ca làm việc (Booking / Calendar)',
        'name': 'Lịch hẹn & Ca làm việc (Booking / Calendar)',
        'category': 'core',
        'skill': 'skill-calendar-schedule',
        'primary_route': '/bookings',
        'primary_resource': 'src/scripts/restful/resources/booking/booking.ts',
        'fe_routes': [
            'src/scripts/routes/booking',
            'src/scripts/routes/setting/booking-site'
        ],
        'fe_forms': [
            'src/scripts/forms/booking'
        ],
        'fe_resources': [
            'src/scripts/restful/resources/booking/booking.ts',
            'src/scripts/restful/resources/bookingPlatformLimit.ts',
            'src/scripts/restful/resources/bookingPortalSetting.ts'
        ],
        'fe_dirs': ['booking', 'booking-detail'],
        'be_controllers': ['BookingsController', 'BookingAvailableStaffsController'],
        'default_desc': 'Lịch biểu đặt hẹn theo nhân viên, khung giờ, check-in khách đến salon và đẩy vào danh sách chờ.'
    },
    {
        'id': 'customer-crm',
        'title': 'Khách hàng & Hạng thẻ VIP (Customer CRM)',
        'name': 'Khách hàng & Hạng thẻ VIP (Customer CRM)',
        'category': 'core',
        'skill': 'skill-customer-crm',
        'primary_route': '/customers',
        'primary_resource': 'src/scripts/restful/resources/customer/customer.ts',
        'fe_routes': [
            'src/scripts/routes/customer',
            'src/scripts/routes/setting/customer-rank',
            'src/scripts/routes/setting/customer-group',
            'src/scripts/routes/setting/customer-source',
            'src/scripts/routes/setting/customer-channel'
        ],
        'fe_forms': [
            'src/scripts/forms/customer',
            'src/scripts/forms/customer-debt-transaction',
            'src/scripts/forms/customer-rank'
        ],
        'fe_resources': [
            'src/scripts/restful/resources/customer/customer.ts',
            'src/scripts/restful/resources/customer/customerDebt.ts',
            'src/scripts/restful/resources/customer/customerRank.ts'
        ],
        'fe_dirs': ['customer', 'customer-care-history', 'customer-channel'],
        'be_controllers': ['CustomersController', 'CustomerDebtsController', 'CustomerRanksController'],
        'default_desc': 'Hồ sơ khách hàng, phân hạng thẻ VIP, tích lũy điểm thưởng, quản lý công nợ và lịch sử làm đẹp.'
    },
    {
        'id': 'warehouse-inventory',
        'title': 'Kho hàng & Nhập xuất tồn (Warehouse)',
        'name': 'Kho hàng & Nhập xuất tồn (Warehouse)',
        'category': 'core',
        'skill': 'skill-warehouse-inventory',
        'primary_route': '/warehouses',
        'primary_resource': 'src/scripts/restful/resources/warehouse/warehouse.ts',
        'fe_routes': [
            'src/scripts/routes/product-service/warehouse',
            'src/scripts/routes/product-service/warehouse-detail'
        ],
        'fe_forms': [
            'src/scripts/forms/warehouse-transaction',
            'src/scripts/forms/warehouse-transaction-detail'
        ],
        'fe_resources': [
            'src/scripts/restful/resources/warehouse/warehouse.ts',
            'src/scripts/restful/resources/warehouse/warehouseTransaction.ts',
            'src/scripts/restful/resources/warehouse/warehouseTransactionDetail.ts'
        ],
        'fe_dirs': ['warehouse-transaction'],
        'be_controllers': ['WarehousesController', 'WarehouseTransactionsController', 'V2_WarehouseTransactionDetailsController'],
        'default_desc': 'Xuất nhập tồn, trừ kho hàng bán & định mức tiêu hao nguyên vật liệu, kiểm kê, cảnh báo tồn tối thiểu.'
    },
    {
        'id': 'commission-setup',
        'title': 'Hoa hồng & Chiết khấu KTV (Commission)',
        'name': 'Hoa hồng & Chiết khấu KTV (Commission)',
        'category': 'core',
        'skill': 'skill-commission-setup',
        'primary_route': '/commission-arrangements',
        'primary_resource': 'src/scripts/restful/resources/commissionArrange.ts',
        'fe_routes': [
            'src/scripts/routes/setting/commission',
            'src/scripts/routes/setting/commission-new'
        ],
        'fe_forms': [
            'src/scripts/forms/commission'
        ],
        'fe_resources': [
            'src/scripts/restful/resources/commissionArrange.ts',
            'src/scripts/restful/resources/commission/commissionProduct.ts',
            'src/scripts/restful/resources/commission/commissionService.ts'
        ],
        'fe_dirs': ['commission-setup', 'commission-product', 'commission-service', 'commission-cashcard'],
        'be_controllers': ['CommissionArrangementsController', 'CommissionProductsController'],
        'default_desc': 'Cấu hình hoa hồng theo bậc nhân viên, dịch vụ, bán sản phẩm, làm tour; tính thưởng tức thì theo bill.'
    },
    {
        'id': 'revenue-expenditure',
        'title': 'Thu chi & Sổ quỹ tiền mặt (Cashbook)',
        'name': 'Thu chi & Sổ quỹ tiền mặt (Cashbook)',
        'category': 'core',
        'skill': 'skill-revenue-expenditure',
        'primary_route': '/cash-book-transactions',
        'primary_resource': 'src/scripts/restful/resources/cashbook/cashbookTransaction.ts',
        'fe_routes': [
            'src/scripts/routes/revenue-expenditure'
        ],
        'fe_forms': [
            'src/scripts/forms/cashbook-transaction',
            'src/scripts/forms/cashbook-setting'
        ],
        'fe_resources': [
            'src/scripts/restful/resources/cashbook/cashbookTransaction.ts',
            'src/scripts/restful/resources/cashbook/cashbookSetting.ts'
        ],
        'fe_dirs': ['cashbook-transaction', 'cashbook-setting'],
        'be_controllers': ['CashBookTransactionsController', 'CashBooksController'],
        'default_desc': 'Tổng hợp phiếu thu bán lẻ, phiếu chi nhập kho, phiếu chi lương; theo dõi dòng tiền mặt và ngân hàng.'
    },
    {
        'id': 'service-package-combo',
        'title': 'Gói liệu trình & Thẻ combo (Package)',
        'name': 'Gói liệu trình & Thẻ combo (Package)',
        'category': 'core',
        'skill': 'skill-service-package-combo',
        'primary_route': '/customer-packages',
        'primary_resource': 'src/scripts/restful/resources/package/package.ts',
        'fe_routes': [
            'src/scripts/routes/product-service/package',
            'src/scripts/routes/product-service/treatment'
        ],
        'fe_forms': [
            'src/scripts/forms/package',
            'src/scripts/forms/customer-treatment'
        ],
        'fe_resources': [
            'src/scripts/restful/resources/package/package.ts',
            'src/scripts/restful/resources/customer/customerPackage.ts',
            'src/scripts/restful/resources/customer-treatment/customerTreatment.ts'
        ],
        'fe_dirs': ['package', 'customer-treatment'],
        'be_controllers': ['CustomerPackagesController', 'CustomerTreatmentController', 'PackagesController'],
        'default_desc': 'Bán gói liệu trình nhiều buổi, trừ buổi tự động khi khách làm tại giường, gia hạn thẻ liệu trình.'
    },
    {
        'id': 'tax-einvoice',
        'title': 'Hóa đơn điện tử (E-Invoice)',
        'name': 'Hóa đơn điện tử (E-Invoice)',
        'category': 'core',
        'skill': 'skill-tax-einvoice',
        'primary_route': '/electronic-invoices',
        'primary_resource': 'src/scripts/restful/resources/e-invoice/electronicInvoice.ts',
        'fe_routes': [
            'src/scripts/routes/tax-accounting',
            'src/scripts/routes/setting/electronic-invoice'
        ],
        'fe_forms': [
            'src/scripts/forms/electronic-invoice',
            'src/scripts/forms/tax-accounting'
        ],
        'fe_resources': [
            'src/scripts/restful/resources/e-invoice/electronicInvoice.ts',
            'src/scripts/restful/resources/e-invoice/electronicInvoicePartner.ts',
            'src/scripts/restful/resources/tax-accounting/tax-declaration-management/taxPeriod.ts'
        ],
        'fe_dirs': ['electronic-invoice'],
        'be_controllers': ['ElectronicInvoicesController', 'ElectronicInvoicePartnersController'],
        'default_desc': 'Kết nối VNPT, Viettel, MISA phát hành hóa đơn điện tử hợp lệ theo quy định của Tổng cục Thuế.'
    },
    {
        'id': 'payroll-timesheet',
        'title': 'Chấm công & Bảng lương (Payroll)',
        'name': 'Chấm công & Bảng lương (Payroll)',
        'category': 'core',
        'skill': 'skill-payroll-timesheet',
        'primary_route': '/time-sheets',
        'primary_resource': 'src/scripts/restful/resources/time-sheets/timeSheet.ts',
        'fe_routes': [
            'src/scripts/routes/worker-management'
        ],
        'fe_forms': [
            'src/scripts/forms/time-sheet',
            'src/scripts/forms/worker'
        ],
        'fe_resources': [
            'src/scripts/restful/resources/time-sheets/timeSheet.ts',
            'src/scripts/restful/resources/time-sheets/timeSheetSetting.ts',
            'src/scripts/restful/resources/worker/worker.ts'
        ],
        'fe_dirs': ['time-sheet'],
        'be_controllers': ['TimeSheetsController'],
        'default_desc': 'Tổng hợp ngày công, ca kíp, phạt đi muộn và tiền hoa hồng trong tháng để chốt phiếu lương nhân viên.'
    },
    {
        'id': 'report-analytics',
        'title': 'Báo cáo & Thống kê (Analytics)',
        'name': 'Báo cáo & Thống kê (Analytics)',
        'category': 'core',
        'skill': 'skill-report-analytics',
        'primary_route': '/report',
        'primary_resource': 'src/scripts/restful/resources/report/reportRevenue.ts',
        'fe_routes': [
            'src/scripts/routes/reports'
        ],
        'fe_forms': [],
        'fe_resources': [
            'src/scripts/restful/resources/report/reportRevenue.ts',
            'src/scripts/restful/resources/report/reportInvoice.ts',
            'src/scripts/restful/resources/report/reportCustomer.ts'
        ],
        'fe_dirs': ['report'],
        'be_controllers': ['ReportController', 'InvoiceReportController'],
        'default_desc': 'Dashboard doanh thu bán lẻ, tỷ lệ lấp đầy giường, hiệu suất kỹ thuật viên và lợi nhuận gộp.'
    }
]

# -------------------------------------------------------------
# VERIFIED 11-MODULE ARCHITECTURE CATALOG (EasySalon WebApp & API)
# -------------------------------------------------------------
MODULE_VERIFIED_DATA = {
    'booking-bedroom': {
        'screens': ['RouteBedRoomPosition.tsx', 'RouteBedRoomManager.tsx'],
        'components': ['BedRoomContainer.tsx', 'BedRoomPositionTable.tsx', 'BedRoomPositionForm.tsx'],
        'resources': ['bedRoomPosition.ts', 'bedRoomManager.ts'],
        'route': '/bed-room-position',
        'endpoints': [
            {'method': 'GET', 'path': '/bed-room-position', 'note': 'Lấy danh sách vị trí giường'},
            {'method': 'POST', 'path': '/bed-room-position', 'note': 'Tạo vị trí giường mới'},
            {'method': 'PUT', 'path': '/bed-room-position/{id}', 'note': 'Cập nhật cấu hình giường'},
            {'method': 'DELETE', 'path': '/bed-room-position/{id}', 'note': 'Xóa vị trí giường'}
        ],
        'controller': 'BedRoomPositionController',
        'service': 'BedRoomPositionService',
        'manager': 'BedRoomPositionManager',
        'entities': ['BedRoomPosition', 'BedRoom']
    },
    'pos-cashier': {
        'screens': ['RouteCashier.tsx', 'RouteInvoiceList.tsx'],
        'components': ['InvoiceContent.tsx', 'InvoiceDetails.tsx', 'InvoiceFooter.tsx'],
        'resources': ['invoice.ts', 'invoiceDetail.ts'],
        'route': '/invoices',
        'endpoints': [
            {'method': 'GET', 'path': '/invoices', 'note': 'Tra cứu danh sách hóa đơn'},
            {'method': 'POST', 'path': '/invoices', 'note': 'Khởi tạo bill mới tại quầy'},
            {'method': 'PUT', 'path': '/invoices/pay-invoice/{id}', 'note': 'Thanh toán hóa đơn đa phương thức'},
            {'method': 'PUT', 'path': '/cashiers/invoice/{invoiceId}', 'note': 'Cập nhật giỏ hàng thu ngân POS'}
        ],
        'controller': 'InvoicesController',
        'service': 'InvoiceService',
        'manager': 'InvoiceManager',
        'entities': ['Invoice', 'InvoiceDetail', 'InvoicePayment']
    },
    'calendar-schedule': {
        'screens': ['RouteBooking.tsx'],
        'components': ['BookingsFetcher.tsx', 'BookingFormControl.tsx', 'BookingDetailServiceItem.tsx'],
        'resources': ['booking.ts', 'bookingAvailableStaff.ts'],
        'route': '/bookings',
        'endpoints': [
            {'method': 'GET', 'path': '/bookings', 'note': 'Lấy danh sách lịch hẹn theo khung giờ'},
            {'method': 'POST', 'path': '/bookings', 'note': 'Tạo lịch hẹn mới'},
            {'method': 'PUT', 'path': '/bookings/{id}', 'note': 'Cập nhật thông tin / đổi giờ hẹn'},
            {'method': 'PUT', 'path': '/bookings/checkin/{id}', 'note': 'Check-in khách đến salon'}
        ],
        'controller': 'BookingsController',
        'service': 'BookingService',
        'manager': 'BookingManager',
        'entities': ['Booking', 'BookingDetail', 'BookingDetailStaff']
    },
    'customer-crm': {
        'screens': ['RouteCustomer.tsx', 'RouteCustomerDetail.tsx'],
        'components': ['CustomerTable.tsx', 'CustomerFilter.tsx', 'CustomerFormButton.tsx'],
        'resources': ['customer.ts', 'customerDebt.ts', 'customerRank.ts'],
        'route': '/customers',
        'endpoints': [
            {'method': 'GET', 'path': '/customers', 'note': 'Tìm kiếm và phân trang hồ sơ khách'},
            {'method': 'POST', 'path': '/customers', 'note': 'Tạo hồ sơ khách hàng mới (Unicode FormC)'},
            {'method': 'PUT', 'path': '/customers/{id}', 'note': 'Cập nhật thông tin khách hàng'},
            {'method': 'GET', 'path': '/customers/debts', 'note': 'Tra cứu công nợ khách hàng'}
        ],
        'controller': 'CustomersController',
        'service': 'CustomerService',
        'manager': 'CustomerManager',
        'entities': ['Customer', 'CustomerDebt', 'CustomerRank']
    },
    'warehouse-inventory': {
        'screens': ['RouteWarehouse.tsx', 'RouteWarehouseDetail.tsx'],
        'components': ['WarehouseTransactionTable.tsx', 'WarehouseTransactionForm.tsx'],
        'resources': ['warehouse.ts', 'warehouseTransaction.ts'],
        'route': '/warehouses',
        'endpoints': [
            {'method': 'GET', 'path': '/warehouses', 'note': 'Tồn kho thực tế theo sản phẩm'},
            {'method': 'GET', 'path': '/warehouses/product/inventories', 'note': 'Tồn kho sản phẩm theo chi nhánh'},
            {'method': 'GET', 'path': '/warehouse-transactions', 'note': 'Danh sách phiếu nhập / xuất kho'},
            {'method': 'POST', 'path': '/warehouse-transactions', 'note': 'Tạo phiếu nhập/xuất kho'}
        ],
        'controller': 'WarehousesController',
        'service': 'WarehouseService',
        'manager': 'WarehouseManager',
        'entities': ['Warehouse', 'WarehouseTransaction', 'WarehouseTransactionDetail']
    },
    'commission-setup': {
        'screens': ['RouteCommission.tsx'],
        'components': ['CommissionTableContainer.tsx', 'CommissionServiceFormControl.tsx', 'CommissionProductFormControl.tsx'],
        'resources': ['commissionArrange.ts', 'commissionService.ts', 'commissionProduct.ts'],
        'route': '/commission-arrangements',
        'endpoints': [
            {'method': 'GET', 'path': '/commission-arrangements', 'note': 'Tra cứu hoa hồng theo hóa đơn'},
            {'method': 'PUT', 'path': '/commission-arrangements/{id}', 'note': 'Lưu chia hoa hồng KTV cho hóa đơn'},
            {'method': 'GET', 'path': '/commission-services', 'note': 'Cấu hình hoa hồng dịch vụ'},
            {'method': 'PUT', 'path': '/commission-products', 'note': 'Lưu cấu hình hoa hồng sản phẩm'}
        ],
        'controller': 'CommissionArrangementsController',
        'service': 'CommissionArrangementService',
        'manager': 'CommissionArrangementManager',
        'entities': ['CommissionArrangement', 'CommissionService', 'CommissionProduct']
    },
    'revenue-expenditure': {
        'screens': ['RouteCashbook.tsx', 'RouteBankBook.tsx'],
        'components': ['CashbookTransactionTable.tsx', 'CashbookTransactionFormButton.tsx'],
        'resources': ['cashbookTransaction.ts', 'cashbookSetting.ts'],
        'route': '/cash-book-transactions',
        'endpoints': [
            {'method': 'GET', 'path': '/cash-book-transactions', 'note': 'Danh sách phiếu thu / phiếu chi'},
            {'method': 'POST', 'path': '/cash-book-transactions', 'note': 'Lập phiếu thu chi mới'},
            {'method': 'PUT', 'path': '/cash-book-transactions/{id}', 'note': 'Cập nhật chứng từ thu chi'},
            {'method': 'GET', 'path': '/cash-books', 'note': 'Số dư và tồn quỹ tiền mặt'}
        ],
        'controller': 'CashBookTransactionsController',
        'service': 'CashBookTransactionService',
        'manager': 'CashBookTransactionManager',
        'entities': ['CashBookTransaction', 'CashBook', 'BankBook']
    },
    'service-package-combo': {
        'screens': ['RoutePackage.tsx', 'RouteCustomerTreatment.tsx'],
        'components': ['PackageTable.tsx', 'CustomerTreatmentUseForm.tsx'],
        'resources': ['package.ts', 'customerTreatment.ts', 'customerPackage.ts'],
        'route': '/customer-packages',
        'endpoints': [
            {'method': 'GET', 'path': '/customer-packages', 'note': 'Danh sách các gói combo và thẻ liệu trình'},
            {'method': 'POST', 'path': '/customer-packages', 'note': 'Tạo gói dịch vụ combo mới'},
            {'method': 'GET', 'path': '/customer-treatments/by-customer/{customerId}', 'note': 'Tra cứu số buổi liệu trình của khách'},
            {'method': 'POST', 'path': '/customer-treatments/{id}/use', 'note': 'Trừ buổi liệu trình khi làm dịch vụ tại giường'}
        ],
        'controller': 'CustomerPackagesController',
        'service': 'CustomerPackageService',
        'manager': 'CustomerPackageManager',
        'entities': ['CustomerPackage', 'CustomerTreatment', 'Package']
    },
    'tax-einvoice': {
        'screens': ['RouteEInvoiceList.tsx', 'RouteElectronicInvoicePartner.tsx'],
        'components': ['ElectronicInvoiceTable.tsx', 'ElectronicInvoiceHandleButton.tsx'],
        'resources': ['electronicInvoice.ts', 'electronicInvoicePartner.ts'],
        'route': '/electronic-invoices',
        'endpoints': [
            {'method': 'GET', 'path': '/electronic-invoices', 'note': 'Danh sách hóa đơn điện tử đã phát hành'},
            {'method': 'POST', 'path': '/electronic-invoices', 'note': 'Ký số và phát hành HĐĐT chính thức'},
            {'method': 'POST', 'path': '/electronic-invoices/draft', 'note': 'Xuất bản HĐĐT nháp (Draft)'},
            {'method': 'GET', 'path': '/electronic-invoice-partners', 'note': 'Danh sách kết nối đối tác VNPT, Viettel, MISA'}
        ],
        'controller': 'ElectronicInvoicesController',
        'service': 'ElectronicInvoiceService',
        'manager': 'ElectronicInvoiceManager',
        'entities': ['ElectronicInvoice', 'ElectronicInvoicePartner']
    },
    'payroll-timesheet': {
        'screens': ['RouteTimeSheet.tsx', 'RoutePayroll.tsx'],
        'components': ['TimeSheetContainer.tsx', 'TimeSheetActionFormButton.tsx'],
        'resources': ['timeSheet.ts', 'worker.ts'],
        'route': '/time-sheets',
        'endpoints': [
            {'method': 'GET', 'path': '/time-sheets', 'note': 'Bảng chấm công tổng hợp trong kỳ'},
            {'method': 'GET', 'path': '/time-sheets/overview', 'note': 'Tổng kết ngày công, đi muộn, về sớm'},
            {'method': 'POST', 'path': '/time-sheets', 'note': 'Chốt công thủ công cho nhân viên'},
            {'method': 'GET', 'path': '/worker-advance-payments', 'note': 'Danh sách tạm ứng lương nhân viên'}
        ],
        'controller': 'TimeSheetsController',
        'service': 'TimeSheetService',
        'manager': 'TimeSheetManager',
        'entities': ['TimeSheet', 'Worker', 'WorkerAdvancePayment']
    },
    'report-analytics': {
        'screens': ['RouteReportRevenue.tsx', 'RouteReportCustomer.tsx'],
        'components': ['ReportRevenueInvoiceDetail.tsx', 'ReportRevenueServiceDetail.tsx'],
        'resources': ['reportRevenue.ts', 'reportCustomer.ts'],
        'route': '/report',
        'endpoints': [
            {'method': 'GET', 'path': '/report/revenue-invoice-detail', 'note': 'Chi tiết doanh thu theo hóa đơn'},
            {'method': 'GET', 'path': '/report/revenue-service-detail', 'note': 'Doanh thu phân tích theo dịch vụ'},
            {'method': 'GET', 'path': '/report/revenue-payment-method-general', 'note': 'Cơ cấu doanh thu theo phương thức thanh toán'},
            {'method': 'GET', 'path': '/report/customer-frequency', 'note': 'Tần suất khách quay lại salon'}
        ],
        'controller': 'ReportController',
        'service': 'ReportService',
        'manager': 'ReportManager',
        'entities': ['Invoice View', 'Customer View', 'Staff View']
    }
}



def _is_preferred_api_caller_name(fn_name: str) -> bool:
    if not fn_name:
        return False
    low = fn_name.lower()
    if low.startswith(('on', 'handle', 'render', 'use', 'set', 'toggle', 'open', 'close')):
        return False
    return low.startswith((
        'fetch', 'load', 'get', 'create', 'update', 'upsert', 'delete',
        'remove', 'request', 'search', 'check', 'cancel', 'restore',
        'import', 'export', 'preview', 'submit', 'save', 'pay'
    ))


def extract_caller_functions_from_ts(content):
    """
    Quét nội dung file .ts/.tsx để tìm tên hàm (function / const arrow function) thực sự gọi API resource:
    Ví dụ:
      const fetchDataBedRoomPositions = async () => { ... bedRoomPositionResources.getAll ... }
      const createBedRoomPosition = (values) => { ... bedRoomPositionResources.create ... }
    Trả về dict: { 'bedRoomPositionResources.getAll': 'fetchDataBedRoomPositions', 'getAll': ... }
    """
    caller_map = {}
    if not content or ('Resources' not in content and 'Resource' not in content and 'fetchResource' not in content and 'request(' not in content):
        return caller_map

    # Tìm tất cả định nghĩa hàm / arrow function trong file
    func_Header_pattern = re.compile(
        r'(?:export\s+)?(?:const|let|var)\s+([a-zA-Z0-9_$]+)\s*=\s*(?:async\s*)?(?:\([^)]*\)|[a-zA-Z0-9_$]+)\s*=>|'
        r'(?:export\s+)?(?:async\s+)?function\s+([a-zA-Z0-9_$]+)\s*\('
    )
    matches = list(func_Header_pattern.finditer(content))
    for idx, m in enumerate(matches):
        fn_name = m.group(1) or m.group(2)
        if not fn_name or fn_name in ('Component', 'render', 'useEffect', 'useCallback', 'useMemo'):
            continue
        if fn_name.lower().startswith(('on', 'handle')) and len(matches) > 1:
            continue
        start_pos = m.start()
        end_pos = matches[idx + 1].start() if idx + 1 < len(matches) else min(len(content), start_pos + 1200)
        snippet = content[start_pos:end_pos]

        # Bắt các lệnh gọi <resObj>.<prop> (VD: bedRoomPositionResources.getAll)
        for rm in re.finditer(r'\b([a-zA-Z0-9_$]*Resources?)\.([a-zA-Z0-9_$]+)\b', snippet):
            res_obj, res_prop = rm.group(1), rm.group(2)
            key_full = f"{res_obj}.{res_prop}"
            if key_full not in caller_map or (_is_preferred_api_caller_name(fn_name) and not _is_preferred_api_caller_name(caller_map[key_full])):
                caller_map[key_full] = fn_name

        # Bắt các lệnh gọi trực tiếp biến resource đơn lẻ trong fetchResource(xxx) hoặc request(xxx)
        for dm in re.finditer(r'(?:fetchResource|request)\s*\(\s*([a-zA-Z0-9_$]+)\b', snippet):
            res_var = dm.group(1)
            if res_var not in caller_map or (_is_preferred_api_caller_name(fn_name) and not _is_preferred_api_caller_name(caller_map[res_var])):
                caller_map[res_var] = fn_name

    return caller_map


_GLOBAL_FE_CALLER_MAP = None


def get_global_fe_caller_map(base_dir):
    global _GLOBAL_FE_CALLER_MAP
    if _GLOBAL_FE_CALLER_MAP is not None:
        return _GLOBAL_FE_CALLER_MAP

    caller_map = {}
    scripts_dir = os.path.join(base_dir, 'src', 'scripts')
    if os.path.isdir(scripts_dir):
        for root, _, files in os.walk(scripts_dir):
            if 'restful' in root.replace('\\', '/').split('/'):
                continue
            for f in files:
                if f.endswith(('.tsx', '.ts')) and not f.endswith('.d.ts'):
                    fpath = os.path.join(root, f)
                    try:
                        with open(fpath, 'r', encoding='utf-8', errors='ignore') as fp:
                            sub_map = extract_caller_functions_from_ts(fp.read())
                            for k, v in sub_map.items():
                                if k not in caller_map:
                                    caller_map[k] = v
                    except Exception:
                        pass
    _GLOBAL_FE_CALLER_MAP = caller_map
    return caller_map


GENERIC_RESOURCE_PROPS = {
    'getall', 'getbyid', 'get', 'create', 'update', 'delete', 'remove',
    'post', 'put', 'patch', 'list', 'detail', 'execute', 'fetch'
}


def parse_resource_file(file_path, caller_map=None):
    """
    Trích xuất tên hàm caller thực tế ở Frontend (ví dụ fetchDataBedRoomPositions, createBedRoomPosition...),
    HTTP Method và URL endpoint thực tế từ file Resource TypeScript + Caller Map.
    """
    endpoints = []
    if not os.path.isfile(file_path):
        return endpoints
    try:
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as fp:
            content = fp.read()

        # Tìm tên object Resource export trong file (VD: export const bedRoomPositionResources = { ... })
        res_obj_m = re.search(r'export\s+const\s+([a-zA-Z0-9_$]*Resources?)\s*=', content)
        res_obj_name = res_obj_m.group(1) if res_obj_m else ''

        matches = re.finditer(
            r'(?:(?:const|let|var)\s+([a-zA-Z0-9_$]+)\s*=\s*|([a-zA-Z0-9_$]+)\s*:\s*)?new\s+Resource(?:<[\s\S]*?>)?\s*\(\s*\{([\s\S]*?)\}\s*\)',
            content
        )
        for m in matches:
            raw_prop = m.group(1) or m.group(2) or ''
            body = m.group(3)
            url_m = re.search(r'url\s*:\s*[`\'"]([^`\'"]+)[`\'"]', body)
            if not url_m:
                continue
            raw_url = url_m.group(1).strip()

            # Chuẩn hóa URL path
            if raw_url.startswith('./'):
                url = raw_url[1:]
            elif not raw_url.startswith('/'):
                url = '/' + raw_url
            else:
                url = raw_url
            url = url.replace('/./', '/')
            url = re.sub(r'/+', '/', url)
            url = re.sub(r':([a-zA-Z_0-9]+)', r'{\1}', url)

            method_m = re.search(r'method\s*:\s*[\'"](GET|POST|PUT|DELETE|PATCH)[\'"]', body, re.IGNORECASE)
            method = method_m.group(1).upper() if method_m else 'GET'

            # Ưu tiên lấy hàm caller thực tế gọi API này từ KNOWN_FE_CALLER_FUNCS hoặc các container/component/form
            norm_generic = re.sub(r'\{[a-zA-Z0-9_]+\}', '{id}', url)
            fe_func = KNOWN_FE_CALLER_FUNCS.get((method, norm_generic), '')
            if not fe_func and caller_map and raw_prop:
                if res_obj_name and f"{res_obj_name}.{raw_prop}" in caller_map:
                    fe_func = caller_map[f"{res_obj_name}.{raw_prop}"]
                elif raw_prop in caller_map:
                    fe_func = caller_map[raw_prop]

            # Nếu raw_prop là tên generic (getAll, create, update, delete...) hoặc trống -> suy luận tên hàm call API chuẩn
            if not fe_func:
                if raw_prop and raw_prop.lower() not in GENERIC_RESOURCE_PROPS:
                    fe_func = raw_prop
                else:
                    fe_func = infer_fe_func(method, url)

            note = ''
            if '{id}' in url:
                if method == 'GET': note = 'Lấy chi tiết theo ID'
                elif method == 'PUT': note = 'Cập nhật bản ghi theo ID'
                elif method == 'DELETE': note = 'Xóa bản ghi theo ID'
            elif method == 'GET': note = 'Lấy danh sách dữ liệu'
            elif method == 'POST': note = 'Tạo mới bản ghi'
            elif method == 'PUT': note = 'Cập nhật thông tin'
            elif method == 'DELETE': note = 'Xóa thông tin'

            if not any(e['method'] == method and e['path'] == url for e in endpoints):
                endpoints.append({'method': method, 'path': url, 'fe_func': fe_func, 'note': note})
    except Exception:
        pass
    return endpoints


def scan_fe_directory(base_dir, target):
    """
    Quét động cấu trúc mã nguồn Frontend (React) từ easysalon-webapp:
    - Screens: Các file Route*.tsx, Router*.tsx từ src/scripts/routes/
    - Components: Các React component tương tác từ routes/ và forms/
    - Resources: Định nghĩa RESTful Resource từ src/scripts/restful/resources/
    - Endpoints: Danh sách API contract thực tế kèm tên hàm FE call API thực tế
    """
    if isinstance(target, dict):
        cfg = target
        routes_dirs = cfg.get('fe_routes', [])
        forms_dirs = cfg.get('fe_forms', [])
        res_targets = cfg.get('fe_resources', [])
        primary_res_preset = cfg.get('primary_resource', '')
        primary_route_preset = cfg.get('primary_route', '')
        mod_id = cfg.get('id', '')
    elif isinstance(target, (list, tuple)):
        routes_dirs = [f'src/scripts/routes/{d}' for d in target] + [f'src/scripts/business/{d}' for d in target]
        forms_dirs = [f'src/scripts/forms/{d}' for d in target]
        res_targets = [f'src/scripts/restful/resources/{d}' for d in target] + [f'src/scripts/restful/resources/{d}.ts' for d in target]
        primary_res_preset = ''
        primary_route_preset = ''
        mod_id = target[0] if target else 'module'
    else:
        routes_dirs, forms_dirs, res_targets = [], [], []
        primary_res_preset, primary_route_preset, mod_id = '', '', 'module'

    screens = []
    components = []
    resources = []
    found_paths = []
    imports = set()
    exports = set()
    endpoints = []
    primary_resource = primary_res_preset
    primary_path = ''
    local_caller_map = dict(get_global_fe_caller_map(base_dir))

    # 1. Quét Routes & Trích xuất các hàm gọi API thực tế
    for r_dir in routes_dirs:
        full_dir = os.path.join(base_dir, r_dir)
        if os.path.exists(full_dir):
            if not primary_path:
                primary_path = r_dir
            found_paths.append(r_dir)
            for root, _, files in os.walk(full_dir):
                for f in sorted(files):
                    if f.endswith(('.tsx', '.ts')) and not f.startswith('index'):
                        file_path = os.path.join(root, f)
                        if f.startswith(('Route', 'Router')):
                            screens.append(f)
                        else:
                            components.append(f)
                        try:
                            with open(file_path, 'r', encoding='utf-8', errors='ignore') as fp:
                                content = fp.read()
                                local_caller_map.update(extract_caller_functions_from_ts(content))
                                for m in re.finditer(r"from\s+['\"](@/[^'\"]+|libs/[^'\"]+)['\"]", content):
                                    imports.add(m.group(1))
                                for m in re.finditer(r"export\s+(?:default\s+)?(?:const|function|class|interface|type)\s+([A-Za-z0-9_]+)", content):
                                    exports.add(m.group(1))
                        except Exception:
                            pass

    # 2. Quét Forms & Trích xuất các hàm gọi API thực tế
    for f_dir in forms_dirs:
        full_dir = os.path.join(base_dir, f_dir)
        if os.path.exists(full_dir):
            found_paths.append(f_dir)
            for root, _, files in os.walk(full_dir):
                for f in sorted(files):
                    if f.endswith(('.tsx', '.ts')) and not f.startswith('index'):
                        file_path = os.path.join(root, f)
                        components.append(f)
                        try:
                            with open(file_path, 'r', encoding='utf-8', errors='ignore') as fp:
                                content = fp.read()
                                local_caller_map.update(extract_caller_functions_from_ts(content))
                                for m in re.finditer(r"from\s+['\"](@/[^'\"]+|libs/[^'\"]+)['\"]", content):
                                    imports.add(m.group(1))
                                for m in re.finditer(r"export\s+(?:default\s+)?(?:const|function|class|interface|type)\s+([A-Za-z0-9_]+)", content):
                                    exports.add(m.group(1))
                        except Exception:
                            pass

    # 3. Quét Resources & Trích xuất Endpoints kèm tên hàm FE caller
    for res_target in res_targets:
        full_target = os.path.join(base_dir, res_target)
        if os.path.isfile(full_target):
            rel_res = res_target
            if not primary_resource:
                primary_resource = rel_res
            resources.append(os.path.basename(full_target))
            endpoints.extend(parse_resource_file(full_target, caller_map=local_caller_map))
        elif os.path.isdir(full_target):
            for root, _, files in os.walk(full_target):
                for f in sorted(files):
                    if f.endswith('.ts') and not f.startswith('index'):
                        fpath = os.path.join(root, f)
                        rel_res = os.path.relpath(fpath, base_dir)
                        if not primary_resource:
                            primary_resource = rel_res
                        resources.append(f)
                        endpoints.extend(parse_resource_file(fpath, caller_map=local_caller_map))

    screens = sorted(list(set(screens)))
    components = sorted(list(set(components)))
    resources = sorted(list(set(resources)))

    if primary_route_preset:
        primary_route = primary_route_preset
    elif endpoints:
        primary_route = endpoints[0]['path']
    else:
        primary_route = f'/{mod_id}'

    primary_clean = '/' + primary_route.strip('/').split('/')[0]
    def ep_rank(ep):
        p = ep['path']
        m = ep['method']
        score = 10
        if p.rstrip('/') == primary_clean:
            if m == 'GET': score = 1
            elif m == 'POST': score = 2
        elif p.rstrip('/') == f'{primary_clean}/{{id}}':
            if m == 'PUT': score = 3
            elif m == 'DELETE': score = 4
            elif m == 'GET': score = 5
        return (score, p, m)

    sorted_endpoints = sorted(endpoints, key=ep_rank)

    return {
        'screens': screens,
        'components': components,
        'resources': resources,
        'endpoints': sorted_endpoints,
        'route': primary_route,
        'paths': found_paths,
        'path': primary_path or (found_paths[0] if found_paths else f'src/scripts/routes/{mod_id}'),
        'resource': primary_resource or f'src/scripts/restful/resources/{mod_id}.ts',
        'imports': sorted(list(imports))[:8],
        'exports': sorted(list(exports))[:8]
    }


def to_kebab_case(s):
    """Converts PascalCase / CamelCase string to kebab-case."""
    if not s:
        return ''
    s = re.sub(r'(?:Base)?Controller$', '', s)
    s = re.sub(r'^V\d+_', '', s)
    s = re.sub(r'([a-z0-9])([A-Z])', r'\1-\2', s).lower()
    return s


def resolve_controller_route(content, controller_name):
    """
    Extracts and resolves base route from ASP.NET Core controller C# content.
    Handles:
    - [Route("path")]
    - [Route("[controller]")] -> replaces with kebab-case controller name
    - Multiple [Route] attributes (filters obsolete routes, selects kebab-case)
    """
    route_matches = re.findall(r'\[Route\("([^"]+)"\)(?:\s*//\s*(Obsolete))?', content, re.IGNORECASE)
    if route_matches:
        valid_routes = [r[0] for r in route_matches if not r[1]]
        if not valid_routes:
            valid_routes = [r[0] for r in route_matches]

        kebab_candidates = [r for r in valid_routes if '-' in r or r.islower()]
        chosen_route = kebab_candidates[0] if kebab_candidates else valid_routes[0]

        if '[controller]' in chosen_route.lower():
            kebab_cname = to_kebab_case(controller_name)
            chosen_route = re.sub(r'\[controller\]', kebab_cname, chosen_route, flags=re.IGNORECASE)
        elif not chosen_route.startswith('/') and not chosen_route.startswith('api/'):
            if chosen_route.isalnum() and any(c.isupper() for c in chosen_route):
                chosen_route = to_kebab_case(chosen_route)

        return chosen_route.strip('/')

    return to_kebab_case(controller_name)


def generate_endpoint_note(action_name, verb, path):
    """Generates natural, accurate Vietnamese descriptions for API endpoints."""
    act = action_name.lower()
    if 'cancel' in act:
        return 'Hủy trạng thái giao dịch'
    if 'export' in act:
        return 'Xuất báo cáo dữ liệu Excel'
    if 'print' in act:
        return 'Dữ liệu in chứng từ / phiếu'
    if 'draft' in act:
        return 'Tạo bản ghi nháp (Draft)'
    if 'preview' in act:
        return 'Xem trước mẫu chứng từ'
    if 'revenue' in act:
        return 'Báo cáo phân tích doanh thu'
    if 'checkin' in act:
        return 'Khách check-in tại quầy'
    if 'nearest' in act:
        return 'Lấy lịch hẹn gần nhất'
    if 'search' in act or 'bymobile' in act:
        return 'Tìm kiếm nhanh theo từ khóa / SĐT'
    if 'group' in act:
        return 'Tổng hợp theo nhóm danh mục'
    if 'overview' in act:
        return 'Báo cáo tổng quan số liệu'
    if 'pay' in act and 'paymentmethod' not in act:
        return 'Thanh toán giao dịch hóa đơn'

    if verb == 'GET':
        if '{id}' in path or act.endswith('byid'):
            return 'Xem chi tiết theo mã ID'
        if 'bycustomer' in act or 'by-customer' in path:
            return 'Tra cứu lịch sử theo khách hàng'
        return 'Truy vấn danh sách dữ liệu'
    elif verb == 'POST':
        return 'Tạo mới bản ghi'
    elif verb == 'PUT':
        if '{id}' in path:
            return 'Cập nhật thông tin bản ghi'
        return 'Cập nhật dữ liệu'
    elif verb == 'DELETE':
        return 'Xóa bản ghi khỏi hệ thống'
    return f'{action_name} action'


def extract_action_endpoints(content, base_route):
    """
    Extracts HTTP verb attributes, action method names, and constructs genuine endpoint paths.
    Eliminates artificial /{route}/{action_name} concatenation.
    """
    action_pattern = re.compile(
        r'\[Http(Get|Post|Put|Delete|Patch)(?:\(\s*["\']([^"\']*)["\']\s*\))?[^\]]*\]'
        r'(?:[\s\r\n]*\[[^\]]+\])*'
        r'[\s\r\n]*public\s+(?:async\s+)?(?:Task<)?([^\s>]+)>?\s+([A-Za-z0-9_]+)\s*\(([^)]*)\)',
        re.MULTILINE
    )

    endpoints = []
    seen = set()

    for m in action_pattern.finditer(content):
        verb = m.group(1).upper()
        tpl = (m.group(2) or '').strip()
        action_name = m.group(4)

        # Resolve true path template without method name concatenation
        if not tpl:
            path = '/' + base_route.strip('/')
        elif tpl.startswith('/') or tpl.startswith('~/'):
            path = '/' + tpl.lstrip('~/')
        else:
            path = '/' + base_route.strip('/') + '/' + tpl.strip('/')

        path = re.sub(r':([a-zA-Z_0-9]+)', r'{\1}', path)
        if '[controller]' in path.lower():
            path = re.sub(r'\[controller\]', base_route.strip('/'), path, flags=re.IGNORECASE)

        key = (verb, path)
        if key in seen:
            continue
        seen.add(key)

        note = generate_endpoint_note(action_name, verb, path)
        endpoints.append({
            'method': verb,
            'path': path,
            'action': action_name,
            'be_action': action_name,
            'note': note
        })

    return endpoints


def trace_downstream_chain(base_dir, controller_name, controller_content, injections):
    """
    Traces Controller -> ApplicationService<T> -> Domain Manager -> Entity
    from the .NET project layout in SALON_HAIR_CORE and SALON_HAIR_ENTITY.
    """
    base_name = controller_name.replace('Controller', '')
    base_name = re.sub(r'^V\d+_', '', base_name)
    singular = base_name.rstrip('s') if base_name.endswith('s') and not base_name.endswith('ss') else base_name

    candidates = [f"{base_name}Service", f"{singular}Service", f"{base_name}Manager", f"{singular}Manager"]
    service_name = None
    for cand in candidates:
        if cand in injections:
            service_name = cand
            break
    if not service_name:
        for cand in candidates:
            if cand.endswith('Service') and glob.glob(os.path.join(base_dir, 'SALON_HAIR_CORE/Services/**/' + cand + '.cs'), recursive=True):
                service_name = cand
                break
    if not service_name:
        for inj in injections:
            if inj.endswith('Service') and inj not in ('UserService', 'ValuesService', 'AppModulePermissionService', 'SalonBranchService', 'StreamExcelService', 'ExcelService', 'FirebaseDatabaseService'):
                service_name = inj
                break
    if not service_name:
        service_name = f"{singular}Service"

    entity_name = singular
    manager_name = f"{singular}Manager"

    smatches = glob.glob(os.path.join(base_dir, 'SALON_HAIR_CORE/Services/**/' + service_name + '.cs'), recursive=True)
    if smatches:
        try:
            with open(smatches[0], 'r', encoding='utf-8', errors='ignore') as fp:
                scontent = fp.read()
            em = re.search(r'ApplicationService<([A-Za-z0-9_]+)>', scontent)
            if em:
                entity_name = em.group(1)

            mgr_candidates = [f"{base_name}Manager", f"{singular}Manager", f"{entity_name}Manager"]
            for mc in mgr_candidates:
                if mc in scontent:
                    manager_name = mc
                    break
            if not manager_name or manager_name == f"{singular}Manager":
                sm = re.search(r'public\s+' + service_name + r'\s*\((.*?)\)', scontent, re.DOTALL)
                if sm:
                    for p in sm.group(1).split(','):
                        parts = p.strip().split()
                        if len(parts) >= 2 and parts[0].endswith('Manager') and parts[0] not in ('DomainService', 'Manager'):
                            manager_name = parts[0]
                            break
        except Exception:
            pass

    ent_dir = os.path.join(base_dir, 'SALON_HAIR_ENTITY/Entities')
    known_entities = set()
    if os.path.exists(ent_dir):
        try:
            for f in os.listdir(ent_dir):
                if f.endswith('.cs'):
                    known_entities.add(f[:-3])
        except Exception:
            pass

    entities = [entity_name] if entity_name in known_entities else [singular]
    for e in sorted(known_entities):
        if e != entities[0] and (e.startswith(entities[0]) or entities[0] in e) and len(entities) < 4:
            entities.append(e)

    return {
        'service': service_name,
        'manager': manager_name,
        'entity': entities[0],
        'entities': entities,
        'be_stack_str': f"{controller_name} → {service_name} → {entities[0]} Entity"
    }


def scan_be_controllers(base_dir, controller_names):
    """
    Scans backend controllers in SALON_HAIR_API, resolves exact routes,
    parses true action endpoints, and traces downstream services/managers/entities.
    """
    found_controllers = []
    primary_controller = controller_names[0] if controller_names else ''
    primary_path = ''
    primary_route = ''
    all_injections = set()
    primary_injections = []
    endpoints = []
    primary_content = ''

    for idx, cname in enumerate(controller_names):
        pattern = os.path.join(base_dir, 'SALON_HAIR_API/**/' + cname + '.cs')
        matches = glob.glob(pattern, recursive=True)
        if matches:
            fpath = matches[0]
            rel_path = fpath.replace(base_dir.rstrip('/') + '/', '')
            found_controllers.append(cname)
            if not primary_path:
                primary_path = rel_path
                primary_controller = cname

            try:
                with open(fpath, 'r', encoding='utf-8', errors='ignore') as fp:
                    content = fp.read()

                if not primary_content and idx == 0:
                    primary_content = content

                c_route = resolve_controller_route(content, cname)
                if not primary_route:
                    primary_route = c_route

                ctor_match = re.search(r'public\s+' + cname + r'\s*\((.*?)\)', content, re.DOTALL)
                if not ctor_match:
                    ctor_match = re.search(r'public\s+(?:[A-Za-z0-9_]+)\s*\((.*?)\)', content, re.DOTALL)

                c_injections = []
                if ctor_match:
                    params = ctor_match.group(1).split(',')
                    for p in params:
                        parts = p.strip().split()
                        if len(parts) >= 2 and not parts[0].startswith('//'):
                            all_injections.add(parts[0])
                            c_injections.append(parts[0])

                if idx == 0:
                    primary_injections = c_injections

                c_endpoints = extract_action_endpoints(content, c_route)
                if idx == 0:
                    endpoints.extend(c_endpoints)
                else:
                    for ep in c_endpoints:
                        if not any(e['path'] == ep['path'] and e['method'] == ep['method'] for e in endpoints):
                            endpoints.append(ep)
            except Exception:
                pass

    if not primary_route and controller_names:
        primary_route = to_kebab_case(controller_names[0])

    chain = trace_downstream_chain(base_dir, primary_controller, primary_content, primary_injections)

    return {
        'controllers': found_controllers,
        'primary_controller': primary_controller,
        'path': primary_path or f'SALON_HAIR_API/Controllers/{primary_controller}.cs',
        'route': primary_route,
        'injections': sorted(list(all_injections))[:8],
        'actions': [f"{ep['method']} {ep['action']}()" for ep in endpoints][:8],
        'endpoints': endpoints,
        'service': chain['service'],
        'manager': chain['manager'],
        'entity': chain['entity'],
        'entities': chain['entities'],
        'be_stack_str': chain['be_stack_str']
    }


def build_mermaid_code(modules, fe_branch, be_branch):
    """
    Tự động xây dựng mã Mermaid Flowchart động dựa trên mã nguồn thực tế của nhánh hiện tại.
    Liên kết 3 tầng: Frontend Screens -> API Contracts (có HTTP verbs) -> Backend Controllers/Services.
    Bảo đảm 100% cú pháp Mermaid v10, giữ nguyên quy tắc ID để click highlight mượt mà.
    """
    def clean(s):
        if not s:
            return ''
        s = str(s).replace('"', "'")
        s = re.sub(r'[\r\n]+', ' ', s)
        s = s.replace('[', '(').replace(']', ')')
        s = s.replace('{', '(').replace('}', ')')
        return re.sub(r'\s+', ' ', s).strip()

    lines = [
        'flowchart LR',
        f'    subgraph FE ["FRONTEND ({clean(fe_branch)})"]',
        '        direction TB'
    ]
    for m in modules:
        token = re.sub(r'[^a-zA-Z0-9]', '_', m['id']).upper()
        nid = f'FE_{token}'
        title = clean(m.get('title', m['id']).split('(')[0].strip())
        screens = m.get('fe', {}).get('screens', [])
        screen_sub = clean(screens[0]) if screens else clean(m.get('fe', {}).get('path', ''))
        res = m.get('fe', {}).get('resources', [])
        res_sub = clean(res[0]) if res else ''
        sub_text = f'{screen_sub}' + (f'<br/><i>{res_sub}</i>' if res_sub else '')
        lines.append(f'        {nid}["<b>{title}</b><br/>{sub_text}"]')
    lines.append('    end')

    lines.append('    subgraph API ["RESTful API CONTRACTS"]')
    lines.append('        direction TB')
    for m in modules:
        token = re.sub(r'[^a-zA-Z0-9]', '_', m['id']).upper()
        nid = f'API_{token}'
        route = clean(m.get('api', {}).get('route', f'/{m["id"]}'))
        endpoints = m.get('api', {}).get('endpoints', [])
        verbs = []
        for ep in endpoints:
            v = clean(ep.get('method', 'GET').upper().replace('HTTP', ''))
            badge = f'[{v}]'
            if badge not in verbs:
                verbs.append(badge)
        verbs_str = ' '.join(verbs[:4]) if verbs else '[GET] [POST]'
        first_note = clean(endpoints[0].get('note', '')) if endpoints else ''
        lines.append(f'        {nid}["<b>{route}</b><br/>{verbs_str}<br/><i>{first_note}</i>"]')
    lines.append('    end')

    lines.append(f'    subgraph BE ["BACKEND ({clean(be_branch)})"]')
    lines.append('        direction TB')
    for m in modules:
        token = re.sub(r'[^a-zA-Z0-9]', '_', m['id']).upper()
        nid = f'BE_{token}'
        controller = clean(m.get('be', {}).get('controller', '').split(':')[0].strip().split()[0])
        service = clean(m.get('be', {}).get('service', '')) or (controller.replace('Controller', '') + 'Service')
        entities = m.get('be', {}).get('entities', [])
        ent_str = clean(', '.join(entities[:2])) if isinstance(entities, list) else clean(str(entities))
        lines.append(f'        {nid}["<b>{controller}</b><br/>↳ {service}<br/><i>Entity: {ent_str}</i>"]')
    lines.append('    end')

    lines.append('    %% Liên kết kết nối 2 đầu Frontend <==> Backend')
    for m in modules:
        token = re.sub(r'[^a-zA-Z0-9]', '_', m['id']).upper()
        fe_nid = f'FE_{token}'
        api_nid = f'API_{token}'
        be_nid = f'BE_{token}'
        lines.append(f'    {fe_nid} ==>|gọi RESTful API| {api_nid}')
        lines.append(f'    {api_nid} ==>|xử lý Controller & Service| {be_nid}')

    return '\n'.join(lines)


def build_tree_nodes(modules):
    """
    Xây dựng cấu trúc cây phân cấp 4 tầng nghiệp vụ hoàn chỉnh (Feature 5 / R2):
      - Cấp 1 (Gốc/Module): type='module', id='tree-{mod_id}'
      - Cấp 2 (Màn hình / Component FE): type='fe_component', id='tree-fe-{mod_id}-{g_idx}'
      - Cấp 3 (API Contract): type='api_contract', id='tree-api-{mod_id}-{g_idx}-{ep_idx}-{method}'
      - Cấp 4 (Backend .NET Stack): type='be_stack', id='tree-be-{mod_id}-{g_idx}-{ep_idx}-{method}'
    Bảo đảm 100% ID node là duy nhất toàn cục và đầy đủ liên kết.
    """
    tree_nodes = []
    seen_ids = set()

    for m in modules:
        mod_id = m['id']
        mod_name = m.get('title') or m.get('name', mod_id)
        l1_id = f'tree-{mod_id}'
        l1_node = {
            'id': l1_id,
            'name': mod_name,
            'type': 'module',
            'category': m.get('category', 'core'),
            'children': []
        }
        seen_ids.add(l1_id)

        fe = m.get('fe', {})
        screens = fe.get('screens', [])
        components = fe.get('components', [])

        api = m.get('api', {})
        endpoints = api.get('endpoints', [])
        base_route = api.get('route', f'/{mod_id}')
        if not endpoints:
            endpoints = [{'method': 'GET', 'path': base_route, 'note': 'Truy vấn danh sách'}]

        be = m.get('be', {})
        controller = be.get('controller', f'{mod_id.capitalize()}Controller')
        controller_clean = controller.split(':')[0].strip().split()[0]
        service = be.get('service') or (controller_clean.replace('Controller', '') + 'Service')
        entities = be.get('entities') or [controller_clean.replace('Controller', '')]
        entity_str = ', '.join(entities[:2]) if isinstance(entities, list) else str(entities)

        if len(screens) >= 2:
            half = max(1, len(endpoints) // 2)
            c1 = components[0] if components else ''
            c2 = components[1] if len(components) > 1 else ''
            groups = [
                (f'Frontend: {screens[0]}' + (f' / {c1}' if c1 else ''), endpoints[:half], 0),
                (f'Frontend: {screens[1]}' + (f' / {c2}' if c2 else ''), endpoints[half:], 1)
            ]
        else:
            s_name = screens[0] if screens else f'Route{controller_clean.replace("Controller", "")}.tsx'
            c_name = components[0] if components else 'Container.tsx'
            groups = [(f'Frontend: {s_name} / {c_name}', endpoints, 0)]

        for fe_name, ep_list, g_idx in groups:
            if not ep_list:
                ep_list = endpoints
            l2_id = f'tree-fe-{mod_id}-{g_idx}'
            l2_node = {
                'id': l2_id,
                'name': fe_name,
                'type': 'fe_component',
                'children': []
            }
            seen_ids.add(l2_id)

            for ep_idx, ep in enumerate(ep_list):
                method = ep.get('method', 'GET').upper().replace('HTTP', '')
                path = ep.get('path', base_route)
                note = ep.get('note', '')
                l3_id = f'tree-api-{mod_id}-{g_idx}-{ep_idx}-{method.lower()}'
                suffix = 0
                orig_l3_id = l3_id
                while l3_id in seen_ids:
                    suffix += 1
                    l3_id = f'{orig_l3_id}-{suffix}'
                seen_ids.add(l3_id)

                l3_node = {
                    'id': l3_id,
                    'name': f'[{method}] {path}',
                    'method': method,
                    'path': path,
                    'note': note,
                    'type': 'api_contract',
                    'children': []
                }

                l4_id = f'tree-be-{mod_id}-{g_idx}-{ep_idx}-{method.lower()}'
                if suffix > 0:
                    l4_id = f'{l4_id}-{suffix}'
                while l4_id in seen_ids:
                    suffix += 1
                    l4_id = f'tree-be-{mod_id}-{g_idx}-{ep_idx}-{method.lower()}-{suffix}'
                seen_ids.add(l4_id)

                be_stack_name = f'{controller_clean} → {service} → {entity_str} Entity'
                l4_node = {
                    'id': l4_id,
                    'name': be_stack_name,
                    'controller': controller_clean,
                    'service': service,
                    'type': 'be_stack',
                    'children': []
                }

                l3_node['children'].append(l4_node)
                l2_node['children'].append(l3_node)

            l1_node['children'].append(l2_node)

        tree_nodes.append(l1_node)

    return tree_nodes


def normalize_endpoint_path(p):
    if not p:
        return '', ''
    p = p.strip()
    if p.startswith('./'):
        p = p[1:]
    if not p.startswith('/'):
        p = '/' + p
    p = re.sub(r'/+', '/', p)
    p = re.sub(r':([a-zA-Z0-9_]+)', r'{\1}', p)
    p_generic = re.sub(r'\{[a-zA-Z0-9_]+\}', r'{id}', p)
    p_norm = p_generic.lower().replace('-', '').replace('_', '')
    return p, p_norm


def _path_to_pascal_entity(path):
    """Chuyển route '/bed-room-position/{id}' -> ('BedRoomPosition', 'BedRoomPositions')"""
    segments = [
        s for s in path.strip('/').split('/')
        if s and not s.startswith('{') and not s.startswith(':') and s.lower() not in ('api', 'v1', 'v2')
    ]
    base_seg = segments[0] if segments else 'item'
    words = [w.capitalize() for w in re.split(r'[-_]+', base_seg) if w]
    pascal = ''.join(words) or 'Item'
    if pascal.endswith('ies'):
        singular = pascal[:-3] + 'y'
        plural = pascal
    elif pascal.endswith('s') and not pascal.endswith('ss'):
        singular = pascal[:-1]
        plural = pascal
    else:
        singular = pascal
        plural = pascal + 's'
    return singular, plural


KNOWN_FE_CALLER_FUNCS = {
    ('GET', '/bed-room-position'): 'fetchDataBedRoomPositions',
    ('POST', '/bed-room-position'): 'createBedRoomPosition',
    ('PUT', '/bed-room-position/{id}'): 'updateBedRoomPosition',
    ('DELETE', '/bed-room-position/{id}'): 'deleteBedRoomPosition',
    ('GET', '/bed-room'): 'fetchRooms',
    ('POST', '/bed-room'): 'createBedRoomManager',
    ('PUT', '/bed-room/{id}'): 'updateBedRoomManager',
    ('DELETE', '/bed-room/{id}'): 'deleteBedRoomManager',
    ('GET', '/invoices'): 'fetchInvoices',
    ('GET', '/invoices/{id}'): 'fetchInvoiceDetail',
    ('POST', '/invoices'): 'createInvoice',
    ('PUT', '/invoices/{id}'): 'updateInvoice',
    ('PUT', '/invoices/pay-invoice/{id}'): 'createInvoicePayment',
    ('PUT', '/invoices/cancel-payment/{id}'): 'cancelInvoicePayment',
    ('DELETE', '/invoices/{id}'): 'deleteInvoice',
    ('GET', '/bookings'): 'loadBookings',
    ('GET', '/bookings/nearest'): 'requestNearestBookings',
    ('POST', '/bookings'): 'upsertBooking',
    ('PUT', '/bookings/{id}'): 'upsertBooking',
    ('PUT', '/bookings/checkin/{id}'): 'checkinBooking',
    ('DELETE', '/bookings/{id}'): 'deleteBooking',
    ('GET', '/customers'): 'fetchCustomers',
    ('GET', '/customers/search'): 'searchCustomerByKey',
    ('POST', '/customers'): 'upsertCustomer',
    ('PUT', '/customers/{id}'): 'upsertCustomer',
    ('PUT', '/customers/restore/{id}'): 'restoreCustomer',
    ('DELETE', '/customers/{id}'): 'deleteCustomer',
    ('GET', '/warehouses'): 'fetchWarehouseResource',
    ('POST', '/warehouse-transactions'): 'createWarehouseTransaction',
    ('PUT', '/warehouse-transaction-details/{id}'): 'upsertWarehouseTransactionDetail',
    ('DELETE', '/warehouse-transaction-details/{id}'): 'deleteWarehouseTransactionDetail',
    ('GET', '/cashbook-transactions'): 'fetchCashbookTransactions',
    ('GET', '/cashbook-transactions/print'): 'fetchCashBookTransactionPrint',
    ('POST', '/cashbook-transactions'): 'upsertCashbookTransaction',
    ('PUT', '/cashbook-transactions/{id}'): 'upsertCashbookTransaction',
    ('DELETE', '/cashbook-transactions/{id}'): 'deleteCashbookTransaction',
    ('GET', '/packages'): 'searchPackageByName',
    ('POST', '/packages'): 'upsertPackage',
    ('PUT', '/packages/{id}'): 'upsertPackage',
    ('DELETE', '/packages/{id}'): 'deletePackage',
    ('POST', '/electronic-invoices'): 'createElectronicInvoice',
    ('POST', '/electronic-invoices/draft'): 'createElectronicInvoiceDraft',
    ('POST', '/electronic-invoices/preview'): 'previewElectronicInvoice',
    ('GET', '/electronic-invoice-partners'): 'fetchSettings',
    ('GET', '/time-sheets/overview'): 'fetchResourceOverViewById',
    ('POST', '/time-sheets'): 'createTimeSheets',
    ('PUT', '/time-sheets'): 'updateTimeSheets',
}


def infer_fe_func(verb, path):
    v = verb.upper()
    norm_path = re.sub(r':([a-zA-Z0-9_]+)', r'{\1}', path.strip())
    norm_generic = re.sub(r'\{[a-zA-Z0-9_]+\}', '{id}', norm_path)
    if (v, norm_generic) in KNOWN_FE_CALLER_FUNCS:
        return KNOWN_FE_CALLER_FUNCS[(v, norm_generic)]

    # Tra cứu thêm trong global caller map nếu có
    singular, plural = _path_to_pascal_entity(norm_generic)
    has_id = '{id}' in norm_generic.lower()
    p_lower = norm_generic.lower()

    if v == 'GET':
        if 'search' in p_lower: return f'search{singular}ByKey'
        if 'print' in p_lower: return f'fetch{singular}Print'
        if 'group' in p_lower: return f'fetch{singular}Groups'
        if 'nearest' in p_lower: return f'requestNearest{plural}'
        if 'export' in p_lower: return f'export{plural}'
        if 'overview' in p_lower: return f'fetch{singular}Overview'
        return f'fetch{singular}ById' if has_id else f'fetch{plural}'
    elif v == 'POST':
        if 'import' in p_lower: return f'import{singular}'
        if 'upload' in p_lower: return f'upload{singular}'
        if 'draft' in p_lower: return f'create{singular}Draft'
        if 'preview' in p_lower: return f'preview{singular}'
        return f'create{singular}'
    elif v == 'PUT':
        if 'restore' in p_lower: return f'restore{singular}'
        if 'cancel' in p_lower: return f'cancel{singular}'
        if 'pay' in p_lower: return f'create{singular}Payment'
        if 'checkin' in p_lower: return f'checkin{singular}'
        if 'avatar' in p_lower: return f'update{singular}Avatar'
        return f'update{singular}'
    elif v == 'DELETE':
        return f'delete{singular}'
    return f'execute{singular}'


def infer_be_action(verb, path, controller_name=''):
    base_name = controller_name.replace('Controller', '') if controller_name else 'Item'
    base_name = re.sub(r'^V\d+_', '', base_name)
    v = verb.upper()
    has_id = '{id}' in path.lower() or ':id' in path.lower()
    p_lower = path.lower()
    if v == 'GET':
        if 'search' in p_lower: return f'Get{base_name}BySearch'
        if 'print' in p_lower: return f'Get{base_name}Print'
        if 'group' in p_lower: return f'Get{base_name}Group'
        if 'nearest' in p_lower: return f'Get{base_name}Nearest'
        if 'export' in p_lower: return f'Export{base_name}s'
        return f'Get{base_name}ById' if has_id else f'Get{base_name}'
    elif v == 'POST':
        if 'import' in p_lower: return f'Import{base_name}'
        return f'Post{base_name}'
    elif v == 'PUT':
        if 'restore' in p_lower: return f'Restore{base_name}'
        if 'cancel' in p_lower: return f'Cancel{base_name}'
        return f'Put{base_name}'
    elif v == 'DELETE':
        return f'Delete{base_name}'
    return f'Execute{base_name}'


def merge_module_endpoints(fe_endpoints, be_endpoints, base_route='', primary_controller='', vdata=None):
    merged = []
    seen = set()

    # Build FE lookup
    fe_items = []
    for ep in fe_endpoints:
        m = ep.get('method', 'GET').upper().replace('HTTP', '')
        raw_p = ep.get('path', '')
        p_clean, p_norm = normalize_endpoint_path(raw_p)
        fe_items.append({
            'method': m,
            'path': p_clean,
            'p_norm': p_norm,
            'fe_func': ep.get('fe_func') or infer_fe_func(m, p_clean),
            'note': ep.get('note', '')
        })

    # Build BE lookup
    be_items = []
    for ep in be_endpoints:
        m = ep.get('method', 'GET').upper().replace('HTTP', '')
        raw_p = ep.get('path', '')
        p_clean, p_norm = normalize_endpoint_path(raw_p)
        action = ep.get('be_action') or ep.get('action') or ''
        be_items.append({
            'method': m,
            'path': p_clean,
            'p_norm': p_norm,
            'be_action': action or infer_be_action(m, p_clean, primary_controller),
            'note': ep.get('note', '')
        })

    # 1. Match BE with FE
    for be in be_items:
        m = be['method']
        key = (m, be['p_norm'])
        if key in seen:
            continue
        seen.add(key)

        matched_fe = None
        for fe in fe_items:
            if fe['method'] == m and (fe['p_norm'] == be['p_norm'] or be['p_norm'].endswith(fe['p_norm']) or fe['p_norm'].endswith(be['p_norm'])):
                matched_fe = fe
                break

        if not matched_fe:
            has_id = '{id}' in be['p_norm']
            for fe in fe_items:
                if fe['method'] == m and ('{id}' in fe['p_norm']) == has_id:
                    matched_fe = fe
                    break

        fe_func = matched_fe['fe_func'] if matched_fe else infer_fe_func(m, be['path'])
        note = be['note'] or (matched_fe['note'] if matched_fe else '') or generate_endpoint_note(be['be_action'], m, be['path'])

        merged.append({
            'method': m,
            'path': be['path'],
            'fe_func': fe_func,
            'be_action': be['be_action'],
            'note': note
        })

    # 2. Add remaining FE endpoints
    for fe in fe_items:
        m = fe['method']
        key = (m, fe['p_norm'])
        if key in seen:
            continue
        seen.add(key)

        matched_be = None
        for be in be_items:
            if be['method'] == m and (be['p_norm'] == fe['p_norm'] or be['p_norm'].endswith(fe['p_norm']) or fe['p_norm'].endswith(be['p_norm'])):
                matched_be = be
                break

        be_action = matched_be['be_action'] if matched_be else infer_be_action(m, fe['path'], primary_controller)
        note = fe['note'] or (matched_be['note'] if matched_be else '') or generate_endpoint_note(be_action, m, fe['path'])

        merged.append({
            'method': m,
            'path': fe['path'],
            'fe_func': fe['fe_func'],
            'be_action': be_action,
            'note': note
        })

    # 3. Add vdata fallback endpoints if merged is empty
    if not merged and vdata and vdata.get('endpoints'):
        for vep in vdata['endpoints']:
            m = vep.get('method', 'GET').upper().replace('HTTP', '')
            p = vep.get('path', base_route)
            merged.append({
                'method': m,
                'path': p,
                'fe_func': infer_fe_func(m, p),
                'be_action': infer_be_action(m, p, primary_controller),
                'note': vep.get('note', '')
            })

    # 4. Ensure all 4 CRUD methods (GET, POST, PUT, DELETE) are present
    crud_methods = ['GET', 'POST', 'PUT', 'DELETE']
    present_methods = {e['method'] for e in merged}
    clean_base = base_route or f"/{to_kebab_case(primary_controller)}"
    if not clean_base.startswith('/'):
        clean_base = '/' + clean_base

    for cm in crud_methods:
        if cm not in present_methods:
            p = f"{clean_base}/{{id}}" if cm in ('PUT', 'DELETE') else clean_base
            fe_func = infer_fe_func(cm, p)
            be_action = infer_be_action(cm, p, primary_controller)
            merged.append({
                'method': cm,
                'path': p,
                'fe_func': fe_func,
                'be_action': be_action,
                'note': generate_endpoint_note(be_action, cm, p)
            })

    # Prioritize CRUD order: GET (list), POST, PUT, DELETE, GET (details / others)
    def priority_sort(e):
        m = e['method']
        has_id = '{id}' in e['path'].lower()
        if m == 'GET' and not has_id: return 1
        if m == 'POST': return 2
        if m == 'PUT': return 3
        if m == 'DELETE': return 4
        if m == 'GET' and has_id: return 5
        return 6

    merged.sort(key=priority_sort)
    return merged


def get_diagram_data(force=False):
    global _GLOBAL_FE_CALLER_MAP
    fe_ws = get_fe_workspace()
    be_ws = get_be_workspace()
    fe_branch, fe_commit = get_git_info(fe_ws)
    be_branch, be_commit = get_git_info(be_ws)
    cache_key = f"{fe_branch}@{fe_commit}|{be_branch}@{be_commit}"

    with state_lock:
        if not force and app_state.get('diagram_cache') and app_state.get('diagram_cache_key') == cache_key:
            return app_state['diagram_cache']

    _GLOBAL_FE_CALLER_MAP = None
    modules = []
    for cfg in CORE_MODULE_CONFIGS:
        mid = cfg['id']
        vdata = MODULE_VERIFIED_DATA.get(mid, {})

        fe_info = scan_fe_directory(fe_ws, cfg)
        be_info = scan_be_controllers(be_ws, cfg['be_controllers'])

        # Controllers & services
        primary_c = be_info.get('primary_controller') or (cfg['be_controllers'][0] if cfg.get('be_controllers') else vdata.get('controller', f"{mid.capitalize()}Controller"))

        # Merge / fallback for routes & endpoints
        route = be_info.get('route') or fe_info.get('route') or vdata.get('route', f"/{mid}")
        if '[controller]' in route.lower():
            route = to_kebab_case(primary_c)
        api_route = '/' + route.lstrip('/')

        # Merge endpoints from BE and FE with Frontend function and Backend action matching
        endpoints = merge_module_endpoints(
            fe_info.get('endpoints', []),
            be_info.get('endpoints', []),
            base_route=api_route,
            primary_controller=primary_c,
            vdata=vdata
        )

        # Select representative endpoints guaranteeing all 4 CRUD methods (GET, POST, PUT, DELETE)
        selected_endpoints = []
        for target_verb in ['GET', 'POST', 'PUT', 'DELETE']:
            for ep in endpoints:
                if ep['method'] == target_verb and ep not in selected_endpoints:
                    selected_endpoints.append(ep)
                    break
        for ep in endpoints:
            if ep['method'] == 'GET' and ('{id}' in ep['path'].lower() or ':id' in ep['path'].lower()) and ep not in selected_endpoints:
                selected_endpoints.append(ep)
                break
        for ep in endpoints:
            if len(selected_endpoints) >= 6:
                break
            if ep not in selected_endpoints:
                selected_endpoints.append(ep)

        # Screens & components
        screens = fe_info.get('screens') or vdata.get('screens', [f"Route{mid.capitalize()}.tsx"])
        components = fe_info.get('components') or vdata.get('components', ['Container.tsx'])
        resources = fe_info.get('resources') or vdata.get('resources', [f"{mid}.ts"])

        # Controllers & services
        primary_c = be_info.get('primary_controller') or (cfg['be_controllers'][0] if cfg.get('be_controllers') else vdata.get('controller', f"{mid.capitalize()}Controller"))
        service = be_info.get('service') or vdata.get('service', f"{primary_c.replace('Controller', '')}Service")
        manager = be_info.get('manager') or vdata.get('manager', f"{primary_c.replace('Controller', '')}Manager")
        entity = be_info.get('entity') or (vdata.get('entities', [primary_c.replace('Controller', '')])[0])
        entities = be_info.get('entities') or vdata.get('entities', [entity])
        be_stack_str = be_info.get('be_stack_str') or f"{primary_c} → {service} → {entity} Entity"

        # Construct be_links
        be_links = [service, manager, f"{entity} Entity"]
        for extra_c in cfg['be_controllers']:
            if extra_c != primary_c and extra_c not in be_links:
                be_links.append(extra_c)

        mod = {
            'id': mid,
            'title': cfg['title'],
            'name': cfg.get('name', cfg['title']),
            'category': cfg.get('category', 'core'),
            'skill': cfg['skill'],
            'api': {
                'route': api_route,
                'endpoints': selected_endpoints
            },
            'fe': {
                'screens': screens[:12],
                'components': components[:15],
                'resources': resources,
                'path': fe_info.get('path') or (cfg['fe_routes'][0] if cfg.get('fe_routes') else f"src/scripts/routes/{mid}"),
                'resource': fe_info.get('resource') or (cfg['fe_resources'][0] if cfg.get('fe_resources') else f"src/scripts/restful/resources/{mid}.ts"),
                'desc': cfg['default_desc'],
                'imports': fe_info.get('imports') or ['@/restful', '@/components/common'],
                'exports': fe_info.get('exports') or ['Container', 'Actions']
            },
            'be': {
                'path': be_info.get('path') or f"SALON_HAIR_API/Controllers/{primary_c}.cs",
                'controller': primary_c,
                'controller_full': f"{primary_c} : SalonControllerBase",
                'controllers': cfg['be_controllers'],
                'service': service,
                'manager': manager,
                'entity': entity,
                'entities': entities,
                'be_stack_str': be_stack_str,
                'desc': f"Xử lý Controller nghiệp vụ cho {cfg['title']}, tích hợp Service Layer và MySQL.",
                'injections': be_info.get('injections') or ['IUnitOfWork', 'ISalonContext', service],
                'exports': be_info.get('actions') or [f"{ep['method']} {ep['path']}" for ep in endpoints[:4]],
                'links': be_links
            }
        }
        modules.append(mod)

    mermaid_code = build_mermaid_code(modules, fe_branch, be_branch)
    tree_nodes = build_tree_nodes(modules)

    result = {
        'fe_branch': fe_branch,
        'fe_commit': fe_commit,
        'be_branch': be_branch,
        'be_commit': be_commit,
        'scanned_at': datetime.datetime.now().strftime('%H:%M:%S - %d/%m/%Y'),
        'modules': modules,
        'tree_nodes': tree_nodes,
        'mermaid_code': mermaid_code
    }

    with state_lock:
        app_state['diagram_cache'] = result
        app_state['diagram_cache_key'] = cache_key

    return result

