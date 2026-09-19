import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { changePassword } from "../../api/api";

export default function ChangePassword() {
  const navigate = useNavigate();

  const [currentPassword, setCurrentPassword] =
    useState("");

  const [newPassword, setNewPassword] =
    useState("");

  const [confirmPassword, setConfirmPassword] =
    useState("");

  const [showCurrent, setShowCurrent] =
    useState(false);

  const [showNew, setShowNew] =
    useState(false);

  const [showConfirm, setShowConfirm] =
    useState(false);

  const [loading, setLoading] =
    useState(false);

  const [error, setError] =
    useState("");

  const [message, setMessage] =
    useState("");

  const handleChangePassword = async () => {
    setError("");
    setMessage("");

    if (
      !currentPassword ||
      !newPassword ||
      !confirmPassword
    ) {
      setError("Please complete all password fields.");
      return;
    }

    if (newPassword.length < 8) {
      setError(
        "New password must contain at least 8 characters."
      );
      return;
    }

    if (!/[A-Z]/.test(newPassword)) {
      setError(
        "New password must contain an uppercase letter."
      );
      return;
    }

    if (!/[a-z]/.test(newPassword)) {
      setError(
        "New password must contain a lowercase letter."
      );
      return;
    }

    if (!/[0-9]/.test(newPassword)) {
      setError(
        "New password must contain a number."
      );
      return;
    }

    if (newPassword !== confirmPassword) {
      setError(
        "New password and confirm password do not match."
      );
      return;
    }

    if (currentPassword === newPassword) {
      setError(
        "New password must be different from the current password."
      );
      return;
    }

    try {
      setLoading(true);

      const result = await changePassword({
        current_password: currentPassword,
        new_password: newPassword,
      });

      setMessage(
        result.message ||
          "Password changed successfully."
      );

      const oldUser = JSON.parse(
        localStorage.getItem("user") || "{}"
      );

      localStorage.setItem(
        "user",
        JSON.stringify({
          ...oldUser,
          must_change_password: false,
        })
      );

      setCurrentPassword("");
      setNewPassword("");
      setConfirmPassword("");

      setTimeout(() => {
        navigate("/student/profile");
      }, 1500);
    } catch (err) {
      console.error(
        "Password change error:",
        err
      );

      setError(
        err?.response?.data?.detail ||
          err?.message ||
          "Password change failed."
      );
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-[#020817] text-white px-4 py-10">
      <div className="max-w-lg mx-auto">

        <div className="flex items-center justify-between mb-8">
          <div>
            <h1 className="text-3xl font-bold">
              Change Password
            </h1>

            <p className="text-gray-400 mt-1">
              Create a secure password for your account
            </p>
          </div>

          <button
            onClick={() =>
              navigate("/student/profile")
            }
            className="px-4 py-2 bg-white/10 hover:bg-white/20 rounded-xl transition"
          >
            ← Back
          </button>
        </div>

        <div className="bg-[#0b2236] border border-white/10 rounded-2xl p-7">

          {message && (
            <div className="mb-5 p-4 bg-green-500/10 border border-green-500/30 text-green-300 rounded-xl">
              {message}
            </div>
          )}

          {error && (
            <div className="mb-5 p-4 bg-red-500/10 border border-red-500/30 text-red-300 rounded-xl">
              {error}
            </div>
          )}

          <PasswordField
            label="Current Password"
            value={currentPassword}
            setValue={setCurrentPassword}
            visible={showCurrent}
            setVisible={setShowCurrent}
          />

          <PasswordField
            label="New Password"
            value={newPassword}
            setValue={setNewPassword}
            visible={showNew}
            setVisible={setShowNew}
          />

          <PasswordField
            label="Confirm New Password"
            value={confirmPassword}
            setValue={setConfirmPassword}
            visible={showConfirm}
            setVisible={setShowConfirm}
          />

          <div className="bg-[#071828] border border-white/10 rounded-xl p-4 mb-6">
            <p className="text-sm font-semibold text-gray-200">
              Password requirements
            </p>

            <p className="text-sm text-gray-400 mt-2">
              At least 8 characters, one uppercase
              letter, one lowercase letter and one
              number.
            </p>
          </div>

          <button
            onClick={handleChangePassword}
            disabled={loading}
            className="w-full py-3 rounded-xl bg-gradient-to-r from-blue-600 to-purple-600 hover:opacity-90 disabled:opacity-50 disabled:cursor-not-allowed font-semibold transition"
          >
            {loading
              ? "Changing Password..."
              : "Change Password"}
          </button>

        </div>
      </div>
    </div>
  );
}

function PasswordField({
  label,
  value,
  setValue,
  visible,
  setVisible,
}) {
  return (
    <div className="mb-5">
      <label className="block text-sm text-gray-300 mb-2">
        {label}
      </label>

      <div className="relative">
        <input
          type={visible ? "text" : "password"}
          value={value}
          onChange={(event) =>
            setValue(event.target.value)
          }
          className="w-full p-3 pr-20 rounded-xl bg-[#071828] border border-white/10 text-white outline-none focus:border-blue-500"
          placeholder={`Enter ${label.toLowerCase()}`}
        />

        <button
          type="button"
          onClick={() =>
            setVisible(!visible)
          }
          className="absolute right-3 top-1/2 -translate-y-1/2 text-sm text-blue-300 hover:text-blue-200"
        >
          {visible ? "Hide" : "Show"}
        </button>
      </div>
    </div>
  );
}