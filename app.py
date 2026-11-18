"""
Campus Connect - Integrated Student Enrollment and Information System
=====================================================================
Flask REST API backend + SQLite database.

This file is the "server" half of the project. It:
  1. creates and seeds database.db automatically on first run
  2. keeps the Laboratory 3 course endpoints (GET/POST/PUT/DELETE courses)
  3. adds the Laboratory 4 portal resources: students, enrollments,
     announcements and dashboard statistics
  4. answers every request with JSON so the frontend can show real messages

Run locally (Windows):
    pip install -r requirements.txt
    run.bat                (or: python app.py)

Deploy on Render:
    Build command : pip install -r requirements.txt
    Start command : gunicorn app:app
"""

import os
import sqlite3
from datetime import date, datetime

from flask import Flask, g, jsonify, render_template, request
from flask_cors import CORS

BASE_DIR = os.path.abspath(os.path.dirname(__file__))
DATABASE = os.environ.get("DATABASE_PATH") or os.path.join(BASE_DIR, "database.db")
COURSE_CAPACITY = int(os.environ.get("COURSE_CAPACITY", "40"))
STATUSES = ("Pending", "Approved", "Rejected", "Cancelled")

app = Flask(__name__)

# CORS lets the Campus Connect frontend (a different origin) call this API.
CORS(app, resources={r"/api/*": {"origins": "*"}})

# ---------------------------------------------------------------------------
# 1. DATABASE SCHEMA
# ---------------------------------------------------------------------------
SCHEMA = """
CREATE TABLE IF NOT EXISTS students (
    student_id      TEXT PRIMARY KEY,
    first_name      TEXT NOT NULL,
    last_name       TEXT NOT NULL,
    email           TEXT NOT NULL UNIQUE,
    program         TEXT NOT NULL,
    year_level      TEXT NOT NULL,
    contact_number  TEXT,
    created_at      TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS courses (
    course_id    INTEGER PRIMARY KEY AUTOINCREMENT,
    course_code  TEXT NOT NULL UNIQUE,
    course_name  TEXT NOT NULL,
    department   TEXT NOT NULL,
    created_at   TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS enrollments (
    enrollment_id   INTEGER PRIMARY KEY AUTOINCREMENT,
    student_id      TEXT NOT NULL,
    course_id       INTEGER NOT NULL,
    enrollment_date TEXT NOT NULL,
    status          TEXT NOT NULL DEFAULT 'Pending',
    UNIQUE (student_id, course_id),
    FOREIGN KEY (student_id) REFERENCES students (student_id) ON DELETE CASCADE,
    FOREIGN KEY (course_id)  REFERENCES courses (course_id)  ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS announcements (
    announcement_id INTEGER PRIMARY KEY AUTOINCREMENT,
    title           TEXT NOT NULL,
    content         TEXT NOT NULL,
    date_posted     TEXT NOT NULL,
    author          TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS users (
    user_id       INTEGER PRIMARY KEY AUTOINCREMENT,
    username      TEXT NOT NULL UNIQUE,
    password_hash TEXT NOT NULL,
    role          TEXT NOT NULL DEFAULT 'admin'
);
"""

ENROLLMENT_SELECT = """
SELECT e.enrollment_id,
       e.student_id,
       e.course_id,
       e.enrollment_date,
       e.status,
       s.first_name || ' ' || s.last_name AS student_name,
       s.program,
       s.year_level,
       c.course_code,
       c.course_name,
       c.department
FROM enrollments e
JOIN students s ON s.student_id = e.student_id
JOIN courses  c ON c.course_id  = e.course_id
"""

# ---------------------------------------------------------------------------
# 2. SAMPLE DATA (fictional records for testing)
# ---------------------------------------------------------------------------
SAMPLE_STUDENTS = [
    ("2026-00142", "Maria Clara", "Santos", "maria.santos@campusconnect.edu", "BS Information Technology", "3rd Year", "0917 555 0142"),
    ("2026-00118", "Juan Miguel", "Reyes", "juan.reyes@campusconnect.edu", "BS Computer Science", "2nd Year", "0917 555 0118"),
    ("2026-00093", "Ana Liza", "Cruz", "ana.cruz@campusconnect.edu", "BS Business Administration", "4th Year", "0917 555 0093"),
    ("2026-00161", "Paolo Miguel", "Lim", "paolo.lim@campusconnect.edu", "BA Communication", "1st Year", "0917 555 0161"),
    ("2026-00104", "Josefa", "Andres", "josefa.andres@campusconnect.edu", "BS Nursing", "2nd Year", "0917 555 0104"),
    ("2026-00077", "Ramon", "Bautista", "ramon.bautista@campusconnect.edu", "BS Civil Engineering", "3rd Year", "0917 555 0077"),
    ("2026-00188", "Bea Kristine", "Villanueva", "bea.villanueva@campusconnect.edu", "BS Information Systems", "2nd Year", "0917 555 0188"),
    ("2026-00051", "Miguel Angelo", "Torres", "miguel.torres@campusconnect.edu", "BS Accountancy", "4th Year", "0917 555 0051"),
]

SAMPLE_COURSES = [
    ("CS 101", "Introduction to Computing", "College of Computer Studies"),
    ("IT 204", "Data Structures and Algorithms", "College of Computer Studies"),
    ("IS 310", "Systems Integration and Architecture", "College of Computer Studies"),
    ("BA 310", "Principles of Management", "College of Business"),
    ("ENG 102", "Technical Writing", "College of Arts and Sciences"),
    ("NUR 201", "Fundamentals of Nursing", "College of Nursing"),
    ("CE 220", "Structural Analysis", "College of Engineering"),
    ("ACC 301", "Financial Accounting", "College of Business"),
]

SAMPLE_ENROLLMENTS = [
    ("2026-00142", 1, "2026-11-18", "Approved"),
    ("2026-00142", 3, "2026-11-18", "Pending"),
    ("2026-00118", 2, "2026-11-18", "Pending"),
    ("2026-00093", 4, "2026-11-17", "Approved"),
    ("2026-00161", 5, "2026-11-17", "Cancelled"),
    ("2026-00104", 6, "2026-11-16", "Approved"),
    ("2026-00077", 7, "2026-11-16", "Rejected"),
    ("2026-00188", 3, "2026-11-15", "Approved"),
    ("2026-00051", 8, "2026-11-15", "Approved"),
    ("2026-00188", 1, "2026-11-14", "Approved"),
]

SAMPLE_ANNOUNCEMENTS = [
    ("Enrollment for 1st Semester, A.Y. 2026-2027 is now open",
     "Enrollment runs until 30 November 2026. Submit your course requests through the Enrollment module and wait for adviser approval.",
     "2026-11-16", "Office of the University Registrar"),
    ("Midterm examination schedule released",
     "The midterm examination schedule is now available. Please review your course enrollments before the examination period begins.",
     "2026-11-12", "Office of Academic Affairs"),
    ("Laboratory 3 course API maintenance",
     "The course management endpoints will be unavailable on Saturday from 10:00 PM to 12:00 AM for scheduled maintenance.",
     "2026-11-08", "Management Information Systems Office"),
]

SAMPLE_USERS = [
    ("admin", "pbkdf2:sha256:sample-hash-change-me", "admin"),
    ("registrar", "pbkdf2:sha256:sample-hash-change-me", "staff"),
]

# ---------------------------------------------------------------------------
# 3. DATABASE HELPERS
# ---------------------------------------------------------------------------
def get_db():
    """One SQLite connection per request, stored on Flask's g object."""
    if "db" not in g:
        g.db = sqlite3.connect(DATABASE)
        g.db.row_factory = sqlite3.Row
        g.db.execute("PRAGMA foreign_keys = ON")
    return g.db


@app.teardown_appcontext
def close_db(_exception=None):
    db = g.pop("db", None)
    if db is not None:
        db.close()


def to_dict(row):
    return dict(row) if row is not None else None


def fail(message, status=400):
    """Every failure answers with JSON so the frontend can show a real message."""
    return jsonify({"error": message}), status


def today():
    return date.today().isoformat()


def init_db():
    """Create the tables and add sample rows when the database is empty."""
    connection = sqlite3.connect(DATABASE)
    connection.executescript(SCHEMA)
    connection.commit()

    already_seeded = connection.execute("SELECT COUNT(*) FROM students").fetchone()[0] > 0
    if not already_seeded:
        connection.executemany(
            "INSERT INTO students (student_id, first_name, last_name, email, program, year_level, contact_number)"
            " VALUES (?, ?, ?, ?, ?, ?, ?)",
            SAMPLE_STUDENTS,
        )
        connection.executemany(
            "INSERT INTO courses (course_code, course_name, department) VALUES (?, ?, ?)",
            SAMPLE_COURSES,
        )
        connection.executemany(
            "INSERT INTO enrollments (student_id, course_id, enrollment_date, status) VALUES (?, ?, ?, ?)",
            SAMPLE_ENROLLMENTS,
        )
        connection.executemany(
            "INSERT INTO announcements (title, content, date_posted, author) VALUES (?, ?, ?, ?)",
            SAMPLE_ANNOUNCEMENTS,
        )
        connection.executemany(
            "INSERT INTO users (username, password_hash, role) VALUES (?, ?, ?)",
            SAMPLE_USERS,
        )
        connection.commit()
        print("[Campus Connect] database created and seeded with sample records.")

    connection.close()


def fetch_enrollment(db, enrollment_id):
    row = db.execute(ENROLLMENT_SELECT + " WHERE e.enrollment_id = ?", (enrollment_id,)).fetchone()
    return to_dict(row)


# ---------------------------------------------------------------------------
# 4. STATUS PAGE (open http://127.0.0.1:5000 in a browser)
# ---------------------------------------------------------------------------
@app.route("/")
def home():
    db = get_db()
    counts = {
        table: db.execute("SELECT COUNT(*) FROM " + table).fetchone()[0]
        for table in ("students", "courses", "enrollments", "announcements")
    }
    return render_template("index.html", counts=counts, database=DATABASE)


@app.route("/api", methods=["GET"])
def api_index():
    return jsonify({
        "service": "Campus Connect API",
        "version": "1.0",
        "endpoints": [
            "GET /api/health", "GET /api/stats",
            "GET|POST /api/students", "GET|PUT|DELETE /api/students/<student_id>",
            "GET|POST /api/courses", "GET|PUT|DELETE /api/courses/<course_id>",
            "GET|POST /api/enrollments", "GET|PUT|DELETE /api/enrollments/<enrollment_id>",
            "GET|POST /api/announcements", "GET|PUT|DELETE /api/announcements/<announcement_id>",
        ],
    })


@app.route("/api/health", methods=["GET"])
def health():
    db = get_db()
    counts = {
        table: db.execute("SELECT COUNT(*) FROM " + table).fetchone()[0]
        for table in ("students", "courses", "enrollments", "announcements")
    }
    return jsonify({
        "status": "ok",
        "service": "Campus Connect API",
        "database": DATABASE,
        "time": datetime.now().isoformat(timespec="seconds"),
        "counts": counts,
    })


# ---------------------------------------------------------------------------
# 5. DASHBOARD STATISTICS
# ---------------------------------------------------------------------------
@app.route("/api/stats", methods=["GET"])
def stats():
    db = get_db()
    total_students = db.execute("SELECT COUNT(*) FROM students").fetchone()[0]
    total_courses = db.execute("SELECT COUNT(*) FROM courses").fetchone()[0]
    total_enrollments = db.execute("SELECT COUNT(*) FROM enrollments").fetchone()[0]
    available_courses = db.execute(
        """SELECT COUNT(*) FROM courses c
            WHERE (SELECT COUNT(*) FROM enrollments e
                    WHERE e.course_id = c.course_id
                      AND e.status IN ('Pending', 'Approved')) < ?""",
        (COURSE_CAPACITY,),
    ).fetchone()[0]

    recent_announcements = [
        to_dict(row)
        for row in db.execute(
            "SELECT * FROM announcements ORDER BY date_posted DESC, announcement_id DESC LIMIT 3"
        ).fetchall()
    ]
    recent_enrollments = [
        to_dict(row)
        for row in db.execute(ENROLLMENT_SELECT + " ORDER BY e.enrollment_id DESC LIMIT 5").fetchall()
    ]

    return jsonify({
        "total_students": total_students,
        "total_courses": total_courses,
        "total_enrollments": total_enrollments,
        "available_courses": available_courses,
        "pending_enrollments": db.execute(
            "SELECT COUNT(*) FROM enrollments WHERE status = 'Pending'"
        ).fetchone()[0],
        "approved_enrollments": db.execute(
            "SELECT COUNT(*) FROM enrollments WHERE status = 'Approved'"
        ).fetchone()[0],
        "recent_announcements": recent_announcements,
        "recent_enrollments": recent_enrollments,
        "course_capacity": COURSE_CAPACITY,
    })


# ---------------------------------------------------------------------------
# 6. STUDENTS (Laboratory 4 portal records)
# ---------------------------------------------------------------------------
@app.route("/api/students", methods=["GET"])
def list_students():
    db = get_db()
    search = (request.args.get("q") or "").strip()
    sql = """
        SELECT s.*,
               (SELECT COUNT(*) FROM enrollments e
                 WHERE e.student_id = s.student_id AND e.status <> 'Cancelled') AS enrollment_count
        FROM students s
    """
    params = []
    if search:
        like = "%" + search + "%"
        sql += """ WHERE s.student_id LIKE ? OR s.first_name LIKE ? OR s.last_name LIKE ?
                    OR s.email LIKE ? OR s.program LIKE ?"""
        params = [like] * 5
    sql += " ORDER BY s.last_name ASC, s.first_name ASC"
    return jsonify([to_dict(row) for row in db.execute(sql, params).fetchall()])


@app.route("/api/students/<student_id>", methods=["GET"])
def get_student(student_id):
    db = get_db()
    student = db.execute("SELECT * FROM students WHERE student_id = ?", (student_id,)).fetchone()
    if student is None:
        return fail("Student " + student_id + " was not found.", 404)
    payload = to_dict(student)
    payload["enrollments"] = [
        to_dict(row)
        for row in db.execute(
            ENROLLMENT_SELECT + " WHERE e.student_id = ? ORDER BY e.enrollment_id DESC", (student_id,)
        ).fetchall()
    ]
    return jsonify(payload)


@app.route("/api/students", methods=["POST"])
def create_student():
    data = request.get_json(silent=True) or {}
    required = ["student_id", "first_name", "last_name", "email", "program", "year_level"]
    missing = [field for field in required if not str(data.get(field, "")).strip()]
    if missing:
        return fail("Missing required field(s): " + ", ".join(missing))

    db = get_db()
    try:
        db.execute(
            """INSERT INTO students (student_id, first_name, last_name, email, program, year_level, contact_number)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (
                str(data["student_id"]).strip(),
                str(data["first_name"]).strip(),
                str(data["last_name"]).strip(),
                str(data["email"]).strip(),
                str(data["program"]).strip(),
                str(data["year_level"]).strip(),
                str(data.get("contact_number", "")).strip(),
            ),
        )
        db.commit()
    except sqlite3.IntegrityError as error:
        if "email" in str(error):
            return fail("A student with that email address already exists.", 409)
        return fail("A student with that student ID already exists.", 409)

    row = db.execute("SELECT * FROM students WHERE student_id = ?", (str(data["student_id"]).strip(),)).fetchone()
    return jsonify(to_dict(row)), 201


@app.route("/api/students/<student_id>", methods=["PUT"])
def update_student(student_id):
    db = get_db()
    existing = db.execute("SELECT * FROM students WHERE student_id = ?", (student_id,)).fetchone()
    if existing is None:
        return fail("Student " + student_id + " was not found.", 404)

    data = request.get_json(silent=True) or {}
    updated = {
        "first_name": str(data.get("first_name", existing["first_name"])).strip(),
        "last_name": str(data.get("last_name", existing["last_name"])).strip(),
        "email": str(data.get("email", existing["email"])).strip(),
        "program": str(data.get("program", existing["program"])).strip(),
        "year_level": str(data.get("year_level", existing["year_level"])).strip(),
        "contact_number": str(data.get("contact_number", existing["contact_number"] or "")).strip(),
    }
    try:
        db.execute(
            """UPDATE students
                  SET first_name = ?, last_name = ?, email = ?, program = ?, year_level = ?, contact_number = ?
                WHERE student_id = ?""",
            (
                updated["first_name"], updated["last_name"], updated["email"],
                updated["program"], updated["year_level"], updated["contact_number"], student_id,
            ),
        )
        db.commit()
    except sqlite3.IntegrityError:
        return fail("Another student already uses that email address.", 409)

    return jsonify(to_dict(db.execute("SELECT * FROM students WHERE student_id = ?", (student_id,)).fetchone()))


@app.route("/api/students/<student_id>", methods=["DELETE"])
def delete_student(student_id):
    db = get_db()
    existing = db.execute("SELECT student_id FROM students WHERE student_id = ?", (student_id,)).fetchone()
    if existing is None:
        return fail("Student " + student_id + " was not found.", 404)
    db.execute("DELETE FROM students WHERE student_id = ?", (student_id,))
    db.commit()
    return jsonify({"deleted": student_id})


# ---------------------------------------------------------------------------
# 7. COURSES (Laboratory 3 endpoints, preserved)
# ---------------------------------------------------------------------------
@app.route("/api/courses", methods=["GET"])
def list_courses():
    db = get_db()
    search = (request.args.get("q") or "").strip()
    sql = """
        SELECT c.*,
               (SELECT COUNT(*) FROM enrollments e
                 WHERE e.course_id = c.course_id AND e.status <> 'Cancelled') AS enrolled_count
        FROM courses c
    """
    params = []
    if search:
        like = "%" + search + "%"
        sql += " WHERE c.course_code LIKE ? OR c.course_name LIKE ? OR c.department LIKE ?"
        params = [like] * 3
    sql += " ORDER BY c.course_code ASC"
    return jsonify([to_dict(row) for row in db.execute(sql, params).fetchall()])


@app.route("/api/courses/<int:course_id>", methods=["GET"])
def get_course(course_id):
    db = get_db()
    row = db.execute("SELECT * FROM courses WHERE course_id = ?", (course_id,)).fetchone()
    if row is None:
        return fail("Course " + str(course_id) + " was not found.", 404)
    return jsonify(to_dict(row))


@app.route("/api/courses", methods=["POST"])
def create_course():
    data = request.get_json(silent=True) or {}
    required = ["course_code", "course_name", "department"]
    missing = [field for field in required if not str(data.get(field, "")).strip()]
    if missing:
        return fail("Missing required field(s): " + ", ".join(missing))

    db = get_db()
    try:
        cursor = db.execute(
            "INSERT INTO courses (course_code, course_name, department) VALUES (?, ?, ?)",
            (
                str(data["course_code"]).strip().upper(),
                str(data["course_name"]).strip(),
                str(data["department"]).strip(),
            ),
        )
        db.commit()
    except sqlite3.IntegrityError:
        return fail("A course with that course code already exists.", 409)

    row = db.execute("SELECT * FROM courses WHERE course_id = ?", (cursor.lastrowid,)).fetchone()
    return jsonify(to_dict(row)), 201


@app.route("/api/courses/<int:course_id>", methods=["PUT"])
def update_course(course_id):
    db = get_db()
    existing = db.execute("SELECT * FROM courses WHERE course_id = ?", (course_id,)).fetchone()
    if existing is None:
        return fail("Course " + str(course_id) + " was not found.", 404)

    data = request.get_json(silent=True) or {}
    try:
        db.execute(
            "UPDATE courses SET course_code = ?, course_name = ?, department = ? WHERE course_id = ?",
            (
                str(data.get("course_code", existing["course_code"])).strip().upper(),
                str(data.get("course_name", existing["course_name"])).strip(),
                str(data.get("department", existing["department"])).strip(),
                course_id,
            ),
        )
        db.commit()
    except sqlite3.IntegrityError:
        return fail("Another course already uses that course code.", 409)

    return jsonify(to_dict(db.execute("SELECT * FROM courses WHERE course_id = ?", (course_id,)).fetchone()))


@app.route("/api/courses/<int:course_id>", methods=["DELETE"])
def delete_course(course_id):
    db = get_db()
    existing = db.execute("SELECT course_id FROM courses WHERE course_id = ?", (course_id,)).fetchone()
    if existing is None:
        return fail("Course " + str(course_id) + " was not found.", 404)
    db.execute("DELETE FROM courses WHERE course_id = ?", (course_id,))
    db.commit()
    return jsonify({"deleted": course_id})


# ---------------------------------------------------------------------------
# 8. ENROLLMENTS (combined Laboratory 3 + 4 feature)
# ---------------------------------------------------------------------------
@app.route("/api/enrollments", methods=["GET"])
def list_enrollments():
    db = get_db()
    sql = ENROLLMENT_SELECT
    conditions = []
    params = []

    search = (request.args.get("q") or "").strip()
    if search:
        like = "%" + search + "%"
        conditions.append(
            "(s.student_id LIKE ? OR s.first_name LIKE ? OR s.last_name LIKE ?"
            " OR c.course_code LIKE ? OR c.course_name LIKE ? OR e.status LIKE ?)"
        )
        params.extend([like] * 6)

    status = (request.args.get("status") or "").strip()
    if status:
        conditions.append("e.status = ?")
        params.append(status)

    student_id = (request.args.get("student_id") or "").strip()
    if student_id:
        conditions.append("e.student_id = ?")
        params.append(student_id)

    course_id = (request.args.get("course_id") or "").strip()
    if course_id.isdigit():
        conditions.append("e.course_id = ?")
        params.append(int(course_id))

    if conditions:
        sql += " WHERE " + " AND ".join(conditions)
    sql += " ORDER BY e.enrollment_id DESC"

    return jsonify([to_dict(row) for row in db.execute(sql, params).fetchall()])


@app.route("/api/enrollments/<int:enrollment_id>", methods=["GET"])
def get_enrollment(enrollment_id):
    db = get_db()
    payload = fetch_enrollment(db, enrollment_id)
    if payload is None:
        return fail("Enrollment " + str(enrollment_id) + " was not found.", 404)
    return jsonify(payload)


@app.route("/api/enrollments", methods=["POST"])
def create_enrollment():
    data = request.get_json(silent=True) or {}
    student_id = str(data.get("student_id", "")).strip()
    course_id = data.get("course_id")
    status = str(data.get("status") or "Pending").strip()
    enrollment_date = str(data.get("enrollment_date") or today()).strip()

    if not student_id:
        return fail("student_id is required.")
    if course_id in (None, "", 0):
        return fail("course_id is required.")
    if status not in STATUSES:
        return fail("Status must be one of: " + ", ".join(STATUSES))

    db = get_db()
    if db.execute("SELECT 1 FROM students WHERE student_id = ?", (student_id,)).fetchone() is None:
        return fail("Student " + student_id + " does not exist.", 404)
    if db.execute("SELECT 1 FROM courses WHERE course_id = ?", (course_id,)).fetchone() is None:
        return fail("Course " + str(course_id) + " does not exist.", 404)

    duplicate = db.execute(
        "SELECT enrollment_id FROM enrollments WHERE student_id = ? AND course_id = ?",
        (student_id, course_id),
    ).fetchone()
    if duplicate is not None:
        return fail(
            "This student is already enrolled in that course (enrollment #"
            + str(duplicate["enrollment_id"]) + ").",
            409,
        )

    seats_taken = db.execute(
        "SELECT COUNT(*) FROM enrollments WHERE course_id = ? AND status IN ('Pending', 'Approved')",
        (course_id,),
    ).fetchone()[0]
    if seats_taken >= COURSE_CAPACITY:
        return fail("That course already has its maximum of " + str(COURSE_CAPACITY) + " students.", 409)

    cursor = db.execute(
        "INSERT INTO enrollments (student_id, course_id, enrollment_date, status) VALUES (?, ?, ?, ?)",
        (student_id, course_id, enrollment_date, status),
    )
    db.commit()
    return jsonify(fetch_enrollment(db, cursor.lastrowid)), 201


@app.route("/api/enrollments/<int:enrollment_id>", methods=["PUT"])
def update_enrollment(enrollment_id):
    db = get_db()
    existing = db.execute("SELECT * FROM enrollments WHERE enrollment_id = ?", (enrollment_id,)).fetchone()
    if existing is None:
        return fail("Enrollment " + str(enrollment_id) + " was not found.", 404)

    data = request.get_json(silent=True) or {}
    status = str(data.get("status") or existing["status"]).strip()
    enrollment_date = str(data.get("enrollment_date") or existing["enrollment_date"]).strip()
    if status not in STATUSES:
        return fail("Status must be one of: " + ", ".join(STATUSES))

    db.execute(
        "UPDATE enrollments SET status = ?, enrollment_date = ? WHERE enrollment_id = ?",
        (status, enrollment_date, enrollment_id),
    )
    db.commit()
    return jsonify(fetch_enrollment(db, enrollment_id))


@app.route("/api/enrollments/<int:enrollment_id>", methods=["DELETE"])
def delete_enrollment(enrollment_id):
    db = get_db()
    existing = db.execute("SELECT enrollment_id FROM enrollments WHERE enrollment_id = ?", (enrollment_id,)).fetchone()
    if existing is None:
        return fail("Enrollment " + str(enrollment_id) + " was not found.", 404)
    db.execute("DELETE FROM enrollments WHERE enrollment_id = ?", (enrollment_id,))
    db.commit()
    return jsonify({"deleted": enrollment_id})


# ---------------------------------------------------------------------------
# 9. ANNOUNCEMENTS (Laboratory 4 portal)
# ---------------------------------------------------------------------------
@app.route("/api/announcements", methods=["GET"])
def list_announcements():
    db = get_db()
    search = (request.args.get("q") or "").strip()
    sql = "SELECT * FROM announcements"
    params = []
    if search:
        like = "%" + search + "%"
        sql += " WHERE title LIKE ? OR content LIKE ? OR author LIKE ?"
        params = [like] * 3
    sql += " ORDER BY date_posted DESC, announcement_id DESC"
    return jsonify([to_dict(row) for row in db.execute(sql, params).fetchall()])


@app.route("/api/announcements/<int:announcement_id>", methods=["GET"])
def get_announcement(announcement_id):
    db = get_db()
    row = db.execute("SELECT * FROM announcements WHERE announcement_id = ?", (announcement_id,)).fetchone()
    if row is None:
        return fail("Announcement " + str(announcement_id) + " was not found.", 404)
    return jsonify(to_dict(row))


@app.route("/api/announcements", methods=["POST"])
def create_announcement():
    data = request.get_json(silent=True) or {}
    required = ["title", "content", "author"]
    missing = [field for field in required if not str(data.get(field, "")).strip()]
    if missing:
        return fail("Missing required field(s): " + ", ".join(missing))

    db = get_db()
    cursor = db.execute(
        "INSERT INTO announcements (title, content, date_posted, author) VALUES (?, ?, ?, ?)",
        (
            str(data["title"]).strip(),
            str(data["content"]).strip(),
            str(data.get("date_posted") or today()).strip(),
            str(data["author"]).strip(),
        ),
    )
    db.commit()
    row = db.execute("SELECT * FROM announcements WHERE announcement_id = ?", (cursor.lastrowid,)).fetchone()
    return jsonify(to_dict(row)), 201


@app.route("/api/announcements/<int:announcement_id>", methods=["PUT"])
def update_announcement(announcement_id):
    db = get_db()
    existing = db.execute("SELECT * FROM announcements WHERE announcement_id = ?", (announcement_id,)).fetchone()
    if existing is None:
        return fail("Announcement " + str(announcement_id) + " was not found.", 404)

    data = request.get_json(silent=True) or {}
    db.execute(
        "UPDATE announcements SET title = ?, content = ?, author = ?, date_posted = ? WHERE announcement_id = ?",
        (
            str(data.get("title", existing["title"])).strip(),
            str(data.get("content", existing["content"])).strip(),
            str(data.get("author", existing["author"])).strip(),
            str(data.get("date_posted", existing["date_posted"])).strip(),
            announcement_id,
        ),
    )
    db.commit()
    row = db.execute("SELECT * FROM announcements WHERE announcement_id = ?", (announcement_id,)).fetchone()
    return jsonify(to_dict(row))


@app.route("/api/announcements/<int:announcement_id>", methods=["DELETE"])
def delete_announcement(announcement_id):
    db = get_db()
    existing = db.execute("SELECT announcement_id FROM announcements WHERE announcement_id = ?", (announcement_id,)).fetchone()
    if existing is None:
        return fail("Announcement " + str(announcement_id) + " was not found.", 404)
    db.execute("DELETE FROM announcements WHERE announcement_id = ?", (announcement_id,))
    db.commit()
    return jsonify({"deleted": announcement_id})


# ---------------------------------------------------------------------------
# 10. ERROR HANDLERS + STARTUP
# ---------------------------------------------------------------------------
@app.errorhandler(404)
def handle_404(_error):
    return fail("That API endpoint does not exist. Check the README for the endpoint list.", 404)


@app.errorhandler(405)
def handle_405(_error):
    return fail("That HTTP method is not allowed on this endpoint.", 405)


@app.errorhandler(500)
def handle_500(_error):
    return fail("The server hit an unexpected error. Check the terminal running Flask.", 500)


# Create database.db (and the sample records) the first time the app starts.
init_db()

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=True)
