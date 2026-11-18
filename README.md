# Campus Connect — Integrated Student Enrollment and Information System

Backend for the Campus Connect student portal: a **Python Flask REST API** with a
**SQLite** database. It combines Laboratory 3 (student course management API) and
Laboratory 4 (student information portal) into one service.

The user interface is the Campus Connect web portal. This folder is the server it
talks to over HTTP + JSON.

---

## 1. What is inside this folder

    Campus-Connect/
    ├── app.py                  the whole Flask application (routes + database helpers)
    ├── database.db             the SQLite database (created automatically on first run)
    ├── requirements.txt        Python packages the project needs
    ├── README.md               this file
    ├── run.bat                 Windows: creates a virtual environment, installs, runs
    ├── start.bat               Windows: quick run without a virtual environment
    ├── .gitignore              files that must never be committed
    ├── templates/
    │   └── index.html          small status page shown at http://127.0.0.1:5000/
    ├── static/
    │   ├── css/style.css       styling for the status page
    │   ├── javascript/script.js  checks the API health from the status page
    │   └── images/             put your screenshots or logos here
    └── screenshots/            screenshots for your laboratory report

What each important file does:

- **app.py** — creates the database tables, adds sample records, and exposes every
  REST endpoint under /api. This is the only file you need to understand for the
  demonstration.
- **requirements.txt** — Flask (the web framework), flask-cors (lets the browser
  frontend call the API from another address) and gunicorn (the production server
  used by Render).
- **database.db** — a single file holding all five tables. It is created the first
  time app.py runs, so you do not need to ship it.
- **run.bat / start.bat** — double-click runners for Windows.

---

## 2. Requirements

- Python 3.10 or newer (python.org). On Windows, tick "Add Python to PATH" when installing.
- Internet access the first time, to download the packages.

---

## 3. Run it on Windows (3 steps)

1. Double-click **run.bat**.
   The first run creates a virtual environment (venv), installs Flask, and starts the server.
2. Wait for the line:
       Running on http://127.0.0.1:5000
3. Open http://127.0.0.1:5000 in your browser.
   You should see the Campus Connect API status page with the record counts.

Leave that window open while you use the portal. Closing it stops the API.

### Run it manually (any operating system)

    python -m venv venv
    venv/Scripts/activate        (Windows)
    source venv/bin/activate     (macOS / Linux)
    pip install -r requirements.txt
    python app.py

Then open http://127.0.0.1:5000/api/health — it must return status "ok".

---

## 4. The database

SQLite keeps everything in one file, database.db, created next to app.py.

Five tables:

| Table         | Important columns                                                        |
|---------------|--------------------------------------------------------------------------|
| students      | student_id (primary key), first_name, last_name, email, program, year_level, contact_number |
| courses       | course_id (primary key), course_code (unique), course_name, department   |
| enrollments   | enrollment_id (primary key), student_id (foreign key), course_id (foreign key), enrollment_date, status |
| announcements | announcement_id (primary key), title, content, date_posted, author       |
| users         | user_id (primary key), username, password_hash, role                     |

Relationships:

- enrollments.student_id points at students.student_id
- enrollments.course_id points at courses.course_id
- A UNIQUE (student_id, course_id) rule stops the same student enrolling twice in
  the same course. Deleting a student also deletes their enrollments (ON DELETE CASCADE).

Sample data is inserted only when the students table is empty. To start over:
stop the server, delete database.db, and run app.py again.

---

## 5. REST API reference

Base URL: http://127.0.0.1:5000/api

| Method | Endpoint                        | Purpose                          |
|--------|---------------------------------|----------------------------------|
| GET    | /api/health                     | Is the API running? record counts |
| GET    | /api/stats                      | Dashboard totals + recent activity |
| GET    | /api/students?q=                | List / search students           |
| POST   | /api/students                   | Add a student                    |
| GET    | /api/students/<student_id>      | One student + enrollment history |
| PUT    | /api/students/<student_id>      | Edit a student                   |
| DELETE | /api/students/<student_id>      | Delete a student                 |
| GET    | /api/courses?q=                 | List / search courses            |
| POST   | /api/courses                    | Add a course                     |
| GET    | /api/courses/<course_id>        | One course                       |
| PUT    | /api/courses/<course_id>        | Edit a course                    |
| DELETE | /api/courses/<course_id>        | Delete a course                  |
| GET    | /api/enrollments?q=&status=&student_id=&course_id= | List / filter enrollments |
| POST   | /api/enrollments                | Enroll a student in a course     |
| GET    | /api/enrollments/<id>           | One enrollment                   |
| PUT    | /api/enrollments/<id>           | Update status / date             |
| DELETE | /api/enrollments/<id>           | Delete an enrollment             |
| GET    | /api/announcements?q=           | List / search announcements      |
| POST   | /api/announcements              | Create an announcement           |
| GET    | /api/announcements/<id>         | One announcement                 |
| PUT    | /api/announcements/<id>         | Edit an announcement             |
| DELETE | /api/announcements/<id>         | Delete an announcement           |

Every response is JSON. Errors use a real HTTP status code and an "error" message:

    { "error": "This student is already enrolled in that course (enrollment #4)." }

Statuses used by enrollments: Pending, Approved, Rejected, Cancelled.

---

## 6. Connecting the portal to this API

1. Start the API (run.bat).
2. Open the Campus Connect portal and click the API status chip in the top bar.
3. Enter the API base URL and press **Test connection**, then **Save address**.
   - Local:   http://127.0.0.1:5000/api
   - Deployed: https://your-service-name.onrender.com/api

Important: a page served over HTTPS cannot call a plain http://127.0.0.1 address —
the browser blocks it. While presenting locally, open the portal from localhost;
for a public demo, deploy the API (section 8) and use its HTTPS address.

CORS is already enabled in app.py for every /api route, which is what allows the
portal (a different address) to call this API.

---

## 7. Upload to GitHub

1. Create a repository at github.com (for example campus-connect).
2. Open a terminal in this folder and run:

       git init
       git add .
       git commit -m "Campus Connect Flask API"
       git branch -M main
       git remote add origin https://github.com/YOUR-USERNAME/campus-connect.git
       git push -u origin main

3. Refresh the repository page: app.py, requirements.txt, README.md and the
   folders should all be there.

Never commit secrets. database.db is ignored on purpose because it is rebuilt
automatically; if your instructor requires the database file in the repository,
remove the "*.db" line from .gitignore.

To update the repository later:

    git add .
    git commit -m "Describe your change"
    git push

---

## 8. Deploy on Render

1. Push the project to GitHub first (section 7).
2. On render.com choose **New +** then **Web Service**, and connect the repository.
3. Settings:
   - Runtime: Python 3
   - Build command:  pip install -r requirements.txt
   - Start command:  gunicorn app:app
   - Health check path: /api/health
4. Environment variables (optional):
   - COURSE_CAPACITY = 40
   - PYTHON_VERSION = 3.11.9
5. **Persistent storage for SQLite** — important:
   Render's normal disk is wiped on every deploy, which would erase database.db.
   Add a **Disk** to the service (for example mount path /var/data, 1 GB), then add
   the environment variable DATABASE_PATH = /var/data/database.db.
   app.py already reads that variable.
6. Deploy. When it finishes, open https://your-service-name.onrender.com/api/health.
   You should see status "ok".
7. In the Campus Connect portal, set the API base URL to
   https://your-service-name.onrender.com/api

Note: free Render services sleep after a period of inactivity, so the first request
can take up to a minute. Press "Test connection" again if it times out.

---

## 9. Testing guide

Run these checks in order. Each one proves a different part of the integration.

1. **Dashboard** — open the portal home page. The four cards show real counts.
2. **Add a student** — Students → Add student. Fill in 2026-00999, Ana, Reyes,
   ana.reyes@campusconnect.edu, BS Information Technology, 1st Year.
   The table refreshes and the new row appears.
3. **Add a course** — Courses → Add course. Use code TEST 100, name Test Course,
   department College of Computer Studies.
4. **Course list** — the new course appears with an Enrolled count of 0.
5. **Edit a course** — pencil icon, change the name, save. The row updates.
6. **Delete a course** — trash icon, confirm. The row disappears.
7. **Enroll a student** — Enrollments → New enrollment, pick the student from
   step 2 and any course, submit. Status starts as Pending.
8. **Enrollment records** — the new row is at the top with the student name,
   course code and date.
9. **Update status** — change the status dropdown to Approved. The badge updates.
10. **Create an announcement** — Announcements → Post announcement. It appears at
    the top of the list and on the dashboard.
11. **Student profile** — open the student from the table. Student ID, program,
    year level, email and the enrollment history are shown.
12. **Verify SQLite** — refresh the browser; the record is still there. In the
    Flask terminal run: sqlite3 database.db "SELECT * FROM students;" (or open the
    file in DB Browser for SQLite).
13. **Verify the request reached Flask** — the Flask terminal prints one line per
    request, for example:
        127.0.0.1 - - [18/Nov/2026 20:41:02] "POST /api/enrollments HTTP/1.1" 201 -

Also test the failure paths, because they prove there are no fake success messages:

- Enroll the same student in the same course twice → the API answers 409 and the
  form shows the duplicate message.
- Stop the Flask server, then press Add student → the portal shows a connection
  error, not a success message.

---

## 10. Troubleshooting

| Symptom | Cause and fix |
|---------|----------------|
| Portal says "Could not reach the API" | Flask is not running, or the base URL is wrong. Start run.bat and check http://127.0.0.1:5000/api/health |
| Browser blocks the request on an HTTPS page | An HTTPS page cannot call http://127.0.0.1. Deploy the API or run the portal from localhost |
| CORS error in the console | flask-cors is missing. Run: pip install -r requirements.txt |
| "database is locked" | Two copies of app.py are running. Close the extra terminal |
| Records disappear after a Render deploy | The SQLite file is on the temporary disk. Add a persistent disk and set DATABASE_PATH |
| 404 from /api/students | Check the URL: the student ID is part of the path, e.g. /api/students/2026-00142 |

---

## 11. How Laboratory 3 and Laboratory 4 fit together

Laboratory 3 built the courses resource: course_id, course_code, course_name and
department, with GET, POST, PUT and DELETE endpoints. Those endpoints are kept
exactly as they were.

Laboratory 4 added the portal: students, announcements and the dashboard. It needed
a way to connect a student to a course, so this project adds the enrollments table
and resource, which references both of them with foreign keys.

The result is one database, one API and one portal:

    portal page  ->  HTTP request  ->  Flask route  ->  SQL query  ->  SQLite
                 <-  JSON response <-

The course module still works on its own (Laboratory 3), and it now also feeds the
enrollment module and the dashboard counters (Laboratory 4).
