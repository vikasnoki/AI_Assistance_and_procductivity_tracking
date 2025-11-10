import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from db import (get_all_students, get_student_summary, get_student_sessions,
                get_session_emotions, get_session_focus, get_productivity_score,
                get_all_sessions_with_students, assign_task, get_student_tasks,
                add_feedback, get_student_feedback)

st.set_page_config(page_title="Teacher Dashboard", layout="wide", page_icon="👨‍🏫")

# --- Authentication check ---
if not st.session_state.get("login_state") or st.session_state.get("user_role") != "teacher":
    st.warning("⚠️ Please log in as a teacher first.")
    st.stop()

teacher_id = st.session_state["user_id"]
teacher_name = st.session_state["username"]

# Custom CSS
st.markdown("""
<style>
    .student-card {
        padding: 1.5rem;
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        border-radius: 10px;
        color: white;
        margin: 0.5rem 0;
    }
    .metric-card {
        padding: 1rem;
        background: #f8f9fa;
        border-radius: 8px;
        border-left: 4px solid #667eea;
        margin: 0.5rem 0;
    }
    .task-card {
        padding: 1rem;
        background: #fff3cd;
        border-radius: 8px;
        border-left: 4px solid #ffc107;
        margin: 0.5rem 0;
    }
    .feedback-card {
        padding: 1rem;
        background: #d1ecf1;
        border-radius: 8px;
        border-left: 4px solid #17a2b8;
        margin: 0.5rem 0;
    }
</style>
""", unsafe_allow_html=True)

# Header
st.title("👨‍🏫 Teacher Dashboard")
st.markdown(f"### Welcome, **Prof. {teacher_name}**! 📚")
st.markdown("---")

# Tabs
tab1, tab2, tab3, tab4 = st.tabs(["📊 Class Overview", "🎯 Assign Tasks", "👥 Student Details", "💬 Feedback Hub"])

# ==================== TAB 1: CLASS OVERVIEW ====================
with tab1:
    st.markdown("### 📈 Class Performance Overview")
    
    students = get_all_students()
    
    if not students:
        st.info("👥 No students registered yet. Students will appear here once they sign up.")
        st.stop()
    
    # Class Statistics
    col1, col2, col3, col4 = st.columns(4)
    
    total_students = len(students)
    all_sessions = get_all_sessions_with_students()
    total_sessions = len(all_sessions)
    
    # Calculate averages
    avg_productivity = 0
    active_students = 0
    total_study_time = 0
    
    for student_id, student_name in students:
        summary = get_student_summary(student_id)
        if summary['total_sessions'] > 0:
            active_students += 1
            total_study_time += summary['total_time']
            if summary['latest_session'] and summary['latest_session'][2] is not None:
                avg_productivity += summary['latest_session'][2]
    
    avg_productivity = (avg_productivity / active_students) if active_students > 0 else 0
    avg_study_time = (total_study_time / active_students) if active_students > 0 else 0
    
    with col1:
        st.metric("👥 Total Students", total_students)
    with col2:
        st.metric("📚 Total Sessions", total_sessions)
    with col3:
        st.metric("📊 Avg Productivity", f"{avg_productivity:.0f}%")
    with col4:
        st.metric("⏱️ Avg Study Time", f"{avg_study_time:.0f} min")
    
    st.markdown("---")
    
    # Student Performance Table
    st.markdown("### 🎓 Student Performance Summary")
    
    student_data = []
    for student_id, student_name in students:
        summary = get_student_summary(student_id)
        
        productivity = 0
        status = "🔴 Inactive"
        
        if summary['latest_session'] and summary['latest_session'][2] is not None:
            productivity = summary['latest_session'][2]
            status = "🟢 Active"
        
        student_data.append({
            'ID': student_id,
            'Student': student_name,
            'Status': status,
            'Sessions': summary['total_sessions'],
            'Study Time (min)': summary['total_time'],
            'Latest Productivity': f"{productivity:.0f}%",
            'Performance': '🌟 Excellent' if productivity >= 80 else '👍 Good' if productivity >= 60 else '⚠️ Needs Support'
        })
    
    df_students = pd.DataFrame(student_data)
    
    # Color-coded display
    st.dataframe(
        df_students[['Student', 'Status', 'Sessions', 'Study Time (min)', 'Latest Productivity', 'Performance']],
        use_container_width=True,
        hide_index=True
    )
    
    st.markdown("---")
    
    # Visualizations
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("#### 📊 Productivity Distribution")
        
        productivity_ranges = {
            '🌟 Excellent (80-100%)': 0,
            '👍 Good (60-79%)': 0,
            '⚠️ Needs Support (40-59%)': 0,
            '🚨 Critical (<40%)': 0
        }
        
        for _, row in df_students.iterrows():
            prod = float(row['Latest Productivity'].replace('%', ''))
            if prod >= 80:
                productivity_ranges['🌟 Excellent (80-100%)'] += 1
            elif prod >= 60:
                productivity_ranges['👍 Good (60-79%)'] += 1
            elif prod >= 40:
                productivity_ranges['⚠️ Needs Support (40-59%)'] += 1
            else:
                productivity_ranges['🚨 Critical (<40%)'] += 1
        
        fig_dist = px.bar(
            x=list(productivity_ranges.keys()),
            y=list(productivity_ranges.values()),
            labels={'x': 'Performance Level', 'y': 'Number of Students'},
            color=list(productivity_ranges.values()),
            color_continuous_scale='RdYlGn'
        )
        fig_dist.update_layout(showlegend=False, height=350)
        st.plotly_chart(fig_dist, use_container_width=True)
    
    with col2:
        st.markdown("#### ⏱️ Study Time Comparison")
        
        top_students = df_students.nlargest(5, 'Study Time (min)')
        
        fig_time = px.bar(
            top_students,
            x='Student',
            y='Study Time (min)',
            color='Study Time (min)',
            color_continuous_scale='Blues'
        )
        fig_time.update_layout(showlegend=False, height=350)
        st.plotly_chart(fig_time, use_container_width=True)

# ==================== TAB 2: ASSIGN TASKS ====================
with tab2:
    st.markdown("### 🎯 Task Assignment Center")
    
    col1, col2 = st.columns([2, 1])
    
    with col1:
        st.markdown("#### 📝 Create New Task")
        
        with st.form("task_form", clear_on_submit=True):
            task_title = st.text_input("Task Title", placeholder="e.g., Complete Chapter 5 Exercises")
            task_description = st.text_area("Task Description", placeholder="Provide detailed instructions...", height=150)
            
            col_a, col_b = st.columns(2)
            with col_a:
                due_date = st.date_input("Due Date")
            with col_b:
                priority = st.selectbox("Priority", ["Low", "Medium", "High"])
            
            # Student selection
            students = get_all_students()
            student_options = {f"{name} (ID: {sid})": sid for sid, name in students}
            
            assign_to = st.multiselect(
                "Assign to Students",
                options=list(student_options.keys()),
                help="Select one or more students"
            )
            
            submit_task = st.form_submit_button("📤 Assign Task", use_container_width=True)
            
            if submit_task:
                if not task_title or not task_description:
                    st.error("❌ Please fill in all required fields")
                elif not assign_to:
                    st.error("❌ Please select at least one student")
                else:
                    try:
                        for student_key in assign_to:
                            student_id = student_options[student_key]
                            assign_task(teacher_id, student_id, task_title, task_description, 
                                      str(due_date), priority)
                        
                        st.success(f"✅ Task assigned to {len(assign_to)} student(s)!")
                        st.balloons()
                    except Exception as e:
                        st.error(f"⚠️ Error assigning task: {str(e)}")
    
    with col2:
        st.markdown("#### 📋 Quick Stats")
        
        # Count tasks by priority
        all_tasks_count = 0
        for sid, name in students:
            tasks = get_student_tasks(sid)
            all_tasks_count += len(tasks)
        
        st.markdown(f"""
        <div class="metric-card">
            <h3 style='margin: 0;'>{all_tasks_count}</h3>
            <p style='margin: 0; color: #666;'>Total Active Tasks</p>
        </div>
        """, unsafe_allow_html=True)
        
        st.markdown(f"""
        <div class="metric-card">
            <h3 style='margin: 0;'>{len(students)}</h3>
            <p style='margin: 0; color: #666;'>Students in Class</p>
        </div>
        """, unsafe_allow_html=True)
        
        st.info("💡 **Tip:** Use High priority for urgent tasks and upcoming exams!")

# ==================== TAB 3: STUDENT DETAILS ====================
with tab3:
    st.markdown("### 👥 Individual Student Analysis")
    
    students = get_all_students()
    
    if not students:
        st.info("👥 No students available")
        st.stop()
    
    # Student selector
    student_names = [name for sid, name in students]
    selected_student = st.selectbox("Select Student", student_names)
    
    # Get student ID
    student_id = [sid for sid, name in students if name == selected_student][0]
    
    st.markdown("---")
    
    # Student info and stats
    col1, col2, col3 = st.columns([1, 2, 2])
    
    with col1:
        st.markdown(f"""
        <div class="student-card">
            <h2 style='margin: 0;'>👨‍🎓</h2>
            <h3 style='margin: 10px 0 5px 0;'>{selected_student}</h3>
            <p style='margin: 0; opacity: 0.9;'>Student ID: {student_id}</p>
        </div>
        """, unsafe_allow_html=True)
    
    summary = get_student_summary(student_id)
    sessions = get_student_sessions(student_id)
    
    with col2:
        st.markdown("#### 📊 Performance Metrics")
        st.metric("Total Sessions", summary['total_sessions'])
        st.metric("Total Study Time", f"{summary['total_time']:.0f} min")
        
        if summary['latest_session'] and summary['latest_session'][2] is not None:
            st.metric("Latest Productivity", f"{summary['latest_session'][2]:.0f}%")
        else:
            st.metric("Latest Productivity", "N/A")
    
    with col3:
        st.markdown("#### 📋 Assigned Tasks")
        tasks = get_student_tasks(student_id)
        st.metric("Active Tasks", len(tasks))
        
        if tasks:
            pending = len([t for t in tasks if t[6] == 'Pending'])
            completed = len([t for t in tasks if t[6] == 'Completed'])
            st.metric("Pending", pending, delta=f"-{completed} completed")
    
    st.markdown("---")
    
    # Detailed Analysis
    if not sessions:
        st.info(f"📚 {selected_student} hasn't completed any sessions yet.")
    else:
        # Get latest session for detailed analysis
        latest_session_id = sessions[0][0]
        emotions_data = get_session_emotions(latest_session_id)
        focus_data = get_session_focus(latest_session_id)
        
        # Row 1: Productivity Trend & Emotion Distribution
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("#### 📈 Productivity Trend (Last 10 Sessions)")
            
            session_data = []
            for i, session in enumerate(sessions[:10]):
                score = get_productivity_score(session[0])
                if score:
                    session_data.append({
                        'Session': f"S{i+1}",
                        'Score': score,
                        'Date': session[2][:10]  # Extract date
                    })
            
            if session_data:
                df_trend = pd.DataFrame(session_data).iloc[::-1]
                
                fig_trend = go.Figure()
                fig_trend.add_trace(go.Scatter(
                    x=df_trend['Session'],
                    y=df_trend['Score'],
                    mode='lines+markers',
                    line=dict(color='#667eea', width=3),
                    marker=dict(size=10, color='#667eea', line=dict(color='white', width=2)),
                    fill='tozeroy',
                    fillcolor='rgba(102, 126, 234, 0.2)',
                    hovertemplate='<b>%{x}</b><br>Score: %{y:.1f}%<br>Date: %{text}<extra></extra>',
                    text=df_trend['Date']
                ))
                
                # Add target line
                fig_trend.add_hline(y=70, line_dash="dash", line_color="green", 
                                   annotation_text="Target: 70%", annotation_position="right")
                
                fig_trend.update_layout(
                    height=300,
                    yaxis=dict(range=[0, 100], title="Productivity %"),
                    xaxis_title="",
                    showlegend=False
                )
                st.plotly_chart(fig_trend, use_container_width=True)
        
        with col2:
            st.markdown("#### 😊 Emotion Distribution (Latest Session)")
            
            if emotions_data:
                emotion_counts = {}
                for emotion, confidence, timestamp in emotions_data:
                    emotion_counts[emotion] = emotion_counts.get(emotion, 0) + 1
                
                # Emoji mapping
                emoji_map = {
                    'happy': '😊', 'sad': '😢', 'angry': '😠', 
                    'surprise': '😲', 'fear': '😨', 'disgust': '🤢', 'neutral': '😐'
                }
                
                labels = [f"{emoji_map.get(e, '😐')} {e.title()}" for e in emotion_counts.keys()]
                
                fig_emotion = px.pie(
                    names=labels,
                    values=list(emotion_counts.values()),
                    hole=0.4,
                    color_discrete_sequence=px.colors.qualitative.Pastel
                )
                fig_emotion.update_traces(textposition='outside', textinfo='percent+label')
                fig_emotion.update_layout(height=300, showlegend=False)
                st.plotly_chart(fig_emotion, use_container_width=True)
            else:
                st.info("No emotion data available")
        
        st.markdown("---")
        
        # Row 2: Focus Analysis & Stress Level
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("#### 👁️ Focus Analysis (Latest Session)")
            
            if focus_data:
                focus_counts = {}
                for status, timestamp in focus_data:
                    focus_counts[status] = focus_counts.get(status, 0) + 1
                
                focused = focus_counts.get("Focused", 0)
                distracted = focus_counts.get("Distracted", 0) + focus_counts.get("Unfocused", 0)
                total = focused + distracted
                focus_pct = (focused / total * 100) if total > 0 else 0
                
                # Donut chart
                fig_focus = go.Figure(data=[go.Pie(
                    labels=['✅ Focused', '❌ Distracted'],
                    values=[focused, distracted],
                    hole=0.6,
                    marker=dict(colors=['#28a745', '#dc3545']),
                    textinfo='label+percent',
                    hovertemplate='<b>%{label}</b><br>Count: %{value}<br>%{percent}<extra></extra>'
                )])
                
                fig_focus.add_annotation(
                    text=f"<b>{focus_pct:.0f}%</b><br>Focus",
                    x=0.5, y=0.5,
                    font=dict(size=24),
                    showarrow=False
                )
                
                fig_focus.update_layout(height=300, showlegend=True, 
                                       legend=dict(orientation="h", yanchor="bottom", y=-0.1, x=0.5, xanchor="center"))
                st.plotly_chart(fig_focus, use_container_width=True)
                
                # Focus metrics
                col_f1, col_f2 = st.columns(2)
                with col_f1:
                    st.metric("✅ Focused", f"{focused} times")
                with col_f2:
                    st.metric("❌ Distracted", f"{distracted} times")
            else:
                st.info("No focus data available")
        
        with col2:
            st.markdown("#### 😰 Stress Level Analysis")
            
            if emotions_data:
                # Calculate stress
                negative_emotions = ['angry', 'sad', 'fear', 'disgust']
                stress_indicators = sum([emotion_counts.get(e, 0) for e in negative_emotions])
                total_emotions = sum(emotion_counts.values())
                stress_level = (stress_indicators / total_emotions * 100) if total_emotions > 0 else 0
                
                # Stress gauge
                fig_stress = go.Figure(go.Indicator(
                    mode="gauge+number+delta",
                    value=stress_level,
                    domain={'x': [0, 1], 'y': [0, 1]},
                    title={'text': "Stress Level", 'font': {'size': 18}},
                    number={'suffix': "%", 'font': {'size': 32}},
                    delta={'reference': 20, 'increasing': {'color': "red"}, 'decreasing': {'color': 'green'}},
                    gauge={
                        'axis': {'range': [None, 100]},
                        'bar': {'color': "darkred" if stress_level > 40 else "orange" if stress_level > 20 else "lightgreen"},
                        'steps': [
                            {'range': [0, 20], 'color': 'rgba(144, 238, 144, 0.4)'},
                            {'range': [20, 40], 'color': 'rgba(255, 215, 0, 0.4)'},
                            {'range': [40, 100], 'color': 'rgba(255, 69, 0, 0.4)'}
                        ],
                        'threshold': {'line': {'color': "black", 'width': 4}, 'value': stress_level}
                    }
                ))
                
                fig_stress.update_layout(height=300, margin=dict(l=20, r=20, t=60, b=20))
                st.plotly_chart(fig_stress, use_container_width=True)
                
                # Stress interpretation
                if stress_level < 20:
                    st.success("✅ **Low Stress** - Student is performing well!")
                elif stress_level < 40:
                    st.warning("⚠️ **Moderate Stress** - Monitor and provide support")
                else:
                    st.error("🚨 **High Stress** - Immediate attention needed!")
            else:
                st.info("No stress data available")
        
        st.markdown("---")
        
        # Row 3: Detailed Emotion Timeline & Teacher Recommendations
        col1, col2 = st.columns([2, 1])
        
        with col1:
            st.markdown("#### 📊 Emotion Timeline (Latest Session)")
            
            if emotions_data and len(emotions_data) > 1:
                # Create timeline of emotions
                emotion_timeline = []
                for i, (emotion, confidence, timestamp) in enumerate(emotions_data):
                    emotion_timeline.append({
                        'Time': i,
                        'Emotion': emotion.title(),
                        'Confidence': confidence * 100,
                        'Timestamp': timestamp
                    })
                
                df_timeline = pd.DataFrame(emotion_timeline)
                
                # Color mapping for emotions
                color_map = {
                    'Happy': '#28a745', 'Surprise': '#17a2b8',
                    'Neutral': '#6c757d', 'Sad': '#ffc107',
                    'Angry': '#dc3545', 'Fear': '#fd7e14', 'Disgust': '#e83e8c'
                }
                
                fig_timeline = px.scatter(
                    df_timeline, x='Time', y='Emotion', 
                    color='Emotion', size='Confidence',
                    color_discrete_map=color_map,
                    hover_data={'Timestamp': True, 'Confidence': ':.1f'}
                )
                
                fig_timeline.update_layout(
                    height=300,
                    xaxis_title="Detection Points",
                    yaxis_title="",
                    showlegend=False
                )
                st.plotly_chart(fig_timeline, use_container_width=True)
            else:
                st.info("Not enough emotion data to show timeline")
        
        with col2:
            st.markdown("#### 💡 Teacher Recommendations")
            
            if emotions_data and focus_data:
                st.markdown("**Based on Analysis:**")
                
                # Recommendations based on data
                if focus_pct < 60:
                    st.warning("🎯 **Focus Issue Detected**\n- Schedule 1-on-1 meeting\n- Check study environment\n- Break tasks into smaller goals")
                
                if stress_level > 40:
                    st.error("😰 **High Stress Alert**\n- Provide emotional support\n- Reduce workload if needed\n- Suggest counseling resources")
                elif stress_level > 20:
                    st.info("⚠️ **Moderate Stress**\n- Check in regularly\n- Offer study tips\n- Monitor progress closely")
                
                if focus_pct >= 80 and stress_level < 20:
                    st.success("🌟 **Excellent Performance**\n- Provide positive feedback\n- Encourage current approach\n- Consider as peer mentor")
            else:
                st.info("Complete more sessions to get recommendations")

# ==================== TAB 4: FEEDBACK HUB ====================
with tab4:
    st.markdown("### 💬 Student Feedback Center")
    
    students = get_all_students()
    
    col1, col2 = st.columns([1, 1])
    
    with col1:
        st.markdown("#### ✍️ Give Feedback")
        
        with st.form("feedback_form", clear_on_submit=True):
            student_names = [name for sid, name in students]
            selected_student_fb = st.selectbox("Select Student", student_names, key="fb_student")
            
            # Get student ID
            student_id_fb = [sid for sid, name in students if name == selected_student_fb][0]
            
            feedback_type = st.selectbox("Feedback Type", ["Positive", "Constructive", "Alert"])
            feedback_text = st.text_area("Feedback Message", placeholder="Write your feedback here...", height=150)
            
            submit_feedback = st.form_submit_button("📤 Send Feedback", use_container_width=True)
            
            if submit_feedback:
                if not feedback_text:
                    st.error("❌ Please write feedback message")
                else:
                    try:
                        add_feedback(teacher_id, student_id_fb, feedback_text, feedback_type)
                        st.success(f"✅ Feedback sent to {selected_student_fb}!")
                    except Exception as e:
                        st.error(f"⚠️ Error: {str(e)}")
    
    with col2:
        st.markdown("#### 📜 Feedback History")
        
        if students:
            view_student = st.selectbox("View feedback for", [name for sid, name in students], key="view_fb")
            view_student_id = [sid for sid, name in students if name == view_student][0]
            
            feedbacks = get_student_feedback(view_student_id)
            
            if feedbacks:
                for fb in feedbacks[:5]:
                    fb_id, teacher_id, student_id, message, fb_type, timestamp = fb
                    
                    color = "#d4edda" if fb_type == "Positive" else "#fff3cd" if fb_type == "Constructive" else "#f8d7da"
                    
                    st.markdown(f"""
                    <div style='padding: 1rem; background: {color}; border-radius: 8px; margin: 0.5rem 0;'>
                        <strong>{fb_type} Feedback</strong> - {timestamp}
                        <p style='margin: 0.5rem 0 0 0;'>{message}</p>
                    </div>
                    """, unsafe_allow_html=True)
            else:
                st.info(f"No feedback given to {view_student} yet.")

st.markdown("---")
st.caption(f"👨‍🏫 Teacher Dashboard | Logged in as {teacher_name} | Last updated: {pd.Timestamp.now().strftime('%Y-%m-%d %H:%M')}")