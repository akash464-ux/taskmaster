from flask import Flask, render_template, request, redirect, url_for, flash, session
from flask_mysqldb import MySQL
from werkzeug.security import generate_password_hash, check_password_hash
from functools import wraps
from datetime import datetime
import os

app = Flask(__name__)
app.secret_key = 'your-secret-key-change-this-in-production'

# --- MariaDB Configuration ---
app.config['MYSQL_HOST']     = ''  # use IP, not 'localhost'
app.config['MYSQL_PORT']     =    # use your database port                                                                                                                                                                                                                                                                                                                                          
app.config['MYSQL_USER']     = ''       #use database username                         
app.config['MYSQL_PASSWORD'] = ''       #use database password
app.config['MYSQL_DB']       = 'taskmaster'
app.config['MYSQL_CURSORCLASS'] = 'DictCursor'

mysql = MySQL(app)

# --- Login Required Decorator ---                                                      
def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'user_id' not in session:
            flash('Please log in to access this page.', 'warning')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated

# ===================== AUTH ROUTES =====================

@app.route('/')
def index():
    if 'user_id' in session:
        return redirect(url_for('dashboard'))
    return redirect(url_for('login'))

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username'].strip()
        email    = request.form['email'].strip()
        password = request.form['password']

        if not username or not email or not password:
            flash('All fields are required.', 'error')
            return render_template('register.html')

        cur = mysql.connection.cursor()
        cur.execute("SELECT id FROM users WHERE email = %s OR username = %s", (email, username))
        existing = cur.fetchone()
        if existing:
            flash('Username or email already taken.', 'error')
            cur.close()
            return render_template('register.html')

        hashed = generate_password_hash(password)
        cur.execute("INSERT INTO users (username, email, password_hash) VALUES (%s, %s, %s)",
                    (username, email, hashed))
        mysql.connection.commit()
        cur.close()
        flash('Account created! Please log in.', 'success')
        return redirect(url_for('login'))

    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email    = request.form['email'].strip()
        password = request.form['password']

        cur = mysql.connection.cursor()
        cur.execute("SELECT * FROM users WHERE email = %s", (email,))
        user = cur.fetchone()
        cur.close()

        if user and check_password_hash(user['password_hash'], password):
            session['user_id']  = user['id']
            session['username'] = user['username']
            flash(f"Welcome back, {user['username']}!", 'success')
            return redirect(url_for('dashboard'))
        else:
            flash('Invalid email or password.', 'error')

    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    flash('You have been logged out.', 'info')
    return redirect(url_for('login'))

# ===================== DASHBOARD =====================

@app.route('/dashboard')
@login_required
def dashboard():
    cur = mysql.connection.cursor()
    user_id = session['user_id']

    # Counts for summary cards
    cur.execute("SELECT COUNT(*) as total FROM tasks WHERE user_id = %s", (user_id,))
    total = cur.fetchone()['total']

    cur.execute("SELECT COUNT(*) as done FROM tasks WHERE user_id = %s AND status = 'done'", (user_id,))
    done = cur.fetchone()['done']

    cur.execute("SELECT COUNT(*) as pending FROM tasks WHERE user_id = %s AND status = 'pending'", (user_id,))
    pending = cur.fetchone()['pending']

    cur.execute("""SELECT COUNT(*) as overdue FROM tasks
                   WHERE user_id = %s AND status != 'done'
                   AND due_date IS NOT NULL AND due_date < CURDATE()""", (user_id,))
    overdue = cur.fetchone()['overdue']

    # Filter logic
    filter_status   = request.args.get('status', 'all')
    filter_priority = request.args.get('priority', 'all')
    sort_by         = request.args.get('sort', 'due_date')

    query = "SELECT * FROM tasks WHERE user_id = %s"
    params = [user_id]

    if filter_status != 'all':
        query += " AND status = %s"
        params.append(filter_status)

    if filter_priority != 'all':
        query += " AND priority = %s"
        params.append(filter_priority)

    order_map = {
        'due_date':  'due_date ASC',
        'priority':  "FIELD(priority, 'high', 'medium', 'low')",
        'created':   'created_at DESC',
        'title':     'title ASC'
    }
    query += f" ORDER BY {order_map.get(sort_by, 'due_date ASC')}"

    cur.execute(query, params)
    tasks = cur.fetchall()
    cur.close()

    today = datetime.today().date()
    return render_template('dashboard.html',
                           tasks=tasks, today=today,
                           total=total, done=done, pending=pending, overdue=overdue,
                           filter_status=filter_status,
                           filter_priority=filter_priority,
                           sort_by=sort_by)

# ===================== TASK CRUD =====================

@app.route('/task/new', methods=['GET', 'POST'])
@login_required
def new_task():
    if request.method == 'POST':
        title       = request.form['title'].strip()
        description = request.form.get('description', '').strip()
        priority    = request.form.get('priority', 'medium')
        due_date    = request.form.get('due_date') or None

        if not title:
            flash('Task title is required.', 'error')
            return render_template('task_form.html', task=None)

        cur = mysql.connection.cursor()
        cur.execute("""INSERT INTO tasks (user_id, title, description, priority, due_date)
                       VALUES (%s, %s, %s, %s, %s)""",
                    (session['user_id'], title, description, priority, due_date))
        mysql.connection.commit()
        cur.close()
        flash('Task created successfully!', 'success')
        return redirect(url_for('dashboard'))

    return render_template('task_form.html', task=None)

@app.route('/task/<int:task_id>/edit', methods=['GET', 'POST'])
@login_required
def edit_task(task_id):
    cur = mysql.connection.cursor()
    cur.execute("SELECT * FROM tasks WHERE id = %s AND user_id = %s", (task_id, session['user_id']))
    task = cur.fetchone()

    if not task:
        flash('Task not found.', 'error')
        cur.close()
        return redirect(url_for('dashboard'))

    if request.method == 'POST':
        title       = request.form['title'].strip()
        description = request.form.get('description', '').strip()
        priority    = request.form.get('priority', 'medium')
        due_date    = request.form.get('due_date') or None
        status      = request.form.get('status', 'pending')

        cur.execute("""UPDATE tasks SET title=%s, description=%s, priority=%s,
                       due_date=%s, status=%s WHERE id=%s AND user_id=%s""",
                    (title, description, priority, due_date, status, task_id, session['user_id']))
        mysql.connection.commit()
        cur.close()
        flash('Task updated!', 'success')
        return redirect(url_for('dashboard'))

    cur.close()
    return render_template('task_form.html', task=task)

@app.route('/task/<int:task_id>/toggle', methods=['POST'])
@login_required
def toggle_task(task_id):
    cur = mysql.connection.cursor()
    cur.execute("SELECT status FROM tasks WHERE id = %s AND user_id = %s", (task_id, session['user_id']))
    task = cur.fetchone()
    if task:
        new_status = 'done' if task['status'] == 'pending' else 'pending'
        cur.execute("UPDATE tasks SET status = %s WHERE id = %s AND user_id = %s",
                    (new_status, task_id, session['user_id']))
        mysql.connection.commit()
    cur.close()
    return redirect(url_for('dashboard'))

@app.route('/task/<int:task_id>/delete', methods=['POST'])
@login_required
def delete_task(task_id):
    cur = mysql.connection.cursor()
    cur.execute("DELETE FROM tasks WHERE id = %s AND user_id = %s", (task_id, session['user_id']))
    mysql.connection.commit()
    cur.close()
    flash('Task deleted.', 'info')
    return redirect(url_for('dashboard'))

if __name__ == '__main__':
    app.run(debug=True)