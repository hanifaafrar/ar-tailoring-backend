import os
from flask import Flask, render_template, request, redirect, url_for, session, jsonify, flash
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
import secrets
from supabase import create_client, Client

app = Flask(__name__)

# Configuration - using environment variables with fallback defaults
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', secrets.token_hex(32))

# Supabase Configuration
SUPABASE_URL = os.environ.get('SUPABASE_URL', 'https://supabase.com/dashboard/project/wjbmphqqlztzndzaprdq')
SUPABASE_KEY = os.environ.get('SUPABASE_KEY', 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6IndqYm1waHFxbHp0em5kemFwcmRxIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NTM4MDgyMjksImV4cCI6MjA2OTM4NDIyOX0.DnpnmZiXFtzFaEwTVTxgNc5ICx2sVb7XXnIez8TEXls')

# Initialize Supabase client
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

# User Model for Flask-Login
class User(UserMixin):
    def __init__(self, user_data):
        self.id = user_data['id']
        self.username = user_data['username']
        self.email = user_data['email']
        self.first_name = user_data['first_name']
        self.last_name = user_data['last_name']
        self.mobile_number = user_data['mobile_number']
        self.national_id = user_data['national_id']
        self.created_at = user_data['created_at']
        self.is_admin = user_data.get('is_admin', False)

@login_manager.user_loader
def load_user(user_id):
    try:
        # Fetch user from Supabase
        response = supabase.table('users').select('*').eq('id', user_id).execute()
        if response.data:
            return User(response.data[0])
    except Exception as e:
        print(f"Error loading user: {e}")
    return None

# Routes
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        # Get form data
        username = request.form['username']
        email = request.form['email']
        first_name = request.form['first_name']
        last_name = request.form['last_name']
        password = request.form['password']
        mobile_number = request.form['mobile_number']
        national_id = request.form['national_id']
        
        try:
            # Check if user already exists
            existing_user = supabase.table('users').select('*').eq('email', email).execute()
            if existing_user.data:
                flash('Email already exists')
                return redirect(url_for('register'))
            
            # Check if username already exists
            existing_username = supabase.table('users').select('*').eq('username', username).execute()
            if existing_username.data:
                flash('Username already exists')
                return redirect(url_for('register'))
            
            # Check if national ID already exists
            existing_national_id = supabase.table('users').select('*').eq('national_id', national_id).execute()
            if existing_national_id.data:
                flash('National ID already exists')
                return redirect(url_for('register'))
            
            # Create new user
            user_data = {
                'username': username,
                'email': email,
                'first_name': first_name,
                'last_name': last_name,
                'password_hash': generate_password_hash(password),
                'mobile_number': mobile_number,
                'national_id': national_id,
                'created_at': datetime.utcnow().isoformat(),
                'is_admin': False
            }
            
            # Insert user into Supabase
            response = supabase.table('users').insert(user_data).execute()
            
            if response.data:
                # Login the user
                user = User(response.data[0])
                login_user(user)
                flash('Registration successful!')
                return redirect(url_for('index'))
            else:
                flash('Registration failed. Please try again.')
                
        except Exception as e:
            print(f"Registration error: {e}")
            flash('An error occurred during registration. Please try again.')
    
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        
        try:
            # Fetch user from Supabase
            response = supabase.table('users').select('*').eq('email', email).execute()
            
            if response.data:
                user_data = response.data[0]
                if check_password_hash(user_data['password_hash'], password):
                    user = User(user_data)
                    login_user(user)
                    
                    # Log login activity
                    login_log = {
                        'user_id': user_data['id'],
                        'login_time': datetime.utcnow().isoformat(),
                        'ip_address': request.remote_addr,
                        'user_agent': request.headers.get('User-Agent')
                    }
                    supabase.table('user_login_logs').insert(login_log).execute()
                    
                    return redirect(url_for('index'))
                else:
                    flash('Invalid email or password')
            else:
                flash('Invalid email or password')
                
        except Exception as e:
            print(f"Login error: {e}")
            flash('An error occurred during login. Please try again.')
    
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    try:
        # Log logout activity
        logout_log = {
            'user_id': current_user.id,
            'logout_time': datetime.utcnow().isoformat(),
            'ip_address': request.remote_addr
        }
        supabase.table('user_logout_logs').insert(logout_log).execute()
    except Exception as e:
        print(f"Logout logging error: {e}")
    
    logout_user()
    return redirect(url_for('index'))

@app.route('/profile')
@login_required
def profile():
    return render_template('profile.html', user=current_user)

@app.route('/update_profile', methods=['POST'])
@login_required
def update_profile():
    try:
        # Get form data
        first_name = request.form['first_name']
        last_name = request.form['last_name']
        mobile_number = request.form['mobile_number']
        
        # Update user in Supabase
        update_data = {
            'first_name': first_name,
            'last_name': last_name,
            'mobile_number': mobile_number,
            'updated_at': datetime.utcnow().isoformat()
        }
        
        response = supabase.table('users').update(update_data).eq('id', current_user.id).execute()
        
        if response.data:
            flash('Profile updated successfully!')
        else:
            flash('Failed to update profile. Please try again.')
            
    except Exception as e:
        print(f"Profile update error: {e}")
        flash('An error occurred while updating profile.')
    
    return redirect(url_for('profile'))

# Admin Routes
@app.route('/admin')
@login_required
def admin_dashboard():
    if not current_user.is_admin:
        flash('Access denied. Admin privileges required.')
        return redirect(url_for('index'))
    
    try:
        # Get user statistics
        total_users = supabase.table('users').select('id', count='exact').execute()
        recent_registrations = supabase.table('users').select('*').order('created_at', desc=True).limit(10).execute()
        recent_logins = supabase.table('user_login_logs').select('*, users(username, email)').order('login_time', desc=True).limit(20).execute()
        
        return render_template('admin_dashboard.html', 
                             total_users=total_users.count,
                             recent_registrations=recent_registrations.data,
                             recent_logins=recent_logins.data)
    except Exception as e:
        print(f"Admin dashboard error: {e}")
        flash('Error loading admin dashboard.')
        return redirect(url_for('index'))

@app.route('/admin/users')
@login_required
def admin_users():
    if not current_user.is_admin:
        flash('Access denied. Admin privileges required.')
        return redirect(url_for('index'))
    
    try:
        # Get all users with pagination
        page = request.args.get('page', 1, type=int)
        per_page = 20
        offset = (page - 1) * per_page
        
        users = supabase.table('users').select('*').order('created_at', desc=True).range(offset, offset + per_page - 1).execute()
        
        return render_template('admin_users.html', users=users.data, page=page)
    except Exception as e:
        print(f"Admin users error: {e}")
        flash('Error loading users list.')
        return redirect(url_for('admin_dashboard'))

@app.route('/admin/user/<int:user_id>')
@login_required
def admin_user_details(user_id):
    if not current_user.is_admin:
        flash('Access denied. Admin privileges required.')
        return redirect(url_for('index'))
    
    try:
        # Get user details
        user = supabase.table('users').select('*').eq('id', user_id).execute()
        if not user.data:
            flash('User not found.')
            return redirect(url_for('admin_users'))
        
        # Get user login history
        login_history = supabase.table('user_login_logs').select('*').eq('user_id', user_id).order('login_time', desc=True).limit(50).execute()
        
        return render_template('admin_user_details.html', 
                             user=user.data[0], 
                             login_history=login_history.data)
    except Exception as e:
        print(f"Admin user details error: {e}")
        flash('Error loading user details.')
        return redirect(url_for('admin_users'))

@app.route('/admin/toggle_user_status/<int:user_id>', methods=['POST'])
@login_required
def toggle_user_status(user_id):
    if not current_user.is_admin:
        return jsonify({'success': False, 'message': 'Access denied'})
    
    try:
        # Get current user status
        user = supabase.table('users').select('is_active').eq('id', user_id).execute()
        if not user.data:
            return jsonify({'success': False, 'message': 'User not found'})
        
        # Toggle status
        new_status = not user.data[0].get('is_active', True)
        response = supabase.table('users').update({'is_active': new_status}).eq('id', user_id).execute()
        
        if response.data:
            return jsonify({'success': True, 'new_status': new_status})
        else:
            return jsonify({'success': False, 'message': 'Failed to update user status'})
            
    except Exception as e:
        print(f"Toggle user status error: {e}")
        return jsonify({'success': False, 'message': 'An error occurred'})

def init_supabase_tables():
    """Initialize Supabase tables - Run these SQL commands in Supabase SQL editor"""
    sql_commands = """
    -- Users table
    CREATE TABLE IF NOT EXISTS users (
        id SERIAL PRIMARY KEY,
        username VARCHAR(80) UNIQUE NOT NULL,
        email VARCHAR(120) UNIQUE NOT NULL,
        first_name VARCHAR(50) NOT NULL,
        last_name VARCHAR(50) NOT NULL,
        password_hash VARCHAR(128) NOT NULL,
        mobile_number VARCHAR(20) NOT NULL,
        national_id VARCHAR(20) UNIQUE NOT NULL,
        is_admin BOOLEAN DEFAULT FALSE,
        is_active BOOLEAN DEFAULT TRUE,
        created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
        updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
    );

    -- User login logs table
    CREATE TABLE IF NOT EXISTS user_login_logs (
        id SERIAL PRIMARY KEY,
        user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
        login_time TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
        ip_address INET,
        user_agent TEXT
    );

    -- User logout logs table
    CREATE TABLE IF NOT EXISTS user_logout_logs (
        id SERIAL PRIMARY KEY,
        user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
        logout_time TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
        ip_address INET
    );

    -- Create indexes for better performance
    CREATE INDEX IF NOT EXISTS idx_users_email ON users(email);
    CREATE INDEX IF NOT EXISTS idx_users_username ON users(username);
    CREATE INDEX IF NOT EXISTS idx_users_national_id ON users(national_id);
    CREATE INDEX IF NOT EXISTS idx_login_logs_user_id ON user_login_logs(user_id);
    CREATE INDEX IF NOT EXISTS idx_login_logs_time ON user_login_logs(login_time);
    CREATE INDEX IF NOT EXISTS idx_logout_logs_user_id ON user_logout_logs(user_id);
    """
    print("Run these SQL commands in your Supabase SQL editor:")
    print(sql_commands)

if __name__ == '__main__':
    print("Setting up Supabase tables...")
    init_supabase_tables()
    app.run(host='127.0.0.1', port=5000, debug=True)
