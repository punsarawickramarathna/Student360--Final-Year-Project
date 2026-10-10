// src/pages/student/Profile.jsx

import React, { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";

import Navbar from "../../components/Navbar";

import {
  getMyProfile,
  getImageURL,
} from "../../api/api";

export default function Profile() {
  const navigate = useNavigate();

  const [profile, setProfile] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    loadProfile();
  }, []);

  const loadProfile = async () => {
    try {
      setLoading(true);
      setError("");

      const result = await getMyProfile();
      const profileData =
        result?.user ||
        result?.student ||
        result?.data?.user ||
        result?.data?.student ||
        result?.data ||
        result ||
        {};

      setProfile(profileData);

      const oldUser = JSON.parse(
        localStorage.getItem("user") || "{}"
      );

      localStorage.setItem(
        "user",
        JSON.stringify({
          ...oldUser,
          ...profileData,
          role:
            profileData.role ||
            oldUser.role ||
            "student",
        })
      );
    } catch (err) {
      console.error("Profile load error:", err);

      setError(
        err?.response?.data?.detail ||
        err?.message ||
        "Unable to load profile."
      );
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-[#030c18] flex items-center justify-center text-white">
        <div className="flex items-center gap-3 bg-[#081526] border border-slate-800 px-6 py-4 rounded-2xl shadow-xl">
          <div className="w-5 h-5 border-2 border-slate-600 border-t-blue-500 rounded-full animate-spin" />
          <span className="font-semibold text-sm text-slate-300">Loading student profile...</span>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="min-h-screen bg-[#030c18] flex items-center justify-center px-4">
        <div className="max-w-md w-full bg-[#081526] border border-rose-500/30 shadow-2xl rounded-2xl p-6 text-center text-white">
          <div className="text-4xl mb-2">⚠️</div>
          <h2 className="text-lg font-bold">Unable to Load Profile</h2>
          <p className="text-rose-400 text-sm mt-2">{error}</p>
          <button
            onClick={loadProfile}
            className="mt-5 px-5 py-2.5 bg-blue-600 hover:bg-blue-700 text-white font-semibold rounded-xl text-sm transition"
          >
            Try Again
          </button>
        </div>
      </div>
    );
  }

  if (!profile) {
    return null;
  }

  return (
    <div className="min-h-screen bg-[#030c18] text-slate-100 selection:bg-blue-600 selection:text-white pb-14">
      <Navbar />

      <main className="max-w-5xl mx-auto px-4 sm:px-6 pt-7 space-y-6">

        {/* Top Header Card */}
        <section className="bg-[#081526] border border-slate-800 rounded-2xl p-6 shadow-xl relative overflow-hidden">
          <div className="absolute top-0 right-10 w-64 h-32 bg-blue-500/10 rounded-full blur-3xl pointer-events-none" />

          <div className="relative z-10">
            <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-blue-500/10 border border-blue-500/20 mb-2">
              <span className="w-1.5 h-1.5 rounded-full bg-blue-400 animate-pulse" />
              <span className="text-xs font-bold uppercase tracking-wider text-blue-400">
                Account Verification
              </span>
            </div>
            <h1 className="text-2xl sm:text-3xl font-black tracking-tight text-white">
              Student <span className="bg-gradient-to-r from-blue-400 via-sky-300 to-teal-300 bg-clip-text text-transparent">Profile</span>
            </h1>
            <p className="text-xs text-slate-400 mt-1">
              Verified personal, institutional and academic credentials
            </p>
          </div>
        </section>

        {/* Profile Content Grid */}
        <div className="grid lg:grid-cols-3 gap-6">

          {/* Left Avatar / Account Status Card */}
          <div className="bg-[#081526] border border-slate-800 rounded-2xl p-6 shadow-xl h-fit">
            <div className="flex flex-col items-center text-center">
              {profile.photo ? (
                <img
                  src={getImageURL(profile.photo)}
                  alt="Profile"
                  className="w-32 h-32 rounded-full object-cover border-4 border-slate-800 shadow-2xl"
                />
              ) : (
                <div className="w-32 h-32 rounded-full bg-gradient-to-br from-blue-600 via-indigo-600 to-purple-700 flex items-center justify-center text-4xl font-black text-white shadow-xl shadow-blue-900/30">
                  {profile.name
                    ? profile.name.charAt(0).toUpperCase()
                    : "S"}
                </div>
              )}

              <h2 className="text-xl font-black text-white mt-4 tracking-tight">
                {profile.name || "Student"}
              </h2>

              <p className="text-xs font-mono font-semibold text-sky-400 bg-slate-900 px-3 py-1 rounded-md border border-slate-800 mt-2">
                {profile.student_id}
              </p>

              <span className="mt-3 px-3 py-1 rounded-full bg-emerald-950/60 border border-emerald-500/30 text-emerald-400 text-xs font-bold capitalize">
                ● {profile.account_status || "Active Student"}
              </span>
            </div>

            <div className="mt-6 space-y-2.5 pt-5 border-t border-slate-800">
              <button
                onClick={() => navigate("/student/edit-profile")}
                className="w-full py-2.5 rounded-xl bg-blue-600 hover:bg-blue-700 text-white font-bold text-xs shadow-lg shadow-blue-600/30 hover:scale-[1.01] active:scale-[0.99] transition"
              >
                Edit Profile
              </button>

              <button
                onClick={() => navigate("/student/change-password")}
                className="w-full py-2.5 rounded-xl bg-slate-900 hover:bg-slate-800 border border-slate-700 text-slate-300 font-semibold text-xs transition"
              >
                Change Password
              </button>
            </div>
          </div>

          {/* Right Academic & Contact Sections */}
          <div className="lg:col-span-2 space-y-6">

            {/* Academic Information */}
            <section className="bg-[#081526] border border-slate-800 rounded-2xl p-6 shadow-xl">
              <div className="flex items-center gap-2 mb-4 pb-3 border-b border-slate-800">
                <span className="text-lg">🎓</span>
                <h3 className="text-xs font-bold uppercase tracking-wider text-slate-300">
                  Academic Credentials
                </h3>
              </div>

              <div className="grid md:grid-cols-2 gap-3.5">
                <ProfileItem
                  label="Student ID"
                  value={profile.student_id}
                />
                <ProfileItem
                  label="Intake"
                  value={profile.intake}
                />
                <ProfileItem
                  label="Department"
                  value={profile.department}
                />
                <ProfileItem
                  label="Academic Year"
                  value={
                    profile.academic_year ||
                    profile.year ||
                    profile.academic_details?.academic_year ||
                    profile.academic_details?.year ||
                    "Not Provided"
                  }
                />
                <ProfileItem
                  label="Semester"
                  value={
                    profile.semester ||
                    profile.sem ||
                    profile.current_semester ||
                    profile.academic_details?.semester ||
                    profile.academic_details?.sem ||
                    "Not Provided"
                  }
                />
                <ProfileItem
                  label="Group"
                  value={
                    profile.group ||
                    profile.student_group ||
                    profile.batch_group ||
                    profile.batch ||
                    profile.academic_details?.group ||
                    "Not Provided"
                  }
                />
                <ProfileItem
                  label="Enrolled Role"
                  value={profile.role}
                />
                <ProfileItem
                  label="Status"
                  value={profile.account_status}
                />
              </div>
            </section>

            {/* Contact Information */}
            <section className="bg-[#081526] border border-slate-800 rounded-2xl p-6 shadow-xl">
              <div className="flex items-center gap-2 mb-4 pb-3 border-b border-slate-800">
                <span className="text-lg">📬</span>
                <h3 className="text-xs font-bold uppercase tracking-wider text-slate-300">
                  Contact Information
                </h3>
              </div>

              <div className="grid md:grid-cols-2 gap-3.5">
                <ProfileItem
                  label="Campus Email Address"
                  value={profile.email}
                />
                <ProfileItem
                  label="Phone Number"
                  value={profile.phone}
                />
                <div className="md:col-span-2">
                  <ProfileItem
                    label="Registered Address"
                    value={profile.address}
                  />
                </div>
              </div>
            </section>

            {/* Password Change Alert */}
            {profile.must_change_password && (
              <section className="bg-amber-950/40 border border-amber-500/30 rounded-2xl p-5 shadow-xl">
                <div className="flex items-start gap-3">
                  <span className="text-2xl">⚠️</span>
                  <div>
                    <h3 className="text-amber-400 font-bold text-sm">
                      Password Change Required
                    </h3>
                    <p className="text-slate-300 text-xs mt-1 leading-relaxed">
                      Your account is currently using a temporary system password.
                      Please create a new secure password to safeguard your credentials.
                    </p>
                    <button
                      onClick={() => navigate("/student/change-password")}
                      className="mt-3 px-4 py-2 bg-amber-600 hover:bg-amber-700 text-white rounded-xl text-xs font-bold shadow-md transition"
                    >
                      Change Password
                    </button>
                  </div>
                </div>
              </section>
            )}

          </div>

        </div>

      </main>
    </div>
  );
}

function ProfileItem({ label, value }) {
  return (
    <div className="bg-[#0c1a2c] border border-slate-800 rounded-xl p-3.5">
      <p className="text-[11px] font-bold uppercase tracking-wider text-slate-400">
        {label}
      </p>
      <p className="text-white font-semibold text-sm mt-1 break-words capitalize">
        {value || "Not Provided"}
      </p>
    </div>
  );
}