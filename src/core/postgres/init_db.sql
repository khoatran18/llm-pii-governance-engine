-- =====================================================================
-- TẦNG DDL: KHỞI TẠO CẤU TRÚC BẢNG METADATA STORE
-- =====================================================================

-- 1. Bảng quản lý danh sách bảng Iceberg (Tuần 2)
CREATE TABLE IF NOT EXISTS tables_metadata (
    table_id SERIAL PRIMARY KEY,
    table_name VARCHAR(255) UNIQUE NOT NULL,
    iceberg_path VARCHAR(512) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 2. Bảng quản lý cấu trúc cột và nhãn PII (Tuần 2 + 3)
CREATE TABLE IF NOT EXISTS columns_metadata (
    column_id SERIAL PRIMARY KEY,
    table_id INT REFERENCES tables_metadata(table_id) ON DELETE CASCADE,
    column_name VARCHAR(255) NOT NULL,
    sensitivity_tag VARCHAR(50) DEFAULT 'NONE',      -- Ép theo Enum: RESIDENT_ID, PHONE, EMAIL, TAX_CODE, ...
    sensitivity_level VARCHAR(20) DEFAULT 'NONE',    -- Ép theo Enum: HIGH, MEDIUM, LOW, NONE
    detection_method VARCHAR(50) DEFAULT 'REGEX',    -- Ép theo Enum: REGEX, LLM, HYBRID
    confidence_score FLOAT DEFAULT 1.0,
    reason TEXT,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (table_id, column_name)
);

-- 3. Bảng danh mục các Vai trò người dùng trong doanh nghiệp (Mới tách)
CREATE TABLE IF NOT EXISTS roles (
    role_id SERIAL PRIMARY KEY,
    role_name VARCHAR(50) UNIQUE NOT NULL,           -- ADMIN, ANALYST, AUDITOR
    role_description VARCHAR(255) DEFAULT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 4. Bảng quản lý chính sách bảo mật động (Tuần 4)
CREATE TABLE IF NOT EXISTS access_policies (
    policy_id SERIAL PRIMARY KEY,
    role_name VARCHAR(50) REFERENCES roles(role_name) ON UPDATE CASCADE,      -- HIGH, MEDIUM, LOW
    sensitivity_level VARCHAR(10) NOT NULL,
    masking_rule VARCHAR(50) NOT NULL,            -- HASH_MASK, REDACTED, NULLIFY, PARTIAL_MASK, CLEAR_TEXT
    UNIQUE (role_name, sensitivity_level)
);

-- 4. Bảng nhật ký quét PII phục vụ Audit & Compliance (Tuần 3 + 5)
CREATE TABLE IF NOT EXISTS governance_audit_logs (
    log_id SERIAL PRIMARY KEY,
    table_id INT REFERENCES tables_metadata(table_id) ON DELETE CASCADE,
    table_name VARCHAR(255) NOT NULL,
    column_name VARCHAR(255) NOT NULL,
    detection_method VARCHAR(50) NOT NULL,            -- REGEX, LLM, HYBRID
    sensitivity_tag VARCHAR(50) NOT NULL,
    sensitivity_level VARCHAR(20) NOT NULL,
    confidence_score FLOAT NOT NULL,
    reason TEXT,                                      -- Lưu vết chuỗi lý do [DetectionReason] + LLM Context Reason
    scanned_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- =====================================================================
-- TẦNG DML: NẠP MA TRẬN CHÍNH SÁCH KIỂM SOÁT TRUY CẬP TRỤC DỌC (TUẦN 4)
-- =====================================================================

TRUNCATE TABLE access_policies CASCADE;

-- Nạp danh mục roles trước để làm mỏ neo khóa ngoại
INSERT INTO roles (role_name, role_description) VALUES
('ADMIN', 'Quản trị viên toàn quyền'),
('ANALYST', 'Chuyên viên phân tích dữ liệu'),
('AUDITOR', 'Kiểm toán viên an toàn thông tin')
ON CONFLICT (role_name) DO NOTHING;

TRUNCATE TABLE access_policies CASCADE;

-- 1. CHÍNH SÁCH CHO ROLE: ADMIN
INSERT INTO access_policies (role_name, sensitivity_level, masking_rule) VALUES
('ADMIN', 'LOW', 'CLEAR_TEXT'),
('ADMIN', 'MEDIUM', 'CLEAR_TEXT'),
('ADMIN', 'HIGH', 'CLEAR_TEXT');

-- 2. CHÍNH SÁCH CHO ROLE: ANALYST
INSERT INTO access_policies (role_name, sensitivity_level, masking_rule) VALUES
('ANALYST', 'LOW', 'HASH_MASK'),
('ANALYST', 'MEDIUM', 'NULLIFY_MASK'),
('ANALYST', 'HIGH', 'HASH_MASK');

-- 3. CHÍNH SÁCH CHO ROLE: AUDITOR
INSERT INTO access_policies (role_name, sensitivity_level, masking_rule) VALUES
('AUDITOR', 'LOW', 'REDACTED_MASK'),
('AUDITOR', 'MEDIUM', 'PARTIAL_MASK'),
('AUDITOR', 'HIGH', 'PARTIAL_MASK');    -- Che giữa giữ đầu đuôi phục vụ kiểm toán chứng từ