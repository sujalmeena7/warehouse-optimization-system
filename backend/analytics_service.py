"""Advanced analytics service for warehouse KPIs and metrics."""

from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta, timezone
from motor.motor_asyncio import AsyncIOMotorDatabase


class AnalyticsService:
    def __init__(self, db: AsyncIOMotorDatabase):
        self.db = db

    async def get_kpis(self, time_range: str = "today") -> Dict[str, Any]:
        """
        Get key performance indicators.

        Args:
            time_range: "today", "week", "month", "year"

        Returns:
            KPI dictionary
        """
        now = datetime.now(timezone.utc)

        if time_range == "today":
            start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        elif time_range == "week":
            start = now - timedelta(days=7)
        elif time_range == "month":
            start = now - timedelta(days=30)
        else:  # year
            start = now - timedelta(days=365)

        # Get orders metrics
        orders_query = {"created_at": {"$gte": start.isoformat()}}
        total_orders = await self.db.orders.count_documents(orders_query)
        completed_orders = await self.db.orders.count_documents({
            **orders_query,
            "status": "shipped"
        })
        overdue_orders = await self.db.orders.count_documents({
            **orders_query,
            "status": {"$in": ["queued", "picking", "packed"]},
            "created_at": {"$lt": (now - timedelta(days=2)).isoformat()}
        })

        # Get inventory metrics
        inventory = await self.db.inventory.find({}).to_list(10000)
        total_items = len(inventory)
        total_qty = sum(item.get("quantity", 0) for item in inventory)
        total_value = sum(
            item.get("quantity", 0) * item.get("unit_cost", 0)
            for item in inventory
        )
        low_stock = sum(
            1 for item in inventory
            if item.get("quantity", 0) <= item.get("reorder_threshold", 0)
        )
        critical_stock = sum(
            1 for item in inventory
            if item.get("quantity", 0) <= item.get("reorder_threshold", 0) * 0.5
        )

        # Calculate metrics
        fulfillment_rate = (completed_orders / total_orders * 100) if total_orders > 0 else 0

        # Average pick time (mock calculation based on orders)
        avg_pick_time = 8.5  # Simplified for now

        # Space utilization (mock)
        space_utilization = 65.5

        # Inventory turnover
        monthly_orders = await self.db.orders.count_documents({
            "created_at": {"$gte": (now - timedelta(days=30)).isoformat()},
            "status": "shipped"
        })
        inventory_turnover = (monthly_orders / total_items * 12) if total_items > 0 else 0

        return {
            "orders_today": total_orders,
            "orders_completed": completed_orders,
            "overdue_orders": overdue_orders,
            "fulfillment_rate": round(fulfillment_rate, 1),
            "total_items": total_items,
            "total_quantity": total_qty,
            "inventory_value": round(total_value, 2),
            "low_stock_items": low_stock,
            "critical_stock_items": critical_stock,
            "avg_pick_time": avg_pick_time,
            "space_utilization": space_utilization,
            "inventory_turnover": round(inventory_turnover, 2),
            "time_range": time_range,
            "generated_at": now.isoformat()
        }

    async def get_inventory_metrics(self) -> Dict[str, Any]:
        """Get detailed inventory metrics."""
        inventory = await self.db.inventory.find({}).to_list(10000)

        categories = {}
        zones = {}
        total_value = 0

        for item in inventory:
            # By category
            cat = item.get("category", "Unknown")
            if cat not in categories:
                categories[cat] = {"count": 0, "qty": 0, "value": 0}
            categories[cat]["count"] += 1
            categories[cat]["qty"] += item.get("quantity", 0)
            categories[cat]["value"] += item.get("quantity", 0) * item.get("unit_cost", 0)

            # By zone
            zone = item.get("zone", "Unknown")
            if zone not in zones:
                zones[zone] = {"count": 0, "qty": 0, "value": 0}
            zones[zone]["count"] += 1
            zones[zone]["qty"] += item.get("quantity", 0)
            zones[zone]["value"] += item.get("quantity", 0) * item.get("unit_cost", 0)

            total_value += item.get("quantity", 0) * item.get("unit_cost", 0)

        return {
            "total_items": len(inventory),
            "total_quantity": sum(i.get("quantity", 0) for i in inventory),
            "total_value": round(total_value, 2),
            "by_category": [
                {
                    "category": cat,
                    "items": v["count"],
                    "quantity": v["qty"],
                    "value": round(v["value"], 2)
                }
                for cat, v in categories.items()
            ],
            "by_zone": [
                {
                    "zone": zone,
                    "items": v["count"],
                    "quantity": v["qty"],
                    "value": round(v["value"], 2)
                }
                for zone, v in zones.items()
            ]
        }

    async def get_order_metrics(self, days: int = 30) -> Dict[str, Any]:
        """Get order fulfillment metrics."""
        start = datetime.now(timezone.utc) - timedelta(days=days)

        orders = await self.db.orders.find({
            "created_at": {"$gte": start.isoformat()}
        }).to_list(10000)

        statuses = {"queued": 0, "picking": 0, "packed": 0, "shipped": 0}
        priorities = {"low": 0, "medium": 0, "high": 0}
        total_items = 0

        for order in orders:
            statuses[order.get("status", "queued")] = statuses.get(order.get("status", "queued"), 0) + 1
            priorities[order.get("priority", "medium")] = priorities.get(order.get("priority", "medium"), 0) + 1
            total_items += len(order.get("items", []))

        shipped = statuses.get("shipped", 0)
        fulfillment_rate = (shipped / len(orders) * 100) if orders else 0

        return {
            "total_orders": len(orders),
            "total_items_ordered": total_items,
            "fulfillment_rate": round(fulfillment_rate, 1),
            "by_status": [
                {"status": k, "count": v} for k, v in statuses.items()
            ],
            "by_priority": [
                {"priority": k, "count": v} for k, v in priorities.items()
            ],
            "period_days": days,
            "generated_at": datetime.now(timezone.utc).isoformat()
        }

    async def get_performance_trends(self, days: int = 30) -> Dict[str, Any]:
        """Get performance trend data."""
        trends = []
        now = datetime.now(timezone.utc)

        for i in range(days, 0, -1):
            date = now - timedelta(days=i)
            start = date.replace(hour=0, minute=0, second=0, microsecond=0)
            end = start + timedelta(days=1)

            orders = await self.db.orders.count_documents({
                "created_at": {
                    "$gte": start.isoformat(),
                    "$lt": end.isoformat()
                }
            })

            shipped = await self.db.orders.count_documents({
                "created_at": {
                    "$gte": start.isoformat(),
                    "$lt": end.isoformat()
                },
                "status": "shipped"
            })

            fulfillment = (shipped / orders * 100) if orders > 0 else 0

            trends.append({
                "date": date.date().isoformat(),
                "orders": orders,
                "shipped": shipped,
                "fulfillment_rate": round(fulfillment, 1)
            })

        return {
            "period_days": days,
            "trends": trends,
            "generated_at": now.isoformat()
        }

    async def get_top_moving_items(self, limit: int = 10) -> Dict[str, Any]:
        """Get top moving items based on order frequency."""
        # Simplified: return highest quantity items
        inventory = await self.db.inventory.find({}).sort("quantity", -1).limit(limit).to_list(None)

        items = [
            {
                "sku": item.get("sku", ""),
                "name": item.get("name", ""),
                "quantity": item.get("quantity", 0),
                "category": item.get("category", ""),
                "value": item.get("quantity", 0) * item.get("unit_cost", 0)
            }
            for item in inventory
        ]

        return {
            "top_items": items,
            "total_items_tracked": len(inventory),
            "generated_at": datetime.now(timezone.utc).isoformat()
        }

    async def get_low_stock_alerts(self) -> Dict[str, Any]:
        """Get items that need restocking."""
        inventory = await self.db.inventory.find({
            "$expr": {"$lte": ["$quantity", "$reorder_threshold"]}
        }).sort("quantity", 1).to_list(None)

        items = [
            {
                "sku": item.get("sku", ""),
                "name": item.get("name", ""),
                "quantity": item.get("quantity", 0),
                "threshold": item.get("reorder_threshold", 0),
                "category": item.get("category", ""),
                "urgency": "critical" if item.get("quantity", 0) <= item.get("reorder_threshold", 0) * 0.5 else "warning"
            }
            for item in inventory
        ]

        critical = sum(1 for i in items if i["urgency"] == "critical")
        warning = sum(1 for i in items if i["urgency"] == "warning")

        return {
            "total_low_stock": len(items),
            "critical": critical,
            "warning": warning,
            "items": items,
            "generated_at": datetime.now(timezone.utc).isoformat()
        }
