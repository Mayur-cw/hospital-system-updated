-- ==============================================================================
-- Script Name: seed_secure_accounts.sql
-- Description: Non-production seed template for local testing schema.
-- SECURITY MANDATE: Do not store plaintext passwords or production credentials here.
-- Use 'flask create-admin' or 'flask seed-demo' to populate development environments.
-- ==============================================================================

USE hms;

-- ------------------------------------------------------------------------------
-- 1. MASTER ACCOUNTS (Non-production demo placeholders)
-- ------------------------------------------------------------------------------

-- Master Admin Account Placeholder
INSERT INTO user (id, username, usertype, email, phone, gender, password) 
VALUES (
    1, 'Hospital Administrator', 'Admin', 'admin@hospital.local', '555-0100', 'Male',           
    'pbkdf2:sha256:600000$FAQHYDMCGcUV7cZu$8fa6fece9349fe77fb0d543c428136eb0ee4401f94958f05262701b135009e02'
);

-- Primary Doctor Account Placeholder
INSERT INTO user (id, username, usertype, email, gender, password) 
VALUES (
    2, 'Dr. Siddhi Meghale', 'Doctor', 'drsiddhi@hospital.local', 'Female',
    'pbkdf2:sha256:600000$1n03ta2yOQgT2H30$17e9ce072ce26e73c252d4b7c3222b07b9ce3d0dca5f07926413477e1509cfa8'
);

-- Primary Patient Account Placeholder
INSERT INTO user (id, username, usertype, email, phone, gender, password) 
VALUES (
    3, 'Rehman Daket', 'Patient', 'rehman@hospital.local', '555-0200', 'Male',
    'pbkdf2:sha256:600000$5kTAk9fr1fnvKZrK$dd0d506c14e04c44bdff51ed442f79bdc704cfadf0716b3a13edd681cfce6ada'
);

-- ------------------------------------------------------------------------------
-- 2. SAMPLE DOCTOR ACCOUNTS
-- ------------------------------------------------------------------------------
INSERT INTO user (id, username, usertype, email, password) VALUES 
(4, 'Dr. Anushka', 'Doctor', 'anushka@hospital.local', 'pbkdf2:sha256:600000$FAQHYDMCGcUV7cZu$8fa6fece9349fe77fb0d543c428136eb0ee4401f94958f05262701b135009e02'),
(5, 'Dr. Amruta', 'Doctor', 'amruta@hospital.local', 'pbkdf2:sha256:600000$FAQHYDMCGcUV7cZu$8fa6fece9349fe77fb0d543c428136eb0ee4401f94958f05262701b135009e02'),
(6, 'Dr. Aaditya', 'Doctor', 'aaditya@hospital.local', 'pbkdf2:sha256:600000$FAQHYDMCGcUV7cZu$8fa6fece9349fe77fb0d543c428136eb0ee4401f94958f05262701b135009e02'),
(7, 'Dr. Mangesh Wagh', 'Doctor', 'mangesh@hospital.local', 'pbkdf2:sha256:600000$FAQHYDMCGcUV7cZu$8fa6fece9349fe77fb0d543c428136eb0ee4401f94958f05262701b135009e02'),
(8, 'Dr. Pranjal', 'Doctor', 'pranjal@hospital.local', 'pbkdf2:sha256:600000$FAQHYDMCGcUV7cZu$8fa6fece9349fe77fb0d543c428136eb0ee4401f94958f05262701b135009e02');

INSERT INTO doctors (did, user_id, dept) VALUES
(1, 4, 'Cardiologists'),
(2, 5, 'Dermatologists'),
(3, 6, 'Anesthesiologists'),
(4, 7, 'Endocrinologists'),
(5, 8, 'Infectious Disease'),
(6, 2, 'Cardiologists');

-- ------------------------------------------------------------------------------
-- 3. SAMPLE PATIENT ACCOUNTS
-- ------------------------------------------------------------------------------
INSERT INTO user (id, username, usertype, email, phone, gender, password) VALUES 
(9,  'Priya Patil',    'Patient', 'priya.patil@hospital.local',    '555-0201', 'Female', 'pbkdf2:sha256:600000$FAQHYDMCGcUV7cZu$8fa6fece9349fe77fb0d543c428136eb0ee4401f94958f05262701b135009e02'),
(10, 'Arjun Sharma',   'Patient', 'arjun.sharma@hospital.local',   '555-0202', 'Male',   'pbkdf2:sha256:600000$FAQHYDMCGcUV7cZu$8fa6fece9349fe77fb0d543c428136eb0ee4401f94958f05262701b135009e02'),
(11, 'Sneha Kulkarni', 'Patient', 'sneha.kulkarni@hospital.local', '555-0203', 'Female', 'pbkdf2:sha256:600000$FAQHYDMCGcUV7cZu$8fa6fece9349fe77fb0d543c428136eb0ee4401f94958f05262701b135009e02'),
(12, 'Vikram Singh',   'Patient', 'vikram.singh@hospital.local',   '555-0204', 'Male',   'pbkdf2:sha256:600000$FAQHYDMCGcUV7cZu$8fa6fece9349fe77fb0d543c428136eb0ee4401f94958f05262701b135009e02');

-- ------------------------------------------------------------------------------
-- 4. NORMALIZED APPOINTMENT DATA
-- ------------------------------------------------------------------------------
INSERT INTO appointments (apt_id, user_id, slot, disease, time, date, dept, doctor) VALUES
(1, 3, 'Completed', 'Chest Pain',        '10:30 PM', '2026-05-03', 'Cardiologists',      'Dr. Siddhi Meghale'),
(2, 3, 'Scheduled', 'Routine Follow-up', '08:30 PM', '2026-05-03', 'Cardiologists',      'Dr. Siddhi Meghale'),
(3, 3, 'Attended',  'Viral Fever',       '11:00 AM', '2026-05-02', 'Infectious Disease', 'Dr. Pranjal'),
(4, 9, 'Completed', 'Skin Rash',         '10:00 AM', '2026-05-01', 'Dermatologists',     'Dr. Amruta'),
(5, 10, 'Missed',   'Back Surgery Prep', '03:30 PM', '2026-05-04', 'Anesthesiologists',  'Dr. Aaditya'),
(6, 11, 'Scheduled', 'Diabetes Check',   '11:30 AM', '2026-05-05', 'Endocrinologists',   'Dr. Mangesh Wagh'),
(7, 12, 'Attended',  'High BP',          '12:30 PM', '2026-05-07', 'Cardiologists',      'Dr. Anushka'),
(8, 9,  'Cancelled', 'Acne Treatment',   '04:30 PM', '2026-05-10', 'Dermatologists',     'Dr. Amruta');

-- ------------------------------------------------------------------------------
-- 5. MEDICAL RECORDS
-- ------------------------------------------------------------------------------
INSERT INTO medical_records (record_id, apt_id, diagnosis, prescription, notes) VALUES
(1, 1, 'Mild Angina Pectoris, stable condition.', 'Aspirin 75mg OD for 30 days.\nAtorvastatin 10mg HS.', 'Check BP daily. Avoid heavy lifting and saturated fats.'),
(2, 4, 'Contact Dermatitis.', 'Hydrocortisone 1% cream apply twice daily.\nCetirizine 10mg SOS for itching.', 'Keep affected area dry. Avoid suspected allergens.');

-- ------------------------------------------------------------------------------
-- 6. ROOMS (Inpatient Ward Setup)
-- ------------------------------------------------------------------------------
INSERT INTO rooms (room_id, room_number, ward_type, rate_per_day, status) VALUES
(1, '101', 'General',   800.00, 'Available'),
(2, '102', 'General',   800.00, 'Available'),
(3, '201', 'ICU',      3500.00, 'Available'),
(4, '301', 'VIP',      5000.00, 'Available'),
(5, '401', 'Maternity', 1500.00, 'Available');
