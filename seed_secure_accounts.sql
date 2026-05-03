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

use hms;

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
-- 2. SAMPLE DOCTOR ACCOUNTS (Password: mayur)
-- ------------------------------------------------------------------------------
INSERT INTO user (id, username, usertype, email, password) VALUES 
(4, 'Anushka', 'Doctor', 'anushka@gmail.com', 'pbkdf2:sha256:600000$FAQHYDMCGcUV7cZu$8fa6fece9349fe77fb0d543c428136eb0ee4401f94958f05262701b135009e02'),
(5, 'Amruta', 'Doctor', 'amruta@gmail.com', 'pbkdf2:sha256:600000$FAQHYDMCGcUV7cZu$8fa6fece9349fe77fb0d543c428136eb0ee4401f94958f05262701b135009e02'),
(6, 'Aaditya', 'Doctor', 'aaditya@gmail.com', 'pbkdf2:sha256:600000$FAQHYDMCGcUV7cZu$8fa6fece9349fe77fb0d543c428136eb0ee4401f94958f05262701b135009e02'),
(7, 'Mangesh Wagh', 'Doctor', 'mangesh@gmail.com', 'pbkdf2:sha256:600000$FAQHYDMCGcUV7cZu$8fa6fece9349fe77fb0d543c428136eb0ee4401f94958f05262701b135009e02'),
(8, 'Pranjal', 'Doctor', 'pranjal@gmail.com', 'pbkdf2:sha256:600000$FAQHYDMCGcUV7cZu$8fa6fece9349fe77fb0d543c428136eb0ee4401f94958f05262701b135009e02');

-- 🎓 UPGRADE: Link them into the Doctors table using ONLY their user_id (Foreign Key)
INSERT INTO doctors (did, user_id, dept) VALUES
(1, 4, 'Cardiologists'),
(2, 5, 'Dermatologists'),
(3, 6, 'Anesthesiologists'),
(4, 7, 'Endocrinologists'),
(5, 8, 'Infectious Disease'),
(6, 2, 'Cardiologists');

-- ------------------------------------------------------------------------------
-- 3. SAMPLE PATIENT ACCOUNTS (Password: mayur)
-- ------------------------------------------------------------------------------
INSERT INTO user (id, username, usertype, email, phone, gender, password) VALUES 
(9,  'Priya Patil',    'Patient', 'priya.patil@gmail.com',    '9850011223', 'Female', 'pbkdf2:sha256:600000$FAQHYDMCGcUV7cZu$8fa6fece9349fe77fb0d543c428136eb0ee4401f94958f05262701b135009e02'),
(10, 'Arjun Sharma',   'Patient', 'arjun.sharma@gmail.com',   '9970055443', 'Male',   'pbkdf2:sha256:600000$FAQHYDMCGcUV7cZu$8fa6fece9349fe77fb0d543c428136eb0ee4401f94958f05262701b135009e02'),
(11, 'Sneha Kulkarni', 'Patient', 'sneha.kulkarni@gmail.com', '9881166554', 'Female', 'pbkdf2:sha256:600000$FAQHYDMCGcUV7cZu$8fa6fece9349fe77fb0d543c428136eb0ee4401f94958f05262701b135009e02'),
(12, 'Vikram Singh',   'Patient', 'vikram.singh@gmail.com',   '9422077889', 'Male',   'pbkdf2:sha256:600000$FAQHYDMCGcUV7cZu$8fa6fece9349fe77fb0d543c428136eb0ee4401f94958f05262701b135009e02');

-- ------------------------------------------------------------------------------
-- 4. NORMALIZED APPOINTMENT DATA (Varying Statuses for UI Testing)
-- ------------------------------------------------------------------------------
INSERT INTO appointments (apt_id, user_id, slot, disease, time, date, dept, doctor) VALUES
(1, 3, 'Completed', 'Chest Pain',        '10:30 PM', '2026-05-03', 'Cardiologists',      'Siddhi Meghale'),
(2, 3, 'Scheduled', 'Routine Follow-up', '08:30 PM', '2026-05-03', 'Cardiologists',      'Siddhi Meghale'),
(3, 3, 'Attended',  'Viral Fever',       '11:00 AM', '2026-05-02', 'Infectious Disease', 'Pranjal'),
(4, 9, 'Completed', 'Skin Rash',         '10:00 AM', '2026-05-01', 'Dermatologists',     'Amruta'),
(5, 10, 'Missed',   'Back Surgery Prep', '03:30 PM', '2026-05-04', 'Anesthesiologists',  'Aaditya'),
(6, 11, 'Scheduled', 'Diabetes Check',   '11:30 AM', '2026-05-05', 'Endocrinologists',   'Mangesh Wagh'),
(7, 12, 'Attended',  'High BP',          '12:30 PM', '2026-05-07', 'Cardiologists',      'Anushka'),
(8, 9,  'Cancelled', 'Acne Treatment',   '04:30 PM', '2026-05-10', 'Dermatologists',     'Amruta');

-- ------------------------------------------------------------------------------
-- 5. MEDICAL RECORDS (For 'Completed' Appointments)
-- ------------------------------------------------------------------------------
INSERT INTO medical_records (record_id, apt_id, diagnosis, prescription, notes) VALUES
(1, 1, 'Mild Angina Pectoris, stable condition.', 'Aspirin 75mg OD for 30 days.\nAtorvastatin 10mg HS.', 'Check BP daily. Avoid heavy lifting and saturated fats.'),
(2, 4, 'Contact Dermatitis.', 'Hydrocortisone 1% cream apply twice daily.\nCetirizine 10mg SOS for itching.', 'Keep affected area dry. Avoid suspected allergens.');

-- ------------------------------------------------------------------------------
-- 6. BILLING DATA (Populating the Financial/Invoice Gateways)
-- ------------------------------------------------------------------------------
INSERT INTO billing (bill_id, apt_id, user_id, amount, status, issued_on, paid_on, payment_mode, bank_name) VALUES
-- Rehman Daket's Bills (1 Paid, 2 Unpaid)
(1, 1, 3, 500.00, 'Paid',   '2026-04-30 11:00:00', '2026-04-30 11:05:00', 'cash', NULL),
(2, 2, 3, 500.00, 'Unpaid', '2026-05-08 10:00:00', NULL, NULL, NULL),
(3, 3, 3, 650.00, 'Unpaid', '2026-05-02 11:45:00', NULL, NULL, NULL),

-- Other Patients (Mix of Paid Netbanking, Paid Cash, Unpaid)
(4, 4, 9,  800.00, 'Paid',   '2026-05-01 10:30:00', '2026-05-01 14:20:00', 'netbanking', 'HDFC'),
(5, 5, 10, 500.00, 'Unpaid', '2026-05-04 16:00:00', NULL, NULL, NULL),
(6, 6, 11, 750.00, 'Unpaid', '2026-05-05 09:00:00', NULL, NULL, NULL),
(7, 7, 12, 500.00, 'Unpaid', '2026-05-07 13:00:00', NULL, NULL, NULL),
(8, 8, 9,  500.00, 'Unpaid', '2026-05-10 08:00:00', NULL, NULL, NULL);

-- ------------------------------------------------------------------------------
-- 7. RESET AUTO_INCREMENT COUNTERS
-- ------------------------------------------------------------------------------
ALTER TABLE user AUTO_INCREMENT = 13;
ALTER TABLE doctors AUTO_INCREMENT = 7;
ALTER TABLE appointments AUTO_INCREMENT = 9;
ALTER TABLE medical_records AUTO_INCREMENT = 3;
ALTER TABLE billing AUTO_INCREMENT = 9;