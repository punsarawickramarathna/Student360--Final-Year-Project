// src/pages/Login.jsx

import React, { useState } from "react";
import { useNavigate } from "react-router-dom";

export default function Login() {

  const [identifier, setIdentifier] = useState("");
  const [password, setPassword] = useState("");

  const navigate = useNavigate();

  const handleLogin = async (e) => {

    e.preventDefault();

    if (!identifier || !password) {
      alert("Enter Student ID and Password");
      return;
    }

    try {

      const response = await fetch(
        "http://127.0.0.1:8000/login",
        {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
          },

          body: JSON.stringify({
            student_id: identifier,
            password: password,
          }),
        }
      );

      const data = await response.json();

      // login failed
      if (!response.ok) {
        alert(data.detail || "Login Failed");
        return;
      }

      // save token
      localStorage.setItem(
        "token",
        data.token
      );

      // save user
      localStorage.setItem(
        "user",
        JSON.stringify(data.user)
      );

      // get role from backend
      const role = data.user.role;

      // navigate by backend role
      if (role === "student") {

        navigate("/student/dashboard");

      } else if (role === "lecturer") {

        navigate("/lecturer/classroom");

      } else if (role === "admin") {

        navigate("/admin/dashboard");

      }

    } catch (err) {

      console.log(err);

      alert("Server Error");

    }
  };

  return (

    <div className="min-h-screen flex items-center justify-center px-4">

      <div className="max-w-md w-full">

        <div className="bg-[var(--card)] rounded-2xl p-8 shadow-2xl border border-[#123041]">

          <h2 className="text-2xl font-bold mb-1">
            Welcome Back
          </h2>

          <p className="text-[var(--muted)] mb-6">
            Login to Student360
          </p>

          <form
            onSubmit={handleLogin}
            className="space-y-4"
          >

            {/* STUDENT ID */}
            <div>

              <label className="text-sm text-[var(--muted)]">
                User ID
              </label>

              <input
                className="mt-1 w-full bg-[#071828] border border-[#122236] rounded-lg p-3 text-white"
                value={identifier}
                onChange={(e) =>
                  setIdentifier(e.target.value)
                }
                placeholder="Student / Lecturer / Admin ID"
              />

            </div>

            {/* PASSWORD */}
            <div>

              <label className="text-sm text-[var(--muted)]">
                Password
              </label>

              <input
                type="password"
                className="mt-1 w-full bg-[#071828] border border-[#122236] rounded-lg p-3 text-white"
                value={password}
                onChange={(e) =>
                  setPassword(e.target.value)
                }
                placeholder="Enter password"
              />

            </div>

            {/* BUTTON */}
            <button
              type="submit"
              className="w-full py-3 rounded-lg mt-2 text-lg font-semibold bg-gradient-to-r from-[var(--accent-from)] to-[var(--accent-to)]"
            >

              Sign in

            </button>

          </form>

          <p className="text-center text-sm text-[var(--muted)] mt-4">

            © Student360

          </p>

        </div>

      </div>

    </div>
  );
}