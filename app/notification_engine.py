import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from sqlalchemy.orm import Session
from app.models import Order, NotificationLog
from app.config import SMTP_HOST, SMTP_PORT, SMTP_USER, SMTP_PASS, SYSTEM_EMAIL
from datetime import datetime

def send_actual_email(to_email: str, subject: str, body_text: str) -> bool:
    """
    Sends email via SMTP if credentials configured in .env.
    """
    if not (SMTP_HOST and SMTP_USER and SMTP_PASS):
        # Fallback to simulated delivery
        return True

    try:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"] = SYSTEM_EMAIL
        msg["To"] = to_email

        html_content = f"""
        <div style="font-family: Arial, sans-serif; padding: 20px; color: #333; line-height: 1.6;">
            <div style="background-color: #2563eb; color: white; padding: 15px; border-radius: 8px 8px 0 0;">
                <h2 style="margin: 0;">🚚 Last-Mile Delivery Tracker</h2>
            </div>
            <div style="border: 1px solid #e5e7eb; padding: 20px; border-radius: 0 0 8px 8px;">
                <p>{body_text.replace('\n', '<br>')}</p>
                <hr style="border: 0; border-top: 1px solid #eee; margin: 20px 0;">
                <small style="color: #6b7280;">This is an automated notification from Last-Mile Delivery Tracker.</small>
            </div>
        </div>
        """
        msg.attach(MIMEText(html_content, "html"))

        with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as server:
            server.starttls()
            server.login(SMTP_USER, SMTP_PASS)
            server.send_message(msg)
        return True
    except Exception as e:
        print(f"[Notification Engine] SMTP delivery failed: {e}")
        return False

def notify_order_status_change(db: Session, order: Order, previous_status: str, new_status: str, custom_notes: str = ""):
    """
    Dispatches notifications via Email and SMS log whenever order status changes.
    Appends entry to NotificationLog database table.
    """
    customer = order.customer
    if not customer or not customer.email:
        return

    subject = f"Order #{order.tracking_number} Update: {new_status}"
    message = (
        f"Hello {customer.name},\n\n"
        f"Your order (Tracking #: {order.tracking_number}) status has been updated.\n"
        f"Status: {previous_status} ➔ {new_status}\n"
    )
    if custom_notes:
        message += f"Details: {custom_notes}\n"

    message += f"\nTotal Amount: ₹{order.total_charge:.2f} ({order.payment_type})\n"
    message += f"Pickup: {order.pickup_address}\n"
    message += f"Dropoff: {order.drop_address}\n"

    # Send Email
    email_sent = send_actual_email(customer.email, subject, message)

    # Log Email Notification
    email_log = NotificationLog(
        order_id=order.id,
        recipient_email=customer.email,
        recipient_phone=customer.phone,
        channel="EMAIL",
        subject=subject,
        message=message,
        status="SENT" if email_sent else "FAILED"
    )
    db.add(email_log)

    # Log SMS Notification (Simulated SMS Gateway)
    sms_text = f"Delivery Update: Order #{order.tracking_number} status is now '{new_status}'. Track live on dashboard."
    sms_log = NotificationLog(
        order_id=order.id,
        recipient_email=customer.email,
        recipient_phone=customer.phone or "N/A",
        channel="SMS",
        subject=f"SMS Notification for {order.tracking_number}",
        message=sms_text,
        status="SENT"
    )
    db.add(sms_log)

    db.commit()
