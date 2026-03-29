#!/usr/bin/env python3
"""
Update all endpoints to use JWT dependency instead of role query parameter
"""

import re

# Read the server.py file
with open('server.py', 'r') as f:
    content = f.read()

# Define replacements: (old_pattern, new_pattern)
replacements = [
    # warehouse_overview
    (
        r'async def warehouse_overview\(role: str = Query\(\.\.\.\)\) -> WarehouseOverview:\n    require_permission\(role, "dashboard"\)',
        'async def warehouse_overview(user: Dict[str, str] = Depends(get_current_user)) -> WarehouseOverview:\n    require_permission(user["role"], "dashboard")'
    ),
    # get_inventory
    (
        r'async def get_inventory\(\n    role: str = Query\(\.\.\.\),',
        'async def get_inventory(\n    user: Dict[str, str] = Depends(get_current_user),'
    ),
    # Need to replace require_permission call too
    (
        r'require_permission\(role, "inventory"\)',
        'require_permission(user["role"], "inventory")'
    ),
    # create_inventory_item
    (
        r'async def create_inventory_item\(payload: InventoryCreate, role: str = Query\(\.\.\.\)\) -> InventoryView:',
        'async def create_inventory_item(payload: InventoryCreate, user: Dict[str, str] = Depends(get_current_user)) -> InventoryView:'
    ),
    # update_inventory_item
    (
        r'async def update_inventory_item\(item_id: str, payload: InventoryUpdate, role: str = Query\(\.\.\.\)\) -> InventoryView:',
        'async def update_inventory_item(item_id: str, payload: InventoryUpdate, user: Dict[str, str] = Depends(get_current_user)) -> InventoryView:'
    ),
    # get_orders
    (
        r'async def get_orders\(role: str = Query\(\.\.\.\)\) -> OrderListResponse:',
        'async def get_orders(user: Dict[str, str] = Depends(get_current_user)) -> OrderListResponse:'
    ),
    # update_order_status
    (
        r'async def update_order_status\(order_id: str, payload: OrderStatusUpdate, role: str = Query\(\.\.\.\)\) -> OrderView:',
        'async def update_order_status(order_id: str, payload: OrderStatusUpdate, user: Dict[str, str] = Depends(get_current_user)) -> OrderView:'
    ),
    # optimize_route
    (
        r'async def optimize_route\(order_id: str = Query\(\.\.\.\), role: str = Query\(\.\.\.\)\) -> RoutePlan:',
        'async def optimize_route(order_id: str = Query(...), user: Dict[str, str] = Depends(get_current_user)) -> RoutePlan:'
    ),
    # analytics_trends
    (
        r'async def analytics_trends\(role: str = Query\(\.\.\.\)\) -> AnalyticsResponse:',
        'async def analytics_trends(user: Dict[str, str] = Depends(get_current_user)) -> AnalyticsResponse:'
    ),
    # get_alerts
    (
        r'async def get_alerts\(\n    role: str = Query\(\.\.\.\),',
        'async def get_alerts(\n    user: Dict[str, str] = Depends(get_current_user),'
    ),
]

# Apply replacements
for old, new in replacements:
    content = re.sub(old, new, content)

# Replace all role variables with user["role"] in require_permission calls
content = re.sub(r'require_permission\(role,', 'require_permission(user["role"],', content)

# Write back
with open('server.py', 'w') as f:
    f.write(content)

print("Updated server.py with JWT dependency")
