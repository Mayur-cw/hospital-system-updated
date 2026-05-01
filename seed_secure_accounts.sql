-- ==============================================================================
-- Script Name: seed_and_sample_data.sql
-- Description: Initializes master accounts AND populates sample test data.
-- Security Note: Passwords are hashed using Werkzeug's PBKDF2:SHA256 algorithm.
-- Testing Note: Admin and Sample accounts use password 'mayur'. 
--               Main doctor is 'siddhi'. Main patient is 'rehman'.
-- ==============================================================================

-- ==============================================================================
-- NOTE: Password creation ,
-- HOW THE HASH for Password is GENERATED (Run this exact command in your terminal):
-- python -c "from werkzeug.security import generate_password_hash; print(generate_password_hash('the_password_you wanna set'))"
-- ---eg:
-- python -c "from werkzeug.security import generate_password_hash; print(generate_password_hash('mayur'))"
-- output : pbkdf2:sha256:600000$FAQHYDMCGcUV7cZu$8fa6fece9349fe77fb0d543c428136eb0ee4401f94958f05262701b135009e02
-- ==============================================================================


USE hms;

-- ------------------------------------------------------------------------------
-- 1. MASTER ACCOUNTS (Your Seed Data)
-- ------------------------------------------------------------------------------

-- Master Admin Account (Password: mayur)
INSERT INTO user (id, username, usertype, email, phone, gender, password) 
VALUES (
    1, 'Mayur Wakchaure', 'Admin', 'mayur@gmail.com', '9850064866', 'Male',           
    'pbkdf2:sha256:600000$FAQHYDMCGcUV7cZu$8fa6fece9349fe77fb0d543c428136eb0ee4401f94958f05262701b135009e02'
);

-- Primary Doctor Account (Password: siddhi)
INSERT INTO user (id, username, usertype, email, gender, password) 
VALUES (
    2, 'Siddhi Meghale', 'Doctor', 'drsiddhi@gmail.com', 'Female',
    'pbkdf2:sha256:600000$1n03ta2yOQgT2H30$17e9ce072ce26e73c252d4b7c3222b07b9ce3d0dca5f07926413477e1509cfa8'
);

-- Primary Patient Account (Password: rehman)
INSERT INTO user (id, username, usertype, email, phone, gender, password) 
VALUES (
    3, 'Rehman Daket', 'Patient', 'rehmandaket@gmail.com', '9822012345', 'Male',
    'pbkdf2:sha256:600000$5kTAk9fr1fnvKZrK$dd0d506c14e04c44bdff51ed442f79bdc704cfadf0716b3a13edd681cfce6ada'
);

-- ------------------------------------------------------------------------------
-- 2. SAMPLE DOCTOR ACCOUNTS (So you can log in as them!)
--    All passwords for these accounts are: mayur
-- ------------------------------------------------------------------------------

INSERT INTO user (id, username, usertype, email, password) VALUES 
(4, 'Anushka', 'Doctor', 'anushka@gmail.com', 'pbkdf2:sha256:600000$FAQHYDMCGcUV7cZu$8fa6fece9349fe77fb0d543c428136eb0ee4401f94958f05262701b135009e02'),
(5, 'Amruta', 'Doctor', 'amruta@gmail.com', 'pbkdf2:sha256:600000$FAQHYDMCGcUV7cZu$8fa6fece9349fe77fb0d543c428136eb0ee4401f94958f05262701b135009e02'),
(6, 'Aaditya', 'Doctor', 'aaditya@gmail.com', 'pbkdf2:sha256:600000$FAQHYDMCGcUV7cZu$8fa6fece9349fe77fb0d543c428136eb0ee4401f94958f05262701b135009e02'),
(7, 'Mangesh Wagh', 'Doctor', 'mangesh@gmail.com', 'pbkdf2:sha256:600000$FAQHYDMCGcUV7cZu$8fa6fece9349fe77fb0d543c428136eb0ee4401f94958f05262701b135009e02'),
(8, 'Pranjal', 'Doctor', 'pranjal@gmail.com', 'pbkdf2:sha256:600000$FAQHYDMCGcUV7cZu$8fa6fece9349fe77fb0d543c428136eb0ee4401f94958f05262701b135009e02');

-- Link them into the public Doctors Directory
INSERT INTO doctors (did, email, doctorname, dept) VALUES
(1, 'anushka@gmail.com',    'Anushka',        'Cardiologists'),
(2, 'amruta@gmail.com',     'Amruta',         'Dermatologists'),
(3, 'aaditya@gmail.com',    'Aaditya',        'Anesthesiologists'),
(4, 'mangesh@gmail.com',    'Mangesh Wagh',   'Endocrinologists'),
(5, 'pranjal@gmail.com',    'Pranjal',        'Infectious Disease'),
(6, 'drsiddhi@gmail.com',   'Siddhi Meghale', 'Cardiologists');

-- ------------------------------------------------------------------------------
-- 3. SAMPLE PATIENT ACCOUNTS
--    All passwords for these accounts are: mayur
-- ------------------------------------------------------------------------------

INSERT INTO user (id, username, usertype, email, phone, gender, password) VALUES 
(9,  'Priya Patil',    'Patient', 'priya.patil@gmail.com',    '9850011223', 'Female', 'pbkdf2:sha256:600000$FAQHYDMCGcUV7cZu$8fa6fece9349fe77fb0d543c428136eb0ee4401f94958f05262701b135009e02'),
(10, 'Arjun Sharma',   'Patient', 'arjun.sharma@gmail.com',   '9970055443', 'Male',   'pbkdf2:sha256:600000$FAQHYDMCGcUV7cZu$8fa6fece9349fe77fb0d543c428136eb0ee4401f94958f05262701b135009e02'),
(11, 'Sneha Kulkarni', 'Patient', 'sneha.kulkarni@gmail.com', '9881166554', 'Female', 'pbkdf2:sha256:600000$FAQHYDMCGcUV7cZu$8fa6fece9349fe77fb0d543c428136eb0ee4401f94958f05262701b135009e02'),
(12, 'Vikram Singh',   'Patient', 'vikram.singh@gmail.com',   '9422077889', 'Male',   'pbkdf2:sha256:600000$FAQHYDMCGcUV7cZu$8fa6fece9349fe77fb0d543c428136eb0ee4401f94958f05262701b135009e02');

-- ------------------------------------------------------------------------------
-- 4. NORMALIZED APPOINTMENT DATA (April 30 - May 10)
-- ------------------------------------------------------------------------------

INSERT INTO appointments (apt_id, user_id, slot, disease, time, date, dept, doctor) VALUES
-- Rehman Daket (user_id: 3) visiting Dr. Siddhi
(1, 3, 'Scheduled', 'Chest Pain',        '10:30 AM', '2026-04-30', 'Cardiologists',      'Siddhi Meghale'),
(2, 3, 'Scheduled', 'Routine Follow-up', '04:00 PM', '2026-05-08', 'Cardiologists',      'Siddhi Meghale'),
-- Rehman Daket visiting another doctor
(3, 3, 'Scheduled', 'Viral Fever',       '11:00 AM', '2026-05-02', 'Infectious Disease', 'Pranjal'),

-- Other Patients (user_ids: 9, 10, 11, 12)
(4, 9,  'Scheduled', 'Skin Rash',        '10:00 AM', '2026-05-01', 'Dermatologists',     'Amruta'),
(5, 10, 'Scheduled', 'Back Surgery Prep','03:30 PM', '2026-05-04', 'Anesthesiologists',  'Aaditya'),
(6, 11, 'Scheduled', 'Diabetes Check',   '11:30 AM', '2026-05-05', 'Endocrinologists',   'Mangesh Wagh'),
(7, 12, 'Scheduled', 'High Blood Pressure','12:30 PM','2026-05-07','Cardiologists',      'Anushka'),
(8, 9,  'Scheduled', 'Acne Treatment',   '04:30 PM', '2026-05-10', 'Dermatologists',     'Amruta');

-- ------------------------------------------------------------------------------
-- 5. RESET AUTO_INCREMENT COUNTERS (Optional but clean)
-- ------------------------------------------------------------------------------
ALTER TABLE user AUTO_INCREMENT = 13;
ALTER TABLE doctors AUTO_INCREMENT = 7;
ALTER TABLE appointments AUTO_INCREMENT = 9;