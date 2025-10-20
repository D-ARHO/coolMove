# FILE: web/app.py

import os
import json 
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
# ADDED DeviceShare
from models import User, Device, Reading, DeviceShare, get_db_connection 

load_dotenv()

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('FLASK_SECRET_KEY', 'a-very-secret-default-key') 

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login' 
login_manager.login_message = 'Please log in to access this page.'

# --- USER LOADER ---
@login_manager.user_loader
def load_user(user_id):
    return User.get_by_id(user_id) 

# ----------------------------------------------------------------------
# 1. NEW PUBLIC/STATIC ROUTES
# ----------------------------------------------------------------------

# --- About Page (NEW) ---
@app.route('/about')
def about():
    return render_template('about.html')

# --- Services Page (NEW) ---
@app.route('/services')
def services():
    return render_template('services.html')

# ----------------------------------------------------------------------
# 2. AUTHENTICATION ROUTES (No significant changes)
# ----------------------------------------------------------------------

@app.route('/register', methods=['GET', 'POST'])
def register():
    # ... (Registration logic remains the same) ...
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
            flash('Registration successful! Welcome to Kold.', 'success')
            return redirect(url_for('dashboard'))
        except Exception as e:
            conn.rollback()
            flash(f'An error occurred during registration. Details: {e}', 'error')
        finally:
            if conn: conn.close()

    return render_template('register.html')

@app.route('/', methods=['GET', 'POST'])
@app.route('/login', methods=['GET', 'POST'])
def login():
    # ... (Login logic remains the same) ...
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

@app.route('/logout')
@login_required 
def logout():
    # ... (Logout logic remains the same) ...
    logout_user() 
    flash('You have been logged out.', 'info')
    return redirect(url_for('login'))


# ----------------------------------------------------------------------
# 3. PROTECTED DASHBOARD AND DEVICE MANAGEMENT ROUTES (Updated)
# ----------------------------------------------------------------------

# --- Main Dashboard (Protected) ---
@app.route('/dashboard')
@login_required 
def dashboard():
    devices = Device.get_user_devices(current_user.id)
    
    # We now fetch latest reading data via the new API endpoint in the template
    # This keeps the initial page load fast.
    return render_template('dashboard.html', devices=devices, user=current_user)

# --- Device Detail/History Route (Map Functionality) ---
@app.route('/device/<int:device_id>')
@login_required
def device_history(device_id):
    device = Device.get_by_id_and_user(device_id, current_user.id)
    if not device:
        flash("Device not found or you do not have permission to view it.", 'error')
        return redirect(url_for('dashboard'))
    
    readings = Device.get_readings(device_id, limit=50) 
    readings.reverse() # Oldest to newest for correct route drawing
    
    route_data = [
        {'lat': r.latitude, 'lon': r.longitude, 'temp': r.temperature, 'time': r.received_at.strftime('%Y-%m-%d %H:%M:%S')}
        for r in readings
    ]
    
    route_data_json = json.dumps(route_data)

    return render_template('device_history.html', 
                            device=device,
                            route_data_json=route_data_json)


# --- Device Management Route (Updated to handle DeviceShare) ---
@app.route('/devices/add', methods=['GET', 'POST'])
@login_required
def add_device():
    if request.method == 'POST':
        device_name = request.form.get('device_name')
        full_imei = request.form.get('unique_imei') 
        user_id = current_user.id
        
        # 1. Basic validation 
        if not device_name or not full_imei or len(full_imei) != 15 or not full_imei.isdigit():
            flash('Invalid device name or IMEI format. IMEI must be 15 digits.', 'error')
            return render_template('add_device.html')

        # 2. Check if device already exists in the 'devices' table
        device = Device.get_by_imei(full_imei)
        
        # --- Transaction START ---
        conn = get_db_connection()
        if not conn:
            flash('Database connection failed.', 'error')
            return render_template('add_device.html')
        cur = conn.cursor()
        
        try:
            # A. If device IMEI is new, create the device first.
            if not device:
                cur.execute(
                    "INSERT INTO devices (device_name, unique_imei) VALUES (%s, %s) RETURNING id",
                    (device_name, full_imei)
                )
                device_id = cur.fetchone()[0]
                conn.commit() # Commit the new device creation
                
                # Re-fetch the device object (or just use the data)
                device = Device(device_id, device_name, full_imei)

                flash_message = f'New Device "{device_name}" successfully registered!'
                
            # B. If device IMEI already exists, use its ID.
            else:
                # Update the name in case the original registering user made a typo/wanted to change it
                cur.execute(
                    "UPDATE devices SET device_name = %s WHERE id = %s",
                    (device_name, device.id)
                )
                device_id = device.id
                conn.commit()

                flash_message = f'Device "{device_name}" (IMEI {device.imei_suffix}) was already registered by someone else. You have now been linked to it.'

            # 3. Link the current user to the device (DeviceShare)
            success, link_message = DeviceShare.link_user_to_device(user_id, device_id)
            
            if success:
                flash(flash_message, 'success')
            else:
                flash(f'Device registered, but linking failed: {link_message}', 'warning')
                
            return redirect(url_for('dashboard'))
            
        except Exception as e:
            conn.rollback()
            flash(f'Database error during device linking: {e}', 'error')
        finally:
            if conn: conn.close()

    return render_template('add_device.html')


# ----------------------------------------------------------------------
# 4. API ROUTES
# ----------------------------------------------------------------------

# --- API for Real-Time Dashboard Refresh (NEW) ---
@app.route('/api/latest/<int:device_id>')
@login_required # Protects the real-time API endpoint
def api_latest_reading(device_id):
    # 1. Ensure the device is linked to the current user
    device = Device.get_by_id_and_user(device_id, current_user.id)
    if not device:
        return jsonify({"error": "Device not authorized"}), 403

    # 2. Fetch the latest reading
    reading = Reading.get_latest_reading(device_id)

    if reading:
        data = {
            'temp': round(reading.temperature, 1),
            'lat': reading.latitude,
            'lon': reading.longitude,
            'time': reading.received_at.strftime('%Y-%m-%d %H:%M:%S'),
            'status': 'OK'
        }
        return jsonify(data), 200
    else:
        return jsonify({"status": "NoData", "message": "No readings found for this device"}), 200


# --- API for Firmware Data (No Login Required) ---
@app.route('/api/data', methods=['POST'])
def receive_data():
    # ... (Data receiving logic remains the same) ...
    if not request.is_json:
        return jsonify({"message": "Expected JSON payload"}), 415

    data = request.get_json()
    
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
    # ... (App run logic remains the same) ...
    if os.environ.get('DATABASE_URL') is None:
        try:
            db_url = f"postgresql://{os.environ.get('DB_USER')}:{os.environ.get('DB_PASSWORD')}@{os.environ.get('DB_HOST')}/{os.environ.get('DB_NAME')}"
            os.environ['DATABASE_URL'] = db_url
        except TypeError:
            print("Warning: Missing required DB environment variables in .env file.")
        
    if not app.config['SECRET_KEY']:
        print("FATAL: FLASK_SECRET_KEY is not set. Cannot run securely.")
        
    app.run(debug=True)