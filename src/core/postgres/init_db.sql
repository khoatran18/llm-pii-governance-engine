-- 1. Bảng quản lý danh sách bảng Iceberg
CREATE TABLE IF NOT EXISTS tables_metadata (
    table_id SERIAL PRIMARY KEY,
    table_name VARCHAR(255) UNIQUE NOT NULL,
    iceberg_path VARCHAR(512) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 2. Bảng quản lý cấu trúc cột và nhãn PII
CREATE TABLE IF NOT EXISTS columns_metadata (
    column_id SERIAL PRIMARY KEY,
    table_id INT REFERENCES tables_metadata(table_id) ON DELETE CASCADE,
    column_name VARCHAR(255) NOT NULL,
    sensitivity_tag VARCHAR(50) DEFAULT 'NONE',
    sensitivity_level VARCHAR(20) DEFAULT 'NONE',
    detection_method VARCHAR(50) DEFAULT 'REGEX',
    confidence_score FLOAT DEFAULT 1.0,
    reason TEXT,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (table_id, column_name)
);

-- 3. Bảng danh mục các Vai trò người dùng trong doanh nghiệp
CREATE TABLE IF NOT EXISTS roles (
    role_id SERIAL PRIMARY KEY,
    role_name VARCHAR(50) UNIQUE NOT NULL,                                      -- ADMIN, ANALYST, AUDITOR
    role_description VARCHAR(255) DEFAULT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 4. Bảng chính sách truy cập theo
CREATE TABLE IF NOT EXISTS access_policies (
    policy_id SERIAL PRIMARY KEY,
    role_name VARCHAR(50) REFERENCES roles(role_name) ON UPDATE CASCADE,        -- HIGH, MEDIUM, LOW
    sensitivity_level VARCHAR(10) NOT NULL,
    masking_rule VARCHAR(50) NOT NULL,                                          -- HASH_MASK, REDACTED, NULLIFY, PARTIAL_MASK, CLEAR_TEXT
    UNIQUE (role_name, sensitivity_level)
);

-- 5. Các bảng Audit
CREATE TABLE IF NOT EXISTS governance_audit_logs (
    log_id SERIAL PRIMARY KEY,
    table_id INT REFERENCES tables_metadata(table_id) ON DELETE CASCADE,
    table_name VARCHAR(255) NOT NULL,
    column_name VARCHAR(255) NOT NULL,
    detection_method VARCHAR(50) NOT NULL,
    sensitivity_tag VARCHAR(50) NOT NULL,
    sensitivity_level VARCHAR(20) NOT NULL,
    confidence_score FLOAT NOT NULL,
    reason TEXT,
    scanned_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS policy_engine_audit_logs (
    log_id BIGSERIAL PRIMARY KEY,
    user_role VARCHAR(50) NOT NULL,
    target_table VARCHAR(255) NOT NULL,
    context_details JSONB,
    executed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);


TRUNCATE TABLE access_policies CASCADE;

INSERT INTO roles (role_name, role_description) VALUES
('ADMIN', 'Quản trị viên toàn quyền'),
('ANALYST', 'Chuyên viên phân tích dữ liệu'),
('AUDITOR', 'Kiểm toán viên an toàn thông tin')
ON CONFLICT (role_name) DO NOTHING;

TRUNCATE TABLE access_policies CASCADE;

-- 1. Chính sách cho Role: ADMIN
INSERT INTO access_policies (role_name, sensitivity_level, masking_rule) VALUES
('ADMIN', 'LOW', 'CLEAR_TEXT'),
('ADMIN', 'MEDIUM', 'CLEAR_TEXT'),
('ADMIN', 'HIGH', 'CLEAR_TEXT'),
('ADMIN', 'NONE', 'CLEAR_TEXT');

-- 2. Chính sách cho Role: ANALYST
INSERT INTO access_policies (role_name, sensitivity_level, masking_rule) VALUES
('ANALYST', 'LOW', 'HASH_MASK'),
('ANALYST', 'MEDIUM', 'NULLIFY_MASK'),
('ANALYST', 'HIGH', 'HASH_MASK'),
('ANALYST', 'NONE', 'CLEAR_TEXT');

-- 3. Chính sách cho Role: AUDITOR
INSERT INTO access_policies (role_name, sensitivity_level, masking_rule) VALUES
('AUDITOR', 'LOW', 'REDACTED_MASK'),
('AUDITOR', 'MEDIUM', 'PARTIAL_MASK'),
('AUDITOR', 'HIGH', 'PARTIAL_MASK'),
('AUDITOR', 'NONE', 'CLEAR_TEXT');