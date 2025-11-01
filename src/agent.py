"""
LangGraph workflow for Network Utilization Agent
"""
from typing import TypedDict, List, Dict, Annotated
import operator
from langgraph.graph import Graph, StateGraph, END
from langchain_openai import ChatOpenAI
from langchain.prompts import ChatPromptTemplate
from datetime import datetime
from src.data_processor import WarehouseDataProcessor

from config.settings import STATE_KEYS, UTILIZATION_THRESHOLD
from src.data_processor import WarehouseDataProcessor
from src.email_generator import EmailGenerator


# Define the state structure
class AgentState(TypedDict):
    warehouse_data: dict
    overutilized_warehouses: list
    underutilized_warehouses: list
    regions: dict
    recommendations: Annotated[list, operator.add]
    emails_generated: Annotated[list, operator.add]
    emails_sent: Annotated[list, operator.add]
    status: str
    error: str


class NetworkUtilizationAgent:
    """LangGraph-based agent for warehouse utilization monitoring and optimization"""
    
    def __init__(self, openai_api_key: str, excel_path: str, 
                 sender_email: str = None, client_secret_path: str = "client_secret.json"):
        self.openai_api_key = openai_api_key
        self.excel_path = excel_path
        self.processor = WarehouseDataProcessor(excel_path)
        self.email_gen = None
        
        if sender_email:
            self.email_gen = EmailGenerator(sender_email, client_secret_path)
        
        # Initialize LLM
        self.llm = ChatOpenAI(
            api_key=openai_api_key,
            model="gpt-4o-mini",
            temperature=0.3
        )
        
        # Build the graph
        self.graph = self._build_graph()
    
    def _build_graph(self) -> Graph:
        """Build the LangGraph workflow"""
        workflow = StateGraph(AgentState)
        
        # Add nodes
        workflow.add_node("monitor", self.monitor_node)
        workflow.add_node("detect", self.detect_node)
        workflow.add_node("analyze", self.analyze_node)
        workflow.add_node("generate_email", self.generate_email_node)
        workflow.add_node("send_email", self.send_email_node)
        
        # Define edges
        workflow.set_entry_point("monitor")
        workflow.add_edge("monitor", "detect")
        workflow.add_edge("detect", "analyze")
        workflow.add_edge("analyze", "generate_email")
        workflow.add_edge("generate_email", "send_email")
        workflow.add_edge("send_email", END)
        
        return workflow.compile()
    
    def monitor_node(self, state: AgentState) -> AgentState:
        """Node 1: Monitor warehouse utilization levels"""
        try:
            # Load and process data
            df = self.processor.load_data()
            
            state["warehouse_data"] = df.to_dict('records')
            state["status"] = "Monitoring complete"
            
            return state
        except Exception as e:
            state["error"] = f"Monitoring error: {str(e)}"
            state["status"] = "Error in monitoring"
            return state
    
    def detect_node(self, state: AgentState) -> AgentState:
        """Node 2: Detect over-utilized and under-utilized warehouses"""
        try:
            overutilized, underutilized = self.processor.identify_utilization_issues()
            
            state["overutilized_warehouses"] = overutilized.to_dict('records')
            state["underutilized_warehouses"] = underutilized.to_dict('records')
            
            # Group by region
            regions = self.processor.group_by_region()
            state["regions"] = {
                region: df.to_dict('records') 
                for region, df in regions.items()
            }
            
            state["status"] = f"Detection complete: {len(overutilized)} over-utilized, {len(underutilized)} under-utilized"
            
            return state
        except Exception as e:
            state["error"] = f"Detection error: {str(e)}"
            state["status"] = "Error in detection"
            return state
    
    def analyze_node(self, state: AgentState) -> AgentState:
        """Node 3: Analyze and generate recommendations using LLM"""
        try:
            import pandas as pd
            
            overutilized_df = pd.DataFrame(state["overutilized_warehouses"])
            underutilized_df = pd.DataFrame(state["underutilized_warehouses"])
            
            # Calculate recommendations
            recommendations = self.processor.calculate_reallocation(
                overutilized_df, 
                underutilized_df
            )
            
            # Use LLM to enhance recommendations with insights
            if recommendations:
                prompt = ChatPromptTemplate.from_messages([
                    ("system", """You are an expert supply chain analyst. 
                    Analyze the warehouse utilization data and provide strategic insights 
                    about the recommendations."""),
                    ("user", """Given these warehouse reallocation recommendations:
                    {recommendations}
                    
                    Provide a brief strategic insight (2-3 sentences) about:
                    1. The overall network health
                    2. Potential operational impact
                    3. Priority of implementation""")
                ])
                
                chain = prompt | self.llm
                response = chain.invoke({
                    "recommendations": str(recommendations[:3])  # Limit for token efficiency
                })
                
                # Add LLM insight to state
                state["llm_insight"] = response.content
            
            state["recommendations"] = recommendations
            state["status"] = f"Analysis complete: {len(recommendations)} recommendations generated"
            
            return state
        except Exception as e:
            state["error"] = f"Analysis error: {str(e)}"
            state["status"] = "Error in analysis"
            return state
    
    def generate_email_node(self, state: AgentState) -> AgentState:
        """Node 4: Generate and prepare emails for branch managers"""
        try:
            emails_generated = []
            recommendations_by_region = {}
            
            # Group recommendations by region
            for rec in state.get("recommendations", []):
                region = rec['region']
                if region not in recommendations_by_region:
                    recommendations_by_region[region] = []
                recommendations_by_region[region].append(rec)
            
            # Generate email for each region
            for region, recs in recommendations_by_region.items():
                # Get region summary
                region_summary = self.processor.get_region_summary(region)
                
                # Get manager details from first recommendation
                manager_name = recs[0]['branch_manager']
                manager_email = recs[0]['branch_email']
                
                if self.email_gen:
                    # Generate HTML email
                    html_content = self.email_gen.generate_html_email(
                        region=region,
                        warehouses_df=region_summary,
                        recommendations=recs,
                        manager_name=manager_name
                    )
                    
                    emails_generated.append({
                        'region': region,
                        'manager_name': manager_name,
                        'manager_email': manager_email,
                        'html_content': html_content,
                        'recommendation_count': len(recs)
                    })
            
            state["emails_generated"] = emails_generated
            state["status"] = f"Email generation complete: {len(emails_generated)} emails prepared"
            
            return state
        except Exception as e:
            state["error"] = f"Email generation error: {str(e)}"
            state["status"] = "Error in email generation"
            return state
    
    def send_email_node(self, state: AgentState) -> AgentState:
        """Node 5: Automatically send all generated emails"""
        try:
            if not self.email_gen:
                state["status"] = "Email sending skipped - no email configuration"
                state["emails_sent"] = []
                return state
            
            emails_sent = []
            
            for email in state.get("emails_generated", []):
                subject = f"🏭 Warehouse Utilization Report - {email['region']} Region"
                
                try:
                    success = self.email_gen.send_email(
                        recipient_email=email['manager_email'],
                        subject=subject,
                        html_content=email['html_content']
                    )
                    
                    emails_sent.append({
                        'region': email['region'],
                        'manager_name': email['manager_name'],
                        'manager_email': email['manager_email'],
                        'success': success,
                        'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                    })
                    
                    if success:
                        print(f"✅ Email sent to {email['manager_email']} ({email['region']})")
                    else:
                        print(f"❌ Failed to send email to {email['manager_email']} ({email['region']})")
                        
                except Exception as e:
                    print(f"❌ Error sending to {email['manager_email']}: {str(e)}")
                    emails_sent.append({
                        'region': email['region'],
                        'manager_name': email['manager_name'],
                        'manager_email': email['manager_email'],
                        'success': False,
                        'error': str(e),
                        'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                    })
            
            state["emails_sent"] = emails_sent
            success_count = sum(1 for e in emails_sent if e.get('success', False))
            state["status"] = f"Email sending complete: {success_count}/{len(emails_sent)} emails sent successfully"
            
            return state
        except Exception as e:
            state["error"] = f"Email sending error: {str(e)}"
            state["status"] = "Error in email sending"
            return state
    
    def run(self) -> AgentState:
        """Execute the complete workflow"""
        initial_state = {
            "warehouse_data": {},
            "overutilized_warehouses": [],
            "underutilized_warehouses": [],
            "regions": {},
            "recommendations": [],
            "emails_generated": [],
            "emails_sent": [],
            "status": "Starting",
            "error": ""
        }
        
        result = self.graph.invoke(initial_state)
        return result
    
    def send_emails(self, state: AgentState) -> Dict[str, bool]:
        """Send all generated emails"""
        if not self.email_gen:
            return {"error": "Email generator not configured"}
        
        results = {}
        for email in state.get("emails_generated", []):
            subject = f"🏭 Warehouse Utilization Report - {email['region']} Region"
            success = self.email_gen.send_email(
                recipient_email=email['manager_email'],
                subject=subject,
                html_content=email['html_content']
            )
            results[email['region']] = success
        
        return results