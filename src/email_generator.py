"""
Email generation and sending module with Gmail API (OAuth2)
"""
import os
import base64
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import List, Dict
import pandas as pd
from datetime import datetime
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
import sys
sys.path.append('..')
from config.settings import (
    UTILIZATION_THRESHOLD, COLOR_OVERUTILIZED, 
    COLOR_UNDERUTILIZED, AGENT_NAME, COMPANY_NAME
)

# Gmail API scopes
SCOPES = ['https://www.googleapis.com/auth/gmail.send']


class EmailGenerator:
    """Generates and sends beautiful HTML emails using Gmail API"""
    
    def __init__(self, sender_email: str, client_secret_path: str = "client_secret.json"):
        self.sender_email = sender_email
        self.client_secret_path = client_secret_path
        self.service = None
        self._authenticate()
    
    def _authenticate(self):
        """Authenticate with Gmail API using OAuth2"""
        creds = None
        
        # Token file stores user's access and refresh tokens
        if os.path.exists('token.json'):
            creds = Credentials.from_authorized_user_file('token.json', SCOPES)
        
        # If no valid credentials, let user log in
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                if not os.path.exists(self.client_secret_path):
                    raise FileNotFoundError(
                        f"client_secret.json not found! Please place it in the project root.\n"
                        f"Download it from: https://console.cloud.google.com/apis/credentials"
                    )
                
                flow = InstalledAppFlow.from_client_secrets_file(
                    self.client_secret_path, SCOPES
                )
                creds = flow.run_local_server(port=0)
            
            # Save credentials for next run
            with open('token.json', 'w') as token:
                token.write(creds.to_json())
        
        try:
            self.service = build('gmail', 'v1', credentials=creds)
            print("✅ Gmail API authenticated successfully!")
        except HttpError as error:
            print(f"❌ Gmail API authentication error: {error}")
            raise
    
    def generate_html_email(self, region: str, warehouses_df: pd.DataFrame, 
                           recommendations: List[Dict], 
                           manager_name: str) -> str:
        """Generate beautiful HTML email with warehouse analysis"""
        
        # Build warehouse table rows
        warehouse_rows = ""
        for _, row in warehouses_df.iterrows():
            util = row['Utilization_Percentage']
            if util > UTILIZATION_THRESHOLD:
                color = COLOR_OVERUTILIZED
                status = "⚠️ Over-utilized"
            else:
                color = COLOR_UNDERUTILIZED
                status = "✅ Under-utilized"
            
            warehouse_rows += f"""
            <tr>
                <td style="padding: 12px; border: 1px solid #ddd;">{row['Warehouse_ID']}</td>
                <td style="padding: 12px; border: 1px solid #ddd;">{row['Warehouse_Name']}</td>
                <td style="padding: 12px; border: 1px solid #ddd; text-align: center;">{row['Total_Capacity_Pallets']}</td>
                <td style="padding: 12px; border: 1px solid #ddd; text-align: center;">{row['Current_Pallets']}</td>
                <td style="padding: 12px; border: 1px solid #ddd; text-align: center; font-weight: bold; color: {color};">
                    {util}%
                </td>
                <td style="padding: 12px; border: 1px solid #ddd; text-align: center;">
                    <span style="background-color: {color}; color: white; padding: 4px 8px; border-radius: 4px; font-size: 12px;">
                        {status}
                    </span>
                </td>
            </tr>
            """
        
        # Build recommendations section
        recommendations_html = ""
        if recommendations:
            recommendations_html = """
            <div style="background-color: #fff3cd; border-left: 4px solid #ffc107; padding: 20px; margin: 20px 0; border-radius: 5px;">
                <h3 style="color: #856404; margin-top: 0;">📦 Recommended Pallet Movements</h3>
            """
            
            for rec in recommendations:
                recommendations_html += f"""
                <div style="background-color: white; padding: 15px; margin: 10px 0; border-radius: 5px; border: 1px solid #ffc107;">
                    <p style="margin: 5px 0; font-size: 16px;">
                        <strong>Move {rec['pallets_to_move']} pallets</strong> from 
                        <span style="color: {COLOR_OVERUTILIZED}; font-weight: bold;">{rec['from_warehouse']} ({rec['from_name']})</span>
                        to 
                        <span style="color: {COLOR_UNDERUTILIZED}; font-weight: bold;">{rec['to_warehouse']} ({rec['to_name']})</span>
                    </p>
                    <p style="margin: 5px 0; font-size: 14px; color: #666;">
                        This will reduce {rec['from_warehouse']}'s utilization from {rec['from_current_util']:.1f}% to below {UTILIZATION_THRESHOLD}%
                    </p>
                </div>
                """
            
            recommendations_html += f"""
                <p style="margin-top: 15px; color: #856404;">
                    <strong>Impact:</strong> Following these recommendations will balance warehouse utilization 
                    across {region}, ensuring all facilities operate below the {UTILIZATION_THRESHOLD}% threshold 
                    for optimal efficiency and flexibility.
                </p>
            </div>
            """
        else:
            recommendations_html = """
            <div style="background-color: #d4edda; border-left: 4px solid #28a745; padding: 20px; margin: 20px 0; border-radius: 5px;">
                <h3 style="color: #155724; margin-top: 0;">✅ All Warehouses Operating Optimally</h3>
                <p style="color: #155724; margin: 0;">
                    No reallocation needed. All warehouses in your region are within acceptable utilization levels.
                </p>
            </div>
            """
        
        # Complete HTML template
        html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
        </head>
        <body style="font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; line-height: 1.6; color: #333; margin: 0; padding: 0; background-color: #f4f4f4;">
            <div style="max-width: 800px; margin: 20px auto; background-color: white; border-radius: 10px; overflow: hidden; box-shadow: 0 0 20px rgba(0,0,0,0.1);">
                
                <!-- Header -->
                <div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 30px; text-align: center;">
                    <h1 style="margin: 0; font-size: 28px;">🏭 Network Utilization Report</h1>
                    <p style="margin: 10px 0 0 0; font-size: 16px; opacity: 0.9;">{COMPANY_NAME}</p>
                </div>
                
                <!-- Content -->
                <div style="padding: 30px;">
                    <p style="font-size: 16px;">Dear {manager_name},</p>
                    
                    <p style="font-size: 15px; line-height: 1.8;">
                        Our {AGENT_NAME} has completed its analysis of warehouse utilization across 
                        <strong>{region}</strong> region as of <strong>{datetime.now().strftime('%B %d, %Y at %I:%M %p')}</strong>.
                    </p>
                    
                    <div style="background-color: #e7f3ff; border-left: 4px solid #2196F3; padding: 15px; margin: 20px 0; border-radius: 5px;">
                        <p style="margin: 0; color: #0c5c9c;">
                            <strong>📊 Target Utilization:</strong> Below {UTILIZATION_THRESHOLD}% for optimal operations
                        </p>
                    </div>
                    
                    <h2 style="color: #667eea; border-bottom: 2px solid #667eea; padding-bottom: 10px;">
                        Warehouse Status Overview - {region}
                    </h2>
                    
                    <table style="width: 100%; border-collapse: collapse; margin: 20px 0; box-shadow: 0 2px 4px rgba(0,0,0,0.1);">
                        <thead>
                            <tr style="background-color: #667eea; color: white;">
                                <th style="padding: 12px; text-align: left; border: 1px solid #ddd;">ID</th>
                                <th style="padding: 12px; text-align: left; border: 1px solid #ddd;">Warehouse</th>
                                <th style="padding: 12px; text-align: center; border: 1px solid #ddd;">Capacity</th>
                                <th style="padding: 12px; text-align: center; border: 1px solid #ddd;">Current</th>
                                <th style="padding: 12px; text-align: center; border: 1px solid #ddd;">Utilization</th>
                                <th style="padding: 12px; text-align: center; border: 1px solid #ddd;">Status</th>
                            </tr>
                        </thead>
                        <tbody style="background-color: white;">
                            {warehouse_rows}
                        </tbody>
                    </table>
                    
                    {recommendations_html}
                    
                    <div style="background-color: #f8f9fa; padding: 20px; margin: 20px 0; border-radius: 5px; border: 1px solid #dee2e6;">
                        <h3 style="color: #495057; margin-top: 0;">📌 Next Steps</h3>
                        <ol style="color: #495057; line-height: 2;">
                            <li>Review the recommendations above</li>
                            <li>Coordinate with logistics teams for pallet movements</li>
                            <li>Implement changes within the next 48-72 hours</li>
                            <li>Monitor utilization levels post-implementation</li>
                        </ol>
                    </div>
                    
                    <p style="font-size: 15px;">
                        If you have any questions or need assistance with implementation, please don't hesitate to reach out.
                    </p>
                    
                    <p style="font-size: 15px;">
                        Best regards,<br>
                        <strong>{AGENT_NAME}</strong><br>
                        <em>{COMPANY_NAME}</em>
                    </p>
                </div>
                
                <!-- Footer -->
                <div style="background-color: #f8f9fa; padding: 20px; text-align: center; border-top: 1px solid #dee2e6;">
                    <p style="margin: 0; font-size: 12px; color: #6c757d;">
                        This is an automated report generated by AI. For support, contact your system administrator.
                    </p>
                    <p style="margin: 5px 0 0 0; font-size: 12px; color: #6c757d;">
                        © {datetime.now().year} {COMPANY_NAME}. All rights reserved.
                    </p>
                </div>
                
            </div>
        </body>
        </html>
        """
        
        return html
    
    def send_email(self, recipient_email: str, subject: str, html_content: str) -> bool:
        """Send HTML email via Gmail API"""
        try:
            # Create message
            message = MIMEMultipart("alternative")
            message["Subject"] = subject
            message["From"] = self.sender_email
            message["To"] = recipient_email
            
            # Attach HTML content
            html_part = MIMEText(html_content, "html")
            message.attach(html_part)
            
            # Encode message
            raw_message = base64.urlsafe_b64encode(message.as_bytes()).decode()
            
            # Send message
            send_message = self.service.users().messages().send(
                userId="me",
                body={"raw": raw_message}
            ).execute()
            
            print(f"✅ Email sent successfully! Message ID: {send_message['id']}")
            return True
            
        except HttpError as error:
            print(f"❌ Gmail API error: {error}")
            return False
        except Exception as e:
            print(f"❌ Error sending email: {str(e)}")
            return False