import { useEffect, useMemo, useState } from "react";
import { motion } from "framer-motion";
import { AlertCircle, Layers, LayoutGrid, Search, Settings } from "lucide-react";
import { toast } from "@/components/ui/sonner";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { warehouseApi } from "@/lib/api";

const sizeColorMap = {
  Small: "bg-blue-100 text-blue-700",
  Medium: "bg-amber-100 text-amber-800",
  Large: "bg-slate-300 text-slate-900",
};

const accessBorderMap = {
  High: "border-orange-500",
  Medium: "border-slate-400",
  Low: "border-slate-300",
};

const accessTagMap = {
  High: "bg-orange-100 text-orange-700",
  Medium: "bg-slate-200 text-slate-700",
  Low: "bg-slate-100 text-slate-500",
};

const strategyLabels = {
  greedy_access: "Greedy Access Priority",
  genetic_algorithm: "Genetic Algorithm (future)",
  a_star: "A* Search (future)",
  reinforcement_learning: "Reinforcement Learning (future)",
};

const emptyConfig = {
  rows: 10,
  cols: 10,
  max_stack_height: 5,
  strategy: "greedy_access",
  clear_containers: false,
};

const emptyContainer = {
  container_id: "",
  size: "Medium",
  weight: 50,
  access_frequency: "Medium",
  arrival_time: "",
};

const cellShade = (height, maxHeight) => {
  const ratio = maxHeight === 0 ? 0 : height / maxHeight;
  if (ratio === 0) return "bg-white";
  if (ratio <= 0.25) return "bg-slate-100";
  if (ratio <= 0.5) return "bg-slate-200";
  if (ratio <= 0.75) return "bg-slate-300";
  return "bg-slate-500 text-white";
};

export default function WarehouseLayoutPage({ user }) {
  const [layoutState, setLayoutState] = useState(null);
  const [strategies, setStrategies] = useState([]);
  const [configForm, setConfigForm] = useState(emptyConfig);
  const [containerForm, setContainerForm] = useState(emptyContainer);
  const [retrievalId, setRetrievalId] = useState("");
  const [retrievalResult, setRetrievalResult] = useState(null);
  const [loading, setLoading] = useState(true);
  const [savingConfig, setSavingConfig] = useState(false);
  const [addingContainer, setAddingContainer] = useState(false);
  const [runningRetrieval, setRunningRetrieval] = useState(false);

  const gridCells = useMemo(() => (layoutState ? layoutState.grid.flat() : []), [layoutState]);

  const loadLayoutData = async () => {
    try {
      const [strategyResponse, stateResponse] = await Promise.all([
        warehouseApi.getLayoutStrategies(user.role),
        warehouseApi.getLayoutState(user.role),
      ]);
      setStrategies(strategyResponse);
      setLayoutState(stateResponse);
      setConfigForm({ ...stateResponse.config, clear_containers: false });
    } catch (error) {
      toast.error(error?.response?.data?.detail || "Failed to load layout optimization module");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadLayoutData();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [user.role]);

  const applyConfig = async () => {
    setSavingConfig(true);
    try {
      const updated = await warehouseApi.configureLayout(user.role, {
        rows: Number(configForm.rows),
        cols: Number(configForm.cols),
        max_stack_height: Number(configForm.max_stack_height),
        strategy: configForm.strategy,
        clear_containers: Boolean(configForm.clear_containers),
      });
      setLayoutState(updated);
      setConfigForm((prev) => ({ ...prev, clear_containers: false }));
      setRetrievalResult(null);
      toast.success("Layout configuration applied");
    } catch (error) {
      toast.error(error?.response?.data?.detail || "Unable to apply configuration");
    } finally {
      setSavingConfig(false);
    }
  };

  const addContainer = async (event) => {
    event.preventDefault();
    setAddingContainer(true);
    try {
      const payload = {
        containers: [
          {
            container_id: containerForm.container_id,
            size: containerForm.size,
            weight: Number(containerForm.weight),
            access_frequency: containerForm.access_frequency,
            arrival_time: containerForm.arrival_time || undefined,
          },
        ],
      };
      const updated = await warehouseApi.addLayoutContainers(user.role, payload);
      setLayoutState(updated);
      setContainerForm({ ...emptyContainer, arrival_time: containerForm.arrival_time });
      toast.success("Container added and optimized");
    } catch (error) {
      toast.error(error?.response?.data?.detail || "Unable to add container");
    } finally {
      setAddingContainer(false);
    }
  };

  const seedSample = async (replaceExisting) => {
    try {
      const updated = await warehouseApi.seedLayoutContainers(user.role, { replace_existing: replaceExisting });
      setLayoutState(updated);
      toast.success(replaceExisting ? "Sample data reset complete" : "Sample data added");
    } catch (error) {
      toast.error(error?.response?.data?.detail || "Unable to seed sample containers");
    }
  };

  const runRetrievalSimulation = async () => {
    if (!retrievalId.trim()) {
      toast.error("Enter a container ID to simulate retrieval");
      return;
    }
    setRunningRetrieval(true);
    try {
      const result = await warehouseApi.retrieveLayoutContainer(user.role, { container_id: retrievalId.trim() });
      setRetrievalResult(result);
      toast.success("Retrieval simulation complete");
    } catch (error) {
      setRetrievalResult(null);
      toast.error(error?.response?.data?.detail || "Container not found in current optimized layout");
    } finally {
      setRunningRetrieval(false);
    }
  };

  if (loading || !layoutState) {
    return (
      <div className="rounded-xl border border-slate-200 bg-white p-6" data-testid="layout-page-loading-state">
        Loading warehouse layout optimizer...
      </div>
    );
  }

  return (
    <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.3 }} className="space-y-6" data-testid="layout-page-root">
      <Card className="border-slate-200">
        <CardHeader>
          <p className="font-mono text-xs uppercase tracking-[0.24em] text-slate-500" data-testid="layout-page-eyebrow-text">
            Grid Stacking Simulation
          </p>
          <CardTitle className="font-heading text-3xl" data-testid="layout-page-title-text">
            Warehouse Layout Optimization
          </CardTitle>
          <p className="text-sm text-slate-500" data-testid="layout-page-subtitle-text">
            Configure a 2D grid, place containers with stacking rules, and simulate retrieval cost using weighted heuristics.
          </p>
        </CardHeader>
      </Card>

      <div className="grid gap-6 xl:grid-cols-[1.45fr_1fr]" data-testid="layout-main-grid">
        <Card className="border-slate-200" data-testid="layout-grid-card">
          <CardHeader className="flex flex-row items-center justify-between">
            <CardTitle className="text-xl" data-testid="layout-grid-title">
              <span className="inline-flex items-center gap-2">
                <LayoutGrid className="h-5 w-5 text-orange-500" /> Grid Visualizer
              </span>
            </CardTitle>
            <div className="rounded-md bg-slate-100 px-3 py-1 text-xs font-mono text-slate-600" data-testid="layout-grid-dimensions-text">
              {layoutState.config.rows} × {layoutState.config.cols} · Max H {layoutState.config.max_stack_height}
            </div>
          </CardHeader>
          <CardContent>
            <div className="overflow-x-auto rounded-xl border border-slate-200 bg-slate-50 p-3" data-testid="layout-grid-container">
              <div
                className="grid gap-2"
                style={{ gridTemplateColumns: `repeat(${layoutState.config.cols}, minmax(92px, 1fr))` }}
                data-testid="layout-grid-cells-wrapper"
              >
                {gridCells.map((cell) => {
                  const visibleContainers = [...cell.containers].slice(-3).reverse();
                  return (
                    <div
                      key={`${cell.row}-${cell.col}`}
                      className={`rounded-md border border-slate-200 p-2 transition-colors ${cellShade(
                        cell.stack_height,
                        layoutState.config.max_stack_height,
                      )}`}
                      data-testid={`layout-grid-cell-${cell.row}-${cell.col}`}
                    >
                      <div className="mb-2 flex items-center justify-between text-[10px] font-mono uppercase" data-testid={`layout-grid-cell-header-${cell.row}-${cell.col}`}>
                        <span>R{cell.row + 1}C{cell.col + 1}</span>
                        <span data-testid={`layout-grid-cell-height-${cell.row}-${cell.col}`}>{cell.stack_height}</span>
                      </div>
                      {visibleContainers.length === 0 ? (
                        <div className="rounded-sm border border-dashed border-slate-300 py-2 text-center text-[10px] font-mono text-slate-500" data-testid={`layout-grid-cell-empty-${cell.row}-${cell.col}`}>
                          EMPTY
                        </div>
                      ) : (
                        <div className="space-y-1" data-testid={`layout-grid-cell-stack-${cell.row}-${cell.col}`}>
                          {visibleContainers.map((container) => (
                            <div
                              key={`${container.container_id}-${container.level}`}
                              className={`truncate rounded-sm border px-1 py-1 text-[10px] font-mono ${sizeColorMap[container.size]} ${accessBorderMap[container.access_frequency]}`}
                              data-testid={`layout-grid-container-pill-${container.container_id}`}
                            >
                              {container.container_id}
                            </div>
                          ))}
                          {cell.stack_height > 3 ? (
                            <p className="text-center text-[10px] text-slate-500" data-testid={`layout-grid-more-${cell.row}-${cell.col}`}>
                              +{cell.stack_height - 3} more
                            </p>
                          ) : null}
                        </div>
                      )}
                    </div>
                  );
                })}
              </div>
            </div>
          </CardContent>
        </Card>

        <div className="space-y-6" data-testid="layout-controls-column">
          <Card className="border-slate-200" data-testid="layout-metrics-card">
            <CardHeader>
              <CardTitle className="text-lg" data-testid="layout-metrics-title">Performance Metrics</CardTitle>
            </CardHeader>
            <CardContent className="grid gap-3 sm:grid-cols-2">
              <div className="rounded-lg border border-slate-200 p-3" data-testid="layout-metric-space-utilization">
                <p className="text-xs uppercase text-slate-500">Space Utilization</p>
                <p className="font-heading text-2xl">{layoutState.metrics.space_utilization}%</p>
              </div>
              <div className="rounded-lg border border-slate-200 p-3" data-testid="layout-metric-average-retrieval-time">
                <p className="text-xs uppercase text-slate-500">Avg Retrieval Time</p>
                <p className="font-heading text-2xl">{layoutState.metrics.average_retrieval_time}</p>
              </div>
              <div className="rounded-lg border border-slate-200 p-3" data-testid="layout-metric-average-movements">
                <p className="text-xs uppercase text-slate-500">Avg Movements</p>
                <p className="font-heading text-2xl">{layoutState.metrics.average_container_movements}</p>
              </div>
              <div className="rounded-lg border border-slate-200 p-3" data-testid="layout-metric-total-containers">
                <p className="text-xs uppercase text-slate-500">Placed / Total</p>
                <p className="font-heading text-2xl">{layoutState.placed_containers}/{layoutState.total_containers}</p>
              </div>
            </CardContent>
          </Card>

          <Card className="border-slate-200" data-testid="layout-config-card">
            <CardHeader>
              <CardTitle className="text-lg" data-testid="layout-config-title">
                <span className="inline-flex items-center gap-2"><Settings className="h-4 w-4" /> Layout Configuration</span>
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-3">
              <div className="grid grid-cols-3 gap-2">
                <Input type="number" value={configForm.rows} min={4} max={20} onChange={(event) => setConfigForm((prev) => ({ ...prev, rows: event.target.value }))} data-testid="layout-config-rows-input" />
                <Input type="number" value={configForm.cols} min={4} max={20} onChange={(event) => setConfigForm((prev) => ({ ...prev, cols: event.target.value }))} data-testid="layout-config-cols-input" />
                <Input type="number" value={configForm.max_stack_height} min={2} max={8} onChange={(event) => setConfigForm((prev) => ({ ...prev, max_stack_height: event.target.value }))} data-testid="layout-config-max-height-input" />
              </div>

              <select value={configForm.strategy} onChange={(event) => setConfigForm((prev) => ({ ...prev, strategy: event.target.value }))} className="h-10 w-full rounded-md border border-slate-200 px-3 text-sm" data-testid="layout-config-strategy-select">
                {strategies.map((strategy) => (
                  <option key={strategy.key} value={strategy.key} data-testid={`layout-config-strategy-option-${strategy.key}`}>
                    {strategyLabels[strategy.key] || strategy.label}
                  </option>
                ))}
              </select>

              <label className="flex items-center gap-2 text-sm text-slate-600" data-testid="layout-config-clear-container-label">
                <input type="checkbox" checked={configForm.clear_containers} onChange={(event) => setConfigForm((prev) => ({ ...prev, clear_containers: event.target.checked }))} data-testid="layout-config-clear-container-checkbox" />
                Clear containers while applying config
              </label>

              <Button onClick={applyConfig} disabled={savingConfig} className="w-full" data-testid="layout-config-apply-button">
                {savingConfig ? "Applying..." : "Apply Configuration"}
              </Button>

              <div className="grid grid-cols-2 gap-2">
                <Button variant="outline" onClick={() => seedSample(false)} data-testid="layout-seed-sample-append-button">Add Sample Data</Button>
                <Button variant="outline" onClick={() => seedSample(true)} data-testid="layout-seed-sample-reset-button">Reset with Sample</Button>
              </div>
            </CardContent>
          </Card>

          <Card className="border-slate-200" data-testid="layout-add-container-card">
            <CardHeader>
              <CardTitle className="text-lg" data-testid="layout-add-container-title">
                <span className="inline-flex items-center gap-2"><Layers className="h-4 w-4" /> Add Container</span>
              </CardTitle>
            </CardHeader>
            <CardContent>
              <form className="space-y-3" onSubmit={addContainer} data-testid="layout-add-container-form">
                <Input value={containerForm.container_id} placeholder="Container ID (e.g., CNT-2001)" onChange={(event) => setContainerForm((prev) => ({ ...prev, container_id: event.target.value }))} data-testid="layout-container-id-input" required />
                <div className="grid grid-cols-2 gap-2">
                  <select value={containerForm.size} onChange={(event) => setContainerForm((prev) => ({ ...prev, size: event.target.value }))} className="h-10 rounded-md border border-slate-200 px-2 text-sm" data-testid="layout-container-size-select">
                    <option value="Small">Small</option>
                    <option value="Medium">Medium</option>
                    <option value="Large">Large</option>
                  </select>
                  <Input type="number" value={containerForm.weight} min={1} step={0.1} onChange={(event) => setContainerForm((prev) => ({ ...prev, weight: event.target.value }))} data-testid="layout-container-weight-input" required />
                </div>
                <select value={containerForm.access_frequency} onChange={(event) => setContainerForm((prev) => ({ ...prev, access_frequency: event.target.value }))} className="h-10 rounded-md border border-slate-200 px-2 text-sm" data-testid="layout-container-access-select">
                  <option value="High">High</option>
                  <option value="Medium">Medium</option>
                  <option value="Low">Low</option>
                </select>
                <Input type="datetime-local" value={containerForm.arrival_time} onChange={(event) => setContainerForm((prev) => ({ ...prev, arrival_time: event.target.value }))} data-testid="layout-container-arrival-input" />
                <Button type="submit" disabled={addingContainer} className="w-full" data-testid="layout-container-submit-button">
                  {addingContainer ? "Adding..." : "Add and Optimize"}
                </Button>
              </form>
            </CardContent>
          </Card>

          <Card className="border-slate-200" data-testid="layout-retrieval-card">
            <CardHeader>
              <CardTitle className="text-lg" data-testid="layout-retrieval-title">
                <span className="inline-flex items-center gap-2"><Search className="h-4 w-4" /> Retrieval Simulation</span>
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-3">
              <div className="flex gap-2">
                <Input value={retrievalId} onChange={(event) => setRetrievalId(event.target.value)} placeholder="Enter container ID" data-testid="layout-retrieval-id-input" />
                <Button onClick={runRetrievalSimulation} disabled={runningRetrieval} data-testid="layout-retrieval-run-button">
                  {runningRetrieval ? "Running..." : "Run"}
                </Button>
              </div>

              {retrievalResult ? (
                <div className="space-y-2 rounded-lg border border-slate-200 bg-slate-50 p-3" data-testid="layout-retrieval-result-block">
                  <p className="text-sm font-semibold" data-testid="layout-retrieval-result-header">
                    {retrievalResult.container_id} at R{retrievalResult.row + 1}C{retrievalResult.col + 1}, Level {retrievalResult.level}
                  </p>
                  <p className="text-xs text-slate-600" data-testid="layout-retrieval-result-metrics">
                    Time: {retrievalResult.estimated_retrieval_time} · Cost: {retrievalResult.estimated_retrieval_cost} · Movements: {retrievalResult.movement_count}
                  </p>
                  <div className="flex flex-wrap gap-1" data-testid="layout-retrieval-blockers-list">
                    {retrievalResult.blockers.length > 0 ? (
                      retrievalResult.blockers.map((blockerId) => (
                        <span key={blockerId} className="rounded bg-orange-100 px-2 py-0.5 text-xs text-orange-700" data-testid={`layout-retrieval-blocker-${blockerId}`}>
                          {blockerId}
                        </span>
                      ))
                    ) : (
                      <span className="text-xs text-emerald-700" data-testid="layout-retrieval-no-blockers-text">No blockers above target container</span>
                    )}
                  </div>
                  <div className="space-y-1" data-testid="layout-retrieval-steps-list">
                    {retrievalResult.steps.map((step) => (
                      <p key={`${step.step}-${step.container_id}`} className="text-xs text-slate-600" data-testid={`layout-retrieval-step-${step.step}`}>
                        Step {step.step}: {step.action} ({step.container_id})
                      </p>
                    ))}
                  </div>
                </div>
              ) : (
                <div className="rounded-md border border-dashed border-slate-300 p-3 text-xs text-slate-500" data-testid="layout-retrieval-placeholder">
                  Enter a container ID to visualize blockers and retrieval effort.
                </div>
              )}
            </CardContent>
          </Card>

          <Card className="border-slate-200" data-testid="layout-legend-card">
            <CardHeader>
              <CardTitle className="text-base" data-testid="layout-legend-title">Color Legend</CardTitle>
            </CardHeader>
            <CardContent className="space-y-2 text-xs">
              <p className="text-slate-600">Size colors:</p>
              <div className="flex flex-wrap gap-2" data-testid="layout-size-legend-items">
                {Object.keys(sizeColorMap).map((size) => (
                  <span key={size} className={`rounded px-2 py-0.5 ${sizeColorMap[size]}`} data-testid={`layout-size-legend-${size.toLowerCase()}`}>
                    {size}
                  </span>
                ))}
              </div>
              <p className="text-slate-600">Access priority tags:</p>
              <div className="flex flex-wrap gap-2" data-testid="layout-access-legend-items">
                {Object.keys(accessTagMap).map((access) => (
                  <span key={access} className={`rounded px-2 py-0.5 ${accessTagMap[access]}`} data-testid={`layout-access-legend-${access.toLowerCase()}`}>
                    {access}
                  </span>
                ))}
              </div>
              {layoutState.unplaced_containers.length > 0 ? (
                <div className="mt-2 rounded-md border border-orange-200 bg-orange-50 p-2 text-orange-700" data-testid="layout-unplaced-warning">
                  <span className="inline-flex items-center gap-1"><AlertCircle className="h-3.5 w-3.5" /> Unplaced:</span> {layoutState.unplaced_containers.join(", ")}
                </div>
              ) : null}
            </CardContent>
          </Card>
        </div>
      </div>
    </motion.div>
  );
}
