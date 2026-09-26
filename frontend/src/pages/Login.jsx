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
      return "Student Login";
    }

    if (selectedRole === "lecturer") {
      return "Lecturer Login";
    }

    if (selectedRole === "admin") {
      return "Admin Login";
    }

    return "Login";
  };

  return (
    <div
      className="relative min-h-screen w-full flex items-center justify-center bg-cover bg-center bg-no-repeat overflow-hidden px-4 py-8"
      style={{
        backgroundImage: `url('/assets/horizon-campus-bg.jpg')`,
      }}
    >
      {/* Light subtle overlay so background is visible clearly */}
      <div className="absolute inset-0 bg-black/15 backdrop-blur-[10px]"></div>

      {/* Portrait White Glassmorphism Card */}
      <div className="relative z-10 w-full max-w-[420px] p-8 sm:p-10 rounded-3xl bg-white/75 backdrop-blur-md border border-white/80 shadow-lg flex flex-col items-center">

        {/* Horizon Campus Logo Link */}
        <a
          href="https://horizoncampus.edu.lk/"
          target="_blank"
          rel="noopener noreferrer"
          className="transition-transform hover:scale-105 duration-200 cursor-pointer mb-3"
          title="Visit Horizon Campus"
        >
          <img
            src="/assets/horizon-logo.png"
            alt="Horizon Campus"
            className="h-20 w-auto object-contain drop-shadow-sm"
          />
        </a>

        {/* Header */}
        <h1 className="text-3xl font-black text-slate-900 tracking-tight">
          Student<span className="text-blue-600">360</span>
        </h1>

        <p className="text-xs sm:text-sm font-semibold text-slate-600 uppercase tracking-wider mt-1 mb-6">
          {getRoleTitle()}
        </p>

        {/* User ID Field */}
        <div className="w-full mb-4 text-left">
          <label className="block text-xs font-bold text-slate-700 uppercase tracking-wide mb-1.5">
            User ID
          </label>

          <input
            type="text"
            placeholder={
              selectedRole === "student"
                ? "Example: ITBIN-2211-0253"
                : "Enter your user ID"
            }
            className="w-full p-3.5 rounded-xl bg-white/80 border border-slate-300 text-slate-900 placeholder-slate-400 outline-none focus:border-blue-500 focus:ring-2 focus:ring-blue-500/20 focus:bg-white shadow-sm transition"
            value={studentId}
            onChange={(event) => setStudentId(event.target.value)}
            onKeyDown={handleKeyDown}
            autoComplete="username"
          />
        </div>

        {/* Password input with SVG Eye Toggle */}
        <div className="w-full mb-4 text-left">
          <label className="block text-xs font-bold text-slate-700 uppercase tracking-wide mb-1.5">
            Password
          </label>

          <div className="relative">
            <input
              type={showPassword ? "text" : "password"}
              placeholder="Enter your password"
              className="w-full p-3.5 pr-11 rounded-xl bg-white/80 border border-slate-300 text-slate-900 placeholder-slate-400 outline-none focus:border-blue-500 focus:ring-2 focus:ring-blue-500/20 focus:bg-white shadow-sm transition"
              value={password}
              onChange={(event) => setPassword(event.target.value)}
              onKeyDown={handleKeyDown}
              autoComplete="current-password"
            />

            <button
              type="button"
              onClick={() => setShowPassword((prev) => !prev)}
              className="absolute right-3.5 top-1/2 -translate-y-1/2 text-slate-400 hover:text-slate-700 transition"
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

        {/* Error Notification */}
        {error && (
          <div className="w-full bg-red-50 border border-red-200 text-red-600 rounded-xl p-3 mb-4 text-xs font-medium text-left">
            {error}
          </div>
        )}

        {/* Login Button */}
        <button
          onClick={login}
          disabled={loading}
          className="w-full bg-blue-600 hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed text-white py-3.5 rounded-xl font-bold shadow-md hover:shadow-lg transition flex items-center justify-center gap-2"
        >
          {loading && (
            <span className="w-5 h-5 border-2 border-white/40 border-t-white rounded-full animate-spin" />
          )}

          {loading ? "Signing In..." : "Login"}
        </button>

        {/* Back to Roles Button */}
        <button
          onClick={() => navigate("/roles")}
          disabled={loading}
          className="w-full mt-4 text-xs font-semibold text-slate-500 hover:text-blue-600 disabled:opacity-50 transition"
        >
          ← Change Role
        </button>

      </div>
    </div>
  );
}