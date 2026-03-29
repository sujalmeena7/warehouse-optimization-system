"""Real-time notification service for warehouse events."""

import uuid
from typing import Dict, List, Optional, Any
from datetime import datetime, timezone
from motor.motor_asyncio import AsyncIOMotorDatabase


class NotificationService:
    def __init__(self, db: AsyncIOMotorDatabase):
        self.db = db
        self.active_connections: Dict[str, List] = {}  # user_id -> list of websocket connections

    async def create_indexes(self) -> None:
        """Create indexes for notification queries."""
        try:
            await self.db.notifications.create_index("user_id")
            await self.db.notifications.create_index("created_at")
            await self.db.notifications.create_index([("user_id", 1), ("read", 1)])
            await self.db.notifications.create_index([("user_id", 1), ("created_at", -1)])
        except Exception as e:
            raise RuntimeError(f"Failed to create notification indexes: {e}")

    async def send_notification(
        self,
        user_id: str,
        title: str,
        message: str,
        notification_type: str = "info",  # info, warning, critical
        severity: str = "info",
        entity_type: Optional[str] = None,
        entity_id: Optional[str] = None,
        action_url: Optional[str] = None,
    ) -> str:
        """
        Create and store a notification.

        Args:
            user_id: Target user
            title: Notification title
            message: Notification message
            notification_type: Type of notification (alert, update, etc.)
            severity: info, warning, critical
            entity_type: Type of entity (inventory, orders, etc.)
            entity_id: ID of related entity
            action_url: URL to navigate on click

        Returns:
            Notification ID
        """
        notification = {
            "id": str(uuid.uuid4()),
            "user_id": user_id,
            "title": title,
            "message": message,
            "type": notification_type,
            "severity": severity,
            "entity_type": entity_type,
            "entity_id": entity_id,
            "action_url": action_url,
            "read": False,
            "created_at": datetime.now(timezone.utc).isoformat(),
        }

        await self.db.notifications.insert_one(notification)
        return notification["id"]

    async def notify_low_stock(
        self, user_ids: List[str], item_sku: str, item_name: str, quantity: int, threshold: int
    ) -> List[str]:
        """Send low stock alert to specified users."""
        notification_ids = []
        for user_id in user_ids:
            notif_id = await self.send_notification(
                user_id,
                "Low Stock Alert 📉",
                f"{item_name} ({item_sku}) is below reorder threshold: {quantity} units (threshold: {threshold})",
                notification_type="stock_alert",
                severity="warning",
                entity_type="inventory",
                entity_id=item_sku,
                action_url=f"/inventory",
            )
            notification_ids.append(notif_id)
        return notification_ids

    async def notify_overdue_order(
        self, user_ids: List[str], order_ref: str, destination: str, days_overdue: int
    ) -> List[str]:
        """Send overdue order alert to specified users."""
        notification_ids = []
        for user_id in user_ids:
            notif_id = await self.send_notification(
                user_id,
                "Overdue Order ⏰",
                f"Order {order_ref} to {destination} is {days_overdue} days overdue",
                notification_type="order_alert",
                severity="critical",
                entity_type="orders",
                entity_id=order_ref,
                action_url=f"/orders",
            )
            notification_ids.append(notif_id)
        return notification_ids

    async def notify_all_users(self, title: str, message: str, severity: str = "info") -> List[str]:
        """Send system-wide notification to all active users."""
        # Get all user IDs
        users = await self.db.users.find({}).to_list(100000)
        user_ids = [user["id"] for user in users]

        notification_ids = []
        for user_id in user_ids:
            notif_id = await self.send_notification(
                user_id,
                title,
                message,
                notification_type="system",
                severity=severity,
            )
            notification_ids.append(notif_id)
        return notification_ids

    async def get_user_notifications(
        self, user_id: str, limit: int = 50, skip: int = 0
    ) -> Dict[str, Any]:
        """Get paginated notifications for user."""
        notifications = await self.db.notifications.find(
            {"user_id": user_id}
        ).sort("created_at", -1).skip(skip).limit(limit).to_list(None)

        total = await self.db.notifications.count_documents({"user_id": user_id})
        unread = await self.db.notifications.count_documents(
            {"user_id": user_id, "read": False}
        )

        return {
            "notifications": notifications,
            "total": total,
            "unread": unread,
            "page": skip // limit,
            "per_page": limit,
        }

    async def get_unread_count(self, user_id: str) -> int:
        """Get count of unread notifications for user."""
        return await self.db.notifications.count_documents(
            {"user_id": user_id, "read": False}
        )

    async def mark_as_read(self, notification_id: str, user_id: str) -> bool:
        """Mark notification as read."""
        result = await self.db.notifications.update_one(
            {"id": notification_id, "user_id": user_id},
            {"$set": {"read": True}},
        )
        return result.modified_count > 0

    async def mark_all_as_read(self, user_id: str) -> int:
        """Mark all unread notifications as read."""
        result = await self.db.notifications.update_many(
            {"user_id": user_id, "read": False},
            {"$set": {"read": True}},
        )
        return result.modified_count

    async def delete_notification(self, notification_id: str, user_id: str) -> bool:
        """Delete a notification."""
        result = await self.db.notifications.delete_one(
            {"id": notification_id, "user_id": user_id}
        )
        return result.deleted_count > 0

    async def delete_old_notifications(self, user_id: str, days: int = 30) -> int:
        """Delete notifications older than specified days."""
        from datetime import timedelta
        cutoff_date = datetime.now(timezone.utc) - timedelta(days=days)
        result = await self.db.notifications.delete_many({
            "user_id": user_id,
            "created_at": {"$lt": cutoff_date.isoformat()}
        })
        return result.deleted_count

    # WebSocket connection management
    def connect(self, user_id: str, websocket) -> None:
        """Register a WebSocket connection for a user."""
        if user_id not in self.active_connections:
            self.active_connections[user_id] = []
        self.active_connections[user_id].append(websocket)

    def disconnect(self, user_id: str, websocket) -> None:
        """Remove a WebSocket connection."""
        if user_id in self.active_connections:
            self.active_connections[user_id].remove(websocket)
            if not self.active_connections[user_id]:
                del self.active_connections[user_id]

    async def broadcast_to_user(self, user_id: str, message: Dict[str, Any]) -> None:
        """Send message to all active WebSocket connections for a user."""
        if user_id in self.active_connections:
            for connection in self.active_connections[user_id]:
                try:
                    await connection.send_json(message)
                except Exception as e:
                    # Connection might be closed, skip it
                    pass

    async def broadcast_to_all(self, message: Dict[str, Any]) -> None:
        """Send message to all active WebSocket connections."""
        for user_id, connections in self.active_connections.items():
            for connection in connections:
                try:
                    await connection.send_json(message)
                except Exception as e:
                    pass
