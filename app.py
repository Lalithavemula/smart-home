import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime
import io
import os
from dotenv import load_dotenv
import requests

# Load API key from .env file (NOT hardcoded!)
load_dotenv()
GROQ_API_KEY = os.getenv('GROQ_API_KEY')

# Page config
st.set_page_config(page_title="Smart Home Energy AI", layout="wide")
st.markdown("""
<style>
    .stTabs [data-baseweb="tab-list"] {gap: 8px;}
    .stTabs [data-baseweb="tab"] {border-radius: 4px; padding: 10px 20px;}
    div[data-testid="stMetricValue"] {font-size: 28px;}
</style>
""", unsafe_allow_html=True)

# Function to query Groq API
def query_groq(prompt):
    """Query Groq API for AI insights"""
    if not GROQ_API_KEY or GROQ_API_KEY == "your_groq_api_key_here":
        return "⚠️ Please add your Groq API key to the .env file"
    
    try:
        headers = {
            "Authorization": f"Bearer {GROQ_API_KEY}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "model": "llama3-70b-8192",
            "messages": [
                {
                    "role": "system",
                    "content": "You are an energy efficiency expert. Provide concise, actionable advice."
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            "temperature": 0.7,
            "max_tokens": 500
        }
        
        response = requests.post(
            "https://api.groq.com/openai/v1/chat/completions",
            headers=headers,
            json=payload,
            timeout=30
        )
        
        if response.status_code == 200:
            return response.json()['choices'][0]['message']['content']
        else:
            return f"API Error: {response.status_code}"
            
    except Exception as e:
        return f"Error: {str(e)}"

# Title
st.title("🏠 Smart Home Energy AI")
st.markdown("---")

# File upload
uploaded_file = st.file_uploader("Upload Energy Consumption File", type=['xlsx', 'xls', 'csv'])

if uploaded_file:
    # Process data based on file type
    if uploaded_file.name.endswith('.csv'):
        df = pd.read_csv(uploaded_file)
        st.success(f"✅ Loaded CSV file: {uploaded_file.name}")
    else:
        df = pd.read_excel(uploaded_file)
        st.success(f"✅ Loaded Excel file: {uploaded_file.name}")
    
    # Check if consumption column exists
    if 'consumption' not in df.columns:
        st.error("❌ File must contain a 'consumption' column")
        st.stop()
    
    # Add timestamp if not present
    if 'timestamp' not in df.columns:
        df['timestamp'] = pd.date_range(start='2024-01-01', periods=len(df), freq='H')[:len(df)]
    
    # Convert timestamp to datetime
    df['timestamp'] = pd.to_datetime(df['timestamp'])
    df['hour'] = df['timestamp'].dt.hour
    df['day'] = df['timestamp'].dt.day_name()
    
    # Metrics
    total_kwh = df['consumption'].sum()
    avg_kwh = df['consumption'].mean()
    peak_kwh = df['consumption'].max()
    peak_hour = df.loc[df['consumption'].idxmax(), 'hour']
    efficiency = min(100, max(0, (1 - df['consumption'].std()/df['consumption'].mean()) * 100))
    
    # Tabs
    tab1, tab2, tab3, tab4 = st.tabs(["📊 Input Data", "📈 Analysis", "📉 Forecast", "💡 AI Recommendations"])
    
    with tab1:
        st.subheader("Raw Energy Data")
        col1, col2 = st.columns([2, 1])
        with col1:
            st.dataframe(df.head(15), use_container_width=True)
        with col2:
            st.metric("Total Records", len(df))
            st.metric("Date Range", f"{df['timestamp'].min().date()} to {df['timestamp'].max().date()}")
    
    with tab2:
        col1, col2 = st.columns(2)
        with col1:
            hourly_pattern = df.groupby('hour')['consumption'].mean().reset_index()
            fig1 = px.bar(hourly_pattern, x='hour', y='consumption', 
                         title='Average Consumption by Hour', 
                         color='consumption',
                         color_continuous_scale='Viridis')
            st.plotly_chart(fig1, use_container_width=True)
            
            colm1, colm2, colm3 = st.columns(3)
            colm1.metric("Total kWh", f"{total_kwh:.0f}")
            colm2.metric("Avg kWh", f"{avg_kwh:.1f}")
            colm3.metric("Peak kWh", f"{peak_kwh:.1f} @ {peak_hour}:00")
        
        with col2:
            day_dist = df.groupby('day')['consumption'].sum().reset_index()
            fig2 = px.pie(day_dist, values='consumption', names='day', 
                         title='Energy Distribution by Day')
            st.plotly_chart(fig2, use_container_width=True)
            
            fig3 = go.Figure(go.Indicator(
                mode="gauge+number",
                value=efficiency,
                title={'text': "Efficiency Score (%)"},
                gauge={
                    'axis': {'range': [0, 100]},
                    'bar': {'color': "darkgreen"},
                    'steps': [
                        {'range': [0, 50], 'color': "red"},
                        {'range': [50, 75], 'color': "yellow"},
                        {'range': [75, 100], 'color': "lightgreen"}
                    ]
                }
            ))
            fig3.update_layout(height=250)
            st.plotly_chart(fig3, use_container_width=True)
    
    with tab3:
        col1, col2 = st.columns(2)
        with col1:
            df['forecast_12h'] = df['consumption'].rolling(12, min_periods=1).mean()
            
            fig4 = go.Figure()
            fig4.add_trace(go.Scatter(x=df['timestamp'][:72], y=df['consumption'][:72], 
                                     name='Actual', mode='lines', line=dict(color='blue')))
            fig4.add_trace(go.Scatter(x=df['timestamp'][:72], y=df['forecast_12h'][:72], 
                                     name='Forecast', line=dict(dash='dash', color='orange')))
            fig4.update_layout(title='Energy Consumption Forecast (3 Days)')
            st.plotly_chart(fig4, use_container_width=True)
        
        with col2:
            st.subheader("Forecast Summary")
            next_12h_avg = df['forecast_12h'].iloc[-12:].mean() if len(df) >= 12 else avg_kwh
            st.metric("Next 12h Average", f"{next_12h_avg:.1f} kWh")
    
    with tab4:
        st.subheader("🤖 AI-Powered Energy Insights")
        
        data_summary = f"Total: {total_kwh:.0f} kWh, Avg: {avg_kwh:.1f} kWh, Peak: {peak_kwh:.1f} kWh, Efficiency: {efficiency:.0f}%"
        
        col1, col2 = st.columns(2)
        
        with col1:
            if st.button("⚡ Get Efficiency Tips", use_container_width=True):
                with st.spinner("Generating recommendations..."):
                    response = query_groq(f"Based on: {data_summary}. Give 5 energy saving tips.")
                    st.info(response)
        
        with col2:
            if st.button("💰 Cost Savings Analysis", use_container_width=True):
                with st.spinner("Analyzing savings..."):
                    response = query_groq(f"Based on: {data_summary}. Calculate potential savings.")
                    st.success(response)

else:
    st.info("👆 Upload your Excel or CSV file to start analysis")
    
    sample = pd.DataFrame({
        'timestamp': pd.date_range('2024-01-01', periods=24, freq='H'),
        'consumption': np.random.uniform(2, 8, 24).round(2)
    })
    
    st.write("**Sample data format:**")
    st.dataframe(sample.head(8), use_container_width=True)
    
    csv_output = sample.to_csv(index=False)
    st.download_button("📥 Download CSV Template", csv_output, "energy_template.csv", "text/csv")
