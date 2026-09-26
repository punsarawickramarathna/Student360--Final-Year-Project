import React, { useState, useEffect } from "react";
import axios from "axios";
import Navbar from "../../components/Navbar";
import { Link } from "react-router-dom"; 
import UserManagement from './UserManagement'; // UserManagement eka import karala thiyenawa

export default function AdminDashboard() {
  // NEW: State for Tabs (Overview vs Users)
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
  useEffect(() => {
    const fetchDashboardData = async () => {
      try {
        const studentsRes = await axios.get("http://localhost:8000/api/students").catch(() => ({ data: { count: 4 } }));
        const appealsRes = await axios.get("http://localhost:8000/api/appeals").catch(() => ({ data: [] }));

        setStats({
          totalStudents: studentsRes.data.count || 4,
          avgAttendance: "92%",
          avgBehavior: "88%",
          topViolation: "Phone Use",
          riskStudents: 1,
          pendingAppeals: appealsRes.data.length || 0,
        });

        if (!appealsRes.data || appealsRes.data.length === 0) {
          setAppealsList([
            { _id: "1", student_id: "ITBIN-2211-0320", name: "Mithun Wijesinghe", date: "2026-07-23", reason: "Phone use false detection during lecture", status: "Pending" },
            { _id: "2", student_id: "ITBIN-2211-0317", name: "Punsara", date: "2026-07-22", reason: "Attendance marked absent due to camera angle", status: "Pending" }
          ]);
        } else {
          setAppealsList(appealsRes.data);
        }
      } catch (err) {
        console.error("Dashboard Fetch Error:", err);
      } finally {
        setLoading(false);
      }
    };

    fetchDashboardData();
  }, []);

  return (
    <div className="min-h-screen bg-[#0b1120] text-gray-100 font-sans pb-16">
      <Navbar />

      <div className="max-w-7xl mx-auto px-6 pt-8">
        
        {/* NEW: TAB NAVIGATION MENU */}
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

        {/* TAB 1: OVERVIEW CONTENT (Only shows if activeTab is 'overview') */}
        {activeTab === "overview" && (
          <div className="animate-fadeIn">
            {/* TOP HERO BAR & AI RETRAINING PIPELINE */}
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

                {/* AI Model Retraining Card Box */}
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
                    {retrainStatus === "running" ? (
                      <>⚙️ Processing Batch Videos...</>
                    ) : (
                      <>⚡ Trigger AI Model Retraining</>
                    )}
                  </button>
                </div>
              </div>
            </div>

            {/* KEY PERFORMANCE ANALYTICS METRICS (6 CARDS) */}
            <h2 className="text-lg font-bold text-gray-300 mb-4 flex items-center gap-2">
              <span>📊</span> Live Campus Analytics Overview
            </h2>

            <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-5 mb-10">
              <div className="bg-[#1e293b]/70 border border-gray-700/70 hover:border-blue-500/50 p-5 rounded-2xl shadow-lg transition duration-300 transform hover:-translate-y-1">
                <span className="text-xs font-semibold text-gray-400 uppercase">Total Students</span>
                <div className="text-3xl font-extrabold text-white mt-2 flex items-baseline gap-2">
                  {stats.totalStudents}
                  <span className="text-xs font-normal text-blue-400 bg-blue-500/10 px-2 py-0.5 rounded">Active</span>
                </div>
              </div>

              <div className="bg-[#1e293b]/70 border border-gray-700/70 hover:border-emerald-500/50 p-5 rounded-2xl shadow-lg transition duration-300 transform hover:-translate-y-1">
                <span className="text-xs font-semibold text-gray-400 uppercase">Avg Attendance</span>
                <div className="text-3xl font-extrabold text-emerald-400 mt-2">{stats.avgAttendance}</div>
              </div>

              <div className="bg-[#1e293b]/70 border border-gray-700/70 hover:border-yellow-500/50 p-5 rounded-2xl shadow-lg transition duration-300 transform hover:-translate-y-1">
                <span className="text-xs font-semibold text-gray-400 uppercase">Avg Behavior</span>
                <div className="text-3xl font-extrabold text-yellow-400 mt-2">{stats.avgBehavior}</div>
              </div>

              <div className="bg-[#1e293b]/70 border border-gray-700/70 hover:border-red-500/50 p-5 rounded-2xl shadow-lg transition duration-300 transform hover:-translate-y-1">
                <span className="text-xs font-semibold text-gray-400 uppercase">Top Violation</span>
                <div className="text-xl font-bold text-red-400 mt-3 truncate">📱 {stats.topViolation}</div>
              </div>

              <div className="bg-[#1e293b]/70 border border-gray-700/70 hover:border-purple-500/50 p-5 rounded-2xl shadow-lg transition duration-300 transform hover:-translate-y-1">
                <span className="text-xs font-semibold text-gray-400 uppercase">Risk Students</span>
                <div className="text-3xl font-extrabold text-purple-400 mt-2">{stats.riskStudents}</div>
              </div>

              <div className="bg-[#1e293b]/70 border border-gray-700/70 hover:border-pink-500/50 p-5 rounded-2xl shadow-lg transition duration-300 transform hover:-translate-y-1">
                <span className="text-xs font-semibold text-gray-400 uppercase">Pending Appeals</span>
                <div className="text-3xl font-extrabold text-pink-400 mt-2">{stats.pendingAppeals}</div>
              </div>
            </div>

            {/* MANAGEMENT ACTION MODULES (2 CARDS) */}
            <h2 className="text-lg font-bold text-gray-300 mb-4 flex items-center gap-2">
              <span>🛠️</span> System Operations & Management
            </h2>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mb-12">
              <div className="bg-gradient-to-br from-[#1e293b] to-[#0f172a] border border-gray-700 hover:border-blue-500/50 p-6 rounded-3xl shadow-xl transition duration-300 flex flex-col justify-between group">
                <div>
                  <div className="w-12 h-12 bg-blue-500/10 border border-blue-500/20 rounded-2xl flex items-center justify-center text-2xl mb-4 group-hover:scale-110 transition duration-300">
                    👨‍🎓
                  </div>
                  <h3 className="text-xl font-bold text-white mb-2">User Registration Portal</h3>
                  <p className="text-sm text-gray-400 mb-6 leading-relaxed">
                    Onboard new academic personnel, register students, and upload 10-20s facial videos for automated FaceNet vector database generation.
                  </p>
                </div>
                
                <Link
                  to="/admin/add-user"
                  className="w-full text-center bg-gradient-to-r from-blue-600 to-indigo-600 hover:from-blue-500 hover:to-indigo-500 text-white font-bold py-3 px-6 rounded-xl shadow-lg shadow-blue-500/20 transition duration-200 transform group-hover:translate-x-1 flex items-center justify-center gap-2"
                >
                  <span>Launch Registration Portal</span>
                  <span>➔</span>
                </Link>
              </div>

              <div className="bg-gradient-to-br from-[#1e293b] to-[#0f172a] border border-gray-700 hover:border-purple-500/50 p-6 rounded-3xl shadow-xl transition duration-300 flex flex-col justify-between group">
                <div>
                  <div className="w-12 h-12 bg-purple-500/10 border border-purple-500/20 rounded-2xl flex items-center justify-center text-2xl mb-4 group-hover:scale-110 transition duration-300">
                    📥
                  </div>
                  <h3 className="text-xl font-bold text-white mb-2">AI Session Data Upload</h3>
                  <p className="text-sm text-gray-400 mb-6 leading-relaxed">
                    Upload classroom behavior summary CSV logs generated by the ByteTrack unified pipeline directly into the live MongoDB database.
                  </p>
                </div>

                <button
                  type="button"
                  onClick={() => alert("Open CSV Upload Modal (Linked to your upload route)")}
                  className="w-full text-center bg-gradient-to-r from-purple-600 to-pink-600 hover:from-purple-500 hover:to-pink-500 text-white font-bold py-3 px-6 rounded-xl shadow-lg shadow-purple-500/20 transition duration-200 transform group-hover:translate-x-1 flex items-center justify-center gap-2"
                >
                  <span>Upload Classroom CSV</span>
                  <span>➔</span>
                </button>
              </div>
            </div>

            {/* LATEST PENDING APPEALS SECTION */}
            <div className="bg-[#1e293b]/90 border border-gray-700/80 rounded-3xl p-6 shadow-2xl">
              <div className="flex justify-between items-center pb-4 mb-6 border-b border-gray-700/80">
                <div>
                  <h3 className="text-xl font-bold text-white flex items-center gap-2">
                    <span>⚖️</span> Latest Student Appeals
                  </h3>
                  <p className="text-xs text-gray-400 mt-0.5">Review behavior penalties and attendance appeals submitted by students.</p>
                </div>
                <span className="bg-pink-500/10 text-pink-400 border border-pink-500/20 text-xs font-bold px-3 py-1.5 rounded-full">
                  {appealsList.length} Action Required
                </span>
              </div>

              {loading ? (
                <div className="text-center py-10 text-gray-400 font-medium">⏳ Loading live appeals from database...</div>
              ) : appealsList.length === 0 ? (
                <div className="text-center py-12 text-gray-500 font-medium bg-[#0f172a]/50 rounded-2xl border border-dashed border-gray-700">
                  ✅ No pending student appeals available. Everything is clean!
                </div>
              ) : (
                <div className="overflow-x-auto">
                  <table className="w-full text-left border-collapse">
                    <thead>
                      <tr className="border-b border-gray-700 text-xs font-semibold text-gray-400 uppercase tracking-wider bg-[#0f172a]/80">
                        <th className="py-3.5 px-4 rounded-l-xl">Student ID</th>
                        <th className="py-3.5 px-4">Name</th>
                        <th className="py-3.5 px-4">Appeal Date</th>
                        <th className="py-3.5 px-4">Violation / Reason</th>
                        <th className="py-3.5 px-4">Status</th>
                        <th className="py-3.5 px-4 text-right rounded-r-xl">Actions</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-gray-700/50 text-sm">
                      {appealsList.map((appeal, index) => (
                        <tr key={appeal._id || index} className="hover:bg-[#0f172a]/60 transition duration-150">
                          <td className="py-4 px-4 font-mono font-bold text-blue-400">{appeal.student_id}</td>
                          <td className="py-4 px-4 font-semibold text-white">{appeal.name}</td>
                          <td className="py-4 px-4 text-gray-400 text-xs">{appeal.date}</td>
                          <td className="py-4 px-4 text-gray-300 max-w-xs truncate">{appeal.reason}</td>
                          <td className="py-4 px-4">
                            <span className="bg-yellow-500/10 text-yellow-400 border border-yellow-500/30 text-xs font-bold px-2.5 py-1 rounded-full">
                              {appeal.status || "Pending"}
                            </span>
                          </td>
                          <td className="py-4 px-4 text-right">
                            <button type="button" className="bg-emerald-600/20 hover:bg-emerald-600 text-emerald-400 hover:text-white border border-emerald-500/30 text-xs font-bold px-3 py-1.5 rounded-lg mr-2 transition">
                              Approve
                            </button>
                            <button type="button" className="bg-red-600/20 hover:bg-red-600 text-red-400 hover:text-white border border-red-500/30 text-xs font-bold px-3 py-1.5 rounded-lg transition">
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

        {/* TAB 2: USER MANAGEMENT CONTENT (Only shows if activeTab is 'users') */}
        {activeTab === "users" && (
          <div className="animate-fadeIn">
            <UserManagement />
          </div>
        )}

      </div>
    </div>
  );
}