# app.py content (UPDATED for Cloud Deployment)

import os
from flask import Flask, render_template
import psycopg
from dotenv import load_dotenv
# REMOVED: import traceback - not needed for final code

# Load credentials from the .env file (for local testing)
load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv("FLASK_SECRET_KEY")

# --- Database Connection ---
def get_db_connection():
    """Establishes a connection using either DATABASE_URL or local .env credentials."""
    
    # 1. Prioritize the single DATABASE_URL environment variable (used by Render)
    db_url = os.getenv("DATABASE_URL")
    
    if db_url:
        conn_params = db_url
        print("Connecting using DATABASE_URL (Cloud Mode).")
    else:
        # 2. Fall back to local .env credentials (used for local development)
        print("Warning: Using local .env credentials (Local Mode).")
        conn_params = {
            "host": os.getenv("DB_HOST"),
            "dbname": os.getenv("DB_NAME"),
            "user": os.getenv("DB_USER"),
            "password": os.getenv("DB_PASSWORD")
        }

    try:
        # psycopg can accept a dictionary of parameters or a single URL string
        conn = psycopg.connect(conn_params)
        return conn
    except Exception as e:
        # We only print the error details here for simplicity
        print(f"Database connection failed: {e}")
        return None

# --- Application Route (Your Dashboard Page) ---
@app.route('/')
def dashboard():
    """The main dashboard view function."""
    
    # Default data for the template
    dashboard_data = {
        "project_name": "CoolMove Dashboard",
        "total_count": "N/A",
        "db_status": "Disconnected"
    }

    conn = get_db_connection()
    
    if conn:
        try:
            cursor = conn.cursor()
            
            # ⚠️ IMPORTANT: The query runs against your sensor data table.
            # Change 'users' to your final sensor data table name!
            cursor.execute("SELECT COUNT(*) FROM users;") 
            record_count = cursor.fetchone()[0]

            dashboard_data["total_count"] = record_count
            dashboard_data["db_status"] = "Connected"
            
            cursor.close()
            conn.close()

        except Exception as e:
            dashboard_data["db_status"] = f"Query Error: {e}"
    
    # Render the index.html template and pass the data dictionary
    return render_template('index.html', data=dashboard_data)

# --- Run the App ---
if __name__ == '__main__':
    # Use debug=True for local testing
    app.run(debug=True)