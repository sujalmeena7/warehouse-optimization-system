import { useEffect, useMemo, useState } from "react";
import { motion } from "framer-motion";
import { MapPin, Route } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { warehouseApi } from "@/lib/api";

const WarehouseGrid = ({ steps }) => {
  const indexMap = useMemo(() => {
    const map = {};
    steps.forEach((step) => {
      map[`${step.x}-${step.y}`] = step.step;
    });
    return map;
  }, [steps]);

  return (
    <div className="grid grid-cols-8 gap-1 rounded-lg border border-slate-200 p-3" data-testid="routes-warehouse-grid">
      {Array.from({ length: 64 }, (_, idx) => {
        const x = Math.floor(idx / 8) + 1;
        const y = (idx % 8) + 1;
        const stepNumber = indexMap[`${x}-${y}`];
        return (
          <div
            key={`${x}-${y}`}
            className={`flex h-8 items-center justify-center rounded text-xs font-semibold ${
              stepNumber ? "bg-orange-500 text-white" : "bg-slate-100 text-slate-500"
            }`}
            data-testid={`routes-grid-cell-${x}-${y}`}
          >
            {stepNumber || "·"}
          </div>
        );
      })}
    </div>
  );
};

export default function RoutesPage({ user }) {
  const [orders, setOrders] = useState([]);
  const [selectedOrderId, setSelectedOrderId] = useState("");
  const [plan, setPlan] = useState(null);

  useEffect(() => {
    warehouseApi.getOrders(user.role).then((response) => {
      const pendingOrders = response.orders.filter((order) => order.status !== "shipped");
      setOrders(pendingOrders);
      if (pendingOrders.length > 0) {
        setSelectedOrderId(pendingOrders[0].id);
      }
    });
  }, [user.role]);

  const optimize = async () => {
    if (!selectedOrderId) return;
    const routePlan = await warehouseApi.getRoutePlan(user.role, selectedOrderId);
    setPlan(routePlan);
  };

  return (
    <motion.div initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.25 }} className="space-y-6" data-testid="routes-page-root">
      <Card className="border-slate-200">
        <CardHeader>
          <CardTitle className="font-heading text-2xl" data-testid="routes-title-text">Picking Route Optimizer</CardTitle>
          <p className="text-sm text-slate-500" data-testid="routes-subtitle-text">Generate shortest travel paths using nearest-neighbor aisle logic.</p>
        </CardHeader>
        <CardContent className="grid gap-4 md:grid-cols-[1fr_auto]">
          <select
            value={selectedOrderId}
            onChange={(event) => setSelectedOrderId(event.target.value)}
            className="h-11 rounded-md border border-slate-300 px-3 text-sm"
            data-testid="routes-order-select"
          >
            {orders.map((order) => (
              <option key={order.id} value={order.id} data-testid={`routes-order-option-${order.id}`}>
                {order.reference} · {order.destination}
              </option>
            ))}
          </select>
          <Button onClick={optimize} data-testid="routes-generate-button">
            <Route className="mr-2 h-4 w-4" />
            Generate Route
          </Button>
        </CardContent>
      </Card>

      {plan && (
        <div className="grid gap-6 xl:grid-cols-[1fr_1.1fr]" data-testid="routes-plan-grid">
          <Card className="border-slate-200" data-testid="routes-summary-card">
            <CardHeader>
              <CardTitle className="text-xl" data-testid="routes-summary-title">Route Summary</CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="grid grid-cols-2 gap-3">
                <div className="rounded-lg border border-slate-200 bg-slate-50 p-3" data-testid="routes-total-distance-block">
                  <p className="text-xs uppercase text-slate-500">Total Distance</p>
                  <p className="font-heading text-2xl">{plan.total_distance}</p>
                </div>
                <div className="rounded-lg border border-slate-200 bg-slate-50 p-3" data-testid="routes-estimated-time-block">
                  <p className="text-xs uppercase text-slate-500">Estimated Minutes</p>
                  <p className="font-heading text-2xl">{plan.estimated_pick_minutes}</p>
                </div>
              </div>
              <p className="text-sm text-slate-600" data-testid="routes-algorithm-text">Algorithm: {plan.algorithm}</p>

              <div className="space-y-3" data-testid="routes-steps-list">
                {plan.steps.map((step) => (
                  <div key={step.step} className="flex items-center justify-between rounded-lg border border-slate-200 p-3" data-testid={`routes-step-${step.step}`}>
                    <div>
                      <p className="text-sm font-semibold" data-testid={`routes-step-label-${step.step}`}>Step {step.step} · {step.name}</p>
                      <p className="text-xs text-slate-500" data-testid={`routes-step-location-${step.step}`}>{step.zone} · {step.bin_code} · Qty {step.quantity}</p>
                    </div>
                    <div className="flex items-center gap-1 text-xs text-slate-600" data-testid={`routes-step-distance-${step.step}`}>
                      <MapPin className="h-3.5 w-3.5" />
                      +{step.distance_from_previous}
                    </div>
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>

          <Card className="border-slate-200" data-testid="routes-map-card">
            <CardHeader>
              <CardTitle className="text-xl" data-testid="routes-map-title">2D Warehouse Grid</CardTitle>
            </CardHeader>
            <CardContent>
              <WarehouseGrid steps={plan.steps} />
            </CardContent>
          </Card>
        </div>
      )}
    </motion.div>
  );
}
