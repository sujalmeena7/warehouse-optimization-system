import { useState } from "react";
import { Navigate, useNavigate } from "react-router-dom";
import { motion } from "framer-motion";
import { LogIn } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";

const roles = ["Admin", "Manager", "Staff"];

export const LoginPage = ({ onLogin, isAuthenticated }) => {
  const [name, setName] = useState("Alex");
  const [role, setRole] = useState("Manager");
  const [loading, setLoading] = useState(false);
  const navigate = useNavigate();

  if (isAuthenticated) {
    return <Navigate to="/dashboard" replace />;
  }

  const submitHandler = async (event) => {
    event.preventDefault();
    setLoading(true);
    try {
      await onLogin({ name, role });
      navigate("/dashboard");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="flex min-h-screen bg-slate-100 p-4 md:p-8" data-testid="login-page-root">
      <div className="mx-auto grid w-full max-w-6xl gap-6 lg:grid-cols-2">
        <motion.div
          initial={{ opacity: 0, x: -18 }}
          animate={{ opacity: 1, x: 0 }}
          transition={{ duration: 0.3 }}
          className="overflow-hidden rounded-xl border border-slate-300"
        >
          <img
            src="https://images.pexels.com/photos/7019311/pexels-photo-7019311.jpeg?auto=compress&cs=tinysrgb&dpr=2&h=1200&w=1200"
            alt="Warehouse worker"
            className="h-full w-full object-cover"
            data-testid="login-hero-image"
          />
        </motion.div>

        <motion.div initial={{ opacity: 0, x: 18 }} animate={{ opacity: 1, x: 0 }} transition={{ duration: 0.3 }}>
          <Card className="h-full rounded-xl border border-slate-300 bg-white">
            <CardHeader>
              <p className="font-mono text-xs uppercase tracking-[0.26em] text-slate-500" data-testid="login-eyebrow-text">
                Internship Demo
              </p>
              <CardTitle className="font-heading text-4xl text-slate-900" data-testid="login-title-text">
                Warehouse Optimization System
              </CardTitle>
            </CardHeader>
            <CardContent>
              <form onSubmit={submitHandler} className="space-y-5" data-testid="login-form">
                <div className="space-y-2">
                  <label className="text-sm font-medium text-slate-700" htmlFor="name-input" data-testid="login-name-label">
                    Display Name
                  </label>
                  <Input
                    id="name-input"
                    value={name}
                    onChange={(event) => setName(event.target.value)}
                    className="h-11 border-slate-300"
                    data-testid="login-name-input"
                    required
                  />
                </div>

                <div className="space-y-2">
                  <label className="text-sm font-medium text-slate-700" htmlFor="role-input" data-testid="login-role-label">
                    Role
                  </label>
                  <select
                    id="role-input"
                    value={role}
                    onChange={(event) => setRole(event.target.value)}
                    className="h-11 w-full rounded-md border border-slate-300 px-3 text-sm outline-none focus:border-orange-500"
                    data-testid="login-role-select"
                  >
                    {roles.map((roleOption) => (
                      <option key={roleOption} value={roleOption} data-testid={`login-role-option-${roleOption.toLowerCase()}`}>
                        {roleOption}
                      </option>
                    ))}
                  </select>
                </div>

                <Button className="h-11 w-full bg-slate-900 hover:bg-slate-800" disabled={loading} data-testid="login-submit-button">
                  <LogIn className="mr-2 h-4 w-4" />
                  {loading ? "Signing In..." : "Enter Control Tower"}
                </Button>
              </form>
            </CardContent>
          </Card>
        </motion.div>
      </div>
    </div>
  );
};
