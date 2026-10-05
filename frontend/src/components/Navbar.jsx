// src/components/Navbar.jsx

import React from "react";
import { Link, useNavigate, useLocation } from "react-router-dom";

export default function Navbar() {
  const navigate = useNavigate();
  const location = useLocation();

  const user = (() => {
    try {
      return JSON.parse(localStorage.getItem("user")) || {};
    } catch {
      return {};
    }
  })();

  const role = String(user?.role || localStorage.getItem("selectedRole") || "student").toLowerCase();
  const isAdmin = role === "admin";
  const isLecturer = role === "lecturer" || role === "faculty";

  const handleLogout = () => {
    localStorage.removeItem("token");
    localStorage.removeItem("user");
    localStorage.removeItem("classroom");
    localStorage.removeItem("selectedRole");
    navigate("/login");
  };

  const isActive = (path) => location.pathname === path;

  return (
    <header className="bg-slate-200/90 border-b border-slate-300/80 sticky top-0 z-50 transition-all shadow-sm">
      <div className="max-w-[1600px] mx-auto px-4 sm:px-6 h-16 flex items-center justify-between">

        {/* Brand Logo & Title */}
        <div className="flex items-center gap-6">
          <Link
            to={
              isAdmin
                ? "/admin/dashboard"
                : isLecturer
                  ? "/lecturer/dashboard"
                  : "/student/dashboard"
            }
            className="flex items-center gap-3.5 group"
          >
            <img
              src="/assets/horizon-logo.png"
              alt="Horizon Logo"
              className="h-10 w-auto object-contain shrink-0 transition-transform group-hover:scale-105"
              onError={(e) => {
                e.currentTarget.style.display = "none";
              }}
            />
            <span className="text-xl font-black tracking-tight text-slate-900 leading-none">
              Student<span className="text-blue-600">360</span>
            </span>
          </Link>

          {/* Navigation Links */}
          <nav className="hidden md:flex items-center gap-1.5 text-sm font-semibold">
            {isAdmin ? (
              <>
                <Link
                  to="/admin/dashboard"
                  className={`px-3.5 py-1.5 rounded-lg transition ${isActive("/admin/dashboard")
                      ? "text-blue-600 bg-white shadow-xs"
                      : "text-slate-600 hover:text-slate-900 hover:bg-slate-300/50"
                    }`}
                >
                  Dashboard Overview
                </Link>
                <Link
                  to="/admin/users"
                  className={`px-3.5 py-1.5 rounded-lg transition ${isActive("/admin/users")
                      ? "text-blue-600 bg-white shadow-xs"
                      : "text-slate-600 hover:text-slate-900 hover:bg-slate-300/50"
                    }`}
                >
                  User Management
                </Link>
              </>
            ) : isLecturer ? (
              <>
                <Link
                  to="/lecturer/dashboard"
                  className={`px-3.5 py-1.5 rounded-lg transition ${isActive("/lecturer/dashboard")
                      ? "text-blue-600 bg-white shadow-xs"
                      : "text-slate-600 hover:text-slate-900 hover:bg-slate-300/50"
                    }`}
                >
                  Class Analytics
                </Link>
              </>
            ) : (
              <>
                <Link
                  to="/student/dashboard"
                  className={`px-3.5 py-1.5 rounded-lg transition ${isActive("/student/dashboard")
                      ? "text-blue-600 bg-white shadow-xs"
                      : "text-slate-600 hover:text-slate-900 hover:bg-slate-300/50"
                    }`}
                >
                  Dashboard
                </Link>
                <Link
                  to="/student/appeals"
                  className={`px-3.5 py-1.5 rounded-lg transition ${isActive("/student/appeals")
                      ? "text-blue-600 bg-white shadow-xs"
                      : "text-slate-600 hover:text-slate-900 hover:bg-slate-300/50"
                    }`}
                >
                  My Appeals
                </Link>
                <Link
                  to="/student/profile"
                  className={`px-3.5 py-1.5 rounded-lg transition ${isActive("/student/profile")
                      ? "text-blue-600 bg-white shadow-xs"
                      : "text-slate-600 hover:text-slate-900 hover:bg-slate-300/50"
                    }`}
                >
                  Profile
                </Link>
              </>
            )}
          </nav>
        </div>

        {/* Right Actions: Clean Tag & Sign Out */}
        <div className="flex items-center gap-3">
          <span className="hidden sm:inline-block text-[11px] font-bold uppercase tracking-wider bg-slate-100 text-slate-700 border border-slate-300 px-2.5 py-0.5 rounded-full">
            {isAdmin ? "Admin" : isLecturer ? "LECTURER" : "Student"}
          </span>

          <button
            onClick={handleLogout}
            className="px-3.5 py-1.5 rounded-lg border border-slate-300 hover:border-rose-300 text-slate-700 hover:text-rose-600 hover:bg-rose-50 text-xs font-semibold transition shadow-xs"
          >
            Sign out
          </button>
        </div>

      </div>
    </header>
  );
}