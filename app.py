import json
import os
from datetime import datetime
from flask import Flask, render_template, request, redirect, url_for, session, flash
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.secret_key = 'dev-key-change-in-production'

USERS_FILE = 'users.json'
COMPLAINTS_FILE = 'complaints.json'

def load_users():
    # If file doesn't exist, create with default admin
    if not os.path.exists(USERS_FILE):
        default_users = [
            {
                'id': 1,
                'name': 'Admin',
                'email': 'admin@hostel.com',
                'password': generate_password_hash('admin123'),
                'role': 'admin',
                'hostelBlock': '',
                'roomNumber': ''
            }
        ]
        save_users(default_users)
        return default_users

    # If file exists, try to read it
    try:
        with open(USERS_FILE, 'r') as f:
            data = json.load(f)
            # Ensure it's a list
            if not isinstance(data, list):
                raise ValueError("users.json is not a list")
            return data
    except (json.JSONDecodeError, ValueError):
        # File is empty or corrupt – recreate with default admin
        print("users.json is empty or corrupt. Recreating...")
        default_users = [
            {
                'id': 1,
                'name': 'Admin',
                'email': 'admin@hostel.com',
                'password': generate_password_hash('admin123'),
                'role': 'admin',
                'hostelBlock': '',
                'roomNumber': ''
            }
        ]
        save_users(default_users)
        return default_users

def save_users(users):
    with open(USERS_FILE, 'w') as f:
        json.dump(users, f, indent=2)

def load_complaints():
    if not os.path.exists(COMPLAINTS_FILE):
        return []
    try:
        with open(COMPLAINTS_FILE, 'r') as f:
            data = json.load(f)
            if not isinstance(data, list):
                return []
            return data
    except json.JSONDecodeError:
        # File is empty or corrupt – start fresh
        return []

def save_complaints(complaints):
    with open(COMPLAINTS_FILE, 'w') as f:
        json.dump(complaints, f, indent=2)

def get_next_id(items):
    if not items:
        return 1
    return max(item['id'] for item in items) + 1

@app.route('/')
def index():
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        users = load_users()
        user = next((u for u in users if u['email'] == email), None)
        if user and check_password_hash(user['password'], password):
            session['user_id'] = user['id']
            session['role'] = user['role']
            if user['role'] == 'admin':
                return redirect(url_for('admin'))
            else:
                return redirect(url_for('student'))
        else:
            flash('Invalid credentials')
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        name = request.form['name']
        email = request.form['email']
        password = request.form['password']
        hostelBlock = request.form['hostelBlock']
        roomNumber = request.form['roomNumber']
        users = load_users()
        if any(u['email'] == email for u in users):
            flash('Email already registered')
            return redirect(url_for('register'))
        new_user = {
            'id': get_next_id(users),
            'name': name,
            'email': email,
            'password': generate_password_hash(password),
            'role': 'student',
            'hostelBlock': hostelBlock,
            'roomNumber': roomNumber
        }
        users.append(new_user)
        save_users(users)
        # auto login after registration
        session['user_id'] = new_user['id']
        session['role'] = 'student'
        return redirect(url_for('student'))
    return render_template('register.html')

@app.route('/student', methods=['GET'])
def student():
    if 'user_id' not in session or session['role'] != 'student':
        return redirect(url_for('login'))
    user_id = session['user_id']
    complaints = load_complaints()
    my_complaints = [c for c in complaints if c['studentId'] == user_id]
    my_complaints.sort(key=lambda x: x['createdAt'], reverse=True)
    return render_template('student.html', complaints=my_complaints)

@app.route('/student/complaint', methods=['POST'])
def add_complaint():
    if 'user_id' not in session or session['role'] != 'student':
        return redirect(url_for('login'))
    title = request.form['title']
    description = request.form['description']
    category = request.form['category']
    priority = request.form['priority']
    complaints = load_complaints()
    new_complaint = {
        'id': get_next_id(complaints),
        'studentId': session['user_id'],
        'title': title,
        'description': description,
        'category': category,
        'priority': priority,
        'status': 'Pending',
        'adminComment': '',
        'createdAt': datetime.now().isoformat()
    }
    complaints.append(new_complaint)
    save_complaints(complaints)
    return redirect(url_for('student'))

@app.route('/admin')
def admin():
    if 'user_id' not in session or session['role'] != 'admin':
        return redirect(url_for('login'))
    complaints = load_complaints()
    users = load_users()
    user_map = {u['id']: u for u in users}
    enriched = []
    for c in complaints:
        student = user_map.get(c['studentId'], {})
        enriched.append({
            **c,
            'studentName': student.get('name', 'Unknown'),
            'studentRoom': student.get('roomNumber', 'Unknown')
        })
    enriched.sort(key=lambda x: x['createdAt'], reverse=True)
    return render_template('admin.html', complaints=enriched)

@app.route('/admin/complaint/<int:id>', methods=['GET', 'POST'])
def edit_complaint(id):
    if 'user_id' not in session or session['role'] != 'admin':
        return redirect(url_for('login'))
    complaints = load_complaints()
    complaint = next((c for c in complaints if c['id'] == id), None)
    if not complaint:
        flash('Complaint not found')
        return redirect(url_for('admin'))
    if request.method == 'POST':
        complaint['status'] = request.form['status']
        complaint['adminComment'] = request.form['adminComment']
        save_complaints(complaints)
        return redirect(url_for('admin'))
    return render_template('edit_complaint.html', complaint=complaint)

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

if __name__ == '__main__':
    app.run(debug=True)