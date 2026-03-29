#!/usr/bin/env python
"""
API Integration Tests - Test all endpoints live
Run with: python test_api_live.py
"""

import requests
import json
import time
from typing import Dict, Any, Optional

BASE_URL = "http://localhost:8001/api"
TIMEOUT = 5

class APITester:
    def __init__(self):
        self.access_token = None
        self.refresh_token = None
        self.user_id = None
        self.session = requests.Session()
        self.test_results = []

    def log_test(self, name: str, passed: bool, details: str = ""):
        status = "[OK]" if passed else "[FAIL]"
        print(f"{status} {name}")
        if details:
            print(f"     {details}")
        self.test_results.append({"name": name, "passed": passed, "details": details})

    def check_server(self) -> bool:
        """Check if server is running"""
        try:
            resp = requests.get(f"{BASE_URL}/", timeout=2)
            return resp.status_code == 200
        except:
            return False

    def make_request(self, method: str, endpoint: str, data: Dict = None, expect_code: int = 200, auth_required: bool = False) -> Optional[Dict]:
        """Make HTTP request with optional auth"""
        url = f"{BASE_URL}{endpoint}"
        headers = {}

        if auth_required and self.access_token:
            headers["Authorization"] = f"Bearer {self.access_token}"

        try:
            if method == "GET":
                resp = requests.get(url, headers=headers, timeout=TIMEOUT)
            elif method == "POST":
                resp = requests.post(url, json=data, headers=headers, timeout=TIMEOUT)
            elif method == "PUT":
                resp = requests.put(url, json=data, headers=headers, timeout=TIMEOUT)
            elif method == "PATCH":
                resp = requests.patch(url, json=data, headers=headers, timeout=TIMEOUT)
            else:
                raise ValueError(f"Unknown method: {method}")

            if resp.status_code == expect_code:
                try:
                    return resp.json()
                except:
                    return {"_raw": resp.text}
            else:
                print(f"     Status: {resp.status_code} (expected {expect_code})")
                print(f"     Response: {resp.text[:200]}")
                return None
        except Exception as e:
            print(f"     Error: {str(e)}")
            return None

    # ========== AUTHENTICATION TESTS ==========

    def test_register_user(self):
        """Test user registration"""
        payload = {
            "email": f"testuser-{int(time.time())}@warehouse.com",
            "password": "SecurePassword123!",
            "name": "Test User"
        }
        result = self.make_request("POST", "/auth/register", payload, expect_code=201)
        if result and "access_token" in result:
            self.access_token = result["access_token"]
            self.refresh_token = result.get("refresh_token")
            self.user_id = result.get("user_id")
            self.log_test("Register user", True, f"User: {result.get('email')}")
            return True
        self.log_test("Register user", False)
        return False

    def test_login_user(self):
        """Test user login"""
        # Register first
        email = f"test-{int(time.time())}@warehouse.com"
        password = "TestPass123!"

        # Register
        reg_payload = {"email": email, "password": password, "name": "Test"}
        self.make_request("POST", "/auth/register", reg_payload)

        # Login
        login_payload = {"email": email, "password": password}
        result = self.make_request("POST", "/auth/login", login_payload)

        if result and "access_token" in result:
            self.access_token = result["access_token"]
            self.refresh_token = result.get("refresh_token")
            self.log_test("Login user", True, f"Token: {result['access_token'][:30]}...")
            return True

        self.log_test("Login user", False)
        return False

    def test_refresh_token(self):
        """Test token refresh"""
        if not self.refresh_token:
            self.log_test("Refresh token", False, "No refresh token available")
            return False

        payload = {"refresh_token": self.refresh_token}
        result = self.make_request("POST", "/auth/refresh", payload)

        if result and "access_token" in result:
            self.access_token = result["access_token"]
            self.log_test("Refresh token", True)
            return True

        self.log_test("Refresh token", False)
        return False

    # ========== PROTECTED ENDPOINT TESTS ==========

    def test_get_overview(self):
        """Test dashboard overview endpoint"""
        result = self.make_request("GET", "/warehouse/overview", auth_required=True)
        if result:
            self.log_test("Get warehouse overview", True, f"Status: {result.get('status', 'OK')}")
            return True
        self.log_test("Get warehouse overview", False)
        return False

    def test_get_inventory(self):
        """Test get inventory endpoint"""
        result = self.make_request("GET", "/inventory", auth_required=True)
        if result is not None and isinstance(result, list):
            self.log_test("Get inventory", True, f"Items: {len(result)}")
            return True
        self.log_test("Get inventory", False)
        return False

    def test_get_orders(self):
        """Test get orders endpoint"""
        result = self.make_request("GET", "/orders", auth_required=True)
        if result is not None and isinstance(result, list):
            self.log_test("Get orders", True, f"Orders: {len(result)}")
            return True
        self.log_test("Get orders", False)
        return False

    def test_get_audit_logs(self):
        """Test get audit logs endpoint"""
        result = self.make_request("GET", "/audit-logs", auth_required=True)
        if result is not None and isinstance(result, list):
            self.log_test("Get audit logs", True, f"Logs: {len(result)}")
            return True
        self.log_test("Get audit logs", False)
        return False

    # ========== CSV IMPORT TESTS ==========

    def test_get_csv_templates(self):
        """Test CSV template endpoints"""
        # Containers template
        result1 = self.make_request("GET", "/import/templates/containers", auth_required=True)
        # Inventory template
        result2 = self.make_request("GET", "/import/templates/inventory", auth_required=True)

        if result1 and result2:
            self.log_test("Get CSV templates", True, "Containers & inventory templates")
            return True

        self.log_test("Get CSV templates", False)
        return False

    def test_import_containers(self):
        """Test CSV containers import"""
        csv_content = """container_id,size,weight,access_frequency,arrival_time
TEST-CONT-001,Small,2.5,High,2026-03-29T10:00:00
TEST-CONT-002,Medium,5.0,Medium,2026-03-29T11:00:00"""

        files = {"file": ("containers.csv", csv_content, "text/csv")}

        try:
            headers = {}
            if self.access_token:
                headers["Authorization"] = f"Bearer {self.access_token}"

            resp = requests.post(
                f"{BASE_URL}/import/containers",
                files=files,
                headers=headers,
                timeout=TIMEOUT
            )

            if resp.status_code == 200:
                result = resp.json()
                if "success_count" in result:
                    self.log_test("Import containers CSV", True, f"Imported: {result.get('success_count')} containers")
                    return True

            self.log_test("Import containers CSV", False, f"Status: {resp.status_code}")
        except Exception as e:
            self.log_test("Import containers CSV", False, str(e))

        return False

    def test_import_inventory(self):
        """Test CSV inventory import"""
        csv_content = """sku,name,category,zone,bin_code,x,y,quantity,reorder_threshold,max_capacity,unit_cost,lead_time_days
TEST-SKU-001,Test Widget,Hardware,A,A-01,1,2,100,20,150,10.5,5
TEST-SKU-002,Test Gadget,Software,B,B-03,4,5,50,10,100,15.0,3"""

        files = {"file": ("inventory.csv", csv_content, "text/csv")}

        try:
            headers = {}
            if self.access_token:
                headers["Authorization"] = f"Bearer {self.access_token}"

            resp = requests.post(
                f"{BASE_URL}/import/inventory",
                files=files,
                headers=headers,
                timeout=TIMEOUT
            )

            if resp.status_code == 200:
                result = resp.json()
                if "success_count" in result:
                    self.log_test("Import inventory CSV", True, f"Imported: {result.get('success_count')} items")
                    return True

            self.log_test("Import inventory CSV", False, f"Status: {resp.status_code}")
        except Exception as e:
            self.log_test("Import inventory CSV", False, str(e))

        return False

    # ========== USER MANAGEMENT TESTS ==========

    def test_list_users(self):
        """Test list users endpoint"""
        result = self.make_request("GET", "/users", auth_required=True)
        if result is not None and isinstance(result, list):
            self.log_test("List users", True, f"Users: {len(result)}")
            return True
        self.log_test("List users", False)
        return False

    def test_create_user(self):
        """Test create user endpoint (Admin only)"""
        payload = {
            "email": f"newuser-{int(time.time())}@warehouse.com",
            "password": "TempPassword123!",
            "name": "New User",
            "role": "Manager"
        }
        result = self.make_request("POST", "/users", payload, expect_code=201, auth_required=True)
        if result:
            self.log_test("Create user", True, f"Created: {result.get('email')}")
            return True
        self.log_test("Create user", False)
        return False

    # ========== LAYOUT TESTS ==========

    def test_get_layout_strategies(self):
        """Test layout strategies endpoint"""
        result = self.make_request("GET", "/layout/strategies", auth_required=True)
        if result is not None and isinstance(result, list):
            self.log_test("Get layout strategies", True, f"Strategies: {len(result)}")
            return True
        self.log_test("Get layout strategies", False)
        return False

    def test_get_layout_state(self):
        """Test layout state endpoint"""
        result = self.make_request("GET", "/layout/state", auth_required=True)
        if result:
            self.log_test("Get layout state", True)
            return True
        self.log_test("Get layout state", False)
        return False

    # ========== RUN ALL TESTS ==========

    def run_all(self):
        """Run all tests in sequence"""
        print("\n" + "="*70)
        print("WAREHOUSE OPTIMIZATION SYSTEM - LIVE API TESTS")
        print("="*70 + "\n")

        # Check server
        print("Checking server status...")
        if not self.check_server():
            print("[FAIL] Server not running at http://localhost:8001")
            print("Start backend with: python -m uvicorn server:app --port 8001")
            return False

        print("[OK] Server is running\n")

        # Authentication tests
        print("1. AUTHENTICATION TESTS")
        print("-" * 70)
        self.test_register_user()
        self.test_login_user()
        self.test_refresh_token()

        # Protected endpoint tests
        print("\n2. PROTECTED ENDPOINTS TESTS")
        print("-" * 70)
        self.test_get_overview()
        self.test_get_inventory()
        self.test_get_orders()
        self.test_get_audit_logs()

        # CSV import tests
        print("\n3. CSV IMPORT TESTS")
        print("-" * 70)
        self.test_get_csv_templates()
        self.test_import_containers()
        self.test_import_inventory()

        # User management tests
        print("\n4. USER MANAGEMENT TESTS")
        print("-" * 70)
        self.test_list_users()
        self.test_create_user()

        # Layout tests
        print("\n5. LAYOUT & OPTIMIZATION TESTS")
        print("-" * 70)
        self.test_get_layout_strategies()
        self.test_get_layout_state()

        # Summary
        print("\n" + "="*70)
        passed = sum(1 for t in self.test_results if t["passed"])
        total = len(self.test_results)
        print(f"RESULTS: {passed}/{total} tests passed")
        print("="*70 + "\n")

        return passed == total


if __name__ == "__main__":
    tester = APITester()
    success = tester.run_all()
    exit(0 if success else 1)
