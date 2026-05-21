import logging
from typing import List, Optional
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, status, Query, WebSocket, WebSocketDisconnect
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies.db_deps import get_async_db
from app.dependencies.auth_deps import get_current_user
from app.models.user import User
from app.models.notification import Notification
from app.schemas.notification_schemas import NotificationResponse, NotificationMarkRead
from app.utils.notification_helper import create_and_send_notification
from app.utils.websocket_manager import manager

logger = logging.getLogger("company_intel.routes.notification")

router = APIRouter(prefix="/notifications", tags=["Notifications & WebSockets"])


@router.post("/trigger-test", response_model=NotificationResponse)
async def trigger_test_notification(current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_async_db)):
    notification = await create_and_send_notification(
        db=db, user_id=current_user.id, title="Test Real-Time Notification",
        message=f"Hello {current_user.username}! This is a live WebSocket push alert generated at {datetime.utcnow().isoformat()}.",
        notification_type="system"
    )
    return notification


@router.get("", response_model=List[NotificationResponse])
async def list_user_notifications(is_read: Optional[bool] = Query(None), skip: int = Query(0, ge=0), limit: int = Query(100, ge=1), current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_async_db)):
    stmt = select(Notification).filter(Notification.user_id == current_user.id)
    if is_read is not None:
        stmt = stmt.filter(Notification.is_read == is_read)
    result = await db.execute(stmt.order_by(Notification.created_at.desc()).offset(skip).limit(limit))
    return result.scalars().all()


@router.put("/{notification_id}", response_model=NotificationResponse)
async def update_notification_status(notification_id: str, payload: NotificationMarkRead, current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_async_db)):
    result = await db.execute(select(Notification).filter(Notification.id == notification_id, Notification.user_id == current_user.id))
    notification = result.scalars().first()
    if not notification:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Notification with ID '{notification_id}' not found.")
    notification.is_read = payload.is_read
    await db.commit()
    await db.refresh(notification)
    return notification


@router.post("/mark-all-read", status_code=status.HTTP_200_OK)
async def mark_all_notifications_as_read(current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_async_db)):
    result = await db.execute(select(Notification).filter(Notification.user_id == current_user.id, Notification.is_read == False))
    unread = result.scalars().all()
    for notification in unread:
        notification.is_read = True
    await db.commit()
    return {"status": "success", "message": f"Successfully marked {len(unread)} notifications as read."}


@router.websocket("/ws/{user_id}")
async def websocket_notification_endpoint(websocket: WebSocket, user_id: str):
    """
    Accepts real-time WebSockets connection to register user device channels
    and push real-time alerts. Handles ping heartbeats cleanly.
    """
    await manager.connect(user_id, websocket)
    try:
        while True:
            data = await websocket.receive_text()
            if data == "ping" or data.strip().lower() == '{"event":"ping"}':
                await websocket.send_json({"event": "pong", "data": "heartbeat acknowledged"})
            else:
                await websocket.send_json({"event": "echo", "data": data})
    except WebSocketDisconnect:
        manager.disconnect(user_id, websocket)
        logger.info(f"[WebSocket Disconnect] Device disconnected cleanly for user '{user_id}'.")
    except Exception as e:
        manager.disconnect(user_id, websocket)
        logger.error(f"[WebSocket Error] Connection crash/exception for user '{user_id}': {e}")
