# FILE: web/models.py

import os
import psycopg
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash

# --- Database Connection Function ---
def get_db_connection():
    # Fetch the connection string from environment variables
    db_url = os.environ.get('DATABASE_URL')
    if not db_url:
        return None
        
    try:
        # Connect using the full connection string (URI)
        conn = psycopg.connect(conninfo=db_url)
        return conn
    except Exception as e:
        # Print error but return None so routes can handle failure gracefully
        print(f"DB Connection Error: {e}")
        return None

# ----------------------------------------------------------------------
# 1. USER MODEL
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
        return generate_password_hash(password)

    def check_password(self, password):
        """Verifies a plaintext password against the stored hash."""
        return check_password_hash(self.password_hash, password)

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
# 2. DEVICE MODEL
# ----------------------------------------------------------------------

class Device:
    """Represents a record in the 'devices' table."""
    def __init__(self, id, user_id, device_name, unique_imei, imei_suffix):
        self.id = id
        self.user_id = user_id
        self.device_name = device_name
        self.unique_imei = unique_imei
        self.imei_suffix = imei_suffix # The last 6 digits for display
        
    @classmethod
    def get_user_devices(cls, user_id):
        """Retrieves all tracking devices registered by a specific user."""
        conn = get_db_connection()
        if not conn: return []
        try:
            cur = conn.cursor()
            # SQL function RIGHT(string, length) extracts the suffix
            cur.execute("SELECT id, user_id, device_name, unique_imei, RIGHT(unique_imei, 6) AS imei_suffix FROM devices WHERE user_id = %s ORDER BY device_name", (user_id,))
            devices_data = cur.fetchall()
            return [cls(*data) for data in devices_data]
        finally:
            if conn: conn.close()
            
    @classmethod
    def get_by_id_and_user(cls, device_id, user_id):
        """Retrieves a device ensuring it belongs to the given user."""
        conn = get_db_connection()
        if not conn: return None
        try:
            cur = conn.cursor()
            cur.execute(
                "SELECT id, user_id, device_name, unique_imei, RIGHT(unique_imei, 6) FROM devices WHERE id = %s AND user_id = %s",
                (device_id, user_id)
            )
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
                "SELECT id, user_id, device_name, unique_imei, RIGHT(unique_imei, 6) FROM devices WHERE unique_imei = %s",
                (imei,)
            )
            device_data = cur.fetchone()
            return cls(*device_data) if device_data else None
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
# 3. READING MODEL (Data Layer)
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