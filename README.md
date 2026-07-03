# 🎓 Student360

Student360 is an AI-powered Student Performance Monitoring System developed to monitor student attendance, classroom behaviour, academic performance, and appeals using modern web technologies.

---

## Features

### Student Module

- Secure Login
- Dashboard
- Attendance Overview
- Behaviour Analysis
- Performance Summary
- Appeals Submission
- Profile Management
- Upload Profile Photo

---

### Lecturer Module

- Lecturer Dashboard
- Classroom Selection
- Attendance Monitoring
- Behaviour Monitoring
- Risk Student Identification
- Appeal Review

---

### Admin Module

- Admin Dashboard
- Student Management
- User Registration
- AI Analytics
- Attendance Statistics
- Behaviour Statistics
- Risk Student Analytics
- Pending Appeals
- CSV Upload

---

## Technologies Used

### Frontend

- React.js
- Tailwind CSS
- Axios
- Recharts

### Backend

- FastAPI
- Python
- MongoDB
- Motor
- Pydantic

---

## Project Structure

```
Student360
│
├── backend
│   ├── api
│   ├── database
│   ├── models
│   ├── routes
│   └── main.py
│
├── frontend
│   ├── src
│   ├── public
│   └── package.json
│
└── README.md
```

---

## Installation

### Clone Repository

```bash
git clone https://github.com/USERNAME/Student360.git
```

---

### Backend

```bash
cd backend

python -m venv venv

venv\Scripts\activate

pip install -r requirements.txt

uvicorn main:app --reload
```

Backend runs on

```
http://localhost:8000
```

---

### Frontend

```bash
cd frontend

npm install

npm start
```

Frontend runs on

```
http://localhost:3000
```

---

## User Roles

### Student

- View dashboard
- Track attendance
- Monitor behaviour
- Submit appeals
- Manage profile

### Lecturer

- Manage classrooms
- Monitor attendance
- Review behaviour
- Review appeals

### Administrator

- Manage users
- Upload classroom data
- View analytics
- Monitor risk students

---

## Screenshots

You can add screenshots here.

Example

```
docs/images/dashboard.png
docs/images/profile.png
docs/images/admin.png
```

---

## Future Improvements

- JWT Authentication
- Mobile Application


---

