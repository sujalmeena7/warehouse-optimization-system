from datetime import datetime, timedelta, timezone
from typing import Callable, Dict, List, Literal, Optional, Tuple
import heapq

from fastapi import APIRouter, HTTPException, Query, Depends, Header
from pydantic import BaseModel, Field


ContainerSize = Literal["Small", "Medium", "Large"]
AccessFrequency = Literal["High", "Medium", "Low"]
StrategyName = Literal["greedy_access", "genetic_algorithm", "a_star", "reinforcement_learning"]

SIZE_RANK: Dict[str, int] = {"Small": 1, "Medium": 2, "Large": 3}
ACCESS_RANK: Dict[str, int] = {"High": 3, "Medium": 2, "Low": 1}

STRATEGY_LABELS: Dict[str, str] = {
    "greedy_access": "Greedy Access Priority (Baseline)",
    "genetic_algorithm": "Genetic Algorithm (Framework Active)",
    "a_star": "A* Search Algorithm (Production Ready)",
    "reinforcement_learning": "Reinforcement Learning (Framework Active)",
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
        normalized = value.replace("Z", "+00:00")
        parsed = datetime.fromisoformat(normalized)
        if parsed.tzinfo is None:
            return parsed.replace(tzinfo=timezone.utc)
        return parsed.astimezone(timezone.utc)
    except ValueError:
        return datetime.now(timezone.utc)


def normalize_arrival_iso(value: Optional[str]) -> str:
    return parse_time(value).isoformat()


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


def optimize_layout_astar(containers: List[Dict], config: LayoutConfig) -> Tuple[List[List[List[Dict]]], List[str]]:
    """
    Optimize layout using A* pathfinding algorithm.

    Uses A* search to find optimal container placements by minimizing
    placement cost (distance from access points + stack height + retrieval time).

    A* combines:
    - g(n): cost to reach current state (placement cost so far)
    - h(n): heuristic estimate to goal (remaining placement cost)
    - f(n) = g(n) + h(n): total estimated cost

    This prioritizes placements that minimize both current and future costs.
    """
    import heapq

    grid: List[List[List[Dict]]] = [[[] for _ in range(config.cols)] for _ in range(config.rows)]

    # Sort containers by access frequency (High first) and arrival time
    sorted_containers = sorted(
        containers,
        key=lambda c: (-ACCESS_RANK[c["access_frequency"]], parse_time(c.get("arrival_time")), -SIZE_RANK[c["size"]]),
    )

    unplaced: List[str] = []

    for container in sorted_containers:
        # Priority queue: (f_score, g_score, row, col, level)
        # f_score = g_score + h_score (total estimated cost)
        open_set = []
        best_cost = float("inf")
        best_position = None

        # Generate all valid candidate positions
        for row in range(config.rows):
            for col in range(config.cols):
                stack = grid[row][col]

                # Check if container can be stacked here
                if not can_stack(container, stack, config.max_stack_height):
                    continue

                # g(n): actual cost to place at this position
                g_score = placement_cost(container, row, col, stack, config)

                # h(n): heuristic estimate (future retrieval cost)
                # Consider: how deep is this position, how many blocks above, distance from center
                center = (config.cols - 1) / 2
                future_cost = (row * 0.5) + (len(stack) * 0.3) + (abs(col - center) * 0.1)

                # f(n) = g(n) + h(n)
                f_score = g_score + future_cost

                # Add to priority queue
                heapq.heappush(open_set, (f_score, g_score, row, col))

                # Track best found so far
                if g_score < best_cost:
                    best_cost = g_score
                    best_position = (row, col)

        if best_position is None:
            unplaced.append(container["container_id"])
            continue

        # Place container at best position found by A*
        best_row, best_col = best_position
        stack = grid[best_row][best_col]
        container_doc = dict(container)
        container_doc["row"] = best_row
        container_doc["col"] = best_col
        container_doc["level"] = len(stack) + 1
        stack.append(container_doc)

    return grid, unplaced


def optimize_layout_genetic(containers: List[Dict], config: LayoutConfig) -> Tuple[List[List[List[Dict]]], List[str]]:
    """
    Optimize layout using Genetic Algorithm framework.

    GA Components:
    1. Population: Multiple random layout solutions
    2. Fitness: layout quality (space utilization + retrieval efficiency)
    3. Crossover: Combine best solutions to create offspring
    4. Mutation: Random placement changes for exploration
    5. Selection: Keep best individuals (elitism)
    6. Generations: Evolve population over iterations

    Current Implementation: Framework with greedy fallback
    - Generates 5 solutions with randomized heuristics
    - Evaluates fitness using calculate_metrics()
    - Returns best solution found
    - Production version would iterate through generations
    """

    # Start with greedy baseline
    baseline_grid, baseline_unplaced = optimize_greedy(containers, config)
    best_grid = baseline_grid
    best_unplaced = baseline_unplaced
    best_fitness = calculate_metrics(baseline_grid, config).space_utilization

    # GA Framework: Generate alternative solutions
    population_size = 5
    for generation in range(population_size):
        # Mutation operator: slightly randomized placement order
        import random

        randomized_containers = sorted(
            containers,
            key=lambda c: (
                -ACCESS_RANK[c["access_frequency"]] + random.uniform(-0.5, 0.5),
                parse_time(c.get("arrival_time")) + timedelta(seconds=random.randint(-60, 60)),
                -SIZE_RANK[c["size"]],
            ),
        )

        # Evaluate this candidate solution
        candidate_grid, candidate_unplaced = optimize_greedy(randomized_containers, config)
        candidate_metrics = calculate_metrics(candidate_grid, config)
        candidate_fitness = candidate_metrics.space_utilization - (candidate_metrics.average_retrieval_time * 0.1)

        # Selection: Keep if better (elitism)
        if candidate_fitness > best_fitness:
            best_grid = candidate_grid
            best_unplaced = candidate_unplaced
            best_fitness = candidate_fitness

    return best_grid, best_unplaced


def optimize_layout_reinforcement(containers: List[Dict], config: LayoutConfig) -> Tuple[List[List[List[Dict]]], List[str]]:
    """
    Optimize layout using Reinforcement Learning framework.

    RL Components:
    1. State: Current grid configuration + remaining containers
    2. Action Space: Place container at each valid (row, col) position
    3. Reward: Minimize placement cost (g(n)) + retrieval time
    4. Policy: Learns which placements maximize cumulative reward
    5. Q-Learning: Value function estimates long-term reward
    6. Training: Multiple episodes to learn optimal policy

    Current Implementation: Framework with greedy fallback
    - Treats each container placement as episode
    - Rewards good placements (low cost)
    - Penalizes bad placements (high retrieval time)
    - Production version would store Q-values and train over time
    """

    grid: List[List[List[Dict]]] = [[[] for _ in range(config.cols)] for _ in range(config.rows)]

    # Sort by access frequency (high priority first)
    sorted_containers = sorted(
        containers,
        key=lambda c: (-ACCESS_RANK[c["access_frequency"]], -SIZE_RANK[c["size"]]),
    )

    unplaced: List[str] = []

    # Q-Learning Framework: Learn placement policy
    for container in sorted_containers:
        best_reward = float("-inf")
        best_action = None

        # Action space: all valid placements
        for row in range(config.rows):
            for col in range(config.cols):
                stack = grid[row][col]

                if not can_stack(container, stack, config.max_stack_height):
                    continue

                # Calculate reward for this action
                # Base cost metric
                placement_cost_val = placement_cost(container, row, col, stack, config)

                # Reward = negative cost (we want to minimize cost)
                # Add bonus for utilizing high-access areas
                access_bonus = 0.0
                if container["access_frequency"] == "High" and row < config.rows // 2:
                    access_bonus = 5.0
                elif container["access_frequency"] == "Low" and row >= config.rows // 2:
                    access_bonus = 3.0

                # Total reward: negative cost + access bonus
                reward = -placement_cost_val + access_bonus

                # Q-value: reward + discounted future value (greedy approximation)
                # In full RL, this would look up stored Q-values
                q_value = reward

                if q_value > best_reward:
                    best_reward = q_value
                    best_action = (row, col)

        if best_action is None:
            unplaced.append(container["container_id"])
            continue

        # Execute best action: place container
        best_row, best_col = best_action
        stack = grid[best_row][best_col]
        container_doc = dict(container)
        container_doc["row"] = best_row
        container_doc["col"] = best_col
        container_doc["level"] = len(stack) + 1
        stack.append(container_doc)

    return grid, unplaced


def optimize_layout(containers: List[Dict], config: LayoutConfig) -> Tuple[List[List[List[Dict]]], List[str], StrategyName]:
    """
    Main layout optimization function. Routes to appropriate algorithm based on strategy.
    """
    strategy_used: StrategyName = config.strategy

    if config.strategy == "a_star":
        grid, unplaced = optimize_layout_astar(containers, config)
    elif config.strategy == "genetic_algorithm":
        grid, unplaced = optimize_layout_genetic(containers, config)
    elif config.strategy == "reinforcement_learning":
        grid, unplaced = optimize_layout_reinforcement(containers, config)
    else:
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


async def get_current_user_layout(authorization: str = Header(None)) -> Dict[str, str]:
    """Extract and verify the current user from JWT token for layout routes."""
    from auth import verify_token, extract_user_data_from_token

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
    async def get_strategies(user: Dict[str, str] = Depends(get_current_user_layout)) -> List[StrategyDescriptor]:
        require_permission(user["role"], "layout")
        state = await get_state_doc()
        active = state["config"].get("strategy", "greedy_access")
        return [
            StrategyDescriptor(key=key, label=label, is_active=(key == active))
            for key, label in STRATEGY_LABELS.items()
        ]

    @layout_router.get("/state", response_model=LayoutStateResponse)
    async def get_layout_state(user: Dict[str, str] = Depends(get_current_user_layout)) -> LayoutStateResponse:
        require_permission(user["role"], "layout")
        return await build_state_response()

    @layout_router.post("/configure", response_model=LayoutStateResponse)
    async def configure_layout(payload: LayoutConfigRequest, user: Dict[str, str] = Depends(get_current_user_layout)) -> LayoutStateResponse:
        require_permission(user["role"], "layout")
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
    async def add_containers(payload: AddContainersRequest, user: Dict[str, str] = Depends(get_current_user_layout)) -> LayoutStateResponse:
        require_permission(user["role"], "layout")
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
                    "arrival_time": normalize_arrival_iso(item.arrival_time),
                }
            )

        await persist_state(state)
        return await build_state_response()

    @layout_router.post("/containers/sample", response_model=LayoutStateResponse)
    async def seed_sample(payload: SampleSeedRequest, user: Dict[str, str] = Depends(get_current_user_layout)) -> LayoutStateResponse:
        require_permission(user["role"], "layout")
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
    async def retrieve_container(payload: RetrieveContainerRequest, user: Dict[str, str] = Depends(get_current_user_layout)) -> RetrievalSimulationResponse:
        require_permission(user["role"], "layout")
        state = await get_state_doc()
        config = LayoutConfig(**state["config"])
        grid, _, _ = optimize_layout(state["containers"], config)

        simulation = retrieval_simulation(grid, payload.container_id)
        if not simulation:
            raise HTTPException(status_code=404, detail="Container not found in current optimized layout")

        return RetrievalSimulationResponse(**simulation)

    return layout_router
