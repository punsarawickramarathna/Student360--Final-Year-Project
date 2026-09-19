import React, { useState } from "react";
import axios from "axios";
import Navbar from "../../components/Navbar"; 

export default function AddUser() {
  // Tab State: 'student' or 'lecturer'
  const [activeTab, setActiveTab] = useState("student");

  // Student Form State
  const [studentData, setStudentData] = useState({
    student_id: "", name: "", email: "", department: "IT", intake: "", password: ""
  });
  const [videoFile, setVideoFile] = useState(null);
  const [videoPreview, setVideoPreview] = useState(null);

  // Lecturer Form State
  const [lecData, setLecData] = useState({
    lec_id: "", name: "", email: "", faculty: "Faculty of IT", gender: "Male", employment_type: "Permanent", subjects: "", password: ""
  });

  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState({ type: "", text: "" });

  // ==========================================
  // CLEAR FORMS FUNCTION
  // ==========================================
  const handleClear = () => {
    setStudentData({ student_id: "", name: "", email: "", department: "IT", intake: "", password: "" });
    setVideoFile(null);
    setVideoPreview(null);
    if (document.getElementById("videoInput")) document.getElementById("videoInput").value = "";
    
    setLecData({ lec_id: "", name: "", email: "", faculty: "Faculty of IT", gender: "Male", employment_type: "Permanent", subjects: "", password: "" });
    setMessage({ type: "", text: "" });
  };

  // ==========================================
  // STUDENT SUBMIT & VALIDATION
  // ==========================================
  const handleStudentSubmit = async (e) => {
    e.preventDefault();
    setMessage({ type: "", text: "" });

    if (!studentData.student_id || !studentData.name || !studentData.email || !studentData.intake || !studentData.password) {
      setMessage({ type: "error", text: "Please fill all required student fields!" });
      return;
    }
    if (!videoFile) {
      setMessage({ type: "error", text: "Please upload a facial training video for the student!" });
      return;
    }

    setLoading(true);
    try {
      const formData = new FormData();
      Object.keys(studentData).forEach((key) => formData.append(key, studentData[key]));
      formData.append("video", videoFile);

      const res = await axios.post("http://localhost:8000/api/admin/register-student", formData, {
        headers: { "Content-Type": "multipart/form-data" }
      });

      setMessage({ type: "success", text: res.data.message });
      setTimeout(() => {
        handleClear();
        window.location.reload(); // Auto refresh after success
      }, 1500);

    } catch (err) {
      setMessage({ type: "error", text: err.response?.data?.detail || "Error registering student!" });
    } finally {
      setLoading(false);
    }
  };

  // ==========================================
  // LECTURER SUBMIT & VALIDATION
  // ==========================================
  const handleLecturerSubmit = async (e) => {
    e.preventDefault();
    setMessage({ type: "", text: "" });

    if (!lecData.lec_id || !lecData.name || !lecData.email || !lecData.subjects || !lecData.password) {
      setMessage({ type: "error", text: "Please fill all required lecturer fields!" });
      return;
    }

    setLoading(true);
    try {
      const formData = new FormData();
      Object.keys(lecData).forEach((key) => formData.append(key, lecData[key]));

      const res = await axios.post("http://localhost:8000/api/admin/register-lecturer", formData);

      setMessage({ type: "success", text: res.data.message });
      setTimeout(() => {
        handleClear();
        window.location.reload(); // Auto refresh after success
      }, 1500);

    } catch (err) {
      setMessage({ type: "error", text: err.response?.data?.detail || "Error registering lecturer!" });
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-[#0b1120] text-gray-100 font-sans pb-12">
      <Navbar />

      {/* Header Bar with Subtle Gradient & Glow */}
      <div className="bg-gradient-to-r from-[#1e293b] via-[#0f172a] to-[#1e293b] border-b border-gray-800 py-8 px-6 mb-8 shadow-xl">
        <div className="max-w-4xl mx-auto flex flex-col md:flex-row justify-between items-center gap-4">
          <div>
            <h1 className="text-3xl font-extrabold text-transparent bg-clip-text bg-gradient-to-r from-blue-400 to-indigo-300 tracking-tight">
              User Management Portal
            </h1>
            <p className="text-sm text-gray-400 mt-1">
              Register new students with AI facial credentials or onboard academic lecturers.
            </p>
          </div>

          {/* Animated Tab Switcher Buttons */}
          <div className="flex bg-[#0f172a] p-1.5 rounded-2xl border border-gray-700 shadow-inner">
            <button
              type="button"
              onClick={() => { setActiveTab("student"); handleClear(); }}
              className={`flex items-center gap-2 px-6 py-2.5 rounded-xl font-bold text-sm transition-all duration-300 transform ${
                activeTab === "student"
                  ? "bg-gradient-to-r from-blue-600 to-indigo-600 text-white shadow-lg shadow-blue-500/25 scale-105"
                  : "text-gray-400 hover:text-white hover:bg-gray-800/50"
              }`}
            >
              👨‍🎓 Add Student
            </button>
            <button
              type="button"
              onClick={() => { setActiveTab("lecturer"); handleClear(); }}
              className={`flex items-center gap-2 px-6 py-2.5 rounded-xl font-bold text-sm transition-all duration-300 transform ${
                activeTab === "lecturer"
                  ? "bg-gradient-to-r from-purple-600 to-pink-600 text-white shadow-lg shadow-purple-500/25 scale-105"
                  : "text-gray-400 hover:text-white hover:bg-gray-800/50"
              }`}
            >
              👨‍🏫 Add Lecturer
            </button>
          </div>
        </div>
      </div>

      {/* Main Form Container */}
      <div className="max-w-4xl mx-auto px-6">
        <div className="bg-[#1e293b]/80 backdrop-blur-md rounded-3xl border border-gray-700/80 p-8 shadow-2xl transition-all duration-500">
          
          {/* Notification Alert */}
          {message.text && (
            <div className={`p-4 rounded-2xl mb-6 text-sm font-semibold flex items-center gap-3 animate-fade-in ${
              message.type === "success" ? "bg-green-500/10 text-green-400 border border-green-500/30" : "bg-red-500/10 text-red-400 border border-red-500/30"
            }`}>
              <span className="text-xl">{message.type === "success" ? "🎉" : "⚠️"}</span>
              {message.text}
            </div>
          )}

          {/* =========================================================
              TAB 1: STUDENT REGISTRATION FORM
             ========================================================= */}
          {activeTab === "student" && (
            <form onSubmit={handleStudentSubmit} className="space-y-6 animate-fade-in">
              <div className="border-b border-gray-700/60 pb-4 mb-2 flex justify-between items-center">
                <h3 className="text-lg font-bold text-blue-400 flex items-center gap-2">
                  <span>📘</span> Student Academic & AI Profile
                </h3>
                <span className="text-xs bg-blue-500/10 text-blue-300 px-3 py-1 rounded-full border border-blue-500/20">Student Portal</span>
              </div>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                <div>
                  <label className="block text-xs font-bold uppercase text-gray-300 mb-2">Student ID *</label>
                  <input
                    type="text" placeholder="ITBIN-2211-0320"
                    value={studentData.student_id}
                    onChange={(e) => setStudentData({ ...studentData, student_id: e.target.value })}
                    className="w-full bg-[#0f172a] border border-gray-600 rounded-xl px-4 py-3 text-sm focus:outline-none focus:border-blue-500 focus:ring-1 focus:ring-blue-500 transition"
                  />
                </div>
                <div>
                  <label className="block text-xs font-bold uppercase text-gray-300 mb-2">Full Name *</label>
                  <input
                    type="text" placeholder="Mithun Wijesinghe"
                    value={studentData.name}
                    onChange={(e) => setStudentData({ ...studentData, name: e.target.value })}
                    className="w-full bg-[#0f172a] border border-gray-600 rounded-xl px-4 py-3 text-sm focus:outline-none focus:border-blue-500 transition"
                  />
                </div>
              </div>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                <div>
                  <label className="block text-xs font-bold uppercase text-gray-300 mb-2">Email Address *</label>
                  <input
                    type="email" placeholder="student@horizoncampus.edu.lk"
                    value={studentData.email}
                    onChange={(e) => setStudentData({ ...studentData, email: e.target.value })}
                    className="w-full bg-[#0f172a] border border-gray-600 rounded-xl px-4 py-3 text-sm focus:outline-none focus:border-blue-500 transition"
                  />
                </div>
                <div>
                  <label className="block text-xs font-bold uppercase text-gray-300 mb-2">Department</label>
                  <select
                    value={studentData.department}
                    onChange={(e) => setStudentData({ ...studentData, department: e.target.value })}
                    className="w-full bg-[#0f172a] border border-gray-600 rounded-xl px-4 py-3 text-sm focus:outline-none focus:border-blue-500 transition"
                  >
                    <option value="IT">Faculty of IT</option>
                    <option value="Engineering">Faculty of Engineering</option>
                    <option value="Management">Faculty of Management</option>
                    <option value="Science">Faculty of Science</option>
                  </select>
                </div>
              </div>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                <div>
                  <label className="block text-xs font-bold uppercase text-gray-300 mb-2">Intake / Batch *</label>
                  <input
                    type="text" placeholder="Intake 11"
                    value={studentData.intake}
                    onChange={(e) => setStudentData({ ...studentData, intake: e.target.value })}
                    className="w-full bg-[#0f172a] border border-gray-600 rounded-xl px-4 py-3 text-sm focus:outline-none focus:border-blue-500 transition"
                  />
                </div>
                <div>
                  <label className="block text-xs font-bold uppercase text-gray-300 mb-2">Login Password *</label>
                  <input
                    type="password" placeholder="••••••••"
                    value={studentData.password}
                    onChange={(e) => setStudentData({ ...studentData, password: e.target.value })}
                    className="w-full bg-[#0f172a] border border-gray-600 rounded-xl px-4 py-3 text-sm focus:outline-none focus:border-blue-500 transition"
                  />
                </div>
              </div>

              {/* Video Upload Field */}
              <div className="pt-2">
                <label className="block text-xs font-bold uppercase text-gray-300 mb-2">
                  Facial Recognition Training Video * <span className="text-blue-400 font-normal lowercase">(10-20 sec MP4 showing head angles)</span>
                </label>
                <div className="border-2 border-dashed border-gray-600 bg-[#0f172a]/80 rounded-2xl p-6 text-center hover:border-blue-500 hover:bg-[#0f172a] transition duration-300 cursor-pointer relative group">
                  <input
                    id="videoInput" type="file" accept="video/mp4,video/quicktime"
                    onChange={(e) => {
                      const file = e.target.files[0];
                      if (file) { setVideoFile(file); setVideoPreview(URL.createObjectURL(file)); }
                    }}
                    className="absolute inset-0 w-full h-full opacity-0 cursor-pointer"
                  />
                  <div className="space-y-2">
                    <p className="text-sm font-semibold text-gray-300 group-hover:text-blue-400 transition">
                      {videoFile ? `📹 Selected: ${videoFile.name}` : "Click or Drag & Drop Facial Video Here"}
                    </p>
                    <p className="text-xs text-gray-500">MP4 or MOV formats only (Max 50MB)</p>
                  </div>
                </div>
                {videoPreview && (
                  <div className="mt-4">
                    <video src={videoPreview} controls className="w-full h-48 bg-black rounded-2xl border border-gray-700 shadow-inner" />
                  </div>
                )}
              </div>

              {/* Action Buttons */}
              <div className="flex gap-4 pt-4">
                <button
                  type="button" onClick={handleClear}
                  className="w-1/3 py-3.5 px-6 rounded-xl font-bold bg-gray-800 hover:bg-gray-700 text-gray-300 transition duration-200 border border-gray-600"
                >
                  🧹 Clear Form
                </button>
                <button
                  type="submit" disabled={loading}
                  className={`w-2/3 py-3.5 px-6 rounded-xl font-bold text-white shadow-lg transition duration-300 transform active:scale-98 ${
                    loading ? "bg-blue-600/50 cursor-not-allowed" : "bg-gradient-to-r from-blue-600 to-indigo-600 hover:from-blue-500 hover:to-indigo-500 shadow-blue-500/25 hover:shadow-blue-500/40"
                  }`}
                >
                  {loading ? "Registering Student & Uploading..." : "🚀 Register Student"}
                </button>
              </div>
            </form>
          )}

          {/* =========================================================
              TAB 2: LECTURER REGISTRATION FORM
             ========================================================= */}
          {activeTab === "lecturer" && (
            <form onSubmit={handleLecturerSubmit} className="space-y-6 animate-fade-in">
              <div className="border-b border-gray-700/60 pb-4 mb-2 flex justify-between items-center">
                <h3 className="text-lg font-bold text-purple-400 flex items-center gap-2">
                  <span>💼</span> Lecturer Professional Profile
                </h3>
                <span className="text-xs bg-purple-500/10 text-purple-300 px-3 py-1 rounded-full border border-purple-500/20">Academic Portal</span>
              </div>

              <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                <div>
                  <label className="block text-xs font-bold uppercase text-gray-300 mb-2">Lecturer ID *</label>
                  <input
                    type="text" placeholder="LEC001"
                    value={lecData.lec_id}
                    onChange={(e) => setLecData({ ...lecData, lec_id: e.target.value })}
                    className="w-full bg-[#0f172a] border border-gray-600 rounded-xl px-4 py-3 text-sm focus:outline-none focus:border-purple-500 transition"
                  />
                </div>
                <div className="md:col-span-2">
                  <label className="block text-xs font-bold uppercase text-gray-300 mb-2">Full Name with Title *</label>
                  <input
                    type="text" placeholder="Dr. Silva / Mr. Asanka Dinesh"
                    value={lecData.name}
                    onChange={(e) => setLecData({ ...lecData, name: e.target.value })}
                    className="w-full bg-[#0f172a] border border-gray-600 rounded-xl px-4 py-3 text-sm focus:outline-none focus:border-purple-500 transition"
                  />
                </div>
              </div>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                <div>
                  <label className="block text-xs font-bold uppercase text-gray-300 mb-2">Email Address *</label>
                  <input
                    type="email" placeholder="lecturer@horizoncampus.edu.lk"
                    value={lecData.email}
                    onChange={(e) => setLecData({ ...lecData, email: e.target.value })}
                    className="w-full bg-[#0f172a] border border-gray-600 rounded-xl px-4 py-3 text-sm focus:outline-none focus:border-purple-500 transition"
                  />
                </div>
                <div>
                  <label className="block text-xs font-bold uppercase text-gray-300 mb-2">Faculty *</label>
                  <select
                    value={lecData.faculty}
                    onChange={(e) => setLecData({ ...lecData, faculty: e.target.value })}
                    className="w-full bg-[#0f172a] border border-gray-600 rounded-xl px-4 py-3 text-sm focus:outline-none focus:border-purple-500 transition"
                  >
                    <option value="Faculty of IT">Faculty of IT</option>
                    <option value="Faculty of Engineering">Faculty of Engineering</option>
                    <option value="Faculty of Management">Faculty of Management</option>
                    <option value="Faculty of Science">Faculty of Science</option>
                  </select>
                </div>
              </div>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                <div>
                  <label className="block text-xs font-bold uppercase text-gray-300 mb-2">Gender *</label>
                  <select
                    value={lecData.gender}
                    onChange={(e) => setLecData({ ...lecData, gender: e.target.value })}
                    className="w-full bg-[#0f172a] border border-gray-600 rounded-xl px-4 py-3 text-sm focus:outline-none focus:border-purple-500 transition"
                  >
                    <option value="Male">Male</option>
                    <option value="Female">Female</option>
                  </select>
                </div>
                <div>
                  <label className="block text-xs font-bold uppercase text-gray-300 mb-2">Employment Type *</label>
                  <select
                    value={lecData.employment_type}
                    onChange={(e) => setLecData({ ...lecData, employment_type: e.target.value })}
                    className="w-full bg-[#0f172a] border border-gray-600 rounded-xl px-4 py-3 text-sm focus:outline-none focus:border-purple-500 transition"
                  >
                    <option value="Permanent">Permanent Faculty</option>
                    <option value="Visiting">Visiting Lecturer</option>
                  </select>
                </div>
              </div>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                <div>
                  <label className="block text-xs font-bold uppercase text-gray-300 mb-2">
                    Subjects Assigned * <span className="text-purple-300 font-normal lowercase">(Separate by comma)</span>
                  </label>
                  <input
                    type="text" placeholder="e.g., AI, Machine Learning, Data Science"
                    value={lecData.subjects}
                    onChange={(e) => setLecData({ ...lecData, subjects: e.target.value })}
                    className="w-full bg-[#0f172a] border border-gray-600 rounded-xl px-4 py-3 text-sm focus:outline-none focus:border-purple-500 transition"
                  />
                </div>
                <div>
                  <label className="block text-xs font-bold uppercase text-gray-300 mb-2">Login Password *</label>
                  <input
                    type="password" placeholder="••••••••"
                    value={lecData.password}
                    onChange={(e) => setLecData({ ...lecData, password: e.target.value })}
                    className="w-full bg-[#0f172a] border border-gray-600 rounded-xl px-4 py-3 text-sm focus:outline-none focus:border-purple-500 transition"
                  />
                </div>
              </div>

              {/* Action Buttons */}
              <div className="flex gap-4 pt-4">
                <button
                  type="button" onClick={handleClear}
                  className="w-1/3 py-3.5 px-6 rounded-xl font-bold bg-gray-800 hover:bg-gray-700 text-gray-300 transition duration-200 border border-gray-600"
                >
                  🧹 Clear Form
                </button>
                <button
                  type="submit" disabled={loading}
                  className={`w-2/3 py-3.5 px-6 rounded-xl font-bold text-white shadow-lg transition duration-300 transform active:scale-98 ${
                    loading ? "bg-purple-600/50 cursor-not-allowed" : "bg-gradient-to-r from-purple-600 to-pink-600 hover:from-purple-500 hover:to-pink-500 shadow-purple-500/25 hover:shadow-purple-500/40"
                  }`}
                >
                  {loading ? "Registering Lecturer..." : "✨ Register Lecturer"}
                </button>
              </div>
            </form>
          )}

        </div>
      </div>
    </div>
  );
}