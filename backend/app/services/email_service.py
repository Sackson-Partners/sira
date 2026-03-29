"""
Email Notification Service
SMTP-based email delivery for alerts and notifications
"""

import logging
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders
from typing import List, Optional, Dict, Any
from datetime import datetime, timezone

import asyncio
from concurrent.futures import ThreadPoolExecutor

from app.core.config import settings

logger = logging.getLogger(__name__)

# Thread pool for async email sending
_executor = ThreadPoolExecutor(max_workers=4)


class EmailService:
    """Service for sending email notifications"""

    def __init__(self):
        self.smtp_host = settings.SMTP_HOST
        self.smtp_port = settings.SMTP_PORT
        self.smtp_user = settings.SMTP_USER
        self.smtp_password = settings.SMTP_PASSWORD
        self.email_from = settings.EMAIL_FROM
        self.email_from_name = settings.EMAIL_FROM_NAME

    def _is_configured(self) -> bool:
        """Check if email service is properly configured"""
        return all([
            self.smtp_host,
            self.smtp_user,
            self.smtp_password
        ])

    def _get_smtp_connection(self) -> smtplib.SMTP:
        """Create SMTP connection"""
        smtp = smtplib.SMTP(self.smtp_host, self.smtp_port)
        smtp.starttls()
        smtp.login(self.smtp_user, self.smtp_password)
        return smtp

    def _send_email_sync(
        self,
        to_emails: List[str],
        subject: str,
        html_content: str,
        text_content: Optional[str] = None,
        attachments: Optional[List[Dict[str, Any]]] = None
    ) -> bool:
        """Synchronous email sending"""
        if not self._is_configured():
            logger.warning("Email service not configured, skipping send")
            return False

        try:
            msg = MIMEMultipart("alternative")
            msg["Subject"] = subject
            msg["From"] = f"{self.email_from_name} <{self.email_from}>"
            msg["To"] = ", ".join(to_emails)

            # Add text version
            if text_content:
                msg.attach(MIMEText(text_content, "plain"))

            # Add HTML version
            msg.attach(MIMEText(html_content, "html"))

            # Add attachments
            if attachments:
                for attachment in attachments:
                    part = MIMEBase("application", "octet-stream")
                    part.set_payload(attachment["content"])
                    encoders.encode_base64(part)
                    part.add_header(
                        "Content-Disposition",
                        f"attachment; filename={attachment['filename']}"
                    )
                    msg.attach(part)

            with self._get_smtp_connection() as smtp:
                smtp.sendmail(self.email_from, to_emails, msg.as_string())

            logger.info(f"Email sent successfully to {to_emails}")
            return True

        except Exception as e:
            logger.error(f"Error sending email: {e}")
            return False

    async def send_email(
        self,
        to_emails: List[str],
        subject: str,
        html_content: str,
        text_content: Optional[str] = None,
        attachments: Optional[List[Dict[str, Any]]] = None
    ) -> bool:
        """Asynchronous email sending"""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            _executor,
            self._send_email_sync,
            to_emails,
            subject,
            html_content,
            text_content,
            attachments
        )

    async def send_alert_notification(
        self,
        to_emails: List[str],
        alert_data: Dict[str, Any]
    ) -> bool:
        """Send alert notification email"""
        severity = alert_data.get("severity", "Unknown")
        alert_id = alert_data.get("id", "N/A")
        description = alert_data.get("description", "No description")
        domain = alert_data.get("domain", "N/A")
        created_at = alert_data.get("created_at", datetime.now(timezone.utc).isoformat())

        subject = f"[SIRA Alert - {severity}] {description[:50]}..."

        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <style>
                body {{ font-family: Arial, sans-serif; line-height: 1.6; }}
                .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
                .header {{ background-color: {'#dc3545' if severity == 'Critical' else '#fd7e14' if severity == 'High' else '#ffc107' if severity == 'Medium' else '#28a745'}; color: white; padding: 20px; text-align: center; }}
                .content {{ padding: 20px; background-color: #f8f9fa; }}
                .detail {{ margin: 10px 0; }}
                .label {{ font-weight: bold; color: #495057; }}
                .button {{ display: inline-block; padding: 10px 20px; background-color: #007bff; color: white; text-decoration: none; border-radius: 5px; }}
                .footer {{ text-align: center; padding: 20px; color: #6c757d; font-size: 12px; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>Security Alert</h1>
                    <h2>{severity} Severity</h2>
                </div>
                <div class="content">
                    <div class="detail">
                        <span class="label">Alert ID:</span> {alert_id}
                    </div>
                    <div class="detail">
                        <span class="label">Domain:</span> {domain}
                    </div>
                    <div class="detail">
                        <span class="label">Description:</span><br>
                        {description}
                    </div>
                    <div class="detail">
                        <span class="label">Time:</span> {created_at}
                    </div>
                    <br>
                    <a href="#" class="button">View in SIRA Dashboard</a>
                </div>
                <div class="footer">
                    <p>This is an automated notification from SIRA Platform.</p>
                    <p>Do not reply to this email.</p>
                </div>
            </div>
        </body>
        </html>
        """

        text_content = f"""
        SIRA SECURITY ALERT
        ===================
        Severity: {severity}
        Alert ID: {alert_id}
        Domain: {domain}
        Description: {description}
        Time: {created_at}

        Please log in to the SIRA dashboard for more details.
        """

        return await self.send_email(to_emails, subject, html_content, text_content)

    async def send_case_update(
        self,
        to_emails: List[str],
        case_data: Dict[str, Any],
        update_type: str
    ) -> bool:
        """Send case update notification email"""
        case_number = case_data.get("case_number", "N/A")
        title = case_data.get("title", "Untitled Case")
        status = case_data.get("status", "Unknown")
        priority = case_data.get("priority", "medium")

        subject = f"[SIRA Case {update_type.title()}] {case_number}: {title[:40]}..."

        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <style>
                body {{ font-family: Arial, sans-serif; line-height: 1.6; }}
                .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
                .header {{ background-color: #007bff; color: white; padding: 20px; text-align: center; }}
                .content {{ padding: 20px; background-color: #f8f9fa; }}
                .detail {{ margin: 10px 0; }}
                .label {{ font-weight: bold; color: #495057; }}
                .status {{ display: inline-block; padding: 5px 10px; border-radius: 3px; background-color: #28a745; color: white; }}
                .button {{ display: inline-block; padding: 10px 20px; background-color: #007bff; color: white; text-decoration: none; border-radius: 5px; }}
                .footer {{ text-align: center; padding: 20px; color: #6c757d; font-size: 12px; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>Case {update_type.title()}</h1>
                    <h2>{case_number}</h2>
                </div>
                <div class="content">
                    <div class="detail">
                        <span class="label">Title:</span> {title}
                    </div>
                    <div class="detail">
                        <span class="label">Status:</span> <span class="status">{status}</span>
                    </div>
                    <div class="detail">
                        <span class="label">Priority:</span> {priority.title()}
                    </div>
                    <br>
                    <a href="#" class="button">View Case Details</a>
                </div>
                <div class="footer">
                    <p>This is an automated notification from SIRA Platform.</p>
                </div>
            </div>
        </body>
        </html>
        """

        return await self.send_email(to_emails, subject, html_content)

    async def send_sla_breach_notification(
        self,
        to_emails: List[str],
        alert_data: Dict[str, Any]
    ) -> bool:
        """Send SLA breach notification email"""
        alert_id = alert_data.get("id", "N/A")
        severity = alert_data.get("severity", "Unknown")
        description = alert_data.get("description", "No description")
        sla_timer = alert_data.get("sla_timer", 0)

        subject = f"[URGENT] SLA BREACH - Alert {alert_id}"

        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <style>
                body {{ font-family: Arial, sans-serif; line-height: 1.6; }}
                .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
                .header {{ background-color: #dc3545; color: white; padding: 20px; text-align: center; }}
                .content {{ padding: 20px; background-color: #fff3cd; border: 2px solid #dc3545; }}
                .warning {{ color: #dc3545; font-weight: bold; font-size: 18px; }}
                .detail {{ margin: 10px 0; }}
                .label {{ font-weight: bold; }}
                .button {{ display: inline-block; padding: 10px 20px; background-color: #dc3545; color: white; text-decoration: none; border-radius: 5px; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>SLA BREACH</h1>
                    <h2>IMMEDIATE ACTION REQUIRED</h2>
                </div>
                <div class="content">
                    <p class="warning">Alert {alert_id} has breached its SLA of {sla_timer} minutes!</p>
                    <div class="detail">
                        <span class="label">Severity:</span> {severity}
                    </div>
                    <div class="detail">
                        <span class="label">Description:</span><br>
                        {description}
                    </div>
                    <br>
                    <a href="#" class="button">Take Action Now</a>
                </div>
            </div>
        </body>
        </html>
        """

        return await self.send_email(to_emails, subject, html_content)

    async def send_daily_digest(
        self,
        to_email: str,
        digest_data: Dict[str, Any]
    ) -> bool:
        """Send daily digest email"""
        date = digest_data.get("date", datetime.now(timezone.utc).strftime("%Y-%m-%d"))
        total_alerts = digest_data.get("total_alerts", 0)
        critical_alerts = digest_data.get("critical_alerts", 0)
        open_cases = digest_data.get("open_cases", 0)
        sla_breaches = digest_data.get("sla_breaches", 0)

        subject = f"[SIRA] Daily Digest - {date}"

        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <style>
                body {{ font-family: Arial, sans-serif; line-height: 1.6; }}
                .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
                .header {{ background-color: #343a40; color: white; padding: 20px; text-align: center; }}
                .stat-box {{ display: inline-block; width: 45%; margin: 10px 2%; padding: 15px; background-color: #f8f9fa; text-align: center; border-radius: 5px; }}
                .stat-number {{ font-size: 36px; font-weight: bold; color: #007bff; }}
                .stat-label {{ color: #6c757d; }}
                .footer {{ text-align: center; padding: 20px; color: #6c757d; font-size: 12px; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>Daily Digest</h1>
                    <h3>{date}</h3>
                </div>
                <div style="padding: 20px;">
                    <div class="stat-box">
                        <div class="stat-number">{total_alerts}</div>
                        <div class="stat-label">Total Alerts</div>
                    </div>
                    <div class="stat-box">
                        <div class="stat-number" style="color: #dc3545;">{critical_alerts}</div>
                        <div class="stat-label">Critical Alerts</div>
                    </div>
                    <div class="stat-box">
                        <div class="stat-number">{open_cases}</div>
                        <div class="stat-label">Open Cases</div>
                    </div>
                    <div class="stat-box">
                        <div class="stat-number" style="color: #fd7e14;">{sla_breaches}</div>
                        <div class="stat-label">SLA Breaches</div>
                    </div>
                </div>
                <div class="footer">
                    <p>This is your daily summary from SIRA Platform.</p>
                </div>
            </div>
        </body>
        </html>
        """

        return await self.send_email([to_email], subject, html_content)
