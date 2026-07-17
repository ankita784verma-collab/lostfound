-- ==========================================================
-- Lost & Found Portal - Database Schema
-- Engine: pymongo
-- ==========================================================

CREATE DATABASE IF NOT EXISTS lost_found_db
  CHARACTER SET utf8mb4
  COLLATE utf8mb4_unicode_ci;

USE lost_found_db;

-- ----------------------------------------------------------
-- Table: users
-- ----------------------------------------------------------
CREATE TABLE IF NOT EXISTS users (
    id INT AUTO_INCREMENT PRIMARY KEY,
    full_name VARCHAR(120) NOT NULL,
    email VARCHAR(150) NOT NULL UNIQUE,
    phone VARCHAR(20) DEFAULT NULL,
    password_hash VARCHAR(255) NOT NULL,
    is_admin TINYINT(1) NOT NULL DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB;

-- ----------------------------------------------------------
-- Table: items  (both lost & found reports live here)
-- ----------------------------------------------------------
CREATE TABLE IF NOT EXISTS items (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL,
    item_type ENUM('lost', 'found') NOT NULL,
    title VARCHAR(150) NOT NULL,
    category VARCHAR(60) NOT NULL,
    description TEXT,
    location VARCHAR(150) NOT NULL,
    event_date DATE NOT NULL,
    contact_info VARCHAR(150) NOT NULL,
    image_path VARCHAR(255) DEFAULT NULL,
    status ENUM('open', 'matched', 'resolved') NOT NULL DEFAULT 'open',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    INDEX idx_item_type (item_type),
    INDEX idx_category (category),
    INDEX idx_status (status)
) ENGINE=InnoDB;

-- ----------------------------------------------------------
-- Table: claims (someone responds to an item saying
-- "this is mine" or "I think I found this")
-- ----------------------------------------------------------
CREATE TABLE IF NOT EXISTS claims (
    id INT AUTO_INCREMENT PRIMARY KEY,
    item_id INT NOT NULL,
    claimant_id INT NOT NULL,
    message TEXT NOT NULL,
    status ENUM('pending', 'accepted', 'rejected') NOT NULL DEFAULT 'pending',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (item_id) REFERENCES items(id) ON DELETE CASCADE,
    FOREIGN KEY (claimant_id) REFERENCES users(id) ON DELETE CASCADE
) ENGINE=InnoDB;

-- ----------------------------------------------------------
-- View used for Power BI / analytics (clean, flattened data)
-- ----------------------------------------------------------
CREATE OR REPLACE VIEW vw_items_report AS
SELECT
    i.id,
    i.item_type,
    i.title,
    i.category,
    i.location,
    i.event_date,
    i.status,
    i.created_at,
    u.full_name AS reported_by,
    (SELECT COUNT(*) FROM claims c WHERE c.item_id = i.id) AS claim_count
FROM items i
JOIN users u ON u.id = i.user_id;
