import os

import pytest
import requests


# Core warehouse API coverage: auth, dashboard, inventory, orders, routes, analytics, alerts
BASE_URL = os.environ.get("REACT_APP_BACKEND_URL")
if not BASE_URL:
    pytest.skip("REACT_APP_BACKEND_URL is not set", allow_module_level=True)
BASE_URL = BASE_URL.rstrip("/")


@pytest.fixture(scope="session")
def api_client():
    session = requests.Session()
    session.headers.update({"Content-Type": "application/json"})
    return session


@pytest.fixture(scope="session")
def seeded(api_client):
    response = api_client.post(f"{BASE_URL}/api/bootstrap/seed")
    assert response.status_code in [200, 201]
    data = response.json()
    assert "status" in data
    return data


class TestWarehouseCoreApi:
    def test_demo_login_admin_and_permissions(self, api_client, seeded):
        response = api_client.post(
            f"{BASE_URL}/api/auth/demo-login",
            json={"name": "TEST_QA_Admin", "role": "Admin"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["role"] == "Admin"
        assert data["permissions"]["analytics"] is True
        assert "dashboard" in data["allowed_pages"]

    def test_dashboard_overview_loads_for_manager(self, api_client, seeded):
        response = api_client.get(f"{BASE_URL}/api/warehouse/overview", params={"role": "Manager"})
        assert response.status_code == 200
        data = response.json()
        assert data["kpis"]["total_skus"] > 0
        assert isinstance(data["recent_orders"], list)
        assert len(data["efficiency_trend"]) == 7

    def test_inventory_filter_and_search(self, api_client, seeded):
        base_response = api_client.get(
            f"{BASE_URL}/api/inventory",
            params={"role": "Manager", "search": "SKU-1004"},
        )
        assert base_response.status_code == 200
        base_data = base_response.json()
        assert len(base_data) >= 1
        expected_status = base_data[0]["stock_status"]

        response = api_client.get(
            f"{BASE_URL}/api/inventory",
            params={"role": "Manager", "search": "SKU-1004", "status": expected_status},
        )
        assert response.status_code == 200
        data = response.json()
        assert len(data) >= 1
        assert data[0]["sku"] == "SKU-1004"
        assert data[0]["stock_status"] == expected_status

    def test_inventory_update_persists_for_manager(self, api_client, seeded):
        get_response = api_client.get(
            f"{BASE_URL}/api/inventory",
            params={"role": "Manager", "search": "SKU-1006"},
        )
        assert get_response.status_code == 200
        item = get_response.json()[0]
        item_id = item["id"]
        new_qty = item["quantity"] + 1

        update_response = api_client.put(
            f"{BASE_URL}/api/inventory/{item_id}",
            params={"role": "Manager"},
            json={"quantity": new_qty},
        )
        assert update_response.status_code == 200
        updated = update_response.json()
        assert updated["quantity"] == new_qty

        verify_response = api_client.get(
            f"{BASE_URL}/api/inventory",
            params={"role": "Manager", "search": item["sku"]},
        )
        assert verify_response.status_code == 200
        verify_item = verify_response.json()[0]
        assert verify_item["quantity"] == new_qty

    def test_orders_list_and_status_progression(self, api_client, seeded):
        list_response = api_client.get(f"{BASE_URL}/api/orders", params={"role": "Manager"})
        assert list_response.status_code == 200
        data = list_response.json()
        assert len(data["orders"]) > 0

        non_shipped = next((o for o in data["orders"] if o["status"] != "shipped"), None)
        assert non_shipped is not None
        next_status = {"queued": "picking", "picking": "packed", "packed": "shipped"}[non_shipped["status"]]

        update_response = api_client.patch(
            f"{BASE_URL}/api/orders/{non_shipped['id']}/status",
            params={"role": "Manager"},
            json={"status": next_status},
        )
        assert update_response.status_code == 200
        updated = update_response.json()
        assert updated["status"] == next_status

        verify_response = api_client.get(f"{BASE_URL}/api/orders", params={"role": "Manager"})
        assert verify_response.status_code == 200
        verify_order = next(o for o in verify_response.json()["orders"] if o["id"] == non_shipped["id"])
        assert verify_order["status"] == next_status

    def test_route_optimization_generation(self, api_client, seeded):
        orders_response = api_client.get(f"{BASE_URL}/api/orders", params={"role": "Manager"})
        assert orders_response.status_code == 200
        order_id = orders_response.json()["orders"][0]["id"]

        route_response = api_client.get(
            f"{BASE_URL}/api/routes/optimize",
            params={"role": "Manager", "order_id": order_id},
        )
        assert route_response.status_code == 200
        route_data = route_response.json()
        assert route_data["order_id"] == order_id
        assert len(route_data["steps"]) > 0
        assert isinstance(route_data["total_distance"], int)

    def test_analytics_allowed_for_manager(self, api_client, seeded):
        response = api_client.get(f"{BASE_URL}/api/analytics/trends", params={"role": "Manager"})
        assert response.status_code == 200
        data = response.json()
        assert len(data["category_turnover"]) > 0
        assert len(data["fulfillment_trend"]) == 7
        assert len(data["demand_forecast"]) == 7

    def test_analytics_forbidden_for_staff(self, api_client, seeded):
        response = api_client.get(f"{BASE_URL}/api/analytics/trends", params={"role": "Staff"})
        assert response.status_code == 403
        assert "cannot access analytics" in response.json()["detail"]

    def test_alerts_severity_filter(self, api_client, seeded):
        response = api_client.get(f"{BASE_URL}/api/alerts", params={"role": "Manager", "severity": "critical"})
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) > 0
        assert all(alert["severity"] == "critical" for alert in data)
