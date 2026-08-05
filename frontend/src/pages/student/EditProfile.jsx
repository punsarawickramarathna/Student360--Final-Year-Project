import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";

import {
  getMyProfile,
  updateMyProfile,
  uploadProfileImage,
  deleteProfileImage,
  getImageURL,
} from "../../api/api";

export default function EditProfile() {
  const navigate = useNavigate();

  const [name, setName] = useState("");
  const [studentId, setStudentId] = useState("");
  const [intake, setIntake] = useState("");
  const [department, setDepartment] = useState("");
  const [year, setYear] = useState("");
  const [email, setEmail] = useState("");
  const [phone, setPhone] = useState("");
  const [address, setAddress] = useState("");
  const [photo, setPhoto] = useState("");

  const [selectedFile, setSelectedFile] = useState(null);

  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [uploading, setUploading] = useState(false);

  const [message, setMessage] = useState("");
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

    setName(profileData.name || "");
    setStudentId(profileData.student_id || "");
    setIntake(profileData.intake || "");
    setDepartment(profileData.department || "");
    setYear(profileData.year || "");
    setEmail(profileData.email || "");
    setPhone(profileData.phone || "");
    setAddress(profileData.address || "");
    setPhoto(profileData.photo || "");

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

  const handleUpdate = async () => {
  try {
    setSaving(true);
    setMessage("");
    setError("");

    const result = await updateMyProfile({
      name,
      department,
      year,
      email,
      phone,
      address,
    });

    const updatedProfile = result.user || result;

    setName(updatedProfile.name || name);
    setDepartment(
      updatedProfile.department || department
    );
    setYear(updatedProfile.year || year);
    setEmail(updatedProfile.email || email);
    setPhone(updatedProfile.phone || phone);
    setAddress(updatedProfile.address || address);

    const oldUser = JSON.parse(
      localStorage.getItem("user") || "{}"
    );

    localStorage.setItem(
      "user",
      JSON.stringify({
        ...oldUser,
        ...updatedProfile,
        role:
          updatedProfile.role ||
          oldUser.role ||
          "student",
      })
    );

    setMessage("Profile updated successfully.");

    setTimeout(() => {
      navigate("/student/profile");
    }, 1000);
  } catch (err) {
    console.error("Profile update error:", err);

    setError(
      err?.response?.data?.detail ||
        err?.message ||
        "Profile update failed."
    );
  } finally {
    setSaving(false);
  }
};

  const handlePhotoUpload = async () => {
  if (!selectedFile) {
    setError("Please select an image.");
    return;
  }

  try {
    setUploading(true);
    setMessage("");
    setError("");

    const result = await uploadProfileImage(
      selectedFile
    );

    const uploadedPhoto =
      result.user?.photo ||
      result.photo ||
      result.file_path ||
      "";

    setPhoto(uploadedPhoto);

    const oldUser = JSON.parse(
      localStorage.getItem("user") || "{}"
    );

    const updatedUser = {
      ...oldUser,
      ...(result.user || {}),
      photo: uploadedPhoto,
      role:
        result.user?.role ||
        oldUser.role ||
        "student",
    };

    localStorage.setItem(
      "user",
      JSON.stringify(updatedUser)
    );

    setSelectedFile(null);
    setMessage("Profile photo uploaded successfully.");

    await loadProfile();
  } catch (err) {
    console.error("Photo upload error:", err);

    setError(
      err?.response?.data?.detail ||
        err?.message ||
        "Photo upload failed."
    );
  } finally {
    setUploading(false);
  }
};

  const handleDeletePhoto = async () => {
    try {
      setUploading(true);
      setMessage("");
      setError("");

      const result = await deleteProfileImage();

      setPhoto("");

      if (result.user) {
        localStorage.setItem(
          "user",
          JSON.stringify(result.user)
        );
      } else {
        await loadProfile();
      }

      setMessage("Profile photo removed successfully.");
    } catch (err) {
      setError(
        err?.response?.data?.detail ||
          err?.message ||
          "Unable to remove profile photo."
      );
    } finally {
      setUploading(false);
    }
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-[#020817] flex items-center justify-center">
        <div className="text-white text-lg">
          Loading profile...
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-[#020817] text-white px-4 py-10">
      <div className="max-w-4xl mx-auto">

        <div className="flex items-center justify-between mb-8">
          <div>
            <h1 className="text-3xl font-bold">
              Edit Profile
            </h1>

            <p className="text-gray-400 mt-1">
              Update your personal information and profile photo
            </p>
          </div>

          <button
            onClick={() => navigate(-1)}
            className="px-4 py-2 bg-white/10 hover:bg-white/20 rounded-xl transition"
          >
            ← Back
          </button>
        </div>

        {message && (
          <div className="mb-5 p-4 rounded-xl bg-green-500/10 border border-green-500/30 text-green-300">
            {message}
          </div>
        )}

        {error && (
          <div className="mb-5 p-4 rounded-xl bg-red-500/10 border border-red-500/30 text-red-300">
            {error}
          </div>
        )}

        <div className="grid lg:grid-cols-3 gap-6">

          {/* Profile Photo */}
          <div className="bg-[#0b2236] border border-white/10 rounded-2xl p-6 h-fit">
            <h2 className="text-xl font-semibold mb-5">
              Profile Photo
            </h2>

            <div className="flex justify-center mb-5">
              {photo ? (
                <img
                  src={getImageURL(photo)}
                  alt="Profile"
                  className="w-36 h-36 rounded-full object-cover border-4 border-blue-500/40"
                />
              ) : (
                <div className="w-36 h-36 rounded-full bg-gradient-to-br from-blue-500 to-purple-600 flex items-center justify-center text-5xl font-bold">
                  {name
                    ? name.charAt(0).toUpperCase()
                    : "S"}
                </div>
              )}
            </div>

            <input
              type="file"
              accept="image/jpeg,image/png,image/webp"
              onChange={(event) =>
                setSelectedFile(event.target.files[0])
              }
              className="w-full text-sm text-gray-300 mb-4 file:mr-3 file:py-2 file:px-4 file:rounded-lg file:border-0 file:bg-blue-600 file:text-white"
            />

            <button
              onClick={handlePhotoUpload}
              disabled={uploading || !selectedFile}
              className="w-full py-3 rounded-xl bg-blue-600 hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed transition"
            >
              {uploading
                ? "Uploading..."
                : "Upload Photo"}
            </button>

            {photo && (
              <button
                onClick={handleDeletePhoto}
                disabled={uploading}
                className="w-full mt-3 py-3 rounded-xl bg-red-500/10 border border-red-500/30 text-red-300 hover:bg-red-500/20 disabled:opacity-50 transition"
              >
                Remove Photo
              </button>
            )}
          </div>

          {/* Profile Form */}
          <div className="lg:col-span-2 bg-[#0b2236] border border-white/10 rounded-2xl p-6">
            <h2 className="text-xl font-semibold mb-6">
              Personal Information
            </h2>

            <div className="grid md:grid-cols-2 gap-5">

              <InputField
                label="Student ID"
                value={studentId}
                disabled
              />

              <InputField
                label="Intake"
                value={intake}
                disabled
              />

              <InputField
                label="Full Name"
                value={name}
                onChange={setName}
              />

              <InputField
                label="Department"
                value={department}
                onChange={setDepartment}
                placeholder="Example: Information Technology"
              />

              <InputField
                label="Academic Year"
                value={year}
                onChange={setYear}
                placeholder="Example: Year 4"
              />

              <InputField
                label="Email"
                type="email"
                value={email}
                onChange={setEmail}
                placeholder="student@email.com"
              />

              <InputField
                label="Phone Number"
                value={phone}
                onChange={setPhone}
                placeholder="07XXXXXXXX"
              />

              <div className="md:col-span-2">
                <label className="block text-sm text-gray-300 mb-2">
                  Address
                </label>

                <textarea
                  value={address}
                  onChange={(event) =>
                    setAddress(event.target.value)
                  }
                  placeholder="Enter your address"
                  rows="4"
                  className="w-full p-3 rounded-xl bg-[#071828] border border-white/10 text-white outline-none focus:border-blue-500 resize-none"
                />
              </div>
            </div>

            <div className="flex flex-col sm:flex-row gap-3 mt-7">
              <button
                onClick={handleUpdate}
                disabled={saving}
                className="flex-1 py-3 rounded-xl bg-gradient-to-r from-blue-600 to-purple-600 hover:opacity-90 disabled:opacity-50 transition font-semibold"
              >
                {saving
                  ? "Saving..."
                  : "Save Changes"}
              </button>

              <button
                onClick={() =>
                  navigate("/student/change-password")
                }
                className="flex-1 py-3 rounded-xl bg-white/10 hover:bg-white/20 transition"
              >
                Change Password
              </button>
            </div>
          </div>

        </div>
      </div>
    </div>
  );
}

function InputField({
  label,
  value,
  onChange,
  type = "text",
  placeholder = "",
  disabled = false,
}) {
  return (
    <div>
      <label className="block text-sm text-gray-300 mb-2">
        {label}
      </label>

      <input
        type={type}
        value={value}
        placeholder={placeholder}
        disabled={disabled}
        onChange={(event) =>
          onChange && onChange(event.target.value)
        }
        className={`w-full p-3 rounded-xl border outline-none transition ${
          disabled
            ? "bg-white/5 border-white/5 text-gray-500 cursor-not-allowed"
            : "bg-[#071828] border-white/10 text-white focus:border-blue-500"
        }`}
      />
    </div>
  );
}