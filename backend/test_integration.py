"""
Integration tests for JWT auth, audit logging, and CSV import
Run with: pytest test_integration.py -v
"""

import pytest
import json
from datetime import datetime
from auth import create_access_token, verify_token, hash_password, verify_password
from csv_import import parse_containers_csv, parse_inventory_csv, get_containers_csv_template, get_inventory_csv_template
from io import StringIO


class TestJWTAuthentication:
    """Test JWT token generation and verification"""

    def test_create_access_token(self):
        """Test creating access token"""
        user_data = {
            "user_id": "test-123",
            "email": "test@example.com",
            "role": "Admin"
        }
        token = create_access_token(user_data)
        assert isinstance(token, str)
        assert len(token) > 0
        print(f"[OK] Token created: {token[:40]}...")

    def test_verify_token_valid(self):
        """Test verifying valid token"""
        user_data = {
            "user_id": "test-123",
            "email": "test@example.com",
            "role": "Admin"
        }
        token = create_access_token(user_data)
        payload = verify_token(token)

        assert payload is not None
        assert payload["user_id"] == "test-123"
        assert payload["email"] == "test@example.com"
        assert payload["role"] == "Admin"
        print(f"[OK] Token verified: {payload}")

    def test_verify_token_invalid(self):
        """Test verifying invalid token"""
        invalid_token = "invalid.token.here"
        payload = verify_token(invalid_token)
        assert payload is None
        print("[OK] Invalid token rejected")

    def test_password_hashing(self):
        """Test password hashing and verification"""
        password = "SecurePassword123!"
        hashed = hash_password(password)

        assert hashed != password
        assert verify_password(password, hashed)
        assert not verify_password("WrongPassword", hashed)
        print(f"[OK] Password hashing works: {hashed[:20]}...")

    def test_token_payload_extraction(self):
        """Test extracting user data from token"""
        user_data = {
            "user_id": "user-456",
            "email": "manager@warehouse.com",
            "role": "Manager"
        }
        token = create_access_token(user_data)
        payload = verify_token(token)

        assert payload["role"] == "Manager"
        assert payload["email"] == "manager@warehouse.com"
        print(f"[OK] Payload extraction works: role={payload['role']}")


class TestCSVImport:
    """Test CSV parsing and validation"""

    def test_containers_csv_template(self):
        """Test containers CSV template generation"""
        template = get_containers_csv_template()

        assert "container_id" in template
        assert "size" in template
        assert "weight" in template
        assert "access_frequency" in template
        print(f"[OK] Containers template generated:\n{template[:100]}...")

    def test_inventory_csv_template(self):
        """Test inventory CSV template generation"""
        template = get_inventory_csv_template()

        assert "sku" in template
        assert "name" in template
        assert "category" in template
        assert "zone" in template
        print(f"[OK] Inventory template generated:\n{template[:100]}...")

    def test_parse_valid_containers_csv(self):
        """Test parsing valid containers CSV"""
        csv_content = """container_id,size,weight,access_frequency,arrival_time
CONT001,Small,2.5,High,2026-03-29T10:00:00
CONT002,Medium,5.0,Medium,2026-03-29T11:00:00
CONT003,Large,10.0,Low,2026-03-29T12:00:00"""

        file_obj = StringIO(csv_content)
        result = parse_containers_csv(file_obj.getvalue())

        assert result.success_count == 3
        assert result.error_count == 0
        assert len(result.errors) == 0
        assert len(result.containers) == 3
        print(f"[OK] Containers CSV parsed: {result.success_count} valid rows")

    def test_parse_invalid_containers_csv(self):
        """Test parsing invalid containers CSV"""
        csv_content = """container_id,size,weight,access_frequency
CONT001,InvalidSize,2.5,High
CONT002,Small,invalid_weight,Medium
CONT003,Large,10.0"""

        result = parse_containers_csv(csv_content)

        assert result.error_count > 0
        assert len(result.errors) > 0
        print(f"[OK] Invalid containers detected: {result.error_count} errors")
        for error in result.errors[:2]:
            print(f"  - Row {error.get('row')}: {error.get('error')}")

    def test_parse_valid_inventory_csv(self):
        """Test parsing valid inventory CSV"""
        csv_content = """sku,name,category,zone,bin_code,x,y,quantity,reorder_threshold,max_capacity,unit_cost,lead_time_days
SKU001,Widget A,Hardware,A,A-01,1,2,100,20,150,10.5,5
SKU002,Widget B,Hardware,B,B-03,4,5,50,10,100,15.0,3"""

        result = parse_inventory_csv(csv_content)

        assert result.success_count == 2
        assert result.error_count == 0
        print(f"[OK] Inventory CSV parsed: {result.success_count} valid rows")

    def test_parse_invalid_inventory_csv(self):
        """Test parsing invalid inventory CSV with invalid data"""
        csv_content = """sku,name,category,zone,bin_code,x,y,quantity,reorder_threshold,max_capacity,unit_cost,lead_time_days
SKU001,Widget A,Hardware,A,A-01,invalid_x,2,100,20,150,10.5,5
SKU002,Widget B,Hardware,B,B-03,4,not_integer,50,10,100,15.0,3"""

        result = parse_inventory_csv(csv_content)

        assert result.error_count > 0
        print(f"[OK] Invalid inventory detected: {result.error_count} errors")


class TestAccessControl:
    """Test role-based access control via JWT"""

    def test_admin_token(self):
        """Test admin role in token"""
        admin_data = {
            "user_id": "admin-1",
            "email": "admin@warehouse.com",
            "role": "Admin"
        }
        token = create_access_token(admin_data)
        payload = verify_token(token)

        assert payload["role"] == "Admin"
        print(f"[OK] Admin token created and verified")

    def test_manager_token(self):
        """Test manager role in token"""
        manager_data = {
            "user_id": "mgr-1",
            "email": "manager@warehouse.com",
            "role": "Manager"
        }
        token = create_access_token(manager_data)
        payload = verify_token(token)

        assert payload["role"] == "Manager"
        print(f"[OK] Manager token created and verified")

    def test_staff_token(self):
        """Test staff role in token"""
        staff_data = {
            "user_id": "staff-1",
            "email": "staff@warehouse.com",
            "role": "Staff"
        }
        token = create_access_token(staff_data)
        payload = verify_token(token)

        assert payload["role"] == "Staff"
        print(f"[OK] Staff token created and verified")

    def test_multiple_users_different_tokens(self):
        """Test that different users get different tokens"""
        user1 = {
            "user_id": "user-1",
            "email": "user1@warehouse.com",
            "role": "Manager"
        }
        user2 = {
            "user_id": "user-2",
            "email": "user2@warehouse.com",
            "role": "Staff"
        }

        token1 = create_access_token(user1)
        token2 = create_access_token(user2)

        payload1 = verify_token(token1)
        payload2 = verify_token(token2)

        assert token1 != token2
        assert payload1["user_id"] != payload2["user_id"]
        assert payload1["role"] != payload2["role"]
        print(f"[OK] Different users have different tokens")


class TestAuditLogging:
    """Test audit logging structure"""

    def test_audit_log_schema(self):
        """Test that audit log schema is valid"""
        from audit_logger import create_audit_record

        audit_record = create_audit_record(
            action="CREATE",
            user_id="user-123",
            user_email="user@example.com",
            entity_type="inventory",
            entity_id="sku-001",
            entity_details="Widget A",
            old_value=None,
            new_value={"sku": "SKU001", "name": "Widget A", "quantity": 100},
            ip_address="127.0.0.1"
        )

        assert audit_record["id"] is not None
        assert audit_record["action"] == "CREATE"
        assert audit_record["user_id"] == "user-123"
        assert audit_record["entity_type"] == "inventory"
        assert audit_record["timestamp"] is not None
        print(f"[OK] Audit record created: {audit_record['id']}")

    def test_immutable_audit_log(self):
        """Test audit log immutability concept"""
        from audit_logger import create_audit_record

        log1 = create_audit_record(
            action="UPDATE",
            user_id="user-1",
            user_email="user1@example.com",
            entity_type="order",
            entity_id="order-1",
            entity_details="Order #ORD001",
            old_value={"status": "queued"},
            new_value={"status": "picking"},
            ip_address="192.168.1.100"
        )

        log2 = create_audit_record(
            action="UPDATE",
            user_id="user-2",
            user_email="user2@example.com",
            entity_type="order",
            entity_id="order-1",
            entity_details="Order #ORD001",
            old_value={"status": "picking"},
            new_value={"status": "packed"},
            ip_address="192.168.1.101"
        )

        assert log1["id"] != log2["id"]
        assert log1["user_id"] != log2["user_id"]
        assert log1["timestamp"] is not None
        assert log2["timestamp"] is not None
        print(f"[OK] Immutable audit logs created: {log1['id']}, {log2['id']}")


if __name__ == "__main__":
    # Run tests
    print("\n" + "="*60)
    print("WAREHOUSE OPTIMIZATION SYSTEM - INTEGRATION TESTS")
    print("="*60 + "\n")

    # Test JWT
    print("Testing JWT Authentication...\n")
    jwt_tests = TestJWTAuthentication()
    jwt_tests.test_create_access_token()
    jwt_tests.test_verify_token_valid()
    jwt_tests.test_verify_token_invalid()
    jwt_tests.test_password_hashing()
    jwt_tests.test_token_payload_extraction()

    # Test CSV
    print("\nTesting CSV Import...\n")
    csv_tests = TestCSVImport()
    csv_tests.test_containers_csv_template()
    csv_tests.test_inventory_csv_template()
    csv_tests.test_parse_valid_containers_csv()
    csv_tests.test_parse_invalid_containers_csv()
    csv_tests.test_parse_valid_inventory_csv()
    csv_tests.test_parse_invalid_inventory_csv()

    # Test Access Control
    print("\nTesting Role-Based Access Control...\n")
    access_tests = TestAccessControl()
    access_tests.test_admin_token()
    access_tests.test_manager_token()
    access_tests.test_staff_token()
    access_tests.test_multiple_users_different_tokens()

    # Test Audit
    print("\nTesting Audit Logging...\n")
    audit_tests = TestAuditLogging()
    audit_tests.test_audit_log_schema()
    audit_tests.test_immutable_audit_log()

    print("\n" + "="*60)
    print("[OK] ALL TESTS PASSED")
    print("="*60 + "\n")
