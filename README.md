# Warehouse Optimization System

A robust, full-stack application for managing warehouse operations, featuring machine learning for demand forecasting, real-time inventory tracking, and dynamic visualizations.

## Features Added & Fixed

- **Visual Dashboard**: A completely responsive and interactive dashboard displaying real-time KPIs (Total SKUs, Low Stock, Pick Efficiency).
- **ML Demand Forecasting**: Integrated forecasting analytics that fall back to a reliable baseline when historical data is limited.
- **Trend & Anomaly Detection**: Statistical analysis for tracking inventory trends over time.
- **Robust Role-based Access (RBAC)**: Secure frontend routing derived strictly from backend JWT claims, preventing unauthorized access.
- **RESTful API Architecture**: Built on FastAPI with correct router attachments, ensuring reliable connections between the React frontend and MongoDB backend.

## Tech Stack

### Backend
- **Python & FastAPI**: High-performance asynchronous API.
- **Motor**: Asynchronous MongoDB driver.
- **Pydantic**: Data validation and serialization.
- **Scikit-Learn**: Machine learning models for inventory forecasting (Random Forest, Linear Regression).
- **JWT Authentication**: Secure token-based user sessions.

### Frontend
- **React 19**: Modern component-based UI.
- **TailwindCSS**: Utility-first CSS framework for rapid styling.
- **Recharts**: Responsive charts and graphs for data visualization.
- **Lucide React**: Clean, consistent icon set.

## Getting Started

### Prerequisites
- Python 3.10+
- Node.js 18+ (with Yarn or npm)
- MongoDB instance (running locally or via Atlas)

### Backend Setup
1. Navigate to the `backend` directory.
2. Install dependencies: `pip install -r requirements.txt` (Includes `email-validator` and `passlib[bcrypt]`).
3. Set up your `.env` file with `MONGODB_URL`, `JWT_SECRET`, etc.
4. Run the server: `python -m uvicorn server:app --host 0.0.0.0 --port 8000 --reload`

### Frontend Setup
1. Navigate to the `frontend` directory.
2. Install dependencies: `npm install --legacy-peer-deps` or `yarn install`.
3. Set your API base URL in `.env` (maps to `http://localhost:8000/api`).
4. Start the application: `npm start` or `yarn start`.

## Recent Bug Fixes
- Resolved `warehouseApi.get is not a function` in the frontend API utilities.
- Fixed 404 Not Found errors on Forecasting and Analytics endpoints by correcting FastAPI router registrations.
- Gracefully handled `insufficient_data` ML responses in UI charts.
- Fixed permission checks (`PageGuard`) incorrectly using `allowed_pages` instead of role-based maps.

---
*Built to optimize and streamline modern warehouse telemetry.*
