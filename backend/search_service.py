"""Advanced search and filtering service for warehouse system."""

from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
from motor.motor_asyncio import AsyncIOMotorDatabase
import uuid


class SearchService:
    def __init__(self, db: AsyncIOMotorDatabase):
        self.db = db

    async def initialize_indexes(self) -> None:
        """Create necessary indexes for search functionality."""
        try:
            # Text search indexes
            await self.db.inventory.create_index([("sku", "text"), ("name", "text"), ("category", "text")])
            await self.db.orders.create_index([("reference", "text"), ("destination", "text")])

            # Regular indexes for filtering
            await self.db.inventory.create_index("category")
            await self.db.inventory.create_index("zone")
            await self.db.inventory.create_index("quantity")
            await self.db.inventory.create_index("reorder_threshold")

            await self.db.orders.create_index("status")
            await self.db.orders.create_index("priority")
            await self.db.orders.create_index("created_at")

            # User filter indexes
            await self.db.saved_filters.create_index("user_id")
            await self.db.saved_filters.create_index("created_at")
        except Exception as e:
            raise RuntimeError(f"Failed to create search indexes: {e}")

    async def search_inventory(
        self,
        query: Optional[str] = None,
        filters: Optional[Dict[str, Any]] = None,
        skip: int = 0,
        limit: int = 100,
    ) -> Dict[str, Any]:
        """
        Search inventory with optional full-text search and filters.
        
        Query: search in sku, name, category
        Filters: {
            "category": "Hardware",
            "status": "low",  # healthy, low, critical
            "qty_range": {"min": 0, "max": 100},
            "zone": "A"
        }
        """
        match_filters = {}

        if query:
            # Text search on multiple fields
            match_filters["$text"] = {"$search": query}

        # Apply category filter
        if filters and "category" in filters:
            match_filters["category"] = filters["category"]

        # Apply zone filter
        if filters and "zone" in filters:
            match_filters["zone"] = filters["zone"]

        # Apply quantity range filter
        if filters and "qty_range" in filters:
            qty_range = filters["qty_range"]
            match_filters["quantity"] = {}
            if "min" in qty_range:
                match_filters["quantity"]["$gte"] = qty_range["min"]
            if "max" in qty_range:
                match_filters["quantity"]["$lte"] = qty_range["max"]

        # Calculate stock status and filter
        pipeline = [
            {"$match": match_filters} if match_filters else {"$match": {}},
            {
                "$addFields": {
                    "stock_status": {
                        "$cond": [
                            {"$lte": ["$quantity", {"$multiply": ["$reorder_threshold", 0.5]}]},
                            "critical",
                            {
                                "$cond": [
                                    {"$lte": ["$quantity", "$reorder_threshold"]},
                                    "low",
                                    "healthy",
                                ]
                            },
                        ]
                    }
                }
            },
        ]

        # Add status filter if specified
        if filters and "status" in filters:
            pipeline.append({"$match": {"stock_status": filters["status"]}})

        # Add sorting
        pipeline.append({"$sort": {"zone": 1, "bin_code": 1}})

        # Add pagination
        pipeline.append({"$skip": skip})
        pipeline.append({"$limit": limit})

        results = await self.db.inventory.aggregate(pipeline).to_list(None)

        # Get total count
        count_pipeline = [
            {"$match": match_filters} if match_filters else {"$match": {}},
        ]
        total = await self.db.inventory.count_documents(
            match_filters if match_filters else {}
        )

        return {
            "items": results,
            "total": total,
            "page": skip // limit,
            "per_page": limit,
        }

    async def search_orders(
        self,
        query: Optional[str] = None,
        filters: Optional[Dict[str, Any]] = None,
        skip: int = 0,
        limit: int = 100,
    ) -> Dict[str, Any]:
        """
        Search orders with optional full-text search and filters.
        
        Query: search in reference, destination
        Filters: {
            "status": "picking",  # queued, picking, packed, shipped
            "priority": "high",
            "date_range": {"start": "2026-03-20", "end": "2026-03-29"}
        }
        """
        match_filters = {}

        if query:
            match_filters["$text"] = {"$search": query}

        # Status filter
        if filters and "status" in filters:
            match_filters["status"] = filters["status"]

        # Priority filter
        if filters and "priority" in filters:
            match_filters["priority"] = filters["priority"]

        # Date range filter
        if filters and "date_range" in filters:
            date_range = filters["date_range"]
            match_filters["created_at"] = {}
            if "start" in date_range:
                match_filters["created_at"]["$gte"] = date_range["start"]
            if "end" in date_range:
                match_filters["created_at"]["$lte"] = date_range["end"]

        results = await self.db.orders.find(match_filters, {"_id": 0}).skip(skip).limit(limit).to_list(None)

        total = await self.db.orders.count_documents(match_filters)

        return {
            "orders": results,
            "total": total,
            "page": skip // limit,
            "per_page": limit,
        }

    async def save_filter(
        self,
        user_id: str,
        name: str,
        entity_type: str,  # "inventory", "orders"
        filters: Dict[str, Any],
    ) -> str:
        """Save a filter for later reuse."""
        filter_doc = {
            "id": str(uuid.uuid4()),
            "user_id": user_id,
            "name": name,
            "entity_type": entity_type,
            "filters": filters,
            "created_at": datetime.utcnow().isoformat(),
        }
        await self.db.saved_filters.insert_one(filter_doc)
        return filter_doc["id"]

    async def get_saved_filters(self, user_id: str, entity_type: Optional[str] = None) -> List[Dict]:
        """Get all saved filters for a user."""
        query = {"user_id": user_id}
        if entity_type:
            query["entity_type"] = entity_type

        filters = await self.db.saved_filters.find(query, {"_id": 0}).sort("created_at", -1).to_list(100)
        return filters

    async def delete_saved_filter(self, filter_id: str, user_id: str) -> bool:
        """Delete a saved filter."""
        result = await self.db.saved_filters.delete_one({"id": filter_id, "user_id": user_id})
        return result.deleted_count > 0

    async def get_search_suggestions(self, query: str, entity_type: str = "inventory") -> List[str]:
        """Get autocomplete suggestions based on query."""
        if entity_type == "inventory":
            # Search in inventory fields
            collection = self.db.inventory
            search_fields = ["sku", "name", "category"]
        else:
            # Search in orders fields
            collection = self.db.orders
            search_fields = ["reference", "destination"]

        suggestions = []
        for field in search_fields:
            pipeline = [
                {"$match": {field: {"$regex": f"^{query}", "$options": "i"}}},
                {"$group": {"_id": f"${field}"}},
                {"$sort": {"_id": 1}},
                {"$limit": 5},
            ]
            results = await collection.aggregate(pipeline).to_list(None)
            suggestions.extend([r["_id"] for r in results if r["_id"]])

        return list(set(suggestions))[:10]  # Return unique, limit to 10
