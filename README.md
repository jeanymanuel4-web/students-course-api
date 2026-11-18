# Campus Connect – Student Information Portal

An integrated Student Information System developed using **Python, Flask, SQLite, HTML, CSS, and JavaScript** for the System Integration and Architecture laboratory activities.

This project combines:

- **Laboratory 3A – Student Course Management API**
- **Laboratory 4 – Campus Connect Student Information Portal**

The application provides a simple university portal for managing student records, courses, enrollments, announcements, and dashboard statistics.

## Technologies Used

| Technology | Purpose |
| --- | --- |
| Python | Backend programming language |
| Flask | Web framework and REST API |
| SQLite | Database management |
| HTML | Webpage structure |
| CSS | Website styling |
| JavaScript | Frontend functionality |
| Flask-CORS | Cross-origin API communication |
| Gunicorn | Production web server |

## Project Structure

```text
student-course-api/
├── app.py
├── requirements.txt
├── README.md
├── templates/
│   ├── index.html
│   ├── students.html
│   ├── courses.html
│   ├── enrollment.html
│   └── announcements.html
└── static/
    ├── css/
    │   └── style.css
    └── javascript/
        └── script.js
```

## Main Features

### 1. Dashboard
- Displays total students.
- Displays total courses.
- Displays enrollment statistics.
- Displays available courses.
- Displays pending and approved enrollments.
- Displays total announcements.

### 2. Student Management
- View student records.
- Search for students.
- Add new students.
- Update student information.
- Delete student records.
- View a student's enrollments.

### 3. Course Management
- View available courses.
- Search and filter courses.
- Add new courses.
- Update course information.
- Delete courses.
- Monitor course capacity and enrollment count.

### 4. Enrollment Management
- View enrollment records.
- Create new enrollments.
- Update enrollment status.
- Delete enrollment records.
- Manage Pending, Approved, Rejected, and Cancelled statuses.

### 5. Announcement Management
- View announcements.
- Add announcements.
- Update announcements.
- Delete announcements.

### 6. User Login
- Provides a demonstration login API.
- Supports administrator and student demo accounts.
- Stores password hashes in the database.

## Database

The application uses **SQLite** as its database.

The database is automatically created when the Flask application starts.

The following tables are included:

| Table | Description |
| --- | --- |
| students | Stores student information |
| courses | Stores course information |
| enrollments | Stores student enrollment records |
| announcements | Stores university announcements |
| users | Stores demo user accounts |

Sample data is automatically added when the database is empty.

## API Endpoints

The REST API uses the following endpoints:

### General and Dashboard

| Method | Endpoint | Description |
| --- | --- | --- |
| GET | `/api/health` | Checks API and database status |
| GET | `/api/stats` | Retrieves dashboard statistics |

### Students

| Method | Endpoint | Description |
| --- | --- | --- |
| GET | `/api/students` | Retrieves all students |
| GET | `/api/students/<id>` | Retrieves one student |
| POST | `/api/students` | Adds a student |
| PUT | `/api/students/<id>` | Updates a student |
| DELETE | `/api/students/<id>` | Deletes a student |
| GET | `/api/students/<id>/enrollments` | Retrieves a student's enrollments |

### Courses

| Method | Endpoint | Description |
| --- | --- | --- |
| GET | `/api/courses` | Retrieves all courses |
| GET | `/api/courses/<id>` | Retrieves one course |
| POST | `/api/courses` | Adds a course |
| PUT | `/api/courses/<id>` | Updates a course |
| DELETE | `/api/courses/<id>` | Deletes a course |

### Enrollments

| Method | Endpoint | Description |
| --- | --- | --- |
| GET | `/api/enrollments` | Retrieves enrollment records |
| POST | `/api/enrollments` | Creates an enrollment |
| PUT | `/api/enrollments/<id>` | Updates an enrollment |
| DELETE | `/api/enrollments/<id>` | Deletes an enrollment |

### Announcements

| Method | Endpoint | Description |
| --- | --- | --- |
| GET | `/api/announcements` | Retrieves announcements |
| GET | `/api/announcements/<id>` | Retrieves one announcement |
| POST | `/api/announcements` | Adds an announcement |
| PUT | `/api/announcements/<id>` | Updates an announcement |
| DELETE | `/api/announcements/<id>` | Deletes an announcement |

### Users and Login

| Method | Endpoint | Description |
| --- | --- | --- |
| GET | `/api/users` | Retrieves demo user information |
| POST | `/api/login` | Checks login credentials |

## Demo Login Accounts

The application includes sample accounts for testing.

| Role | Username | Password |
| --- | --- | --- |
| Administrator | `registrar` | `campus123` |
| Student | `student` | `campus123` |

These are demonstration accounts for classroom use only.

## Running the Project Locally

### Requirements

- Python 3.9 or newer
- pip
- A code editor such as Visual Studio Code

### Step 1: Create a Virtual Environment

```bash
python -m venv .venv
```

### Step 2: Activate the Virtual Environment

Windows PowerShell:

```bash
.venv\Scripts\Activate.ps1
```

macOS or Linux:

```bash
source .venv/bin/activate
```

### Step 3: Install Dependencies

```bash
pip install -r requirements.txt
```

### Step 4: Run the Application

```bash
python app.py
```

### Step 5: Open the Application

Open your browser and visit:

```text
http://127.0.0.1:5000
```

## Testing the API

After starting the application, open these URLs in your browser:

| URL | Expected Result |
| --- | --- |
| `http://127.0.0.1:5000/api/health` | API health information |
| `http://127.0.0.1:5000/api/stats` | Dashboard statistics |
| `http://127.0.0.1:5000/api/students` | Student records |
| `http://127.0.0.1:5000/api/courses` | Course records |
| `http://127.0.0.1:5000/api/enrollments` | Enrollment records |
| `http://127.0.0.1:5000/api/announcements` | Announcement records |

POST, PUT, and DELETE requests can be tested using an API testing tool such as Postman.

## Deployment to Render

The application can be deployed using GitHub and Render.

### Render Configuration

| Setting | Value |
| --- | --- |
| Runtime | Python 3 |
| Build Command | `pip install -r requirements.txt` |
| Start Command | `gunicorn app:app` |

### Deployment Steps

1. Push the project files to the GitHub repository.
2. Log in to Render.
3. Select **New → Web Service**.
4. Connect the GitHub repository.
5. Select the `lab3-lab4-integration` branch.
6. Enter the build and start commands listed above.
7. Click **Deploy Web Service**.

After deployment, open your Render service URL to access Campus Connect.

You can also check the API using:

```text
https://your-service.onrender.com/api/health
```

### Important Database Note

The application uses SQLite. On Render, the default filesystem is not persistent across all redeployments and service changes.

To preserve database records, configure a Render persistent disk and set the environment variable:

```text
CAMPUS_CONNECT_DB=/var/data/database.db
```

Mount the persistent disk at:

```text
/var/data
```

## Project Notes

- This project uses fictional student and university information.
- SQLite automatically creates the database and sample records when needed.
- The application combines the course API from Laboratory 3A with the student information portal from Laboratory 4.
- The project is intended for educational and laboratory demonstration purposes.
- The demo login is not a complete production authentication system.

## Developers' Learning Objectives

Through this project, students demonstrate their understanding of:

- Backend API development using Flask.
- Database integration using SQLite.
- Frontend and backend integration.
- REST API methods and endpoints.
- Student and course information management.
- Application deployment using GitHub and Render.

**Project:** Campus Connect – Student Information Portal  
**Subject:** System Integration and Architecture
