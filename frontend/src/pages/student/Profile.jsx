import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";

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

    const profileData = result.user || result;

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
      <div className="min-h-screen bg-[#020817] flex items-center justify-center">
        <div className="flex items-center gap-3 text-white">
          <div className="w-6 h-6 border-2 border-white/30 border-t-white rounded-full animate-spin" />

          <span>Loading profile...</span>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="min-h-screen bg-[#020817] flex items-center justify-center px-4">
        <div className="max-w-md w-full bg-[#0b2236] border border-red-500/30 rounded-2xl p-6 text-center">
          <h2 className="text-xl font-semibold text-white">
            Unable to Load Profile
          </h2>

          <p className="text-red-300 mt-3">
            {error}
          </p>

          <button
            onClick={loadProfile}
            className="mt-5 px-5 py-3 bg-blue-600 hover:bg-blue-700 text-white rounded-xl transition"
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
    <div className="min-h-screen bg-[#020817] text-white px-4 py-10">
      <div className="max-w-5xl mx-auto">

        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 mb-8">

          <div>
            <h1 className="text-3xl font-bold">
              My Profile
            </h1>

            <p className="text-gray-400 mt-1">
              View your personal and academic information
            </p>
          </div>

          <button
            onClick={() =>
              navigate("/student/dashboard")
            }
            className="px-4 py-2 bg-white/10 hover:bg-white/20 rounded-xl transition"
          >
            ← Dashboard
          </button>

        </div>

        <div className="grid lg:grid-cols-3 gap-6">

          <div className="bg-[#0b2236] border border-white/10 rounded-2xl p-6 h-fit">

            <div className="flex flex-col items-center text-center">

              {profile.photo ? (
                <img
                  src={getImageURL(profile.photo)}
                  alt="Profile"
                  className="w-36 h-36 rounded-full object-cover border-4 border-blue-500/40 shadow-xl"
                />
              ) : (
                <div className="w-36 h-36 rounded-full bg-gradient-to-br from-blue-500 to-purple-600 flex items-center justify-center text-5xl font-bold shadow-xl">
                  {profile.name
                    ? profile.name
                        .charAt(0)
                        .toUpperCase()
                    : "S"}
                </div>
              )}

              <h2 className="text-2xl font-bold mt-5">
                {profile.name || "Student"}
              </h2>

              <p className="text-blue-300 mt-1">
                {profile.student_id}
              </p>

              <span className="mt-4 px-4 py-1.5 rounded-full bg-green-500/10 border border-green-500/30 text-green-300 text-sm capitalize">
                {profile.account_status || "active"}
              </span>

            </div>

            <div className="mt-6 space-y-3">

              <button
                onClick={() =>
                  navigate("/student/edit-profile")
                }
                className="w-full py-3 rounded-xl bg-gradient-to-r from-blue-600 to-purple-600 hover:opacity-90 transition font-semibold"
              >
                Edit Profile
              </button>

              <button
                onClick={() =>
                  navigate("/student/change-password")
                }
                className="w-full py-3 rounded-xl bg-white/10 hover:bg-white/20 transition"
              >
                Change Password
              </button>

            </div>

          </div>

          <div className="lg:col-span-2 space-y-6">

            <section className="bg-[#0b2236] border border-white/10 rounded-2xl p-6">

              <h3 className="text-xl font-semibold mb-5">
                Academic Information
              </h3>

              <div className="grid md:grid-cols-2 gap-4">

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
                  value={profile.year}
                />

                <ProfileItem
                  label="Role"
                  value={profile.role}
                />

                <ProfileItem
                  label="Account Status"
                  value={profile.account_status}
                />

              </div>

            </section>

            <section className="bg-[#0b2236] border border-white/10 rounded-2xl p-6">

              <h3 className="text-xl font-semibold mb-5">
                Contact Information
              </h3>

              <div className="grid md:grid-cols-2 gap-4">

                <ProfileItem
                  label="Email Address"
                  value={profile.email}
                />

                <ProfileItem
                  label="Phone Number"
                  value={profile.phone}
                />

                <div className="md:col-span-2">
                  <ProfileItem
                    label="Address"
                    value={profile.address}
                  />
                </div>

              </div>

            </section>

            {profile.must_change_password && (
              <section className="bg-yellow-500/10 border border-yellow-500/30 rounded-2xl p-5">

                <h3 className="text-yellow-200 font-semibold">
                  Password Change Required
                </h3>

                <p className="text-yellow-100/70 mt-2">
                  Your account is using a temporary password.
                  Please create a new secure password.
                </p>

                <button
                  onClick={() =>
                    navigate(
                      "/student/change-password"
                    )
                  }
                  className="mt-4 px-5 py-2.5 bg-yellow-500 text-black rounded-xl font-semibold hover:bg-yellow-400 transition"
                >
                  Change Password
                </button>

              </section>
            )}

          </div>

        </div>

      </div>
    </div>
  );
}

function ProfileItem({ label, value }) {
  return (
    <div className="bg-[#071828] border border-white/10 rounded-xl p-4">
      <p className="text-sm text-gray-400">
        {label}
      </p>

      <p className="text-white font-medium mt-2 break-words capitalize">
        {value || "Not provided"}
      </p>
    </div>
  );
}