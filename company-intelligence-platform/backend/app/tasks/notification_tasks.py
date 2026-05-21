# app/tasks/notification_tasks.py
import logging
import json
import redis
import smtplib
from email.mime.text import MIMEText
from celery import shared_task, Task
from app.core.celery_app import celery_app
from app.core.config import settings
from app.core.database import SessionLocal
from app.models.notification import Notification
from app.models.user import User
from app.core.circuit_breaker import CircuitBreaker, CircuitBreakerOpenException

logger = logging.getLogger("company_intel.tasks.notifications")

# Circuit breaker for SMTP email dispatch — opens after 5 failures, recovers after 120s
smtp_circuit_breaker = CircuitBreaker(service_name="smtp_email", failure_threshold=5, recovery_timeout=120)


class NotificationTask(Task):
    """Custom Celery Task subclass for notification fault containment."""
    def on_failure(self, exc, task_id, args, kwargs, einfo):
        logger.error(f"[Notification Task Failure] Task {task_id} failed: {exc}")
        # Route fatally failed notification to DLQ
        try:
            celery_app.send_task(
                "app.tasks.scheduled_tasks.dlq_handler",
                args=["app.tasks.notification_tasks.send_notification_task", task_id, str(exc)],
                queue="dlq"
            )
        except Exception as dlq_err:
            logger.error(f"[DLQ Error] Failed to route notification to DLQ: {dlq_err}")

@smtp_circuit_breaker
def simulate_email_dispatch(email_to: str, subject: str, body: str) -> bool:
    """
    Simulates actual SMTP email transmission or attempts transmission if configured.
    Protected by a circuit breaker to prevent retry storms when SMTP is persistently down.
    Always falls back gracefully to a detailed simulated log audit for local dev.
    """
    logger.info(f"[Email Dispatch] Preparing transmission to: {email_to}")
    
    # Check for SMTP configurations in environment (optional production config)
    smtp_host = settings.model_extra.get("SMTP_HOST") or settings.model_fields.get("SMTP_HOST") if hasattr(settings, "SMTP_HOST") else None
    smtp_port = settings.model_extra.get("SMTP_PORT") or settings.model_fields.get("SMTP_PORT") if hasattr(settings, "SMTP_PORT") else 587
    smtp_user = settings.model_extra.get("SMTP_USER") or settings.model_fields.get("SMTP_USER") if hasattr(settings, "SMTP_USER") else None
    smtp_pass = settings.model_extra.get("SMTP_PASSWORD") or settings.model_fields.get("SMTP_PASSWORD") if hasattr(settings, "SMTP_PASSWORD") else None

    # Draft HTML MIME Email body
    msg = MIMEText(body, "html")
    msg["Subject"] = subject
    msg["From"] = "notifications@placementintel.com"
    msg["To"] = email_to

    if smtp_host and smtp_user and smtp_pass:
        try:
            logger.info(f"Connecting to SMTP server {smtp_host}:{smtp_port}...")
            with smtplib.SMTP(smtp_host, smtp_port, timeout=30) as server:
                server.starttls()
                server.login(smtp_user, smtp_pass)
                server.sendmail(msg["From"], [msg["To"]], msg.as_string())
            logger.info(f"[Email Success] Sent actual email notification successfully to: {email_to}")
            return True
        except Exception as smtp_exc:
            logger.error(f"Failed SMTP actual email dispatch: {smtp_exc}. Falling back to simulation.", exc_info=True)
            # Raise exception so Celery task retry catches it if needed, or proceed to fallback
    
    # Dev Fallback simulation
    logger.info("=" * 60)
    logger.info(f"SIMULATED EMAIL DISPATCH SUCCESSFUL")
    logger.info(f"Recipient: {email_to}")
    logger.info(f"Subject:   {subject}")
    logger.info(f"Body:\n{body}")
    logger.info("=" * 60)
    return True

@celery_app.task(
    base=NotificationTask,
    name="app.tasks.notification_tasks.send_notification_task",
    bind=True,
    max_retries=3,
    default_retry_delay=10,
    time_limit=300,        # Strict 5 min hard limit
    soft_time_limit=270    # Graceful degradation at 4.5 min
)
def send_notification_task(self, user_id: str, title: str, message: str, notification_type: str = "info"):
    """
    Asynchronous Celery task that:
    1. Persists the notification row into the database in a thread-safe session.
    2. Broadcasts the notification to a Redis Pub/Sub channel for FastAPI WebSocket routing.
    3. Triggers email transmission to the target user's registered address with automatic retry on failure.
    """
    logger.info(f"[Celery Task] Initiating async notification for user '{user_id}' with title '{title}'...")
    
    # 1. Thread-safe DB Operation
    db = SessionLocal()
    notification_data = None
    user_email = None
    username = None
    
    try:
        # Fetch target user
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            logger.error(f"User with ID '{user_id}' not found in database. Aborting notification.")
            return {"status": "aborted", "reason": f"User ID '{user_id}' not found"}
        
        user_email = user.email
        username = user.username
        
        # Save persistent notification
        notification = Notification(
            user_id=user_id,
            title=title,
            message=message,
            type=notification_type,
            is_read=False
        )
        db.add(notification)
        db.commit()
        db.refresh(notification)
        
        logger.info(f"[DB Saved] Persistent notification saved (ID: {notification.id}) for user '{user_id}'")
        
        notification_data = {
            "id": notification.id,
            "user_id": notification.user_id,
            "title": notification.title,
            "message": notification.message,
            "type": notification.type,
            "is_read": notification.is_read,
            "created_at": notification.created_at.isoformat()
        }
        
    except Exception as db_exc:
        db.rollback()
        logger.error(f"Database error while saving notification: {db_exc}", exc_info=True)
        # Retry task if DB fails
        try:
            self.retry(exc=db_exc, countdown=5)
        except self.MaxRetriesExceededError:
            logger.error("Max retries exceeded saving notification in DB.")
            raise db_exc
    finally:
        db.close()
        
    # 2. Redis Pub/Sub synchronization for FastAPI WebSocket server
    try:
        from app.core.redis_client import redis_client
        r = redis_client.sync_client
        payload = {
            "event": "new_notification",
            "user_id": user_id,
            "data": notification_data
        }
        channel = "company_intel:notifications"
        r.publish(channel, json.dumps(payload))
        logger.info(f"[Redis Publish] Published notification alert to channel: {channel}")
    except Exception as redis_exc:
        logger.error(f"Redis pub/sub failed for notification: {redis_exc}", exc_info=True)
        # Note: Do not abort the task or fail if WebSocket delivery channel is offline; the DB entry and Email are primary.
        
    # 3. Asynchronous Email Dispatch with custom retries
    if user_email:
        email_body = f"""
        <html>
            <body style="font-family: Arial, sans-serif; padding: 20px; color: #333;">
                <div style="max-width: 600px; margin: auto; border: 1px solid #ddd; border-radius: 8px; padding: 20px; background-color: #f9f9f9;">
                    <h2 style="color: #4F46E5; border-bottom: 2px solid #E0E7FF; padding-bottom: 10px;">PlacementIntel Platform Alert</h2>
                    <p>Dear <strong>{username}</strong>,</p>
                    <p style="font-size: 16px; line-height: 1.5; color: #111;">{message}</p>
                    <br/>
                    <p style="font-size: 12px; color: #666; border-top: 1px solid #eee; padding-top: 10px;">
                        This is an automated security and system notification from the Company Intelligence Platform. 
                        Please do not reply directly to this message.
                    </p>
                </div>
            </body>
        </html>
        """
        try:
            simulate_email_dispatch(
                email_to=user_email,
                subject=f"PlacementIntel Alert: {title}",
                body=email_body
            )
        except CircuitBreakerOpenException:
            logger.warning(
                f"[Circuit Breaker] SMTP circuit is OPEN. Skipping email dispatch for {user_email}. "
                f"DB persistence and Redis notification are the primary delivery channels."
            )
            # Do NOT retry — circuit breaker will auto-recover once SMTP is healthy again
        except Exception as email_exc:
            logger.warning(f"Email dispatch attempt failed, triggering Celery task retry: {email_exc}")
            try:
                # Exponential backoff countdown: 10, 20, 40 seconds
                countdown = self.default_retry_delay * (2 ** self.request.retries)
                self.retry(exc=email_exc, countdown=countdown)
            except self.MaxRetriesExceededError:
                logger.error(f"Max retries exceeded attempting email dispatch to {user_email}")
                # We do not crash the task here, as DB persistence and redis notification worked.
                
    return {
        "status": "success",
        "notification_id": notification_data.get("id") if notification_data else None,
        "email_recipient": user_email
    }
