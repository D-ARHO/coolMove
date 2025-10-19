import os
from flask import Flask, render_template, request, redirect, url_for, flash
import psycopg
from dotenv import load_dotenv
from werkzeug.security import generate_password_hash # Kept in case of direct use, though model uses it
from flask_login import (
    LoginManager, 
    login_user, 
    login_required, 
    logout_user, 
    current_user
)

# IMPORT THE NEW DATABASE MODELS AND CONNECTION FUNCTION
from .models import User, Device, get_db_connection

# Load credentials from the .env file (for local testing)
load_dotenv()

app = Flask(__name__)
# IMPORTANT: Use FLASK_SECRET_KEY for sessions and CSRF protection (Flask-WTF dependency)
app.config['SECRET_KEY'] = os.environ.get('FLASK_SECRET_KEY', 'a-very-secret-default-key') 

# --- FLASK-LOGIN SETUP ---
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login' # Function name for the login route
login_manager.login_message = 'Please log in to access this page.'

# --- USER LOADER (REQUIRED BY FLASK-LOGIN) ---
@login_manager.user_loader
def load_user(user_id):
    """Callback function to reload the user object from the user ID stored in the session."""
    conn = get_db_connection()
    if not conn:
        return None
        
    cur = conn.cursor()
    try:
        cur.execute("SELECT id, email, password_hash, name FROM users WHERE id = %s", (user_id,))
        user_data = cur.fetchone()
        
        if user_data:
            # Create a User object from the database record
            return User(*user_data) 
    except Exception as e:
        print(f"Error loading user: {e}")
    finally:
        if conn:
            conn.close()
    return None

# ----------------------------------------------------------------------
# 1. AUTHENTICATION ROUTES
# ----------------------------------------------------------------------

# --- Registration Route ---
@app.route('/register', methods=['GET', 'POST'])
def register():
    # If the user is already logged in, redirect them to the dashboard
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))

    if request.method == 'POST':
        email = request.form.get('email')
        name = request.form.get('name')
        password = request.form.get('password')
        
        # 1. Check if user already exists
        if User.get_by_email(email):
            flash('A user with that email already exists.', 'warning')
            return redirect(url_for('register'))

        # 2. Hash the password
        password_hash = User.set_password(password)

        # 3. Insert new user into the database
        conn = get_db_connection()
        if not conn:
            flash('Database connection failed.', 'error')
            return redirect(url_for('register'))
            
        cur = conn.cursor()
        try:
            # Use RETURNING id to immediately get the primary key of the new record
            cur.execute(
                "INSERT INTO users (email, name, password_hash) VALUES (%s, %s, %s) RETURNING id",
                (email, name, password_hash)
            )
            new_user_id = cur.fetchone()[0]
            conn.commit()
            
            # Log the new user in immediately
            new_user = User(new_user_id, email, password_hash, name)
            login_user(new_user)
            flash('Registration successful! Welcome to CoolMove.', 'success')
            return redirect(url_for('dashboard'))
        except Exception as e:
            conn.rollback()
            flash(f'An error occurred during registration. Details: {e}', 'error')
        finally:
            conn.close()

    return render_template('register.html')

# --- Login Route (Main Landing Page) ---
@app.route('/', methods=['GET', 'POST'])
@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        # If logged in, redirect to the main protected dashboard
        return redirect(url_for('dashboard'))

    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        
        # 1. Attempt to get user by email
        user = User.get_by_email(email)
        
        # 2. Check if user exists AND password is correct
        if user and user.check_password(password):
            login_user(user) # Start the session
            flash('Login successful.', 'success')
            
            # Flask-Login stores the URL the user tried to access in 'next'
            next_page = request.args.get('next')
            return redirect(next_page or url_for('dashboard'))
            
        flash('Invalid email or password.', 'error')
        
    return render_template('login.html')

# --- Logout Route ---
@app.route('/logout')
@login_required 
def logout():
    logout_user() # End the user session
    flash('You have been logged out.', 'info')
    return redirect(url_for('login'))


# ----------------------------------------------------------------------
# 2. PROTECTED DASHBOARD AND DEVICE MANAGEMENT ROUTES
# ----------------------------------------------------------------------

# --- Main Dashboard (Protected) ---
@app.route('/dashboard')
@login_required # ONLY LOGGED-IN USERS CAN ACCESS THIS
def dashboard():
    # 1. Fetch devices belonging to the logged-in user
    devices = Device.get_user_devices(current_user.id)
    
    # You will eventually include logic here to:
    # - Get the latest readings for each device
    # - Determine high-temperature status
    # - Prepare data for mapping
    
    return render_template('dashboard.html', devices=devices, user=current_user)


# --- Device Management Placeholder (Future Feature) ---
@app.route('/devices/add', methods=['GET', 'POST'])
@login_required
def add_device():
    # Placeholder for the logic to register a new device to the user's account
    flash('Device addition feature coming soon!', 'info')
    return redirect(url_for('dashboard'))


# --- Run the App ---
if __name__ == '__main__':
    # Ensure you have a SECRET_KEY set in your .env for local testing
    if not app.config['SECRET_KEY']:
        print("FATAL: FLASK_SECRET_KEY is not set. Cannot run securely.")
    app.run(debug=True)