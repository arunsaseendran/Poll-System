# 🗳️ Poll System

A simple **Flask-based Poll System** where users can register, log in, vote on polls, and view results.  
Admins can create and manage polls, and view results in both summary and chart form (via Chart.js).  

---

## ✨ Features
- User authentication (Register/Login/Logout)  
- Admin panel for creating and managing polls  
- Real-time poll results with progress bars and charts  
- Export poll results to CSV  
- Responsive Bootstrap UI  

---

## 🔑 Default Admin Credentials
```
Username: admin
Password: admin123
```

*(You can change this in the database after the first run.)*

---

## ⚙️ Setup Instructions

### 1. Clone the repo
```bash
git clone https://github.com/yourusername/poll-system.git
cd poll-system/Poll\ System
```

### 2. Create & activate virtual environment
```bash
python -m venv venv
source venv/bin/activate   # On Mac/Linux
venv\Scripts\activate      # On Windows
```

### 3. Install dependencies
```bash
pip install -r requirements.txt
```

### 4. Run the app
```bash
flask run
```

The app will be available at:  
👉 http://127.0.0.1:5000

---

## 🐳 Run with Docker

### 1. Build the Docker image
Inside the `Poll System` folder, create a `Dockerfile`:

```dockerfile
# Use Python base image
FROM python:3.10-slim

# Set working directory
WORKDIR /app

# Copy project files
COPY . /app

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Expose Flask port
EXPOSE 5000

# Run Flask app
CMD ["flask", "run", "--host=0.0.0.0", "--port=5000"]
```

### 2. Build & run container
```bash
docker build -t poll-system .
docker run -d -p 5000:5000 poll-system
```

App will be available at:  
👉 http://localhost:5000  

---

## 📂 Project Structure
```
Poll System/
│── app.py               # Main Flask app
│── requirements.txt      # Python dependencies
│── static/               # CSS/JS/Images
│── templates/            # HTML templates (Flask Jinja2)
│── instance/             # Database (SQLite)
```

---

## 📜 License
MIT License – free to use and modify.
