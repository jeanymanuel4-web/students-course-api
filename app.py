
Campus Connect - Integrated Student Enrollment and Information System
Backend: Python + Flask + SQLite REST API

Combines:
  * Laboratory 3 - Student Course Management API (courses endpoints)
  * Laboratory 4 - Campus Connect Student Information Portal (students,
    enrollments, announcements, dashboard statistics)

Run locally:   python app.py
Then browse:   http://127.0.0.1:5000
API base URL:  http://127.0.0.1:5000/api
"""

import os
import sqlite3
from datetime import date, datetime

from flask import Flask, g, jsonify, render_template, request
from flask_cors import CORS
from werkzeug.security import check_password_hash, generate_password_hash

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.environ.get("CAMPUS_CONNECT_DB", os.path.join(BASE_DIR, "database.db"))

app = Flask(__name__)
app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "campus-connect-development-key")

# The Base44 frontend runs on a different origin, so the API must allow CORS.
CORS(app, resources={r"/api/*": {"origins": "*"}})

ENROLLMENT_STATUSES = ("Pending", "Approved", "Rejected", "Cancelled")
STUDENT_FIELDS = ("first_name", "last_name", "email", "program", "year_level")
COURSE_FIELDS = ("course_code", "course_name", "department")
ANNOUNCEMENT_FIELDS = ("title", "content", "author")

SCHEMA = """
CREATE TABLE IF NOT EXISTS students (
    student_id      INTEGER PRIMARY KEY AUTOINCREMENT,
    first_name      TEXT NOT NULL,
    last_name       TEXT NOT NULL,
    email           TEXT NOT NULL UNIQUE,
    program         TEXT NOT NULL,
    year_level      TEXT NOT NULL,
    contact_number  TEXT,
    created_at      TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS courses (
    course_id    INTEGER PRIMARY KEY AUTOINCREMENT,
    course_code  TEXT NOT NULL UNIQUE,
    course_name  TEXT NOT NULL,
    department   TEXT NOT NULL,
    capacity     INTEGER NOT NULL DEFAULT 40,
    created_at   TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS enrollments (
    enrollment_id    INTEGER PRIMARY KEY AUTOINCREMENT,
    student_id       INTEGER NOT NULL,
    course_id        INTEGER NOT NULL,
    enrollment_date  TEXT NOT NULL,
    status           TEXT NOT NULL DEFAULT 'Pending',
    FOREIGN KEY (student_id) REFERENCES students (student_id) ON DELETE CASCADE,
    FOREIGN KEY (course_id)  REFERENCES courses (course_id)  ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS announcements (
    announcement_id  INTEGER PRIMARY KEY AUTOINCREMENT,
    title            TEXT NOT NULL,
    content          TEXT NOT NULL,
    date_posted      TEXT NOT NULL,
    author           TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS users (
    user_id        INTEGER PRIMARY KEY AUTOINCREMENT,
    username       TEXT NOT NULL UNIQUE,
    password_hash  TEXT NOT NULL,
    full_name      TEXT NOT NULL,
    role           TEXT NOT NULL DEFAULT 'student',
    student_id     INTEGER,
    FOREIGN KEY (student_id) REFERENCES students (student_id) ON DELETE SET NULL
);

CREATE INDEX IF NOT EXISTS idx_enrollment_student ON enrollments (student_id);
CREATE INDEX IF NOT EXISTS idx_enrollment_course  ON enrollments (course_id);
"""

ENROLLMENT_SELECT = """
SELECT e.enrollment_id, e.student_id, e.course_id, e.enrollment_date, e.status,
       s.first_name || ' ' || s.last_name AS student_name,
       s.program                          AS program,
       c.course_code                      AS course_code,
       c.course_name                      AS course_name,
       c.department                       AS department
FROM enrollments e
JOIN students s ON s.student_id = e.student_id
JOIN courses  c ON c.course_id  = e.course_id
"""

COURSE_SELECT = """
SELECT c.course_id, c.course_code, c.course_name, c.department, c.capacity,
       (SELECT COUNT(*) FROM enrollments e
        WHERE e.course_id = c.course_id AND e.status IN ('Pending', 'Approved')) AS enrolled_count
FROM courses c
"""


# ---------------------------------------------------------------------------
# Database helpers
# ---------------------------------------------------------------------------
def get_db():
    """One SQLite connection per request (closed automatically at teardown)."""
    if "db" not in g:
        g.db = sqlite3.connect(DB_PATH)
        g.db.row_factory = sqlite3.Row
        g.db.execute("PRAGMA foreign_keys = ON")
    return g.db


@app.teardown_appcontext
def close_db(_exception=None):
    db = g.pop("db", None)
    if db is not None:
        db.close()


def rows(cursor):
    return [dict(row) for row in cursor.fetchall()]


def first(cursor):
    row = cursor.fetchone()
    return dict(row) if row else None


def fail(message, status=400):
    return jsonify({"error": message}), status


def missing_fields(data, fields):
    return [field for field in fields if not str(data.get(field, "")).strip()]


def init_db():
    """Create the tables (and demo rows) automatically when the app starts."""
    with app.app_context():
        db = get_db()
        db.executescript(SCHEMA)
        db.commit()
        if db.execute("SELECT COUNT(*) FROM students").fetchone()[0] == 0:
            seed_demo_data(db)
            db.commit()


def seed_demo_data(db):
    students = [
        ("Maria Clara", "Santos", "maria.santos@campusconnect.edu.ph", "BS Computer Science", "3rd Year", "0917 555 0142"),
        ("Juan Miguel", "Dela Cruz", "juan.delacruz@campusconnect.edu.ph", "BS Information Technology", "2nd Year", "0918 442 7710"),
        ("Ana Lucia", "Reyes", "ana.reyes@campusconnect.edu.ph", "BS Business Administration", "4th Year", "0995 118 3320"),
        ("Kyle Adrian", "Mendoza", "kyle.mendoza@campusconnect.edu.ph", "BS Computer Science", "1st Year", "0921 774 0098"),
        ("Sofia Isabel", "Garcia", "sofia.garcia@campusconnect.edu.ph", "BS Nursing", "2nd Year", "0906 220 8871"),
        ("Daniel Paolo", "Ramos", "daniel.ramos@campusconnect.edu.ph", "BS Civil Engineering", "3rd Year", "0917 660 4455"),
        ("Liza Marie", "Fernandez", "liza.fernandez@campusconnect.edu.ph", "BS Psychology", "4th Year", "0933 512 6604"),
        ("Marco Antonio", "Villanueva", "marco.villanueva@campusconnect.edu.ph", "BS Information Systems", "1st Year", "0947 883 2210"),
    ]
    db.executemany(
        "INSERT INTO students (first_name, last_name, email, program, year_level, contact_number)"
        " VALUES (?, ?, ?, ?, ?, ?)",
        students,
    )

    courses = [
        ("CS101", "Introduction to Computing", "Computer Science", 45),
        ("CS210", "Data Structures and Algorithms", "Computer Science", 40),
        ("CS301", "Database Systems", "Computer Science", 35),
        ("IT210", "Web Systems and Technologies", "Information Technology", 40),
        ("IT320", "Network Administration", "Information Technology", 30),
        ("BA120", "Business Analytics", "Business Administration", 50),
        ("NUR210", "Anatomy and Physiology", "Nursing", 35),
        ("CE230", "Structural Analysis", "Civil Engineering", 30),
    ]
    db.executemany(
        "INSERT INTO courses (course_code, course_name, department, capacity) VALUES (?, ?, ?, ?)",
        courses,
    )

    enrollments = [
        (1, 3, "2026-11-17", "Approved"),
        (1, 2, "2026-11-17", "Pending"),
        (2, 4, "2026-11-17", "Pending"),
        (3, 6, "2026-11-16", "Approved"),
        (4, 1, "2026-11-15", "Approved"),
        (4, 2, "2026-11-14", "Rejected"),
        (5, 7, "2026-11-14", "Approved"),
        (6, 8, "2026-11-13", "Pending"),
        (7, 6, "2026-11-12", "Cancelled"),
        (8, 4, "2026-11-12", "Approved"),
        (2, 5, "2026-11-11", "Approved"),
        (3, 1, "2026-11-10", "Pending"),
    ]
    db.executemany(
        "INSERT INTO enrollments (student_id, course_id, enrollment_date, status) VALUES (?, ?, ?, ?)",
        enrollments,
    )

    announcements = [
        (
            "Enrollment for 1st Semester, A.Y. 2026-2027 is now open",
            "The Office of the Registrar announces that enrollment for the 1st Semester of Academic"
            " Year 2026-2027 opens on November 18, 2026. Review your program curriculum and settle"
            " outstanding records before submitting course requests through Campus Connect.",
            "2026-11-14",
            "Office of the Registrar",
        ),
        (
            "Midterm examination schedule released",
            "The midterm examination schedule for all colleges has been published. Examinations run"
            " from December 1 to December 5, 2026. File schedule adjustment requests at the Academic"
            " Affairs Office not later than November 25, 2026.",
            "2026-11-11",
            "Academic Affairs",
        ),
        (
            "New elective courses added to the Computer Science department",
            "Three new electives are open for enrollment: Mobile Application Development (CS410),"
            " Introduction to Machine Learning (CS420), and Cloud Infrastructure (CS430). Each"
            " elective accepts 25 students on a first-come, first-served basis.",
            "2026-11-06",
            "College of Computing",
        ),
        (
            "Library extends operating hours during examination weeks",
            "The university library is open from 7:00 AM to 10:00 PM, Monday to Saturday, from"
            " November 24 to December 5, 2026. Group discussion rooms may be reserved at the counter.",
            "2026-11-03",
            "University Library",
        ),
    ]
    db.executemany(
        "INSERT INTO announcements (title, content, date_posted, author) VALUES (?, ?, ?, ?)",
        announcements,
    )

    # Demo accounts only. Change the password before using this outside a laboratory.
    db.execute(
        "INSERT INTO users (username, password_hash, full_name, role, student_id)"
        " VALUES (?, ?, ?, ?, ?)",
        ("registrar", generate_password_hash("campus123"), "Registrar Administrator", "admin", None),
    )
    db.execute(
        "INSERT INTO users (username, password_hash, full_name, role, student_id)"
        " VALUES (?, ?, ?, ?, ?)",
        ("student", generate_password_hash("campus123"), "Maria Clara Santos", "student", 1),
    )


# ---------------------------------------------------------------------------
# Health and dashboard statistics
# ---------------------------------------------------------------------------
@app.get("/api/health")
def health():
    db = get_db()
    db.execute("SELECT 1 FROM students LIMIT 1")
    return jsonify(
        {
            "status": "ok",
            "service": "Campus Connect API",
            "database": "sqlite",
            "database_file": os.path.basename(DB_PATH),
            "time": datetime.now().isoformat(timespec="seconds"),
        }
    )


@app.get("/api/stats")
def stats():
    db = get_db()
    counter = lambda sql: db.execute(sql).fetchone()[0]
    return jsonify(
        {
            "total_students": counter("SELECT COUNT(*) FROM students"),
            "total_courses": counter("SELECT COUNT(*) FROM courses"),
            "total_enrollments": counter(
                "SELECT COUNT(*) FROM enrollments WHERE status != 'Cancelled'"
            ),
            "available_courses": counter(
                "SELECT COUNT(*) FROM courses c WHERE ("
                " SELECT COUNT(*) FROM enrollments e"
                " WHERE e.course_id = c.course_id AND e.status IN ('Pending', 'Approved')"
                ") < c.capacity"
            ),
            "pending_enrollments": counter(
                "SELECT COUNT(*) FROM enrollments WHERE status = 'Pending'"
            ),
            "approved_enrollments": counter(
                "SELECT COUNT(*) FROM enrollments WHERE status = 'Approved'"
            ),
            "total_announcements": counter("SELECT COUNT(*) FROM announcements"),
        }
    )


# ---------------------------------------------------------------------------
# Students
# ---------------------------------------------------------------------------
@app.get("/api/students")
def list_students():
    db = get_db()
    search = request.args.get("search", "").strip()
    sql = "SELECT * FROM students"
    params = []
    if search:
        like = "%" + search + "%"
        sql += (
            " WHERE first_name LIKE ? OR last_name LIKE ? OR email LIKE ?"
            " OR program LIKE ? OR year_level LIKE ? OR CAST(student_id AS TEXT) LIKE ?"
        )
        params = [like] * 6
    sql += " ORDER BY last_name, first_name"
    return jsonify(rows(db.execute(sql, params)))


@app.get("/api/students/<int:student_id>")
def get_student(student_id):
    student = first(get_db().execute("SELECT * FROM students WHERE student_id = ?", (student_id,)))
    if student is None:
        return fail("Student not found.", 404)
    return jsonify(student)


@app.post("/api/students")
def create_student():
    data = request.get_json(silent=True) or {}
    missing = missing_fields(data, STUDENT_FIELDS)
    if missing:
        return fail("Missing required field(s): " + ", ".join(missing))

    db = get_db()
    email = str(data["email"]).strip().lower()
    if db.execute("SELECT 1 FROM students WHERE lower(email) = ?", (email,)).fetchone():
        return fail("A student with this email address already exists.", 409)

    cursor = db.execute(
        "INSERT INTO students (first_name, last_name, email, program, year_level, contact_number)"
        " VALUES (?, ?, ?, ?, ?, ?)",
        (
            str(data["first_name"]).strip(),
            str(data["last_name"]).strip(),
            email,
            str(data["program"]).strip(),
            str(data["year_level"]).strip(),
            str(data.get("contact_number", "")).strip(),
        ),
    )
    db.commit()
    created = first(db.execute("SELECT * FROM students WHERE student_id = ?", (cursor.lastrowid,)))
    return jsonify(created), 201


@app.put("/api/students/<int:student_id>")
def update_student(student_id):
    db = get_db()
    existing = first(db.execute("SELECT * FROM students WHERE student_id = ?", (student_id,)))
    if existing is None:
        return fail("Student not found.", 404)

    data = request.get_json(silent=True) or {}
    email = str(data.get("email", existing["email"])).strip().lower()
    duplicate = db.execute(
        "SELECT 1 FROM students WHERE lower(email) = ? AND student_id != ?", (email, student_id)
    ).fetchone()
    if duplicate:
        return fail("Another student already uses this email address.", 409)

    db.execute(
        "UPDATE students SET first_name = ?, last_name = ?, email = ?, program = ?,"
        " year_level = ?, contact_number = ? WHERE student_id = ?",
        (
            str(data.get("first_name", existing["first_name"])).strip(),
            str(data.get("last_name", existing["last_name"])).strip(),
            email,
            str(data.get("program", existing["program"])).strip(),
            str(data.get("year_level", existing["year_level"])).strip(),
            str(data.get("contact_number", existing["contact_number"] or "")).strip(),
            student_id,
        ),
    )
    db.commit()
    return jsonify(first(db.execute("SELECT * FROM students WHERE student_id = ?", (student_id,))))


@app.delete("/api/students/<int:student_id>")
def delete_student(student_id):
    db = get_db()
    if db.execute("SELECT 1 FROM students WHERE student_id = ?", (student_id,)).fetchone() is None:
        return fail("Student not found.", 404)
    db.execute("DELETE FROM students WHERE student_id = ?", (student_id,))
    db.commit()
    return jsonify({"success": True, "deleted_student_id": student_id})


@app.get("/api/students/<int:student_id>/enrollments")
def student_enrollments(student_id):
    db = get_db()
    if db.execute("SELECT 1 FROM students WHERE student_id = ?", (student_id,)).fetchone() is None:
        return fail("Student not found.", 404)
    return jsonify(
        rows(
            db.execute(
                ENROLLMENT_SELECT
                + " WHERE e.student_id = ? ORDER BY e.enrollment_date DESC, e.enrollment_id DESC",
                (student_id,),
            )
        )
    )


# ---------------------------------------------------------------------------
# Courses (Laboratory 3 endpoints, preserved and extended with capacity)
# ---------------------------------------------------------------------------
@app.get("/api/courses")
def list_courses():
    db = get_db()
    search = request.args.get("search", "").strip()
    department = request.args.get("department", "").strip()
    sql = COURSE_SELECT
    params = []
    if department and department != "All":
        sql += " WHERE c.department = ?"
        params.append(department)
    else:
        sql += " WHERE 1 = 1"
    if search:
        like = "%" + search + "%"
        sql += " AND (c.course_code LIKE ? OR c.course_name LIKE ? OR c.department LIKE ?)"
        params.extend([like, like, like])
    sql += " ORDER BY c.course_code"
    return jsonify(rows(db.execute(sql, params)))


@app.get("/api/courses/<int:course_id>")
def get_course(course_id):
    course = first(get_db().execute(COURSE_SELECT + " WHERE c.course_id = ?", (course_id,)))
    if course is None:
        return fail("Course not found.", 404)
    return jsonify(course)


@app.post("/api/courses")
def create_course():
    data = request.get_json(silent=True) or {}
    missing = missing_fields(data, COURSE_FIELDS)
    if missing:
        return fail("Missing required field(s): " + ", ".join(missing))

    db = get_db()
    code = str(data["course_code"]).strip().upper()
    if db.execute("SELECT 1 FROM courses WHERE upper(course_code) = ?", (code,)).fetchone():
        return fail("A course with this course code already exists.", 409)

    cursor = db.execute(
        "INSERT INTO courses (course_code, course_name, department, capacity) VALUES (?, ?, ?, ?)",
        (
            code,
            str(data["course_name"]).strip(),
            str(data["department"]).strip(),
            int(data.get("capacity") or 40),
        ),
    )
    db.commit()
    created = first(db.execute(COURSE_SELECT + " WHERE c.course_id = ?", (cursor.lastrowid,)))
    return jsonify(created), 201


@app.put("/api/courses/<int:course_id>")
def update_course(course_id):
    db = get_db()
    existing = first(db.execute("SELECT * FROM courses WHERE course_id = ?", (course_id,)))
    if existing is None:
        return fail("Course not found.", 404)

    data = request.get_json(silent=True) or {}
    code = str(data.get("course_code", existing["course_code"])).strip().upper()
    duplicate = db.execute(
        "SELECT 1 FROM courses WHERE upper(course_code) = ? AND course_id != ?", (code, course_id)
    ).fetchone()
    if duplicate:
        return fail("Another course already uses this course code.", 409)

    db.execute(
        "UPDATE courses SET course_code = ?, course_name = ?, department = ?, capacity = ?"
        " WHERE course_id = ?",
        (
            code,
            str(data.get("course_name", existing["course_name"])).strip(),
            str(data.get("department", existing["department"])).strip(),
            int(data.get("capacity", existing["capacity"]) or 40),
            course_id,
        ),
    )
    db.commit()
    return jsonify(first(db.execute(COURSE_SELECT + " WHERE c.course_id = ?", (course_id,))))


@app.delete("/api/courses/<int:course_id>")
def delete_course(course_id):
    db = get_db()
    if db.execute("SELECT 1 FROM courses WHERE course_id = ?", (course_id,)).fetchone() is None:
        return fail("Course not found.", 404)
    db.execute("DELETE FROM courses WHERE course_id = ?", (course_id,))
    db.commit()
    return jsonify({"success": True, "deleted_course_id": course_id})


# ---------------------------------------------------------------------------
# Enrollments (the combined Laboratory 3 + 4 feature)
# ---------------------------------------------------------------------------
@app.get("/api/enrollments")
def list_enrollments():
    db = get_db()
    search = request.args.get("search", "").strip()
    status = request.args.get("status", "").strip()
    student_id = request.args.get("student_id", "").strip()
    course_id = request.args.get("course_id", "").strip()

    sql = ENROLLMENT_SELECT + " WHERE 1 = 1"
    params = []
    if status and status != "All":
        sql += " AND e.status = ?"
        params.append(status)
    if student_id:
        sql += " AND e.student_id = ?"
        params.append(student_id)
    if course_id:
        sql += " AND e.course_id = ?"
        params.append(course_id)
    if search:
        like = "%" + search + "%"
        sql += (
            " AND (s.first_name LIKE ? OR s.last_name LIKE ? OR c.course_code LIKE ?"
            " OR c.course_name LIKE ? OR e.status LIKE ?)"
        )
        params.extend([like] * 5)
    sql += " ORDER BY e.enrollment_date DESC, e.enrollment_id DESC"
    return jsonify(rows(db.execute(sql, params)))


@app.post("/api/enrollments")
def create_enrollment():
    data = request.get_json(silent=True) or {}
    student_id = data.get("student_id")
    course_id = data.get("course_id")
    status = str(data.get("status") or "Pending").strip()

    if not student_id or not course_id:
        return fail("student_id and course_id are required.")
    if status not in ENROLLMENT_STATUSES:
        return fail("Status must be one of: " + ", ".join(ENROLLMENT_STATUSES))

    db = get_db()
    if db.execute("SELECT 1 FROM students WHERE student_id = ?", (student_id,)).fetchone() is None:
        return fail("Student not found.", 404)
    if db.execute("SELECT 1 FROM courses WHERE course_id = ?", (course_id,)).fetchone() is None:
        return fail("Course not found.", 404)

    duplicate = db.execute(
        "SELECT 1 FROM enrollments WHERE student_id = ? AND course_id = ?"
        " AND status IN ('Pending', 'Approved')",
        (student_id, course_id),
    ).fetchone()
    if duplicate:
        return fail("This student is already enrolled in this course.", 409)

    cursor = db.execute(
        "INSERT INTO enrollments (student_id, course_id, enrollment_date, status)"
        " VALUES (?, ?, ?, ?)",
        (
            student_id,
            course_id,
            str(data.get("enrollment_date") or date.today().isoformat()),
            status,
        ),
    )
    db.commit()
    created = first(
        db.execute(ENROLLMENT_SELECT + " WHERE e.enrollment_id = ?", (cursor.lastrowid,))
    )
    return jsonify(created), 201


@app.put("/api/enrollments/<int:enrollment_id>")
def update_enrollment(enrollment_id):
    db = get_db()
    existing = first(
        db.execute("SELECT * FROM enrollments WHERE enrollment_id = ?", (enrollment_id,))
    )
    if existing is None:
        return fail("Enrollment not found.", 404)

    data = request.get_json(silent=True) or {}
    status = str(data.get("status", existing["status"])).strip()
    if status not in ENROLLMENT_STATUSES:
        return fail("Status must be one of: " + ", ".join(ENROLLMENT_STATUSES))

    db.execute(
        "UPDATE enrollments SET status = ?, enrollment_date = ? WHERE enrollment_id = ?",
        (
            status,
            str(data.get("enrollment_date", existing["enrollment_date"])),
            enrollment_id,
        ),
    )
    db.commit()
    return jsonify(
        first(db.execute(ENROLLMENT_SELECT + " WHERE e.enrollment_id = ?", (enrollment_id,)))
    )


@app.delete("/api/enrollments/<int:enrollment_id>")
def delete_enrollment(enrollment_id):
    db = get_db()
    if (
        db.execute("SELECT 1 FROM enrollments WHERE enrollment_id = ?", (enrollment_id,)).fetchone()
        is None
    ):
        return fail("Enrollment not found.", 404)
    db.execute("DELETE FROM enrollments WHERE enrollment_id = ?", (enrollment_id,))
    db.commit()
    return jsonify({"success": True, "deleted_enrollment_id": enrollment_id})


# ---------------------------------------------------------------------------
# Announcements (Laboratory 4)
# ---------------------------------------------------------------------------
@app.get("/api/announcements")
def list_announcements():
    return jsonify(
        rows(
            get_db().execute(
                "SELECT * FROM announcements ORDER BY date_posted DESC, announcement_id DESC"
            )
        )
    )


@app.get("/api/announcements/<int:announcement_id>")
def get_announcement(announcement_id):
    announcement = first(
        get_db().execute(
            "SELECT * FROM announcements WHERE announcement_id = ?", (announcement_id,)
        )
    )
    if announcement is None:
        return fail("Announcement not found.", 404)
    return jsonify(announcement)


@app.post("/api/announcements")
def create_announcement():
    data = request.get_json(silent=True) or {}
    missing = missing_fields(data, ANNOUNCEMENT_FIELDS)
    if missing:
        return fail("Missing required field(s): " + ", ".join(missing))

    db = get_db()
    cursor = db.execute(
        "INSERT INTO announcements (title, content, date_posted, author) VALUES (?, ?, ?, ?)",
        (
            str(data["title"]).strip(),
            str(data["content"]).strip(),
            str(data.get("date_posted") or date.today().isoformat()),
            str(data["author"]).strip(),
        ),
    )
    db.commit()
    created = first(
        db.execute(
            "SELECT * FROM announcements WHERE announcement_id = ?", (cursor.lastrowid,)
        )
    )
    return jsonify(created), 201


@app.put("/api/announcements/<int:announcement_id>")
def update_announcement(announcement_id):
    db = get_db()
    existing = first(
        db.execute(
            "SELECT * FROM announcements WHERE announcement_id = ?", (announcement_id,)
        )
    )
    if existing is None:
        return fail("Announcement not found.", 404)

    data = request.get_json(silent=True) or {}
    db.execute(
        "UPDATE announcements SET title = ?, content = ?, author = ?, date_posted = ?"
        " WHERE announcement_id = ?",
        (
            str(data.get("title", existing["title"])).strip(),
            str(data.get("content", existing["content"])).strip(),
            str(data.get("author", existing["author"])).strip(),
            str(data.get("date_posted", existing["date_posted"])),
            announcement_id,
        ),
    )
    db.commit()
    return jsonify(
        first(
            db.execute(
                "SELECT * FROM announcements WHERE announcement_id = ?", (announcement_id,)
            )
        )
    )


@app.delete("/api/announcements/<int:announcement_id>")
def delete_announcement(announcement_id):
    db = get_db()
    if (
        db.execute(
            "SELECT 1 FROM announcements WHERE announcement_id = ?", (announcement_id,)
        ).fetchone()
        is None
    ):
        return fail("Announcement not found.", 404)
    db.execute("DELETE FROM announcements WHERE announcement_id = ?", (announcement_id,))
    db.commit()
    return jsonify({"success": True, "deleted_announcement_id": announcement_id})


# ---------------------------------------------------------------------------
# Users (demo accounts for the laboratory)
# ---------------------------------------------------------------------------
@app.get("/api/users")
def list_users():
    db = get_db()
    return jsonify(
        rows(
            db.execute(
                "SELECT user_id, username, full_name, role, student_id FROM users ORDER BY user_id"
            )
        )
    )


@app.post("/api/login")
def login():
    data = request.get_json(silent=True) or {}
    db = get_db()
    user = first(
        db.execute(
            "SELECT * FROM users WHERE username = ?", (str(data.get("username", "")).strip(),)
        )
    )
    if user is None or not check_password_hash(user["password_hash"], str(data.get("password", ""))):
        return fail("Invalid username or password.", 401)
    return jsonify(
        {
            "user_id": user["user_id"],
            "username": user["username"],
            "full_name": user["full_name"],
            "role": user["role"],
            "student_id": user["student_id"],
        }
    )


# ---------------------------------------------------------------------------
# Standalone pages (served by Flask for quick API demonstrations)
# ---------------------------------------------------------------------------
@app.get("/")
def page_dashboard():
    return render_template("index.html")


@app.get("/students")
def page_students():
    return render_template("students.html")


@app.get("/courses")
def page_courses():
    return render_template("courses.html")


@app.get("/enrollment")
def page_enrollment():
    return render_template("enrollment.html")


@app.get("/announcements")
def page_announcements():
    return render_template("announcements.html")


init_db()

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=True)

