-- --------------------------------------------------------
-- Hospital Management System (HMS) Database
-- MySQL Version - Finalized & Cleaned
-- --------------------------------------------------------

-- Create and select database
CREATE DATABASE IF NOT EXISTS hms;
USE hms;

-- --------------------------------------------------------
-- 1. DROP TABLES (Reverse Dependency Order)
-- --------------------------------------------------------
-- medical_records must be dropped before appointments due to the Foreign Key constraint

DROP TABLE IF EXISTS medical_records;
DROP TABLE IF EXISTS trigr;
DROP TABLE IF EXISTS appointments;
DROP TABLE IF EXISTS doctors;
DROP TABLE IF EXISTS test;
DROP TABLE IF EXISTS user;

-- --------------------------------------------------------
-- 2. CREATE TABLES
-- --------------------------------------------------------

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

CREATE TABLE appointments (
  apt_id INT(11) NOT NULL AUTO_INCREMENT,
  email VARCHAR(50) NOT NULL,
  name VARCHAR(50) NOT NULL,
  gender VARCHAR(50) NOT NULL,
  slot VARCHAR(50) NOT NULL,
  disease VARCHAR(50) NOT NULL,
  time TIME NOT NULL,
  date DATE NOT NULL,
  dept VARCHAR(50) NOT NULL,
  doctor VARCHAR(100) NOT NULL,
  number VARCHAR(12) NOT NULL,
  PRIMARY KEY (apt_id)
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

CREATE TABLE trigr (
  tid INT(11) NOT NULL AUTO_INCREMENT,
  apt_id INT(11) NOT NULL,
  email VARCHAR(50) NOT NULL,
  name VARCHAR(50) NOT NULL,
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


-- --------------------------------------------------------
-- 3. INSERT REVISED SAMPLE DATA (April - May 2026)
-- --------------------------------------------------------

-- Insert Doctors Directory
INSERT INTO doctors (did, email, doctorname, dept) VALUES
(1, 'anushka@gmail.com',    'Anushka',        'Cardiologists'),
(2, 'amruta@gmail.com',     'Amruta',         'Dermatologists'),
(3, 'aaditya@gmail.com',    'Aaditya',        'Anesthesiologists'),
(4, 'mangesh@gmail.com',    'Mangesh Wagh',   'Endocrinologists'),
(5, 'pranjal@gmail.com',    'pranjal',        'corona');

-- Updated Appointments with Indian Names and 2026 Dates
INSERT INTO appointments (apt_id, email, name, gender, slot, disease, time, date, dept, doctor, number) VALUES
(1,  'arjun.sharma@gmail.com',   'Arjun Sharma',     'Male',   'morning', 'Fever',      '10:30:00', '2026-04-25', 'Cardiologists',     'Anushka',        '9850012345'),
(2,  'priya.patil@gmail.com',    'Priya Patil',      'Female', 'evening', 'Skin Rash',  '04:00:00', '2026-04-27', 'Dermatologists',    'Amruta',         '9822012345'),
(3,  'rahul.deshmukh@gmail.com', 'Rahul Deshmukh',   'Male',   'morning', 'Back Pain',  '11:00:00', '2026-04-29', 'Anesthesiologists', 'Aaditya',        '9970054321'),
(4,  'sneha.kulkarni@gmail.com', 'Sneha Kulkarni',   'Female', 'evening', 'Diabetes',   '03:30:00', '2026-05-01', 'Endocrinologists',  'Mangesh Wagh',   '9881165432'),
(5,  'amit.verma@gmail.com',     'Amit Verma',       'Male',   'morning', 'Chest Pain', '10:00:00', '2026-05-04', 'Cardiologists',     'Anushka', '9123456789'),
(6,  'ananya.iyer@gmail.com',    'Ananya Iyer',      'Female', 'evening', 'Migraine',   '04:30:00', '2026-05-06', 'Anesthesiologists', 'Aaditya',        '9011022334'),
(7,  'vikram.singh@gmail.com',   'Vikram Singh',     'Male',   'morning', 'Thyroid',    '11:30:00', '2026-05-08', 'Endocrinologists',  'Mangesh Wagh',   '9422055667');

-- --------------------------------------------------------

-- Insert Test Connection Data
INSERT INTO test (id, name, email) VALUES
(1, 'ANEES', 'ARK@GMAIL.COM'),
(2, 'test',  'test@gmail.com');
-- --------------------------------------------------------

-- Updated Sample Audit Logs (Matching the 2026 events)
INSERT INTO trigr (tid, apt_id, email, name, action, timestamp) VALUES
(1, 1, 'arjun.sharma@gmail.com',   'Arjun Sharma',   'APPOINTMENT BOOKED', '2026-04-20 10:15:00'),
(2, 2, 'priya.patil@gmail.com',    'Priya Patil',    'APPOINTMENT BOOKED', '2026-04-21 14:30:00'),
(3, 3, 'rahul.deshmukh@gmail.com', 'Rahul Deshmukh', 'APPOINTMENT BOOKED', '2026-04-22 09:00:00'),
(4, 4, 'sneha.kulkarni@gmail.com', 'Sneha Kulkarni', 'APPOINTMENT BOOKED', '2026-04-23 16:45:00'),
(5, 5, 'amit.verma@gmail.com',     'Amit Verma',     'APPOINTMENT BOOKED', '2026-04-24 11:20:00'),
(6, 6, 'ananya.iyer@gmail.com',    'Ananya Iyer',    'APPOINTMENT BOOKED', '2026-04-25 13:10:00'),
(7, 7, 'vikram.singh@gmail.com',   'Vikram Singh',   'APPOINTMENT BOOKED', '2026-04-26 08:55:00');

-- --------------------------------------------------------
-- 4. MYSQL TRIGGERS
-- --------------------------------------------------------

-- Trigger: Log every new appointment INSERT
DELIMITER $$
CREATE TRIGGER appointment_insertion
AFTER INSERT ON appointments
FOR EACH ROW
BEGIN
  INSERT INTO trigr (apt_id, email, name, action, timestamp)
  VALUES (NEW.apt_id, NEW.email, NEW.name, 'APPOINTMENT BOOKED', NOW());
END$$
DELIMITER ;

-- --------------------------------------------------------

-- Trigger: Log every appointment UPDATE
DELIMITER $$
CREATE TRIGGER appointment_update
AFTER UPDATE ON appointments
FOR EACH ROW
BEGIN
  INSERT INTO trigr (apt_id, email, name, action, timestamp)
  VALUES (NEW.apt_id, NEW.email, NEW.name, 'APPOINTMENT UPDATED', NOW());
END$$
DELIMITER ;

-- --------------------------------------------------------

-- Trigger: Log every appointment DELETE
DELIMITER $$
CREATE TRIGGER appointment_delete
BEFORE DELETE ON appointments
FOR EACH ROW
BEGIN
  INSERT INTO trigr (apt_id, email, name, action, timestamp)
  VALUES (OLD.apt_id, OLD.email, OLD.name, 'APPOINTMENT CANCELLED', NOW());
END$$
DELIMITER ;

-- --------------------------------------------------------
-- 5. SET AUTO_INCREMENT VALUES
-- --------------------------------------------------------

ALTER TABLE doctors  AUTO_INCREMENT = 6;
ALTER TABLE appointments AUTO_INCREMENT = 18;
ALTER TABLE test     AUTO_INCREMENT = 3;
ALTER TABLE trigr    AUTO_INCREMENT = 20;
ALTER TABLE user     AUTO_INCREMENT = 16;
ALTER TABLE medical_records AUTO_INCREMENT = 1;
