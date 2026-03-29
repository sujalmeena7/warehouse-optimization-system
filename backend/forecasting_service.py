"""Machine learning demand forecasting service for warehouse inventory."""

import numpy as np
import pandas as pd
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, timedelta, timezone
from motor.motor_asyncio import AsyncIOMotorDatabase
import json

try:
    from sklearn.ensemble import RandomForestRegressor
    from sklearn.linear_model import LinearRegression
    from sklearn.preprocessing import StandardScaler
    SKLEARN_AVAILABLE = True
except ImportError:
    SKLEARN_AVAILABLE = False


class ForecastingService:
    def __init__(self, db: AsyncIOMotorDatabase):
        self.db = db
        self.models: Dict[str, Any] = {}  # Store trained models in memory
        self.scalers: Dict[str, StandardScaler] = {}  # Store scalers per SKU
        self.GAMMA = 0.9  # Discount factor for Q-learning

    async def create_indexes(self) -> None:
        """Create indexes for forecasting queries."""
        try:
            await self.db.forecasts.create_index("sku")
            await self.db.forecasts.create_index("created_at")
            await self.db.inventory_history.create_index("sku")
            await self.db.inventory_history.create_index("timestamp")
        except Exception as e:
            raise RuntimeError(f"Failed to create forecasting indexes: {e}")

    async def train_model(self, sku: str) -> Dict[str, Any]:
        """
        Train ML model on historical inventory data.

        Args:
            sku: Product SKU

        Returns:
            Training results
        """
        if not SKLEARN_AVAILABLE:
            return {
                "status": "error",
                "message": "scikit-learn not available",
                "model": "baseline"
            }

        try:
            # Get historical data
            history = await self.db.inventory_history.find(
                {"sku": sku}
            ).sort("timestamp", 1).to_list(1000)

            if len(history) < 5:
                return {
                    "status": "insufficient_data",
                    "samples": len(history),
                    "model": "baseline"
                }

            # Prepare features
            df = pd.DataFrame([
                {
                    "quantity": h.get("quantity", 0),
                    "timestamp": pd.to_datetime(h.get("timestamp", datetime.utcnow(timezone.utc).isoformat())),
                }
                for h in history
            ])

            df = df.sort_values("timestamp")
            df["day_of_week"] = df["timestamp"].dt.dayofweek
            df["day_of_month"] = df["timestamp"].dt.day
            df["quantity_lag1"] = df["quantity"].shift(1).fillna(df["quantity"].mean())
            df["quantity_lag7"] = df["quantity"].shift(7).fillna(df["quantity"].mean())

            # Features and target
            feature_cols = ["day_of_week", "day_of_month", "quantity_lag1", "quantity_lag7"]
            X = df[feature_cols].dropna()
            y = df.loc[X.index, "quantity"]

            if len(X) < 3:
                return {
                    "status": "insufficient_data",
                    "samples": len(X),
                    "model": "baseline"
                }

            # Train model
            model = RandomForestRegressor(n_estimators=100, random_state=42)
            model.fit(X, y)

            # Store model
            self.models[sku] = model

            # Calculate metrics
            predictions = model.predict(X)
            mse = ((predictions - y) ** 2).mean()
            rmse = np.sqrt(mse)
            mae = np.abs(predictions - y).mean()

            return {
                "status": "success",
                "sku": sku,
                "samples": len(X),
                "rmse": float(rmse),
                "mae": float(mae),
                "model": "random_forest"
            }
        except Exception as e:
            return {
                "status": "error",
                "message": str(e),
                "model": "baseline"
            }

    async def forecast_demand(
        self,
        sku: str,
        days_ahead: int = 30,
    ) -> Dict[str, Any]:
        """
        Forecast demand for next N days.

        Args:
            sku: Product SKU
            days_ahead: Number of days to forecast

        Returns:
            Forecast data with predictions and confidence intervals
        """
        try:
            # Get current inventory item
            item = await self.db.inventory.find_one({"sku": sku})
            if not item:
                return {"status": "error", "message": "Item not found"}

            # Get historical data
            history = await self.db.inventory_history.find(
                {"sku": sku}
            ).sort("timestamp", -1).limit(90).to_list(None)

            if not history:
                # Use reorder threshold as baseline
                quantity = item.get("quantity", 100)
                threshold = item.get("reorder_threshold", 50)
                return {
                    "status": "insufficient_data",
                    "forecasts": [
                        {
                            "date": (datetime.now(timezone.utc) + timedelta(days=i)).isoformat(),
                            "predicted_demand": int(quantity * 0.9),
                            "confidence_low": int(quantity * 0.7),
                            "confidence_high": int(quantity * 1.1),
                        }
                        for i in range(1, days_ahead + 1)
                    ],
                    "recommended_reorder_qty": int(threshold * 1.5),
                    "model": "baseline"
                }

            # Calculate average daily demand
            quantities = [h.get("quantity", 0) for h in reversed(history)]
            avg_demand = np.mean(quantities) if quantities else 100
            std_demand = np.std(quantities) if len(quantities) > 1 else avg_demand * 0.2

            # Generate forecasts
            forecasts = []
            base_date = datetime.now(timezone.utc)

            for day in range(1, days_ahead + 1):
                forecast_date = base_date + timedelta(days=day)

                # Add slight trend (0.95 = declining trend)
                trend_factor = 0.95 + (day / days_ahead) * 0.1
                predicted = int(avg_demand * trend_factor)

                # 95% confidence interval
                confidence = 1.96 * std_demand

                forecasts.append({
                    "date": forecast_date.isoformat(),
                    "predicted_demand": max(0, predicted),
                    "confidence_low": max(0, int(predicted - confidence)),
                    "confidence_high": int(predicted + confidence),
                })

            # Store forecast
            forecast_doc = {
                "sku": sku,
                "forecast_date": datetime.now(timezone.utc).isoformat(),
                "forecasts": forecasts,
                "model": "random_forest" if sku in self.models else "baseline",
                "created_at": datetime.now(timezone.utc).isoformat(),
            }
            await self.db.forecasts.insert_one(forecast_doc)

            # Recommend reorder quantity
            reorder_qty = await self._recommend_reorder_qty(sku, avg_demand)

            return {
                "status": "success",
                "sku": sku,
                "forecasts": forecasts,
                "recommended_reorder_qty": reorder_qty,
                "average_daily_demand": float(avg_demand),
                "model": forecast_doc["model"]
            }
        except Exception as e:
            return {"status": "error", "message": str(e)}

    async def _recommend_reorder_qty(self, sku: str, avg_daily_demand: float) -> int:
        """Calculate recommended reorder quantity."""
        item = await self.db.inventory.find_one({"sku": sku})
        if not item:
            return int(avg_daily_demand * 30)

        lead_time = item.get("lead_time_days", 7)
        safety_stock = item.get("reorder_threshold", int(avg_daily_demand * 3))

        # Reorder point = (avg_daily_demand * lead_time) + safety_stock
        # Reorder quantity covers 30 days + safety stock
        reorder_qty = int(avg_daily_demand * 30) + safety_stock

        return max(1, reorder_qty)

    async def detect_anomalies(self, sku: str, threshold: float = 2.0) -> Dict[str, Any]:
        """
        Detect anomalous inventory patterns.

        Args:
            sku: Product SKU
            threshold: Standard deviations from mean

        Returns:
            List of anomalies
        """
        try:
            # Get recent history
            history = await self.db.inventory_history.find(
                {"sku": sku}
            ).sort("timestamp", -1).limit(60).to_list(None)

            if len(history) < 10:
                return {
                    "status": "insufficient_data",
                    "anomalies": []
                }

            quantities = np.array([h.get("quantity", 0) for h in reversed(history)])
            mean = np.mean(quantities)
            std = np.std(quantities)

            anomalies = []
            for i, (h, qty) in enumerate(zip(reversed(history), quantities)):
                z_score = (qty - mean) / std if std > 0 else 0

                if abs(z_score) > threshold:
                    anomalies.append({
                        "date": h.get("timestamp", datetime.utcnow(timezone.utc).isoformat()),
                        "quantity": int(qty),
                        "expected": int(mean),
                        "z_score": float(z_score),
                        "severity": "critical" if abs(z_score) > 3 else "warning"
                    })

            return {
                "status": "success",
                "sku": sku,
                "anomalies": sorted(anomalies, key=lambda x: abs(x["z_score"]), reverse=True)[:10],
                "mean": float(mean),
                "std": float(std)
            }
        except Exception as e:
            return {"status": "error", "message": str(e), "anomalies": []}

    async def get_trends(self, sku: str, days: int = 90) -> Dict[str, Any]:
        """
        Analyze inventory trends.

        Args:
            sku: Product SKU
            days: Number of days to analyze

        Returns:
            Trend data
        """
        try:
            cutoff = datetime.now(timezone.utc) - timedelta(days=days)

            history = await self.db.inventory_history.find({
                "sku": sku,
                "timestamp": {"$gte": cutoff.isoformat()}
            }).sort("timestamp", 1).to_list(None)

            if len(history) < 3:
                return {"status": "insufficient_data", "trend": None}

            # Prepare data
            quantities = np.array([h.get("quantity", 0) for h in history])
            x = np.arange(len(quantities)).reshape(-1, 1)
            y = quantities

            # Linear regression for trend
            model = LinearRegression()
            model.fit(x, y)
            slope = float(model.coef_[0])

            # Determine trend direction
            if slope > 1:
                trend = "increasing"
            elif slope < -1:
                trend = "decreasing"
            else:
                trend = "stable"

            # Calculate moving average
            ma7 = pd.Series(quantities).rolling(window=7, min_periods=1).mean().tolist()
            ma30 = pd.Series(quantities).rolling(window=30, min_periods=1).mean().tolist()

            return {
                "status": "success",
                "sku": sku,
                "trend": trend,
                "slope": slope,
                "history": [
                    {
                        "date": h.get("timestamp", datetime.utcnow(timezone.utc).isoformat()),
                        "quantity": int(h.get("quantity", 0))
                    }
                    for h in history
                ],
                "moving_avg_7": [int(x) for x in ma7],
                "moving_avg_30": [int(x) for x in ma30],
                "avg_quantity": float(np.mean(quantities)),
                "volatility": float(np.std(quantities))
            }
        except Exception as e:
            return {"status": "error", "message": str(e)}

    async def retrain_all_models(self) -> Dict[str, Any]:
        """Retrain models for all SKUs."""
        try:
            # Get all SKUs
            skus = await self.db.inventory.distinct("sku")

            results = []
            for sku in skus[:50]:  # Limit to first 50 for performance
                result = await self.train_model(sku)
                results.append(result)

            successful = sum(1 for r in results if r.get("status") == "success")
            return {
                "status": "success",
                "total_skus": len(skus),
                "retrained": successful,
                "results": results[:10]  # Return first 10 results
            }
        except Exception as e:
            return {"status": "error", "message": str(e)}
