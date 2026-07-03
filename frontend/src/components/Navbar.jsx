// src/components/Navbar.jsx
import React from "react";
import { Link, useNavigate } from "react-router-dom";

export default function Navbar() {
  const navigate = useNavigate();
  const userJson = localStorage.getItem("user");
  const user = userJson ? JSON.parse(userJson) : null;
  const role = user?.role || "student";

  function signOut() {
    localStorage.removeItem("token");
    localStorage.removeItem("user");
    navigate("/login");
  }

  return (
    <div className="w-full bg-[#071829] border-b border-[#122236]">
      <div className="max-w-6xl mx-auto px-6 py-4 flex items-center justify-between">
        <div className="flex items-center gap-4">
          <Link
            to={role === "student" ? "/student/dashboard" : role === "lecturer" ? "/lecturer/dashboard" : "/admin/dashboard"}
            className="text-2xl font-bold text-white"
          >
            Student360
          </Link>

          {/* role-specific nav links */}
          <div className="hidden md:flex items-center gap-4 text-sm">
            {role === "student" && (
              <>
                <Link to="/student/dashboard" className="nav-link">Dashboard</Link>
                <Link to="/student/appeals" className="nav-link">My Appeals</Link>
                <Link to="/student/profile" className="nav-link">Profile</Link>
              </>
            )}

            {role === "lecturer" && (
              <>
                <Link to="/lecturer/dashboard" className="nav-link">Lecturer</Link>
                <Link to="/lecturer/classes" className="nav-link">Classes</Link>
              </>
            )}

            {role === "admin" && (
              <>
                <Link to="/admin/dashboard" className="nav-link">Admin</Link>
                <Link to="/admin/users" className="nav-link">Users</Link>
              </>
            )}
          </div>
        </div>

        <div className="flex items-center gap-4">
          {user && (
            <div className="text-right mr-2 hidden sm:block">
              <div className="text-sm text-gray-300">Hello</div>
              <div className="font-semibold text-white">{user.name}</div>
              <div className="text-xs text-[var(--muted)]">{user.regNo}</div>
            </div>
          )}

          <button
            onClick={signOut}
            className="px-3 py-1 text-sm rounded-md bg-gradient-to-r from-[var(--accent-from)] to-[var(--accent-to)] shadow-md hover:scale-105 transition-transform"
          >
            Sign out
          </button>
        </div>
      </div>

      {/* small CSS-in-Tailwind nav link style (applies to .nav-link) */}
      <style>{`
        .nav-link {
          color: #cfe6ff;
          padding: 6px 10px;
          border-radius: 8px;
          transition: background 0.18s, transform 0.12s;
        }
        .nav-link:hover {
          background: rgba(255,255,255,0.03);
          transform: translateY(-2px);
        }
      `}</style>
    </div>
  );
}
