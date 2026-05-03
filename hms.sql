-- ==============================================================================
-- Hospital Management System (HMS) Database
-- ACADEMIC UPGRADE VERSION: 3NF, ENUM Constraints, Indexes, Views & Procedures
-- ==============================================================================

CREATE DATABASE IF NOT EXISTS hms;
USE hms;

-- ------------------------------------------------------------------------------
-- 1. CLEANUP (Strict Reverse Dependency Order to prevent FK errors)
-- ------------------------------------------------------------------------------
DROP PROCEDURE IF EXISTS BookAppointmentSafe;
DROP VIEW IF EXISTS revenue_summary;
DROP VIEW IF EXISTS doctor_directory_view;
DROP TRIGGER IF EXISTS billing_update;
DROP TRIGGER IF EXISTS billing_insertion;
DROP TRIGGER IF EXISTS appointment_delete;
DROP TRIGGER IF EXISTS appointment_update;
DROP TRIGGER IF EXISTS appointment_insertion;
DROP TRIGGER IF EXISTS admission_update;
DROP TRIGGER IF EXISTS admission_insert;

DROP TABLE IF EXISTS audit_log;
DROP TABLE IF EXISTS billing;
DROP TABLE IF EXISTS medical_records;
DROP TABLE IF EXISTS admissions;
DROP TABLE IF EXISTS rooms;
DROP TABLE IF EXISTS appointments;
DROP TABLE IF EXISTS doctors;
DROP TABLE IF EXISTS user;
DROP TABLE IF EXISTS test;

-- ------------------------------------------------------------------------------
-- 2. CREATE TABLES (With Strict Domain Constraints)
-- ------------------------------------------------------------------------------

CREATE TABLE user (
  id INT(11) NOT NULL AUTO_INCREMENT,
  username VARCHAR(50) NOT NULL,
  usertype ENUM('Admin', 'Doctor', 'Patient') NOT NULL, 
  email VARCHAR(50) NOT NULL,
  phone VARCHAR(12) DEFAULT NULL,
  gender ENUM('Male', 'Female', 'Others') DEFAULT NULL,
  password VARCHAR(1000) NOT NULL,
  PRIMARY KEY (id),
  UNIQUE KEY unique_email (email)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE doctors (
  did INT(11) NOT NULL AUTO_INCREMENT,
  user_id INT(11) NOT NULL, 
  dept VARCHAR(100) NOT NULL,
  PRIMARY KEY (did),
  FOREIGN KEY (user_id) REFERENCES user(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE appointments (
  apt_id INT(11) NOT NULL AUTO_INCREMENT,
  user_id INT(11) NOT NULL,            
  slot VARCHAR(50) NOT NULL,
  disease VARCHAR(50) NOT NULL,
  time VARCHAR(15) NOT NULL,
  date DATE NOT NULL,
  dept VARCHAR(50) NOT NULL,
  doctor VARCHAR(100) NOT NULL,
  PRIMARY KEY (apt_id),
  FOREIGN KEY (user_id) REFERENCES user(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE INDEX idx_doctor_date ON appointments(doctor, date);

-- 🏥 NEW ROOM MANAGEMENT TABLES
CREATE TABLE rooms (
  room_id INT(11) NOT NULL AUTO_INCREMENT,
  room_number VARCHAR(10) NOT NULL UNIQUE,
  ward_type ENUM('General', 'ICU', 'VIP', 'Maternity') NOT NULL,
  rate_per_day DECIMAL(10,2) NOT NULL,
  status ENUM('Available', 'Occupied', 'Maintenance') NOT NULL DEFAULT 'Available',
  PRIMARY KEY (room_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE admissions (
  admission_id INT(11) NOT NULL AUTO_INCREMENT,
  apt_id INT(11) NOT NULL,  -- 🚨 NEW: Links admission to the exact appointment
  patient_id INT(11) NOT NULL,
  doctor_id INT(11) NOT NULL,
  room_id INT(11) NOT NULL,
  admission_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  discharge_date TIMESTAMP NULL DEFAULT NULL,
  status ENUM('Admitted', 'Discharged') NOT NULL DEFAULT 'Admitted',
  PRIMARY KEY (admission_id),
  FOREIGN KEY (apt_id) REFERENCES appointments(apt_id) ON DELETE CASCADE, -- 🚨 NEW
  FOREIGN KEY (patient_id) REFERENCES user(id) ON DELETE CASCADE,
  FOREIGN KEY (doctor_id) REFERENCES doctors(did) ON DELETE CASCADE,
  FOREIGN KEY (room_id) REFERENCES rooms(room_id) ON DELETE CASCADE
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

CREATE TABLE billing (
  bill_id INT(11) NOT NULL AUTO_INCREMENT,
  apt_id INT(11) NOT NULL,
  user_id INT(11) NOT NULL,
  amount DECIMAL(10,2) NOT NULL DEFAULT 500.00,
  status ENUM('Paid', 'Unpaid', 'Refunded') NOT NULL DEFAULT 'Unpaid', 
  issued_on TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  paid_on TIMESTAMP NULL DEFAULT NULL,
  payment_mode VARCHAR(50) DEFAULT NULL,
  bank_name VARCHAR(100) DEFAULT NULL,
  PRIMARY KEY (bill_id),
  FOREIGN KEY (apt_id) REFERENCES appointments(apt_id) ON DELETE CASCADE,
  FOREIGN KEY (user_id) REFERENCES user(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

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
-- 3. SQL VIEWS (Data Abstraction)
-- ------------------------------------------------------------------------------

CREATE VIEW revenue_summary AS
SELECT 
    SUM(amount) AS gross_revenue,
    SUM(CASE WHEN status = 'Paid' THEN amount ELSE 0 END) AS total_collected,
    SUM(CASE WHEN status = 'Unpaid' THEN amount ELSE 0 END) AS pending_revenue
FROM billing;

CREATE VIEW doctor_directory_view AS
SELECT 
    d.did, 
    u.email, 
    u.username AS doctorname, 
    d.dept 
FROM doctors d
JOIN user u ON d.user_id = u.id;

-- ------------------------------------------------------------------------------
-- 4. MYSQL TRIGGERS (Automated Auditing & State Management)
-- ------------------------------------------------------------------------------

DELIMITER $$
CREATE TRIGGER appointment_insertion
AFTER INSERT ON appointments
FOR EACH ROW
BEGIN
  INSERT INTO audit_log (apt_id, user_id, action, timestamp)
  VALUES (NEW.apt_id, NEW.user_id, 'APPOINTMENT BOOKED', NOW());
END$$
DELIMITER ;

DELIMITER $$
CREATE TRIGGER appointment_update
AFTER UPDATE ON appointments
FOR EACH ROW
BEGIN
  INSERT INTO audit_log (apt_id, user_id, action, timestamp)
  VALUES (NEW.apt_id, NEW.user_id, 'APPOINTMENT UPDATED', NOW());
END$$
DELIMITER ;

DELIMITER $$
CREATE TRIGGER appointment_delete
BEFORE DELETE ON appointments
FOR EACH ROW
BEGIN
  INSERT INTO audit_log (apt_id, user_id, action, timestamp)
  VALUES (OLD.apt_id, OLD.user_id, 'APPOINTMENT CANCELLED', NOW());
END$$
DELIMITER ;

DELIMITER $$
CREATE TRIGGER billing_insertion
AFTER INSERT ON billing
FOR EACH ROW
BEGIN
  INSERT INTO audit_log (apt_id, user_id, action, timestamp)
  VALUES (NEW.apt_id, NEW.user_id, 'BILL GENERATED', NOW());
END$$
DELIMITER ;

DELIMITER $$
CREATE TRIGGER billing_update
AFTER UPDATE ON billing
FOR EACH ROW
BEGIN
  IF OLD.status <> NEW.status AND NEW.status = 'Paid' THEN
    INSERT INTO audit_log (apt_id, user_id, action, timestamp)
    VALUES (NEW.apt_id, NEW.user_id, 'BILL PAID', NOW());
  END IF;
END$$
DELIMITER ;

-- 🏥 NEW AUTOMATION: Auto-Toggle Room Availability
DELIMITER $$
CREATE TRIGGER admission_insert
AFTER INSERT ON admissions
FOR EACH ROW
BEGIN
  IF NEW.status = 'Admitted' THEN
    UPDATE rooms SET status = 'Occupied' WHERE room_id = NEW.room_id;
  END IF;
END$$
DELIMITER ;

DELIMITER $$
CREATE TRIGGER admission_update
AFTER UPDATE ON admissions
FOR EACH ROW
BEGIN
  IF OLD.status <> NEW.status AND NEW.status = 'Discharged' THEN
    UPDATE rooms SET status = 'Available' WHERE room_id = NEW.room_id;
  END IF;
END$$
DELIMITER ;

-- ------------------------------------------------------------------------------
-- 5. STORED PROCEDURES (ACID Concurrency Control)
-- ------------------------------------------------------------------------------

DELIMITER $$

CREATE PROCEDURE BookAppointmentSafe(
    IN p_user_id INT,
    IN p_slot VARCHAR(50),
    IN p_disease VARCHAR(50),
    IN p_time VARCHAR(15),
    IN p_date DATE,
    IN p_dept VARCHAR(50),
    IN p_doctor VARCHAR(100)
)
BEGIN
    DECLARE slot_count INT;
    
    START TRANSACTION;
    
    SELECT COUNT(*) INTO slot_count 
    FROM appointments 
    WHERE doctor = p_doctor AND date = p_date AND time = p_time AND slot NOT IN ('Cancelled', 'Missed')
    FOR UPDATE; 
    
    IF slot_count > 0 THEN
        ROLLBACK;
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Concurrency Error: Time slot was just booked by another user.';
    ELSE
        INSERT INTO appointments (user_id, slot, disease, time, date, dept, doctor)
        VALUES (p_user_id, p_slot, p_disease, p_time, p_date, p_dept, p_doctor);
        COMMIT;
    END IF;
END$$

DELIMITER ;