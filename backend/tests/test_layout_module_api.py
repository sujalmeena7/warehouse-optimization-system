import os

import pytest
import requests


# Layout module API coverage: grid config, sample/add containers, stacking constraints, retrieval, metrics, role access
BASE_URL = os.environ.get("REACT_APP_BACKEND_URL")
if not BASE_URL:
    pytest.skip("REACT_APP_BACKEND_URL is not set", allow_module_level=True)
BASE_URL = BASE_URL.rstrip("/")

SIZE_RANK = {"Small": 1, "Medium": 2, "Large": 3}
ACCESS_RANK = {"Low": 1, "Medium": 2, "High": 3}


@pytest.fixture(scope="session")
def api_client():
    session = requests.Session()
    session.headers.update({"Content-Type": "application/json"})
    return session


@pytest.fixture(scope="function")
def reset_layout(api_client):
    response = api_client.post(
        f"{BASE_URL}/api/layout/configure",
        params={"role": "Manager"},
        json={
            "rows": 4,
            "cols": 4,
            "max_stack_height": 2,
            "strategy": "greedy_access",
            "clear_containers": True,
        },
    )
    assert response.status_code == 200
    return response.json()


class TestLayoutModuleApi:
    def test_layout_state_returns_configurable_grid(self, api_client, reset_layout):
        state_response = api_client.get(f"{BASE_URL}/api/layout/state", params={"role": "Manager"})
        assert state_response.status_code == 200

        state = state_response.json()
        assert state["config"]["rows"] == 4
        assert state["config"]["cols"] == 4
        assert len(state["grid"]) == 4
        assert len(state["grid"][0]) == 4

    def test_configure_updates_rows_cols_height_and_strategy(self, api_client):
        response = api_client.post(
            f"{BASE_URL}/api/layout/configure",
            params={"role": "Manager"},
            json={
                "rows": 7,
                "cols": 6,
                "max_stack_height": 5,
                "strategy": "a_star",
                "clear_containers": False,
            },
        )
        assert response.status_code == 200

        data = response.json()
        assert data["config"]["rows"] == 7
        assert data["config"]["cols"] == 6
        assert data["config"]["max_stack_height"] == 5
        assert data["config"]["strategy"] == "a_star"
        assert data["strategy_used"] == "greedy_access"

    def test_sample_seed_replace_and_append_without_duplicates(self, api_client, reset_layout):
        replace_response = api_client.post(
            f"{BASE_URL}/api/layout/containers/sample",
            params={"role": "Manager"},
            json={"replace_existing": True},
        )
        assert replace_response.status_code == 200
        replaced = replace_response.json()
        assert replaced["total_containers"] == 6

        append_response = api_client.post(
            f"{BASE_URL}/api/layout/containers/sample",
            params={"role": "Manager"},
            json={"replace_existing": False},
        )
        assert append_response.status_code == 200
        appended = append_response.json()
        assert appended["total_containers"] == 6

    def test_add_containers_validates_unique_ids(self, api_client, reset_layout):
        response = api_client.post(
            f"{BASE_URL}/api/layout/containers",
            params={"role": "Manager"},
            json={
                "containers": [
                    {
                        "container_id": "TEST-DUP-1",
                        "size": "Small",
                        "weight": 10,
                        "access_frequency": "Medium",
                    },
                    {
                        "container_id": "TEST-DUP-1",
                        "size": "Large",
                        "weight": 50,
                        "access_frequency": "Low",
                    },
                ]
            },
        )
        assert response.status_code == 409
        assert "Duplicate container IDs" in response.json()["detail"]

    def test_add_containers_validates_existing_duplicate_ids(self, api_client, reset_layout):
        seed_response = api_client.post(
            f"{BASE_URL}/api/layout/containers/sample",
            params={"role": "Manager"},
            json={"replace_existing": True},
        )
        assert seed_response.status_code == 200

        response = api_client.post(
            f"{BASE_URL}/api/layout/containers",
            params={"role": "Manager"},
            json={
                "containers": [
                    {
                        "container_id": "CNT-1002",
                        "size": "Small",
                        "weight": 20,
                        "access_frequency": "High",
                    }
                ]
            },
        )
        assert response.status_code == 409
        assert "already exist" in response.json()["detail"]

    def test_add_containers_applies_stacking_rules_and_height_limit(self, api_client, reset_layout):
        containers = []
        for idx in range(1, 27):
            containers.append(
                {
                    "container_id": f"TEST-STK-{idx}",
                    "size": "Small" if idx % 3 else "Medium",
                    "weight": 15 + idx,
                    "access_frequency": "High" if idx % 2 else "Medium",
                }
            )

        response = api_client.post(
            f"{BASE_URL}/api/layout/containers",
            params={"role": "Manager"},
            json={"containers": containers},
        )
        assert response.status_code == 200
        data = response.json()

        assert data["config"]["max_stack_height"] == 2
        assert data["placed_containers"] <= 32
        assert data["total_containers"] == 26

        for row in data["grid"]:
            for cell in row:
                assert cell["stack_height"] <= 2
                ordered = sorted(cell["containers"], key=lambda c: c["level"])
                for i in range(len(ordered) - 1):
                    below = ordered[i]
                    above = ordered[i + 1]
                    assert SIZE_RANK[above["size"]] <= SIZE_RANK[below["size"]]
                    assert ACCESS_RANK[above["access_frequency"]] >= ACCESS_RANK[below["access_frequency"]]

    def test_retrieval_simulation_returns_blockers_movements_and_steps(self, api_client, reset_layout):
        add_response = api_client.post(
            f"{BASE_URL}/api/layout/containers",
            params={"role": "Manager"},
            json={
                "containers": [
                    {
                        "container_id": "TEST-RET-BASE",
                        "size": "Large",
                        "weight": 90,
                        "access_frequency": "Low",
                    },
                    {
                        "container_id": "TEST-RET-TOP",
                        "size": "Small",
                        "weight": 20,
                        "access_frequency": "High",
                    },
                ]
            },
        )
        assert add_response.status_code == 200

        retrieval = api_client.post(
            f"{BASE_URL}/api/layout/retrieve",
            params={"role": "Manager"},
            json={"container_id": "TEST-RET-BASE"},
        )
        assert retrieval.status_code == 200
        data = retrieval.json()

        assert data["found"] is True
        assert isinstance(data["blockers"], list)
        assert data["movement_count"] >= 0
        assert data["estimated_retrieval_time"] > 0
        assert data["estimated_retrieval_cost"] > 0
        assert len(data["steps"]) >= 1
        assert data["steps"][-1]["action"] == "Retrieve target container"

    def test_metrics_consistency_space_and_movement_averages(self, api_client, reset_layout):
        seed_response = api_client.post(
            f"{BASE_URL}/api/layout/containers/sample",
            params={"role": "Manager"},
            json={"replace_existing": True},
        )
        assert seed_response.status_code == 200
        state = seed_response.json()

        capacity = state["config"]["rows"] * state["config"]["cols"] * state["config"]["max_stack_height"]
        expected_utilization = round((state["placed_containers"] / capacity) * 100, 2)
        assert state["metrics"]["space_utilization"] == expected_utilization

        if state["placed_containers"] > 0:
            expected_avg_movements = round(
                state["metrics"]["total_container_movements_for_all_retrievals"] / state["placed_containers"],
                2,
            )
            assert state["metrics"]["average_container_movements"] == expected_avg_movements

    def test_staff_can_access_layout_but_not_analytics(self, api_client, reset_layout):
        layout_response = api_client.get(f"{BASE_URL}/api/layout/state", params={"role": "Staff"})
        assert layout_response.status_code == 200

        analytics_response = api_client.get(f"{BASE_URL}/api/analytics/trends", params={"role": "Staff"})
        assert analytics_response.status_code == 403
