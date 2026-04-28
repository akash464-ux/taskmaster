# ⚡ TaskMaster — Task Manager App

A personal task manager web app built with **Python Flask**, **MariaDB**, and plain HTML/CSS.
Supports multiple users with login, task priorities, due dates, and more.

---

## 📁 Project Structure

```
taskmaster/
├── app.py               ← Main Flask application (all routes & logic)
├── schema.sql           ← Database setup script
├── requirements.txt     ← Python packages needed
├── README.md            ← This file
└── templates/
    ├── base.html        ← Shared layout (nav, styles)
    ├── login.html       ← Login page
    ├── register.html    ← Register page
    ├── dashboard.html   ← Main task list
    └── task_form.html   ← Create / Edit task form
```

---

## 🚀 Step-by-Step Setup

### Step 1 — Install Python
If not installed, download from https://python.org (version 3.10 or higher).

### Step 2 — Open the project in VS Code
```
File → Open Folder → select the "taskmaster" folder
```

### Step 3 — Open the VS Code Terminal
```
Terminal → New Terminal  (or press Ctrl + `)
```

### Step 4 — Install Python packages
```bash
pip install -r requirements.txt
```
> If `pip` doesn't work, try `pip3` instead.

### Step 5 — Set up MariaDB database
Open your MariaDB client (HeidiSQL, DBeaver, or terminal) and run:

```bash
mysql -u root -p < schema.sql
```

Or open `schema.sql` in your MariaDB tool and run it manually.
This creates a database called **taskmaster** with two tables: `users` and `tasks`.

### Step 6 — Configure your database password
Open `app.py` and find these lines near the top:

```python
app.config['MYSQL_USER']     = 'root'   # ← your MariaDB username
app.config['MYSQL_PASSWORD'] = ''       # ← your MariaDB password
```

Change them to match your MariaDB credentials.

### Step 7 — Run the app
```bash
python app.py
```

You should see:
```
 * Running on http://127.0.0.1:5000
```

### Step 8 — Open in browser
Go to: **http://localhost:5000**

---

## ✨ Features

| Feature              | Description                              |
|----------------------|------------------------------------------|
| User Registration    | Create an account with username + email  |
| Login / Logout       | Secure password hashing                  |
| Create Tasks         | Title, description, priority, due date   |
| Edit Tasks           | Update any field, change status          |
| Delete Tasks         | With confirmation prompt                 |
| Mark Complete        | Click the checkbox to toggle done/pending|
| Priority Levels      | High 🔴 / Medium 🟡 / Low 🟢             |
| Due Dates            | Overdue tasks are highlighted in red     |
| Filters              | Filter by status and priority            |
| Sort                 | Sort by due date, priority, or newest    |
| Stats Cards          | See totals: pending, done, overdue       |

---

## 🛠 Tech Stack

- **Backend**: Python + Flask
- **Database**: MariaDB (via Flask-MySQLdb)
- **Frontend**: HTML + CSS (no external framework)
- **Auth**: Werkzeug password hashing (bcrypt-style)
- **Fonts**: Syne + DM Sans (Google Fonts)

---

## 🔒 Security Notes

- Passwords are hashed — never stored in plain text
- Each user can only see and edit their own tasks
- `login_required` decorator protects all task routes
- Change `app.secret_key` to a long random string before deploying

---

## 💡 Tips for VS Code

- Install the **Python** extension by Microsoft
- Install **SQLTools** + **SQLTools MySQL/MariaDB** extension to browse your database
- Use **Ctrl+`** to open a terminal
- Use **F5** to run/debug the app with the Python debugger