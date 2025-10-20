-- FILE: web/database_setup.sql

-- WARNING: Running this script will DELETE and recreate the tables.
-- ONLY run this if you are setting up a fresh database.

-- Drop tables if they exist (to allow safe re-running)
DROP TABLE IF EXISTS readings;
DROP TABLE IF EXISTS device_shares; -- New share table
DROP TABLE IF EXISTS devices;
DROP TABLE IF EXISTS users;

-- 1. USERS Table (Authentication)
CREATE TABLE users (
    id SERIAL PRIMARY KEY,
    email VARCHAR(100) UNIQUE NOT NULL,
    name VARCHAR(100) NOT NULL,
    password_hash VARCHAR(150) NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- 2. DEVICES Table (The physical tracker unit)
-- The device is now independent of a single user.
CREATE TABLE devices (
    id SERIAL PRIMARY KEY,
    device_name VARCHAR(100) NOT NULL,
    -- IMEI is the unique identifier from the physical tracker
    unique_imei VARCHAR(15) UNIQUE NOT NULL, 
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- 3. DEVICE_SHARES Table (The link for multi-user access)
-- Allows a single IMEI (device) to be linked to multiple users.
CREATE TABLE device_shares (
    id SERIAL PRIMARY KEY,
    device_id INTEGER NOT NULL REFERENCES devices(id) ON DELETE CASCADE,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    -- Ensures a user can't link the same device more than once
    UNIQUE (device_id, user_id) 
);

-- 4. READINGS Table (GPS/Temp Data)
CREATE TABLE readings (
    id SERIAL PRIMARY KEY,
    device_id INTEGER NOT NULL REFERENCES devices(id) ON DELETE CASCADE,
    latitude DOUBLE PRECISION NOT NULL,
    longitude DOUBLE PRECISION NOT NULL,
    temperature DOUBLE PRECISION NOT NULL,
    gsm_time TIMESTAMP WITH TIME ZONE, -- Time from the GPS/GSM module
    received_at TIMESTAMP WITH TIME ZONE DEFAULT NOW() -- Time received by the server
);

-- Create index for faster data retrieval by device
CREATE INDEX idx_readings_device_id_received_at ON readings (device_id, received_at DESC);

-- Example: To run this script: psql -d your_db_name -f web/database_setup.sql