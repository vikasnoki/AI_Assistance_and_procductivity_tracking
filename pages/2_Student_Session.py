import streamlit as st
st.set_page_config(page_title="Student Session", layout="wide")

import os
os.environ['TF_CPP_MIN_LOG_LEVEL'] = '2'  # Suppress TensorFlow warnings

import cv2
import numpy as np
from db import log_session, log_emotion, log_focus, end_session
import time
import traceback

# Try to import emotion detection libraries
EMOTION_BACKEND = None
backend_error = None

try:
    from deepface import DeepFace
    EMOTION_BACKEND = 'deepface'
    st.sidebar.success("✓ DeepFace loaded")
except Exception as e:
    backend_error = f"DeepFace: {str(e)}"
    st.sidebar.warning(f"⚠ DeepFace not available: {str(e)[:50]}...")
    try:
        from fer import FER
        EMOTION_BACKEND = 'fer'
        st.sidebar.success("✓ FER loaded as fallback")
    except Exception as e2:
        backend_error = f"FER: {str(e2)}"
        st.sidebar.error(f"⚠ FER also not available: {str(e2)[:50]}...")


# --- Authentication check ---
if not st.session_state.get("login_state") or st.session_state.get("user_role") != "student":
    st.warning("⚠️ Please log in as a student first.")
    st.stop()

st.title("📹 Student Session Monitoring")
st.markdown(f"### Welcome, **{st.session_state['username']}**! 🎓")

# Show backend status prominently
if EMOTION_BACKEND is None:
    st.error("❌ No emotion detection library available!")
    st.code("pip install fer==22.4.0 tensorflow==2.15.0")
    if backend_error:
        with st.expander("See error details"):
            st.code(backend_error)
elif EMOTION_BACKEND == 'fer':
    st.info("🔧 Using FER for emotion detection (lightweight)")
elif EMOTION_BACKEND == 'deepface':
    st.info("🔧 Using DeepFace for emotion detection (advanced)")

st.divider()

# --- Session state initialization ---
if 'running' not in st.session_state:
    st.session_state['running'] = False
if 'last_emotion' not in st.session_state:
    st.session_state['last_emotion'] = "Waiting..."
if 'focus_status' not in st.session_state:
    st.session_state['focus_status'] = "Unknown"
if 'session_id' not in st.session_state:
    st.session_state['session_id'] = None
if 'emotion_score' not in st.session_state:
    st.session_state['emotion_score'] = "N/A"
if 'last_error' not in st.session_state:
    st.session_state['last_error'] = None
if 'emotion_attempts' not in st.session_state:
    st.session_state['emotion_attempts'] = 0
if 'emotion_successes' not in st.session_state:
    st.session_state['emotion_successes'] = 0
if 'emotion_logged_count' not in st.session_state:
    st.session_state['emotion_logged_count'] = 0
if 'focus_logged_count' not in st.session_state:
    st.session_state['focus_logged_count'] = 0
if 'focused_count' not in st.session_state:
    st.session_state['focused_count'] = 0
if 'distracted_count' not in st.session_state:
    st.session_state['distracted_count'] = 0

# Initialize FER detector if needed
if 'emotion_detector' not in st.session_state:
    if EMOTION_BACKEND == 'fer':
        try:
            st.session_state['emotion_detector'] = FER(mtcnn=False)
            st.sidebar.success("✓ FER detector initialized")
        except Exception as e:
            st.sidebar.error(f"✗ FER init failed: {e}")
            st.session_state['emotion_detector'] = None
    else:
        st.session_state['emotion_detector'] = None

# Initialize cascades
face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')
eye_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_eye.xml')

student_id = st.session_state["user_id"]

# --- UI Layout ---
col1, col2 = st.columns([2, 1])

with col1:
    st.markdown("### 🎥 Live Camera Feed")
    frame_placeholder = st.empty()

with col2:
    st.markdown("### 📊 Current Status")
    emotion_container = st.container()
    focus_container = st.container()
    
    with emotion_container:
        st.markdown("#### 😊 Emotion Detection")
        emotion_placeholder = st.empty()
    
    with focus_container:
        st.markdown("#### 👁️ Focus Status")
        focus_placeholder = st.empty()
    
    st.divider()
    st.markdown("#### ℹ️ Session Info")
    info_placeholder = st.empty()
    
    # Debug info
    if st.session_state.get('last_error'):
        with st.expander("🐛 Last Error"):
            st.error(st.session_state['last_error'])

# --- Control Buttons ---
st.divider()
col_btn1, col_btn2, col_btn3 = st.columns([1, 1, 2])

with col_btn1:
    if st.button("▶️ Start Session", disabled=st.session_state['running'], use_container_width=True):
        st.session_state['running'] = True
        st.session_state['session_id'] = log_session(student_id)
        st.session_state['last_error'] = None
        st.session_state['emotion_attempts'] = 0
        st.session_state['emotion_successes'] = 0
        st.session_state['emotion_logged_count'] = 0
        st.session_state['focus_logged_count'] = 0
        st.session_state['focused_count'] = 0
        st.session_state['distracted_count'] = 0
        st.success(f"✅ Session started! ID: {st.session_state['session_id']}")
        st.rerun()

with col_btn2:
    if st.button("⏹️ End Session", disabled=not st.session_state['running'], use_container_width=True):
        st.session_state['running'] = False
        if st.session_state['session_id']:
            end_session(st.session_state['session_id'])
            st.success(f"✅ Session ended! Logged {st.session_state['emotion_logged_count']} emotions and {st.session_state['focus_logged_count']} focus checks.")
            st.info("📊 Go to **Dashboard** to see your results!")
            st.balloons()
        st.rerun()

# --- Helper function for emotion detection ---
def detect_emotion(frame):
    """Detect emotion using available backend"""
    st.session_state['emotion_attempts'] += 1
    
    try:
        if EMOTION_BACKEND is None:
            return None, None, "No emotion detection backend available"
        
        # Ensure frame is valid
        if frame is None or frame.size == 0:
            return None, None, "Empty frame"
        
        # Resize for performance
        h, w = frame.shape[:2]
        if w > 640:
            scale = 640 / w
            frame = cv2.resize(frame, (640, int(h * scale)))
        
        if EMOTION_BACKEND == 'deepface':
            # Use DeepFace
            result = DeepFace.analyze(
                frame, 
                actions=['emotion'], 
                enforce_detection=False,
                silent=True,
                detector_backend='opencv'
            )
            
            if isinstance(result, list):
                if len(result) == 0:
                    return None, None, "DeepFace: No face detected"
                result = result[0]
            
            emotions = result['emotion']
            dominant_emotion = result['dominant_emotion']
            confidence = emotions[dominant_emotion] / 100.0
            
            st.session_state['emotion_successes'] += 1
            return dominant_emotion, confidence, None
            
        elif EMOTION_BACKEND == 'fer':
            # Use FER
            detector = st.session_state.get('emotion_detector')
            if detector is None:
                return None, None, "FER detector not initialized"
            
            result = detector.detect_emotions(frame)
            
            if not result or len(result) == 0:
                return None, None, "FER: No face detected in frame"
            
            # Get emotions from first detected face
            emotions = result[0]['emotions']
            dominant_emotion = max(emotions, key=emotions.get)
            confidence = emotions[dominant_emotion]
            
            st.session_state['emotion_successes'] += 1
            return dominant_emotion, confidence, None
        
    except Exception as e:
        error_msg = f"{EMOTION_BACKEND}: {str(e)}"
        return None, None, error_msg

# --- Main monitoring loop ---
if st.session_state['running']:
    cap = cv2.VideoCapture(0)
    
    if not cap.isOpened():
        st.error("❌ Cannot open webcam. Please check your camera permissions.")
        st.session_state['running'] = False
    else:
        st.markdown("### 🔴 Recording in Progress...")
        
        frame_count = 0
        emotion_check_interval = 60  # Check every 60 frames (~2 seconds)
        focus_check_interval = 15    # Log focus every 15 frames (~0.5 seconds)
        last_emotion_time = time.time()
        
        while st.session_state['running']:
            ret, frame = cap.read()
            if not ret:
                st.warning("Failed to read frame")
                time.sleep(0.1)
                continue
            
            frame_count += 1
            rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            
            # --- Emotion Detection (less frequent) ---
            current_time = time.time()
            if frame_count % emotion_check_interval == 0 or (current_time - last_emotion_time) > 2:
                if EMOTION_BACKEND is not None:
                    emotion, score, error = detect_emotion(rgb_frame)
                    
                    if error:
                        st.session_state['last_error'] = error
                    elif emotion is not None and score is not None:
                        # LOG TO DATABASE
                        log_emotion(st.session_state['session_id'], emotion, float(score))
                        st.session_state['emotion_logged_count'] += 1
                        
                        # Update display
                        st.session_state['last_emotion'] = emotion.capitalize()
                        st.session_state['emotion_score'] = f"{score:.1%}"
                        st.session_state['last_error'] = None
                        last_emotion_time = current_time
            
            # --- IMPROVED Focus Detection with Better Distraction Detection ---
            focus_status = "Distracted"
            face_detected = False
            eyes_detected = 0
            
            # Detect faces with stricter parameters
            faces = face_cascade.detectMultiScale(
                gray, 
                scaleFactor=1.3, 
                minNeighbors=5,
                minSize=(80, 80)  # Minimum face size to reduce false positives
            )
            
            for (x, y, w, h) in faces:
                face_detected = True
                face_roi_gray = gray[y:y+h, x:x+w]
                face_roi_color = frame[y:y+h, x:x+w]
                
                # More strict eye detection to reduce false positives
                eyes = eye_cascade.detectMultiScale(
                    face_roi_gray,
                    scaleFactor=1.1,
                    minNeighbors=6,  # Increased from 3 to 6 - much stricter
                    minSize=(25, 25),  # Minimum eye size
                    maxSize=(80, 80)   # Maximum eye size
                )
                
                eyes_detected = len(eyes)
                
                # Only mark as focused if BOTH eyes are clearly detected
                if eyes_detected >= 2:
                    focus_status = "Focused"
                    color = (0, 255, 0)  # Green
                    status_text = f"FOCUSED (Eyes: {eyes_detected})"
                else:
                    focus_status = "Distracted"
                    color = (0, 0, 255)  # Red
                    if eyes_detected == 1:
                        status_text = f"DISTRACTED (Only {eyes_detected} eye)"
                    else:
                        status_text = "DISTRACTED (No eyes detected)"
                
                # Draw face rectangle
                cv2.rectangle(frame, (x, y), (x+w, y+h), color, 3)
                
                # Draw status text above face
                cv2.putText(frame, status_text, (x, y-10), 
                           cv2.FONT_HERSHEY_SIMPLEX, 0.7, color, 2)
                
                # Draw eye count below face
                cv2.putText(frame, f"Face detected | Eyes: {eyes_detected}/2", 
                           (x, y+h+25), cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 2)
                
                # Draw rectangles around detected eyes
                for (ex, ey, ew, eh) in eyes:
                    cv2.rectangle(frame, (x+ex, y+ey), (x+ex+ew, y+ey+eh), (255, 255, 0), 2)
                    cv2.putText(frame, "EYE", (x+ex, y+ey-5), 
                               cv2.FONT_HERSHEY_SIMPLEX, 0.4, (255, 255, 0), 1)
            
            # If no face detected at all, definitely distracted
            if not face_detected:
                focus_status = "Distracted"
                cv2.putText(frame, "NO FACE DETECTED - DISTRACTED", 
                           (50, 50), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 3)
                cv2.putText(frame, "Look at the camera!", 
                           (50, 90), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 255), 2)
            
            # Update session counters
            if focus_status == "Focused":
                st.session_state['focused_count'] += 1
            else:
                st.session_state['distracted_count'] += 1
            
            # LOG FOCUS STATUS (every N frames)
            if frame_count % focus_check_interval == 0:
                st.session_state['focus_status'] = focus_status
                log_focus(st.session_state['session_id'], focus_status)
                st.session_state['focus_logged_count'] += 1
            
            # Update displays
            frame_placeholder.image(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB), use_column_width=True)

            emotion_placeholder.markdown(f"""
            <div style='padding: 1rem; background: #f0f2f6; border-radius: 8px; text-align: center;'>
                <h2 style='margin: 0;'>{st.session_state.get('last_emotion', 'Waiting...')}</h2>
                <p style='margin: 0; color: #666;'>Confidence: {st.session_state.get('emotion_score', 'N/A')}</p>
            </div>
            """, unsafe_allow_html=True)
            
            if focus_status == "Focused":
                focus_placeholder.markdown(f"""
                <div style='padding: 1rem; background: #d4edda; border-radius: 8px; text-align: center; border: 2px solid #28a745;'>
                    <h2 style='margin: 0; color: #28a745;'>✅ {focus_status}</h2>
                    <p style='margin: 0; color: #28a745;'>Eyes detected: {eyes_detected}</p>
                </div>
                """, unsafe_allow_html=True)
            else:
                focus_placeholder.markdown(f"""
                <div style='padding: 1rem; background: #f8d7da; border-radius: 8px; text-align: center; border: 2px solid #dc3545;'>
                    <h2 style='margin: 0; color: #dc3545;'>⚠️ {focus_status}</h2>
                    <p style='margin: 0; color: #dc3545;'>Eyes detected: {eyes_detected if face_detected else 'No face'}</p>
                </div>
                """, unsafe_allow_html=True)
            
            # Calculate real-time focus percentage
            total_frames = st.session_state['focused_count'] + st.session_state['distracted_count']
            focus_pct = (st.session_state['focused_count'] / total_frames * 100) if total_frames > 0 else 0
            
            # Update info
            info_placeholder.info(f"""
            **Backend:** {EMOTION_BACKEND or 'None'}
            
            **Logged Data:**
            - Emotions: {st.session_state.get('emotion_logged_count', 0)}
            - Focus checks: {st.session_state.get('focus_logged_count', 0)}
            
            **Detection:**
            - Attempts: {st.session_state.get('emotion_attempts', 0)}
            - Success: {st.session_state.get('emotion_successes', 0)}
            
            **Current Session Focus:**
            - ✅ Focused frames: {st.session_state['focused_count']}
            - ❌ Distracted frames: {st.session_state['distracted_count']}
            - 📊 Focus %: {focus_pct:.1f}%
            """)
            
            time.sleep(0.033)  # ~30 FPS
            
            if not st.session_state['running']:
                break
        
        cap.release()
        cv2.destroyAllWindows()
else:
    st.info("👆 Click 'Start Session' to begin monitoring your study session.")
    
    st.markdown("### 📸 Camera Preview")
    st.markdown("""
    <div style='padding: 4rem; background: #f0f2f6; border-radius: 10px; text-align: center;'>
        <h3>Camera will appear here when session starts</h3>
        <p style='color: #666;'>Make sure your camera is connected and permissions are granted</p>
    </div>
    """, unsafe_allow_html=True)
    
    # Instructions for testing distraction
    st.markdown("---")
    st.markdown("### 🧪 How to Test Focus Detection")
    col_test1, col_test2 = st.columns(2)
    
    with col_test1:
        st.success("""
        **✅ To be marked as FOCUSED:**
        - Look directly at the camera
        - Keep both eyes open and visible
        - Maintain good lighting
        - Stay still for best detection
        """)
    
    with col_test2:
        st.error("""
        **❌ To be marked as DISTRACTED:**
        - Look away from the camera
        - Close your eyes
        - Cover your face/eyes
        - Turn your head to the side
        - Move out of camera view
        """)

st.divider()
st.caption("💡 Tip: For best results, ensure you're in a well-lit environment and looking at your screen regularly.")