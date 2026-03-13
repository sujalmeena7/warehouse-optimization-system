from datetime import datetime, timedelta, timezone
from math import ceil
from pathlib import Path
from typing import Dict, List, Literal, Optional
import logging
import os
import uuid

from dotenv import load_dotenv
from fastapi import APIRouter, FastAPI, HTTPException, Query
from motor.motor_asyncio import AsyncIOMotorClient
from pydantic import BaseModel, ConfigDict, Field
from starlette.middleware.cors import CORSMiddleware
from layout_api import create_layout_router


ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / ".env")

mongo_url = os.environ["MONGO_URL"]
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ["DB_NAME"]]

app = FastAPI()
api_router = APIRouter(prefix="/api")

RoleName = Literal["Admin", "Manager", "Staff"]
OrderStatus = Literal["queued", "picking", "packed", "shipped"]

ROLE_PERMISSIONS: Dict[str, Dict[str, bool]] = {
    "Admin": {
        "dashboard": True,
        "inventory": True,
        "orders": True,
        "routes": True,
        "layout": True,
        "analytics": True,
        "alerts": True,
        "can_edit_inventory": True,
    },
    "Manager": {
        "dashboard": True,
        "inventory": True,
        "orders": True,
        "routes": True,
        "layout": True,
        "analytics": True,
        "alerts": True,
        "can_edit_inventory": True,
    },
    "Staff": {
        "dashboard": True,
        "inventory": True,
        "orders": True,
        "routes": True,
        "layout": True,
        "analytics": False,
        "alerts": True,
        "can_edit_inventory": False,
    },
}


class StatusCheck(BaseModel):
    model_config = ConfigDict(extra="ignore")

    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    client_name: str
    timestamp: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class StatusCheckCreate(BaseModel):
    client_name: str


class DemoLoginRequest(BaseModel):
    name: str = Field(min_length=2, max_length=40)
    role: RoleName


class DemoLoginResponse(BaseModel):
    user_id: str
    name: str
    role: RoleName
    permissions: Dict[str, bool]
    allowed_pages: List[str]


class InventoryItemBase(BaseModel):
    sku: str
    name: str
    category: str
    zone: str
    bin_code: str
    x: int
    y: int
    quantity: int
    reorder_threshold: int
    max_capacity: int
    unit_cost: float
    lead_time_days: int
    daily_demand: List[int]
    last_restocked: str


class InventoryItem(InventoryItemBase):
    id: str


class InventoryCreate(InventoryItemBase):
    pass


class InventoryUpdate(BaseModel):
    quantity: Optional[int] = Field(default=None, ge=0)
    reorder_threshold: Optional[int] = Field(default=None, ge=0)
    max_capacity: Optional[int] = Field(default=None, ge=1)
    zone: Optional[str] = None
    bin_code: Optional[str] = None


class InventoryView(InventoryItem):
    stock_status: Literal["healthy", "low", "critical"]
    reorder_point: int
    suggested_reorder_qty: int


class OrderLine(BaseModel):
    sku: str
    name: str
    quantity: int
    bin_code: str
    zone: str
    x: int
    y: int


class OrderRecord(BaseModel):
    id: str
    reference: str
    priority: Literal["low", "medium", "high"]
    status: OrderStatus
    destination: str
    picker: str
    created_at: str
    due_at: str
    updated_at: str
    items: List[OrderLine]


class OrderView(OrderRecord):
    priority_score: float


class OrderStatusUpdate(BaseModel):
    status: OrderStatus


class OrderListResponse(BaseModel):
    orders: List[OrderView]
    status_counts: Dict[str, int]


class RouteStep(BaseModel):
    step: int
    sku: str
    name: str
    quantity: int
    zone: str
    bin_code: str
    x: int
    y: int
    distance_from_previous: int


class RoutePlan(BaseModel):
    order_id: str
    order_reference: str
    algorithm: str
    total_distance: int
    estimated_pick_minutes: int
    steps: List[RouteStep]


class AlertRecord(BaseModel):
    id: str
    severity: Literal["info", "warning", "critical"]
    type: str
    message: str
    source: str
    created_at: str
    resolved: bool


class WarehouseKPIs(BaseModel):
    total_skus: int
    low_stock_items: int
    open_orders: int
    space_utilization: float
    picking_efficiency: float


class EfficiencyPoint(BaseModel):
    day: str
    completed_orders: int
    avg_pick_minutes: float


class ReorderRecommendation(BaseModel):
    sku: str
    name: str
    current_qty: int
    reorder_point: int
    suggested_qty: int


class WarehouseOverview(BaseModel):
    kpis: WarehouseKPIs
    recent_orders: List[OrderView]
    low_stock: List[InventoryView]
    efficiency_trend: List[EfficiencyPoint]
    reorder_recommendations: List[ReorderRecommendation]


class CategoryTurnover(BaseModel):
    category: str
    turnover_index: float
    stock_value: float


class FulfillmentPoint(BaseModel):
    day: str
    processed_orders: int
    on_time_rate: float


class DemandForecastPoint(BaseModel):
    day: str
    projected_units: int


class AnalyticsResponse(BaseModel):
    category_turnover: List[CategoryTurnover]
    fulfillment_trend: List[FulfillmentPoint]
    demand_forecast: List[DemandForecastPoint]


def utc_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def parse_iso(value: str) -> datetime:
    return datetime.fromisoformat(value)


def validate_role(role: str) -> RoleName:
    if role not in ROLE_PERMISSIONS:
        raise HTTPException(status_code=400, detail="Invalid role")
    return role  # type: ignore[return-value]


def require_permission(role: str, permission_key: str) -> None:
    valid_role = validate_role(role)
    if not ROLE_PERMISSIONS[valid_role].get(permission_key, False):
        raise HTTPException(status_code=403, detail=f"Role '{valid_role}' cannot access {permission_key}")


def inventory_metrics(item: Dict) -> Dict[str, int | str]:
    avg_daily_demand = sum(item["daily_demand"]) / max(len(item["daily_demand"]), 1)
    reorder_point = ceil(avg_daily_demand * item["lead_time_days"] * 1.15)
    suggested = max(0, reorder_point * 2 - item["quantity"])
    if item["quantity"] <= max(2, int(item["reorder_threshold"] * 0.5)):
        status = "critical"
    elif item["quantity"] <= item["reorder_threshold"]:
        status = "low"
    else:
        status = "healthy"
    return {
        "reorder_point": reorder_point,
        "suggested_reorder_qty": suggested,
        "stock_status": status,
    }


def priority_score(order: Dict) -> float:
    priority_bonus = {"high": 55, "medium": 35, "low": 15}.get(order["priority"], 10)
    now = datetime.now(timezone.utc)
    due_at = parse_iso(order["due_at"])
    hours_to_due = (due_at - now).total_seconds() / 3600
    if hours_to_due <= 8:
        urgency = 50
    elif hours_to_due <= 24:
        urgency = 35
    elif hours_to_due <= 48:
        urgency = 20
    else:
        urgency = 8
    complexity_penalty = min(20, len(order["items"]) * 2)
    return round(priority_bonus + urgency - complexity_penalty, 1)


def manhattan_distance(a: Dict[str, int], b: Dict[str, int]) -> int:
    return abs(a["x"] - b["x"]) + abs(a["y"] - b["y"])


def build_route(order: Dict) -> RoutePlan:
    remaining = [dict(item) for item in order["items"]]
    current = {"x": 0, "y": 0}
    route_steps: List[RouteStep] = []
    total_distance = 0
    step_number = 1

    while remaining:
        closest_index = 0
        closest_distance = 10**9
        for idx, item in enumerate(remaining):
            candidate_distance = manhattan_distance(current, {"x": item["x"], "y": item["y"]})
            if candidate_distance < closest_distance:
                closest_distance = candidate_distance
                closest_index = idx

        selected = remaining.pop(closest_index)
        route_steps.append(
            RouteStep(
                step=step_number,
                sku=selected["sku"],
                name=selected["name"],
                quantity=selected["quantity"],
                zone=selected["zone"],
                bin_code=selected["bin_code"],
                x=selected["x"],
                y=selected["y"],
                distance_from_previous=closest_distance,
            )
        )
        total_distance += closest_distance
        current = {"x": selected["x"], "y": selected["y"]}
        step_number += 1

    return RoutePlan(
        order_id=order["id"],
        order_reference=order["reference"],
        algorithm="Nearest Neighbor (Manhattan distance)",
        total_distance=total_distance,
        estimated_pick_minutes=max(6, int(total_distance * 1.5)),
        steps=route_steps,
    )


async def seed_database(force: bool = False) -> Dict[str, str | int]:
    collections = ["inventory", "orders", "alerts"]
    existing_inventory_count = await db.inventory.count_documents({})
    if existing_inventory_count > 0 and not force:
        return {"status": "already_seeded", "inventory_records": existing_inventory_count}

    if force:
        for collection in collections:
            await db[collection].delete_many({})

    now = datetime.now(timezone.utc)
    inventory_docs = [
        InventoryItem(
            id=str(uuid.uuid4()),
            sku="SKU-1001",
            name="Industrial Safety Helmet",
            category="Safety",
            zone="A",
            bin_code="A-01",
            x=1,
            y=1,
            quantity=120,
            reorder_threshold=60,
            max_capacity=200,
            unit_cost=22.5,
            lead_time_days=5,
            daily_demand=[14, 12, 15, 16, 13, 12, 14],
            last_restocked=(now - timedelta(days=5)).isoformat(),
        ).model_dump(),
        InventoryItem(
            id=str(uuid.uuid4()),
            sku="SKU-1002",
            name="Pallet Wrap Roll",
            category="Packaging",
            zone="A",
            bin_code="A-04",
            x=1,
            y=4,
            quantity=42,
            reorder_threshold=50,
            max_capacity=160,
            unit_cost=8.4,
            lead_time_days=4,
            daily_demand=[11, 9, 10, 12, 8, 7, 9],
            last_restocked=(now - timedelta(days=11)).isoformat(),
        ).model_dump(),
        InventoryItem(
            id=str(uuid.uuid4()),
            sku="SKU-1003",
            name="Barcode Scanner",
            category="Equipment",
            zone="B",
            bin_code="B-02",
            x=2,
            y=2,
            quantity=24,
            reorder_threshold=20,
            max_capacity=60,
            unit_cost=149.0,
            lead_time_days=7,
            daily_demand=[2, 3, 3, 2, 2, 1, 2],
            last_restocked=(now - timedelta(days=18)).isoformat(),
        ).model_dump(),
        InventoryItem(
            id=str(uuid.uuid4()),
            sku="SKU-1004",
            name="Shipping Labels (500pc)",
            category="Packaging",
            zone="B",
            bin_code="B-06",
            x=2,
            y=6,
            quantity=14,
            reorder_threshold=30,
            max_capacity=90,
            unit_cost=18.0,
            lead_time_days=3,
            daily_demand=[8, 9, 7, 8, 8, 7, 9],
            last_restocked=(now - timedelta(days=20)).isoformat(),
        ).model_dump(),
        InventoryItem(
            id=str(uuid.uuid4()),
            sku="SKU-1005",
            name="Cordless Drill",
            category="Tools",
            zone="C",
            bin_code="C-03",
            x=3,
            y=3,
            quantity=18,
            reorder_threshold=10,
            max_capacity=40,
            unit_cost=129.0,
            lead_time_days=8,
            daily_demand=[1, 1, 2, 2, 1, 1, 1],
            last_restocked=(now - timedelta(days=9)).isoformat(),
        ).model_dump(),
        InventoryItem(
            id=str(uuid.uuid4()),
            sku="SKU-1006",
            name="Torque Wrench Set",
            category="Tools",
            zone="C",
            bin_code="C-05",
            x=3,
            y=5,
            quantity=7,
            reorder_threshold=12,
            max_capacity=32,
            unit_cost=99.0,
            lead_time_days=9,
            daily_demand=[1, 1, 1, 1, 2, 1, 1],
            last_restocked=(now - timedelta(days=25)).isoformat(),
        ).model_dump(),
        InventoryItem(
            id=str(uuid.uuid4()),
            sku="SKU-1007",
            name="Smart Conveyor Sensor",
            category="Automation",
            zone="D",
            bin_code="D-02",
            x=4,
            y=2,
            quantity=15,
            reorder_threshold=12,
            max_capacity=36,
            unit_cost=189.0,
            lead_time_days=12,
            daily_demand=[1, 2, 1, 2, 1, 1, 2],
            last_restocked=(now - timedelta(days=16)).isoformat(),
        ).model_dump(),
        InventoryItem(
            id=str(uuid.uuid4()),
            sku="SKU-1008",
            name="Rack Mount Bracket",
            category="Hardware",
            zone="D",
            bin_code="D-07",
            x=4,
            y=7,
            quantity=63,
            reorder_threshold=35,
            max_capacity=120,
            unit_cost=14.0,
            lead_time_days=6,
            daily_demand=[6, 7, 8, 6, 7, 6, 7],
            last_restocked=(now - timedelta(days=6)).isoformat(),
        ).model_dump(),
    ]

    sku_map = {item["sku"]: item for item in inventory_docs}

    def order_line(sku: str, quantity: int) -> Dict:
        item = sku_map[sku]
        return {
            "sku": sku,
            "name": item["name"],
            "quantity": quantity,
            "bin_code": item["bin_code"],
            "zone": item["zone"],
            "x": item["x"],
            "y": item["y"],
        }

    orders_docs = [
        OrderRecord(
            id=str(uuid.uuid4()),
            reference="ORD-24071",
            priority="high",
            status="queued",
            destination="North Dock - Retail Shipment",
            picker="Ava Singh",
            created_at=(now - timedelta(hours=10)).isoformat(),
            due_at=(now + timedelta(hours=6)).isoformat(),
            updated_at=utc_iso(),
            items=[order_line("SKU-1004", 8), order_line("SKU-1002", 6), order_line("SKU-1001", 10)],
        ).model_dump(),
        OrderRecord(
            id=str(uuid.uuid4()),
            reference="ORD-24072",
            priority="medium",
            status="picking",
            destination="Export Lane - SEA-04",
            picker="Noah Chen",
            created_at=(now - timedelta(hours=22)).isoformat(),
            due_at=(now + timedelta(hours=14)).isoformat(),
            updated_at=utc_iso(),
            items=[order_line("SKU-1003", 3), order_line("SKU-1006", 2)],
        ).model_dump(),
        OrderRecord(
            id=str(uuid.uuid4()),
            reference="ORD-24073",
            priority="low",
            status="packed",
            destination="B2B Pallet 19",
            picker="Iris Gomez",
            created_at=(now - timedelta(hours=30)).isoformat(),
            due_at=(now + timedelta(hours=30)).isoformat(),
            updated_at=utc_iso(),
            items=[order_line("SKU-1008", 18), order_line("SKU-1007", 3)],
        ).model_dump(),
        OrderRecord(
            id=str(uuid.uuid4()),
            reference="ORD-24074",
            priority="high",
            status="queued",
            destination="Urgent Service Ticket",
            picker="Mika Patel",
            created_at=(now - timedelta(hours=6)).isoformat(),
            due_at=(now + timedelta(hours=4)).isoformat(),
            updated_at=utc_iso(),
            items=[order_line("SKU-1005", 2), order_line("SKU-1003", 1), order_line("SKU-1001", 4)],
        ).model_dump(),
        OrderRecord(
            id=str(uuid.uuid4()),
            reference="ORD-24068",
            priority="medium",
            status="shipped",
            destination="Regional Hub East",
            picker="Ava Singh",
            created_at=(now - timedelta(days=1, hours=6)).isoformat(),
            due_at=(now - timedelta(hours=18)).isoformat(),
            updated_at=utc_iso(),
            items=[order_line("SKU-1001", 14), order_line("SKU-1002", 12)],
        ).model_dump(),
    ]

    alerts_docs = [
        AlertRecord(
            id=str(uuid.uuid4()),
            severity="critical",
            type="stock",
            message="Shipping Labels (SKU-1004) is below critical threshold.",
            source="inventory",
            created_at=(now - timedelta(minutes=40)).isoformat(),
            resolved=False,
        ).model_dump(),
        AlertRecord(
            id=str(uuid.uuid4()),
            severity="warning",
            type="route",
            message="Aisle C temporary congestion detected in zone C.",
            source="operations",
            created_at=(now - timedelta(hours=2)).isoformat(),
            resolved=False,
        ).model_dump(),
        AlertRecord(
            id=str(uuid.uuid4()),
            severity="info",
            type="maintenance",
            message="Conveyor line 2 preventive maintenance scheduled at 18:00.",
            source="system",
            created_at=(now - timedelta(hours=6)).isoformat(),
            resolved=False,
        ).model_dump(),
    ]

    if existing_inventory_count > 0 and force:
        await db.inventory.delete_many({})
        await db.orders.delete_many({})
        await db.alerts.delete_many({})

    await db.inventory.insert_many(inventory_docs)
    await db.orders.insert_many(orders_docs)
    await db.alerts.insert_many(alerts_docs)

    return {
        "status": "seeded",
        "inventory_records": len(inventory_docs),
        "order_records": len(orders_docs),
        "alert_records": len(alerts_docs),
    }


@api_router.get("/")
async def root() -> Dict[str, str]:
    return {"message": "Warehouse Optimization API online"}


@api_router.post("/status", response_model=StatusCheck)
async def create_status_check(input_data: StatusCheckCreate) -> StatusCheck:
    status_obj = StatusCheck(client_name=input_data.client_name)
    await db.status_checks.insert_one(status_obj.model_dump())
    return status_obj


@api_router.get("/status", response_model=List[StatusCheck])
async def get_status_checks() -> List[StatusCheck]:
    checks = await db.status_checks.find({}, {"_id": 0}).to_list(200)
    return [StatusCheck(**check) for check in checks]


@api_router.post("/bootstrap/seed")
async def bootstrap_seed(force: bool = False) -> Dict[str, str | int]:
    return await seed_database(force=force)


@api_router.get("/auth/roles")
async def get_roles() -> Dict[str, List[str]]:
    return {"roles": list(ROLE_PERMISSIONS.keys())}


@api_router.post("/auth/demo-login", response_model=DemoLoginResponse)
async def demo_login(payload: DemoLoginRequest) -> DemoLoginResponse:
    role = validate_role(payload.role)
    permissions = ROLE_PERMISSIONS[role]
    return DemoLoginResponse(
        user_id=str(uuid.uuid4()),
        name=payload.name,
        role=role,
        permissions=permissions,
        allowed_pages=[key for key, allowed in permissions.items() if allowed and key != "can_edit_inventory"],
    )


@api_router.get("/warehouse/overview", response_model=WarehouseOverview)
async def warehouse_overview(role: str = Query(...)) -> WarehouseOverview:
    require_permission(role, "dashboard")
    inventory_docs = await db.inventory.find({}, {"_id": 0}).to_list(500)
    order_docs = await db.orders.find({}, {"_id": 0}).to_list(500)

    inventory_views: List[InventoryView] = []
    low_stock_items: List[InventoryView] = []
    for item in inventory_docs:
        metrics = inventory_metrics(item)
        model = InventoryView(**item, **metrics)
        inventory_views.append(model)
        if model.stock_status in {"low", "critical"}:
            low_stock_items.append(model)

    order_views: List[OrderView] = [OrderView(**order, priority_score=priority_score(order)) for order in order_docs]
    order_views.sort(key=lambda entry: entry.priority_score, reverse=True)

    total_capacity = sum(item.max_capacity for item in inventory_views)
    total_units = sum(item.quantity for item in inventory_views)
    active_orders = len([item for item in order_views if item.status != "shipped"])
    completed_orders = len([item for item in order_views if item.status in {"packed", "shipped"}])

    efficiency_trend: List[EfficiencyPoint] = []
    for idx in range(6, -1, -1):
        day = (datetime.now(timezone.utc) - timedelta(days=idx)).strftime("%a")
        efficiency_trend.append(
            EfficiencyPoint(
                day=day,
                completed_orders=max(1, completed_orders + (3 - idx)),
                avg_pick_minutes=round(max(9.0, 19.0 - (0.9 * (6 - idx))), 1),
            )
        )

    recommendations = [
        ReorderRecommendation(
            sku=item.sku,
            name=item.name,
            current_qty=item.quantity,
            reorder_point=item.reorder_point,
            suggested_qty=item.suggested_reorder_qty,
        )
        for item in low_stock_items
        if item.suggested_reorder_qty > 0
    ]

    return WarehouseOverview(
        kpis=WarehouseKPIs(
            total_skus=len(inventory_views),
            low_stock_items=len(low_stock_items),
            open_orders=active_orders,
            space_utilization=round((total_units / max(total_capacity, 1)) * 100, 1),
            picking_efficiency=round((completed_orders / max(len(order_views), 1)) * 100, 1),
        ),
        recent_orders=order_views[:5],
        low_stock=sorted(low_stock_items, key=lambda value: (value.stock_status, value.quantity))[:6],
        efficiency_trend=efficiency_trend,
        reorder_recommendations=recommendations[:5],
    )


@api_router.get("/inventory", response_model=List[InventoryView])
async def get_inventory(
    role: str = Query(...),
    search: Optional[str] = Query(default=None),
    status: Optional[Literal["healthy", "low", "critical"]] = Query(default=None),
) -> List[InventoryView]:
    require_permission(role, "inventory")
    inventory_docs = await db.inventory.find({}, {"_id": 0}).to_list(1200)

    output: List[InventoryView] = []
    lowered_search = (search or "").strip().lower()
    for item in inventory_docs:
        metrics = inventory_metrics(item)
        candidate = InventoryView(**item, **metrics)
        if lowered_search and lowered_search not in (
            f"{candidate.sku} {candidate.name} {candidate.category} {candidate.zone} {candidate.bin_code}".lower()
        ):
            continue
        if status and candidate.stock_status != status:
            continue
        output.append(candidate)
    output.sort(key=lambda value: (value.stock_status, value.zone, value.bin_code))
    return output


@api_router.post("/inventory", response_model=InventoryView)
async def create_inventory_item(payload: InventoryCreate, role: str = Query(...)) -> InventoryView:
    require_permission(role, "inventory")
    require_permission(role, "can_edit_inventory")

    exists = await db.inventory.find_one({"sku": payload.sku}, {"_id": 0})
    if exists:
        raise HTTPException(status_code=409, detail="SKU already exists")

    item = InventoryItem(id=str(uuid.uuid4()), **payload.model_dump())
    item_doc = item.model_dump()
    await db.inventory.insert_one(item_doc)
    metrics = inventory_metrics(item_doc)
    return InventoryView(**item_doc, **metrics)


@api_router.put("/inventory/{item_id}", response_model=InventoryView)
async def update_inventory_item(item_id: str, payload: InventoryUpdate, role: str = Query(...)) -> InventoryView:
    require_permission(role, "inventory")
    require_permission(role, "can_edit_inventory")

    update_payload = {k: v for k, v in payload.model_dump().items() if v is not None}
    if not update_payload:
        raise HTTPException(status_code=400, detail="No fields provided for update")

    result = await db.inventory.update_one({"id": item_id}, {"$set": update_payload})
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Inventory item not found")

    updated = await db.inventory.find_one({"id": item_id}, {"_id": 0})
    if not updated:
        raise HTTPException(status_code=404, detail="Inventory item not found after update")
    metrics = inventory_metrics(updated)
    return InventoryView(**updated, **metrics)


@api_router.get("/orders", response_model=OrderListResponse)
async def get_orders(role: str = Query(...)) -> OrderListResponse:
    require_permission(role, "orders")
    order_docs = await db.orders.find({}, {"_id": 0}).to_list(1200)
    orders = [OrderView(**order, priority_score=priority_score(order)) for order in order_docs]
    orders.sort(key=lambda entry: entry.priority_score, reverse=True)

    counts: Dict[str, int] = {"queued": 0, "picking": 0, "packed": 0, "shipped": 0}
    for order in orders:
        counts[order.status] = counts.get(order.status, 0) + 1

    return OrderListResponse(orders=orders, status_counts=counts)


@api_router.patch("/orders/{order_id}/status", response_model=OrderView)
async def update_order_status(order_id: str, payload: OrderStatusUpdate, role: str = Query(...)) -> OrderView:
    require_permission(role, "orders")
    update_data = {"status": payload.status, "updated_at": utc_iso()}
    result = await db.orders.update_one({"id": order_id}, {"$set": update_data})
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Order not found")

    if payload.status == "shipped":
        await db.alerts.insert_one(
            AlertRecord(
                id=str(uuid.uuid4()),
                severity="info",
                type="shipment",
                message=f"Order {order_id} moved to shipped.",
                source="orders",
                created_at=utc_iso(),
                resolved=False,
            ).model_dump()
        )

    updated = await db.orders.find_one({"id": order_id}, {"_id": 0})
    if not updated:
        raise HTTPException(status_code=404, detail="Order not found after update")
    return OrderView(**updated, priority_score=priority_score(updated))


@api_router.get("/routes/optimize", response_model=RoutePlan)
async def optimize_route(order_id: str = Query(...), role: str = Query(...)) -> RoutePlan:
    require_permission(role, "routes")
    order = await db.orders.find_one({"id": order_id}, {"_id": 0})
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    return build_route(order)


@api_router.get("/analytics/trends", response_model=AnalyticsResponse)
async def analytics_trends(role: str = Query(...)) -> AnalyticsResponse:
    require_permission(role, "analytics")
    inventory_docs = await db.inventory.find({}, {"_id": 0}).to_list(500)
    order_docs = await db.orders.find({}, {"_id": 0}).to_list(500)

    category_groups: Dict[str, Dict[str, float]] = {}
    for item in inventory_docs:
        category = item["category"]
        metrics = inventory_metrics(item)
        avg_daily = sum(item["daily_demand"]) / max(len(item["daily_demand"]), 1)
        existing = category_groups.get(category, {"qty": 0.0, "value": 0.0, "demand": 0.0, "reorder": 0.0})
        existing["qty"] += item["quantity"]
        existing["value"] += item["quantity"] * item["unit_cost"]
        existing["demand"] += avg_daily * 30
        existing["reorder"] += metrics["reorder_point"]
        category_groups[category] = existing

    category_turnover = [
        CategoryTurnover(
            category=category,
            turnover_index=round(values["demand"] / max(values["qty"], 1), 2),
            stock_value=round(values["value"], 2),
        )
        for category, values in category_groups.items()
    ]
    category_turnover.sort(key=lambda item: item.turnover_index, reverse=True)

    fulfillment_trend: List[FulfillmentPoint] = []
    shipped_count = len([order for order in order_docs if order["status"] == "shipped"])
    for idx in range(6, -1, -1):
        day = (datetime.now(timezone.utc) - timedelta(days=idx)).strftime("%a")
        processed = max(2, shipped_count + (4 - idx))
        on_time = max(78.0, min(99.0, 84.0 + (idx * 1.5)))
        fulfillment_trend.append(FulfillmentPoint(day=day, processed_orders=processed, on_time_rate=round(on_time, 1)))

    demand_forecast: List[DemandForecastPoint] = []
    high_velocity_items = sorted(
        inventory_docs,
        key=lambda item: sum(item["daily_demand"]) / max(len(item["daily_demand"]), 1),
        reverse=True,
    )[:3]
    forecast_base = sum(
        sum(item["daily_demand"]) / max(len(item["daily_demand"]), 1) for item in high_velocity_items
    )
    for offset in range(1, 8):
        projected = ceil(forecast_base * (1 + (offset * 0.03)))
        demand_forecast.append(
            DemandForecastPoint(
                day=(datetime.now(timezone.utc) + timedelta(days=offset)).strftime("%a"),
                projected_units=projected,
            )
        )

    return AnalyticsResponse(
        category_turnover=category_turnover,
        fulfillment_trend=fulfillment_trend,
        demand_forecast=demand_forecast,
    )


@api_router.get("/alerts", response_model=List[AlertRecord])
async def get_alerts(
    role: str = Query(...),
    severity: Optional[Literal["info", "warning", "critical"]] = Query(default=None),
) -> List[AlertRecord]:
    require_permission(role, "alerts")
    alert_docs = await db.alerts.find({}, {"_id": 0}).to_list(500)
    inventory_docs = await db.inventory.find({}, {"_id": 0}).to_list(500)
    order_docs = await db.orders.find({}, {"_id": 0}).to_list(500)

    generated_alerts: List[AlertRecord] = []
    now = datetime.now(timezone.utc)

    for item in inventory_docs:
        metrics = inventory_metrics(item)
        if metrics["stock_status"] == "critical":
            generated_alerts.append(
                AlertRecord(
                    id=f"generated-{item['id']}",
                    severity="critical",
                    type="stock",
                    message=f"{item['name']} is critically low ({item['quantity']} units left).",
                    source="inventory",
                    created_at=utc_iso(),
                    resolved=False,
                )
            )
        elif metrics["stock_status"] == "low":
            generated_alerts.append(
                AlertRecord(
                    id=f"generated-low-{item['id']}",
                    severity="warning",
                    type="stock",
                    message=f"{item['name']} is below reorder threshold.",
                    source="inventory",
                    created_at=utc_iso(),
                    resolved=False,
                )
            )

    for order in order_docs:
        due_time = parse_iso(order["due_at"])
        if order["status"] != "shipped" and due_time < now:
            generated_alerts.append(
                AlertRecord(
                    id=f"generated-order-{order['id']}",
                    severity="warning",
                    type="sla",
                    message=f"Order {order['reference']} is overdue and requires attention.",
                    source="orders",
                    created_at=utc_iso(),
                    resolved=False,
                )
            )

    stored_alerts = [AlertRecord(**alert) for alert in alert_docs]
    all_alerts = stored_alerts + generated_alerts
    if severity:
        all_alerts = [alert for alert in all_alerts if alert.severity == severity]

    all_alerts.sort(key=lambda entry: entry.created_at, reverse=True)
    return all_alerts[:25]


@app.on_event("startup")
async def startup_seed() -> None:
    await seed_database(force=False)


app.include_router(api_router)
app.include_router(create_layout_router(db, require_permission))

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=os.environ.get("CORS_ORIGINS", "*").split(","),
    allow_methods=["*"],
    allow_headers=["*"],
)

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


@app.on_event("shutdown")
async def shutdown_db_client() -> None:
    client.close()