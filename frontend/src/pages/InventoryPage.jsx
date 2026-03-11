import { useEffect, useMemo, useState } from "react";
import { motion } from "framer-motion";
import { Save, Search } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Sheet, SheetContent, SheetHeader, SheetTitle } from "@/components/ui/sheet";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { StatusBadge } from "@/components/common/StatusBadge";
import { warehouseApi } from "@/lib/api";
import { canEditInventory } from "@/lib/permissions";

export default function InventoryPage({ user }) {
  const [items, setItems] = useState([]);
  const [search, setSearch] = useState("");
  const [statusFilter, setStatusFilter] = useState("all");
  const [editingItem, setEditingItem] = useState(null);
  const [quantity, setQuantity] = useState(0);
  const [threshold, setThreshold] = useState(0);

  const editable = useMemo(() => canEditInventory(user), [user]);

  const loadInventory = () => {
    warehouseApi
      .getInventory(user.role, {
        search: search || undefined,
        status: statusFilter === "all" ? undefined : statusFilter,
      })
      .then(setItems);
  };

  useEffect(() => {
    loadInventory();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [user.role, statusFilter]);

  const openEditor = (item) => {
    setEditingItem(item);
    setQuantity(item.quantity);
    setThreshold(item.reorder_threshold);
  };

  const saveInventory = async () => {
    if (!editingItem) return;
    await warehouseApi.updateInventory(user.role, editingItem.id, {
      quantity: Number(quantity),
      reorder_threshold: Number(threshold),
    });
    setEditingItem(null);
    loadInventory();
  };

  return (
    <motion.div initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.25 }} className="space-y-6" data-testid="inventory-page-root">
      <Card className="border-slate-200">
        <CardHeader className="flex flex-col gap-4 md:flex-row md:items-center md:justify-between">
          <div>
            <CardTitle className="font-heading text-2xl" data-testid="inventory-title-text">Inventory Intelligence</CardTitle>
            <p className="text-sm text-slate-500" data-testid="inventory-subtitle-text">Monitor stock position, threshold risk, and restock priorities.</p>
          </div>
          <div className="flex w-full max-w-lg gap-3">
            <div className="relative flex-1">
              <Search className="absolute left-3 top-3.5 h-4 w-4 text-slate-400" />
              <Input value={search} onChange={(event) => setSearch(event.target.value)} className="h-11 border-slate-300 pl-9" placeholder="Search SKU, name, zone" data-testid="inventory-search-input" />
            </div>
            <Button onClick={loadInventory} data-testid="inventory-search-button">Search</Button>
          </div>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="flex flex-wrap gap-2" data-testid="inventory-status-filters">
            {["all", "healthy", "low", "critical"].map((status) => (
              <Button key={status} variant={statusFilter === status ? "default" : "outline"} onClick={() => setStatusFilter(status)} data-testid={`inventory-filter-${status}`}>
                {status}
              </Button>
            ))}
          </div>

          <div className="overflow-hidden rounded-lg border border-slate-200">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead data-testid="inventory-header-sku">SKU</TableHead>
                  <TableHead data-testid="inventory-header-product">Product</TableHead>
                  <TableHead data-testid="inventory-header-location">Location</TableHead>
                  <TableHead data-testid="inventory-header-quantity">Qty</TableHead>
                  <TableHead data-testid="inventory-header-status">Status</TableHead>
                  <TableHead data-testid="inventory-header-action">Action</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {items.map((item) => (
                  <TableRow key={item.id} data-testid={`inventory-row-${item.id}`}>
                    <TableCell data-testid={`inventory-sku-${item.id}`}>{item.sku}</TableCell>
                    <TableCell data-testid={`inventory-name-${item.id}`}>
                      <p className="font-semibold">{item.name}</p>
                      <p className="text-xs text-slate-500">{item.category}</p>
                    </TableCell>
                    <TableCell data-testid={`inventory-location-${item.id}`}>{item.zone} · {item.bin_code}</TableCell>
                    <TableCell data-testid={`inventory-qty-${item.id}`}>{item.quantity}</TableCell>
                    <TableCell><StatusBadge status={item.stock_status} testId={`inventory-status-${item.id}`} /></TableCell>
                    <TableCell>
                      <Button variant="outline" disabled={!editable} onClick={() => openEditor(item)} data-testid={`inventory-edit-button-${item.id}`}>
                        Edit
                      </Button>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </div>
        </CardContent>
      </Card>

      <Sheet open={Boolean(editingItem)} onOpenChange={() => setEditingItem(null)}>
        <SheetContent className="border-slate-200 bg-white">
          <SheetHeader>
            <SheetTitle data-testid="inventory-edit-sheet-title">Quick Stock Edit</SheetTitle>
          </SheetHeader>
          {editingItem && (
            <div className="space-y-4 pt-4" data-testid="inventory-edit-sheet-content">
              <p className="text-sm text-slate-600" data-testid="inventory-edit-item-name">{editingItem.name}</p>
              <div className="space-y-2">
                <label className="text-sm font-medium" htmlFor="edit-qty-input" data-testid="inventory-edit-qty-label">Quantity</label>
                <Input id="edit-qty-input" type="number" value={quantity} onChange={(event) => setQuantity(event.target.value)} data-testid="inventory-edit-qty-input" />
              </div>
              <div className="space-y-2">
                <label className="text-sm font-medium" htmlFor="edit-threshold-input" data-testid="inventory-edit-threshold-label">Reorder Threshold</label>
                <Input id="edit-threshold-input" type="number" value={threshold} onChange={(event) => setThreshold(event.target.value)} data-testid="inventory-edit-threshold-input" />
              </div>
              <Button onClick={saveInventory} className="w-full" data-testid="inventory-edit-save-button">
                <Save className="mr-2 h-4 w-4" />
                Save Changes
              </Button>
            </div>
          )}
        </SheetContent>
      </Sheet>
    </motion.div>
  );
}
