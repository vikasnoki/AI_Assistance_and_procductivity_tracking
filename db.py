# db.py
import sqlite3
from datetime import datetime

DB_FILE = "student_teacher.db"
conn = sqlite3.connect(DB_FILE, check_same_thread=False)
cursor = conn.cursor()

# --- helper: ensure column exists (auto-migration) ---
def ensure_column_exists(table, column, col_type):
    cursor.execute(f"PRAGMA table_info({table})")
    columns = [row[1] for row in cursor.fetchall()]
    if column not in columns:
        print(f"🛠️ Adding missing column '{column}' to table '{table}'")
        cursor.execute(f"ALTER TABLE {table} ADD COLUMN {column} {col_type}")
        conn.commit()

# --- Tables ---
cursor.execute("""
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT UNIQUE,
    password TEXT,
    role TEXT CHECK(role IN ('student','teacher'))
)
""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS sessions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    student_id INTEGER,
    start_time TEXT,
    end_time TEXT,
    productivity_score REAL DEFAULT 0,
    FOREIGN KEY(student_id) REFERENCES users(id)
)
""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS emotion_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id INTEGER,
    timestamp TEXT,
    emotion TEXT,
    confidence REAL,
    FOREIGN KEY(session_id) REFERENCES sessions(id)
)
""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS focus_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id INTEGER,
    timestamp TEXT,
    status TEXT,
    FOREIGN KEY(session_id) REFERENCES sessions(id)
)
""")

# NEW: Tasks table
cursor.execute("""
CREATE TABLE IF NOT EXISTS tasks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    teacher_id INTEGER,
    student_id INTEGER,
    title TEXT,
    description TEXT,
    due_date TEXT,
    priority TEXT,
    status TEXT DEFAULT 'Pending',
    created_at TEXT,
    FOREIGN KEY(teacher_id) REFERENCES users(id),
    FOREIGN KEY(student_id) REFERENCES users(id)
)
""")

# NEW: Feedback table
cursor.execute("""
CREATE TABLE IF NOT EXISTS feedback (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    teacher_id INTEGER,
    student_id INTEGER,
    message TEXT,
    feedback_type TEXT,
    timestamp TEXT,
    FOREIGN KEY(teacher_id) REFERENCES users(id),
    FOREIGN KEY(student_id) REFERENCES users(id)
)
""")

conn.commit()

# Ensure productivity_score column exists for older DB files
ensure_column_exists("sessions", "productivity_score", "REAL")

# --- User functions ---
def register_user(username, password, role):
    cursor.execute("INSERT INTO users (username, password, role) VALUES (?, ?, ?)", (username, password, role))
    conn.commit()
    return cursor.lastrowid

def authenticate_user(username, password):
    cursor.execute("SELECT id, role FROM users WHERE username=? AND password=?", (username, password))
    return cursor.fetchone()

# --- Session functions ---
def log_session(student_id):
    start_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    cursor.execute("INSERT INTO sessions (student_id, start_time) VALUES (?, ?)", (student_id, start_time))
    conn.commit()
    return cursor.lastrowid

def log_emotion(session_id, emotion, confidence):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    cursor.execute(
        "INSERT INTO emotion_logs (session_id, timestamp, emotion, confidence) VALUES (?, ?, ?, ?)",
        (session_id, timestamp, emotion, confidence)
    )
    conn.commit()

def log_focus(session_id, status):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    cursor.execute(
        "INSERT INTO focus_logs (session_id, timestamp, status) VALUES (?, ?, ?)",
        (session_id, timestamp, status)
    )
    conn.commit()

# --- Productivity calculation (emotion + focus weighted) ---
def calculate_productivity_score(session_id):
    # emotion summary: dict {emotion: {count, avg_confidence}}
    emotions = get_session_summary(session_id)
    focus_data = get_focus_summary(session_id)

    positive_emotions = {"happy", "surprise"}
    neutral_emotions = {"neutral"}
    negative_emotions = {"angry", "sad", "fear", "disgust"}

    total_emotions = sum(v["count"] for v in emotions.values()) or 1
    focus_total = sum(focus_data.values()) or 1

    # Emotion score (0-100)
    emotion_score = 0.0
    for e, v in emotions.items():
        count = v["count"]
        if e in positive_emotions:
            emotion_score += count * 1.0
        elif e in neutral_emotions:
            emotion_score += count * 0.7
        elif e in negative_emotions:
            emotion_score += count * 0.4
        else:
            emotion_score += count * 0.5
    emotion_score = (emotion_score / total_emotions) * 100

    # Focus score (0-100)
    focused = focus_data.get("Focused", 0)
    focus_score = (focused / focus_total) * 100 if focus_total > 0 else 0

    # Weighted final score (70% focus, 30% emotion)
    productivity_score = (0.7 * focus_score) + (0.3 * emotion_score)
    return round(productivity_score, 2)

def end_session(session_id):
    end_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    score = calculate_productivity_score(session_id)
    cursor.execute("UPDATE sessions SET end_time=?, productivity_score=? WHERE id=?", (end_time, score, session_id))
    conn.commit()

# --- Retrieval helpers ---
def get_session_summary(session_id):
    cursor.execute(
        "SELECT emotion, COUNT(*), AVG(confidence) FROM emotion_logs WHERE session_id=? GROUP BY emotion",
        (session_id,)
    )
    rows = cursor.fetchall()
    summary = {row[0]: {"count": row[1], "avg_confidence": row[2]} for row in rows}
    return summary

def get_student_sessions(student_id):
    """Get all completed sessions for a student (for dashboard)"""
    cursor.execute(
        "SELECT id, student_id, start_time, end_time, productivity_score FROM sessions WHERE student_id=? AND end_time IS NOT NULL ORDER BY start_time DESC",
        (student_id,)
    )
    rows = cursor.fetchall()
    
    # Calculate duration in minutes for each session
    sessions = []
    for row in rows:
        session_id, sid, start_time, end_time, score = row
        
        # Parse datetime strings and calculate duration
        try:
            start = datetime.strptime(start_time, "%Y-%m-%d %H:%M:%S")
            end = datetime.strptime(end_time, "%Y-%m-%d %H:%M:%S")
            duration = (end - start).total_seconds() / 60.0  # minutes
        except:
            duration = 0
        
        sessions.append((session_id, sid, start_time, end_time, duration))
    
    return sessions

def get_focus_summary(session_id):
    cursor.execute(
        "SELECT status, COUNT(*) FROM focus_logs WHERE session_id=? GROUP BY status",
        (session_id,)
    )
    rows = cursor.fetchall()
    summary = {row[0]: row[1] for row in rows}
    return summary

def get_productivity_score(session_id):
    cursor.execute("SELECT productivity_score FROM sessions WHERE id=?", (session_id,))
    row = cursor.fetchone()
    return row[0] if row else None

def get_all_students():
    cursor.execute("SELECT id, username FROM users WHERE role='student'")
    return cursor.fetchall()

# --- Additional functions for Student Dashboard ---

def get_session_emotions(session_id):
    """Get all emotion logs for a session with timestamps"""
    cursor.execute(
        "SELECT emotion, confidence, timestamp FROM emotion_logs WHERE session_id=? ORDER BY timestamp",
        (session_id,)
    )
    return cursor.fetchall()

def get_session_focus(session_id):
    """Get all focus logs for a session with timestamps"""
    cursor.execute(
        "SELECT status, timestamp FROM focus_logs WHERE session_id=? ORDER BY timestamp",
        (session_id,)
    )
    return cursor.fetchall()

def get_student_summary(student_id):
    """Get summary statistics for a student (for teacher dashboard)"""
    # Total sessions and time
    cursor.execute(
        "SELECT COUNT(*), SUM(CASE WHEN end_time IS NOT NULL THEN 1 ELSE 0 END) FROM sessions WHERE student_id=?",
        (student_id,)
    )
    total_sessions, completed_sessions = cursor.fetchone()
    
    # Calculate total study time
    cursor.execute(
        "SELECT start_time, end_time FROM sessions WHERE student_id=? AND end_time IS NOT NULL",
        (student_id,)
    )
    rows = cursor.fetchall()
    
    total_time = 0
    for start_time, end_time in rows:
        try:
            start = datetime.strptime(start_time, "%Y-%m-%d %H:%M:%S")
            end = datetime.strptime(end_time, "%Y-%m-%d %H:%M:%S")
            total_time += (end - start).total_seconds() / 60.0
        except:
            pass
    
    # Latest session
    cursor.execute(
        "SELECT id, start_time, productivity_score FROM sessions WHERE student_id=? AND end_time IS NOT NULL ORDER BY start_time DESC LIMIT 1",
        (student_id,)
    )
    latest_session = cursor.fetchone()
    
    return {
        'total_sessions': completed_sessions or 0,
        'total_time': round(total_time, 1),
        'latest_session': latest_session
    }

def get_all_sessions_with_students():
    """Get all sessions with student usernames for teacher view"""
    cursor.execute("""
        SELECT s.id, u.username, s.start_time, s.end_time, s.productivity_score
        FROM sessions s
        JOIN users u ON s.student_id = u.id
        WHERE s.end_time IS NOT NULL
        ORDER BY s.start_time DESC
    """)
    return cursor.fetchall()

# --- NEW: Task Management Functions ---

def assign_task(teacher_id, student_id, title, description, due_date, priority):
    """Assign a task to a student"""
    created_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    cursor.execute(
        "INSERT INTO tasks (teacher_id, student_id, title, description, due_date, priority, created_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
        (teacher_id, student_id, title, description, due_date, priority, created_at)
    )
    conn.commit()
    return cursor.lastrowid

def get_student_tasks(student_id):
    """Get all tasks assigned to a student"""
    cursor.execute(
        "SELECT id, teacher_id, student_id, title, description, due_date, status, priority, created_at FROM tasks WHERE student_id=? ORDER BY created_at DESC",
        (student_id,)
    )
    return cursor.fetchall()

def get_all_tasks():
    """Get all tasks for teacher view"""
    cursor.execute("""
        SELECT t.id, t.title, u.username, t.due_date, t.priority, t.status, t.created_at
        FROM tasks t
        JOIN users u ON t.student_id = u.id
        ORDER BY t.created_at DESC
    """)
    return cursor.fetchall()

def update_task_status(task_id, status):
    """Update task status (Pending/Completed)"""
    cursor.execute("UPDATE tasks SET status=? WHERE id=?", (status, task_id))
    conn.commit()

def delete_task(task_id):
    """Delete a task"""
    cursor.execute("DELETE FROM tasks WHERE id=?", (task_id,))
    conn.commit()

# --- NEW: Feedback Management Functions ---

def add_feedback(teacher_id, student_id, message, feedback_type):
    """Add feedback from teacher to student"""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    cursor.execute(
        "INSERT INTO feedback (teacher_id, student_id, message, feedback_type, timestamp) VALUES (?, ?, ?, ?, ?)",
        (teacher_id, student_id, message, feedback_type, timestamp)
    )
    conn.commit()
    return cursor.lastrowid

def get_student_feedback(student_id):
    """Get all feedback for a student"""
    cursor.execute(
        "SELECT id, teacher_id, student_id, message, feedback_type, timestamp FROM feedback WHERE student_id=? ORDER BY timestamp DESC",
        (student_id,)
    )
    return cursor.fetchall()

def get_all_feedback():
    """Get all feedback for teacher view"""
    cursor.execute("""
        SELECT f.id, u.username, f.message, f.feedback_type, f.timestamp
        FROM feedback f
        JOIN users u ON f.student_id = u.id
        ORDER BY f.timestamp DESC
    """)
    return cursor.fetchall()

def delete_feedback(feedback_id):
    """Delete feedback"""
    cursor.execute("DELETE FROM feedback WHERE id=?", (feedback_id,))
    conn.commit()

# --- Utility Functions ---

def get_teacher_stats(teacher_id):
    """Get statistics for a teacher"""
    # Count tasks assigned by this teacher
    cursor.execute("SELECT COUNT(*) FROM tasks WHERE teacher_id=?", (teacher_id,))
    total_tasks = cursor.fetchone()[0]
    
    # Count feedback given by this teacher
    cursor.execute("SELECT COUNT(*) FROM feedback WHERE teacher_id=?", (teacher_id,))
    total_feedback = cursor.fetchone()[0]
    
    return {
        'total_tasks': total_tasks,
        'total_feedback': total_feedback
    }

# Optional: destructive helper - only use in dev
def clear_all_data():
    """Clear all data from database - USE WITH CAUTION!"""
    cursor.execute("DELETE FROM feedback")
    cursor.execute("DELETE FROM tasks")
    cursor.execute("DELETE FROM emotion_logs")
    cursor.execute("DELETE FROM focus_logs")
    cursor.execute("DELETE FROM sessions")
    cursor.execute("DELETE FROM users")
    conn.commit()
    print("🗑️ All data cleared from database!")