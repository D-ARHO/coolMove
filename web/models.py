import os
import psycopg
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash

# --- Database Connection Function ---
# This is repeated here for modularity, making User methods self-contained.
def get_db_connection():
    # Fetch the connection string from environment variables
    db_url = os.environ.get('DATABASE_URL')
    if not db_url:
        # In a development environment, you might use a .env file or local default
        raise Exception("DATABASE_URL environment variable is not set.")
        
    # Connect using the full connection string (URI)
    conn = psycopg.connect(conninfo=db_url)
    return conn

# ----------------------------------------------------------------------
# 1. USER MODEL
# ----------------------------------------------------------------------

class User(UserMixin):
    """
    Represents a record in the 'users' table.
    Inherits from UserMixin for Flask-Login compatibility.
    """
    def __init__(self, id, email, password_hash, name):
        self.id = id
        self.email = email
        self.password_hash = password_hash
        self.name = name

    # Flask-Login Requirement: Returns the unique identifier for the user
    def get_id(self):
        return str(self.id)

    # Authentication Helpers
    @staticmethod
    def set_password(password):
        """Hashes a plaintext password for secure storage."""
        # Uses Werkzeug's secure hashing function
        return generate_password_hash(password)

    def check_password(self, password):
        """Verifies a plaintext password against the stored hash."""
        return check_password_hash(self.password_hash, password)

    # Data Retrieval Methods
    @classmethod
    def get_by_id(cls, user_id):
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("SELECT id, email, password_hash, name FROM users WHERE id = %s", (user_id,))
        user_data = cur.fetchone()
        conn.close()
        
        if user_data:
            return cls(*user_data)
        return None

    @classmethod
    def get_by_email(cls, email):
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("SELECT id, email, password_hash, name FROM users WHERE email = %s", (email,))
        user_data = cur.fetchone()
        conn.close()
        
        if user_data:
            return cls(*user_data)
        return None


# ----------------------------------------------------------------------
# 2. DEVICE MODEL
# ----------------------------------------------------------------------

class Device:
    """
    Represents a record in the 'devices' table.
    """
    def __init__(self, id, user_id, device_name, unique_imei):
        self.id = id
        self.user_id = user_id
        self.device_name = device_name
        self.unique_imei = unique_imei
        
    @classmethod
    def get_user_devices(cls, user_id):
        """Retrieves all tracking devices registered by a specific user."""
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("SELECT id, user_id, device_name, unique_imei FROM devices WHERE user_id = %s ORDER BY device_name", (user_id,))
        devices_data = cur.fetchall()
        conn.close()
        
        # Create a list of Device objects
        return [cls(*data) for data in devices_data]
        
# ----------------------------------------------------------------------
# 3. READING MODEL (Data Layer)
# ----------------------------------------------------------------------

class Reading:
    """
    Represents a record in the 'readings' table (GPS and Sensor data).
    """
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
        cur = conn.cursor()
        cur.execute(
            """
            SELECT id, device_id, latitude, longitude, temperature, gsm_time, received_at 
            FROM readings 
            WHERE device_id = %s 
            ORDER BY gsm_time DESC 
            LIMIT 1
            """, 
            (device_id,)
        )
        reading_data = cur.fetchone()
        conn.close()
        
        if reading_data:
            return cls(*reading_data)
        return None