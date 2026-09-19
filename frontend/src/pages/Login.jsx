import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { loginUser } from "../api/api";

export default function Login() {
  const navigate = useNavigate();

  const selectedRole =
    localStorage.getItem("selectedRole") || "student";

  const [studentId, setStudentId] = useState("");
  const [password, setPassword] = useState("");

  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  const login = async () => {
    if (!studentId.trim() || !password.trim()) {
      setError("Please enter your ID and password.");
      return;
    }

    try {
      setLoading(true);
      setError("");

      const result = await loginUser({
        student_id: studentId.trim(),
        password: password,
      });

      if (!result?.token || !result?.user) {
        throw new Error("Invalid login response");
      }

      if (result.user.role !== selectedRole) {
        setError(
          `This account belongs to the ${result.user.role} role. Please select the correct role.`
        );
        return;
      }

      localStorage.setItem("token", result.token);
      localStorage.setItem(
        "user",
        JSON.stringify(result.user)
      );

      if (
        result.user.role === "student" &&
        result.user.must_change_password
      ) {
        navigate("/student/change-password");
        return;
      }

      if (result.user.role === "student") {
        navigate("/student/dashboard");
      } else if (result.user.role === "lecturer") {
        navigate("/lecturer/dashboard");
      } else if (result.user.role === "admin") {
        navigate("/admin/dashboard");
      } else {
        setError("Invalid account role.");
      }
    } catch (err) {
      console.error("Login error:", err);

      setError(
        err?.response?.data?.detail ||
          err?.message ||
          "Login failed. Please check your ID and password."
      );
    } finally {
      setLoading(false);
    }
  };

  const handleKeyDown = (event) => {
    if (event.key === "Enter") {
      login();
    }
  };

  const getRoleTitle = () => {
    if (selectedRole === "student") {
      return "🎓 Student Login";
    }

    if (selectedRole === "lecturer") {
      return "👨‍🏫 Lecturer Login";
    }

    if (selectedRole === "admin") {
      return "👨‍💼 Admin Login";
    }

    return "Login";
  };

  return (
    <div className="min-h-screen bg-[#020817] flex items-center justify-center px-4">

      <div className="w-full max-w-[420px] bg-[#0b2236] border border-white/10 p-8 rounded-2xl shadow-2xl">

        <div className="text-center mb-7">

          <div className="w-16 h-16 mx-auto rounded-2xl bg-gradient-to-br from-blue-500 to-purple-600 flex items-center justify-center text-4xl shadow-lg">
            🎓
          </div>

          <h1 className="text-3xl font-bold text-white mt-4">
            Student360
          </h1>

          <p className="text-gray-400 mt-2">
            {getRoleTitle()}
          </p>

        </div>

        <div className="mb-4">

          <label className="block text-sm text-gray-300 mb-2">
            User ID
          </label>

          <input
            type="text"
            placeholder={
              selectedRole === "student"
                ? "Example: ITBIN-2211-0253"
                : "Enter your user ID"
            }
            className="w-full p-3 rounded-xl bg-[#071828] border border-white/10 text-white outline-none focus:border-blue-500 transition"
            value={studentId}
            onChange={(event) =>
              setStudentId(event.target.value)
            }
            onKeyDown={handleKeyDown}
            autoComplete="username"
          />

        </div>

        <div className="mb-4">

          <label className="block text-sm text-gray-300 mb-2">
            Password
          </label>

          <input
            type="password"
            placeholder="Enter your password"
            className="w-full p-3 rounded-xl bg-[#071828] border border-white/10 text-white outline-none focus:border-blue-500 transition"
            value={password}
            onChange={(event) =>
              setPassword(event.target.value)
            }
            onKeyDown={handleKeyDown}
            autoComplete="current-password"
          />

        </div>

        {error && (
          <div className="bg-red-500/10 border border-red-500/30 text-red-300 rounded-xl p-3 mb-4 text-sm">
            {error}
          </div>
        )}

        <button
          onClick={login}
          disabled={loading}
          className="w-full bg-gradient-to-r from-blue-600 to-purple-600 hover:from-blue-700 hover:to-purple-700 disabled:opacity-50 disabled:cursor-not-allowed text-white py-3 rounded-xl font-semibold transition flex items-center justify-center gap-2"
        >
          {loading && (
            <span className="w-5 h-5 border-2 border-white/40 border-t-white rounded-full animate-spin" />
          )}

          {loading ? "Signing In..." : "Login"}
        </button>

        <button
          onClick={() => navigate("/roles")}
          disabled={loading}
          className="w-full mt-4 text-gray-400 hover:text-white disabled:opacity-50 transition"
        >
          ← Change Role
        </button>

      </div>

    </div>
  );
}