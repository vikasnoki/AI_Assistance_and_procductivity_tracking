import streamlit as st
from db import authenticate_user, register_user
import hashlib

st.set_page_config(
    page_title="Student-Teacher Portal",
    page_icon="🎓",
    layout="centered"
)

# Custom CSS for better styling
st.markdown("""
<style>
    .main-header {
        text-align: center;
        padding: 2rem 0;
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        border-radius: 10px;
        margin-bottom: 2rem;
        color: white;
    }
    .feature-box {
        padding: 1.5rem;
        background: #f8f9fa;
        border-radius: 8px;
        margin: 1rem 0;
        border-left: 4px solid #667eea;
    }
    .success-box {
        padding: 1rem;
        background: #E0FFFF;
        border-left: 4px solid #28a745;
        border-radius: 5px;
        margin: 1rem 0;
    }
    .warning-box {
        padding: 1rem;
        background: #fff3cd;
        border-left: 4px solid #ffc107;
        border-radius: 5px;
        margin: 1rem 0;
    }
</style>
""", unsafe_allow_html=True)

# Header
st.markdown("""
<div class="main-header">
    <h1>🎓 Student–Teacher Portal</h1>
    <p>AI-Powered Learning Analytics & Productivity Tracking</p>
</div>
""", unsafe_allow_html=True)

# --- Session state initialization ---
if "login_state" not in st.session_state:
    st.session_state["login_state"] = False
    st.session_state["user_role"] = None
    st.session_state["username"] = None
    st.session_state["user_id"] = None

# Helper function for password hashing (basic example)
def hash_password(password):
    """Simple password hashing - in production, use bcrypt or similar"""
    return hashlib.sha256(password.encode()).hexdigest()

# Check if user is already logged in
if st.session_state["login_state"]:
    role = st.session_state["user_role"]
    username = st.session_state["username"]
    
    st.markdown(f"""
    <div class="success-box">
        <h3>✅ Welcome back, {username}!</h3>
        <p>You are logged in as: <strong>{role.capitalize()}</strong></p>
    </div>
    """, unsafe_allow_html=True)
    
    st.markdown("### 🚀 Quick Navigation")
    
    if role == "student":
        col1, col2 = st.columns(2)
        with col1:
            st.info("📹 **Student Session**\nStart monitoring your study session with AI-powered emotion and focus tracking.")
        with col2:
            st.info("📊 **Student Dashboard**\nView your performance analytics, productivity scores, and improvement trends.")
    else:  # teacher
        col1, col2 = st.columns(2)
        with col1:
            st.info("👥 **Class Overview**\nMonitor all students' performance and identify those who need support.")
        with col2:
            st.info("📈 **Analytics Dashboard**\nView class-wide statistics and individual student progress.")
    
    st.markdown("---")
    st.markdown("💡 **Tip:** Use the sidebar to navigate between pages →")
    
    if st.button("🚪 Logout", use_container_width=True):
        st.session_state["login_state"] = False
        st.session_state["user_role"] = None
        st.session_state["username"] = None
        st.session_state["user_id"] = None
        st.rerun()
    
    st.stop()

# --- Login/Signup tabs ---
tab1, tab2, tab3 = st.tabs(["🔑 Login", "📝 Sign Up", "ℹ️ About"])

# =========================
# TAB 1: LOGIN
# =========================
with tab1:
    st.markdown("### 🔑 Login to Your Account")
    
    with st.form("login_form", clear_on_submit=True):
        username = st.text_input("Username", placeholder="Enter your username")
        password = st.text_input("Password", type="password", placeholder="Enter your password")
        
        col1, col2 = st.columns([3, 1])
        with col1:
            submit = st.form_submit_button("Login", use_container_width=True)
        with col2:
            remember = st.checkbox("Remember me")

        if submit:
            if not username or not password:
                st.error("❌ Please enter both username and password")
            else:
                user = authenticate_user(username, password)
                if user:
                    user_id, role = user
                    st.session_state.update({
                        "login_state": True,
                        "user_role": role,
                        "username": username,
                        "user_id": user_id
                    })
                    st.success(f"✅ Welcome {username}! Redirecting...")
                    st.balloons()
                    st.rerun()
                else:
                    st.error("❌ Invalid username or password. Please try again.")

# =========================
# TAB 2: SIGN UP
# =========================
with tab2:
    st.markdown("### 📝 Create New Account")
    
    with st.form("signup_form", clear_on_submit=True):
        new_username = st.text_input("Choose a username", placeholder="e.g., john_doe")
        new_password = st.text_input("Choose a password", type="password", placeholder="Min 6 characters")
        confirm_password = st.text_input("Confirm password", type="password", placeholder="Re-enter password")
        
        role = st.selectbox("I am a:", ["Student", "Teacher"], format_func=lambda x: f"👨‍🎓 {x}" if x == "Student" else f"👨‍🏫 {x}")
        
        agree_terms = st.checkbox("I agree to the terms and conditions")
        
        submit_signup = st.form_submit_button("Create Account", use_container_width=True)

        if submit_signup:
            if not new_username or not new_password:
                st.error("❌ Please fill in all fields")
            elif len(new_password) < 6:
                st.error("❌ Password must be at least 6 characters long")
            elif new_password != confirm_password:
                st.error("❌ Passwords do not match")
            elif not agree_terms:
                st.error("❌ Please agree to the terms and conditions")
            else:
                try:
                    role_lower = role.lower()
                    register_user(new_username, new_password, role_lower)
                    st.markdown("""
                    <div class="success-box">
                        <h4>🎉 Account Created Successfully!</h4>
                        <p>You can now log in with your credentials.</p>
                    </div>
                    """, unsafe_allow_html=True)
                    st.balloons()
                except Exception as e:
                    st.error(f"⚠️ Username already exists or registration failed: {str(e)}")

# =========================
# TAB 3: ABOUT
# =========================
with tab3:
    st.markdown("### ℹ️ About This System")
    
    st.markdown("""
    <div class="feature-box">
        <h4>🎯 What is this?</h4>
        <p>An AI-powered learning analytics platform that monitors student engagement, 
        emotional state, and focus levels during study sessions.</p>
    </div>
    """, unsafe_allow_html=True)
    
    st.markdown("### ✨ Key Features")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("""
        <div class="feature-box">
            <h4>👨‍🎓 For Students</h4>
            <ul>
                <li>📹 Real-time webcam monitoring</li>
                <li>😊 Emotion detection & tracking</li>
                <li>👁️ Focus level analysis</li>
                <li>📊 Productivity scoring</li>
                <li>📈 Performance trends</li>
            </ul>
        </div>
        """, unsafe_allow_html=True)
    
    with col2:
        st.markdown("""
        <div class="feature-box">
            <h4>👨‍🏫 For Teachers</h4>
            <ul>
                <li>👥 Monitor all students</li>
                <li>📊 Class-wide analytics</li>
                <li>🎯 Identify struggling students</li>
                <li>📈 Track progress over time</li>
                <li>💡 Get actionable insights</li>
            </ul>
        </div>
        """, unsafe_allow_html=True)
    
    st.markdown("### 🔬 How It Works")
    
    st.markdown("""
    1. **🎥 Camera Monitoring**: The system uses your webcam to analyze facial expressions and eye movements
    2. **😊 Emotion Detection**: AI identifies emotions like happy, sad, focused, distracted, etc.
    3. **🎯 Focus Tracking**: Detects whether you're looking at the screen and maintaining focus
    4. **📊 Score Calculation**: Combines emotion (30%) and focus (70%) into a productivity score
    5. **📈 Analytics**: Generates detailed reports and trends for continuous improvement
    """)
    
    st.markdown("### 🔒 Privacy & Security")
    
    st.markdown("""
    <div class="warning-box">
        <h4>⚠️ Important Notes</h4>
        <ul>
            <li>All video processing happens locally on your device</li>
            <li>No video is stored - only metadata (emotions, focus status)</li>
            <li>You can stop monitoring at any time</li>
            <li>Data is only accessible to you and your teachers</li>
        </ul>
    </div>
    """, unsafe_allow_html=True)
    
    st.markdown("### 🚀 Getting Started")
    
    st.markdown("""
    1. **Create an account** in the Sign Up tab
    2. **Log in** with your credentials
    3. **Students**: Go to "Student Session" to start monitoring
    4. **Teachers**: Go to "Teacher Dashboard" to view analytics
    5. Review your performance and improve your productivity!
    """)

# Footer
st.markdown("---")
st.markdown("""
<div style='text-align: center; color: #666; padding: 1rem;'>
    <p>🎓 Student-Teacher Portal | Powered by AI & Computer Vision</p>
    <p style='font-size: 0.8rem;'>Built with Streamlit, OpenCV, and FER</p>
</div>
""", unsafe_allow_html=True)