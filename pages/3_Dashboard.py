import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from db import (get_student_sessions, get_session_emotions, get_session_focus, 
                get_productivity_score)

st.set_page_config(page_title="Student Dashboard", layout="wide", page_icon="📊")

# --- Authentication check ---
if not st.session_state.get("login_state") or st.session_state.get("user_role") != "student":
    st.warning("⚠️ Please log in as a student first.")
    st.stop()

student_id = st.session_state["user_id"]
username = st.session_state["username"]

# Custom CSS for better visuals
st.markdown("""
<style>
    .big-metric {
        font-size: 2.5rem !important;
        font-weight: bold;
        color: #1f77b4;
    }
    .metric-label {
        font-size: 1rem;
        color: #666;
    }
</style>
""", unsafe_allow_html=True)

# Header
st.title("📊 Student Analytics Dashboard")
st.markdown(f"### Welcome back, **{username}**! 👋")
st.markdown("---")

# Get sessions
sessions = get_student_sessions(student_id)

if not sessions or len(sessions) == 0:
    st.info("🎯 **Get Started!**")
    st.markdown("""
    ### No study sessions found yet. Let's begin your learning journey!
    
    **Quick Start Guide:**
    1. 📝 Go to **Student Session** page
    2. ▶️ Click **Start Session**
    3. 📚 Study for at least 1 minute
    4. ⏹️ Click **End Session**
    5. 🔄 Return here to view your insights
    """)
    st.stop()

# ============ MAIN METRICS - BIG CARDS ============
st.markdown("### 📈 Your Study Stats at a Glance")
col1, col2, col3, col4 = st.columns(4)

total_sessions = len(sessions)
total_duration = sum([s[4] for s in sessions])
avg_duration = total_duration / total_sessions if total_sessions > 0 else 0

latest_session_id = sessions[0][0]
latest_productivity = get_productivity_score(latest_session_id) or 0

with col1:
    st.metric("📚 Total Sessions", total_sessions, delta="+1 today" if total_sessions > 0 else None)
with col2:
    st.metric("⏱️ Study Time", f"{total_duration:.0f} min", delta=f"+{sessions[0][4]:.0f} min" if len(sessions) > 0 else None)
with col3:
    st.metric("📊 Avg Duration", f"{avg_duration:.0f} min")
with col4:
    productivity_delta = latest_productivity - 70 if latest_productivity > 0 else None
    st.metric("🎯 Productivity", f"{latest_productivity:.0f}%", delta=f"{productivity_delta:.0f}%" if productivity_delta else None)

st.markdown("---")

# ============ ROW 1: STUDY TIME & PRODUCTIVITY ============
col1, col2 = st.columns(2)

with col1:
    st.markdown("### ⏰ Study Time per Session")
    
    session_df = pd.DataFrame(sessions[:10], columns=['ID', 'Student_ID', 'Start', 'End', 'Duration'])
    session_df['Session'] = [f"Session {i+1}" for i in range(len(session_df))]
    session_df = session_df.iloc[::-1]  # Reverse to show oldest first
    
    fig_duration = go.Figure()
    fig_duration.add_trace(go.Bar(
        x=session_df['Session'],
        y=session_df['Duration'],
        marker=dict(
            color=session_df['Duration'],
            colorscale='Blues',
            showscale=False,
            line=dict(color='rgb(8,48,107)', width=1.5)
        ),
        text=session_df['Duration'].apply(lambda x: f"{x:.0f} min"),
        textposition='outside',
        hovertemplate='<b>%{x}</b><br>Duration: %{y:.1f} minutes<extra></extra>'
    ))
    
    fig_duration.update_layout(
        height=350,
        xaxis_title="",
        yaxis_title="Minutes",
        plot_bgcolor='rgba(240,240,240,0.3)',
        showlegend=False,
        font=dict(size=12),
        yaxis=dict(gridcolor='lightgray')
    )
    st.plotly_chart(fig_duration, use_container_width=True)

with col2:
    st.markdown("### 📊 Productivity Score Trend")
    
    productivity_data = []
    for i, session in enumerate(sessions[:10]):
        score = get_productivity_score(session[0])
        if score is not None:
            productivity_data.append({
                'Session': f"Session {i+1}",
                'Score': score
            })
    
    if productivity_data:
        prod_df = pd.DataFrame(productivity_data).iloc[::-1]
        
        fig_prod = go.Figure()
        
        # Add line and markers
        fig_prod.add_trace(go.Scatter(
            x=prod_df['Session'],
            y=prod_df['Score'],
            mode='lines+markers',
            name='Productivity',
            line=dict(color='#FF6B6B', width=4),
            marker=dict(size=12, color='#FF6B6B', line=dict(color='white', width=2)),
            fill='tozeroy',
            fillcolor='rgba(255, 107, 107, 0.2)',
            hovertemplate='<b>%{x}</b><br>Score: %{y:.0f}%<extra></extra>'
        ))
        
        # Add target line
        fig_prod.add_hline(
            y=70, 
            line_dash="dash", 
            line_color="green", 
            line_width=2,
            annotation_text="🎯 Target: 70%", 
            annotation_position="right"
        )
        
        fig_prod.update_layout(
            height=350,
            xaxis_title="",
            yaxis_title="Score (%)",
            yaxis=dict(range=[0, 100], gridcolor='lightgray'),
            plot_bgcolor='rgba(240,240,240,0.3)',
            showlegend=False,
            font=dict(size=12)
        )
        st.plotly_chart(fig_prod, use_container_width=True)
    else:
        st.info("📊 Complete more sessions to see productivity trends!")

st.markdown("---")

# ============ ROW 2: EMOTIONS & STRESS ============
st.markdown("### 🎭 Emotional State Analysis")
col1, col2 = st.columns(2)

emotions_data = get_session_emotions(latest_session_id)

with col1:
    st.markdown("#### 😊 Emotion Distribution (Latest Session)")
    
    if emotions_data and len(emotions_data) > 0:
        emotion_counts = {}
        for emotion, confidence, timestamp in emotions_data:
            emotion_counts[emotion] = emotion_counts.get(emotion, 0) + 1
        
        emotion_df = pd.DataFrame(list(emotion_counts.items()), columns=['Emotion', 'Count'])
        
        # Emoji mapping for emotions
        emoji_map = {
            'happy': '😊', 'sad': '😢', 'angry': '😠', 
            'surprise': '😲', 'fear': '😨', 'disgust': '🤢', 'neutral': '😐'
        }
        emotion_df['Label'] = emotion_df['Emotion'].apply(lambda x: f"{emoji_map.get(x, '😐')} {x.title()}")
        
        fig_emotion = px.pie(
            emotion_df,
            values='Count',
            names='Label',
            hole=0.4,
            color_discrete_sequence=px.colors.qualitative.Pastel
        )
        
        fig_emotion.update_traces(
            textposition='outside',
            textinfo='percent+label',
            textfont_size=14,
            marker=dict(line=dict(color='white', width=2))
        )
        
        fig_emotion.update_layout(
            height=350,
            showlegend=False,
            font=dict(size=13)
        )
        st.plotly_chart(fig_emotion, use_container_width=True)
    else:
        st.warning("😕 No emotion data available for this session")

with col2:
    st.markdown("#### 😰 Stress Level Indicator")
    
    if emotions_data and len(emotions_data) > 0:
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
            title={'text': "Current Stress Level", 'font': {'size': 18}},
            number={'suffix': "%", 'font': {'size': 32, 'color': 'black'}},
            delta={'reference': 20, 'increasing': {'color': "red"}, 'decreasing': {'color': 'green'}},
            gauge={
                'axis': {'range': [None, 100], 'tickwidth': 2, 'tickcolor': "darkblue"},
                'bar': {'color': "darkred" if stress_level > 40 else "orange" if stress_level > 20 else "lightgreen", 'thickness': 0.8},
                'bgcolor': "white",
                'borderwidth': 3,
                'bordercolor': "gray",
                'steps': [
                    {'range': [0, 20], 'color': 'rgba(144, 238, 144, 0.4)', 'name': 'Low'},
                    {'range': [20, 40], 'color': 'rgba(255, 215, 0, 0.4)', 'name': 'Moderate'},
                    {'range': [40, 100], 'color': 'rgba(255, 69, 0, 0.4)', 'name': 'High'}
                ],
                'threshold': {
                    'line': {'color': "black", 'width': 4},
                    'thickness': 0.8,
                    'value': stress_level
                }
            }
        ))
        
        fig_stress.update_layout(
            height=350,
            margin=dict(l=20, r=20, t=60, b=20)
        )
        st.plotly_chart(fig_stress, use_container_width=True)
        
        # Stress interpretation
        if stress_level < 20:
            st.success("✅ **Low Stress** - You're doing great! Keep it up! 😌")
        elif stress_level < 40:
            st.warning("⚠️ **Moderate Stress** - Take short breaks to stay refreshed 😐")
        else:
            st.error("🚨 **High Stress** - Consider taking a longer break or trying relaxation techniques 😰")
    else:
        st.info("No stress data available")

st.markdown("---")

# ============ ROW 3: FOCUS ANALYSIS ============
st.markdown("### 👁️ Focus & Attention Analysis")
col1, col2 = st.columns([1, 1])

focus_data = get_session_focus(latest_session_id)

with col1:
    st.markdown("#### Focus Status Distribution")
    
    if focus_data and len(focus_data) > 0:
        focus_counts = {}
        for status, timestamp in focus_data:
            focus_counts[status] = focus_counts.get(status, 0) + 1
        
        # Check for both "Unfocused" and "Distracted" (backward compatibility)
        focused = focus_counts.get("Focused", 0)
        unfocused = focus_counts.get("Unfocused", 0) + focus_counts.get("Distracted", 0)
        total = focused + unfocused
        focus_pct = (focused / total * 100) if total > 0 else 0
        
        # Debug: Show actual counts
        st.caption(f"Debug: Focused={focused}, Distracted={unfocused}, Total={total}")
        
        # Create donut chart
        fig_focus = go.Figure(data=[go.Pie(
            labels=['✅ Focused', '❌ Distracted'],
            values=[focused, unfocused],
            hole=0.6,
            marker=dict(
                colors=['#28a745', '#dc3545'],
                line=dict(color='white', width=3)
            ),
            textinfo='label+percent',
            textfont=dict(size=16, color='white'),
            hovertemplate='<b>%{label}</b><br>Count: %{value}<br>Percentage: %{percent}<extra></extra>'
        )])
        
        # Add center annotation
        fig_focus.add_annotation(
            text=f"<b>{focus_pct:.0f}%</b><br>Focus<br>Score",
            x=0.5, y=0.5,
            font=dict(size=24, color='#333'),
            showarrow=False,
            align='center'
        )
        
        fig_focus.update_layout(
            height=350,
            showlegend=True,
            legend=dict(
                orientation="h", 
                yanchor="bottom", 
                y=-0.1, 
                xanchor="center", 
                x=0.5,
                font=dict(size=14)
            ),
            margin=dict(l=20, r=20, t=20, b=60)
        )
        st.plotly_chart(fig_focus, use_container_width=True)
        
        # Focus metrics
        col_f1, col_f2 = st.columns(2)
        with col_f1:
            st.metric("✅ Focused", f"{focused} times", f"{focus_pct:.1f}%")
        with col_f2:
            st.metric("❌ Distracted", f"{unfocused} times", f"{100-focus_pct:.1f}%")
    else:
        st.warning("No focus data available")

with col2:
    st.markdown("#### 🤖 AI-Powered Insights")
    
    if focus_data and len(focus_data) > 0:
        # AI Analysis based on data
        st.markdown("**📊 Performance Analysis:**")
        
        # Focus Rating
        if focus_pct >= 80:
            st.success("🌟 **Excellent Focus!** You maintained great concentration throughout the session.")
            feedback_color = "success"
        elif focus_pct >= 60:
            st.info("👍 **Good Focus!** You're doing well, but there's room for improvement.")
            feedback_color = "info"
        elif focus_pct >= 40:
            st.warning("⚠️ **Moderate Focus** - Try to minimize distractions during your next session.")
            feedback_color = "warning"
        else:
            st.error("🚨 **Low Focus** - Consider changing your study environment or taking more breaks.")
            feedback_color = "error"
        
        st.markdown("---")
        
        # AI Recommendations
        st.markdown("**💡 AI Recommendations:**")
        
        if focus_pct < 60:
            st.markdown("""
            - 🔕 **Turn off notifications** on your devices
            - 🪑 **Find a quiet study space** away from distractions
            - ⏱️ **Use Pomodoro technique**: 25 min work, 5 min break
            - 📱 **Keep phone in another room** during study time
            """)
        elif focus_pct < 80:
            st.markdown("""
            - ✅ **Good progress!** Keep maintaining this routine
            - 🎯 **Set specific goals** for each study session
            - 💪 **Challenge yourself** to reach 80% focus
            - 🧘 **Practice mindfulness** before studying
            """)
        else:
            st.markdown("""
            - 🏆 **Outstanding performance!** You're in the zone!
            - 📈 **Maintain this momentum** in future sessions
            - 🎓 **Share your study techniques** with others
            - ⭐ **You're a role model** for focused learning
            """)
        
        st.markdown("---")
        
        # Pattern Detection
        st.markdown("**🔍 Pattern Detection:**")
        distraction_rate = (unfocused / total * 100) if total > 0 else 0
        
        if distraction_rate > 50:
            st.warning(f"⚠️ High distraction rate detected ({distraction_rate:.0f}%). Consider shorter study intervals.")
        elif distraction_rate > 30:
            st.info(f"ℹ️ Moderate distractions ({distraction_rate:.0f}%). You're on the right track!")
        else:
            st.success(f"✅ Low distraction rate ({distraction_rate:.0f}%). Excellent self-control!")
    else:
        st.info("Complete a session to receive AI-powered insights and recommendations!")

st.markdown("---")

# ============ SUMMARY SECTION ============
st.markdown("### 📊 Session Summary")
col1, col2, col3, col4 = st.columns(4)

if emotions_data:
    with col1:
        most_emotion = max(emotion_counts, key=emotion_counts.get)
        emoji = emoji_map.get(most_emotion, '😐')
        st.markdown(f"""
        <div style='text-align: center; padding: 15px; background: #f0f8ff; border-radius: 10px;'>
            <div style='font-size: 2.5rem;'>{emoji}</div>
            <div style='font-size: 1.1rem; font-weight: bold; margin-top: 5px;'>Dominant Emotion</div>
            <div style='font-size: 1rem; color: #666;'>{most_emotion.title()}</div>
        </div>
        """, unsafe_allow_html=True)
    
    with col2:
        st.markdown(f"""
        <div style='text-align: center; padding: 15px; background: #fff0f5; border-radius: 10px;'>
            <div style='font-size: 2.5rem;'>😰</div>
            <div style='font-size: 1.1rem; font-weight: bold; margin-top: 5px;'>Stress Level</div>
            <div style='font-size: 1rem; color: #666;'>{stress_level:.0f}%</div>
        </div>
        """, unsafe_allow_html=True)
    
    with col3:
        if focus_data:
            st.markdown(f"""
            <div style='text-align: center; padding: 15px; background: #f0fff0; border-radius: 10px;'>
                <div style='font-size: 2.5rem;'>👁️</div>
                <div style='font-size: 1.1rem; font-weight: bold; margin-top: 5px;'>Focus Score</div>
                <div style='font-size: 1rem; color: #666;'>{focus_pct:.0f}%</div>
            </div>
            """, unsafe_allow_html=True)
    
    with col4:
        st.markdown(f"""
        <div style='text-align: center; padding: 15px; background: #fffacd; border-radius: 10px;'>
            <div style='font-size: 2.5rem;'>🎯</div>
            <div style='font-size: 1.1rem; font-weight: bold; margin-top: 5px;'>Productivity</div>
            <div style='font-size: 1rem; color: #666;'>{latest_productivity:.0f}%</div>
        </div>
        """, unsafe_allow_html=True)

st.markdown("---")

# ============ TIPS SECTION ============
st.markdown("### 💡 Personalized Study Tips")
col1, col2, col3 = st.columns(3)

with col1:
    st.markdown("""
    <div style='padding: 20px; background: linear-gradient(135deg, #a8edea 0%, #fed6e3 100%); border-radius: 15px; height: 180px;'>
        <h3 style='margin-top: 0;'>🎯 Stay Focused</h3>
        <p>Keep your study area clean and minimize distractions. Turn off notifications!</p>
    </div>
    """, unsafe_allow_html=True)

with col2:
    st.markdown("""
    <div style='padding: 20px; background: linear-gradient(135deg, #ffecd2 0%, #fcb69f 100%); border-radius: 15px; height: 180px;'>
        <h3 style='margin-top: 0;'>😌 Manage Stress</h3>
        <p>Take 5-minute breaks every 25 minutes. Practice deep breathing when stressed.</p>
    </div>
    """, unsafe_allow_html=True)

with col3:
    st.markdown("""
    <div style='padding: 20px; background: linear-gradient(135deg, #a1c4fd 0%, #c2e9fb 100%); border-radius: 15px; height: 180px;'>
        <h3 style='margin-top: 0;'>📚 Stay Consistent</h3>
        <p>Study at the same time daily. Consistency builds better learning habits!</p>
    </div>
    """, unsafe_allow_html=True)

st.markdown("---")
st.caption("📊 Dashboard updates automatically after each session | Last updated: " + str(pd.Timestamp.now().strftime('%Y-%m-%d %H:%M')))