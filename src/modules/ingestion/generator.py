"""
gen_data.py — Generate fake PII data for 4 CSV tables (5000 rows each)
Structure:
  - LOOKUP : static value pools (names, addresses, …)  ← edit sample values here
  - GENERATORS : functions that produce one typed value  ← edit formats here
  - SCHEMAS : row-builder for each table                ← add/remove columns here
  - ENGINE : build_csv + main                           ← do not touch
"""

import csv
import json
import random
import string
import os
import unicodedata
from datetime import date, timedelta
from pathlib import Path

from src.core.dtos.enums import SensitivityTag

# Giả định Enum được import chính xác từ hệ thống của bạn
# from src.core.dtos.enums import SensitivityTag, SensitivityLevel

# ── Config ────────────────────────────────────────────────────────────────────
OUTPUT_DIR = Path(__file__).parent.parent.parent.parent / "data" / "csv"
SEED       = 42
random.seed(SEED)

TABLE_SIZES = {
    "citizen_info.csv"           : 5000,
    "administrative_records.csv" : 5000,
    "hr_employees.csv"           : 5000,
    "medical_records.csv"        : 5000,
}

# ── LOOKUP — edit pools here ───────────────────────────────────────────────────

LAST_NAMES  = ["Nguyễn", "Trần", "Lê", "Phạm", "Hoàng", "Huỳnh", "Phan",
               "Vũ", "Đặng", "Bùi", "Đỗ", "Hồ", "Ngô", "Dương", "Lý"]

MID_NAMES   = ["Văn", "Thị", "Đức", "Minh", "Thành", "Quốc", "Anh", "Thùy",
               "Bảo", "Hữu", "Thanh", "Ngọc", "Phương", "Xuân", "Trung"]

FIRST_NAMES = ["An", "Bình", "Châu", "Dũng", "Giang", "Hà", "Hùng", "Lan",
               "Linh", "Long", "Mai", "Nam", "Nga", "Phúc", "Quân", "Sơn",
               "Tâm", "Thảo", "Toàn", "Tuấn", "Uyên", "Việt", "Xuân", "Yến"]

ADDRESS_TREE = {
    "Hà Nội": {
        "Quận Hoàn Kiếm" : ["Phường Hàng Bạc", "Phường Hàng Bồ", "Phường Tràng Tiền", "Phường Lý Thái Tổ"],
        "Quận Cầu Giấy"  : ["Phường Dịch Vọng", "Phường Quan Hoa", "Phường Trung Hòa", "Phường Nghĩa Tân"],
        "Quận Đống Đa"   : ["Phường Văn Chương", "Phường Ô Chợ Dừa", "Phường Láng Hạ", "Phường Nam Đồng"],
        "Huyện Gia Lâm"  : ["Xã Ninh Hiệp", "Xã Đặng Xá", "Thị trấn Yên Viên", "Xã Kim Sơn"],
    },
    "TP. Hồ Chí Minh": {
        "Quận 1"         : ["Phường Bến Nghé", "Phường Bến Thành", "Phường Tân Định", "Phường Đa Kao"],
        "Quận Bình Thạnh": ["Phường 1", "Phường 3", "Phường 11", "Phường 22", "Phường 25"],
        "Quận Tân Bình"  : ["Phường 1", "Phường 4", "Phường Phú Thọ Hòa", "Phường Tân Thành"],
        "Huyện Bình Chánh":["Xã Bình Hưng", "Xã Phong Phú", "Thị trấn Tân Túc", "Xã Vĩnh Lộc A"],
    },
    "Đà Nẵng": {
        "Quận Hải Châu"  : ["Phường Hải Châu 1", "Phường Thanh Bình", "Phường Nam Dương", "Phường Thạch Thang"],
        "Quận Ngũ Hành Sơn":["Phường Mỹ An", "Phường Khuê Mỹ", "Phường Hòa Hải", "Phường Hòa Quý"],
        "Quận Liên Chiểu": ["Phường Hòa Hiệp Bắc", "Phường Hòa Hiệp Nam", "Phường Hòa Khánh Bắc"],
    },
    "Hải Phòng": {
        "Quận Ngô Quyền" : ["Phường Lạch Tray", "Phường Đổng Quốc Bình", "Phường Cầu Tre"],
        "Quận Lê Chân"   : ["Phường An Biên", "Phường Dư Hàng", "Phường Hàng Kênh"],
        "Huyện An Dương"  : ["Xã An Đồng", "Thị trấn An Dương", "Xã Đặng Cương"],
    },
    "Cần Thơ": {
        "Quận Ninh Kiều"  : ["Phường An Khánh", "Phường Tân An", "Phường Xuân Khánh", "Phường An Bình"],
        "Quận Bình Thủy"  : ["Phường Bình Thủy", "Phường Long Tuyền", "Phường An Thới"],
    },
    "Bình Dương": {
        "TP. Thủ Dầu Một" : ["Phường Phú Cường", "Phường Hiệp Thành", "Phường Chánh Nghĩa"],
        "Huyện Thuận An"  : ["Phường An Phú", "Phường Lái Thiêu", "Phường Bình Chuẩn"],
    },
    "Quảng Ninh": {
        "TP. Hạ Long": ["Phường Bãi Cháy", "Phường Hồng Gai", "Phường Cao Thắng", "Phường Hà Khánh"],
        "TP. Cẩm Phả": ["Phường Cẩm Trung", "Phường Cẩm Tây", "Phường Cẩm Bình", "Phường Cẩm Đông"],
        "TX. Quảng Yên": ["Phường Quảng Yên", "Phường Đông Mai", "Phường Minh Thành", "Phường Nam Hòa"],
    },
    "Thái Nguyên": {
        "TP. Thái Nguyên": ["Phường Hoàng Văn Thụ", "Phường Quang Trung", "Phường Túc Duyên", "Phường Đồng Quang"],
        "TP. Sông Công": ["Phường Mỏ Chè", "Phường Cải Đan", "Phường Thắng Lợi", "Phường Bách Quang"],
        "Huyện Đại Từ": ["Xã Hùng Sơn", "Xã Tiên Hội", "Xã Phú Cường", "Xã Bình Thuận"],
    },
    "Bắc Ninh": {
        "TP. Bắc Ninh": ["Phường Vũ Ninh", "Phường Suối Hoa", "Phường Kinh Bắc", "Phường Võ Cường"],
        "TP. Từ Sơn": ["Phường Đông Ngàn", "Phường Đồng Kỵ", "Phường Châu Khê", "Phường Đình Bảng"],
        "Huyện Yên Phong": ["Xã Yên Trung", "Xã Long Châu", "Xã Tam Giang", "Xã Dũng Liệt"],
    },
    "Hải Dương": {
        "TP. Hải Dương": ["Phường Trần Phú", "Phường Thanh Bình", "Phường Hải Tân", "Phường Lê Thanh Nghị"],
        "TP. Chí Linh": ["Phường Sao Đỏ", "Phường Cộng Hòa", "Phường Phả Lại", "Phường Văn An"],
        "Huyện Nam Sách": ["Xã Nam Trung", "Xã An Sơn", "Xã Đồng Lạc", "Xã Hợp Tiến"],
    },
    "Hưng Yên": {
        "TP. Hưng Yên": ["Phường Hiến Nam", "Phường Lam Sơn", "Phường An Tảo", "Phường Minh Khai"],
        "TX. Mỹ Hào": ["Phường Bần Yên Nhân", "Phường Dị Sử", "Phường Phùng Chí Kiên", "Phường Nhân Hòa"],
        "Huyện Văn Lâm": ["Xã Lạc Đạo", "Xã Chỉ Đạo", "Xã Đại Đồng", "Xã Việt Hưng"],
    },
    "Ninh Bình": {
        "TP. Ninh Bình": ["Phường Đông Thành", "Phường Nam Bình", "Phường Thanh Bình", "Phường Ninh Khánh"],
        "TP. Tam Điệp": ["Phường Bắc Sơn", "Phường Nam Sơn", "Phường Trung Sơn", "Phường Tây Sơn"],
        "Huyện Hoa Lư": ["Xã Ninh Mỹ", "Xã Ninh An", "Xã Ninh Giang", "Xã Trường Yên"],
    },
    "Thanh Hóa": {
        "TP. Thanh Hóa": ["Phường Lam Sơn", "Phường Đông Sơn", "Phường Ba Đình", "Phường Ngọc Trạo"],
        "TP. Sầm Sơn": ["Phường Bắc Sơn", "Phường Trung Sơn", "Phường Quảng Tiến", "Phường Trường Sơn"],
        "Huyện Hoằng Hóa": ["Xã Hoằng Phú", "Xã Hoằng Lộc", "Xã Hoằng Đạo", "Xã Hoằng Hà"],
    },
    "Nghệ An": {
        "TP. Vinh": ["Phường Hưng Bình", "Phường Lê Mao", "Phường Quang Trung", "Phường Hà Huy Tập"],
        "TX. Cửa Lò": ["Phường Nghi Hòa", "Phường Nghi Hải", "Phường Thu Thủy", "Phường Nghi Thu"],
        "Huyện Diễn Châu": ["Xã Diễn Thành", "Xã Diễn Kỷ", "Xã Diễn Thịnh", "Xã Diễn Hồng"],
    },
    "Thừa Thiên Huế": {
        "TP. Huế": ["Phường Phú Hội", "Phường Vĩnh Ninh", "Phường Thuận Hòa", "Phường Tây Lộc"],
        "TX. Hương Thủy": ["Phường Thủy Dương", "Phường Thủy Phương", "Phường Phú Bài", "Xã Thủy Thanh"],
        "TX. Hương Trà": ["Phường Tứ Hạ", "Xã Hương Toàn", "Xã Hương Vinh", "Xã Hương Xuân"],
    },
    "Đồng Nai": {
        "TP. Biên Hòa": ["Phường Tân Phong", "Phường Tân Hiệp", "Phường Hố Nai", "Phường Long Bình"],
        "TP. Long Khánh": ["Phường Xuân An", "Phường Xuân Thanh", "Phường Bảo Vinh", "Phường Suối Tre"],
        "Huyện Trảng Bom": ["Xã Bắc Sơn", "Xã Bình Minh", "Xã Đồi 61", "Xã Sông Trầu"],
    },
    "An Giang": {
        "TP. Long Xuyên": ["Phường Mỹ Bình", "Phường Mỹ Long", "Phường Mỹ Xuyên", "Phường Đông Xuyên"],
        "TP. Châu Đốc": ["Phường Châu Phú A", "Phường Châu Phú B", "Phường Núi Sam", "Phường Vĩnh Mỹ"],
        "Huyện Châu Phú": ["Xã Bình Mỹ", "Xã Mỹ Đức", "Xã Khánh Hòa", "Xã Ô Long Vĩ"],
    },
    "Kiên Giang": {
        "TP. Rạch Giá": ["Phường Vĩnh Thanh", "Phường Vĩnh Thanh Vân", "Phường An Bình", "Phường Rạch Sỏi"],
        "TP. Phú Quốc": ["Phường Dương Đông", "Phường An Thới", "Xã Hàm Ninh", "Xã Gành Dầu"],
        "Huyện Kiên Lương": ["Xã Bình An", "Xã Bình Trị", "Xã Dương Hòa", "Xã Hòa Điền"],
    },
}

STREETS = [
    "Nguyễn Huệ", "Lê Lợi", "Trần Phú", "Đinh Tiên Hoàng", "Lý Thường Kiệt",
    "Hai Bà Trưng", "Bà Triệu", "Trường Chinh", "Nguyễn Trãi", "Hoàng Diệu",
    "Phan Đình Phùng", "Võ Thị Sáu", "Cách Mạng Tháng 8", "Nam Kỳ Khởi Nghĩa",
    "Điện Biên Phủ", "Hoàng Văn Thụ", "Lê Văn Sỹ", "Phạm Văn Đồng",
    "Nguyễn Văn Cừ", "Tô Hiến Thành",
]

EMAIL_DOMAINS    = ["gmail.com", "yahoo.com", "hotmail.com", "outlook.com", "protonmail.com"]
CORP_EMAIL_DOMS  = ["viettel.com.vn", "vnpt.vn", "fpt.com.vn", "vingroup.net",
                    "masan.com.vn", "techcombank.com.vn", "mbbank.com.vn"]
BANKS            = ["Vietcombank", "BIDV", "Agribank", "Techcombank", "MB Bank",
                    "VPBank", "ACB", "Sacombank", "TPBank", "VietinBank"]
DEPARTMENTS      = ["Kỹ thuật", "Kinh doanh", "Tài chính - Kế toán", "Nhân sự",
                    "Marketing", "Vận hành", "Pháp lý", "Công nghệ thông tin",
                    "Chăm sóc khách hàng", "Mua hàng"]
POSITIONS        = ["Nhân viên", "Chuyên viên", "Trưởng nhóm", "Phó phòng",
                    "Trưởng phòng", "Phó giám đốc", "Giám đốc", "Thực tập sinh"]
DOC_TYPES        = ["Khai sinh", "Khai tử", "Đăng ký kết hôn", "Ly hôn",
                    "Chứng minh nhân dân", "Hộ chiếu", "Giấy phép lái xe",
                    "Đăng ký kinh doanh", "Giấy phép xây dựng"]
GOV_AGENCIES     = ["UBND Quận 1", "UBND Quận Hoàn Kiếm", "UBND TP. Hà Nội",
                    "Sở Tư pháp Hà Nội", "Sở Tư pháp TP.HCM", "UBND Quận Bình Thạnh",
                    "UBND Huyện Gia Lâm", "Sở Kế hoạch và Đầu tư Hà Nội"]
TXN_TYPES        = ["Chuyển khoản", "Rút tiền", "Nạp tiền", "Thanh toán hóa đơn",
                    "Mua sắm online", "Thanh toán thẻ"]
TXN_CHANNELS     = ["ATM", "Mobile Banking", "Internet Banking", "Quầy giao dịch", "POS"]
TXN_STATUSES     = ["Thành công", "Thất bại", "Đang xử lý", "Chờ xác nhận"]
CONTRACT_TYPES   = ["Thử việc", "Chính thức", "Thời vụ", "Cộng tác viên"]
ETHNICITIES      = ["Kinh", "Tày", "Thái", "Mường", "Khmer", "Nùng", "H'Mông"]
EDUCATION_LEVELS = ["Trung học phổ thông", "Cao đẳng", "Đại học", "Thạc sĩ", "Tiến sĩ"]
OCCUPATIONS      = ["Kỹ sư", "Giáo viên", "Bác sĩ", "Kế toán", "Lập trình viên",
                    "Nhân viên văn phòng", "Kinh doanh tự do", "Công nhân", "Nông dân"]
MARITAL_STATUSES = ["Độc thân", "Đã kết hôn", "Ly hôn", "Góa"]
NATIONALITIES    = ["Việt Nam"]
RECEPTION_CHANNELS = ["Online", "Trực tiếp", "Bưu điện", "Qua đại lý"]
PROCESSING_RESULTS = ["Chấp thuận", "Từ chối", "Đang xem xét"]
DOC_STATUSES     = ["Đang xử lý", "Hoàn thành", "Từ chối", "Chờ bổ sung hồ sơ"]
BLOOD_TYPES      = ["A", "B", "O", "AB"]

DIAGNOSES = [
    "Viêm gan siêu vi B", "Đái tháo đường Tuýp 2", "Tăng huyết áp vô căn",
    "Viêm dạ dày cấp", "Suy thận mạn giai đoạn 2", "Rối loạn lipid máu",
    "Viêm phế quản cấp", "Thoái hóa cột sống thắt lưng", "Thiếu máu thiếu sắt"
]
MEDICATIONS = [
    "Metformin 500mg", "Amlodipine 5mg", "Paracetamol 500mg", "Amoxicillin 500mg",
    "Omeprazole 20mg", "Atorvastatin 10mg", "Losartan 50mg", "Salbutamol 100mcg"
]
HOSPITALS = [
    "Bệnh viện Bạch Mai", "Bệnh viện Chợ Rẫy", "Bệnh viện Trung ương Huế",
    "Bệnh viện Đại học Y Dược TP.HCM", "Bệnh viện 108", "Bệnh viện Đa khoa Đà Nẵng",
    "Bệnh viện Nhi Trung ương", "Bệnh viện Tai Mũi Họng Trung ương"
]

PROVINCE_CODES = ["001","002","004","006","008","010","011","012","014","015","017","019","020","022","024","025","026","027","030","031","033","034","035","036","037","038","040","042","044","045","046","048","049","051","052","054","056","058","060","062","064","066","067","068","070","072","074","075","077","079","080","082","083","084","086","087","089","091","092","093","094","095","096"]

# ── GENERATORS ────────────────────────────────────────────────────────────────

def rand(lst):
    return random.choice(lst)

def make_id(prefix: str) -> tuple:
    return f"{prefix}-{random.randint(100000, 999999)}", SensitivityTag.NONE

def make_cccd(dob_tuple) -> tuple:
    dob_value = dob_tuple[0]
    province = rand(PROVINCE_CODES)
    gender = rand(["0", "1", "2", "3"])
    year = f"{dob_value.year % 100:02d}"
    seq = f"{random.randint(0, 999999):06d}"
    return province + gender + year + seq, SensitivityTag.RESIDENT_ID

def make_full_name() -> tuple:
    return f"{rand(LAST_NAMES)} {rand(MID_NAMES)} {rand(FIRST_NAMES)}", SensitivityTag.NAME

def make_dob() -> tuple:
    return date(1960, 1, 1) + timedelta(days=random.randint(0, 365 * 44)), SensitivityTag.DOB

def make_phone() -> tuple:
    prefixes = [
        "032","033","034","035","036","037","038","039",
        "056","058","059",
        "070","076","077","078","079",
        "081","082","083","084","085","086","088","089",
        "090","091","092","093","094","096","097","098",
    ]
    return rand(prefixes) + f"{random.randint(1_000_000, 9_999_999)}", SensitivityTag.PHONE

def _slugify(name_tuple: tuple) -> tuple:
    name = name_tuple[0].lower()
    nfd = unicodedata.normalize("NFD", name)
    ascii_only = "".join(c for c in nfd if unicodedata.category(c) != "Mn")
    ascii_only = ascii_only.replace("đ", "d")
    return "".join(c if c.isalnum() or c == "." else "" for c in ascii_only.replace(" ", ".")), SensitivityTag.NAME

def make_email(name_tuple: tuple) -> tuple:
    slug = _slugify(name_tuple or make_full_name())
    return f"{slug[0]}{random.randint(1, 999)}@{rand(EMAIL_DOMAINS)}", SensitivityTag.EMAIL

def make_work_email(name_tuple: tuple = None) -> tuple:
    slug = _slugify(name_tuple or make_full_name())
    return f"{slug[0]}@{rand(CORP_EMAIL_DOMS)}", SensitivityTag.EMAIL

def make_address() -> tuple:
    province = rand(list(ADDRESS_TREE.keys()))
    district = rand(list(ADDRESS_TREE[province].keys()))
    ward     = rand(ADDRESS_TREE[province][district])
    house_no = random.randint(1, 500)
    street   = rand(STREETS)
    return f"{house_no} {street}, {ward}, {district}, {province}", SensitivityTag.ADDRESS

def make_province() -> tuple:
    return rand(list(ADDRESS_TREE.keys())), SensitivityTag.ADDRESS

def make_salary() -> tuple:
    return random.randint(5, 100) * 500_000, SensitivityTag.SALARY

def make_ip() -> tuple:
    return ".".join(str(random.randint(1, 254)) for _ in range(4)), SensitivityTag.NONE

def make_date(start_year: int = 2020, end_year: int = 2024) -> tuple:
    start = date(start_year, 1, 1)
    end   = date(end_year, 12, 31)
    return start + timedelta(days=random.randint(0, (end - start).days)), SensitivityTag.NONE

def make_household_no() -> tuple:
    return f"{rand(PROVINCE_CODES)}/{random.randint(100_000, 999_999)}", SensitivityTag.NONE

def make_amount() -> tuple:
    return rand([50, 100, 200, 500, 1_000, 2_000, 5_000, 10_000, 20_000, 50_000, 100_000]) * 1_000, SensitivityTag.NONE

def make_device_fp() -> tuple:
    return "".join(random.choices(string.hexdigits.lower(), k=32)), SensitivityTag.NONE

def make_batch_id() -> tuple:
    return f"BATCH-{random.randint(1000, 9999)}", SensitivityTag.NONE

def make_decision_no() -> tuple:
    return f"{random.randint(100, 999)}/QĐ-UBND", SensitivityTag.NONE

def make_bhyt_no() -> tuple:
    prefix = random.choice(["GD", "DN", "CH", "HC", "XK"])
    digits = "".join(str(random.randint(0, 9)) for _ in range(13))
    return f"{prefix}{digits}", SensitivityTag.HEALTH_INSURANCE_ID

def make_emp_badge_id() -> tuple:
    year = random.choice(["2021", "2022", "2023", "2024", "2025"])
    seq = f"{random.randint(1, 9999):04d}"
    return f"NV-{year}-{seq}", SensitivityTag.NONE


# ── SCHEMAS ───────────────────────────────────────────────────────────────────

def build_citizen_row() -> dict:
    name = make_full_name()
    dob = make_dob()
    cccd = make_cccd(dob)
    return {
        "record_id"          : make_id("CIT"),
        "cccd_so"            : cccd,
        "ho_va_ten"          : name,
        "ngay_sinh"          : dob,
        "gioi_tinh"          : rand(["Nam", "Nữ"]),
        "sdt_chinh"          : make_phone(),
        "dia_chi_cu_tru"     : make_address(),
        "tinh_thanh"         : make_province(),
        "quoc_tich"          : rand(NATIONALITIES),
        "ref_ext"            : make_email(name),
        "so_phu"             : make_phone(),
        "nhom_mau"           : rand(BLOOD_TYPES),
        "tinh_trang_hn"      : rand(MARITAL_STATUSES),
        "trinh_do_hv"        : rand(EDUCATION_LEVELS),
        "nghe_nghiep"        : rand(OCCUPATIONS),
        "noi_sinh"           : make_province(),
        "so_nguoi_phu_thuoc" : random.randint(0, 5),
        "ngay_cap_cccd"      : make_date(2015, 2024),
        "dan_toc"            : rand(ETHNICITIES),
        "created_at"         : make_date(2022, 2024),
    }

def build_admin_row() -> dict:
    name        = make_full_name()
    submitted   = make_date(2021, 2024)
    deadline    = submitted[0] + timedelta(days=random.randint(7, 60)) if isinstance(submitted, tuple) else submitted + timedelta(days=random.randint(7, 60))
    dob         = make_dob()
    cccd        = make_cccd(dob)
    return {
        "ho_so_id"           : make_id("ADM"),
        "ref_id"             : cccd,
        "ten_chu_ho_so"      : name,
        "val_02"             : make_phone(),
        "loai_ho_so"         : rand(DOC_TYPES),
        "co_quan_tiep_nhan"  : rand(GOV_AGENCIES),
        "ngay_nop"           : submitted,
        "han_giai_quyet"     : deadline,
        "trang_thai_xu_ly"   : rand(DOC_STATUSES),
        "ext_info"           : make_email(name),
        "so_bien_lai"        : make_id("BL"),
        "so_bao_hiem"        : make_bhyt_no(),
        "phi_ho_so"          : rand([0, 50_000, 100_000, 200_000]),
        "nhan_vien_xu_ly"    : make_id("NV"),
        "dia_chi_lien_lac"   : make_address(),
        "meta_addr"          : make_address(),
        "so_ho_khau"         : make_household_no(),
        "kenh_tiep_nhan"     : rand(RECEPTION_CHANNELS),
        "ket_qua_xu_ly"      : rand(PROCESSING_RESULTS),
        "updated_at"         : make_date(2022, 2024),
    }

def build_hr_row() -> dict:
    name = make_full_name()
    dob = make_dob()
    cccd = make_cccd(dob)
    return {
        "emp_id"             : make_id("EMP"),
        "so_cccd"            : cccd,
        "ho_ten_nv"          : name,
        "d_entry"            : dob,
        "sdt_ca_nhan"        : make_phone(),
        "personal_email"     : make_email(name),
        "work_email"         : make_work_email(name),
        "res_data"           : make_address(),
        "phong_ban"          : rand(DEPARTMENTS),
        "chuc_vu"            : rand(POSITIONS),
        "m_val"              : make_salary(),
        "mnv"                : make_batch_id(),
        "ten_ngan_hang"      : rand(BANKS),
        "so_quyet_dinh"      : make_decision_no(),
        "ins_num"            : make_bhyt_no(),
        "ngay_vao_lam"       : make_date(2010, 2024),
        "loai_hop_dong"      : rand(CONTRACT_TYPES),
        "gender"             : rand(["male", "female"]),
        "manager_id"         : make_id("EMP"),
        "created_at"         : make_date(2022, 2024),
    }

def build_medical_row() -> dict:
    name = make_full_name()
    dob = make_dob()
    cccd = make_cccd(dob)
    visit_date = make_date(2022, 2024)
    return {
        "record_id"          : make_id("MED"),
        "so_cccd_benh_nhan"  : cccd,
        "ho_ten_benh_nhan"   : name,
        "ngay_sinh"          : dob,
        "gioi_tinh"          : random.choice(["Nam", "Nữ"]),
        "nhom_mau"           : random.choice(["A", "B", "O", "AB"]),
        "so_dien_thoai"      : make_phone(),
        "email_lien_he"      : make_email(name),
        "dia_chi_thuong_tru" : make_address(),
        "ma_so_bhyt"         : make_bhyt_no(),
        "ten_benh_vien"      : random.choice(HOSPITALS),
        "khoa_kham"          : random.choice(["Nội tổng quát", "Ngoại thần kinh", "Tim mạch", "Tiêu hóa", "Nhi"]),
        "chuan_doan"         : random.choice(DIAGNOSES),
        "thuoc_chi_dinh"     : random.choice(MEDICATIONS),
        "chieu_cao_cm"       : random.randint(150, 185),
        "can_nang_kg"        : random.randint(45, 90),
        "huyet_ap"           : f"{random.randint(110, 140)}/{random.randint(70, 90)}",
        "bac_si_dieu_tri"    : make_full_name(),
        "ngay_kham"          : visit_date,
        "ghi_chu_ls"         : "Bệnh nhân tỉnh táo, tiếp xúc tốt.",
    }

# ── ENGINE — Sửa đổi hàm bóc tách dữ liệu linh hoạt ───────────────────────────

TABLES = [
    ("citizen_info.csv",           build_citizen_row),
    ("administrative_records.csv", build_admin_row),
    ("hr_employees.csv",           build_hr_row),
    ("medical_records.csv",        build_medical_row),
]

def normalize_value_and_tag(item) -> tuple:
    """
    Hàm chuẩn hóa: Đảm bảo bất kể hàm generator trả về tuple hay giá trị thô,
    hệ thống đều ép về đúng chuẩn cặp định dạng: (giá_trị_thô, SensitiveTag)
    """
    if isinstance(item, tuple) and len(item) == 2 and isinstance(item[1], SensitivityTag):
        return item[0], item[1]
    return item, SensitivityTag.NONE

def write_csv_and_metadata(filename: str, row_fn, n_rows: int) -> None:
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    os.makedirs(OUTPUT_DIR / "metadata", exist_ok=True)

    # 1. Sinh toàn bộ dữ liệu thô (gồm cả tuple và raw value lẫn lộn)
    raw_rows = [row_fn() for _ in range(n_rows)]
    fieldnames = list(raw_rows[0].keys())

    # 2. Trích xuất Metadata an toàn từ dòng đầu tiên
    columns_metadata = []
    for col in fieldnames:
        _, tag = normalize_value_and_tag(raw_rows[0][col])
        columns_metadata.append({
            "column_name": col,
            "sensitivity_tag": tag.value,
            "sensitivity_level": tag.sensitivity_level.value
        })

    metadata = {
        "table_name": filename,
        "total_columns": len(fieldnames),
        "columns": columns_metadata
    }

    # 3. "Gọt vỏ" chính xác để tạo dòng ghi CSV
    csv_rows = []
    for r in raw_rows:
        row_data = {}
        for col in fieldnames:
            val, _ = normalize_value_and_tag(r[col])
            # Chuyển object date sang chuỗi string để ghi CSV không bị lỗi format
            if isinstance(val, (date,)):
                val = val.isoformat()
            row_data[col] = val
        csv_rows.append(row_data)

    # 4. Ghi file CSV
    csv_path = os.path.join(OUTPUT_DIR, filename)
    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(csv_rows)
    print(f"{filename:40s}  {n_rows:>5,} rows  →  {csv_path}")

    # 5. Ghi file JSON Metadata
    base_name, _ = os.path.splitext(filename)
    meta_path = os.path.join(OUTPUT_DIR / "metadata", f"{base_name}_metadata.json")
    with open(meta_path, "w", encoding="utf-8") as f:
        json.dump(metadata, f, ensure_ascii=False, indent=4)
    print(f"{base_name}_metadata.json  Generated successfully.")

def main() -> None:
    total = sum(TABLE_SIZES.values())
    print(f"\n{'='*60}")
    print(f"  Generating {total:,} rows across {len(TABLES)} tables")
    print(f"{'='*60}")
    for filename, row_fn in TABLES:
        n = TABLE_SIZES.get(filename, 5000)
        write_csv_and_metadata(filename, row_fn, n)
    print(f"{'='*60}")
    print(f"  Done. Output folder: {OUTPUT_DIR}/")
    print(f"{'='*60}\n")

if __name__ == "__main__":
    main()