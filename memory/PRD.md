# Product Requirements Document (PRD)

## Original Problem Statement
Build a warehouse optimization system for an internship project.

## User Confirmed Scope (Static Requirements)
- Combined system with all core modules
- Role-based usage: Admin + Manager + Staff
- Optimization stack:
  - Rule-based heuristics
  - Basic forecasting and reorder suggestions
  - Shortest-path style picking route optimization
- Core pages:
  - Dashboard
  - Inventory
  - Orders
  - Picking Routes
  - Analytics
  - Alerts
- Realistic seeded sample data included

## Architecture Decisions
- Frontend: React (multi-page SPA with React Router)
- Backend: FastAPI + MongoDB (Motor async client)
- Database access model:
  - Seeded collections: `inventory`, `orders`, `alerts`
  - API response-safe documents exclude Mongo `_id`
- Auth approach:
  - Demo role login (lightweight internship demo access)
  - Role permissions enforced in backend API
- Optimization logic:
  - Reorder point from demand + lead time heuristic
  - Priority scoring for order queueing
  - Nearest-neighbor (Manhattan distance) picking route sequencing

## User Personas
- **Admin**: full operational and editing control
- **Manager**: full operational and analytics access with editing rights
- **Staff**: daily execution on dashboard/inventory/orders/routes/alerts with restricted analytics and no inventory edits

## What Has Been Implemented
### 2026-03-11
- Implemented complete FastAPI warehouse domain APIs:
  - Demo login + role permissions
  - Dashboard overview KPIs + trends
  - Inventory list/filter/update
  - Orders list + status transition
  - Route optimization endpoint
  - Analytics trends endpoint
  - Alerts endpoint with severity filter
  - Seed/bootstrap endpoint and startup seeding
- Implemented complete React app flow and page routes:
  - Login page
  - Shared AppShell with role-aware navigation
  - Dashboard page with KPI cards/tables/charts
  - Inventory management page with search/filter and edit sheet
  - Orders page with list + kanban tabs and progression controls
  - Picking Routes page with route summary + 2D grid
  - Analytics page with three chart blocks
  - Alerts page with severity filters and alert cards
- Applied design system direction from generated guidelines:
  - Swiss-industrial visual language
  - Safety-orange accent + slate palette
  - Chivo + IBM Plex Sans + JetBrains Mono typography
  - Framer motion entrances and hover interactions
- Added comprehensive `data-testid` attributes across interactive/critical UI elements.
- Validation:
  - API curl checks successful
  - UI screenshot walkthroughs successful across key pages
  - Backend regression tests passed (`9 passed`)

## Prioritized Backlog
### P0 (Must Have Next)
- Add true authentication/session tokens instead of demo role login
- Add persistent audit trail for inventory and order status changes
- Add pagination and server-side sorting for large inventory/order datasets

### P1 (Should Have)
- CSV import flow for bulk inventory/order ingestion
- Configurable warehouse map editor (zone/bin coordinates)
- Alert acknowledgment workflow with assignee + resolution timestamps

### P2 (Nice to Have)
- Advanced forecasting model alternatives (seasonality aware)
- Multi-warehouse support and cross-site balancing suggestions
- Export-ready internship report views (PDF snapshots of KPIs/charts)

## Next Tasks List
1. Add secure auth and user management storage.
2. Build audit logging collection and timeline UI.
3. Implement pagination/query controls in inventory and orders APIs + UI.
4. Add CSV upload endpoints and frontend import wizard.
5. Add configurable zone/bin map editor for route accuracy tuning.
