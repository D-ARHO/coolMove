# FILE: web/app.py

import os
import json # Added for JSON dump in device_history
from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, abort
import psycopg
from dotenv import load_dotenv
from flask_login import (
    LoginManager, 
    login_user, 
    login_required, 
    logout_user, 
    current_user
)

# Relative import from models.py
from .models import User, Device, Reading, get_db_connection 

# Load credentials from the .env file (for local testing)
load_dotenv()

app = Flask(__name__)
# IMPORTANT: Use FLASK_SECRET_KEY for sessions and CSRF protection
app.config['SECRET_KEY'] = os.environ.get('FLASK_SECRET_KEY', 'a-very-secret-default-key') 

# --- FLASK-LOGIN SETUP ---
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login' 
login_manager.login_message = 'Please log in to access this page.'

# --- USER LOADER (REQUIRED BY FLASK-LOGIN) ---
@login_manager.user_loader
def load_user(user_id):
    """Callback function to reload the user object from the user ID stored in the session."""
    return User.get_by_id(user_id) 

# ----------------------------------------------------------------------
# 1. AUTHENTICATION ROUTES
# ----------------------------------------------------------------------

# --- Registration Route ---
@app.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))

    if request.method == 'POST':
        email = request.form.get('email')
        name = request.form.get('name')
        password = request.form.get('password')
        
        if User.get_by_email(email):
            flash('A user with that email already exists.', 'warning')
            return redirect(url_for('register'))

        password_hash = User.set_password(password)

        conn = get_db_connection()
        if not conn:
            flash('Database connection failed.', 'error')
            return redirect(url_for('register'))
            
        cur = conn.cursor()
        try:
            cur.execute(
                "INSERT INTO users (email, name, password_hash) VALUES (%s, %s, %s) RETURNING id",
                (email, name, password_hash)
            )
            new_user_id = cur.fetchone()[0]
            conn.commit()
            
            new_user = User(new_user_id, email, password_hash, name)
            login_user(new_user)
            flash('Registration successful! Welcome to CoolMove.', 'success')
            return redirect(url_for('dashboard'))
        except Exception as e:
            conn.rollback()
            flash(f'An error occurred during registration. Details: {e}', 'error')
        finally:
            if conn: conn.close()

    return render_template('register.html')

# --- Login Route (Main Landing Page) ---
@app.route('/', methods=['GET', 'POST'])
@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))

    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        
        user = User.get_by_email(email)
        
        if user and user.check_password(password):
            login_user(user) 
            flash('Login successful.', 'success')
            
            next_page = request.args.get('next')
            return redirect(next_page or url_for('dashboard'))
            
        flash('Invalid email or password.', 'error')
        
    return render_template('login.html')

# --- Logout Route ---
@app.route('/logout')
@login_required 
def logout():
    logout_user() 
    flash('You have been logged out.', 'info')
    return redirect(url_for('login'))


# ----------------------------------------------------------------------
# 2. PROTECTED DASHBOARD AND DEVICE MANAGEMENT ROUTES
# ----------------------------------------------------------------------

# --- Main Dashboard (Protected) ---
@app.route('/dashboard')
@login_required 
def dashboard():
    devices = Device.get_user_devices(current_user.id)
    
    device_data = []
    for device in devices:
        latest_reading = Reading.get_latest_reading(device.id)
        
        device_dict = device.__dict__.copy() # Use copy to avoid modifying the model object
        device_dict['latest_reading'] = latest_reading
        
        device_data.append(device_dict)

    return render_template('dashboard.html', devices=device_data, user=current_user)


# --- Device Detail/History Route (New) ---
@app.route('/device/<int:device_id>')
@login_required
def device_history(device_id):
    # Retrieve the device details
    device = Device.get_by_id_and_user(device_id, current_user.id)
    if not device:
        flash("Device not found or you do not have permission to view it.", 'error')
        return redirect(url_for('dashboard'))
    
    # Fetch the historical readings (last 50 points)
    readings = Device.get_readings(device_id, limit=50) 
    
    # Reverse the order so Leaflet draws the route correctly (oldest to newest)
    readings.reverse() 
    
    # Create a list of dictionaries for easy JSON conversion for the map script
    route_data = [
        {'lat': r.latitude, 'lon': r.longitude, 'temp': r.temperature, 'time': r.received_at.strftime('%Y-%m-%d %H:%M:%S')}
        for r in readings
    ]
    
    # Pass the data as a JSON string for the JavaScript side
    route_data_json = json.dumps(route_data)

    return render_template('device_history.html', 
                           device=device,
                           route_data_json=route_data_json)


# --- Device Management Route ---
@app.route('/devices/add', methods=['GET', 'POST'])
@login_required
def add_device():
    if request.method == 'POST':
        device_name = request.form.get('device_name')
        # Use the full IMEI (15 digits)
        full_imei = request.form.get('unique_imei') 
        user_id = current_user.id
        
        # 1. Basic validation 
        if not device_name or not full_imei or len(full_imei) != 15 or not full_imei.isdigit():
            flash('Invalid device name or IMEI format. IMEI must be 15 digits.', 'error')
            return render_template('add_device.html')

        # 2. Check for IMEI uniqueness
        if Device.get_by_imei(full_imei):
            flash(f'The IMEI suffix **{full_imei[-6:]}** is already registered.', 'warning')
            return render_template('add_device.html')

        conn = get_db_connection()
        if not conn:
             flash('Database connection failed.', 'error')
             return render_template('add_device.html')
             
        cur = conn.cursor()
        try:
            # 3. Insert the new device, linking it to the current user
            cur.execute(
                "INSERT INTO devices (user_id, device_name, unique_imei) VALUES (%s, %s, %s)",
                (user_id, device_name, full_imei)
            )
            conn.commit()
            
            flash(f'Device "{device_name}" successfully registered!', 'success')
            return redirect(url_for('dashboard'))
            
        except Exception as e:
            conn.rollback()
            flash(f'Database error during device registration: {e}', 'error')
        finally:
            if conn: conn.close()

    return render_template('add_device.html')


# ----------------------------------------------------------------------
# 3. DEVICE API ROUTE (Receives Data from Firmware - NO LOGIN REQUIRED)
# ----------------------------------------------------------------------

@app.route('/api/data', methods=['POST'])
def receive_data():
    if not request.is_json:
        return jsonify({"message": "Expected JSON payload"}), 415

    data = request.get_json()
    
    # 1. Basic validation and extraction
    try:
        imei = data['imei']
        lat = float(data['lat'])
        lon = float(data['lon'])
        temp = float(data['temp'])
    except (KeyError, ValueError):
        return jsonify({"message": "Invalid or missing data fields (imei, lat, lon, temp)"}), 400

    # 2. Securely insert data using the IMEI
    success, message = Reading.insert_reading(imei, lat, lon, temp)

    if success:
        return jsonify({"message": "Data recorded successfully"}), 200
    else:
        status_code = 404 if "Device not found" in message else 500
        return jsonify({"message": message}), status_code


# --- Run the App ---
if __name__ == '__main__':
    # Logic to handle local environment variables if DATABASE_URL is not explicitly set
    if os.environ.get('DATABASE_URL') is None:
        try:
            db_url = f"postgresql://{os.environ.get('DB_USER')}:{os.environ.get('DB_PASSWORD')}@{os.environ.get('DB_HOST')}/{os.environ.get('DB_NAME')}"
            os.environ['DATABASE_URL'] = db_url
        except TypeError:
            print("Warning: Missing required DB environment variables in .env file.")
        
    if not app.config['SECRET_KEY']:
        print("FATAL: FLASK_SECRET_KEY is not set. Cannot run securely.")
        
    app.run(debug=True)