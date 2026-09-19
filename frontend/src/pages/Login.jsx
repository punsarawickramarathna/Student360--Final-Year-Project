import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { loginUser } from "../api/api";

export default function Login() {
  const navigate = useNavigate();

  const selectedRole =
    localStorage.getItem("selectedRole") || "student";

  const [studentId, setStudentId] = useState("");
  const [password, setPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);

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

        {/* Password input with SVG Eye Toggle */}
        <div className="mb-4">

          <label className="block text-sm text-gray-300 mb-2">
            Password
          </label>

          <div className="relative">
            <input
              type={showPassword ? "text" : "password"}
              placeholder="Enter your password"
              className="w-full p-3 pr-10 rounded-xl bg-[#071828] border border-white/10 text-white outline-none focus:border-blue-500 transition"
              value={password}
              onChange={(event) =>
                setPassword(event.target.value)
              }
              onKeyDown={handleKeyDown}
              autoComplete="current-password"
            />

            <button
              type="button"
              onClick={() => setShowPassword((prev) => !prev)}
              className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-400 hover:text-white transition"
            >
              {showPassword ? (
                <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M13.875 18.825A10.05 10.05 0 0112 19c-4.478 0-8.268-2.943-9.543-7a9.97 9.97 0 011.563-3.029m5.858-5.908a8.959 8.959 0 013.682-.793c4.478 0 8.268 2.943 9.542 7a10.025 10.025 0 01-4.132 5.411m0 0L21 21M3 3l18 18" />
                </svg>
              ) : (
                <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z" />
                </svg>
              )}
            </button>
          </div>

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