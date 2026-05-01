-- ==============================================================================
-- Hospital Management System (HMS) Database
-- MySQL Version - Fully Normalized (3NF) Core Schema
-- ==============================================================================

-- Create and select database
CREATE DATABASE IF NOT EXISTS hms;
USE hms;

-- ------------------------------------------------------------------------------
-- 1. DROP TABLES (Reverse Dependency Order to avoid Foreign Key errors)
-- ------------------------------------------------------------------------------
DROP TABLE IF EXISTS medical_records;
DROP TABLE IF EXISTS audit_log;
DROP TABLE IF EXISTS appointments;
DROP TABLE IF EXISTS doctors;
DROP TABLE IF EXISTS test;
DROP TABLE IF EXISTS user;

-- ------------------------------------------------------------------------------
-- 2. CREATE TABLES
-- ------------------------------------------------------------------------------

CREATE TABLE user (
  id INT(11) NOT NULL AUTO_INCREMENT,
  username VARCHAR(50) NOT NULL,
  usertype VARCHAR(50) NOT NULL,
  email VARCHAR(50) NOT NULL,
  phone VARCHAR(12) DEFAULT NULL,
  gender VARCHAR(20) DEFAULT NULL,
  password VARCHAR(1000) NOT NULL,
  PRIMARY KEY (id),
  UNIQUE KEY unique_email (email)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE doctors (
  did INT(11) NOT NULL AUTO_INCREMENT,
  email VARCHAR(50) NOT NULL,
  doctorname VARCHAR(50) NOT NULL,
  dept VARCHAR(100) NOT NULL,
  PRIMARY KEY (did)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- 🚨 NORMALIZED APPOINTMENTS TABLE (No redundant name, email, phone, or gender)
CREATE TABLE appointments (
  apt_id INT(11) NOT NULL AUTO_INCREMENT,
  user_id INT(11) NOT NULL,            
  slot VARCHAR(50) NOT NULL,
  disease VARCHAR(50) NOT NULL,
  time VARCHAR(50) NOT NULL,
  date DATE NOT NULL,
  dept VARCHAR(50) NOT NULL,
  doctor VARCHAR(100) NOT NULL,
  PRIMARY KEY (apt_id),
  FOREIGN KEY (user_id) REFERENCES user(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE medical_records (
  record_id INT(11) NOT NULL AUTO_INCREMENT,
  apt_id INT(11) NOT NULL,
  diagnosis TEXT NOT NULL,
  prescription TEXT NOT NULL,
  notes TEXT,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (record_id),
  FOREIGN KEY (apt_id) REFERENCES appointments(apt_id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- 🚨 RENAMED AND NORMALIZED AUDIT LOG
CREATE TABLE audit_log (
  tid INT(11) NOT NULL AUTO_INCREMENT,
  apt_id INT(11) NOT NULL,
  user_id INT(11) NOT NULL,            
  action VARCHAR(50) NOT NULL,
  timestamp DATETIME NOT NULL,
  PRIMARY KEY (tid)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE test (
  id INT(11) NOT NULL AUTO_INCREMENT,
  name VARCHAR(20) NOT NULL,
  email VARCHAR(20) NOT NULL,
  PRIMARY KEY (id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;


-- ------------------------------------------------------------------------------
-- 3. MYSQL TRIGGERS (Updated for audit_log and user_id)
-- ------------------------------------------------------------------------------

-- Trigger: Log every new appointment INSERT
DELIMITER $$
CREATE TRIGGER appointment_insertion
AFTER INSERT ON appointments
FOR EACH ROW
BEGIN
  INSERT INTO audit_log (apt_id, user_id, action, timestamp)
  VALUES (NEW.apt_id, NEW.user_id, 'APPOINTMENT BOOKED', NOW());
END$$
DELIMITER ;

-- Trigger: Log every appointment UPDATE
DELIMITER $$
CREATE TRIGGER appointment_update
AFTER UPDATE ON appointments
FOR EACH ROW
BEGIN
  INSERT INTO audit_log (apt_id, user_id, action, timestamp)
  VALUES (NEW.apt_id, NEW.user_id, 'APPOINTMENT UPDATED', NOW());
END$$
DELIMITER ;

-- Trigger: Log every appointment DELETE
DELIMITER $$
CREATE TRIGGER appointment_delete
BEFORE DELETE ON appointments
FOR EACH ROW
BEGIN
  INSERT INTO audit_log (apt_id, user_id, action, timestamp)
  VALUES (OLD.apt_id, OLD.user_id, 'APPOINTMENT CANCELLED', NOW());
END$$
DELIMITER ;