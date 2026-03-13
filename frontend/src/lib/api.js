import axios from "axios";

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;

const client = axios.create({
  baseURL: `${BACKEND_URL}/api`,
  timeout: 15000,
});

const roleQuery = (role) => ({ params: { role } });

export const warehouseApi = {
  async demoLogin(payload) {
    const response = await client.post("/auth/demo-login", payload);
    return response.data;
  },

  async seedDatabase() {
    const response = await client.post("/bootstrap/seed");
    return response.data;
  },

  async getOverview(role) {
    const response = await client.get("/warehouse/overview", roleQuery(role));
    return response.data;
  },

  async getInventory(role, query = {}) {
    const response = await client.get("/inventory", {
      params: { role, ...query },
    });
    return response.data;
  },

  async updateInventory(role, itemId, payload) {
    const response = await client.put(`/inventory/${itemId}`, payload, roleQuery(role));
    return response.data;
  },

  async getOrders(role) {
    const response = await client.get("/orders", roleQuery(role));
    return response.data;
  },

  async updateOrderStatus(role, orderId, status) {
    const response = await client.patch(`/orders/${orderId}/status`, { status }, roleQuery(role));
    return response.data;
  },

  async getRoutePlan(role, orderId) {
    const response = await client.get("/routes/optimize", {
      params: { role, order_id: orderId },
    });
    return response.data;
  },

  async getAnalytics(role) {
    const response = await client.get("/analytics/trends", roleQuery(role));
    return response.data;
  },

  async getAlerts(role, severity = "all") {
    const response = await client.get("/alerts", {
      params: severity === "all" ? { role } : { role, severity },
    });
    return response.data;
  },

  async getLayoutState(role) {
    const response = await client.get("/layout/state", roleQuery(role));
    return response.data;
  },

  async getLayoutStrategies(role) {
    const response = await client.get("/layout/strategies", roleQuery(role));
    return response.data;
  },

  async configureLayout(role, payload) {
    const response = await client.post("/layout/configure", payload, roleQuery(role));
    return response.data;
  },

  async addLayoutContainers(role, payload) {
    const response = await client.post("/layout/containers", payload, roleQuery(role));
    return response.data;
  },

  async seedLayoutContainers(role, payload = { replace_existing: false }) {
    const response = await client.post("/layout/containers/sample", payload, roleQuery(role));
    return response.data;
  },

  async retrieveLayoutContainer(role, payload) {
    const response = await client.post("/layout/retrieve", payload, roleQuery(role));
    return response.data;
  },
};
