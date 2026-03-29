import { useState, useEffect } from "react";
import { useAuth } from "../hooks/useAuth";
import { warehouseApi } from "../lib/api";
import { Button } from "../components/ui/button";
import { Input } from "../components/ui/input";

export default function AdminUsersPage() {
  const { user, isAdmin } = useAuth();
  const [users, setUsers] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [showForm, setShowForm] = useState(false);
  const [newUser, setNewUser] = useState({ name: "", email: "", password: "", role: "Staff" });

  useEffect(() => {
    if (!isAdmin) return;
    fetchUsers();
  }, [isAdmin]);

  const fetchUsers = async () => {
    try {
      setLoading(true);
      const result = await warehouseApi.getUsers();
      setUsers(result || []);
    } catch (err) {
      setError(err.response?.data?.detail || "Failed to fetch users");
    } finally {
      setLoading(false);
    }
  };

  const handleCreateUser = async (e) => {
    e.preventDefault();
    if (!newUser.name || !newUser.email || !newUser.password) {
      setError("All fields are required");
      return;
    }

    try {
      await warehouseApi.createUser({
        name: newUser.name,
        email: newUser.email,
        password: newUser.password,
        role: newUser.role,
      });
      setNewUser({ name: "", email: "", password: "", role: "Staff" });
      setShowForm(false);
      setError("");
      fetchUsers();
    } catch (err) {
      setError(err.response?.data?.detail || "Failed to create user");
    }
  };

  if (!isAdmin) {
    return (
      <div className="p-8 bg-yellow-50 border-l-4 border-yellow-400">
        <p className="text-yellow-700">You do not have permission to access this page.</p>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex justify-between items-center">
        <h1 className="text-2xl font-bold text-gray-900">User Management</h1>
        <Button
          onClick={() => setShowForm(!showForm)}
          className="bg-blue-600 hover:bg-blue-700 text-white"
        >
          {showForm ? "Cancel" : "Add User"}
        </Button>
      </div>

      {error && (
        <div className="rounded-md bg-red-50 p-4">
          <p className="text-sm font-medium text-red-800">{error}</p>
        </div>
      )}

      {showForm && (
        <form onSubmit={handleCreateUser} className="bg-white p-6 rounded-lg shadow space-y-4">
          <div className="grid grid-cols-2 gap-4">
            <Input
              placeholder="Name"
              value={newUser.name}
              onChange={(e) => setNewUser({ ...newUser, name: e.target.value })}
              required
            />
            <Input
              placeholder="Email"
              type="email"
              value={newUser.email}
              onChange={(e) => setNewUser({ ...newUser, email: e.target.value })}
              required
            />
            <Input
              placeholder="Password"
              type="password"
              value={newUser.password}
              onChange={(e) => setNewUser({ ...newUser, password: e.target.value })}
              required
            />
            <select
              value={newUser.role}
              onChange={(e) => setNewUser({ ...newUser, role: e.target.value })}
              className="px-3 py-2 border border-gray-300 rounded-md"
            >
              <option value="Staff">Staff</option>
              <option value="Manager">Manager</option>
              <option value="Admin">Admin</option>
            </select>
          </div>
          <Button type="submit" className="bg-green-600 hover:bg-green-700 text-white w-full">
            Create User
          </Button>
        </form>
      )}

      {loading ? (
        <p>Loading users...</p>
      ) : (
        <div className="bg-white rounded-lg shadow overflow-hidden">
          <table className="min-w-full divide-y divide-gray-200">
            <thead className="bg-gray-50">
              <tr>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Name</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Email</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Role</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Created</th>
              </tr>
            </thead>
            <tbody className="bg-white divide-y divide-gray-200">
              {users.map((u) => (
                <tr key={u.user_id} className="hover:bg-gray-50">
                  <td className="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900">{u.name}</td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-600">{u.email}</td>
                  <td className="px-6 py-4 whitespace-nowrap">
                    <span className={`px-2 py-1 text-xs font-semibold rounded-full ${
                      u.role === "Admin" ? "bg-red-100 text-red-800" :
                      u.role === "Manager" ? "bg-blue-100 text-blue-800" :
                      "bg-green-100 text-green-800"
                    }`}>
                      {u.role}
                    </span>
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                    {new Date(u.created_at).toLocaleDateString()}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
