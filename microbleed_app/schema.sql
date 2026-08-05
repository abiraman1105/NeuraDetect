-- Run this in MySQL to set up the database
CREATE DATABASE IF NOT EXISTS microbleed_db CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
USE microbleed_db;

CREATE TABLE IF NOT EXISTS admins (
    id            INT AUTO_INCREMENT PRIMARY KEY,
    username      VARCHAR(50)  NOT NULL UNIQUE,
    password_hash VARCHAR(255) NOT NULL,
    full_name     VARCHAR(100) NOT NULL,
    email         VARCHAR(120),
    created_at    DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS scans (
    id               INT AUTO_INCREMENT PRIMARY KEY,
    patient_name     VARCHAR(150) NOT NULL,
    patient_id       VARCHAR(50),
    image_filename   VARCHAR(255) NOT NULL,
    result_label     VARCHAR(100) NOT NULL,
    result_class     TINYINT     NOT NULL,
    confidence       FLOAT       NOT NULL,
    probabilities    TEXT        NOT NULL,
    notes            TEXT,
    uploaded_by      INT         NOT NULL,
    created_at       DATETIME    DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (uploaded_by) REFERENCES admins(id)
);

-- Default admin: username=admin  password=Admin@123
INSERT INTO admins (username, password_hash, full_name, email)
VALUES (
    'admin',
    'pbkdf2:sha256:600000$JhKLmNoPqRsTuVwX$a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2',
    'System Administrator',
    'admin@hospital.com'
)
ON DUPLICATE KEY UPDATE id=id;

-- NOTE: The hash above is a placeholder. Run init_admin.py to create a real hashed password.
