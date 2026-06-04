"""
gen_data.py — Generate fake PII data for 4 CSV tables (5000 rows each)
Structure:
  - LOOKUP : static value pools (names, addresses, …)  ← edit sample values here
  - GENERATORS : functions that produce one typed value  ← edit formats here
  - SCHEMAS : row-builder for each table                ← add/remove columns here
  - ENGINE : build_csv + main                           ← do not touch
"""

import csv
import random
import string
import os
import unicodedata
from datetime import date, timedelta
from pathlib import Path

# ── Config ────────────────────────────────────────────────────────────────────
OUTPUT_DIR = Path(__file__).parent.parent.parent.parent / "data" / "csv"
SEED       = 42
random.seed(SEED)

TABLE_SIZES = {
    "citizen_info.csv"           : 5000,
    "administrative_records.csv" : 5000,
    "hr_employees.csv"           : 5000,
    "transaction_logs.csv"       : 5000,
}

# ── LOOKUP — edit pools here ───────────────────────────────────────────────────

LAST_NAMES  = ["Nguyễn", "Trần", "Lê", "Phạm", "Hoàng", "Huỳnh", "Phan",
               "Vũ", "Đặng", "Bùi", "Đỗ", "Hồ", "Ngô", "Dương", "Lý"]

MID_NAMES   = ["Văn", "Thị", "Đức", "Minh", "Thành", "Quốc", "Anh", "Thùy",
               "Bảo", "Hữu", "Thanh", "Ngọc", "Phương", "Xuân", "Trung"]

FIRST_NAMES = ["An", "Bình", "Châu", "Dũng", "Giang", "Hà", "Hùng", "Lan",
               "Linh", "Long", "Mai", "Nam", "Nga", "Phúc", "Quân", "Sơn",
               "Tâm", "Thảo", "Toàn", "Tuấn", "Uyên", "Việt", "Xuân", "Yến"]

# Address data: province → districts → wards
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

# Province codes used in CCCD (3-digit prefix)
PROVINCE_CODES = ["001","002","004","006","008","010","011","012","014","015","017","019","020","022","024","025","026","027","030","031","033","034","035","036","037","038","040","042","044","045","046","048","049","051","052","054","056","058","060","062","064","066","067","068","070","072","074","075","077","079","080","082","083","084","086","087","089","091","092","093","094","095","096"]

# ── GENERATORS — edit value formats here ──────────────────────────────────────

def rand(lst):
    """Pick one item at random from a list."""
    return random.choice(lst)

def make_id(prefix: str) -> str:
    return f"{prefix}-{random.randint(100000, 999999)}"

def make_cccd(dob) -> str:
    """
    12-digit Vietnamese national ID:
      [0:3]  province code (3 digits)
      [3]    gender+century digit (0-3)
      [4:6]  birth year last 2 digits
      [6:12] random sequence (6 digits)
    """
    province = rand(PROVINCE_CODES)
    gender = rand(["0", "1", "2", "3"])
    year = f"{dob.year % 100:02d}"
    seq = f"{random.randint(0, 999999):06d}"
    return province + gender + year + seq

def make_full_name() -> str:
    return f"{rand(LAST_NAMES)} {rand(MID_NAMES)} {rand(FIRST_NAMES)}"

def make_dob() -> date:
    """Date of birth: 1960-01-01 to 2004-12-31."""
    return date(1960, 1, 1) + timedelta(days=random.randint(0, 365 * 44))

def make_phone() -> str:
    """
    10-digit Vietnamese mobile number.
    Prefixes: 03x / 05x / 07x / 08x / 09x as per Việt Nam numbering plan.
    """
    prefixes = [
        "032","033","034","035","036","037","038","039",  # Viettel
        "056","058","059",                                # Vietnamobile
        "070","076","077","078","079",                    # Mobifone
        "081","082","083","084","085","086","088","089",  # Vinaphone
        "090","091","092","093","094","096","097","098",  # legacy
    ]
    return rand(prefixes) + f"{random.randint(1_000_000, 9_999_999)}"

def _slugify(name: str) -> str:
    """Convert Vietnamese name to ASCII slug for email local-part."""
    name = name.lower()
    # NFD decomposition strips combining diacritics
    nfd = unicodedata.normalize("NFD", name)
    ascii_only = "".join(c for c in nfd if unicodedata.category(c) != "Mn")
    ascii_only = ascii_only.replace("đ", "d").replace("đ", "d")
    return "".join(c if c.isalnum() or c == "." else "" for c in ascii_only.replace(" ", "."))

def make_email(name: str = None) -> str:
    """name.name<num>@domain  — personal email."""
    slug = _slugify(name or make_full_name())
    return f"{slug}{random.randint(1, 999)}@{rand(EMAIL_DOMAINS)}"

def make_work_email(name: str = None) -> str:
    """name.name@company.vn  — corporate email."""
    slug = _slugify(name or make_full_name())
    return f"{slug}@{rand(CORP_EMAIL_DOMS)}"

def make_address() -> str:
    """
    Hierarchically consistent address:
      <house_no> <street>, <ward>, <district>, <province>
    Province → district → ward are drawn from the same branch of ADDRESS_TREE.
    """
    province = rand(list(ADDRESS_TREE.keys()))
    district = rand(list(ADDRESS_TREE[province].keys()))
    ward     = rand(ADDRESS_TREE[province][district])
    house_no = random.randint(1, 500)
    street   = rand(STREETS)
    return f"{house_no} {street}, {ward}, {district}, {province}"

def make_province() -> str:
    return rand(list(ADDRESS_TREE.keys()))

def make_tax_code() -> str:
    """10-digit personal tax identification number."""
    return f"{random.randint(1_000_000_000, 9_999_999_999)}"

def make_social_insurance_no() -> str:
    """10-digit social insurance number."""
    return f"{random.randint(1_000_000_000, 9_999_999_999)}"

def make_bank_account() -> str:
    """9–16 digit bank account number."""
    length = random.randint(9, 16)
    return "".join(str(random.randint(0, 9)) for _ in range(length))

def make_salary() -> int:
    """Monthly salary in VND, rounded to nearest 500k."""
    return random.randint(5, 100) * 500_000

def make_ip() -> str:
    return ".".join(str(random.randint(1, 254)) for _ in range(4))

def make_date(start_year: int = 2020, end_year: int = 2024) -> date:
    start = date(start_year, 1, 1)
    end   = date(end_year, 12, 31)
    return start + timedelta(days=random.randint(0, (end - start).days))

def make_household_no() -> str:
    """Household registration number: <province_code>/<6-digit-seq>."""
    return f"{rand(PROVINCE_CODES)}/{random.randint(100_000, 999_999)}"

def make_amount() -> int:
    """Transaction amount in VND."""
    return rand([50, 100, 200, 500, 1_000, 2_000, 5_000, 10_000,
                 20_000, 50_000, 100_000]) * 1_000

def make_device_fp() -> str:
    return "".join(random.choices(string.hexdigits.lower(), k=32))

def make_batch_id() -> str:
    return f"BATCH-{random.randint(1000, 9999)}"


# ── SCHEMAS — one row-builder per table ───────────────────────────────────────

def build_citizen_row() -> dict:
    name = make_full_name()
    dob = make_dob()
    cccd = make_cccd(dob)
    return {
        "record_id"          : make_id("CIT"),
        "cccd_so"            : cccd,              # HIGH   | Regex
        "ho_va_ten"          : name,                     # MEDIUM | LLM
        "ngay_sinh"          : dob,               # LOW    | LLM
        "gioi_tinh"          : rand(["Nam", "Nữ"]),      # NONE
        "sdt_chinh"          : make_phone(),             # MEDIUM | Regex
        "dia_chi_cu_tru"     : make_address(),           # LOW    | LLM
        "tinh_thanh"         : make_province(),          # NONE
        "quoc_tich"          : rand(NATIONALITIES),      # NONE
        "ref_ext"            : make_email(name),         # MEDIUM | LLM   (ambiguous: personal email)
        "so_phu"             : make_phone(),             # MEDIUM | Regex (ambiguous: secondary phone)
        "pid"                : cccd,          # HIGH   | Regex (ambiguous: tax code)
        "tinh_trang_hn"      : rand(MARITAL_STATUSES),  # NONE
        "trinh_do_hv"        : rand(EDUCATION_LEVELS),  # NONE
        "nghe_nghiep"        : rand(OCCUPATIONS),       # NONE
        "noi_sinh"           : make_province(),          # LOW    | LLM
        "so_nguoi_phu_thuoc" : random.randint(0, 5),    # NONE
        "ngay_cap_cccd"      : make_date(2015, 2024),   # NONE
        "dan_toc"            : rand(ETHNICITIES),        # NONE
        "created_at"         : make_date(2022, 2024),   # NONE
    }

def build_admin_row() -> dict:
    name        = make_full_name()
    submitted   = make_date(2021, 2024)
    deadline    = submitted + timedelta(days=random.randint(7, 60))
    dob         = make_dob()
    cccd        = make_cccd(dob)
    return {
        "ho_so_id"           : make_id("ADM"),
        "ref_id"             : cccd,              # HIGH   | Regex (ambiguous: CCCD of applicant)
        "ten_chu_ho_so"      : name,                     # MEDIUM | LLM
        "val_02"             : make_phone(),             # MEDIUM | Regex (ambiguous: contact phone)
        "loai_ho_so"         : rand(DOC_TYPES),          # NONE
        "co_quan_tiep_nhan"  : rand(GOV_AGENCIES),      # NONE
        "ngay_nop"           : submitted,               # NONE
        "han_giai_quyet"     : deadline,                # NONE
        "trang_thai_xu_ly"   : rand(DOC_STATUSES),      # NONE
        "ext_info"           : make_email(name),         # MEDIUM | LLM   (ambiguous: result notification email)
        "code_x"             : cccd,          # HIGH   | Regex (ambiguous: tax code)
        "so_bao_hiem"        : make_social_insurance_no(), # HIGH | Regex
        "phi_ho_so"          : rand([0, 50_000, 100_000, 200_000]),  # NONE
        "nhan_vien_xu_ly"    : make_id("NV"),           # NONE
        "dia_chi_lien_lac"   : make_address(),           # LOW    | LLM
        "meta_addr"          : make_address(),           # LOW    | LLM   (ambiguous: org address)
        "so_ho_khau"         : make_household_no(),      # MEDIUM | Regex
        "kenh_tiep_nhan"     : rand(RECEPTION_CHANNELS),# NONE
        "ket_qua_xu_ly"      : rand(PROCESSING_RESULTS),# NONE
        "updated_at"         : make_date(2022, 2024),   # NONE
    }

def build_hr_row() -> dict:
    name = make_full_name()
    dob = make_dob()
    cccd = make_cccd(dob)
    return {
        "emp_id"             : make_id("EMP"),
        "so_cccd"            : cccd,              # HIGH   | Regex
        "ho_ten_nv"          : name,                     # MEDIUM | LLM
        "d_entry"            : dob,               # LOW    | LLM   (ambiguous: date of birth)
        "sdt_ca_nhan"        : make_phone(),             # MEDIUM | Regex
        "personal_email"     : make_email(name),         # MEDIUM | Regex
        "work_email"         : make_work_email(name),    # MEDIUM | Regex
        "res_data"           : make_address(),           # LOW    | LLM   (ambiguous: home address)
        "phong_ban"          : rand(DEPARTMENTS),        # NONE
        "chuc_vu"            : rand(POSITIONS),          # NONE
        "m_val"              : make_salary(),            # HIGH   | LLM   (ambiguous: monthly salary)
        "stk_ngan_hang"      : make_bank_account(),      # HIGH   | Regex
        "ten_ngan_hang"      : rand(BANKS),              # NONE
        "t_code"             : cccd,                     # HIGH   | Regex (ambiguous: personal tax code)
        "ins_num"            : make_social_insurance_no(), # HIGH | Regex (ambiguous: insurance number)
        "ngay_vao_lam"       : make_date(2010, 2024),   # NONE
        "loai_hop_dong"      : rand(CONTRACT_TYPES),     # NONE
        "noi_lam_viec"       : make_province(),          # LOW    | LLM
        "manager_id"         : make_id("EMP"),           # NONE
        "created_at"         : make_date(2022, 2024),   # NONE
    }

def build_txn_row() -> dict:
    sender   = make_full_name()
    receiver = make_full_name()
    txn_date = make_date(2022, 2024)
    dob      = make_dob()
    cccd     = make_cccd(dob)
    return {
        "txn_id"             : make_id("TXN"),
        "initiator_key"      : cccd,                     # HIGH   | Regex (ambiguous: CCCD of initiator)
        "sender_fullname"    : sender,                   # MEDIUM | LLM
        "acct_a"             : make_bank_account(),      # HIGH   | Regex (ambiguous: sender account)
        "val_c"              : make_phone(),             # MEDIUM | Regex (ambiguous: sender phone)
        "acct_b"             : make_bank_account(),      # HIGH   | Regex (ambiguous: receiver account)
        "receiver_name"      : receiver,                 # MEDIUM | LLM
        "so_tien"            : make_amount(),            # NONE
        "loai_tien_te"       : "VND",                   # NONE
        "loai_giao_dich"     : rand(TXN_TYPES),          # NONE
        "kenh_giao_dich"     : rand(TXN_CHANNELS),       # NONE
        "trang_thai"         : rand(TXN_STATUSES),       # NONE
        "notify_ref"         : make_email(sender),       # MEDIUM | LLM   (ambiguous: confirmation email)
        "ip_addr"            : make_ip(),                # MEDIUM | Regex
        "device_fingerprint" : make_device_fp(),         # NONE
        "geo_label"          : make_province(),          # LOW    | LLM   (ambiguous: transaction location)
        "receiver_phone"     : make_phone(),             # MEDIUM | Regex
        "phi_giao_dich"      : rand([0, 1_000, 2_000, 5_000, 10_000]),  # NONE
        "created_at"         : txn_date,                # NONE
        "batch_id"           : make_batch_id(),          # NONE
    }


# ── ENGINE — do not touch ─────────────────────────────────────────────────────

TABLES = [
    ("citizen_info.csv",           build_citizen_row),
    ("administrative_records.csv", build_admin_row),
    ("hr_employees.csv",           build_hr_row),
    ("transaction_logs.csv",       build_txn_row),
]

def write_csv(filename: str, row_fn, n_rows: int) -> None:
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    path = os.path.join(OUTPUT_DIR, filename)
    rows = [row_fn() for _ in range(n_rows)]
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=rows[0].keys())
        writer.writeheader()
        writer.writerows(rows)
    print(f"  ✅  {filename:40s}  {n_rows:>5,} rows  →  {path}")

def main() -> None:
    total = sum(TABLE_SIZES.values())
    print(f"\n{'='*60}")
    print(f"  Generating {total:,} rows across {len(TABLES)} tables")
    print(f"{'='*60}")
    for filename, row_fn in TABLES:
        n = TABLE_SIZES.get(filename, 5000)
        write_csv(filename, row_fn, n)
    print(f"{'='*60}")
    print(f"  Done. Output folder: {OUTPUT_DIR}/")
    print(f"{'='*60}\n")

if __name__ == "__main__":
    main()