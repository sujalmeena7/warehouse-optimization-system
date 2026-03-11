import { useEffect, useState } from "react";
import { motion } from "framer-motion";
import { BellRing } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { StatusBadge } from "@/components/common/StatusBadge";
import { warehouseApi } from "@/lib/api";

export default function AlertsPage({ user }) {
  const [alerts, setAlerts] = useState([]);
  const [severity, setSeverity] = useState("all");

  const loadAlerts = async (currentSeverity) => {
    const data = await warehouseApi.getAlerts(user.role, currentSeverity);
    setAlerts(data);
  };

  useEffect(() => {
    loadAlerts(severity);
  }, [user.role, severity]);

  return (
    <motion.div initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.25 }} className="space-y-6" data-testid="alerts-page-root">
      <Card className="border-slate-200">
        <CardHeader>
          <CardTitle className="font-heading text-2xl" data-testid="alerts-title-text">Operations Alert Center</CardTitle>
          <p className="text-sm text-slate-500" data-testid="alerts-subtitle-text">Live warnings from inventory, route health, and SLA exceptions.</p>
        </CardHeader>
        <CardContent>
          <div className="flex flex-wrap gap-2" data-testid="alerts-severity-filters">
            {["all", "critical", "warning", "info"].map((key) => (
              <Button key={key} variant={severity === key ? "default" : "outline"} onClick={() => setSeverity(key)} data-testid={`alerts-filter-${key}`}>
                {key}
              </Button>
            ))}
          </div>
        </CardContent>
      </Card>

      <div className="space-y-3" data-testid="alerts-list-container">
        {alerts.map((alert) => (
          <Card key={alert.id} className="border-slate-200" data-testid={`alert-card-${alert.id}`}>
            <CardContent className="flex flex-col gap-3 p-4 md:flex-row md:items-center md:justify-between">
              <div className="flex items-start gap-3">
                <BellRing className="mt-1 h-4 w-4 text-orange-500" />
                <div>
                  <p className="text-sm font-semibold" data-testid={`alert-message-${alert.id}`}>{alert.message}</p>
                  <p className="text-xs text-slate-500" data-testid={`alert-meta-${alert.id}`}>{alert.type} · {alert.source}</p>
                </div>
              </div>
              <StatusBadge status={alert.severity} testId={`alert-severity-${alert.id}`} />
            </CardContent>
          </Card>
        ))}
      </div>
    </motion.div>
  );
}
