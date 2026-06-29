CREATE TABLE IF NOT EXISTS users (
    id CHAR(36) NOT NULL DEFAULT (UUID()),
    email VARCHAR(255) NOT NULL,
    name VARCHAR(255) NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    role ENUM('admin', 'user') NOT NULL DEFAULT 'user',
    is_active TINYINT(1) NOT NULL DEFAULT 1,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    last_login DATETIME NULL,
    PRIMARY KEY (id),
    UNIQUE KEY email (email)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS reason_codes (
    id CHAR(36) NOT NULL DEFAULT (UUID()),
    code VARCHAR(50) NOT NULL,
    medical_aid VARCHAR(100) NOT NULL DEFAULT 'ALL',
    description TEXT NOT NULL,
    classification VARCHAR(100) NOT NULL,
    action TEXT NOT NULL,
    created_by CHAR(36) NULL,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (id),
    UNIQUE KEY uq_code_aid (code, medical_aid),
    KEY idx_codes_aid (medical_aid)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS recon_runs (
    id CHAR(36) NOT NULL DEFAULT (UUID()),
    user_id CHAR(36) NOT NULL,
    run_date DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    pdf_count INT NOT NULL DEFAULT 0,
    excel_claims INT NOT NULL DEFAULT 0,
    matched_count INT NOT NULL DEFAULT 0,
    shortfall_total_usd DECIMAL(12, 2) NOT NULL DEFAULT 0.00,
    error_count INT NOT NULL DEFAULT 0,
    output_filename VARCHAR(255) NOT NULL,
    output_filepath VARCHAR(500) NOT NULL,
    output_data LONGBLOB NULL,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (id),
    KEY idx_runs_user (user_id),
    KEY idx_runs_date (run_date DESC),
    CONSTRAINT recon_runs_ibfk_1
        FOREIGN KEY (user_id) REFERENCES users(id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
