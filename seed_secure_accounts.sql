-- ==============================================================================
-- Script Name: seed_secure_accounts.sql
-- Description: Initializes secure master accounts for the HMS system.
-- Security Note: Passwords are NEVER stored in plain text. They are hashed 
--                using Werkzeug's PBKDF2:SHA256 algorithm with a unique salt.
-- ==============================================================================

USE hms;

-- ------------------------------------------------------------------------------
-- 1. Create Master Administrator Account (Mayur)
-- ------------------------------------------------------------------------------
-- HOW THIS HASH WAS GENERATED (Run this exact command in your terminal):
-- python -c "from werkzeug.security import generate_password_hash; print(generate_password_hash('mayur'))"

INSERT INTO user (id, username, usertype, email, phone, gender, password) 
VALUES (
    1,
    'Mayur Wakchaure', 
    'Admin', 
    'mayur@gmail.com', 
    '9850064866',     
    'Male',           
    'pbkdf2:sha256:600000$FAQHYDMCGcUV7cZu$8fa6fece9349fe77fb0d543c428136eb0ee4401f94958f05262701b135009e02'
);


-- ------------------------------------------------------------------------------
-- 2. Provision Doctor Account (Dr. Siddhi Meghale)
-- ------------------------------------------------------------------------------
-- HOW THIS HASH WAS GENERATED (Run this exact command in your terminal):
-- python -c "from werkzeug.security import generate_password_hash; print(generate_password_hash('siddhi'))"

-- A. Create the secure login credentials in the user table
INSERT INTO user (username, usertype, email, password) 
VALUES (
    'Siddhi Meghale', 
    'Doctor', 
    'drsiddhi@gmail.com', 
    'pbkdf2:sha256:600000$1n03ta2yOQgT2H30$17e9ce072ce26e73c252d4b7c3222b07b9ce3d0dca5f07926413477e1509cfa8'  -- <--- Replace this with your generated hash!
);

-- B. Automatically add the doctor to the public hospital directory
INSERT INTO doctors (did, email, doctorname, dept) 
VALUES (
    6, 
    'drsiddhi@gmail.com', 
    'Siddhi Meghale', 
    'Cardiologists'
);


-- ------------------------------------------------------------------------------
-- 3. Register Patient Account (Rehman Daket)
-- ------------------------------------------------------------------------------
-- HOW THIS HASH WAS GENERATED (Run this exact command in your terminal):
-- python -c "from werkzeug.security import generate_password_hash; print(generate_password_hash('rehman'))"

INSERT INTO user (username, usertype, email, gender, password) 
VALUES (
    'Rehman Daket', 
    'Patient', 
    'rehmandaket@gmail.com', 
    'Male',
    'pbkdf2:sha256:600000$5kTAk9fr1fnvKZrK$dd0d506c14e04c44bdff51ed442f79bdc704cfadf0716b3a13edd681cfce6ada'   -- <--- Replace this with your generated hash!
);

-- ==============================================================================
-- END OF SEED SCRIPT
-- ==============================================================================