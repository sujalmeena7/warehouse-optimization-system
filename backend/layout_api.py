from datetime import datetime, timedelta, timezone
from typing import Callable, Dict, List, Literal, Optional, Tuple

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field


ContainerSize = Literal["Small", "Medium", "Large"]
AccessFrequency = Literal["High", "Medium", "Low"]
StrategyName = Literal["greedy_access", "genetic_algorithm", "a_star", "reinforcement_learning"]

SIZE_RANK: Dict[str, int] = {"Small": 1, "Medium": 2, "Large": 3}
ACCESS_RANK: Dict[str, int] = {"High": 3, "Medium": 2, "Low": 1}

STRATEGY_LABELS: Dict[str, str] = {
    "greedy_access": "Greedy Access Priority",
    "genetic_algorithm": "Genetic Algorithm (placeholder)",
    "a_star": "A* Search (placeholder)",
    "reinforcement_learning": "Reinforcement Learning (placeholder)",
}


class LayoutConfig(BaseModel):
    rows: int = Field(default=10, ge=4, le=20)
    cols: int = Field(default=10, ge=4, le=20)
    max_stack_height: int = Field(default=5, ge=2, le=8)
    strategy: StrategyName = "greedy_access"


class LayoutConfigRequest(LayoutConfig):
    clear_containers: bool = False


class ContainerInput(BaseModel):
    container_id: str = Field(min_length=3, max_length=40)
    size: ContainerSize
    weight: float = Field(gt=0)
    access_frequency: AccessFrequency
    arrival_time: Optional[str] = None


class AddContainersRequest(BaseModel):
    containers: List[ContainerInput]


class SampleSeedRequest(BaseModel):
    replace_existing: bool = False


class RetrieveContainerRequest(BaseModel):
    container_id: str = Field(min_length=3)


class StrategyDescriptor(BaseModel):
    key: StrategyName
    label: str
    is_active: bool


class PlacementContainer(BaseModel):
    container_id: str
    size: ContainerSize
    weight: float
    access_frequency: AccessFrequency
    arrival_time: str
    level: int


class GridCellView(BaseModel):
    row: int
    col: int
    stack_height: int
    available_slots: int
    is_front_row: bool
    containers: List[PlacementContainer]


class LayoutMetrics(BaseModel):
    space_utilization: float
    average_retrieval_time: float
    average_container_movements: float
    total_container_movements_for_all_retrievals: int


class LayoutStateResponse(BaseModel):
    config: LayoutConfig
    strategy_used: StrategyName
    total_containers: int
    placed_containers: int
    unplaced_containers: List[str]
    metrics: LayoutMetrics
    grid: List[List[GridCellView]]


class RetrievalStep(BaseModel):
    step: int
    action: str
    container_id: str


class RetrievalSimulationResponse(BaseModel):
    container_id: str
    found: bool
    row: int
    col: int
    level: int
    blockers: List[str]
    movement_count: int
    estimated_retrieval_time: float
    estimated_retrieval_cost: float
    steps: List[RetrievalStep]


DEFAULT_LAYOUT_STATE = {
    "id": "active-layout",
    "config": LayoutConfig().model_dump(),
    "containers": [],
}


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def parse_time(value: Optional[str]) -> datetime:
    if not value:
        return datetime.now(timezone.utc)
    try:
        return datetime.fromisoformat(value)
    except ValueError:
        return datetime.now(timezone.utc)


def can_stack(container: Dict, stack: List[Dict], max_height: int) -> bool:
    if len(stack) >= max_height:
        return False
    if not stack:
        return True

    top = stack[-1]
    if SIZE_RANK[top["size"]] < SIZE_RANK[container["size"]]:
        return False

    # Protect high-access containers from getting blocked by lower-access items.
    if ACCESS_RANK[top["access_frequency"]] > ACCESS_RANK[container["access_frequency"]]:
        return False
    return True


def placement_cost(container: Dict, row: int, col: int, stack: List[Dict], config: LayoutConfig) -> float:
    center = (config.cols - 1) / 2
    height = len(stack)
    access = container["access_frequency"]

    if access == "High":
        return (row * 4.0) + (height * 3.8) + (abs(col - center) * 0.35)
    if access == "Medium":
        return (row * 2.2) + (height * 2.0) + (abs(col - center) * 0.25)

    # Low-access containers are pushed deeper (higher row index) and lower stack pressure.
    depth_distance = config.rows - 1 - row
    return (depth_distance * 1.8) + (height * 1.2) + (abs(col - center) * 0.2)


def optimize_greedy(containers: List[Dict], config: LayoutConfig) -> Tuple[List[List[List[Dict]]], List[str]]:
    grid: List[List[List[Dict]]] = [[[] for _ in range(config.cols)] for _ in range(config.rows)]

    ordered = sorted(
        containers,
        key=lambda item: (
            -ACCESS_RANK[item["access_frequency"]],
            parse_time(item.get("arrival_time")),
            -SIZE_RANK[item["size"]],
            item["container_id"],
        ),
    )

    unplaced: List[str] = []
    for container in ordered:
        candidates: List[Tuple[float, int, int]] = []
        for row in range(config.rows):
            for col in range(config.cols):
                current_stack = grid[row][col]
                if not can_stack(container, current_stack, config.max_stack_height):
                    continue
                candidates.append((placement_cost(container, row, col, current_stack, config), row, col))

        if not candidates:
            unplaced.append(container["container_id"])
            continue

        _, best_row, best_col = min(candidates, key=lambda item: item[0])
        stack = grid[best_row][best_col]
        container_doc = dict(container)
        container_doc["row"] = best_row
        container_doc["col"] = best_col
        container_doc["level"] = len(stack) + 1
        stack.append(container_doc)

    return grid, unplaced


def optimize_layout(containers: List[Dict], config: LayoutConfig) -> Tuple[List[List[List[Dict]]], List[str], StrategyName]:
    strategy_used: StrategyName = config.strategy
    # Pluggable strategy architecture (future GA/A*/RL can be injected here)
    if config.strategy in {"genetic_algorithm", "a_star", "reinforcement_learning"}:
        strategy_used = "greedy_access"
    grid, unplaced = optimize_greedy(containers, config)
    return grid, unplaced, strategy_used


def retrieval_simulation(grid: List[List[List[Dict]]], container_id: str) -> Optional[Dict]:
    for row in grid:
        for stack in row:
            for index, container in enumerate(stack):
                if container["container_id"] == container_id:
                    blockers = stack[index + 1 :]
                    move_count = len(blockers)
                    distance_component = (container["row"] + 1) * 1.2
                    removal_component = move_count * 2.3
                    size_component = {"Small": 0.8, "Medium": 1.2, "Large": 1.7}[container["size"]]
                    weight_component = min(2.0, container["weight"] / 60)
                    retrieval_time = round(distance_component + removal_component + size_component + weight_component, 2)
                    retrieval_cost = round((retrieval_time * 1.4) + (move_count * 0.9), 2)

                    steps: List[Dict] = []
                    step_counter = 1
                    for blocker in reversed(blockers):
                        steps.append(
                            {
                                "step": step_counter,
                                "action": "Remove blocking container",
                                "container_id": blocker["container_id"],
                            }
                        )
                        step_counter += 1

                    steps.append(
                        {
                            "step": step_counter,
                            "action": "Retrieve target container",
                            "container_id": container["container_id"],
                        }
                    )

                    return {
                        "container_id": container["container_id"],
                        "found": True,
                        "row": container["row"],
                        "col": container["col"],
                        "level": container["level"],
                        "blockers": [item["container_id"] for item in blockers],
                        "movement_count": move_count,
                        "estimated_retrieval_time": retrieval_time,
                        "estimated_retrieval_cost": retrieval_cost,
                        "steps": steps,
                    }
    return None


def calculate_metrics(grid: List[List[List[Dict]]], config: LayoutConfig) -> LayoutMetrics:
    total_capacity = config.rows * config.cols * config.max_stack_height
    all_containers = [container for row in grid for stack in row for container in stack]
    total_containers = len(all_containers)

    if total_containers == 0:
        return LayoutMetrics(
            space_utilization=0.0,
            average_retrieval_time=0.0,
            average_container_movements=0.0,
            total_container_movements_for_all_retrievals=0,
        )

    retrieval_times: List[float] = []
    movement_counts: List[int] = []
    for container in all_containers:
        simulation = retrieval_simulation(grid, container["container_id"])
        if simulation:
            retrieval_times.append(simulation["estimated_retrieval_time"])
            movement_counts.append(simulation["movement_count"])

    return LayoutMetrics(
        space_utilization=round((total_containers / max(total_capacity, 1)) * 100, 2),
        average_retrieval_time=round(sum(retrieval_times) / max(len(retrieval_times), 1), 2),
        average_container_movements=round(sum(movement_counts) / max(len(movement_counts), 1), 2),
        total_container_movements_for_all_retrievals=sum(movement_counts),
    )


def sample_containers() -> List[Dict]:
    now = datetime.now(timezone.utc)
    return [
        {
            "container_id": "CNT-1001",
            "size": "Large",
            "weight": 92,
            "access_frequency": "Low",
            "arrival_time": (now - timedelta(hours=36)).isoformat(),
        },
        {
            "container_id": "CNT-1002",
            "size": "Medium",
            "weight": 57,
            "access_frequency": "High",
            "arrival_time": (now - timedelta(hours=8)).isoformat(),
        },
        {
            "container_id": "CNT-1003",
            "size": "Small",
            "weight": 28,
            "access_frequency": "High",
            "arrival_time": (now - timedelta(hours=5)).isoformat(),
        },
        {
            "container_id": "CNT-1004",
            "size": "Large",
            "weight": 96,
            "access_frequency": "Medium",
            "arrival_time": (now - timedelta(hours=20)).isoformat(),
        },
        {
            "container_id": "CNT-1005",
            "size": "Medium",
            "weight": 61,
            "access_frequency": "Low",
            "arrival_time": (now - timedelta(hours=40)).isoformat(),
        },
        {
            "container_id": "CNT-1006",
            "size": "Small",
            "weight": 24,
            "access_frequency": "Medium",
            "arrival_time": (now - timedelta(hours=12)).isoformat(),
        },
    ]


def create_layout_router(db, require_permission: Callable[[str, str], None]) -> APIRouter:
    layout_router = APIRouter(prefix="/api/layout", tags=["layout"])

    async def get_state_doc() -> Dict:
        doc = await db.layout_states.find_one({"id": DEFAULT_LAYOUT_STATE["id"]}, {"_id": 0})
        if doc:
            return doc
        default_doc = {
            "id": DEFAULT_LAYOUT_STATE["id"],
            "config": dict(DEFAULT_LAYOUT_STATE["config"]),
            "containers": [],
        }
        await db.layout_states.insert_one(dict(default_doc))
        return default_doc

    async def persist_state(doc: Dict) -> None:
        await db.layout_states.update_one(
            {"id": DEFAULT_LAYOUT_STATE["id"]},
            {"$set": {"config": doc["config"], "containers": doc["containers"]}},
            upsert=True,
        )

    def build_grid_response(grid: List[List[List[Dict]]], config: LayoutConfig) -> List[List[GridCellView]]:
        rows: List[List[GridCellView]] = []
        for row_index in range(config.rows):
            row_cells: List[GridCellView] = []
            for col_index in range(config.cols):
                stack = grid[row_index][col_index]
                row_cells.append(
                    GridCellView(
                        row=row_index,
                        col=col_index,
                        stack_height=len(stack),
                        available_slots=max(0, config.max_stack_height - len(stack)),
                        is_front_row=row_index == 0,
                        containers=[
                            PlacementContainer(
                                container_id=item["container_id"],
                                size=item["size"],
                                weight=item["weight"],
                                access_frequency=item["access_frequency"],
                                arrival_time=item["arrival_time"],
                                level=item["level"],
                            )
                            for item in stack
                        ],
                    )
                )
            rows.append(row_cells)
        return rows

    async def build_state_response() -> LayoutStateResponse:
        state = await get_state_doc()
        config = LayoutConfig(**state["config"])
        grid, unplaced, strategy_used = optimize_layout(state["containers"], config)
        metrics = calculate_metrics(grid, config)

        return LayoutStateResponse(
            config=config,
            strategy_used=strategy_used,
            total_containers=len(state["containers"]),
            placed_containers=len(state["containers"]) - len(unplaced),
            unplaced_containers=unplaced,
            metrics=metrics,
            grid=build_grid_response(grid, config),
        )

    @layout_router.get("/strategies", response_model=List[StrategyDescriptor])
    async def get_strategies(role: str = Query(...)) -> List[StrategyDescriptor]:
        require_permission(role, "layout")
        state = await get_state_doc()
        active = state["config"].get("strategy", "greedy_access")
        return [
            StrategyDescriptor(key=key, label=label, is_active=(key == active))
            for key, label in STRATEGY_LABELS.items()
        ]

    @layout_router.get("/state", response_model=LayoutStateResponse)
    async def get_layout_state(role: str = Query(...)) -> LayoutStateResponse:
        require_permission(role, "layout")
        return await build_state_response()

    @layout_router.post("/configure", response_model=LayoutStateResponse)
    async def configure_layout(payload: LayoutConfigRequest, role: str = Query(...)) -> LayoutStateResponse:
        require_permission(role, "layout")
        state = await get_state_doc()
        state["config"] = LayoutConfig(
            rows=payload.rows,
            cols=payload.cols,
            max_stack_height=payload.max_stack_height,
            strategy=payload.strategy,
        ).model_dump()
        if payload.clear_containers:
            state["containers"] = []
        await persist_state(state)
        return await build_state_response()

    @layout_router.post("/containers", response_model=LayoutStateResponse)
    async def add_containers(payload: AddContainersRequest, role: str = Query(...)) -> LayoutStateResponse:
        require_permission(role, "layout")
        state = await get_state_doc()

        existing_ids = {item["container_id"] for item in state["containers"]}
        incoming_ids = [item.container_id for item in payload.containers]
        if len(incoming_ids) != len(set(incoming_ids)):
            raise HTTPException(status_code=409, detail="Duplicate container IDs in request")

        duplicate_ids = [item_id for item_id in incoming_ids if item_id in existing_ids]
        if duplicate_ids:
            raise HTTPException(status_code=409, detail=f"Container IDs already exist: {', '.join(duplicate_ids)}")

        for item in payload.containers:
            state["containers"].append(
                {
                    "container_id": item.container_id,
                    "size": item.size,
                    "weight": item.weight,
                    "access_frequency": item.access_frequency,
                    "arrival_time": item.arrival_time or utc_now_iso(),
                }
            )

        await persist_state(state)
        return await build_state_response()

    @layout_router.post("/containers/sample", response_model=LayoutStateResponse)
    async def seed_sample(payload: SampleSeedRequest, role: str = Query(...)) -> LayoutStateResponse:
        require_permission(role, "layout")
        state = await get_state_doc()
        sample = sample_containers()

        if payload.replace_existing:
            state["containers"] = sample
        else:
            existing = {item["container_id"] for item in state["containers"]}
            for item in sample:
                if item["container_id"] not in existing:
                    state["containers"].append(item)

        await persist_state(state)
        return await build_state_response()

    @layout_router.post("/retrieve", response_model=RetrievalSimulationResponse)
    async def retrieve_container(payload: RetrieveContainerRequest, role: str = Query(...)) -> RetrievalSimulationResponse:
        require_permission(role, "layout")
        state = await get_state_doc()
        config = LayoutConfig(**state["config"])
        grid, _, _ = optimize_layout(state["containers"], config)

        simulation = retrieval_simulation(grid, payload.container_id)
        if not simulation:
            raise HTTPException(status_code=404, detail="Container not found in current optimized layout")

        return RetrievalSimulationResponse(**simulation)

    return layout_router
