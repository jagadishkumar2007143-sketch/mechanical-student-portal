MECHANICAL STUDENT PORTAL

LOCAL TEST
1. Install Python 3.10+.
2. Open terminal in this folder.
3. Run: pip install -r requirements.txt
4. Run: python app.py
5. Open: http://127.0.0.1:5000

DEFAULT ADMIN LOGIN (change before public deployment)
Username: admin
Password: ChangeMe@123

STUDENT ACCESS
1. Student opens the public website and selects Request student access.
2. Student enters name, roll number and creates a password.
3. Request remains pending until admin approves it.
4. After approval, student logs in using roll number + their password.
5. Students can view only their own records. Admin enters marks, fees, attendance and remarks.

DEPLOYMENT NOTES
- Push app.py and requirements.txt to a GitHub repository.
- On Render, create a Web Service connected to that repository.
- Build command: pip install -r requirements.txt
- Start command: gunicorn app:app
- Add environment variables: SECRET_KEY (long random secret), ADMIN_USERNAME, ADMIN_PASSWORD.
- Configure DATABASE_URL to a persistent PostgreSQL database connection string.
- Do not use SQLite on Render free web service: its filesystem is ephemeral.
- Render free web services sleep after 15 minutes idle; use a paid always-on service for continuous availability.
- Keep student data private. Use HTTPS, strong passwords, backups, and change the default admin credentials before sharing the URL.
