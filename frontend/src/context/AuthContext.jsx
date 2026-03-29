import React, { createContext, useState, useEffect, useCallback } from "react";
import { warehouseApi } from "../lib/api";

export const AuthContext = createContext(null);

export const AuthProvider = ({ children }) => {
  const [user, setUser] = useState(null);
  const [accessToken, setAccessToken] = useState(null);
  const [refreshToken, setRefreshToken] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  // Initialize from localStorage on mount
  useEffect(() => {
    const storedToken = localStorage.getItem("accessToken") || localStorage.getItem("access_token");
    const storedUser = localStorage.getItem("user");

    if (storedToken && storedUser) {
      setAccessToken(storedToken);
      setUser(JSON.parse(storedUser));
      warehouseApi.setAuthToken(storedToken);
    }
    setLoading(false);
  }, []);

  const login = useCallback(async (email, password) => {
    setLoading(true);
    setError(null);
    try {
      const response = await warehouseApi.login({ email, password });

      const { access_token, refresh_token, user_id, email: userEmail, name, role } = response;

      const userData = {
        user_id,
        email: userEmail,
        name,
        role,
      };

      setAccessToken(access_token);
      setRefreshToken(refresh_token);
      setUser(userData);

      localStorage.setItem("accessToken", access_token);
      if (refresh_token) localStorage.setItem("refreshToken", refresh_token);
      localStorage.setItem("user", JSON.stringify(userData));

      warehouseApi.setAuthToken(access_token);

      return { success: true };
    } catch (err) {
      const message = err.response?.data?.detail || err.message || "Login failed";
      setError(message);
      return { success: false, error: message };
    } finally {
      setLoading(false);
    }
  }, []);

  const register = useCallback(async (email, password, name) => {
    setLoading(true);
    setError(null);
    try {
      const response = await warehouseApi.register({ email, password, name });

      const { access_token, refresh_token, user_id, email: userEmail, role } = response;

      const userData = {
        user_id,
        email: userEmail,
        name,
        role,
      };

      setAccessToken(access_token);
      setRefreshToken(refresh_token);
      setUser(userData);

      localStorage.setItem("accessToken", access_token);
      if (refresh_token) localStorage.setItem("refreshToken", refresh_token);
      localStorage.setItem("user", JSON.stringify(userData));

      warehouseApi.setAuthToken(access_token);

      return { success: true };
    } catch (err) {
      const message = err.response?.data?.detail || err.message || "Registration failed";
      setError(message);
      return { success: false, error: message };
    } finally {
      setLoading(false);
    }
  }, []);

  const refreshAccessToken = useCallback(async () => {
    try {
      const storedRefreshToken = refreshToken || localStorage.getItem("refreshToken");
      if (!storedRefreshToken) {
        throw new Error("No refresh token available");
      }

      const response = await warehouseApi.refreshToken({ refresh_token: storedRefreshToken });
      const { access_token } = response;

      setAccessToken(access_token);
      localStorage.setItem("accessToken", access_token);
      warehouseApi.setAuthToken(access_token);

      return { success: true, token: access_token };
    } catch (err) {
      logout();
      return { success: false, error: err.message };
    }
  }, [refreshToken]);

  const logout = useCallback(() => {
    setUser(null);
    setAccessToken(null);
    setRefreshToken(null);
    setError(null);

    localStorage.removeItem("accessToken");
    localStorage.removeItem("refreshToken");
    localStorage.removeItem("user");

    warehouseApi.setAuthToken(null);
  }, []);

  const isAdmin = user?.role === "Admin";
  const isAuthenticated = !!user && !!accessToken;

  return (
    <AuthContext.Provider
      value={{
        user,
        accessToken,
        isAuthenticated,
        isAdmin,
        loading,
        error,
        login,
        register,
        logout,
        refreshAccessToken,
        setError,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
};
