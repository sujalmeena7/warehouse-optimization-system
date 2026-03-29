"""Audit logging utilities for tracking all system actions."""
from datetime import datetime, timezone
from typing import Any, Dict, Optional
from motor.motor_asyncio import AsyncIOMotorDatabase
import uuid


async def log_action(
    db: AsyncIOMotorDatabase,
    action: str,
    user_id: str,
    user_email: str,
    entity_type: str,
    entity_id: str,
    entity_details: str = "",
    old_value: Optional[Dict[str, Any]] = None,
    new_value: Optional[Dict[str, Any]] = None,
    ip_address: str = "0.0.0.0",
    status: str = "success",
    error_message: Optional[str] = None,
) -> str:
    """
    Log an action to the immutable audit log.

    Args:
        db: MongoDB database instance
        action: CREATE, UPDATE, DELETE, RETRIEVE
        user_id: ID of the user who performed the action
        user_email: Email of the user
        entity_type: Type of entity (inventory, order, container, user, layout)
        entity_id: ID of the entity affected
        entity_details: Name or SKU or other identifying details
        old_value: Previous state of the entity (for UPDATE actions)
        new_value: New state of the entity (for CREATE/UPDATE)
        ip_address: IP address of the request
        status: success or failure
        error_message: Error message if status == failure

    Returns:
        The audit log ID
    """
    # Determine what fields changed
    changes = []
    if old_value and new_value:
        for key in set(list(old_value.keys()) + list(new_value.keys())):
            if old_value.get(key) != new_value.get(key):
                changes.append(key)

    audit_log = {
        "id": str(uuid.uuid4()),
        "action": action,
        "user_id": user_id,
        "user_email": user_email,
        "entity_type": entity_type,
        "entity_id": entity_id,
        "entity_details": entity_details,
        "old_value": old_value,
        "new_value": new_value,
        "changes": changes,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "ip_address": ip_address,
        "status": status,
        "error_message": error_message,
    }

    await db.audit_logs.insert_one(audit_log)
    return audit_log["id"]


async def get_audit_logs(
    db: AsyncIOMotorDatabase,
    user_id: Optional[str] = None,
    entity_type: Optional[str] = None,
    action: Optional[str] = None,
    limit: int = 100,
    skip: int = 0,
) -> list:
    """
    Retrieve audit logs with optional filtering.

    Args:
        db: MongoDB database instance
        user_id: Filter by specific user
        entity_type: Filter by entity type
        action: Filter by action type
        limit: Maximum number of results
        skip: Number of results to skip

    Returns:
        List of audit log documents
    """
    query = {}
    if user_id:
        query["user_id"] = user_id
    if entity_type:
        query["entity_type"] = entity_type
    if action:
        query["action"] = action

    logs = (
        await db.audit_logs.find(query, {"_id": 0})
        .sort("timestamp", -1)
        .skip(skip)
        .limit(limit)
        .to_list(limit)
    )
    return logs


async def get_entity_audit_trail(
    db: AsyncIOMotorDatabase,
    entity_type: str,
    entity_id: str,
) -> list:
    """
    Get complete audit trail for a specific entity.

    Returns all changes made to the entity in chronological order.
    """
    logs = (
        await db.audit_logs.find(
            {"entity_type": entity_type, "entity_id": entity_id},
            {"_id": 0},
        )
        .sort("timestamp", 1)
        .to_list(500)
    )
    return logs


def create_audit_record(
    action: str,
    user_id: str,
    user_email: str,
    entity_type: str,
    entity_id: str,
    entity_details: str = "",
    old_value: Optional[Dict[str, Any]] = None,
    new_value: Optional[Dict[str, Any]] = None,
    ip_address: str = "0.0.0.0",
    status: str = "success",
    error_message: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Create an audit record (non-async version for testing).

    Returns the audit record dict without inserting to database.
    """
    changes = []
    if old_value and new_value:
        for key in set(list(old_value.keys()) + list(new_value.keys())):
            if old_value.get(key) != new_value.get(key):
                changes.append(key)

    return {
        "id": str(uuid.uuid4()),
        "action": action,
        "user_id": user_id,
        "user_email": user_email,
        "entity_type": entity_type,
        "entity_id": entity_id,
        "entity_details": entity_details,
        "old_value": old_value,
        "new_value": new_value,
        "changes": changes,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "ip_address": ip_address,
        "status": status,
        "error_message": error_message,
    }


async def create_audit_indexes(db: AsyncIOMotorDatabase) -> None:
    """Create required indexes for efficient audit log queries."""
    # Ensure audit_logs collection exists and has indexes
    await db.audit_logs.create_index("user_id")
    await db.audit_logs.create_index("entity_type")
    await db.audit_logs.create_index("entity_id")
    await db.audit_logs.create_index("action")
    await db.audit_logs.create_index("timestamp")
    await db.audit_logs.create_index([("entity_type", 1), ("entity_id", 1)])
