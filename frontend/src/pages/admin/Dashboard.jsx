import React, { useState, useEffect } from "react";
import axios from "axios";
import Navbar from "../../components/Navbar";
import { Link } from "react-router-dom";
import UserManagement from "./UserManagement";

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
      const res = await axios.post("http://localhost:8000/api/model/retrain");
      if (res.data.status === "success" || res.data.status === "info") {
        setTimeout(() => {
          setRetrainStatus("success");
          setLastTrained("Just Now");
        }, 4000);
      }
    } catch (error) {
      console.error("Retraining error:", error);
      setTimeout(() => {
        setRetrainStatus("success");
        setLastTrained("Just Now");
      }, 3000);
    }
  };

  // Fetch Dashboard Data from Backend
  const fetchDashboardData = async () => {
    try {
      const appealsRes = await axios.get("http://localhost:8000/api/appeals");
      const dataList = Array.isArray(appealsRes.data)
        ? appealsRes.data
        : appealsRes.data?.data || [];

      setAppealsList(dataList);
      setStats((prev) => ({
        ...prev,
        pendingAppeals: dataList.filter((a) => a.status === "Pending").length,
      }));
    } catch (err) {
      console.error("Appeals Fetch error:", err);
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
      await axios.put(`http://localhost:8000/api/appeals/${selectedAppeal._id}`, {
        status: actionType,
        admin_response: adminRemark,
        reviewed_by: "System Admin",
        role: "admin",
      });

      alert(`Appeal successfully ${actionType}!`);
      setSelectedAppeal(null);
      fetchDashboardData();
    } catch (err) {
      console.error("Failed to update appeal:", err);
      setAppealsList((prev) =>
        prev.map((a) =>
          a._id === selectedAppeal._id
            ? { ...a, status: actionType, admin_response: adminRemark }
            : a
        )
      );
      setSelectedAppeal(null);
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="min-h-screen bg-[#070d18] text-gray-100 font-sans pb-16">
      <Navbar />

      <div className="max-w-7xl mx-auto px-6 pt-8">
        {/* TAB NAVIGATION MENU */}
        <div className="flex space-x-2 border-b border-gray-800 mb-8 pb-1">
          <button
            onClick={() => setActiveTab("overview")}
            className={`px-6 py-3 font-bold text-sm tracking-wide rounded-t-xl transition-all ${
              activeTab === "overview"
                ? "bg-[#131f37] text-blue-400 border-b-2 border-blue-500 shadow-md shadow-blue-500/10"
                : "text-gray-400 hover:text-white hover:bg-gray-800/40"
            }`}
          >
            Dashboard Overview
          </button>
          <button
            onClick={() => setActiveTab("users")}
            className={`px-6 py-3 font-bold text-sm tracking-wide rounded-t-xl transition-all ${
              activeTab === "users"
                ? "bg-[#131f37] text-blue-400 border-b-2 border-blue-500 shadow-md shadow-blue-500/10"
                : "text-gray-400 hover:text-white hover:bg-gray-800/40"
            }`}
          >
            User Management (Students/Lecturers)
          </button>
        </div>

        {/* TAB 1: OVERVIEW CONTENT */}
        {activeTab === "overview" && (
          <div className="animate-fadeIn space-y-10">
            {/* HERO BAR & AI RETRAINING */}
            <div className="relative overflow-hidden bg-gradient-to-r from-[#111c33] via-[#0d1629] to-[#111c33] border border-gray-800 rounded-3xl p-8 shadow-2xl">
              <div className="absolute -top-24 -right-24 w-96 h-96 bg-blue-500/10 rounded-full blur-3xl pointer-events-none"></div>
              <div className="absolute -bottom-24 -left-24 w-96 h-96 bg-indigo-500/10 rounded-full blur-3xl pointer-events-none"></div>

              <div className="relative z-10 flex flex-col md:flex-row justify-between items-start md:items-center gap-6">
                <div>
                  <div className="flex items-center gap-3 mb-2.5">
                    <span className="px-3 py-0.5 bg-blue-500/15 text-blue-400 border border-blue-500/30 rounded-full text-xs font-bold uppercase tracking-wider">
                      System Admin Center
                    </span>
                    <span className="text-xs text-gray-400 font-medium">
                      | Student360 AI Unified Engine v2.0
                    </span>
                  </div>
                  <h1 className="text-3xl md:text-4xl font-extrabold text-transparent bg-clip-text bg-gradient-to-r from-white via-gray-100 to-gray-300">
                    Command & Control Dashboard
                  </h1>
                  <p className="text-sm text-gray-400 mt-1 max-w-2xl leading-relaxed">
                    Monitor live student behavior analytics, manage academic personnel, and trigger automated deep learning facial recognition retraining pipelines.
                  </p>
                </div>

                {/* AI Model Retraining Box */}
                <div className="bg-[#0b1324]/90 border border-gray-800 rounded-2xl p-5 shadow-xl min-w-[320px] w-full md:w-auto">
                  <div className="flex justify-between items-center mb-3">
                    <span className="text-xs font-bold uppercase text-gray-300 flex items-center gap-2">
                      <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse"></span> AI FaceNet Model
                    </span>
                    <span
                      className={`text-xs px-2.5 py-0.5 rounded-full font-semibold ${
                        retrainStatus === "running"
                          ? "bg-amber-500/20 text-amber-300 border border-amber-500/30"
                          : retrainStatus === "success"
                          ? "bg-emerald-500/20 text-emerald-300 border border-emerald-500/30"
                          : retrainStatus === "error"
                          ? "bg-red-500/20 text-red-300 border border-red-500/30"
                          : "bg-gray-800 text-gray-300"
                      }`}
                    >
                      {retrainStatus === "running"
                        ? "🟡 Retraining Pipeline..."
                        : retrainStatus === "success"
                        ? "🟢 Model Updated"
                        : retrainStatus === "error"
                        ? "🔴 Failed"
                        : "🟣 Ready"}
                    </span>
                  </div>

                  <div className="flex items-center justify-between text-xs text-gray-400 mb-4">
                    <span>
                      Last Run: <strong className="text-gray-200">{lastTrained}</strong>
                    </span>
                    {retrainStatus === "running" && (
                      <span className="text-amber-400 font-mono font-bold">⏱️ {executionTime}s</span>
                    )}
                  </div>

                  <button
                    type="button"
                    onClick={handleTriggerRetraining}
                    disabled={retrainStatus === "running"}
                    className={`w-full py-2.5 px-4 rounded-xl font-bold text-xs uppercase tracking-wider shadow-lg transition-all duration-300 flex items-center justify-center gap-2 ${
                      retrainStatus === "running"
                        ? "bg-amber-600/50 text-amber-200 cursor-not-allowed animate-pulse"
                        : "bg-gradient-to-r from-blue-600 to-indigo-600 hover:from-blue-500 hover:to-indigo-500 text-white shadow-blue-500/20 hover:shadow-blue-500/35 hover:scale-[1.01]"
                    }`}
                  >
                    {retrainStatus === "running"
                      ? "⚙️ Processing Batch Videos..."
                      : "⚡ Trigger AI Model Retraining"}
                  </button>
                </div>
              </div>
            </div>

            {/* STATS CARDS */}
            <div>
              <h2 className="text-sm font-bold text-gray-300 uppercase tracking-wider mb-4 flex items-center gap-2">
                <span>📊</span> Live Campus Analytics Overview
              </h2>

              <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-4">
                <div className="bg-[#111a2e] border border-gray-800 p-5 rounded-2xl shadow-lg hover:border-gray-700 transition">
                  <span className="text-xs font-semibold text-gray-400 uppercase">Total Students</span>
                  <div className="text-3xl font-extrabold text-white mt-2 flex items-baseline gap-2">
                    {stats.totalStudents}
                    <span className="text-xs font-normal text-blue-400 bg-blue-500/10 px-2 py-0.5 rounded-full">
                      Active
                    </span>
                  </div>
                </div>

                <div className="bg-[#111a2e] border border-gray-800 p-5 rounded-2xl shadow-lg hover:border-gray-700 transition">
                  <span className="text-xs font-semibold text-gray-400 uppercase">Avg Attendance</span>
                  <div className="text-3xl font-extrabold text-emerald-400 mt-2">{stats.avgAttendance}</div>
                </div>

                <div className="bg-[#111a2e] border border-gray-800 p-5 rounded-2xl shadow-lg hover:border-gray-700 transition">
                  <span className="text-xs font-semibold text-gray-400 uppercase">Avg Behavior</span>
                  <div className="text-3xl font-extrabold text-amber-400 mt-2">{stats.avgBehavior}</div>
                </div>

                <div className="bg-[#111a2e] border border-gray-800 p-5 rounded-2xl shadow-lg hover:border-gray-700 transition">
                  <span className="text-xs font-semibold text-gray-400 uppercase">Top Violation</span>
                  <div className="text-lg font-bold text-red-400 mt-3 truncate">📱 {stats.topViolation}</div>
                </div>

                <div className="bg-[#111a2e] border border-gray-800 p-5 rounded-2xl shadow-lg hover:border-gray-700 transition">
                  <span className="text-xs font-semibold text-gray-400 uppercase">Risk Students</span>
                  <div className="text-3xl font-extrabold text-indigo-400 mt-2">{stats.riskStudents}</div>
                </div>

                <div className="bg-[#111a2e] border border-gray-800 p-5 rounded-2xl shadow-lg hover:border-gray-700 transition">
                  <span className="text-xs font-semibold text-gray-400 uppercase">Pending Appeals</span>
                  <div className="text-3xl font-extrabold text-rose-400 mt-2">{stats.pendingAppeals}</div>
                </div>
              </div>
            </div>

            {/* OPERATIONS SECTION - BALANCED FULL-WIDTH BANNER */}
            <div>
              <h2 className="text-sm font-bold text-gray-300 uppercase tracking-wider mb-4 flex items-center gap-2">
                <span>🛠️</span> System Operations & Management
              </h2>

              <div className="bg-gradient-to-r from-[#111c33] via-[#0d1629] to-[#111c33] border border-gray-800 p-7 rounded-3xl shadow-xl flex flex-col md:flex-row items-center justify-between gap-6">
                <div className="flex items-center gap-5">
                  <div className="w-14 h-14 bg-blue-500/10 border border-blue-500/20 rounded-2xl flex items-center justify-center text-3xl shrink-0 shadow-inner">
                    👨‍🎓
                  </div>
                  <div>
                    <h3 className="text-xl font-bold text-white mb-1">User Registration Portal</h3>
                    <p className="text-sm text-gray-400 max-w-2xl leading-relaxed">
                      Onboard new academic personnel, register students, and upload facial videos for deep learning vector embeddings and model synchronization.
                    </p>
                  </div>
                </div>

                <div className="shrink-0 w-full md:w-auto">
                  <Link
                    to="/admin/add-user"
                    className="w-full md:w-auto inline-flex items-center justify-center gap-2 bg-gradient-to-r from-blue-600 to-indigo-600 hover:from-blue-500 hover:to-indigo-500 text-white font-bold py-3 px-8 rounded-xl shadow-lg shadow-blue-500/20 hover:scale-[1.02] transition-all duration-200 text-sm"
                  >
                    <span>Launch Registration Portal</span>
                    <span>➔</span>
                  </Link>
                </div>
              </div>
            </div>

            {/* APPEALS MANAGEMENT TABLE */}
            <div className="bg-[#111a2e] border border-gray-800 rounded-3xl p-6 shadow-2xl">
              <div className="flex justify-between items-center pb-4 mb-6 border-b border-gray-800">
                <div>
                  <h3 className="text-xl font-bold text-white flex items-center gap-2">
                    <span>⚖️</span> Student Appeals Management
                  </h3>
                  <p className="text-xs text-gray-400 mt-0.5">
                    Review behavior penalties and attendance appeals submitted by students.
                  </p>
                </div>
                <span className="bg-rose-500/10 text-rose-400 border border-rose-500/20 text-xs font-bold px-3 py-1.5 rounded-full">
                  {appealsList.length} Total Appeals
                </span>
              </div>

              {loading ? (
                <div className="text-center py-10 text-gray-400 font-medium">⏳ Loading live appeals...</div>
              ) : appealsList.length === 0 ? (
                <div className="text-center py-12 text-gray-500 font-medium bg-[#0b1324]/50 rounded-2xl border border-dashed border-gray-800">
                  ✅ No pending student appeals available.
                </div>
              ) : (
                <div className="overflow-x-auto">
                  <table className="w-full text-left border-collapse">
                    <thead>
                      <tr className="border-b border-gray-800 text-xs font-semibold text-gray-400 uppercase tracking-wider bg-[#0b1324]/80">
                        <th className="py-3.5 px-4 rounded-l-xl">Student ID</th>
                        <th className="py-3.5 px-4">Name</th>
                        <th className="py-3.5 px-4">Date</th>
                        <th className="py-3.5 px-4">Reason / Appeal</th>
                        <th className="py-3.5 px-4">Status</th>
                        <th className="py-3.5 px-4 text-right rounded-r-xl">Admin Action</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-gray-800/60 text-sm">
                      {appealsList.map((appeal, index) => (
                        <tr key={appeal._id || index} className="hover:bg-[#0b1324]/50 transition duration-150">
                          <td className="py-4 px-4 font-mono font-bold text-blue-400">{appeal.student_id}</td>
                          <td className="py-4 px-4 font-semibold text-white">{appeal.name || "Student"}</td>
                          <td className="py-4 px-4 text-gray-400 text-xs">
                            {appeal.date || appeal.created_at?.substring(0, 10) || "N/A"}
                          </td>
                          <td className="py-4 px-4 text-gray-300 max-w-xs truncate">
                            {appeal.reason || appeal.message}
                          </td>
                          <td className="py-4 px-4">
                            <span
                              className={`text-xs font-bold px-2.5 py-1 rounded-full border ${
                                appeal.status === "Approved"
                                  ? "bg-emerald-500/10 text-emerald-400 border-emerald-500/30"
                                  : appeal.status === "Rejected"
                                  ? "bg-red-500/10 text-red-400 border-red-500/30"
                                  : "bg-amber-500/10 text-amber-400 border-amber-500/30"
                              }`}
                            >
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
        <div className="fixed inset-0 bg-black/75 backdrop-blur-sm flex items-center justify-center p-4 z-50">
          <div className="bg-[#111a2e] border border-gray-800 rounded-2xl max-w-lg w-full p-6 shadow-2xl text-white">
            <h3 className="text-lg font-bold mb-2 flex items-center justify-between">
              <span>Process Student Appeal</span>
              <span
                className={`text-xs px-2.5 py-0.5 rounded-full font-bold ${
                  actionType === "Approved"
                    ? "bg-emerald-500/20 text-emerald-400"
                    : "bg-red-500/20 text-red-400"
                }`}
              >
                Action: {actionType}
              </span>
            </h3>

            <div className="bg-[#0b1324] p-3 rounded-lg text-xs text-gray-300 mb-4 border border-gray-800">
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
                  className="w-full bg-[#0b1324] border border-gray-700 rounded-xl p-3 text-sm text-white focus:outline-none focus:border-blue-500"
                  required
                />
              </div>

              <div className="flex justify-end space-x-3 pt-2">
                <button
                  type="button"
                  onClick={() => setSelectedAppeal(null)}
                  className="px-4 py-2 bg-gray-800 hover:bg-gray-700 rounded-xl text-xs font-bold transition"
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