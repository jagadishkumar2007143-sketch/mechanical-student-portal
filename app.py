import os
from datetime import datetime
from functools import wraps

from flask import Flask, request, redirect, url_for, session, flash, render_template_string
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "change-this-secret-before-deployment")

database_url = os.environ.get("DATABASE_URL", "sqlite:///mechanical_portal.db")
if database_url.startswith("postgres://"):
    database_url = database_url.replace("postgres://", "postgresql://", 1)

app.config["SQLALCHEMY_DATABASE_URI"] = database_url
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
db = SQLAlchemy(app)

ADMIN_USERNAME = os.environ.get("ADMIN_USERNAME", "admin")
ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD", "ChangeMe@123")


class Student(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    roll_no = db.Column(db.String(40), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    department = db.Column(db.String(80), default="Mechanical Engineering")
    approved = db.Column(db.Boolean, default=False, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class StudentRecord(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey("student.id"), nullable=False)
    subject = db.Column(db.String(120), default="Overall")
    marks = db.Column(db.String(80), default="")
    fees = db.Column(db.String(120), default="")
    attendance = db.Column(db.String(80), default="")
    remarks = db.Column(db.Text, default="")
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    student = db.relationship("Student", backref=db.backref("records", lazy=True))


BASE = """
<!doctype html><html><head><meta name="viewport" content="width=device-width, initial-scale=1">
<title>Mechanical Student Portal</title>
<style>
body{font-family:Arial,sans-serif;background:#f3f6fb;margin:0;color:#172033}
header{background:#13294b;color:white;padding:18px 5%;display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap}
main{max-width:1050px;margin:28px auto;padding:0 16px}.card{background:white;padding:22px;border-radius:12px;
box-shadow:0 3px 14px #17203312;margin-bottom:18px}input,textarea,button{font:inherit;padding:10px;margin:6px 0;
width:100%;box-sizing:border-box;border:1px solid #ccd4e0;border-radius:7px}button,.btn{background:#1769aa;color:white;
border:0;cursor:pointer;padding:10px 15px;border-radius:7px;text-decoration:none;display:inline-block;width:auto}
.danger{background:#b42318}.muted{color:#596579}.flash{background:#fff1c2;padding:10px;border-radius:7px;margin:8px 0}
table{width:100%;border-collapse:collapse;background:white}th,td{text-align:left;padding:10px;border-bottom:1px solid #e4e8ef}
small{color:#596579}.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(220px,1fr));gap:12px}
a{color:#1769aa}form.inline{display:inline}form.inline button{margin:2px}
</style></head><body><header><strong>Mechanical Student Portal</strong>
<span>{% if session.get('role') %}<a style="color:white" href="{{ url_for('logout') }}">Logout</a>{% endif %}</span></header>
<main>{% with messages=get_flashed_messages() %}{% for m in messages %}<div class="flash">{{m}}</div>{% endfor %}{% endwith %}
{{ content|safe }}</main></body></html>
"""

def page(content, **context):
    return render_template_string(BASE, content=render_template_string(content, **context))

def admin_required(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        if session.get("role") != "admin":
            return redirect(url_for("login"))
        return fn(*args, **kwargs)
    return wrapper

def student_required(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        if session.get("role") != "student":
            return redirect(url_for("login"))
        return fn(*args, **kwargs)
    return wrapper

@app.route("/")
def home():
    return page("""
    <section class="card"><h1>Welcome</h1><p>Student information system for the Mechanical Engineering department.</p>
    <a class="btn" href="{{url_for('login')}}">Login</a>
    <a class="btn" href="{{url_for('register')}}">Request student access</a></section>
    <section class="card"><h3>Portal features</h3><p>Admin approval • Student accounts • Marks • Fees • Attendance • Remarks</p></section>
    """)

@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        roll = request.form.get("roll_no", "").strip().upper()
        password = request.form.get("password", "")
        if not name or not roll or len(password) < 8:
            flash("Enter your name, roll number, and a password of at least 8 characters.")
        elif Student.query.filter_by(roll_no=roll).first():
            flash("That roll number is already registered. Contact the admin.")
        else:
            student = Student(name=name, roll_no=roll,
                              password_hash=generate_password_hash(password))
            db.session.add(student)
            db.session.commit()
            flash("Request submitted. You can log in after the admin approves it.")
            return redirect(url_for("login"))
    return page("""
    <section class="card"><h2>Request student access</h2>
    <p class="muted">Only Mechanical Engineering students may apply. The admin must approve your request.</p>
    <form method="post"><label>Full name</label><input name="name" required>
    <label>Roll number (this will be your login ID)</label><input name="roll_no" required>
    <label>Create password (minimum 8 characters)</label><input name="password" type="password" minlength="8" required>
    <button>Submit approval request</button></form><a href="{{url_for('login')}}">Back to login</a></section>
    """)

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        if username == ADMIN_USERNAME and check_password_hash(generate_password_hash(ADMIN_PASSWORD), password):
            session.clear()
            session["role"] = "admin"
            return redirect(url_for("admin_dashboard"))
        student = Student.query.filter_by(roll_no=username.upper()).first()
        if student and check_password_hash(student.password_hash, password):
            if not student.approved:
                flash("Your account is waiting for admin approval.")
            else:
                session.clear()
                session["role"] = "student"
                session["student_id"] = student.id
                return redirect(url_for("student_dashboard"))
        else:
            flash("Invalid login ID or password.")
    return page("""
    <section class="card"><h2>Login</h2><form method="post">
    <label>Admin username or student roll number</label><input name="username" required>
    <label>Password</label><input name="password" type="password" required>
    <button>Login</button></form><a href="{{url_for('register')}}">New student? Request access</a></section>
    """)

@app.route("/admin")
@admin_required
def admin_dashboard():
    pending = Student.query.filter_by(approved=False).order_by(Student.created_at.desc()).all()
    students = Student.query.filter_by(approved=True).order_by(Student.roll_no).all()
    return page("""
    <section class="card"><h2>Admin dashboard</h2><p>Approve only students whose department/identity you have verified.</p>
    <h3>Pending requests ({{pending|length}})</h3>
    {% if pending %}<table><tr><th>Name</th><th>Roll number</th><th>Action</th></tr>
    {% for s in pending %}<tr><td>{{s.name}}</td><td>{{s.roll_no}}</td><td>
    <form class="inline" method="post" action="{{url_for('approve', sid=s.id)}}"><button>Approve</button></form>
    <form class="inline" method="post" action="{{url_for('reject', sid=s.id)}}"><button class="danger">Reject</button></form>
    </td></tr>{% endfor %}</table>{% else %}<p>No pending requests.</p>{% endif %}</section>
    <section class="card"><h3>Approved students ({{students|length}})</h3>
    {% if students %}<table><tr><th>Name</th><th>Roll number</th><th>Records</th></tr>
    {% for s in students %}<tr><td>{{s.name}}</td><td>{{s.roll_no}}</td><td><a href="{{url_for('edit_student', sid=s.id)}}">Manage data</a></td></tr>{% endfor %}</table>
    {% else %}<p>No approved students yet.</p>{% endif %}</section>
    """, pending=pending, students=students)

@app.post("/admin/approve/<int:sid>")
@admin_required
def approve(sid):
    student = db.get_or_404(Student, sid)
    student.approved = True
    db.session.commit()
    flash(f"{student.roll_no} approved.")
    return redirect(url_for("admin_dashboard"))

@app.post("/admin/reject/<int:sid>")
@admin_required
def reject(sid):
    student = db.get_or_404(Student, sid)
    db.session.delete(student)
    db.session.commit()
    flash("Request rejected.")
    return redirect(url_for("admin_dashboard"))

@app.route("/admin/student/<int:sid>", methods=["GET", "POST"])
@admin_required
def edit_student(sid):
    student = db.get_or_404(Student, sid)
    if request.method == "POST":
        record = StudentRecord(
            student_id=student.id,
            subject=request.form.get("subject", "").strip() or "Overall",
            marks=request.form.get("marks", "").strip(),
            fees=request.form.get("fees", "").strip(),
            attendance=request.form.get("attendance", "").strip(),
            remarks=request.form.get("remarks", "").strip()
        )
        db.session.add(record)
        db.session.commit()
        flash("Student record saved.")
        return redirect(url_for("edit_student", sid=sid))
    return page("""
    <section class="card"><h2>Manage: {{student.name}} ({{student.roll_no}})</h2>
    <form method="post"><label>Subject / exam</label><input name="subject" placeholder="e.g. Engineering Mechanics">
    <div class="grid"><div><label>Marks</label><input name="marks" placeholder="e.g. 85/100"></div>
    <div><label>Fees status / amount</label><input name="fees" placeholder="e.g. Paid / ₹12000 pending"></div>
    <div><label>Attendance</label><input name="attendance" placeholder="e.g. 92%"></div></div>
    <label>Remarks</label><textarea name="remarks" rows="3"></textarea><button>Save record</button></form>
    <h3>Saved records</h3>{% if student.records %}<table><tr><th>Subject</th><th>Marks</th><th>Fees</th><th>Attendance</th><th>Remarks</th></tr>
    {% for r in student.records|sort(attribute='updated_at', reverse=True) %}<tr><td>{{r.subject}}</td><td>{{r.marks}}</td><td>{{r.fees}}</td><td>{{r.attendance}}</td><td>{{r.remarks}}</td></tr>{% endfor %}</table>
    {% else %}<p>No records saved.</p>{% endif %}
    <p><a href="{{url_for('admin_dashboard')}}">Back to admin dashboard</a></p></section>
    """, student=student)

@app.route("/student")
@student_required
def student_dashboard():
    student = db.get_or_404(Student, session["student_id"])
    return page("""
    <section class="card"><h2>Student dashboard</h2><h3>{{student.name}}</h3>
    <p><b>Roll number:</b> {{student.roll_no}}<br><b>Department:</b> {{student.department}}</p>
    <h3>Your academic records</h3>{% if student.records %}<table><tr><th>Subject / exam</th><th>Marks</th><th>Fees</th><th>Attendance</th><th>Remarks</th></tr>
    {% for r in student.records|sort(attribute='updated_at', reverse=True) %}<tr><td>{{r.subject}}</td><td>{{r.marks}}</td><td>{{r.fees}}</td><td>{{r.attendance}}</td><td>{{r.remarks}}</td></tr>{% endfor %}</table>
    {% else %}<p>Your records have not been added yet. Contact the admin.</p>{% endif %}</section>
    """, student=student)

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("home"))

with app.app_context():
    db.create_all()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)), debug=False)
