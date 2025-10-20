# FILE: web/models.py

import os
import psycopg
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash

# --- Database Connection Function ---
def get_db_connection():
    db_url = os.environ.get('DATABASE_URL')
    if not db_url:
        # Fallback for local testing without .env loaded
        return None 
        
    try:
        conn = psycopg.connect(conninfo=db_url)
        return conn
    except Exception as e:
        print(f"DB Connection Error: {e}")
        return None

# ----------------------------------------------------------------------
# 1. USER MODEL (Includes new create_user method for registration)
# ----------------------------------------------------------------------

class User(UserMixin):
    """Represents a record in the 'users' table."""
    def __init__(self, id, email, password_hash, name):
        self.id = id
        self.email = email
        self.password_hash = password_hash
        self.name = name

    def get_id(self):
        return str(self.id)

    @staticmethod
    def set_password(password):
        """Hashes a plaintext password for secure storage."""
        # bcrypt hash output is about 60 chars long, but we need extra space
        # in the database (e.g., VARCHAR(100) or VARCHAR(255))
        return generate_password_hash(password)

    def check_password(self, password):
        """Verifies a plaintext password against the stored hash."""
        return check_password_hash(self.password_hash, password)

    # --- NEW METHOD FOR REGISTRATION ---
    @classmethod
    def create_user(cls, email, password, name):
        """Hashes password and inserts a new user record into the database."""
        conn = get_db_connection()
        if not conn: 
            return False, "Database connection failed."

        # 1. Hash the password
        password_hash = cls.set_password(password)

        try:
            cur = conn.cursor()
            # 2. Insert the new user data
            # RETURNING ID is used to immediately get the primary key for the new User object
            cur.execute(
                "INSERT INTO users (email, password_hash, name) VALUES (%s, %s, %s) RETURNING id",
                (email, password_hash, name)
            )
            user_id = cur.fetchone()[0] # Get the ID of the new user
            conn.commit()
            return True, User(id=user_id, email=email, password_hash=password_hash, name=name)
            
        except psycopg.errors.UniqueViolation:
            conn.rollback()
            return False, "User with that email already exists."
        
        except psycopg.errors.StringDataRightTruncation as e:
            conn.rollback()
            # This catches the "value too long for type character varying(150)" error
            return False, f"Registration failed: Input data too long for database. Please check NAME or PASSWORD length. Details: {e}" 
            
        except Exception as e:
            conn.rollback()
            return False, f"An unexpected error occurred during registration. Details: {e}"
            
        finally:
            if conn: conn.close()
    # -----------------------------------

    @classmethod
    def get_by_id(cls, user_id):
        conn = get_db_connection()
        if not conn: return None
        try:
            cur = conn.cursor()
            cur.execute("SELECT id, email, password_hash, name FROM users WHERE id = %s", (user_id,))
            user_data = cur.fetchone()
            return cls(*user_data) if user_data else None
        finally:
            if conn: conn.close()

    @classmethod
    def get_by_email(cls, email):
        conn = get_db_connection()
        if not conn: return None
        try:
            cur = conn.cursor()
            cur.execute("SELECT id, email, password_hash, name FROM users WHERE email = %s", (email,))
            user_data = cur.fetchone()
            return cls(*user_data) if user_data else None
        finally:
            if conn: conn.close()


# ----------------------------------------------------------------------
# 2. DEVICE MODEL (Updated for multi-user architecture)
# ----------------------------------------------------------------------

class Device:
    """Represents a record in the 'devices' table."""
    def __init__(self, id, device_name, unique_imei, imei_suffix=None):
        self.id = id
        self.device_name = device_name
        self.unique_imei = unique_imei
        # Calculate suffix if not passed (e.g., when fetched by IMEI)
        self.imei_suffix = imei_suffix if imei_suffix else unique_imei[-6:]
        
    @classmethod
    def get_user_devices(cls, user_id):
        """Retrieves all devices shared with a specific user."""
        conn = get_db_connection()
        if not conn: return []
        try:
            cur = conn.cursor()
            # JOIN to the device_shares table to only get devices linked to the user
            cur.execute("""
                SELECT 
                    d.id, d.device_name, d.unique_imei, RIGHT(d.unique_imei, 6) AS imei_suffix
                FROM devices d
                JOIN device_shares ds ON d.id = ds.device_id
                WHERE ds.user_id = %s 
                ORDER BY d.device_name
            """, (user_id,))
            devices_data = cur.fetchall()
            return [cls(*data) for data in devices_data]
        finally:
            if conn: conn.close()
            
    @classmethod
    def get_by_id_and_user(cls, device_id, user_id):
        """Retrieves a device ensuring it is shared with the given user."""
        conn = get_db_connection()
        if not conn: return None
        try:
            cur = conn.cursor()
            cur.execute("""
                SELECT 
                    d.id, d.device_name, d.unique_imei, RIGHT(d.unique_imei, 6)
                FROM devices d
                JOIN device_shares ds ON d.id = ds.device_id
                WHERE d.id = %s AND ds.user_id = %s
            """, (device_id, user_id))
            device_data = cur.fetchone()
            return cls(*device_data) if device_data else None
        finally:
            if conn: conn.close()

    @classmethod
    def get_by_imei(cls, imei):
        """Retrieves a device object by its unique 15-digit IMEI number."""
        conn = get_db_connection()
        if not conn: return None
        try:
            cur = conn.cursor()
            cur.execute(
                "SELECT id, device_name, unique_imei FROM devices WHERE unique_imei = %s",
                (imei,)
            )
            device_data = cur.fetchone()
            # If found, return the Device object
            return cls(device_data[0], device_data[1], device_data[2]) if device_data else None
        finally:
            if conn: conn.close()
            
    @classmethod
    def get_readings(cls, device_id, limit=50):
        """Retrieves historical readings for a specific device."""
        conn = get_db_connection()
        if not conn: return []
        try:
            cur = conn.cursor()
            cur.execute(
                """
                SELECT id, device_id, latitude, longitude, temperature, gsm_time, received_at
                FROM readings
                WHERE device_id = %s
                ORDER BY received_at DESC
                LIMIT %s
                """,
                (device_id, limit)
            )
            readings_data = cur.fetchall()
            return [Reading(*data) for data in readings_data]
        finally:
            if conn: conn.close()
            
# ----------------------------------------------------------------------
# 3. DEVICE SHARE MODEL (NEW)
# ----------------------------------------------------------------------

class DeviceShare:
    """Manages the relationship between a User and a Device."""
    
    @staticmethod
    def link_user_to_device(user_id, device_id):
        """Links a user to a device in the device_shares table."""
        conn = get_db_connection()
        if not conn: return False, "Database connection failed."
        cur = conn.cursor()
        try:
            cur.execute(
                "INSERT INTO device_shares (user_id, device_id) VALUES (%s, %s)",
                (user_id, device_id)
            )
            conn.commit()
            return True, "Device successfully linked."
        except psycopg.IntegrityError:
            # Handle the case where the link already exists (UNIQUE constraint failed)
            return True, "Device was already linked to this user."
        except Exception as e:
            conn.rollback()
            return False, f"Database error during linking: {e}"
        finally:
            if conn: conn.close()
            
# ----------------------------------------------------------------------
# 4. READING MODEL (Minor change for real-time API)
# ----------------------------------------------------------------------

class Reading:
    """Represents a record in the 'readings' table (GPS and Sensor data)."""
    def __init__(self, id, device_id, latitude, longitude, temperature, gsm_time, received_at):
        self.id = id
        self.device_id = device_id
        self.latitude = latitude
        self.longitude = longitude
        self.temperature = temperature
        self.gsm_time = gsm_time
        self.received_at = received_at
        
    @classmethod
    def get_latest_reading(cls, device_id):
        """Retrieves the most recent sensor reading for a specific device."""
        conn = get_db_connection()
        if not conn: return None
        try:
            cur = conn.cursor()
            cur.execute(
                """
                SELECT id, device_id, latitude, longitude, temperature, gsm_time, received_at 
                FROM readings 
                WHERE device_id = %s 
                ORDER BY received_at DESC 
                LIMIT 1
                """, 
                (device_id,)
            )
            reading_data = cur.fetchone()
            return cls(*reading_data) if reading_data else None
        finally:
            if conn: conn.close()

    @staticmethod
    def insert_reading(imei, lat, lon, temp):
        """Inserts a new sensor reading, finding the device by IMEI first."""
        conn = get_db_connection()
        if not conn: return False, "Database connection failed"
        cur = conn.cursor()
        
        try:
            # 1. Find the corresponding device_id using the unique IMEI
            cur.execute("SELECT id FROM devices WHERE unique_imei = %s", (imei,))
            device_id_result = cur.fetchone()
            
            if not device_id_result:
                return False, "Device not found"
                
            device_id = device_id_result[0]
            
            # 2. Insert the new reading. gsm_time is NULL as before.
            cur.execute(
                """
                INSERT INTO readings (device_id, latitude, longitude, temperature, gsm_time, received_at) 
                VALUES (%s, %s, %s, %s, NULL, NOW())
                """,
                (device_id, lat, lon, temp)
            )
            conn.commit()
            return True, "Reading saved"
            
        except Exception as e:
            conn.rollback()
            return False, f"Database error: {e}"
            
        finally:
            if conn:
                conn.close()