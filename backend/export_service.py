"""CSV/Excel export service for warehouse data."""

import csv
import io
from typing import Dict, List, Optional, Any
from datetime import datetime
from motor.motor_asyncio import AsyncIOMotorDatabase


class ExportService:
    def __init__(self, db: AsyncIOMotorDatabase):
        self.db = db

    async def export_inventory_csv(
        self,
        selected_columns: Optional[List[str]] = None,
        filters: Optional[Dict[str, Any]] = None,
    ) -> str:
        """
        Export inventory to CSV format.

        Args:
            selected_columns: List of column names to export
            filters: MongoDB query filters

        Returns:
            CSV string
        """
        # Default columns if none selected
        if not selected_columns:
            selected_columns = ["sku", "name", "category", "quantity", "bin_code", "zone", "reorder_threshold"]

        # Query inventory
        query = filters or {}
        inventory_items = await self.db.inventory.find(query).to_list(10000)

        # Create CSV
        output = io.StringIO()
        writer = csv.DictWriter(output, fieldnames=selected_columns)
        writer.writeheader()

        for item in inventory_items:
            row = {}
            for col in selected_columns:
                row[col] = item.get(col, "")
            writer.writerow(row)

        return output.getvalue()

    async def export_orders_csv(
        self,
        selected_columns: Optional[List[str]] = None,
        filters: Optional[Dict[str, Any]] = None,
    ) -> str:
        """
        Export orders to CSV format.

        Args:
            selected_columns: List of column names to export
            filters: MongoDB query filters

        Returns:
            CSV string
        """
        if not selected_columns:
            selected_columns = ["reference", "destination", "status", "priority", "picker", "created_at"]

        query = filters or {}
        orders = await self.db.orders.find(query).to_list(10000)

        output = io.StringIO()
        writer = csv.DictWriter(output, fieldnames=selected_columns)
        writer.writeheader()

        for order in orders:
            row = {}
            for col in selected_columns:
                # Handle nested items field special case
                if col == "items":
                    row[col] = len(order.get("items", []))
                elif col == "item_count":
                    row[col] = len(order.get("items", []))
                else:
                    row[col] = order.get(col, "")
            writer.writerow(row)

        return output.getvalue()

    async def export_analytics_csv(
        self,
        selected_columns: Optional[List[str]] = None,
    ) -> str:
        """
        Export analytics summary to CSV format.

        Args:
            selected_columns: List of column names to export

        Returns:
            CSV string
        """
        if not selected_columns:
            selected_columns = ["metric", "value", "timestamp"]

        # Build analytics data
        inventory_count = await self.db.inventory.count_documents({})
        orders_count = await self.db.orders.count_documents({})
        total_qty = 0
        total_value = 0

        async for item in self.db.inventory.find({}):
            total_qty += item.get("quantity", 0)
            unit_cost = item.get("unit_cost", 0)
            qty = item.get("quantity", 0)
            total_value += unit_cost * qty

        # Low stock items
        low_stock = await self.db.inventory.count_documents(
            {"$expr": {"$lte": ["$quantity", "$reorder_threshold"]}}
        )

        # Orders by status
        completed_orders = await self.db.orders.count_documents({"status": "shipped"})

        analytics_data = [
            {"metric": "Total Inventory Items", "value": inventory_count, "timestamp": datetime.utcnow().isoformat()},
            {"metric": "Total Orders", "value": orders_count, "timestamp": datetime.utcnow().isoformat()},
            {"metric": "Total Quantity in Stock", "value": total_qty, "timestamp": datetime.utcnow().isoformat()},
            {"metric": "Total Inventory Value", "value": f"${total_value:,.2f}", "timestamp": datetime.utcnow().isoformat()},
            {"metric": "Low Stock Items", "value": low_stock, "timestamp": datetime.utcnow().isoformat()},
            {"metric": "Completed Orders", "value": completed_orders, "timestamp": datetime.utcnow().isoformat()},
        ]

        output = io.StringIO()
        writer = csv.DictWriter(output, fieldnames=selected_columns)
        writer.writeheader()

        for row in analytics_data:
            filtered_row = {}
            for col in selected_columns:
                filtered_row[col] = row.get(col, "")
            writer.writerow(filtered_row)

        return output.getvalue()

    def get_available_columns(self, entity_type: str) -> Dict[str, List[str]]:
        """Get available columns for each entity type."""
        columns = {
            "inventory": [
                "sku",
                "name",
                "category",
                "quantity",
                "bin_code",
                "zone",
                "reorder_threshold",
                "lead_time_days",
                "unit_cost",
                "last_restocked",
            ],
            "orders": [
                "reference",
                "destination",
                "status",
                "priority",
                "picker",
                "created_at",
                "updated_at",
                "item_count",
            ],
            "analytics": [
                "metric",
                "value",
                "timestamp",
            ],
        }
        return columns.get(entity_type, [])
