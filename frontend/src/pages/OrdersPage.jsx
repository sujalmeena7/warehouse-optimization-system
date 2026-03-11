import { useEffect, useMemo, useState } from "react";
import { motion } from "framer-motion";
import { ArrowRight, ClipboardList } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { StatusBadge } from "@/components/common/StatusBadge";
import { warehouseApi } from "@/lib/api";

const statuses = ["queued", "picking", "packed", "shipped"];

const nextStatusMap = {
  queued: "picking",
  picking: "packed",
  packed: "shipped",
  shipped: "shipped",
};

export default function OrdersPage({ user }) {
  const [orders, setOrders] = useState([]);
  const [counts, setCounts] = useState({ queued: 0, picking: 0, packed: 0, shipped: 0 });

  const refreshOrders = async () => {
    const response = await warehouseApi.getOrders(user.role);
    setOrders(response.orders);
    setCounts(response.status_counts);
  };

  useEffect(() => {
    refreshOrders();
  }, [user.role]);

  const grouped = useMemo(
    () =>
      statuses.reduce((acc, status) => {
        acc[status] = orders.filter((order) => order.status === status);
        return acc;
      }, {}),
    [orders],
  );

  const progressOrder = async (order) => {
    const nextStatus = nextStatusMap[order.status];
    if (nextStatus === order.status) return;
    await warehouseApi.updateOrderStatus(user.role, order.id, nextStatus);
    refreshOrders();
  };

  return (
    <motion.div initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.25 }} className="space-y-6" data-testid="orders-page-root">
      <Card className="border-slate-200">
        <CardHeader>
          <CardTitle className="font-heading text-2xl" data-testid="orders-title-text">Order Flow Optimizer</CardTitle>
          <p className="text-sm text-slate-500" data-testid="orders-subtitle-text">Prioritize urgent orders and move them quickly across fulfillment stages.</p>
        </CardHeader>
        <CardContent>
          <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4" data-testid="orders-status-count-grid">
            {statuses.map((status) => (
              <div key={status} className="rounded-lg border border-slate-200 bg-slate-50 p-3" data-testid={`orders-count-${status}`}>
                <p className="text-xs uppercase tracking-wider text-slate-500">{status}</p>
                <p className="font-heading text-2xl text-slate-900">{counts[status]}</p>
              </div>
            ))}
          </div>
        </CardContent>
      </Card>

      <Tabs defaultValue="list" data-testid="orders-tabs-root">
        <TabsList data-testid="orders-tabs-list">
          <TabsTrigger value="list" data-testid="orders-tab-list">List View</TabsTrigger>
          <TabsTrigger value="board" data-testid="orders-tab-board">Kanban Board</TabsTrigger>
        </TabsList>

        <TabsContent value="list">
          <Card className="border-slate-200" data-testid="orders-list-card">
            <CardContent className="pt-6">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead data-testid="orders-header-reference">Reference</TableHead>
                    <TableHead data-testid="orders-header-priority">Priority</TableHead>
                    <TableHead data-testid="orders-header-status">Status</TableHead>
                    <TableHead data-testid="orders-header-score">Priority Score</TableHead>
                    <TableHead data-testid="orders-header-action">Action</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {orders.map((order) => (
                    <TableRow key={order.id} data-testid={`orders-row-${order.id}`}>
                      <TableCell data-testid={`orders-reference-${order.id}`}>{order.reference}</TableCell>
                      <TableCell data-testid={`orders-priority-${order.id}`} className="capitalize">{order.priority}</TableCell>
                      <TableCell><StatusBadge status={order.status} testId={`orders-status-${order.id}`} /></TableCell>
                      <TableCell data-testid={`orders-score-${order.id}`}>{order.priority_score}</TableCell>
                      <TableCell>
                        <Button variant="outline" onClick={() => progressOrder(order)} disabled={order.status === "shipped"} data-testid={`orders-progress-button-${order.id}`}>
                          <ArrowRight className="mr-2 h-4 w-4" />
                          Move to {nextStatusMap[order.status]}
                        </Button>
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="board">
          <div className="grid gap-4 xl:grid-cols-4" data-testid="orders-board-grid">
            {statuses.map((status) => (
              <Card key={status} className="border-slate-200" data-testid={`orders-board-column-${status}`}>
                <CardHeader>
                  <CardTitle className="text-base capitalize" data-testid={`orders-board-title-${status}`}>{status}</CardTitle>
                </CardHeader>
                <CardContent className="space-y-3">
                  {grouped[status].map((order) => (
                    <div key={order.id} className="rounded-lg border border-slate-200 p-3" data-testid={`orders-board-card-${order.id}`}>
                      <div className="mb-2 flex items-center justify-between">
                        <p className="text-sm font-semibold" data-testid={`orders-board-reference-${order.id}`}>{order.reference}</p>
                        <ClipboardList className="h-4 w-4 text-slate-400" />
                      </div>
                      <p className="text-xs text-slate-500" data-testid={`orders-board-destination-${order.id}`}>{order.destination}</p>
                      <div className="mt-3 flex items-center justify-between">
                        <StatusBadge status={order.priority} testId={`orders-board-priority-${order.id}`} />
                        <Button size="sm" variant="outline" onClick={() => progressOrder(order)} disabled={order.status === "shipped"} data-testid={`orders-board-progress-${order.id}`}>
                          Next
                        </Button>
                      </div>
                    </div>
                  ))}
                </CardContent>
              </Card>
            ))}
          </div>
        </TabsContent>
      </Tabs>
    </motion.div>
  );
}
