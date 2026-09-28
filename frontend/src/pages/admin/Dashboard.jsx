import React, { useState, useEffect } from "react";
import axios from "axios";
import Navbar from "../../components/Navbar";
import { Link } from "react-router-dom"; 
import UserManagement from './UserManagement'; 

export default function AdminDashboard() {
  const [activeTab, setActiveTab] = useState("overview");

  // Stats states
  const [stats, setStats] = useState({
    totalStudents: 0,
    avgAttendance: "0%",
    avgBehavior: "0%",
    topViolation: "None",
    riskStudents: 0,
    pendingAppeals: 0,
  });

  const [appealsList, setAppealsList] = useState([]);
  const [loading, setLoading] = useState(true);

  // APPEAL DECISION MODAL STATES
  const [selectedAppeal, setSelectedAppeal] = useState(null);
  const [actionType, setActionType] = useState(""); // 'Approved' or 'Rejected'
  const [adminRemark, setAdminRemark] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);

  // AI RETRAINING PIPELINE STATE
  const [retrainStatus, setRetrainStatus] = useState("idle"); 
  const [executionTime, setExecutionTime] = useState(0);
  const [lastTrained, setLastTrained] = useState("Yesterday at 11:30 PM");

  // Timer effect for simulation when running
  useEffect(() => {
    let timer;
    if (retrainStatus === "running") {
      timer = setInterval(() => {
        setExecutionTime((prev) => +(prev + 0.1).toFixed(1));
      }, 100);
    } else {
      clearInterval(timer);
    }
    return () => clearInterval(timer);
  }, [retrainStatus]);

  // Trigger Retraining Button Function
  const handleTriggerRetraining = async () => {
    setRetrainStatus("running");
    setExecutionTime(0);

    try {
      setTimeout(() => {
        setRetrainStatus("success");
        setLastTrained("Just Now");
      }, 5000);
    } catch (error) {
      setRetrainStatus("error");
    }
  };

  // Fetch Dashboard Data from Backend
  // Fetch Dashboard Data from Backend
  const fetchDashboardData = async () => {
    try {
      // 1. Backend එකෙන් direct Appeals ටික ගන්නවා
      const appealsRes = await axios.get("http://localhost:8000/api/appeals");
      
      console.log("Database එකෙන් ආපු Appeals ටික:", appealsRes.data);

      // 2. එන Data ලිස්ට් එක State එකට සෙට් කරනවා
      const dataList = Array.isArray(appealsRes.data) ? appealsRes.data : (appealsRes.data?.data || []);
      
      setAppealsList(dataList);
      setStats(prev => ({
        ...prev,
        pendingAppeals: dataList.filter(a => a.status === "Pending").length
      }));

    } catch (err) {
      console.error("Appeals Fetch කරන්න බැරි වුණා. Error එක:", err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchDashboardData();
  }, []);

  // Open Modal for Decision
  const handleOpenModal = (appeal, type) => {
    setSelectedAppeal(appeal);
    setActionType(type);
    setAdminRemark("");
  };

  // Submit Decision to Backend
  const handleSaveDecision = async (e) => {
    e.preventDefault();
    if (!selectedAppeal) return;

    setIsSubmitting(true);
    try {
      // Backend API call to update appeal
      await axios.put(`http://localhost:8000/api/appeals/${selectedAppeal._id}`, {
        status: actionType,
        admin_response: adminRemark,
        reviewed_by: "System Admin",
        role: "admin"
      });

      alert(`Appeal successfully ${actionType}!`);
      setSelectedAppeal(null);
      fetchDashboardData(); // Refresh list
    } catch (err) {
      console.error("Failed to update appeal:", err);
      // Fallback UI update if API fails during testing
      setAppealsList(prev => prev.map(a => a._id === selectedAppeal._id ? { ...a, status: actionType, admin_response: adminRemark } : a));
      setSelectedAppeal(null);
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="min-h-screen bg-[#0b1120] text-gray-100 font-sans pb-16">
      <Navbar />

      <div className="max-w-7xl mx-auto px-6 pt-8">
        
        {/* TAB NAVIGATION MENU */}
        <div className="flex space-x-2 border-b border-gray-800 mb-8 pb-1">
          <button
            onClick={() => setActiveTab("overview")}
            className={`px-6 py-3 font-bold rounded-t-lg transition-all ${
              activeTab === "overview" 
                ? "bg-[#1e293b] text-blue-400 border-b-2 border-blue-400" 
                : "text-gray-400 hover:text-white hover:bg-gray-800/50"
            }`}
          >
            Dashboard Overview
          </button>
          <button
            onClick={() => setActiveTab("users")}
            className={`px-6 py-3 font-bold rounded-t-lg transition-all ${
              activeTab === "users" 
                ? "bg-[#1e293b] text-blue-400 border-b-2 border-blue-400" 
                : "text-gray-400 hover:text-white hover:bg-gray-800/50"
            }`}
          >
            User Management (Students/Lecturers)
          </button>
        </div>

        {/* TAB 1: OVERVIEW CONTENT */}
        {activeTab === "overview" && (
          <div className="animate-fadeIn">
            {/* HERO BAR & AI RETRAINING */}
            <div className="relative overflow-hidden bg-gradient-to-r from-[#1e293b] via-[#0f172a] to-[#1e293b] border border-gray-700/80 rounded-3xl p-8 mb-10 shadow-2xl">
              <div className="absolute -top-24 -right-24 w-96 h-96 bg-blue-500/10 rounded-full blur-3xl pointer-events-none"></div>
              <div className="absolute -bottom-24 -left-24 w-96 h-96 bg-purple-500/10 rounded-full blur-3xl pointer-events-none"></div>

              <div className="relative z-10 flex flex-col md:flex-row justify-between items-start md:items-center gap-6">
                <div>
                  <div className="flex items-center gap-3 mb-2">
                    <span className="px-3 py-1 bg-blue-500/20 text-blue-400 border border-blue-500/30 rounded-full text-xs font-bold uppercase tracking-wider animate-pulse">
                      System Admin Center
                    </span>
                    <span className="text-xs text-gray-400">| Student360 AI Unified Engine v2.0</span>
                  </div>
                  <h1 className="text-3xl md:text-4xl font-extrabold text-transparent bg-clip-text bg-gradient-to-r from-white via-gray-200 to-gray-400">
                    Command & Control Dashboard
                  </h1>
                  <p className="text-sm text-gray-400 mt-1 max-w-2xl">
                    Monitor live student behavior analytics, manage academic personnel, and trigger automated deep learning facial recognition retraining pipelines.
                  </p>
                </div>

                {/* AI Model Retraining Box */}
                <div className="bg-[#0f172a]/90 border border-gray-700/80 rounded-2xl p-5 shadow-inner min-w-[300px] w-full md:w-auto">
                  <div className="flex justify-between items-center mb-3">
                    <span className="text-xs font-bold uppercase text-gray-400 flex items-center gap-1.5">
                      <span className="w-2 h-2 rounded-full bg-blue-400 animate-ping"></span> AI FaceNet Model
                    </span>
                    <span className={`text-xs px-2.5 py-0.5 rounded-full font-semibold ${
                      retrainStatus === "running" ? "bg-yellow-500/20 text-yellow-400 border border-yellow-500/30" :
                      retrainStatus === "success" ? "bg-green-500/20 text-green-400 border border-green-500/30" :
                      retrainStatus === "error" ? "bg-red-500/20 text-red-400 border border-red-500/30" :
                      "bg-gray-700/50 text-gray-300"
                    }`}>
                      {retrainStatus === "running" ? "🟡 Retraining Pipeline..." :
                       retrainStatus === "success" ? "🟢 Model Updated" :
                       retrainStatus === "error" ? "🔴 Failed" : "🟣 Ready"}
                    </span>
                  </div>

                  <div className="flex items-center justify-between text-xs text-gray-400 mb-4">
                    <span>Last Run: <strong className="text-gray-200">{lastTrained}</strong></span>
                    {retrainStatus === "running" && (
                      <span className="text-yellow-400 font-mono font-bold">⏱️ {executionTime}s</span>
                    )}
                  </div>

                  <button
                    type="button"
                    onClick={handleTriggerRetraining}
                    disabled={retrainStatus === "running"}
                    className={`w-full py-2.5 px-4 rounded-xl font-bold text-xs uppercase tracking-wider shadow-lg transition-all duration-300 flex items-center justify-center gap-2 ${
                      retrainStatus === "running"
                        ? "bg-yellow-600/50 text-yellow-200 cursor-not-allowed animate-pulse"
                        : "bg-gradient-to-r from-blue-600 to-indigo-600 hover:from-blue-500 hover:to-indigo-500 text-white shadow-blue-500/25 hover:shadow-blue-500/40 hover:scale-[1.02]"
                    }`}
                  >
                    {retrainStatus === "running" ? "⚙️ Processing Batch Videos..." : "⚡ Trigger AI Model Retraining"}
                  </button>
                </div>
              </div>
            </div>

            {/* STATS CARDS */}
            <h2 className="text-lg font-bold text-gray-300 mb-4 flex items-center gap-2">
              <span>📊</span> Live Campus Analytics Overview
            </h2>

            <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-5 mb-10">
              <div className="bg-[#1e293b]/70 border border-gray-700/70 p-5 rounded-2xl shadow-lg">
                <span className="text-xs font-semibold text-gray-400 uppercase">Total Students</span>
                <div className="text-3xl font-extrabold text-white mt-2 flex items-baseline gap-2">
                  {stats.totalStudents}
                  <span className="text-xs font-normal text-blue-400 bg-blue-500/10 px-2 py-0.5 rounded">Active</span>
                </div>
              </div>

              <div className="bg-[#1e293b]/70 border border-gray-700/70 p-5 rounded-2xl shadow-lg">
                <span className="text-xs font-semibold text-gray-400 uppercase">Avg Attendance</span>
                <div className="text-3xl font-extrabold text-emerald-400 mt-2">{stats.avgAttendance}</div>
              </div>

              <div className="bg-[#1e293b]/70 border border-gray-700/70 p-5 rounded-2xl shadow-lg">
                <span className="text-xs font-semibold text-gray-400 uppercase">Avg Behavior</span>
                <div className="text-3xl font-extrabold text-yellow-400 mt-2">{stats.avgBehavior}</div>
              </div>

              <div className="bg-[#1e293b]/70 border border-gray-700/70 p-5 rounded-2xl shadow-lg">
                <span className="text-xs font-semibold text-gray-400 uppercase">Top Violation</span>
                <div className="text-xl font-bold text-red-400 mt-3 truncate">📱 {stats.topViolation}</div>
              </div>

              <div className="bg-[#1e293b]/70 border border-gray-700/70 p-5 rounded-2xl shadow-lg">
                <span className="text-xs font-semibold text-gray-400 uppercase">Risk Students</span>
                <div className="text-3xl font-extrabold text-purple-400 mt-2">{stats.riskStudents}</div>
              </div>

              <div className="bg-[#1e293b]/70 border border-gray-700/70 p-5 rounded-2xl shadow-lg">
                <span className="text-xs font-semibold text-gray-400 uppercase">Pending Appeals</span>
                <div className="text-3xl font-extrabold text-pink-400 mt-2">{stats.pendingAppeals}</div>
              </div>
            </div>

            {/* OPERATIONS CARDS */}
            <h2 className="text-lg font-bold text-gray-300 mb-4 flex items-center gap-2">
              <span>🛠️</span> System Operations & Management
            </h2>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mb-12">
              <div className="bg-gradient-to-br from-[#1e293b] to-[#0f172a] border border-gray-700 p-6 rounded-3xl shadow-xl flex flex-col justify-between">
                <div>
                  <div className="w-12 h-12 bg-blue-500/10 border border-blue-500/20 rounded-2xl flex items-center justify-center text-2xl mb-4">
                    👨‍🎓
                  </div>
                  <h3 className="text-xl font-bold text-white mb-2">User Registration Portal</h3>
                  <p className="text-sm text-gray-400 mb-6 leading-relaxed">
                    Onboard new academic personnel, register students, and upload facial videos for vector database generation.
                  </p>
                </div>
                <Link
                  to="/admin/add-user"
                  className="w-full text-center bg-gradient-to-r from-blue-600 to-indigo-600 hover:from-blue-500 hover:to-indigo-500 text-white font-bold py-3 px-6 rounded-xl shadow-lg flex items-center justify-center gap-2"
                >
                  <span>Launch Registration Portal</span>
                  <span>➔</span>
                </Link>
              </div>

              <div className="bg-gradient-to-br from-[#1e293b] to-[#0f172a] border border-gray-700 p-6 rounded-3xl shadow-xl flex flex-col justify-between">
                <div>
                  <div className="w-12 h-12 bg-purple-500/10 border border-purple-500/20 rounded-2xl flex items-center justify-center text-2xl mb-4">
                    📥
                  </div>
                  <h3 className="text-xl font-bold text-white mb-2">AI Session Data Upload</h3>
                  <p className="text-sm text-gray-400 mb-6 leading-relaxed">
                    Upload classroom behavior summary CSV logs generated by the ByteTrack unified pipeline directly into MongoDB.
                  </p>
                </div>
                <button
                  type="button"
                  onClick={() => alert("Open CSV Upload Modal")}
                  className="w-full text-center bg-gradient-to-r from-purple-600 to-pink-600 text-white font-bold py-3 px-6 rounded-xl shadow-lg flex items-center justify-center gap-2"
                >
                  <span>Upload Classroom CSV</span>
                  <span>➔</span>
                </button>
              </div>
            </div>

            {/* LATEST PENDING APPEALS SECTION WITH ACTION BUTTONS */}
            <div className="bg-[#1e293b]/90 border border-gray-700/80 rounded-3xl p-6 shadow-2xl">
              <div className="flex justify-between items-center pb-4 mb-6 border-b border-gray-700/80">
                <div>
                  <h3 className="text-xl font-bold text-white flex items-center gap-2">
                    <span>⚖️</span> Student Appeals Management
                  </h3>
                  <p className="text-xs text-gray-400 mt-0.5">Review behavior penalties and attendance appeals submitted by students.</p>
                </div>
                <span className="bg-pink-500/10 text-pink-400 border border-pink-500/20 text-xs font-bold px-3 py-1.5 rounded-full">
                  {appealsList.length} Total Appeals
                </span>
              </div>

              {loading ? (
                <div className="text-center py-10 text-gray-400 font-medium">⏳ Loading live appeals...</div>
              ) : appealsList.length === 0 ? (
                <div className="text-center py-12 text-gray-500 font-medium bg-[#0f172a]/50 rounded-2xl border border-dashed border-gray-700">
                  ✅ No pending student appeals available.
                </div>
              ) : (
                <div className="overflow-x-auto">
                  <table className="w-full text-left border-collapse">
                    <thead>
                      <tr className="border-b border-gray-700 text-xs font-semibold text-gray-400 uppercase tracking-wider bg-[#0f172a]/80">
                        <th className="py-3.5 px-4 rounded-l-xl">Student ID</th>
                        <th className="py-3.5 px-4">Name</th>
                        <th className="py-3.5 px-4">Date</th>
                        <th className="py-3.5 px-4">Reason / Appeal</th>
                        <th className="py-3.5 px-4">Status</th>
                        <th className="py-3.5 px-4 text-right rounded-r-xl">Admin Action</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-gray-700/50 text-sm">
                      {appealsList.map((appeal, index) => (
                        <tr key={appeal._id || index} className="hover:bg-[#0f172a]/60 transition duration-150">
                          <td className="py-4 px-4 font-mono font-bold text-blue-400">{appeal.student_id}</td>
                          <td className="py-4 px-4 font-semibold text-white">{appeal.name || "Student"}</td>
                          <td className="py-4 px-4 text-gray-400 text-xs">{appeal.date || appeal.created_at?.substring(0,10) || "N/A"}</td>
                          <td className="py-4 px-4 text-gray-300 max-w-xs truncate">
                            {appeal.reason || appeal.message}
                          </td>
                          <td className="py-4 px-4">
                            <span className={`text-xs font-bold px-2.5 py-1 rounded-full border ${
                              appeal.status === "Approved" ? "bg-green-500/10 text-green-400 border-green-500/30" :
                              appeal.status === "Rejected" ? "bg-red-500/10 text-red-400 border-red-500/30" :
                              "bg-yellow-500/10 text-yellow-400 border-yellow-500/30"
                            }`}>
                              {appeal.status || "Pending"}
                            </span>
                          </td>
                          <td className="py-4 px-4 text-right">
                            <button
                              type="button"
                              onClick={() => handleOpenModal(appeal, "Approved")}
                              className="bg-emerald-600/20 hover:bg-emerald-600 text-emerald-400 hover:text-white border border-emerald-500/30 text-xs font-bold px-3 py-1.5 rounded-lg mr-2 transition"
                            >
                              Approve
                            </button>
                            <button
                              type="button"
                              onClick={() => handleOpenModal(appeal, "Rejected")}
                              className="bg-red-600/20 hover:bg-red-600 text-red-400 hover:text-white border border-red-500/30 text-xs font-bold px-3 py-1.5 rounded-lg transition"
                            >
                              Reject
                            </button>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </div>
          </div>
        )}

        {/* TAB 2: USER MANAGEMENT */}
        {activeTab === "users" && (
          <div className="animate-fadeIn">
            <UserManagement />
          </div>
        )}

      </div>

      {/* POPUP MODAL FOR ADMIN RESPONSE */}
      {selectedAppeal && (
        <div className="fixed inset-0 bg-black/70 backdrop-blur-sm flex items-center justify-center p-4 z-50">
          <div className="bg-[#1e293b] border border-gray-700 rounded-2xl max-w-lg w-full p-6 shadow-2xl text-white">
            <h3 className="text-lg font-bold mb-2 flex items-center justify-between">
              <span>Process Student Appeal</span>
              <span className={`text-xs px-2.5 py-0.5 rounded-full font-bold ${
                actionType === "Approved" ? "bg-green-500/20 text-green-400" : "bg-red-500/20 text-red-400"
              }`}>
                Action: {actionType}
              </span>
            </h3>

            <div className="bg-[#0f172a] p-3 rounded-lg text-xs text-gray-300 mb-4 border border-gray-800">
              <p className="font-semibold text-blue-400 mb-1">Student ID: {selectedAppeal.student_id}</p>
              <p>"{selectedAppeal.reason || selectedAppeal.message}"</p>
            </div>

            <form onSubmit={handleSaveDecision} className="space-y-4">
              <div>
                <label className="text-xs text-gray-400 block mb-1">Admin Official Response / Remark</label>
                <textarea
                  rows="4"
                  value={adminRemark}
                  onChange={(e) => setAdminRemark(e.target.value)}
                  placeholder="Enter official remark for student (e.g., Attendance mark updated)..."
                  className="w-full bg-[#0f172a] border border-gray-700 rounded-xl p-3 text-sm text-white focus:outline-none focus:border-blue-500"
                  required
                />
              </div>

              <div className="flex justify-end space-x-3 pt-2">
                <button
                  type="button"
                  onClick={() => setSelectedAppeal(null)}
                  className="px-4 py-2 bg-gray-700 hover:bg-gray-600 rounded-xl text-xs font-bold transition"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={isSubmitting}
                  className={`px-5 py-2 rounded-xl text-xs font-bold transition ${
                    actionType === "Approved" 
                      ? "bg-emerald-600 hover:bg-emerald-500 text-white" 
                      : "bg-red-600 hover:bg-red-500 text-white"
                  }`}
                >
                  {isSubmitting ? "Saving..." : `Confirm ${actionType}`}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

    </div>
  );
}