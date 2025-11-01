"""
Streamlit UI for Network Utilization Agent
"""
import streamlit as st
import pandas as pd
from datetime import datetime
import os
from dotenv import load_dotenv
from src.agent import NetworkUtilizationAgent
from config.settings import UTILIZATION_THRESHOLD, COLOR_OVERUTILIZED, COLOR_UNDERUTILIZED
from src.agent import NetworkUtilizationAgent

# Load environment variables
load_dotenv()

# Page configuration
st.set_page_config(
    page_title="Network Utilization Agent",
    page_icon="🏭",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS
st.markdown("""
<style>
    .main-header {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 2rem;
        border-radius: 10px;
        color: white;
        text-align: center;
        margin-bottom: 2rem;
    }
    .metric-card {
        background-color: #f8f9fa;
        padding: 1.5rem;
        border-radius: 10px;
        border-left: 4px solid #667eea;
        margin: 1rem 0;
    }
    .success-box {
        background-color: #d4edda;
        border-left: 4px solid #28a745;
        padding: 1rem;
        border-radius: 5px;
        margin: 1rem 0;
    }
    .warning-box {
        background-color: #fff3cd;
        border-left: 4px solid #ffc107;
        padding: 1rem;
        border-radius: 5px;
        margin: 1rem 0;
    }
    .error-box {
        background-color: #f8d7da;
        border-left: 4px solid #dc3545;
        padding: 1rem;
        border-radius: 5px;
        margin: 1rem 0;
    }
</style>
""", unsafe_allow_html=True)

# Header
st.markdown("""
<div class="main-header">
    <h1>🏭 Network Utilization Agent</h1>
    <p>AI-Powered Warehouse Optimization & Utilization Monitoring</p>
</div>
""", unsafe_allow_html=True)

# Sidebar
with st.sidebar:
    st.image("https://img.icons8.com/clouds/200/warehouse.png", width=150)
    st.title("⚙️ Configuration")
    
    # API Key input
    openai_api_key = st.text_input(
        "OpenAI API Key",
        type="password",
        value=os.getenv("OPENAI_API_KEY", ""),
        help="Enter your OpenAI API key"
    )
    
    st.divider()
    
    # Email configuration
    st.subheader("📧 Email Settings")
    sender_email = st.text_input(
        "Sender Email",
        value=os.getenv("SENDER_EMAIL", "alshangrillfood@gmail.com"),
        help="Gmail address for sending reports"
    )
    
    st.info("📄 Make sure `client_secret.json` is in the project root folder")
    
    if os.path.exists("client_secret.json"):
        st.success("✅ client_secret.json found!")
    else:
        st.warning("⚠️ client_secret.json not found. Please add it to enable email sending.")
    
    if os.path.exists("token.json"):
        st.success("✅ Gmail authenticated")
    else:
        st.info("ℹ️ First email send will open browser for Gmail authentication")
    
    st.divider()
    
    st.subheader("📊 Threshold Settings")
    threshold = st.slider(
        "Utilization Threshold (%)",
        min_value=70,
        max_value=95,
        value=int(UTILIZATION_THRESHOLD),
        help="Target utilization percentage"
    )
    
    st.info(f"Current threshold: **{threshold}%**")
    
    st.divider()
    
    st.caption("Made with ❤️ using LangGraph")

# Main content
tab1, tab2, tab3, tab4 = st.tabs(["📤 Upload Data", "🔍 Analysis", "📧 Email Preview", "📊 Dashboard"])

with tab1:
    st.header("📤 Upload Warehouse Data")
    
    col1, col2 = st.columns([2, 1])
    
    with col1:
        uploaded_file = st.file_uploader(
            "Upload Excel file with warehouse data",
            type=['xlsx', 'xls'],
            help="Upload your warehouse inventory Excel file"
        )
        
        if uploaded_file:
            # Save uploaded file temporarily
            temp_path = f"temp_{uploaded_file.name}"
            with open(temp_path, "wb") as f:
                f.write(uploaded_file.getbuffer())
            
            # Load and display data
            df = pd.read_excel(temp_path)
            
            st.success(f"✅ Loaded {len(df)} warehouses from {uploaded_file.name}")
            
            # Display data preview
            st.subheader("📋 Data Preview")
            st.dataframe(df.head(10), use_container_width=True)
            
            # Store in session state
            st.session_state['excel_path'] = temp_path
            st.session_state['data_loaded'] = True
    
    with col2:
        st.info("""
        **Required Columns:**
        - Warehouse_ID
        - Warehouse_Name
        - Region
        - Total_Capacity_Pallets
        - Current_Pallets
        - Branch_Manager_Name
        - Branch_Manager_Email
        - Utilization_Percentage
        """)
        
        if uploaded_file:
            st.metric("Total Warehouses", len(df))
            st.metric("Regions", df['Region'].nunique())

with tab2:
    st.header("🔍 Utilization Analysis")
    
    if st.session_state.get('data_loaded'):
        col1, col2 = st.columns([3, 1])
        
        with col2:
            if st.button("▶️ Run Agent", type="primary", use_container_width=True):
                if not openai_api_key:
                    st.error("❌ Please provide OpenAI API Key in the sidebar")
                elif not sender_email:
                    st.error("❌ Please provide Sender Email in the sidebar")
                elif not os.path.exists("client_secret.json"):
                    st.error("❌ client_secret.json not found in project root")
                else:
                    with st.spinner("🤖 Agent is analyzing and sending emails..."):
                        progress_text = st.empty()
                        
                        try:
                            progress_text.text("📊 Step 1/5: Monitoring warehouse data...")
                            
                            # Initialize and run agent
                            agent = NetworkUtilizationAgent(
                                openai_api_key=openai_api_key,
                                excel_path=st.session_state['excel_path'],
                                sender_email=sender_email,
                                client_secret_path="client_secret.json"
                            )
                            
                            progress_text.text("🔍 Step 2/5: Detecting utilization issues...")
                            progress_text.text("🧠 Step 3/5: Analyzing and generating recommendations...")
                            progress_text.text("📧 Step 4/5: Generating emails...")
                            progress_text.text("📤 Step 5/5: Sending emails automatically...")
                            
                            result = agent.run()
                            st.session_state['analysis_result'] = result
                            st.session_state['agent'] = agent
                            
                            progress_text.empty()
                            
                            st.success("✅ Agent completed all tasks successfully!")
                            
                            # Show email sending results
                            if result.get('emails_sent'):
                                st.balloons()
                                st.markdown("### 📧 Email Delivery Report")
                                
                                for email in result['emails_sent']:
                                    if email.get('success'):
                                        st.success(f"✅ Email sent to **{email['manager_email']}** ({email['region']}) at {email['timestamp']}")
                                    else:
                                        error_msg = email.get('error', 'Unknown error')
                                        st.error(f"❌ Failed to send to **{email['manager_email']}** ({email['region']}): {error_msg}")
                            
                        except Exception as e:
                            progress_text.empty()
                            st.error(f"❌ Error: {str(e)}")
        
        # Display results
        if st.session_state.get('analysis_result'):
            result = st.session_state['analysis_result']
            
            # Status
            st.markdown(f"""
            <div class="success-box">
                <strong>Status:</strong> {result.get('status', 'Unknown')}
            </div>
            """, unsafe_allow_html=True)
            
            # Metrics
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                st.metric(
                    "Total Warehouses",
                    len(result.get('warehouse_data', []))
                )
            
            with col2:
                st.metric(
                    "Over-Utilized",
                    len(result.get('overutilized_warehouses', [])),
                    delta=f"Above {threshold}%",
                    delta_color="inverse"
                )
            
            with col3:
                st.metric(
                    "Under-Utilized",
                    len(result.get('underutilized_warehouses', [])),
                    delta=f"Below {threshold}%",
                    delta_color="normal"
                )
            
            with col4:
                st.metric(
                    "Recommendations",
                    len(result.get('recommendations', []))
                )
            
            # Display recommendations
            if result.get('recommendations'):
                st.subheader("📦 Pallet Reallocation Recommendations")
                
                for i, rec in enumerate(result['recommendations'], 1):
                    with st.expander(f"Recommendation #{i} - {rec['region']} Region"):
                        col1, col2 = st.columns(2)
                        
                        with col1:
                            st.markdown(f"""
                            **From:**  
                            🏭 {rec['from_warehouse']} - {rec['from_name']}  
                            📊 Current Utilization: {rec['from_current_util']:.1f}%
                            """)
                        
                        with col2:
                            st.markdown(f"""
                            **To:**  
                            🏭 {rec['to_warehouse']} - {rec['to_name']}  
                            📊 Current Utilization: {rec['to_current_util']:.1f}%
                            """)
                        
                        st.success(f"**Move {rec['pallets_to_move']} pallets** to optimize utilization")
            
            # LLM Insights
            if result.get('llm_insight'):
                st.subheader("🤖 AI Strategic Insights")
                st.markdown(f"""
                <div class="metric-card">
                    {result['llm_insight']}
                </div>
                """, unsafe_allow_html=True)
    else:
        st.info("👆 Please upload warehouse data in the Upload Data tab first")

with tab3:
    st.header("📧 Email Preview & Logs")
    
    if st.session_state.get('analysis_result'):
        result = st.session_state['analysis_result']
        
        # Show email sending logs first
        if result.get('emails_sent'):
            st.subheader("📤 Email Delivery Status")
            
            for email in result['emails_sent']:
                if email.get('success'):
                    st.success(f"✅ **{email['region']}** → {email['manager_email']} (Sent at {email['timestamp']})")
                else:
                    error_msg = email.get('error', 'Failed to send')
                    st.error(f"❌ **{email['region']}** → {email['manager_email']} ({error_msg})")
            
            st.divider()
        
        # Email preview section
        emails = result.get('emails_generated', [])
        
        if emails:
            st.subheader("👁️ Email Content Preview")
            
            # Email selector
            selected_email = st.selectbox(
                "Select email to preview",
                range(len(emails)),
                format_func=lambda x: f"{emails[x]['region']} - {emails[x]['manager_name']} ({emails[x]['manager_email']})"
            )
            
            email_data = emails[selected_email]
            
            # Display email details
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Region", email_data['region'])
            with col2:
                st.metric("Manager", email_data['manager_name'])
            with col3:
                st.metric("Recommendations", email_data['recommendation_count'])
            
            # Check if email was sent
            sent_status = next(
                (e for e in result.get('emails_sent', []) if e['manager_email'] == email_data['manager_email']), 
                None
            )
            
            if sent_status:
                if sent_status.get('success'):
                    st.success(f"✅ This email was sent at {sent_status['timestamp']}")
                else:
                    st.error(f"❌ This email failed to send: {sent_status.get('error', 'Unknown error')}")
            
            # Email preview
            st.subheader("📨 Email Content")
            st.components.v1.html(email_data['html_content'], height=800, scrolling=True)
        else:
            st.info("No emails generated yet. Run agent first.")
    else:
        st.info("👆 Please run the agent in the Analysis tab first")

with tab4:
    st.header("📊 Dashboard")
    
    if st.session_state.get('data_loaded'):
        df = pd.read_excel(st.session_state['excel_path'])
        
        # Calculate utilization if not present
        if 'Utilization_Percentage' not in df.columns:
            df['Utilization_Percentage'] = (df['Current_Pallets'] / df['Total_Capacity_Pallets'] * 100).round(2)
        
        # Overall metrics
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            avg_util = df['Utilization_Percentage'].mean()
            st.metric("Avg Utilization", f"{avg_util:.1f}%")
        
        with col2:
            total_capacity = df['Total_Capacity_Pallets'].sum()
            st.metric("Total Capacity", f"{total_capacity:,}")
        
        with col3:
            total_current = df['Current_Pallets'].sum()
            st.metric("Current Pallets", f"{total_current:,}")
        
        with col4:
            available = total_capacity - total_current
            st.metric("Available Space", f"{available:,}")
        
        # Utilization by region
        st.subheader("📍 Utilization by Region")
        
        region_stats = df.groupby('Region').agg({
            'Utilization_Percentage': 'mean',
            'Total_Capacity_Pallets': 'sum',
            'Current_Pallets': 'sum'
        }).round(2)
        
        st.dataframe(region_stats, use_container_width=True)
        
        # Warehouse status table
        st.subheader("🏭 Warehouse Status")
        
        def highlight_utilization(val):
            if val > threshold:
                return f'background-color: {COLOR_OVERUTILIZED}; color: white'
            else:
                return f'background-color: {COLOR_UNDERUTILIZED}; color: black'
        
        styled_df = df[['Warehouse_ID', 'Warehouse_Name', 'Region', 
                       'Total_Capacity_Pallets', 'Current_Pallets', 
                       'Utilization_Percentage']].style.applymap(
            highlight_utilization,
            subset=['Utilization_Percentage']
        )
        
        st.dataframe(styled_df, use_container_width=True)
    else:
        st.info("👆 Please upload warehouse data first")

# Footer
st.divider()
st.caption(f"🤖 Network Utilization Agent | Powered by LangGraph & OpenAI | © {datetime.now().year}")