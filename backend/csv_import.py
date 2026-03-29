"""CSV import utilities for bulk loading containers and inventory."""
import csv
from io import StringIO
from typing import List, Dict, Tuple, Optional
from pydantic import ValidationError
import uuid


class CSVImportError(Exception):
    """Base exception for CSV import errors."""

    pass


class ContainerImportResult:
    def __init__(self):
        self.success_count = 0
        self.error_count = 0
        self.errors: List[Dict[str, str]] = []
        self.containers: List[Dict] = []

    def add_error(self, row_num: int, error: str):
        self.error_count += 1
        self.errors.append({"row": row_num, "error": error})

    def add_container(self, container: Dict):
        self.success_count += 1
        self.containers.append(container)


class InventoryImportResult:
    def __init__(self):
        self.success_count = 0
        self.error_count = 0
        self.errors: List[Dict[str, str]] = []
        self.items: List[Dict] = []

    def add_error(self, row_num: int, error: str):
        self.error_count += 1
        self.errors.append({"row": row_num, "error": error})

    def add_item(self, item: Dict):
        self.success_count += 1
        self.items.append(item)


def parse_containers_csv(csv_content: str) -> ContainerImportResult:
    """
    Parse and validate containers CSV.

    Expected columns: container_id, size, weight, access_frequency, [arrival_time]
    """
    result = ContainerImportResult()

    try:
        reader = csv.DictReader(StringIO(csv_content))
        if not reader.fieldnames:
            raise CSVImportError("CSV file is empty")

        required_fields = {"container_id", "size", "weight", "access_frequency"}
        missing_fields = required_fields - set(reader.fieldnames)
        if missing_fields:
            raise CSVImportError(f"Missing required columns: {', '.join(missing_fields)}")

        seen_ids = set()
        for row_num, row in enumerate(reader, start=2):  # Start at 2 because row 1 is headers
            try:
                # Validate required fields
                container_id = row.get("container_id", "").strip()
                size = row.get("size", "").strip()
                weight_str = row.get("weight", "").strip()
                access_frequency = row.get("access_frequency", "").strip()
                arrival_time = row.get("arrival_time", "").strip() if "arrival_time" in row else None

                # Check for empty values
                if not all([container_id, size, weight_str, access_frequency]):
                    result.add_error(row_num, "Missing required fields")
                    continue

                # Validate size
                if size not in {"Small", "Medium", "Large"}:
                    result.add_error(row_num, f"Invalid size '{size}'. Must be Small, Medium, or Large")
                    continue

                # Validate weight
                try:
                    weight = float(weight_str)
                    if weight <= 0:
                        raise ValueError("Weight must be positive")
                except ValueError as e:
                    result.add_error(row_num, f"Invalid weight '{weight_str}': {str(e)}")
                    continue

                # Validate access frequency
                if access_frequency not in {"High", "Medium", "Low"}:
                    result.add_error(row_num, f"Invalid access_frequency '{access_frequency}'. Must be High, Medium, or Low")
                    continue

                # Check for duplicates
                if container_id in seen_ids:
                    result.add_error(row_num, f"Duplicate container_id '{container_id}'")
                    continue

                seen_ids.add(container_id)

                # Create container object
                container = {
                    "container_id": container_id,
                    "size": size,
                    "weight": weight,
                    "access_frequency": access_frequency,
                    "arrival_time": arrival_time,
                }

                result.add_container(container)

            except Exception as e:
                result.add_error(row_num, str(e))

    except CSVImportError as e:
        result.errors.append({"row": 1, "error": str(e)})
    except Exception as e:
        result.errors.append({"row": 1, "error": f"CSV parsing error: {str(e)}"})

    return result


def parse_inventory_csv(csv_content: str) -> InventoryImportResult:
    """
    Parse and validate inventory CSV.

    Expected columns: sku, name, category, zone, bin_code, x, y, quantity,
                      reorder_threshold, max_capacity, unit_cost, lead_time_days
    """
    result = InventoryImportResult()

    try:
        reader = csv.DictReader(StringIO(csv_content))
        if not reader.fieldnames:
            raise CSVImportError("CSV file is empty")

        required_fields = {
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
        }
        missing_fields = required_fields - set(reader.fieldnames)
        if missing_fields:
            raise CSVImportError(f"Missing required columns: {', '.join(missing_fields)}")

        seen_skus = set()
        for row_num, row in enumerate(reader, start=2):  # Start at 2 because row 1 is headers
            try:
                # Extract and validate fields
                sku = row.get("sku", "").strip()
                name = row.get("name", "").strip()
                category = row.get("category", "").strip()
                zone = row.get("zone", "").strip()
                bin_code = row.get("bin_code", "").strip()

                # Check required text fields
                if not all([sku, name, category, zone, bin_code]):
                    result.add_error(row_num, "Missing required text fields")
                    continue

                # Check for duplicate SKU
                if sku in seen_skus:
                    result.add_error(row_num, f"Duplicate SKU '{sku}'")
                    continue

                seen_skus.add(sku)

                # Validate numeric fields
                try:
                    x = int(row.get("x", "").strip())
                    y = int(row.get("y", "").strip())
                    quantity = int(row.get("quantity", "").strip())
                    reorder_threshold = int(row.get("reorder_threshold", "").strip())
                    max_capacity = int(row.get("max_capacity", "").strip())
                    unit_cost = float(row.get("unit_cost", "").strip())
                    lead_time_days = int(row.get("lead_time_days", "").strip())

                    # Validate ranges
                    if x < 0 or y < 0:
                        raise ValueError("Grid coordinates (x, y) cannot be negative")
                    if quantity < 0:
                        raise ValueError("Quantity cannot be negative")
                    if reorder_threshold < 0 or max_capacity <= 0:
                        raise ValueError("Reorder threshold and max capacity must be non-negative and positive")
                    if quantity > max_capacity:
                        raise ValueError("Quantity cannot exceed max_capacity")
                    if unit_cost < 0 or lead_time_days < 0:
                        raise ValueError("Unit cost and lead time cannot be negative")

                except (ValueError, TypeError) as e:
                    result.add_error(row_num, f"Invalid numeric field: {str(e)}")
                    continue

                # Create inventory item
                item = {
                    "id": str(uuid.uuid4()),
                    "sku": sku,
                    "name": name,
                    "category": category,
                    "zone": zone,
                    "bin_code": bin_code,
                    "x": x,
                    "y": y,
                    "quantity": quantity,
                    "reorder_threshold": reorder_threshold,
                    "max_capacity": max_capacity,
                    "unit_cost": unit_cost,
                    "lead_time_days": lead_time_days,
                    "daily_demand": [1] * 7,  # Default 7-day demand pattern
                    "last_restocked": "2026-01-01T00:00:00+00:00",
                }

                result.add_item(item)

            except Exception as e:
                result.add_error(row_num, str(e))

    except CSVImportError as e:
        result.errors.append({"row": 1, "error": str(e)})
    except Exception as e:
        result.errors.append({"row": 1, "error": f"CSV parsing error: {str(e)}"})

    return result


def get_containers_csv_template() -> str:
    """Return a CSV template for containers import."""
    return """container_id,size,weight,access_frequency,arrival_time
CONT-001,Small,2.5,High,2026-03-29T10:00:00
CONT-002,Medium,5.0,Medium,2026-03-29T11:00:00
CONT-003,Large,15.0,Low,2026-03-29T12:00:00"""


def get_inventory_csv_template() -> str:
    """Return a CSV template for inventory import."""
    return """sku,name,category,zone,bin_code,x,y,quantity,reorder_threshold,max_capacity,unit_cost,lead_time_days
SKU-001,Widget A,Electronics,A,A-01,0,0,100,20,150,25.50,3
SKU-002,Widget B,Electronics,B,B-05,2,3,50,10,75,15.75,2
SKU-003,Gadget X,Hardware,C,C-10,5,1,200,50,300,5.00,5"""
