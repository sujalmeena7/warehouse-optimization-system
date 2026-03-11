import { Badge } from "@/components/ui/badge";

const badgeStyleByStatus = {
  healthy: "bg-emerald-100 text-emerald-700",
  low: "bg-amber-100 text-amber-800",
  critical: "bg-red-100 text-red-700",
  queued: "bg-slate-200 text-slate-700",
  picking: "bg-blue-100 text-blue-700",
  packed: "bg-purple-100 text-purple-700",
  shipped: "bg-emerald-100 text-emerald-700",
  info: "bg-slate-100 text-slate-700",
  warning: "bg-amber-100 text-amber-800",
};

export const StatusBadge = ({ status, testId }) => {
  const key = String(status || "info").toLowerCase();
  const className = badgeStyleByStatus[key] || "bg-slate-100 text-slate-700";

  return (
    <Badge className={`rounded-md border-transparent capitalize ${className}`} data-testid={testId}>
      {status}
    </Badge>
  );
};
