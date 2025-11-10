import streamlit as st
import pandas as pd
from datetime import datetime
from db import get_student_tasks, update_task_status, get_student_feedback

st.set_page_config(page_title="My Tasks", layout="wide", page_icon="📋")

# --- Authentication check ---
if not st.session_state.get("login_state") or st.session_state.get("user_role") != "student":
    st.warning("⚠️ Please log in as a student first.")
    st.stop()

student_id = st.session_state["user_id"]
username = st.session_state["username"]

# Custom CSS
st.markdown("""
<style>
    .task-card {
        padding: 1.5rem;
        background: white;
        border-radius: 10px;
        border-left: 5px solid #667eea;
        margin: 1rem 0;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
    }
    .task-card-high {
        border-left-color: #dc3545;
    }
    .task-card-medium {
        border-left-color: #ffc107;
    }
    .task-card-low {
        border-left-color: #28a745;
    }
    .task-card-completed {
        opacity: 0.6;
        border-left-color: #6c757d;
    }
    .feedback-card {
        padding: 1rem;
        background: #f8f9fa;
        border-radius: 8px;
        margin: 0.5rem 0;
        border-left: 4px solid #17a2b8;
    }
    .feedback-positive {
        background: #d4edda;
        border-left-color: #28a745;
    }
    .feedback-constructive {
        background: #fff3cd;
        border-left-color: #ffc107;
    }
    .feedback-alert {
        background: #f8d7da;
        border-left-color: #dc3545;
    }
</style>
""", unsafe_allow_html=True)

# Header
st.title("📋 My Tasks & Assignments")
st.markdown(f"### Welcome, **{username}**! 🎯")
st.markdown("---")

# Tabs
tab1, tab2 = st.tabs(["📝 My Tasks", "💬 Teacher Feedback"])

# ==================== TAB 1: TASKS ====================
with tab1:
    tasks = get_student_tasks(student_id)
    
    if not tasks:
        st.info("📚 No tasks assigned yet. Check back later!")
        st.markdown("""
        ### What to do while waiting:
        - 📹 Complete study sessions to build your productivity score
        - 📊 Check your dashboard for performance insights
        - 🎯 Set personal learning goals
        """)
    else:
        # Task statistics
        col1, col2, col3, col4 = st.columns(4)
        
        total_tasks = len(tasks)
        pending_tasks = len([t for t in tasks if t[6] == 'Pending'])
        completed_tasks = len([t for t in tasks if t[6] == 'Completed'])
        
        # Count overdue tasks
        overdue = 0
        today = datetime.now().date()
        for task in tasks:
            if task[6] == 'Pending':
                try:
                    due_date = datetime.strptime(task[5], "%Y-%m-%d").date()
                    if due_date < today:
                        overdue += 1
                except:
                    pass
        
        with col1:
            st.metric("📚 Total Tasks", total_tasks)
        with col2:
            st.metric("⏳ Pending", pending_tasks, delta=f"-{completed_tasks}" if completed_tasks > 0 else None)
        with col3:
            st.metric("✅ Completed", completed_tasks)
        with col4:
            if overdue > 0:
                st.metric("⚠️ Overdue", overdue, delta=f"{overdue}", delta_color="inverse")
            else:
                st.metric("🎉 Overdue", 0)
        
        st.markdown("---")
        
        # Filter options
        col_filter1, col_filter2 = st.columns([1, 3])
        
        with col_filter1:
            filter_status = st.selectbox("Filter by Status", ["All", "Pending", "Completed"])
        
        with col_filter2:
            filter_priority = st.multiselect("Filter by Priority", ["High", "Medium", "Low"], default=["High", "Medium", "Low"])
        
        st.markdown("---")
        
        # Display tasks
        filtered_tasks = []
        for task in tasks:
            if filter_status != "All" and task[6] != filter_status:
                continue
            if task[7] not in filter_priority:
                continue
            filtered_tasks.append(task)
        
        if not filtered_tasks:
            st.info("📭 No tasks match your filters.")
        else:
            for task in filtered_tasks:
                task_id, teacher_id, student_id, title, description, due_date, status, priority, created_at = task
                
                # Calculate if overdue
                is_overdue = False
                due_date_obj = None
                try:
                    due_date_obj = datetime.strptime(due_date, "%Y-%m-%d").date()
                    if status == "Pending" and due_date_obj < today:
                        is_overdue = True
                except:
                    pass
                
                # Card styling based on priority and status
                card_class = "task-card"
                if status == "Completed":
                    card_class += " task-card-completed"
                elif priority == "High":
                    card_class += " task-card-high"
                elif priority == "Medium":
                    card_class += " task-card-medium"
                else:
                    card_class += " task-card-low"
                
                # Priority emoji
                priority_emoji = "🔴" if priority == "High" else "🟡" if priority == "Medium" else "🟢"
                
                # Status emoji
                status_emoji = "✅" if status == "Completed" else "⏳"
                
                # Create task card using columns for better layout
                with st.container():
                    st.markdown(f"""
                    <div class="{card_class}">
                        <div style="display: flex; justify-content: space-between; align-items: start;">
                            <div style="flex: 1;">
                                <h3 style="margin: 0 0 0.5rem 0;">{priority_emoji} {title}</h3>
                                <p style="margin: 0; color: #666;">{description}</p>
                            </div>
                            <div style="text-align: right; margin-left: 1rem;">
                                <span style="background: {'#28a745' if status == 'Completed' else '#ffc107'}; color: white; padding: 0.25rem 0.75rem; border-radius: 15px; font-size: 0.85rem;">
                                    {status_emoji} {status}
                                </span>
                            </div>
                        </div>
                        <div style="margin-top: 1rem;">
                            <span style="color: #666;">📅 Due: <strong>{due_date}</strong></span>
                            {'<span style="color: red; font-weight: bold; margin-left: 0.5rem;">⚠️ OVERDUE!</span>' if is_overdue else ''}
                            <br>
                            <span style="color: #666;">🔖 Priority: <strong>{priority}</strong></span>
                        </div>
                    </div>
                    """, unsafe_allow_html=True)
                    
                    # Action buttons
                    if status == "Pending":
                        col_btn1, col_btn2, col_btn3 = st.columns([1, 1, 4])
                        with col_btn1:
                            if st.button("✅ Mark Complete", key=f"complete_{task_id}"):
                                update_task_status(task_id, "Completed")
                                st.success("🎉 Task marked as completed!")
                                st.rerun()
                        with col_btn2:
                            with st.expander("ℹ️ Details"):
                                st.write(f"**Created:** {created_at}")
                                st.write(f"**Task ID:** {task_id}")
                    else:
                        col_btn1, col_btn2 = st.columns([1, 5])
                        with col_btn1:
                            if st.button("↩️ Reopen", key=f"reopen_{task_id}"):
                                update_task_status(task_id, "Pending")
                                st.info("Task reopened!")
                                st.rerun()

# ==================== TAB 2: FEEDBACK ====================
with tab2:
    st.markdown("### 💬 Feedback from Your Teachers")
    
    feedbacks = get_student_feedback(student_id)
    
    if not feedbacks:
        st.info("📭 No feedback yet. Keep up the good work and check back later!")
        st.markdown("""
        ### Tips to receive feedback:
        - ✅ Complete assigned tasks on time
        - 📚 Maintain consistent study sessions
        - 📊 Keep your productivity score above 70%
        - 🎯 Show improvement in your performance
        """)
    else:
        # Feedback statistics
        col1, col2, col3 = st.columns(3)
        
        positive_count = len([f for f in feedbacks if f[4] == "Positive"])
        constructive_count = len([f for f in feedbacks if f[4] == "Constructive"])
        alert_count = len([f for f in feedbacks if f[4] == "Alert"])
        
        with col1:
            st.metric("😊 Positive", positive_count)
        with col2:
            st.metric("💡 Constructive", constructive_count)
        with col3:
            st.metric("⚠️ Alerts", alert_count)
        
        st.markdown("---")
        
        # Display feedback
        for feedback in feedbacks:
            fb_id, teacher_id, student_id, message, fb_type, timestamp = feedback
            
            # Card styling
            card_class = "feedback-card"
            if fb_type == "Positive":
                card_class += " feedback-positive"
                icon = "😊"
            elif fb_type == "Constructive":
                card_class += " feedback-constructive"
                icon = "💡"
            else:  # Alert
                card_class += " feedback-alert"
                icon = "⚠️"
            
            st.markdown(f"""
            <div class="{card_class}">
                <div style="display: flex; justify-content: space-between; align-items: start;">
                    <div style="flex: 1;">
                        <strong>{icon} {fb_type} Feedback</strong>
                        <p style="margin: 0.5rem 0 0 0; font-size: 1rem;">{message}</p>
                    </div>
                </div>
                <div style="margin-top: 0.5rem; color: #666; font-size: 0.85rem;">
                    📅 {timestamp}
                </div>
            </div>
            """, unsafe_allow_html=True)
            
            st.markdown("")  # Spacing

st.markdown("---")
st.caption(f"📋 My Tasks | {username} | Last updated: {pd.Timestamp.now().strftime('%Y-%m-%d %H:%M')}")