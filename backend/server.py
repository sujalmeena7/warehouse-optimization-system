from datetime import datetime, timedelta, timezone
from math import ceil
from pathlib import Path
from typing import Dict, List, Literal, Optional, Any
import logging
import os
import uuid

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

from dotenv import load_dotenv
from fastapi import APIRouter, FastAPI, HTTPException, Query, Depends, Header, File, UploadFile, Body, WebSocket, WebSocketDisconnect
from fastapi.responses import StreamingResponse
from motor.motor_asyncio import AsyncIOMotorClient
from pydantic import BaseModel, ConfigDict, Field, EmailStr
from starlette.middleware.cors import CORSMiddleware
from layout_api import create_layout_router
from auth import hash_password, verify_password, create_access_token, create_refresh_token, verify_token, extract_user_data_from_token
from audit_logger import log_action, get_audit_logs, get_entity_audit_trail, create_audit_indexes
from csv_import import parse_containers_csv, parse_inventory_csv, get_containers_csv_template, get_inventory_csv_template
from search_service import SearchService
from export_service import ExportService
from notification_service import NotificationService
from forecasting_service import ForecastingService
from analytics_service import AnalyticsService


ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / ".env")

mongo_url = os.environ["MONGO_URL"]
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ["DB_NAME"]]

# Initialize services early for startup
search_service = SearchService(db)
export_service = ExportService(db)
notification_service = NotificationService(db)
forecasting_service = ForecastingService(db)
analytics_service = AnalyticsService(db)

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


# User authentication models
class UserRegister(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=100)
    name: str = Field(min_length=2, max_length=100)


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    user_id: str
    email: str
    name: str
    role: RoleName


class UserResponse(BaseModel):
    user_id: str
    email: str
    name: str
    role: RoleName
    is_active: bool
    created_at: str
    last_login: Optional[str] = None


class UserUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=2, max_length=100)
    role: Optional[RoleName] = None
    is_active: Optional[bool] = None


class RefreshTokenRequest(BaseModel):
    refresh_token: str


# Audit log models
class AuditLogRecord(BaseModel):
    id: str
    action: str
    user_id: str
    user_email: str
    entity_type: str
    entity_id: str
    entity_details: str
    old_value: Optional[Dict[str, Any]] = None
    new_value: Optional[Dict[str, Any]] = None
    changes: List[str] = []
    timestamp: str
    ip_address: str
    status: str
    error_message: Optional[str] = None


class AuditLogFilter(BaseModel):
    user_id: Optional[str] = None
    entity_type: Optional[str] = None
    action: Optional[str] = None
    limit: int = 100
    skip: int = 0


# CSV Import response models
class CSVImportErrorItem(BaseModel):
    row: int
    error: str


class ImportResponse(BaseModel):
    success: bool
    success_count: int
    error_count: int
    total: int
    errors: List[CSVImportErrorItem]
    message: str


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


class SaveFilterRequest(BaseModel):
    name: str
    entity_type: str  # "inventory" or "orders"
    filters: Dict[str, Any]


class ExportRequest(BaseModel):
    entity_type: str  # "inventory", "orders", or "analytics"
    format: str = "csv"  # "csv" or "excel"
    selected_columns: Optional[List[str]] = None
    filters: Optional[Dict[str, Any]] = None


class NotificationBase(BaseModel):
    title: str
    message: str
    type: str = "info"
    severity: str = "info"


class NotificationRecord(NotificationBase):
    id: str
    user_id: str
    entity_type: Optional[str] = None
    entity_id: Optional[str] = None
    action_url: Optional[str] = None
    read: bool = False
    created_at: str


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


async def get_current_user(authorization: Optional[str] = Header(None)) -> Dict[str, str]:
    """Extract and verify the current user from JWT token."""
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing or invalid authorization header")

    token = authorization.replace("Bearer ", "")
    payload = verify_token(token)
    if not payload:
        raise HTTPException(status_code=401, detail="Invalid or expired token")

    user_data = extract_user_data_from_token(payload)
    if not user_data.get("user_id"):
        raise HTTPException(status_code=401, detail="Invalid token claims")

    return user_data


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


@api_router.post("/auth/register", response_model=TokenResponse)
async def register_user(payload: UserRegister) -> TokenResponse:
    """Register a new user. First user becomes Admin, others require admin creation."""
    existing_user = await db.users.find_one({"email": payload.email}, {"_id": 0})
    if existing_user:
        raise HTTPException(status_code=409, detail="Email already registered")

    user_count = await db.users.count_documents({})
    role: RoleName = "Admin" if user_count == 0 else "Staff"

    user_id = str(uuid.uuid4())
    hashed_password = hash_password(payload.password)
    now = datetime.now(timezone.utc).isoformat()

    user_doc = {
        "id": user_id,
        "email": payload.email,
        "hashed_password": hashed_password,
        "name": payload.name,
        "role": role,
        "is_active": True,
        "created_at": now,
        "updated_at": now,
        "last_login": None,
    }
    await db.users.insert_one(user_doc)

    token_data = {"user_id": user_id, "email": payload.email, "name": payload.name, "role": role}
    access_token = create_access_token(token_data)
    refresh_token = create_refresh_token(token_data)

    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        user_id=user_id,
        email=payload.email,
        name=payload.name,
        role=role,
    )


@api_router.post("/auth/login", response_model=TokenResponse)
async def login_user(payload: UserLogin) -> TokenResponse:
    """Login with email and password."""
    user = await db.users.find_one({"email": payload.email}, {"_id": 0})
    if not user or not verify_password(payload.password, user["hashed_password"]):
        raise HTTPException(status_code=401, detail="Invalid email or password")

    if not user.get("is_active", False):
        raise HTTPException(status_code=403, detail="User account is deactivated")

    await db.users.update_one({"id": user["id"]}, {"$set": {"last_login": datetime.now(timezone.utc).isoformat()}})

    token_data = {
        "user_id": user["id"],
        "email": user["email"],
        "name": user["name"],
        "role": user["role"],
    }
    access_token = create_access_token(token_data)
    refresh_token = create_refresh_token(token_data)

    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        user_id=user["id"],
        email=user["email"],
        name=user["name"],
        role=user["role"],
    )


@api_router.post("/auth/refresh", response_model=TokenResponse)
async def refresh_token_endpoint(payload: RefreshTokenRequest) -> TokenResponse:
    """Refresh the access token using a refresh token."""
    token_data = verify_token(payload.refresh_token)
    if not token_data or token_data.get("type") != "refresh":
        raise HTTPException(status_code=401, detail="Invalid refresh token")

    user_id = token_data.get("user_id")
    user = await db.users.find_one({"id": user_id}, {"_id": 0})
    if not user or not user.get("is_active", False):
        raise HTTPException(status_code=401, detail="User not found or inactive")

    new_token_data = {
        "user_id": user["id"],
        "email": user["email"],
        "name": user["name"],
        "role": user["role"],
    }
    new_access_token = create_access_token(new_token_data)
    new_refresh_token = create_refresh_token(new_token_data)

    return TokenResponse(
        access_token=new_access_token,
        refresh_token=new_refresh_token,
        user_id=user["id"],
        email=user["email"],
        name=user["name"],
        role=user["role"],
    )


@api_router.get("/users", response_model=List[UserResponse])
async def list_users(current_user: Dict[str, str] = Depends(get_current_user)) -> List[UserResponse]:
    """List all users (Admin only)."""
    if current_user.get("role") != "Admin":
        raise HTTPException(status_code=403, detail="Only admins can list users")

    users = await db.users.find({}, {"_id": 0, "hashed_password": 0}).to_list(500)
    return [
        UserResponse(
            user_id=user["id"],
            email=user["email"],
            name=user["name"],
            role=user["role"],
            is_active=user.get("is_active", False),
            created_at=user.get("created_at", ""),
            last_login=user.get("last_login"),
        )
        for user in users
    ]


@api_router.post("/users", response_model=UserResponse)
async def create_user(payload: UserRegister, current_user: Dict[str, str] = Depends(get_current_user)) -> UserResponse:
    """Create a new user (Admin only)."""
    if current_user.get("role") != "Admin":
        raise HTTPException(status_code=403, detail="Only admins can create users")

    existing_user = await db.users.find_one({"email": payload.email}, {"_id": 0})
    if existing_user:
        raise HTTPException(status_code=409, detail="Email already registered")

    user_id = str(uuid.uuid4())
    hashed_password = hash_password(payload.password)
    now = datetime.now(timezone.utc).isoformat()

    user_doc = {
        "id": user_id,
        "email": payload.email,
        "hashed_password": hashed_password,
        "name": payload.name,
        "role": "Staff",
        "is_active": True,
        "created_at": now,
        "updated_at": now,
        "last_login": None,
    }
    await db.users.insert_one(user_doc)

    return UserResponse(
        user_id=user_id,
        email=payload.email,
        name=payload.name,
        role="Staff",
        is_active=True,
        created_at=now,
        last_login=None,
    )


@api_router.put("/users/{user_id}", response_model=UserResponse)
async def update_user(
    user_id: str,
    payload: UserUpdate,
    current_user: Dict[str, str] = Depends(get_current_user),
) -> UserResponse:
    """Update a user (Admin only)."""
    if current_user.get("role") != "Admin":
        raise HTTPException(status_code=403, detail="Only admins can update users")

    user = await db.users.find_one({"id": user_id}, {"_id": 0})
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    update_data = {"updated_at": datetime.now(timezone.utc).isoformat()}
    if payload.name is not None:
        update_data["name"] = payload.name
    if payload.role is not None:
        update_data["role"] = payload.role
    if payload.is_active is not None:
        update_data["is_active"] = payload.is_active

    await db.users.update_one({"id": user_id}, {"$set": update_data})

    updated = await db.users.find_one({"id": user_id}, {"_id": 0, "hashed_password": 0})
    return UserResponse(
        user_id=updated["id"],
        email=updated["email"],
        name=updated["name"],
        role=updated["role"],
        is_active=updated.get("is_active", False),
        created_at=updated.get("created_at", ""),
        last_login=updated.get("last_login"),
    )


@api_router.delete("/users/{user_id}", response_model=dict)
async def deactivate_user(
    user_id: str,
    current_user: Dict[str, str] = Depends(get_current_user),
) -> dict:
    """Deactivate a user (Admin only, cannot deactivate self)."""
    if current_user.get("role") != "Admin":
        raise HTTPException(status_code=403, detail="Only admins can deactivate users")

    if current_user.get("user_id") == user_id:
        raise HTTPException(status_code=400, detail="Cannot deactivate your own account")

    user = await db.users.find_one({"id": user_id}, {"_id": 0})
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    await db.users.update_one({"id": user_id}, {"$set": {"is_active": False, "updated_at": datetime.now(timezone.utc).isoformat()}})

    return {"message": f"User {user_id} has been deactivated"}


# Audit log endpoints
@api_router.get("/audit-logs", response_model=List[AuditLogRecord])
async def list_audit_logs(
    user_id: Optional[str] = Query(None),
    entity_type: Optional[str] = Query(None),
    action: Optional[str] = Query(None),
    limit: int = Query(100, le=500),
    skip: int = Query(0, ge=0),
    current_user: Dict[str, str] = Depends(get_current_user),
) -> List[AuditLogRecord]:
    """List audit logs (Admin only)."""
    if current_user.get("role") != "Admin":
        raise HTTPException(status_code=403, detail="Only admins can view audit logs")

    logs = await get_audit_logs(db, user_id=user_id, entity_type=entity_type, action=action, limit=limit, skip=skip)
    return [AuditLogRecord(**log) for log in logs]


@api_router.get("/audit-logs/{entity_type}/{entity_id}", response_model=List[AuditLogRecord])
async def get_entity_history(
    entity_type: str,
    entity_id: str,
    current_user: Dict[str, str] = Depends(get_current_user),
) -> List[AuditLogRecord]:
    """Get audit trail for a specific entity (Admin only)."""
    if current_user.get("role") != "Admin":
        raise HTTPException(status_code=403, detail="Only admins can view audit logs")

    logs = await get_entity_audit_trail(db, entity_type, entity_id)
    return [AuditLogRecord(**log) for log in logs]


@api_router.get("/audit-logs/user/{user_id}", response_model=List[AuditLogRecord])
async def get_user_activity(
    user_id: str,
    limit: int = Query(100, le=500),
    skip: int = Query(0, ge=0),
    current_user: Dict[str, str] = Depends(get_current_user),
) -> List[AuditLogRecord]:
    """Get activity timeline for a specific user (Admin only)."""
    if current_user.get("role") != "Admin":
        raise HTTPException(status_code=403, detail="Only admins can view audit logs")

    logs = await get_audit_logs(db, user_id=user_id, limit=limit, skip=skip)
    return [AuditLogRecord(**log) for log in logs]


# CSV Import endpoints
@api_router.get("/import/templates/containers")
async def get_containers_template() -> dict:
    """Download CSV template for containers import."""
    return {
        "template": get_containers_csv_template(),
        "columns": ["container_id", "size", "weight", "access_frequency", "arrival_time"],
        "size_options": ["Small", "Medium", "Large"],
        "access_frequency_options": ["High", "Medium", "Low"],
    }


@api_router.get("/import/templates/inventory")
async def get_inventory_template() -> dict:
    """Download CSV template for inventory import."""
    return {
        "template": get_inventory_csv_template(),
        "columns": [
            "sku",
            "name",
            "category",
            "zone",
            "bin_code",
            "x",
            "y",
            "quantity",
            "reorder_threshold",
            "max_capacity",
            "unit_cost",
            "lead_time_days",
        ],
    }


@api_router.post("/import/containers", response_model=ImportResponse)
async def import_containers(file: UploadFile = File(...), current_user: Dict[str, str] = Depends(get_current_user)) -> ImportResponse:
    """Import containers from CSV file (Admin only)."""
    if current_user.get("role") != "Admin":
        raise HTTPException(status_code=403, detail="Only admins can import data")

    try:
        content = await file.read()
        csv_content = content.decode("utf-8")
        result = parse_containers_csv(csv_content)

        # If there are errors, return them without importing
        if result.error_count > 0:
            return ImportResponse(
                success=False,
                success_count=0,
                error_count=result.error_count,
                total=result.success_count + result.error_count,
                errors=result.errors,
                message=f"CSV validation failed: {result.error_count} errors found",
            )

        # Insert containers
        if result.containers:
            await db.layout_containers.insert_many(result.containers)

            # Log the import action
            await log_action(
                db,
                action="CREATE",
                user_id=current_user.get("user_id", "unknown"),
                user_email=current_user.get("email", "unknown"),
                entity_type="container_import",
                entity_id=f"bulk_{len(result.containers)}",
                entity_details=f"Imported {len(result.containers)} containers",
                new_value={"count": len(result.containers)},
            )

        return ImportResponse(
            success=True,
            success_count=result.success_count,
            error_count=0,
            total=result.success_count,
            errors=[],
            message=f"Successfully imported {result.success_count} containers",
        )

    except Exception as e:
        logger.error(f"Container import error: {str(e)}")
        raise HTTPException(status_code=400, detail=f"Import failed: {str(e)}")


@api_router.post("/import/inventory", response_model=ImportResponse)
async def import_inventory(file: UploadFile = File(...), current_user: Dict[str, str] = Depends(get_current_user)) -> ImportResponse:
    """Import inventory from CSV file (Admin only)."""
    if current_user.get("role") != "Admin":
        raise HTTPException(status_code=403, detail="Only admins can import data")

    try:
        content = await file.read()
        csv_content = content.decode("utf-8")
        result = parse_inventory_csv(csv_content)

        # If there are errors, return them without importing
        if result.error_count > 0:
            return ImportResponse(
                success=False,
                success_count=0,
                error_count=result.error_count,
                total=result.success_count + result.error_count,
                errors=result.errors,
                message=f"CSV validation failed: {result.error_count} errors found",
            )

        # Insert inventory items
        if result.items:
            await db.inventory.insert_many(result.items)

            # Log the import action
            await log_action(
                db,
                action="CREATE",
                user_id=current_user.get("user_id", "unknown"),
                user_email=current_user.get("email", "unknown"),
                entity_type="inventory_import",
                entity_id=f"bulk_{len(result.items)}",
                entity_details=f"Imported {len(result.items)} inventory items",
                new_value={"count": len(result.items)},
            )

        return ImportResponse(
            success=True,
            success_count=result.success_count,
            error_count=0,
            total=result.success_count,
            errors=[],
            message=f"Successfully imported {result.success_count} inventory items",
        )

    except Exception as e:
        logger.error(f"Inventory import error: {str(e)}")
        raise HTTPException(status_code=400, detail=f"Import failed: {str(e)}")



@api_router.get("/warehouse/overview", response_model=WarehouseOverview)
async def warehouse_overview(user: Dict[str, str] = Depends(get_current_user)) -> WarehouseOverview:
    require_permission(user["role"], "dashboard")
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
    user: Dict[str, str] = Depends(get_current_user),
    search: Optional[str] = Query(default=None),
    status: Optional[Literal["healthy", "low", "critical"]] = Query(default=None),
) -> List[InventoryView]:
    require_permission(user["role"], "inventory")
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
async def create_inventory_item(payload: InventoryCreate, user: Dict[str, str] = Depends(get_current_user)) -> InventoryView:
    require_permission(user["role"], "inventory")
    require_permission(user["role"], "can_edit_inventory")

    exists = await db.inventory.find_one({"sku": payload.sku}, {"_id": 0})
    if exists:
        raise HTTPException(status_code=409, detail="SKU already exists")

    item = InventoryItem(id=str(uuid.uuid4()), **payload.model_dump())
    item_doc = item.model_dump()
    await db.inventory.insert_one(item_doc)
    metrics = inventory_metrics(item_doc)

    # Log the action (use placeholder user data since we don't have JWT yet)
    await log_action(
        db,
        action="CREATE",
        user_id="unknown",
        user_email="unknown",
        entity_type="inventory",
        entity_id=item["id"],
        entity_details=f"SKU: {item['sku']}, Name: {item['name']}",
        new_value=item_doc,
    )

    return InventoryView(**item_doc, **metrics)


@api_router.put("/inventory/{item_id}", response_model=InventoryView)
async def update_inventory_item(item_id: str, payload: InventoryUpdate, user: Dict[str, str] = Depends(get_current_user)) -> InventoryView:
    require_permission(user["role"], "inventory")
    require_permission(user["role"], "can_edit_inventory")

    update_payload = {k: v for k, v in payload.model_dump().items() if v is not None}
    if not update_payload:
        raise HTTPException(status_code=400, detail="No fields provided for update")

    # Get old value for audit log
    old_doc = await db.inventory.find_one({"id": item_id}, {"_id": 0})
    if not old_doc:
        raise HTTPException(status_code=404, detail="Inventory item not found")

    result = await db.inventory.update_one({"id": item_id}, {"$set": update_payload})
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Inventory item not found")

    updated = await db.inventory.find_one({"id": item_id}, {"_id": 0})
    if not updated:
        raise HTTPException(status_code=404, detail="Inventory item not found after update")
    metrics = inventory_metrics(updated)

    # Log the action with old and new values
    await log_action(
        db,
        action="UPDATE",
        user_id="unknown",
        user_email="unknown",
        entity_type="inventory",
        entity_id=item_id,
        entity_details=f"SKU: {updated['sku']}, Name: {updated['name']}",
        old_value=old_doc,
        new_value=updated,
    )

    return InventoryView(**updated, **metrics)


@api_router.get("/orders", response_model=OrderListResponse)
async def get_orders(user: Dict[str, str] = Depends(get_current_user)) -> OrderListResponse:
    require_permission(user["role"], "orders")
    order_docs = await db.orders.find({}, {"_id": 0}).to_list(1200)
    orders = [OrderView(**order, priority_score=priority_score(order)) for order in order_docs]
    orders.sort(key=lambda entry: entry.priority_score, reverse=True)

    counts: Dict[str, int] = {"queued": 0, "picking": 0, "packed": 0, "shipped": 0}
    for order in orders:
        counts[order.status] = counts.get(order.status, 0) + 1

    return OrderListResponse(orders=orders, status_counts=counts)


@api_router.patch("/orders/{order_id}/status", response_model=OrderView)
async def update_order_status(order_id: str, payload: OrderStatusUpdate, user: Dict[str, str] = Depends(get_current_user)) -> OrderView:
    require_permission(user["role"], "orders")

    # Get old value for audit log
    old_order = await db.orders.find_one({"id": order_id}, {"_id": 0})
    if not old_order:
        raise HTTPException(status_code=404, detail="Order not found")

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

    # Log the action
    await log_action(
        db,
        action="UPDATE",
        user_id="unknown",
        user_email="unknown",
        entity_type="order",
        entity_id=order_id,
        entity_details=f"Order: {updated['reference']}, New Status: {payload.status}",
        old_value={"status": old_order["status"]},
        new_value={"status": payload.status},
    )

    return OrderView(**updated, priority_score=priority_score(updated))


@api_router.get("/routes/optimize", response_model=RoutePlan)
async def optimize_route(order_id: str = Query(...), user: Dict[str, str] = Depends(get_current_user)) -> RoutePlan:
    require_permission(user["role"], "routes")
    order = await db.orders.find_one({"id": order_id}, {"_id": 0})
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    return build_route(order)


@api_router.get("/analytics/trends", response_model=AnalyticsResponse)
async def analytics_trends(user: Dict[str, str] = Depends(get_current_user)) -> AnalyticsResponse:
    require_permission(user["role"], "analytics")
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
    user: Dict[str, str] = Depends(get_current_user),
    severity: Optional[Literal["info", "warning", "critical"]] = Query(default=None),
) -> List[AlertRecord]:
    require_permission(user["role"], "alerts")
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
    # Initialize audit log indexes
    try:
        await create_audit_indexes(db)
    except Exception as e:
        logger.warning(f"Could not create audit indexes on startup: {e}")

    # Initialize search indexes
    try:
        await search_service.initialize_indexes()
    except Exception as e:
        logger.warning(f"Could not create search indexes on startup: {e}")

    # Initialize notification indexes
    try:
        await notification_service.create_indexes()
    except Exception as e:
        logger.warning(f"Could not create notification indexes on startup: {e}")

    # Initialize forecasting indexes
    try:
        await forecasting_service.create_indexes()
    except Exception as e:
        logger.warning(f"Could not create forecasting indexes on startup: {e}")

    # Seed demo data
    try:
        await seed_database(force=False)
    except Exception as e:
        logger.warning(f"Could not seed database on startup: {e}")

    # Create demo admin if no users exist
    try:
        user_count = await db.users.count_documents({})
        if user_count == 0:
            demo_admin = {
                "id": str(uuid.uuid4()),
                "email": "demo@warehouse.com",
                "hashed_password": hash_password("password123"),
                "name": "Demo Admin",
                "role": "Admin",
                "is_active": True,
                "created_at": datetime.now(timezone.utc).isoformat(),
                "updated_at": datetime.now(timezone.utc).isoformat(),
                "last_login": None,
            }
            await db.users.insert_one(demo_admin)
            logger.info("Created demo admin user (demo@warehouse.com / password123)")
    except Exception as e:
        logger.warning(f"Could not create demo admin on startup: {e}")



app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=os.environ.get("CORS_ORIGINS", "*").split(","),
    allow_methods=["*"],
    allow_headers=["*"],
)

# logging is configured at the top of this file


@app.on_event("shutdown")
async def shutdown_db_client() -> None:
    client.close()

# Search Service Integration (search_service instantiated at top of file)


# ========== SEARCH ENDPOINTS ==========

@api_router.get("/search/inventory")
async def search_inventory(
    user: Dict[str, str] = Depends(get_current_user),
    q: Optional[str] = Query(None),
    category: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    zone: Optional[str] = Query(None),
    qty_min: Optional[int] = Query(None),
    qty_max: Optional[int] = Query(None),
    skip: int = Query(0),
    limit: int = Query(100),
) -> Dict[str, Any]:
    """Search inventory with filters."""
    require_permission(user["role"], "inventory")

    filters = {}
    if category:
        filters["category"] = category
    if status:
        filters["status"] = status
    if zone:
        filters["zone"] = zone
    if qty_min is not None or qty_max is not None:
        filters["qty_range"] = {}
        if qty_min is not None:
            filters["qty_range"]["min"] = qty_min
        if qty_max is not None:
            filters["qty_range"]["max"] = qty_max

    result = await search_service.search_inventory(q, filters, skip, limit)
    return result


@api_router.get("/search/orders")
async def search_orders(
    user: Dict[str, str] = Depends(get_current_user),
    q: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    priority: Optional[str] = Query(None),
    date_start: Optional[str] = Query(None),
    date_end: Optional[str] = Query(None),
    skip: int = Query(0),
    limit: int = Query(100),
) -> Dict[str, Any]:
    """Search orders with filters."""
    require_permission(user["role"], "orders")

    filters = {}
    if status:
        filters["status"] = status
    if priority:
        filters["priority"] = priority
    if date_start or date_end:
        filters["date_range"] = {}
        if date_start:
            filters["date_range"]["start"] = date_start
        if date_end:
            filters["date_range"]["end"] = date_end

    result = await search_service.search_orders(q, filters, skip, limit)
    return result


@api_router.post("/saved-filters", status_code=201)
async def save_filter(
    user: Dict[str, str] = Depends(get_current_user),
    filter_data: SaveFilterRequest = Body(...),
) -> Dict[str, str]:
    """Save a custom filter."""
    filter_id = await search_service.save_filter(
        user["user_id"],
        filter_data.name,
        filter_data.entity_type,
        filter_data.filters
    )
    return {"id": filter_id, "message": "Filter saved successfully"}


@api_router.get("/saved-filters")
async def get_saved_filters(
    user: Dict[str, str] = Depends(get_current_user),
    entity_type: Optional[str] = Query(None),
) -> List[Dict]:
    """Get user's saved filters."""
    filters = await search_service.get_saved_filters(user["user_id"], entity_type)
    return filters


@api_router.delete("/saved-filters/{filter_id}")
async def delete_saved_filter(
    filter_id: str,
    user: Dict[str, str] = Depends(get_current_user),
) -> Dict[str, str]:
    """Delete a saved filter."""
    success = await search_service.delete_saved_filter(filter_id, user["user_id"])
    if success:
        return {"message": "Filter deleted successfully"}
    return {"message": "Filter not found"}


@api_router.get("/search/suggestions")
async def get_search_suggestions(
    user: Dict[str, str] = Depends(get_current_user),
    q: str = Query(...),
    type: str = Query("inventory"),
) -> List[str]:
    """Get autocomplete suggestions."""
    suggestions = await search_service.get_search_suggestions(q, type)
    return suggestions


# Export Endpoints
@api_router.post("/export")
async def export_data(
    user: Dict[str, str] = Depends(get_current_user),
    export_request: ExportRequest = Body(...),
) -> StreamingResponse:
    """Export data to CSV format."""
    try:
        require_permission(user["role"], "inventory")

        # Generate CSV based on entity type
        if export_request.entity_type == "inventory":
            csv_data = await export_service.export_inventory_csv(
                export_request.selected_columns,
                export_request.filters
            )
            filename = f"inventory_export_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}.csv"
        elif export_request.entity_type == "orders":
            csv_data = await export_service.export_orders_csv(
                export_request.selected_columns,
                export_request.filters
            )
            filename = f"orders_export_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}.csv"
        elif export_request.entity_type == "analytics":
            csv_data = await export_service.export_analytics_csv(
                export_request.selected_columns
            )
            filename = f"analytics_export_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}.csv"
        else:
            raise HTTPException(status_code=400, detail="Invalid entity_type")

        # Log export action
        await log_action(
            db,
            action="EXPORT",
            user_id=user["user_id"],
            user_email=user.get("email", "unknown"),
            entity_type=f"export_{export_request.entity_type}",
            entity_id="export",
            entity_details=f"Exported {export_request.entity_type}",
            new_value={"entity_type": export_request.entity_type, "columns": export_request.selected_columns},
        )

        # Return as streaming response
        return StreamingResponse(
            iter([csv_data]),
            media_type="text/csv",
            headers={"Content-Disposition": f"attachment; filename={filename}"}
        )
    except Exception as e:
        logger.error(f"Export error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@api_router.get("/export/columns/{entity_type}")
async def get_export_columns(
    user: Dict[str, str] = Depends(get_current_user),
    entity_type: str = None,
) -> List[str]:
    """Get available columns for export."""
    require_permission(user["role"], "inventory")
    columns = export_service.get_available_columns(entity_type)
    return columns


# Notification Endpoints
@api_router.get("/notifications")
async def get_notifications(
    user: Dict[str, str] = Depends(get_current_user),
    limit: int = Query(50),
    skip: int = Query(0),
) -> Dict[str, Any]:
    """Get paginated notifications for current user."""
    result = await notification_service.get_user_notifications(user["user_id"], limit, skip)
    return result


@api_router.get("/notifications/unread-count")
async def get_unread_count(
    user: Dict[str, str] = Depends(get_current_user),
) -> Dict[str, int]:
    """Get count of unread notifications."""
    count = await notification_service.get_unread_count(user["user_id"])
    return {"unread": count}


@api_router.put("/notifications/{notification_id}/read")
async def mark_notification_read(
    notification_id: str,
    user: Dict[str, str] = Depends(get_current_user),
) -> Dict[str, str]:
    """Mark notification as read."""
    success = await notification_service.mark_as_read(notification_id, user["user_id"])
    if success:
        return {"message": "Notification marked as read"}
    return {"message": "Notification not found"}


@api_router.put("/notifications/read-all")
async def mark_all_read(
    user: Dict[str, str] = Depends(get_current_user),
) -> Dict[str, int]:
    """Mark all notifications as read."""
    count = await notification_service.mark_all_as_read(user["user_id"])
    return {"marked_as_read": count}


@api_router.delete("/notifications/{notification_id}")
async def delete_notification(
    notification_id: str,
    user: Dict[str, str] = Depends(get_current_user),
) -> Dict[str, str]:
    """Delete a notification."""
    success = await notification_service.delete_notification(notification_id, user["user_id"])
    if success:
        return {"message": "Notification deleted"}
    return {"message": "Notification not found"}


@app.websocket("/ws/notifications/{user_id}")
async def websocket_notifications(websocket: WebSocket, user_id: str):
    """
    WebSocket endpoint for real-time notifications.
    Requires user_id in URL and JWT token in query params or headers.
    """
    # Verify user authentication
    try:
        # Get token from query params or headers
        token = None
        if "token" in websocket.query_params:
            token = websocket.query_params["token"]

        if not token:
            await websocket.close(code=4001, reason="Unauthorized")
            return

        # Verify token
        user_data = verify_token(token)
        if not user_data or user_data.get("user_id") != user_id:
            await websocket.close(code=4001, reason="Unauthorized")
            return
    except Exception as e:
        await websocket.close(code=4001, reason="Unauthorized")
        return

    await websocket.accept()
    notification_service.connect(user_id, websocket)

    try:
        while True:
            # Keep connection alive, receive any messages from client
            data = await websocket.receive_text()
            # Server can ignore incoming messages or use them for heartbeat
    except WebSocketDisconnect:
        notification_service.disconnect(user_id, websocket)
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        notification_service.disconnect(user_id, websocket)


# Forecasting Endpoints
@api_router.get("/forecasting/demand/{sku}")
async def forecast_demand(
    sku: str,
    user: Dict[str, str] = Depends(get_current_user),
    days: int = Query(30),
) -> Dict[str, Any]:
    """Forecast demand for a SKU."""
    require_permission(user["role"], "inventory")
    result = await forecasting_service.forecast_demand(sku, days)
    return result


@api_router.get("/forecasting/recommendation/{sku}")
async def get_recommendation(
    sku: str,
    user: Dict[str, str] = Depends(get_current_user),
) -> Dict[str, Any]:
    """Get reorder recommendation for a SKU."""
    require_permission(user["role"], "inventory")

    # Get current inventory
    item = await db.inventory.find_one({"sku": sku})
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")

    # Get historical avg demand
    history = await db.inventory_history.find(
        {"sku": sku}
    ).sort("timestamp", -1).limit(30).to_list(None)

    if history:
        avg_demand = sum(h.get("quantity", 0) for h in history) / len(history)
    else:
        avg_demand = item.get("quantity", 100)

    lead_time = item.get("lead_time_days", 7)
    safety_stock = item.get("reorder_threshold", int(avg_demand * 3))
    reorder_qty = int(avg_demand * 30) + safety_stock

    return {
        "sku": sku,
        "current_quantity": item.get("quantity", 0),
        "average_daily_demand": avg_demand,
        "lead_time_days": lead_time,
        "safety_stock": safety_stock,
        "recommended_reorder_qty": max(1, reorder_qty),
        "reorder_threshold": item.get("reorder_threshold", 0),
    }


@api_router.get("/forecasting/anomalies")
async def detect_anomalies(
    user: Dict[str, str] = Depends(get_current_user),
    sku: Optional[str] = Query(None),
) -> Dict[str, Any]:
    """Detect anomalies in inventory patterns."""
    require_permission(user["role"], "inventory")

    if sku:
        result = await forecasting_service.detect_anomalies(sku)
        return result
    else:
        # Check all SKUs for anomalies
        skus = await db.inventory.distinct("sku")
        all_anomalies = []

        for s in skus[:20]:  # Limit to first 20 for performance
            result = await forecasting_service.detect_anomalies(s)
            if result.get("anomalies"):
                all_anomalies.extend([
                    {**a, "sku": s} for a in result["anomalies"]
                ])

        # Sort by severity
        severity_order = {"critical": 0, "warning": 1}
        all_anomalies.sort(key=lambda x: (
            severity_order.get(x.get("severity"), 2),
            abs(x.get("z_score", 0))
        ), reverse=True)

        return {
            "status": "success",
            "anomalies": all_anomalies[:20],
            "total_skus_checked": len(skus)
        }


@api_router.get("/forecasting/trends/{sku}")
async def get_trends(
    sku: str,
    user: Dict[str, str] = Depends(get_current_user),
    days: int = Query(90),
) -> Dict[str, Any]:
    """Get trend analysis for a SKU."""
    require_permission(user["role"], "inventory")
    result = await forecasting_service.get_trends(sku, days)
    return result


@api_router.post("/forecasting/retrain")
async def retrain_models(
    user: Dict[str, str] = Depends(get_current_user),
) -> Dict[str, Any]:
    """Manually retrain forecasting models."""
    require_permission(user["role"], "inventory")

    # Only admins can retrain
    if user["role"] != "Admin":
        raise HTTPException(status_code=403, detail="Only admins can retrain models")

    result = await forecasting_service.retrain_all_models()

    # Log action
    await log_action(
        db,
        action="RETRAIN",
        user_id=user["user_id"],
        user_email=user.get("email", "unknown"),
        entity_type="forecasting",
        entity_id="retrain",
        entity_details="Retrained forecasting models",
        new_value=result,
    )

    return result


# Analytics Endpoints
@api_router.get("/analytics/dashboard")
async def get_dashboard(
    user: Dict[str, str] = Depends(get_current_user),
    time_range: str = Query("today"),
) -> Dict[str, Any]:
    """Get dashboard KPIs."""
    require_permission(user["role"], "analytics")
    kpis = await analytics_service.get_kpis(time_range)
    return kpis


@api_router.get("/analytics/inventory")
async def get_inventory_metrics(
    user: Dict[str, str] = Depends(get_current_user),
) -> Dict[str, Any]:
    """Get inventory metrics by category and zone."""
    require_permission(user["role"], "inventory")
    metrics = await analytics_service.get_inventory_metrics()
    return metrics


@api_router.get("/analytics/orders")
async def get_order_metrics(
    user: Dict[str, str] = Depends(get_current_user),
    days: int = Query(30),
) -> Dict[str, Any]:
    """Get order fulfillment metrics."""
    require_permission(user["role"], "orders")
    metrics = await analytics_service.get_order_metrics(days)
    return metrics


@api_router.get("/analytics/performance-trends")
async def get_performance_trends(
    user: Dict[str, str] = Depends(get_current_user),
    days: int = Query(30),
) -> Dict[str, Any]:
    """Get performance trend data."""
    require_permission(user["role"], "analytics")
    trends = await analytics_service.get_performance_trends(days)
    return trends


@api_router.get("/analytics/top-items")
async def get_top_items(
    user: Dict[str, str] = Depends(get_current_user),
    limit: int = Query(10),
) -> Dict[str, Any]:
    """Get top moving items."""
    require_permission(user["role"], "inventory")
    items = await analytics_service.get_top_moving_items(limit)
    return items


@api_router.get("/analytics/low-stock")
async def get_low_stock(
    user: Dict[str, str] = Depends(get_current_user),
) -> Dict[str, Any]:
    """Get low stock items requiring attention."""
    require_permission(user["role"], "inventory")
    alerts = await analytics_service.get_low_stock_alerts()
    return alerts


# Include routers at the very bottom after ALL routes are defined
app.include_router(api_router)
app.include_router(create_layout_router(db, require_permission))
