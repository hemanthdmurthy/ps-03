import logging
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.notification import Notification
from app.utils.websocket_manager import manager

logger = logging.getLogger("company_intel.utils.notification_helper")

async def create_and_send_notification(
    db: AsyncSession,
    user_id: str,
    title: str,
    message: str,
    notification_type: str = "info"
) -> Notification:
    """
    Creates a persistent notification in the database, and immediately broadcasts 
    it via WebSocket if the target user is currently online.
    Uses async database session for non-blocking I/O.
    """
    # 1. Create persistent Notification row
    notification = Notification(
        user_id=user_id,
        title=title,
        message=message,
        type=notification_type,
        is_read=False
    )

    try:
        db.add(notification)
        await db.commit()
        await db.refresh(notification)
        logger.info(f"[Notification Helper] Saved persistent alert '{title}' for user '{user_id}' (ID: {notification.id})")

        # 2. Offload heavy email dispatch and WebSocket broadcasting asynchronously to Celery worker
        from app.tasks.notification_tasks import send_notification_task
        # Dispatch Celery background task immediately
        send_notification_task.delay(
            user_id=user_id,
            title=title,
            message=message,
            notification_type=notification_type
        )
        logger.info(f"[Notification Helper] Asynchronously dispatched email/push task to Celery worker for user '{user_id}'")

    except Exception as e:
        await db.rollback()
        logger.error(f"[Notification Helper] Failed to save notification for user '{user_id}': {e}")
        raise e

    return notification
