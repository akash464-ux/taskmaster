from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify
from flask_mysqldb import MySQL
from werkzeug.security import generate_password_hash, check_password_hash
from functools import wraps
from datetime import datetime, date
import calendar as cal_module

app = Flask(__name__)
app.secret_key = 'your-secret-key-change-this-in-production'

app.config['MYSQL_HOST']        = '127.0.0.1'
app.config['MYSQL_PORT']        = 3306
app.config['MYSQL_USER']        = 'myuser'
app.config['MYSQL_PASSWORD']    = 'mypass'
app.config['MYSQL_DB']          = 'taskmaster'
app.config['MYSQL_CURSORCLASS'] = 'DictCursor'

mysql = MySQL(app)

def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'user_id' not in session:
            flash('Please log in to access this page.', 'warning')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated

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

@app.route('/dashboard')
@login_required
def dashboard():
    cur     = mysql.connection.cursor()
    user_id = session['user_id']

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

    filter_status   = request.args.get('status', 'all')
    filter_priority = request.args.get('priority', 'all')
    sort_by         = request.args.get('sort', 'due_date')

    query  = "SELECT * FROM tasks WHERE user_id = %s"
    params = [user_id]
    if filter_status != 'all':
        query += " AND status = %s"
        params.append(filter_status)
    if filter_priority != 'all':
        query += " AND priority = %s"
        params.append(filter_priority)

    order_map = {
        'due_date': 'due_date ASC',
        'priority': "FIELD(priority, 'high', 'medium', 'low')",
        'created':  'created_at DESC',
        'title':    'title ASC'
    }
    query += f" ORDER BY {order_map.get(sort_by, 'due_date ASC')}"
    cur.execute(query, params)
    tasks = cur.fetchall()
    cur.close()

    progress = round((done / total * 100) if total > 0 else 0)
    today    = datetime.today().date()

    return render_template('dashboard.html',
                           tasks=tasks, today=today,
                           total=total, done=done, pending=pending, overdue=overdue,
                           progress=progress,
                           filter_status=filter_status,
                           filter_priority=filter_priority,
                           sort_by=sort_by)

@app.route('/calendar')
@login_required
def calendar():
    user_id = session['user_id']
    today   = date.today()
    year    = int(request.args.get('year',  today.year))
    month   = int(request.args.get('month', today.month))

    prev_year,  prev_month  = (year - 1, 12) if month == 1  else (year, month - 1)
    next_year,  next_month  = (year + 1, 1)  if month == 12 else (year, month + 1)

    cur = mysql.connection.cursor()
    cur.execute("""SELECT * FROM tasks WHERE user_id = %s
                   AND due_date IS NOT NULL
                   AND YEAR(due_date) = %s AND MONTH(due_date) = %s""",
                (user_id, year, month))
    tasks = cur.fetchall()
    cur.close()

    tasks_by_day = {}
    for task in tasks:
        day = task['due_date'].day
        tasks_by_day.setdefault(day, []).append(task)

    cal      = cal_module.monthcalendar(year, month)
    month_name = cal_module.month_name[month]

    return render_template('calendar.html',
                           cal=cal, tasks_by_day=tasks_by_day,
                           year=year, month=month, month_name=month_name,
                           today=today,
                           prev_year=prev_year, prev_month=prev_month,
                           next_year=next_year, next_month=next_month)

@app.route('/api/alarms')
@login_required
def get_alarms():
    user_id = session['user_id']
    now     = datetime.now()
    cur     = mysql.connection.cursor()
    cur.execute("""SELECT id, title, priority, alarm_time FROM tasks
                   WHERE user_id = %s AND status = 'pending'
                   AND alarm_time IS NOT NULL AND alarm_triggered = 0
                   AND alarm_time <= %s""", (user_id, now))
    due = cur.fetchall()
    for t in due:
        cur.execute("UPDATE tasks SET alarm_triggered = 1 WHERE id = %s", (t['id'],))
    mysql.connection.commit()
    cur.close()
    return jsonify([{
        'id':         t['id'],
        'title':      t['title'],
        'priority':   t['priority'],
        'alarm_time': t['alarm_time'].strftime('%H:%M') if t['alarm_time'] else ''
    } for t in due])

@app.route('/task/new', methods=['GET', 'POST'])
@login_required
def new_task():
    if request.method == 'POST':
        title       = request.form['title'].strip()
        description = request.form.get('description', '').strip()
        priority    = request.form.get('priority', 'medium')
        due_date    = request.form.get('due_date')         or None
        due_time    = request.form.get('due_time')         or None
        alarm_date  = request.form.get('alarm_date')       or None
        alarm_time  = request.form.get('alarm_time_field') or None

        alarm_datetime = None
        if alarm_date and alarm_time:
            try:
                alarm_datetime = datetime.strptime(f"{alarm_date} {alarm_time}", "%Y-%m-%d %H:%M")
            except ValueError:
                pass

        if not title:
            flash('Task title is required.', 'error')
            return render_template('task_form.html', task=None)

        cur = mysql.connection.cursor()
        cur.execute("""INSERT INTO tasks
                       (user_id, title, description, priority, due_date, due_time, alarm_time)
                       VALUES (%s, %s, %s, %s, %s, %s, %s)""",
                    (session['user_id'], title, description, priority,
                     due_date, due_time, alarm_datetime))
        mysql.connection.commit()
        cur.close()
        flash('Task created!', 'success')
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
        due_date    = request.form.get('due_date')         or None
        due_time    = request.form.get('due_time')         or None
        status      = request.form.get('status', 'pending')
        alarm_date  = request.form.get('alarm_date')       or None
        alarm_time  = request.form.get('alarm_time_field') or None

        alarm_datetime = None
        if alarm_date and alarm_time:
            try:
                alarm_datetime = datetime.strptime(f"{alarm_date} {alarm_time}", "%Y-%m-%d %H:%M")
            except ValueError:
                pass

        cur.execute("""UPDATE tasks SET title=%s, description=%s, priority=%s,
                       due_date=%s, due_time=%s, status=%s,
                       alarm_time=%s, alarm_triggered=0
                       WHERE id=%s AND user_id=%s""",
                    (title, description, priority, due_date, due_time,
                     status, alarm_datetime, task_id, session['user_id']))
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