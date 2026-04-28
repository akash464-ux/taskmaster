-- ============================================================
--  TaskMaster Database Schema
--  Run this in MariaDB to set up your database
--  Command: mysql -u root -p < schema.sql
-- ============================================================

CREATE DATABASE IF NOT EXISTS taskmaster
    CHARACTER SET utf8mb4
    COLLATE utf8mb4_unicode_ci;

USE taskmaster;

-- ---- Users Table ----
CREATE TABLE IF NOT EXISTS users (
    id            INT AUTO_INCREMENT PRIMARY KEY,
    username      VARCHAR(50)  NOT NULL UNIQUE,
    email         VARCHAR(120) NOT NULL UNIQUE,
    password_hash VARCHAR(256) NOT NULL,
    created_at    DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- ---- Tasks Table ----
CREATE TABLE IF NOT EXISTS tasks (
    id          INT AUTO_INCREMENT PRIMARY KEY,
    user_id     INT          NOT NULL,
    title       VARCHAR(200) NOT NULL,
    description TEXT,
    priority    ENUM('low', 'medium', 'high') NOT NULL DEFAULT 'medium',
    status      ENUM('pending', 'done')       NOT NULL DEFAULT 'pending',
    due_date    DATE,
    created_at  DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at  DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    INDEX idx_user_status   (user_id, status),
    INDEX idx_user_priority (user_id, priority),
    INDEX idx_due_date      (due_date)
);