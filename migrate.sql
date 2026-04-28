-- ============================================================
--  Migration: Add time & alarm support to tasks
--  Run this in your terminal:
--  docker exec -i myproject_db mariadb -u myuser -pmy taskmaster < migrate.sql
-- ============================================================

USE taskmaster;

-- Add due time (e.g. 14:30:00)
ALTER TABLE tasks
    ADD COLUMN due_time   TIME DEFAULT NULL AFTER due_date;

-- Add alarm time (user-chosen time to be alerted)
ALTER TABLE tasks
    ADD COLUMN alarm_time DATETIME DEFAULT NULL AFTER due_time;

-- Add alarm_triggered flag so we don't repeat alarms
ALTER TABLE tasks
    ADD COLUMN alarm_triggered TINYINT(1) DEFAULT 0 AFTER alarm_time;