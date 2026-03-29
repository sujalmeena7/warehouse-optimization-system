import axios from "axios";

const client = axios.create({
  baseURL: "http://localhost:8000/api",
  timeout: 15000,
});

let authToken = null;

// Add request interceptor to log
client.interceptors.request.use((config) => {
  console.log('[API] Request:', config.method.toUpperCase(), config.url);
  return config;
});

// Single response interceptor with both logging and token refresh
client.interceptors.response.use(
  (response) => {
    console.log('[API] Response:', response.status, response.config.url);
    return response;
  },
  async (error) => {
    console.error('[API] Error:', error.config?.method?.toUpperCase(), error.config?.url, error.response?.status, error.message);
    const originalRequest = error.config;

    // If 401 and we haven't already retried this request
    if (error.response?.status === 401 && !originalRequest._retry) {
      originalRequest._retry = true;

      try {
        const refreshToken = localStorage.getItem("refreshToken") || localStorage.getItem("refresh_token");
        if (!refreshToken) {
          throw new Error("No refresh token available");
        }

        const response = await client.post("/auth/refresh", { refresh_token: refreshToken });
        const { access_token } = response.data;

        if (typeof warehouseApi !== 'undefined') {
          warehouseApi.setAuthToken(access_token);
        }
        localStorage.setItem("accessToken", access_token);

        // Retry the original request
        return client(originalRequest);
      } catch (refreshError) {
        // Refresh failed, clear tokens and redirect to login
        localStorage.removeItem("accessToken");
        localStorage.removeItem("refreshToken");
        localStorage.removeItem("user");
        if (typeof warehouseApi !== 'undefined') {
          warehouseApi.setAuthToken(null);
        }
        window.location.href = "/login";
        return Promise.reject(refreshError);
      }
    }

    return Promise.reject(error);
  }
);

export const warehouseApi = {
  baseURL: "http://localhost:8000/api",

  // Generic HTTP methods for endpoints without dedicated wrappers
  async get(url) {
    const response = await client.get(url);
    return response.data;
  },

  async post(url, data) {
    const response = await client.post(url, data);
    return response.data;
  },

  setAuthToken(token) {
    authToken = token;
    if (token) {
      client.defaults.headers.common["Authorization"] = `Bearer ${token}`;
    } else {
      delete client.defaults.headers.common["Authorization"];
    }
  },

  // JWT-based auth endpoints
  async register(payload) {
    const response = await client.post("/auth/register", payload);
    return response.data;
  },

  async login(payload) {
    const response = await client.post("/auth/login", payload);
    return response.data;
  },

  async refreshToken(payload) {
    const response = await client.post("/auth/refresh", payload);
    return response.data;
  },

  // User management endpoints (Admin only)
  async getUsers() {
    const response = await client.get("/users");
    return response.data;
  },

  async listUsers() {
    const response = await client.get("/users");
    return response.data;
  },

  async createUser(payload) {
    const response = await client.post("/users", payload);
    return response.data;
  },

  async updateUser(userId, payload) {
    const response = await client.put(`/users/${userId}`, payload);
    return response.data;
  },

  async deactivateUser(userId) {
    const response = await client.delete(`/users/${userId}`);
    return response.data;
  },

  // Audit log endpoints
  async getAuditLogs(filters = {}) {
    const response = await client.get("/audit-logs", { params: filters });
    return response.data;
  },

  async getEntityAuditTrail(entityType, entityId) {
    const response = await client.get(`/audit-logs/${entityType}/${entityId}`);
    return response.data;
  },

  async getUserAuditTrail(userId) {
    const response = await client.get(`/audit-logs/user/${userId}`);
    return response.data;
  },

  // CSV Import endpoints
  async importContainers(file) {
    const formData = new FormData();
    formData.append("file", file);
    const response = await client.post("/import/containers", formData, {
      headers: { "Content-Type": "multipart/form-data" },
    });
    return response.data;
  },

  async importInventory(file) {
    const formData = new FormData();
    formData.append("file", file);
    const response = await client.post("/import/inventory", formData, {
      headers: { "Content-Type": "multipart/form-data" },
    });
    return response.data;
  },

  async downloadContainersTemplate() {
    const response = await client.get("/import/templates/containers", {
      responseType: "blob",
    });
    return response.data;
  },

  async downloadInventoryTemplate() {
    const response = await client.get("/import/templates/inventory", {
      responseType: "blob",
    });
    return response.data;
  },

  // Warehouse data endpoints (role extracted from JWT by backend)
  async seedDatabase() {
    const response = await client.post("/bootstrap/seed");
    return response.data;
  },

  async getOverview() {
    const response = await client.get("/warehouse/overview");
    return response.data;
  },

  async getInventory(query = {}) {
    const response = await client.get("/inventory", { params: query });
    return response.data;
  },

  async updateInventory(itemId, payload) {
    const response = await client.put(`/inventory/${itemId}`, payload);
    return response.data;
  },

  async getOrders() {
    const response = await client.get("/orders");
    return response.data;
  },

  async updateOrderStatus(orderId, status) {
    const response = await client.patch(`/orders/${orderId}/status`, { status });
    return response.data;
  },

  async getRoutePlan(orderId) {
    const response = await client.get("/routes/optimize", {
      params: { order_id: orderId },
    });
    return response.data;
  },

  async getAnalytics() {
    const response = await client.get("/analytics/trends");
    return response.data;
  },

  async getAlerts(severity = "all") {
    const params = severity === "all" ? {} : { severity };
    const response = await client.get("/alerts", { params });
    return response.data;
  },

  async getLayoutState() {
    const response = await client.get("/layout/state");
    return response.data;
  },

  async getLayoutStrategies() {
    const response = await client.get("/layout/strategies");
    return response.data;
  },

  async configureLayout(payload) {
    const response = await client.post("/layout/configure", payload);
    return response.data;
  },

  async addLayoutContainers(payload) {
    const response = await client.post("/layout/containers", payload);
    return response.data;
  },

  async seedLayoutContainers(payload = { replace_existing: false }) {
    const response = await client.post("/layout/containers/sample", payload);
    return response.data;
  },

  async retrieveLayoutContainer(payload) {
    const response = await client.post("/layout/retrieve", payload);
    return response.data;
  },
};

export default warehouseApi;
