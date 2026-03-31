import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime
import io

# Page config
st.set_page_config(page_title="Smart Home Energy AI", layout="wide")
st.markdown("""
<style>
    .stTabs [data-baseweb="tab-list"] {gap: 8px;}
    .stTabs [data-baseweb="tab"] {border-radius: 4px; padding: 10px 20px;}
    div[data-testid="stMetricValue"] {font-size: 28px;}
</style>
""", unsafe_allow_html=True)

# Title
st.title("🏠 Smart Home Energy AI")
st.markdown("---")

# File upload - Now accepts CSV as well
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
        st.info("Please ensure your file has a column named 'consumption' with energy usage data")
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
    tab1, tab2, tab3, tab4 = st.tabs(["📊 Input Data", "📈 Analysis", "📉 Forecast", "💡 Recommendations"])
    
    with tab1:
        st.subheader("Raw Energy Data")
        col1, col2 = st.columns([2, 1])
        with col1:
            st.dataframe(df.head(15), use_container_width=True)
        with col2:
            st.metric("Total Records", len(df))
            st.metric("Date Range", f"{df['timestamp'].min().date()} to {df['timestamp'].max().date()}")
            st.metric("Consumption Column", "✅ Found")
    
    with tab2:
        col1, col2 = st.columns(2)
        with col1:
            # Bar chart - Hourly pattern
            hourly_pattern = df.groupby('hour')['consumption'].mean().reset_index()
            fig1 = px.bar(hourly_pattern, x='hour', y='consumption', 
                         title='Average Consumption by Hour', 
                         color='consumption',
                         color_continuous_scale='Viridis')
            st.plotly_chart(fig1, use_container_width=True)
            
            # Metrics row
            colm1, colm2, colm3 = st.columns(3)
            colm1.metric("Total kWh", f"{total_kwh:.0f}")
            colm2.metric("Avg kWh", f"{avg_kwh:.1f}")
            colm3.metric("Peak kWh", f"{peak_kwh:.1f} @ {peak_hour}:00")
        
        with col2:
            # Pie chart - Day distribution
            day_dist = df.groupby('day')['consumption'].sum().reset_index()
            fig2 = px.pie(day_dist, values='consumption', names='day', 
                         title='Energy Distribution by Day',
                         color_discrete_sequence=px.colors.sequential.RdBu)
            st.plotly_chart(fig2, use_container_width=True)
            
            # Gauge for efficiency
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
            # Simple forecast using moving average
            df['forecast_12h'] = df['consumption'].rolling(12, min_periods=1).mean()
            df['forecast_24h'] = df['consumption'].rolling(24, min_periods=1).mean()
            
            fig4 = go.Figure()
            fig4.add_trace(go.Scatter(x=df['timestamp'][:72], y=df['consumption'][:72], 
                                     name='Actual', mode='lines', line=dict(color='blue')))
            fig4.add_trace(go.Scatter(x=df['timestamp'][:72], y=df['forecast_12h'][:72], 
                                     name='12h Forecast', line=dict(dash='dash', color='orange')))
            fig4.update_layout(title='Energy Consumption Forecast (3 Days)',
                              xaxis_title='Timestamp',
                              yaxis_title='kWh')
            st.plotly_chart(fig4, use_container_width=True)
        
        with col2:
            st.subheader("Forecast Summary")
            next_12h_avg = df['forecast_12h'].iloc[-12:].mean() if len(df) >= 12 else avg_kwh
            next_24h_avg = df['forecast_24h'].iloc[-24:].mean() if len(df) >= 24 else avg_kwh
            
            st.metric("Next 12h Average", f"{next_12h_avg:.1f} kWh", 
                     delta=f"{((next_12h_avg/avg_kwh)-1)*100:.1f}%")
            st.metric("Next 24h Average", f"{next_24h_avg:.1f} kWh",
                     delta=f"{((next_24h_avg/avg_kwh)-1)*100:.1f}%")
            
            # Peak prediction
            st.write("**Top 3 Predicted Peak Times:**")
            peak_predictions = df.nlargest(3, 'forecast_24h')[['timestamp', 'forecast_24h']]
            peak_predictions.columns = ['Time', 'Predicted kWh']
            st.dataframe(peak_predictions, use_container_width=True)
    
    with tab4:
        st.subheader("💡 Energy Efficiency Recommendations")
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("### 📊 Performance Metrics")
            st.metric("Efficiency Score", f"{efficiency:.0f}%")
            
            # Calculate potential savings
            if peak_kwh > avg_kwh * 1.3:
                savings_potential = (peak_kwh - avg_kwh) * 0.15 * 30
                st.success(f"**💰 Potential Monthly Savings:** ${savings_potential:.2f}")
            
            # Carbon footprint
            carbon = total_kwh * 0.404  # kg CO2 per kWh (US average)
            st.info(f"**🌍 Carbon Footprint:** {carbon:.0f} kg CO2")
        
        with col2:
            st.markdown("### ⚡ Quick Recommendations")
            
            recommendations = []
            
            # Analyze patterns and generate recommendations
            if peak_hour in [17, 18, 19, 20]:
                recommendations.append("🏠 Shift high-energy activities away from evening peak hours (5-8 PM)")
            
            night_avg = df[df['hour'].between(23, 5)]['consumption'].mean() if len(df[df['hour'].between(23, 5)]) > 0 else 0
            if night_avg > avg_kwh * 0.7:
                recommendations.append("🌙 High night consumption detected - check for vampire devices and standby power")
            
            if df['consumption'].std() / df['consumption'].mean() > 0.5:
                recommendations.append("📊 High consumption variability - consider scheduling regular appliance usage")
            
            recommendations.extend([
                "💡 Replace traditional bulbs with LED alternatives (saves 75% energy)",
                "🔌 Use smart power strips for entertainment systems",
                "🌡️ Optimize thermostat settings by 2°F for heating/cooling",
                "📱 Enable power-saving modes on all devices"
            ])
            
            for i, rec in enumerate(recommendations[:5]):
                st.write(f"{i+1}. {rec}")
        
        st.markdown("---")
        st.subheader("📌 Key Conclusions & Action Items")
        
        colc1, colc2, colc3 = st.columns(3)
        
        peak_reduction = ((peak_kwh - avg_kwh) / peak_kwh * 100) if peak_kwh > 0 else 0
        with colc1:
            st.info(f"**🎯 Peak Reduction Target:** {peak_reduction:.0f}%")
            st.write("Shift 20% of peak usage to off-peak hours")
        
        with colc2:
            estimated_savings = (peak_kwh - avg_kwh) * 0.15 * 30 if peak_kwh > avg_kwh else 0
            st.info(f"**💰 Estimated Monthly Savings:** ${max(0, estimated_savings):.0f}")
            st.write("Based on $0.15/kWh average rate")
        
        with colc3:
            st.info(f"**📈 Efficiency Grade:** {'A' if efficiency > 80 else 'B' if efficiency > 60 else 'C'}")
            st.write(f"Score: {efficiency:.0f}/100")

else:
    st.info("👆 Upload your Excel or CSV file to start analysis")
    
    st.markdown("### 📋 Required File Format:")
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("""
        **Your file must have:**
        - A column named `consumption` (energy usage in kWh)
        - Optional: `timestamp` column (if missing, will be auto-generated)
        
        **Supported formats:**
        - Excel (.xlsx, .xls)
        - CSV (.csv)
        """)
    
    with col2:
        # Create sample template
        sample = pd.DataFrame({
            'timestamp': pd.date_range('2024-01-01', periods=24, freq='H'),
            'consumption': np.random.uniform(2, 8, 24).round(2)
        })
        st.write("**Sample data format:**")
        st.dataframe(sample.head(8), use_container_width=True)
        
        # Download button for template
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            sample.to_excel(writer, index=False)
        
        col1, col2 = st.columns(2)
        with col1:
            st.download_button(
                label="📥 Download Excel Template",
                data=output.getvalue(),
                file_name="energy_template.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
        with col2:
            csv_output = sample.to_csv(index=False)
            st.download_button(
                label="📥 Download CSV Template",
                data=csv_output,
                file_name="energy_template.csv",
                mime="text/csv"
            )