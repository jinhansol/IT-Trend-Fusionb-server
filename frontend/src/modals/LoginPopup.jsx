import React, { useState } from "react";
import { loginUser } from "../api/authAPI";
import PopupLayout from "../components/PopupLayout";

export default function LoginPopup({ onClose, onSwitch, setUser }) {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  const handleLogin = async (e) => {
    e.preventDefault();
    setLoading(true);
    setError("");

    try {
      const data = await loginUser(email, password);

      setUser(data.user);
      localStorage.setItem("user", JSON.stringify(data.user));
      localStorage.setItem("token", data.access_token);

      onClose();
    } catch (err) {
      setError(err.response?.data?.detail || "로그인 실패");
    } finally {
      setLoading(false);
    }
  };

  return (
    <PopupLayout title="Welcome back ⚡" onClose={onClose}>
      <form onSubmit={handleLogin} className="space-y-5">

        <div>
          <label className="block text-sm font-medium text-gray-600 mb-1">Email</label>
          <input
            type="email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            required
            className="w-full border border-gray-300 rounded-md px-3 py-2"
          />
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-600 mb-1">Password</label>
          <input
            type="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            required
            className="w-full border border-gray-300 rounded-md px-3 py-2"
          />
        </div>

        {error && <p className="text-red-500 text-sm">{error}</p>}

        <button type="submit"
          disabled={loading}
          className="w-full bg-emerald-600 text-white py-2 rounded-md"
        >
          {loading ? "Signing in..." : "Sign In"}
        </button>
      </form>

      <div className="mt-8 text-center text-sm text-gray-500">
        Don’t have an account?{" "}
        <button onClick={onSwitch} className="text-emerald-600 font-medium hover:underline">
          Sign Up
        </button>
      </div>
    </PopupLayout>
  );
}
