"""
Email Service for MediAI Platform.

Handles sending asynchronous HTML and plain-text emails,
including immediate appointment confirmations and 30-minute pre-visit reminders.
Gracefully simulates delivery when SMTP is unconfigured.
"""

import asyncio
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from datetime import datetime
from typing import Optional

from core.config.logging import get_logger
from core.config.settings import settings

logger = get_logger("core.email_service")


class EmailService:
    def __init__(self) -> None:
        self.host = settings.smtp_host
        self.port = settings.smtp_port
        self.user = settings.smtp_user
        self.password = settings.smtp_password
        self.from_email = settings.smtp_from_email
        self.from_name = settings.smtp_from_name
        self.tls = settings.smtp_tls
        self.enabled = settings.emails_enabled and bool(self.user and self.password)

    def _format_datetime(self, dt: datetime) -> str:
        """Format datetime into a user-friendly display string."""
        return dt.strftime("%A, %B %d, %Y at %I:%M %p")

    async def send_email(
        self,
        to_email: str,
        subject: str,
        html_content: str,
        text_content: Optional[str] = None,
    ) -> bool:
        """
        Send an email asynchronously.
        If SMTP is disabled or unconfigured, logs the email and returns True.
        """
        if not to_email or "@" not in to_email:
            logger.warning("Skipping email: invalid recipient", recipient=to_email)
            return False

        if not self.enabled:
            logger.info(
                "[SIMULATED EMAIL] Delivery simulated (SMTP credentials not configured)",
                to=to_email,
                subject=subject,
            )
            return True

        # Run synchronous SMTP sending in a background thread to prevent event loop blocking
        return await asyncio.to_thread(
            self._send_smtp_sync,
            to_email,
            subject,
            html_content,
            text_content or "Please view this email in an HTML-compatible client.",
        )

    def _send_smtp_sync(
        self,
        to_email: str,
        subject: str,
        html_content: str,
        text_content: str,
    ) -> bool:
        """Synchronous SMTP worker."""
        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"] = f"{self.from_name} <{self.from_email}>"
        msg["To"] = to_email

        # Attach text & HTML parts
        msg.attach(MIMEText(text_content, "plain", "utf-8"))
        msg.attach(MIMEText(html_content, "html", "utf-8"))

        try:
            if self.port == 465:
                server = smtplib.SMTP_SSL(self.host, self.port, timeout=10)
            else:
                server = smtplib.SMTP(self.host, self.port, timeout=10)
                if self.tls:
                    server.starttls()

            if self.user and self.password:
                server.login(self.user, self.password)

            server.sendmail(self.from_email, [to_email], msg.as_string())
            server.quit()
            logger.info("Email successfully sent via SMTP", to=to_email, subject=subject)
            return True

        except Exception as exc:
            logger.error("Failed to send email via SMTP", to=to_email, error=str(exc))
            return False

    def _format_doctor_name(self, doctor_name: str) -> str:
        """Format doctor name cleanly, avoiding redundant 'Dr. Dr.' prefixes."""
        name = (doctor_name or "Doctor").strip()
        if name.lower().startswith("dr."):
            return f"Dr. {name[3:].strip()}"
        if name.lower().startswith("dr "):
            return f"Dr. {name[3:].strip()}"
        return f"Dr. {name}"

    # ── Template Builders ─────────────────────────────────────────────────────

    def render_confirmation_email(
        self,
        patient_name: str,
        doctor_name: str,
        doctor_specialty: str,
        scheduled_at: datetime,
        duration_minutes: int = 30,
        appointment_type: str = "Consultation",
        reason: Optional[str] = None,
    ) -> tuple[str, str]:
        """
        Builds Subject and HTML body for immediate appointment booking confirmation.
        """
        date_str = self._format_datetime(scheduled_at)
        formatted_doctor = self._format_doctor_name(doctor_name)
        subject = f"🏥 Appointment Confirmed: {formatted_doctor} – {date_str}"
        type_display = (appointment_type or "Consultation").capitalize()

        reason_row = (
            f"""
            <tr>
                <td style="padding: 10px 0; color: #64748b; font-size: 14px;">Reason / Notes:</td>
                <td style="padding: 10px 0; color: #1e293b; font-size: 14px; font-weight: 500; text-align: right;">{reason}</td>
            </tr>
            """
            if reason
            else ""
        )

        html = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{subject}</title>
</head>
<body style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; background-color: #f8fafc; margin: 0; padding: 20px;">
    <table width="100%" border="0" cellspacing="0" cellpadding="0">
        <tr>
            <td align="center">
                <table width="600" border="0" cellspacing="0" cellpadding="0" style="background-color: #ffffff; border-radius: 12px; overflow: hidden; box-shadow: 0 4px 12px rgba(0,0,0,0.06); border: 1px solid #e2e8f0;">
                    <!-- Header -->
                    <tr>
                        <td style="background: linear-gradient(135deg, #0ea5e9 0%, #2563eb 100%); padding: 32px 40px; text-align: center;">
                            <h1 style="color: #ffffff; margin: 0; font-size: 24px; font-weight: 700; letter-spacing: -0.5px;">MediAI Health System</h1>
                            <p style="color: #e0f2fe; margin: 8px 0 0 0; font-size: 14px;">Appointment Booking Confirmation</p>
                        </td>
                    </tr>

                    <!-- Body -->
                    <tr>
                        <td style="padding: 36px 40px;">
                            <h2 style="color: #0f172a; margin: 0 0 12px 0; font-size: 20px;">Hello, {patient_name}</h2>
                            <p style="color: #475569; font-size: 15px; line-height: 1.6; margin: 0 0 24px 0;">
                                Your appointment has been successfully scheduled. Below are your booking details:
                            </p>

                            <!-- Details Card -->
                            <div style="background-color: #f1f5f9; border-radius: 8px; padding: 24px; margin-bottom: 24px; border: 1px solid #e2e8f0;">
                                <table width="100%" border="0" cellspacing="0" cellpadding="0">
                                    <tr>
                                        <td style="padding: 10px 0; color: #64748b; font-size: 14px; border-bottom: 1px solid #e2e8f0;">Doctor:</td>
                                        <td style="padding: 10px 0; color: #0f172a; font-size: 15px; font-weight: 600; text-align: right; border-bottom: 1px solid #e2e8f0;">{formatted_doctor}</td>
                                    </tr>
                                    <tr>
                                        <td style="padding: 10px 0; color: #64748b; font-size: 14px; border-bottom: 1px solid #e2e8f0;">Specialty:</td>
                                        <td style="padding: 10px 0; color: #1e293b; font-size: 14px; font-weight: 500; text-align: right; border-bottom: 1px solid #e2e8f0;">{doctor_specialty}</td>
                                    </tr>
                                    <tr>
                                        <td style="padding: 10px 0; color: #64748b; font-size: 14px; border-bottom: 1px solid #e2e8f0;">Date & Time:</td>
                                        <td style="padding: 10px 0; color: #0284c7; font-size: 15px; font-weight: 700; text-align: right; border-bottom: 1px solid #e2e8f0;">{date_str}</td>
                                    </tr>
                                    <tr>
                                        <td style="padding: 10px 0; color: #64748b; font-size: 14px; border-bottom: 1px solid #e2e8f0;">Duration:</td>
                                        <td style="padding: 10px 0; color: #1e293b; font-size: 14px; font-weight: 500; text-align: right; border-bottom: 1px solid #e2e8f0;">{duration_minutes} Minutes</td>
                                    </tr>
                                    <tr>
                                        <td style="padding: 10px 0; color: #64748b; font-size: 14px; border-bottom: 1px solid #e2e8f0;">Type:</td>
                                        <td style="padding: 10px 0; color: #1e293b; font-size: 14px; font-weight: 500; text-align: right; border-bottom: 1px solid #e2e8f0;">{appointment_type.capitalize()}</td>
                                    </tr>
                                    {reason_row}
                                </table>
                            </div>

                            <p style="color: #475569; font-size: 14px; line-height: 1.6; margin: 0 0 16px 0;">
                                💡 <strong>Tip:</strong> We will also send you a reminder email <strong>30 minutes</strong> prior to your appointment time.
                            </p>
                        </td>
                    </tr>

                    <!-- Footer -->
                    <tr>
                        <td style="background-color: #f8fafc; padding: 20px 40px; text-align: center; border-top: 1px solid #e2e8f0;">
                            <p style="color: #94a3b8; font-size: 12px; margin: 0;">
                                © {datetime.now().year} MediAI Healthcare Inc. All rights reserved.
                            </p>
                        </td>
                    </tr>
                </table>
            </td>
        </tr>
    </table>
</body>
</html>"""
        return subject, html

    def render_reminder_email(
        self,
        patient_name: str,
        doctor_name: str,
        doctor_specialty: str,
        scheduled_at: datetime,
        duration_minutes: int = 30,
        appointment_type: str = "Consultation",
    ) -> tuple[str, str]:
        """
        Builds Subject and HTML body for 30-minute upcoming appointment reminder.
        """
        date_str = self._format_datetime(scheduled_at)
        formatted_doctor = self._format_doctor_name(doctor_name)
        subject = f"⏰ Reminder: Appointment with {formatted_doctor} in 30 minutes"

        html = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{subject}</title>
</head>
<body style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; background-color: #f8fafc; margin: 0; padding: 20px;">
    <table width="100%" border="0" cellspacing="0" cellpadding="0">
        <tr>
            <td align="center">
                <table width="600" border="0" cellspacing="0" cellpadding="0" style="background-color: #ffffff; border-radius: 12px; overflow: hidden; box-shadow: 0 4px 12px rgba(0,0,0,0.06); border: 1px solid #e2e8f0;">
                    <!-- Alert Header -->
                    <tr>
                        <td style="background: linear-gradient(135deg, #f59e0b 0%, #d97706 100%); padding: 32px 40px; text-align: center;">
                            <h1 style="color: #ffffff; margin: 0; font-size: 24px; font-weight: 700; letter-spacing: -0.5px;">⏰ Upcoming Appointment Reminder</h1>
                            <p style="color: #fef3c7; margin: 8px 0 0 0; font-size: 14px;">Your consultation starts in approximately 30 minutes</p>
                        </td>
                    </tr>

                    <!-- Body -->
                    <tr>
                        <td style="padding: 36px 40px;">
                            <h2 style="color: #0f172a; margin: 0 0 12px 0; font-size: 20px;">Hi {patient_name},</h2>
                            <p style="color: #475569; font-size: 15px; line-height: 1.6; margin: 0 0 24px 0;">
                                This is a friendly reminder that your upcoming appointment with <strong>{formatted_doctor}</strong> will begin shortly.
                            </p>

                            <!-- Details Card -->
                            <div style="background-color: #fffbeb; border-radius: 8px; padding: 24px; margin-bottom: 24px; border: 1px solid #fde68a;">
                                <table width="100%" border="0" cellspacing="0" cellpadding="0">
                                    <tr>
                                        <td style="padding: 10px 0; color: #92400e; font-size: 14px; border-bottom: 1px solid #fde68a;">Doctor:</td>
                                        <td style="padding: 10px 0; color: #78350f; font-size: 15px; font-weight: 600; text-align: right; border-bottom: 1px solid #fde68a;">{formatted_doctor} ({doctor_specialty})</td>
                                    </tr>
                                    <tr>
                                        <td style="padding: 10px 0; color: #92400e; font-size: 14px; border-bottom: 1px solid #fde68a;">Scheduled At:</td>
                                        <td style="padding: 10px 0; color: #b45309; font-size: 15px; font-weight: 700; text-align: right; border-bottom: 1px solid #fde68a;">{date_str}</td>
                                    </tr>
                                    <tr>
                                        <td style="padding: 10px 0; color: #92400e; font-size: 14px;">Duration:</td>
                                        <td style="padding: 10px 0; color: #78350f; font-size: 14px; font-weight: 500; text-align: right;">{duration_minutes} Minutes ({(appointment_type or "Consultation").capitalize()})</td>
                                    </tr>
                                </table>
                            </div>

                            <div style="background-color: #f8fafc; border-left: 4px solid #0284c7; padding: 16px; border-radius: 4px; margin-bottom: 24px;">
                                <p style="color: #334155; font-size: 13px; margin: 0; line-height: 1.5;">
                                    📌 <strong>Preparation Checklist:</strong><br>
                                    • Please be ready 5–10 minutes before the scheduled time.<br>
                                    • Have your relevant medical records or current medications list handy.
                                </p>
                            </div>
                        </td>
                    </tr>

                    <!-- Footer -->
                    <tr>
                        <td style="background-color: #f8fafc; padding: 20px 40px; text-align: center; border-top: 1px solid #e2e8f0;">
                            <p style="color: #94a3b8; font-size: 12px; margin: 0;">
                                © {datetime.now().year} MediAI Healthcare Inc. All rights reserved.
                            </p>
                        </td>
                    </tr>
                </table>
            </td>
        </tr>
    </table>
</body>
</html>"""
        return subject, html


# Global singleton instance
email_service = EmailService()
