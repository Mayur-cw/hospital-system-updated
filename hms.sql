-- --------------------------------------------------------
-- Hospital Management System (HMS) Database
-- MySQL Version
-- --------------------------------------------------------

-- Create and select database
CREATE DATABASE IF NOT EXISTS hms;
USE hms;

-- --------------------------------------------------------
-- 1. DROP TABLES (if re-running)
-- --------------------------------------------------------

DROP TABLE IF EXISTS trigr;
DROP TABLE IF EXISTS patients;
DROP TABLE IF EXISTS doctors;
DROP TABLE IF EXISTS test;
DROP TABLE IF EXISTS user;

-- --------------------------------------------------------
-- 2. CREATE TABLES
-- --------------------------------------------------------

CREATE TABLE doctors (
  did INT(11) NOT NULL AUTO_INCREMENT,
  email VARCHAR(50) NOT NULL,
  doctorname VARCHAR(50) NOT NULL,
  dept VARCHAR(100) NOT NULL,
  PRIMARY KEY (did)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- --------------------------------------------------------

CREATE TABLE patients (
  pid INT(11) NOT NULL AUTO_INCREMENT,
  email VARCHAR(50) NOT NULL,
  name VARCHAR(50) NOT NULL,
  gender VARCHAR(50) NOT NULL,
  slot VARCHAR(50) NOT NULL,
  disease VARCHAR(50) NOT NULL,
  time TIME NOT NULL,
  date DATE NOT NULL,
  dept VARCHAR(50) NOT NULL,
  doctor VARCHAR(100) NOT NULL AFTER dept,
  number VARCHAR(12) NOT NULL,
  PRIMARY KEY (pid)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;


-- --------------------------------------------------------

CREATE TABLE test (
  id INT(11) NOT NULL AUTO_INCREMENT,
  name VARCHAR(20) NOT NULL,
  email VARCHAR(20) NOT NULL,
  PRIMARY KEY (id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- --------------------------------------------------------

CREATE TABLE trigr (
  tid INT(11) NOT NULL AUTO_INCREMENT,
  pid INT(11) NOT NULL,
  email VARCHAR(50) NOT NULL,
  name VARCHAR(50) NOT NULL,
  action VARCHAR(50) NOT NULL,
  timestamp DATETIME NOT NULL,
  PRIMARY KEY (tid)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- --------------------------------------------------------

CREATE TABLE user (
  id INT(11) NOT NULL AUTO_INCREMENT,
  username VARCHAR(50) NOT NULL,
  usertype VARCHAR(50) NOT NULL,
  email VARCHAR(50) NOT NULL,
  password VARCHAR(1000) NOT NULL,
  PRIMARY KEY (id),
  UNIQUE KEY unique_email (email)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- --------------------------------------------------------
-- 3. INSERT DATA
-- --------------------------------------------------------

INSERT INTO doctors (did, email, doctorname, dept) VALUES
(1, 'anees@gmail.com',      'anees',          'Cardiologists'),
(2, 'amrutha@gmail.com',    'amrutha bhatta', 'Dermatologists'),
(3, 'aadithyaa@gmail.com',  'aadithyaa',      'Anesthesiologists'),
(4, 'anees@gmail',          'anees',          'Endocrinologists'),
(5, 'aneeqah@gmail.com',    'aneekha',        'corona');

-- --------------------------------------------------------

INSERT INTO patients (pid, email, name, gender, slot, disease, time, date, dept, number) VALUES
(2,  'anees1@gmail.com',         'anees1 rehman khan', 'Male1',  'evening1', 'cold1', '21:20:00', '2020-02-02', 'ortho11predict',    '9874561110'),
(5,  'patient@gmail.com',        'patien',             'Male',   'morning',  'fevr',  '18:06:00', '2020-11-18', 'Cardiologists',     '9874563210'),
(7,  'patient@gmail.com',        'anees',              'Male',   'evening',  'cold',  '22:18:00', '2020-11-05', 'Dermatologists',    '9874563210'),
(8,  'patient@gmail.com',        'anees',              'Male',   'evening',  'cold',  '22:18:00', '2020-11-05', 'Dermatologists',    '9874563210'),
(9,  'aneesurrehman423@gmail.com','anees',             'Male',   'morning',  'cold',  '17:27:00', '2020-11-26', 'Anesthesiologists', '9874563210'),
(10, 'anees@gmail.com',          'anees',              'Male',   'evening',  'fever', '16:25:00', '2020-12-09', 'Cardiologists',     '9874589654'),
(15, 'khushi@gmail.com',         'khushi',             'Female', 'morning',  'corona','20:42:00', '2021-01-23', 'Anesthesiologists', '9874563210'),
(16, 'khushi@gmail.com',         'khushi',             'Female', 'evening',  'fever', '15:46:00', '2021-01-31', 'Endocrinologists',  '9874587496'),
(17, 'aneeqah@gmail.com',        'aneeqah',            'Female', 'evening',  'fever', '15:48:00', '2021-01-23', 'Endocrinologists',  '9874563210');

-- --------------------------------------------------------

INSERT INTO test (id, name, email) VALUES
(1, 'ANEES', 'ARK@GMAIL.COM'),
(2, 'test',  'test@gmail.com');

-- --------------------------------------------------------

INSERT INTO trigr (tid, pid, email, name, action, timestamp) VALUES
(1,  12, 'anees@gmail.com',    'ANEES',   'PATIENT INSERTED', '2020-12-02 16:35:10'),
(2,  11, 'anees@gmail.com',    'anees',   'PATIENT INSERTED', '2020-12-02 16:37:34'),
(3,  10, 'anees@gmail.com',    'anees',   'PATIENT UPDATED',  '2020-12-02 16:38:27'),
(4,  11, 'anees@gmail.com',    'anees',   'PATIENT UPDATED',  '2020-12-02 16:38:33'),
(5,  12, 'anees@gmail.com',    'ANEES',   'Patient Deleted',  '2020-12-02 16:40:40'),
(6,  11, 'anees@gmail.com',    'anees',   'PATIENT DELETED',  '2020-12-02 16:41:10'),
(7,  13, 'testing@gmail.com',  'testing', 'PATIENT INSERTED', '2020-12-02 16:50:21'),
(8,  13, 'testing@gmail.com',  'testing', 'PATIENT UPDATED',  '2020-12-02 16:50:32'),
(9,  13, 'testing@gmail.com',  'testing', 'PATIENT DELETED',  '2020-12-02 16:50:57'),
(10, 14, 'aneeqah@gmail.com',  'aneeqah', 'PATIENT INSERTED', '2021-01-22 15:18:09'),
(11, 14, 'aneeqah@gmail.com',  'aneeqah', 'PATIENT UPDATED',  '2021-01-22 15:18:29'),
(12, 14, 'aneeqah@gmail.com',  'aneeqah', 'PATIENT DELETED',  '2021-01-22 15:41:48'),
(13, 15, 'khushi@gmail.com',   'khushi',  'PATIENT INSERTED', '2021-01-22 15:43:02'),
(14, 15, 'khushi@gmail.com',   'khushi',  'PATIENT UPDATED',  '2021-01-22 15:43:11'),
(15, 16, 'khushi@gmail.com',   'khushi',  'PATIENT INSERTED', '2021-01-22 15:43:37'),
(16, 16, 'khushi@gmail.com',   'khushi',  'PATIENT UPDATED',  '2021-01-22 15:43:49'),
(17, 17, 'aneeqah@gmail.com',  'aneeqah', 'PATIENT INSERTED', '2021-01-22 15:44:41'),
(18, 17, 'aneeqah@gmail.com',  'aneeqah', 'PATIENT UPDATED',  '2021-01-22 15:44:52'),
(19, 17, 'aneeqah@gmail.com',  'aneeqah', 'PATIENT UPDATED',  '2021-01-22 15:44:59');

-- --------------------------------------------------------

INSERT INTO user (id, username, usertype, email, password) VALUES
(13, 'anees',   'Doctor',  'anees@gmail.com',   'pbkdf2:sha256:150000$xAKZCiJG$4c7a7e704708f86659d730565ff92e8327b01be5c49a6b1ef8afdf1c531fa5c3'),
(14, 'aneeqah', 'Patient', 'aneeqah@gmail.com', 'pbkdf2:sha256:150000$Yf51ilDC$028cff81a536ed9d477f9e45efcd9e53a9717d0ab5171d75334c397716d581b8'),
(15, 'khushi',  'Patient', 'khushi@gmail.com',  'pbkdf2:sha256:150000$BeSHeRKV$a8b27379ce9b2499d4caef21d9d387260b3e4ba9f7311168b6e180a00db91f22');

-- --------------------------------------------------------
-- 4. TRIGGERS
-- --------------------------------------------------------

-- Trigger: Log every new patient INSERT
DELIMITER $$
CREATE TRIGGER patientinsertion
AFTER INSERT ON patients
FOR EACH ROW
BEGIN
  INSERT INTO trigr (pid, email, name, action, timestamp)
  VALUES (NEW.pid, NEW.email, NEW.name, 'PATIENT INSERTED', NOW());
END$$
DELIMITER ;

-- --------------------------------------------------------

-- Trigger: Log every patient UPDATE
DELIMITER $$
CREATE TRIGGER PatientUpdate
AFTER UPDATE ON patients
FOR EACH ROW
BEGIN
  INSERT INTO trigr (pid, email, name, action, timestamp)
  VALUES (NEW.pid, NEW.email, NEW.name, 'PATIENT UPDATED', NOW());
END$$
DELIMITER ;

-- --------------------------------------------------------

-- Trigger: Log every patient DELETE (uses OLD since row is being removed)
DELIMITER $$
CREATE TRIGGER PatientDelete
BEFORE DELETE ON patients
FOR EACH ROW
BEGIN
  INSERT INTO trigr (pid, email, name, action, timestamp)
  VALUES (OLD.pid, OLD.email, OLD.name, 'PATIENT DELETED', NOW());
END$$
DELIMITER ;

-- --------------------------------------------------------
-- 5. SET AUTO_INCREMENT values
-- --------------------------------------------------------

ALTER TABLE doctors  AUTO_INCREMENT = 6;
ALTER TABLE patients AUTO_INCREMENT = 18;
ALTER TABLE test     AUTO_INCREMENT = 12;
ALTER TABLE trigr    AUTO_INCREMENT = 20;
ALTER TABLE user     AUTO_INCREMENT = 16;