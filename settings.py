"""
Configuration settings for Network Utilization Agent
"""

# Utilization threshold
UTILIZATION_THRESHOLD = 85.0

# Email configuration
SMTP_SERVER = "smtp.gmail.com"
SMTP_PORT = 587

# Color coding for email
COLOR_OVERUTILIZED = "#ff4444"  # Red
COLOR_UNDERUTILIZED = "#44ff44"  # Green
COLOR_OPTIMAL = "#ffaa00"  # Orange

# Agent configuration
AGENT_NAME = "Network Utilization Agent"
COMPANY_NAME = "Supply Chain AI Solutions"

# LangGraph state keys
STATE_KEYS = {
    "warehouse_data": "warehouse_data",
    "overutilized": "overutilized_warehouses",
    "underutilized": "underutilized_warehouses",
    "regions": "regions",
    "recommendations": "recommendations",
    "emails": "emails_generated"
}