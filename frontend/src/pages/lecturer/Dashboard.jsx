// src/pages/lecturer/Dashboard.jsx

import React, { useEffect, useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";
import axios from "axios";
import Navbar from "../../components/Navbar";

import {
  getStudents,
  getAttendance,
  getBehavior,
  getSessions,
  sendEmail,
} from "../../api/api";

import {
  PieChart,
  Pie,
  Cell,
  Tooltip,
  Legend,
  ResponsiveContainer,
  BarChart,
  Bar,
  CartesianGrid,
  XAxis,
  YAxis,
} from "recharts";

const CHART_COLORS = {
  attendance: "#3b82f6",
  behavior: "#10b981",
  attentive: "#10b981",
  cheating: "#f43f5e",
  phone: "#f59e0b",
  sleeping: "#8b5cf6",
  good: "#10b981",
  warning: "#f59e0b",
  risk: "#f43f5e",
};

export default function LecturerDashboard() {
  const navigate = useNavigate();

  // Appeals States
  const [appealsList, setAppealsList] = useState([]);
  const [loadingAppeals, setLoadingAppeals] = useState(true);

  useEffect(() => {
    const fetchAppeals = async () => {
      try {
        const res = await axios.get("http://localhost:8000/api/appeals");
        const data = Array.isArray(res.data) ? res.data : (res.data?.data || []);
        setAppealsList(data);
      } catch (err) {
        console.error("Error fetching appeals:", err);
      } finally {
        setLoadingAppeals(false);
      }
    };
    fetchAppeals();
  }, []);

  const classroom = useMemo(() => {
    try {
      return (
        JSON.parse(localStorage.getItem("classroom")) || {
          year: "",
          sem: "",
          subject: "",
          group: "",
        }
      );
    } catch {
      return {
        year: "",
        sem: "",
        subject: "",
        group: "",
      };
    }
  }, []);

  const [students, setStudents] = useState([]);
  const [attendance, setAttendance] = useState([]);
  const [behavior, setBehavior] = useState([]);

  const [selected, setSelected] = useState(null);

  const [search, setSearch] = useState("");
  const [statusFilter, setStatusFilter] = useState("all");

  const [loading, setLoading] = useState(true);
  const [notifying, setNotifying] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    loadDashboard();
  }, []);

  const getArrayData = (response) => {
    if (Array.isArray(response)) return response;
    if (Array.isArray(response?.data)) return response.data;
    if (Array.isArray(response?.data?.data)) return response.data.data;
    return [];
  };

  const getSessionCount = (response) => {
    const possibleValues = [
      response?.count,
      response?.data?.count,
      response?.data?.total,
      response?.total,
    ];

    const validValue = possibleValues.find(
      (value) => value !== undefined && value !== null
    );

    return Number(validValue || 0);
  };

  async function loadDashboard() {
    setLoading(true);
    setError("");

    try {
      const [studentResponse, attendanceResponse, behaviorResponse, sessionResponse] =
        await Promise.all([
          getStudents(),
          getAttendance(),
          getBehavior(),
          getSessions(),
        ]);

      const rawStudentData = getArrayData(studentResponse);
      const attendanceData = getArrayData(attendanceResponse);
      const behaviorData = getArrayData(behaviorResponse);
      const totalSessions = getSessionCount(sessionResponse);

      setAttendance(attendanceData);
      setBehavior(behaviorData);

      // Filter students based on classroom
      const studentData = rawStudentData.filter((student) => {
        if (!classroom.year && !classroom.group) return true;

        const sYear = String(student.academic_year || student.year || "").replace("Year ", "").trim();
        const sSem = String(student.semester || student.sem || "").replace("Semester ", "").trim();
        const sGroup = String(student.group || "").replace("Group ", "").trim();

        const matchYear = !classroom.year || sYear === String(classroom.year);
        const matchSem = !classroom.sem || sSem === String(classroom.sem);
        const matchGroup = !classroom.group || sGroup === String(classroom.group);

        return matchYear && matchSem && matchGroup;
      });

      const calculatedStudents = studentData.map((student) => {
        const studentId = student.student_id || student.id || "";

        const attendanceRecords = attendanceData.filter(
          (record) =>
            String(record.student_id || record.id || "") === String(studentId)
        );

        const behaviorRecords = behaviorData.filter(
          (record) =>
            String(record.student_id || record.id || "") === String(studentId)
        );

        let attendanceRate = 0;
        if (totalSessions > 0) {
          attendanceRate = Math.min(
            Math.round((attendanceRecords.length / totalSessions) * 100),
            100
          );
        }

        let attentiveTime = 0;
        let cheatingTime = 0;
        let sleepingTime = 0;
        let phoneTime = 0;
        let notAttentiveTime = 0;

        behaviorRecords.forEach((record) => {
          attentiveTime += Number(record.attentive || 0);
          cheatingTime += Number(record.cheating || 0);
          sleepingTime += Number(record.sleeping || 0);
          phoneTime += Number(record.phone_use || 0);
          notAttentiveTime += Number(record.not_attentive || 0);
        });

        const totalBehaviorTime =
          attentiveTime + cheatingTime + sleepingTime + phoneTime + notAttentiveTime;

        const behaviorScore =
          totalBehaviorTime === 0
            ? 0
            : Math.round((attentiveTime / totalBehaviorTime) * 100);

        const overall = Math.round(attendanceRate * 0.4 + behaviorScore * 0.6);

        let status = "risk";
        if (overall >= 75) {
          status = "good";
        } else if (overall >= 60) {
          status = "warning";
        }

        return {
          id: studentId,
          name: student.name || student.student_name || "Unknown Student",
          intake: student.intake || "N/A",
          attendance: attendanceRate,
          behavior: behaviorScore,
          overall,
          status,
          email: student.email || `${String(studentId).toLowerCase()}@gmail.com`,
          attendanceRecords: attendanceRecords.length,
          behaviorRecords: behaviorRecords.length,
        };
      });

      calculatedStudents.sort((a, b) => b.overall - a.overall);
      setStudents(calculatedStudents);
    } catch (err) {
      console.error("Dashboard loading error:", err);
      setError(
        err?.response?.data?.detail ||
        err?.message ||
        "Unable to load lecturer dashboard data."
      );
    } finally {
      setLoading(false);
    }
  }

  const averageAttendance =
    students.length === 0
      ? 0
      : Math.round(
        students.reduce((total, student) => total + student.attendance, 0) /
        students.length
      );

  const averageBehavior =
    students.length === 0
      ? 0
      : Math.round(
        students.reduce((total, student) => total + student.behavior, 0) /
        students.length
      );

  const averageOverall =
    students.length === 0
      ? 0
      : Math.round(
        students.reduce((total, student) => total + student.overall, 0) /
        students.length
      );

  const riskyStudents = students.filter((student) => student.status === "risk");
  const warningStudents = students.filter((student) => student.status === "warning");
  const goodStudents = students.filter((student) => student.status === "good");

  const performanceData = students.slice(0, 10).map((student) => ({
    name: student.name.length > 12 ? `${student.name.substring(0, 12)}...` : student.name,
    Attendance: student.attendance,
    Behaviour: student.behavior,
  }));

  let attentive = 0;
  let cheating = 0;
  let sleeping = 0;
  let phone = 0;
  let notAttentive = 0;

  behavior.forEach((item) => {
    attentive += Number(item.attentive || 0);
    cheating += Number(item.cheating || 0);
    sleeping += Number(item.sleeping || 0);
    phone += Number(item.phone_use || 0);
    notAttentive += Number(item.not_attentive || 0);
  });

  const totalBehaviourTime = attentive + cheating + sleeping + phone + notAttentive;

  const calculatePercentage = (value) => {
    if (totalBehaviourTime === 0) return 0;
    return Number(((value / totalBehaviourTime) * 100).toFixed(1));
  };

  const behaviourData = [
    { name: "Attentive", value: calculatePercentage(attentive) },
    { name: "Cheating", value: calculatePercentage(cheating) },
    { name: "Phone Use", value: calculatePercentage(phone) },
    { name: "Sleeping", value: calculatePercentage(sleeping) },
    { name: "Not Attentive", value: calculatePercentage(notAttentive) },
  ].filter((item) => item.value > 0);

  const riskData = [
    { name: "Good", value: goodStudents.length },
    { name: "Warning", value: warningStudents.length },
    { name: "Risk", value: riskyStudents.length },
  ];

  const filteredStudents = students.filter((student) => {
    const query = search.trim().toLowerCase();
    const matchesSearch =
      student.id.toLowerCase().includes(query) ||
      student.name.toLowerCase().includes(query) ||
      student.intake.toLowerCase().includes(query);

    const matchesStatus = statusFilter === "all" || student.status === statusFilter;
    return matchesSearch && matchesStatus;
  });

  const escapeCSV = (value) => {
    const stringValue = String(value ?? "");
    return `"${stringValue.replace(/"/g, '""')}"`;
  };

  const exportCSV = () => {
    if (students.length === 0) {
      alert("No student data available to export.");
      return;
    }

    const headers = [
      "Rank",
      "Student ID",
      "Name",
      "Intake",
      "Attendance",
      "Behavior",
      "Overall",
      "Status",
    ];

    const rows = students.map((student, index) => [
      index + 1,
      student.id,
      student.name,
      student.intake,
      `${student.attendance}%`,
      `${student.behavior}%`,
      `${student.overall}%`,
      getStatusText(student.status),
    ]);

    const csvContent = [
      headers.map(escapeCSV).join(","),
      ...rows.map((row) => row.map(escapeCSV).join(",")),
    ].join("\n");

    const blob = new Blob([csvContent], { type: "text/csv;charset=utf-8;" });
    const url = window.URL.createObjectURL(blob);
    const link = document.createElement("a");

    link.href = url;
    link.download = `Student360_${classroom.subject || "Class"}_Report.csv`;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    window.URL.revokeObjectURL(url);
  };

  const notifyStudents = async () => {
    if (riskyStudents.length === 0) {
      alert("There are no risk students to notify.");
      return;
    }

    const emails = riskyStudents.map((student) => student.email).filter(Boolean);
    if (emails.length === 0) {
      alert("Risk students do not have valid email addresses.");
      return;
    }

    const studentList = riskyStudents
      .map(
        (student) => `
          <tr>
            <td style="padding:10px;border-bottom:1px solid #e5e7eb;">${student.name}</td>
            <td style="padding:10px;border-bottom:1px solid #e5e7eb;">${student.id}</td>
            <td style="padding:10px;border-bottom:1px solid #e5e7eb;color:#ef4444;font-weight:bold;">${student.overall}%</td>
          </tr>
        `
      )
      .join("");

    const htmlBody = `
      <!DOCTYPE html>
      <html>
        <head><meta charset="UTF-8" /></head>
        <body style="margin:0;padding:0;background:#f3f4f6;font-family:Arial,sans-serif;">
          <table width="100%" cellpadding="0" cellspacing="0">
            <tr>
              <td align="center" style="padding:30px 10px;">
                <table width="650" cellpadding="0" cellspacing="0" style="max-width:650px;background:white;border-radius:12px;overflow:hidden;box-shadow:0 0 15px rgba(0,0,0,.1);">
                  <tr>
                    <td style="background:#0f172a;padding:25px;color:white;text-align:center;">
                      <h1 style="margin:0;">🎓 Student360 AI</h1>
                      <p style="margin-top:8px;">AI Classroom Analytics System</p>
                    </td>
                  </tr>
                  <tr>
                    <td style="padding:35px;">
                      <h2 style="color:#ef4444;">Academic Performance Alert</h2>
                      <p>Dear Student,</p>
                      <p>The Student360 AI Classroom Monitoring System has identified that your classroom performance requires attention.</p>
                      <div style="margin-top:25px;background:#fef3c7;padding:18px;border-left:6px solid #f59e0b;">
                        <strong>AI Recommendation</strong>
                        <p>Attend lectures regularly, stay attentive, avoid phone usage and actively participate in classroom activities.</p>
                      </div>
                      <h3 style="margin-top:25px;">Students Requiring Attention</h3>
                      <table width="100%" style="border-collapse:collapse;margin-top:10px;">
                        <tr style="background:#f3f4f6;">
                          <th align="left" style="padding:10px;">Name</th>
                          <th align="left" style="padding:10px;">Student ID</th>
                          <th align="left" style="padding:10px;">Overall</th>
                        </tr>
                        ${studentList}
                      </table>
                    </td>
                  </tr>
                </table>
              </td>
            </tr>
          </table>
        </body>
      </html>
    `;

    try {
      setNotifying(true);
      const response = await sendEmail({
        emails,
        subject: "Student360 AI - Academic Performance Alert",
        body: htmlBody,
      });

      alert(response?.message || response?.data?.message || "Notifications sent successfully.");
    } catch (err) {
      console.error("Email sending error:", err);
      alert(err?.response?.data?.detail || "Email sending failed. Please check the backend.");
    } finally {
      setNotifying(false);
    }
  };

  function getStatusText(status) {
    if (status === "good") return "Good";
    if (status === "warning") return "Warning";
    return "Risk";
  }

  function getStatusClass(status) {
    if (status === "good") return "bg-emerald-950/60 text-emerald-400 border-emerald-500/30";
    if (status === "warning") return "bg-amber-950/60 text-amber-400 border-amber-500/30";
    return "bg-rose-950/60 text-rose-400 border-rose-500/30";
  }

  function getScoreClass(score) {
    if (score >= 75) return "text-emerald-400";
    if (score >= 60) return "text-amber-400";
    return "text-rose-400";
  }

  if (loading) {
    return (
      <div className="min-h-screen bg-[#030c18] flex flex-col items-center justify-center text-white">
        <div className="w-12 h-12 border-4 border-slate-700 border-t-blue-500 rounded-full animate-spin" />
        <h2 className="text-base font-semibold mt-4 text-slate-300">
          Syncing Faculty Classroom Analytics...
        </h2>
      </div>
    );
  }

  if (error) {
    return (
      <div className="min-h-screen bg-[#030c18] flex items-center justify-center text-white p-6">
        <div className="max-w-md w-full bg-[#081526] border border-rose-500/30 rounded-2xl p-8 text-center shadow-2xl">
          <div className="text-4xl mb-3">⚠️</div>
          <h2 className="text-lg font-bold">Dashboard Loading Failed</h2>
          <p className="text-slate-400 text-sm mt-2">{error}</p>
          <button
            onClick={loadDashboard}
            className="mt-6 bg-blue-600 hover:bg-blue-700 px-6 py-2.5 rounded-xl font-semibold text-sm transition"
          >
            Retry
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-[#030c18] text-slate-100 selection:bg-blue-600 selection:text-white pb-16">
      <Navbar />

      <main className="max-w-[1600px] mx-auto px-4 md:px-8 pt-7 space-y-7">

        {/* Classroom & Control Header Banner */}
        <section className="bg-[#081526] border border-slate-800 rounded-2xl p-6 sm:p-7 shadow-xl relative overflow-hidden">
          <div className="absolute top-0 right-10 w-96 h-36 bg-blue-500/10 rounded-full blur-3xl pointer-events-none" />

          <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-6 relative z-10">
            <div>
              <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-blue-500/10 border border-blue-500/20 mb-2">
                <span className="w-1.5 h-1.5 rounded-full bg-blue-400 animate-pulse" />
                <span className="text-xs font-bold uppercase tracking-wider text-blue-400">
                  Lecturer Intelligence Console
                </span>
              </div>

              <h1 className="text-2xl sm:text-3xl font-black tracking-tight text-white flex items-center gap-3">
                <span>Subject:</span>
                <span className="bg-gradient-to-r from-blue-400 via-sky-300 to-teal-300 bg-clip-text text-transparent">
                  {classroom.subject || "All Assigned Classrooms"}
                </span>
              </h1>

              {/* Badges + Change Classroom button in one line */}
              <div className="mt-3 flex flex-wrap items-center gap-2.5 text-xs">
                <ClassroomBadge label="Year" value={classroom.year ? `Year ${classroom.year}` : "N/A"} />
                <ClassroomBadge label="Semester" value={classroom.sem ? `Semester ${classroom.sem}` : "N/A"} />
                <ClassroomBadge label="Group" value={classroom.group ? `Group ${classroom.group}` : "N/A"} />

                <button
                  onClick={() => navigate("/lecturer/classroom")}
                  className="px-3 py-1 rounded-lg bg-slate-900/90 hover:bg-slate-800 border border-slate-700/80 text-blue-400 hover:text-blue-300 text-xs font-semibold transition flex items-center gap-1.5 ml-1"
                >
                  <span>✏️</span> Change Classroom
                </button>
              </div>
            </div>

            {/* Right Action Buttons */}
            <div className="flex flex-wrap items-center gap-3">
              <button
                onClick={() => window.open("/lecturer/monitoring", "_blank")}
                className="px-5 py-2.5 rounded-xl font-bold text-xs uppercase tracking-wider bg-gradient-to-r from-blue-600 via-indigo-600 to-purple-600 hover:from-blue-500 hover:to-purple-500 text-white shadow-lg shadow-blue-500/25 border border-blue-400/30 flex items-center gap-2 transition-all transform hover:scale-[1.02]"
              >
                <span className="w-2.5 h-2.5 rounded-full bg-cyan-400 animate-ping" />
                Launch Live AI Console
              </button>

              <button
                onClick={exportCSV}
                className="px-4 py-2.5 rounded-xl bg-emerald-600/20 hover:bg-emerald-600 text-emerald-400 hover:text-white border border-emerald-500/30 text-xs font-bold transition"
              >
                Export CSV
              </button>
            </div>
          </div>
        </section>

        {/* Summary Cards */}
        <section className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-4 gap-4">
          <SummaryCard
            title="Total Students"
            value={students.length}
            subtitle="Registered in cohort"
            icon="👥"
          />
          <SummaryCard
            title="Avg Attendance"
            value={`${averageAttendance}%`}
            subtitle={`${attendance.length} total presences`}
            icon="📅"
            valueClass={getScoreClass(averageAttendance)}
          />
          <SummaryCard
            title="Avg Behaviour"
            value={`${averageBehavior}%`}
            subtitle={`${behavior.length} behavior vectors logged`}
            icon="🧠"
            valueClass={getScoreClass(averageBehavior)}
          />
          <SummaryCard
            title="At-Risk Students"
            value={riskyStudents.length}
            subtitle="Under 60% threshold"
            icon="⚠️"
            valueClass="text-rose-400"
          />
        </section>

        {/* Performance Distribution Indicators */}
        <section className="grid grid-cols-1 lg:grid-cols-3 gap-4">
          <PerformanceCard
            title="Classroom Aggregated Performance"
            value={averageOverall}
            description="Combined attendance (40%) and attention behavior (60%)"
          />
          <StatusCard
            title="Compliant Students (Good)"
            value={goodStudents.length}
            description="Scoring above 75% overall engagement"
            type="good"
          />
          <StatusCard
            title="Borderline (Warning)"
            value={warningStudents.length}
            description="Scoring between 60% and 74%"
            type="warning"
          />
        </section>

        {/* At-Risk Alert Banner */}
        {riskyStudents.length > 0 && (
          <section className="bg-rose-950/40 border border-rose-500/30 rounded-2xl p-5 shadow-xl flex flex-col md:flex-row md:items-center justify-between gap-4">
            <div className="flex items-start gap-4">
              <div className="text-3xl">🚨</div>
              <div>
                <h3 className="text-base font-bold text-rose-300">
                  Academic Performance Notice
                </h3>
                <p className="text-slate-300 text-xs mt-1">
                  {riskyStudents.length} student{riskyStudents.length !== 1 ? "s have" : " has"} an aggregate score below 60%.
                </p>
              </div>
            </div>

            <button
              onClick={notifyStudents}
              disabled={notifying}
              className="bg-rose-600 hover:bg-rose-700 disabled:opacity-50 text-white px-5 py-2.5 rounded-xl text-xs font-bold transition shadow-lg shadow-rose-600/30"
            >
              {notifying ? "Dispatching Emails..." : "Notify Risk Students"}
            </button>
          </section>
        )}

        {/* Search & Filter Bar */}
        <section className="flex flex-col sm:flex-row justify-between gap-4">
          <div className="flex flex-1 gap-3">
            <input
              type="text"
              placeholder="Filter by student ID, name or intake..."
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              className="flex-1 bg-[#081526] border border-slate-800 p-3 rounded-xl outline-none focus:border-blue-500 text-xs text-white"
            />
            <select
              value={statusFilter}
              onChange={(e) => setStatusFilter(e.target.value)}
              className="bg-[#081526] border border-slate-800 p-3 rounded-xl outline-none focus:border-blue-500 text-xs text-slate-300"
            >
              <option value="all">All Statuses</option>
              <option value="good">Good Status</option>
              <option value="warning">Warning</option>
              <option value="risk">At-Risk</option>
            </select>
          </div>

          <button
            onClick={loadDashboard}
            className="px-4 py-3 bg-[#081526] hover:bg-slate-800 border border-slate-800 rounded-xl text-xs font-bold transition text-slate-300"
          >
            ↻ Refresh Records
          </button>
        </section>

        {/* Analytics Charts */}
        <section className="grid grid-cols-1 xl:grid-cols-2 gap-5">
          {/* Attendance vs Behavior */}
          <div className="bg-[#081526] border border-slate-800 rounded-2xl p-5 shadow-xl">
            <div className="mb-4">
              <h2 className="text-sm font-bold text-white uppercase tracking-wide">
                Cohort Engagement (Top 10)
              </h2>
              <p className="text-xs text-slate-400 mt-0.5">
                Attendance rate compared with computer-vision attention score
              </p>
            </div>

            {performanceData.length > 0 ? (
              <ResponsiveContainer width="100%" height={290}>
                <BarChart data={performanceData} margin={{ top: 10, right: 10, left: -20, bottom: 25 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" vertical={false} />
                  <XAxis dataKey="name" stroke="#64748b" angle={-15} textAnchor="end" height={50} tick={{ fontSize: 10 }} />
                  <YAxis domain={[0, 100]} stroke="#64748b" tick={{ fontSize: 10 }} />
                  <Tooltip
                    contentStyle={{
                      backgroundColor: "#0b1a2e",
                      border: "1px solid #1e293b",
                      borderRadius: "10px",
                      color: "#fff",
                      fontSize: "12px",
                    }}
                  />
                  <Legend wrapperStyle={{ fontSize: "11px" }} />
                  <Bar dataKey="Attendance" fill={CHART_COLORS.attendance} radius={[4, 4, 0, 0]} />
                  <Bar dataKey="Behaviour" fill={CHART_COLORS.behavior} radius={[4, 4, 0, 0]} />
                </BarChart>
              </ResponsiveContainer>
            ) : (
              <EmptyChart message="No performance metrics registered for current classroom." />
            )}
          </div>

          {/* Behavior Breakdown Pie */}
          <div className="bg-[#081526] border border-slate-800 rounded-2xl p-5 shadow-xl">
            <div className="mb-4">
              <h2 className="text-sm font-bold text-white uppercase tracking-wide">
                Cumulative AI Behavioral Breakdown
              </h2>
              <p className="text-xs text-slate-400 mt-0.5">
                Ratio of monitored classroom posture and gaze events
              </p>
            </div>

            {behaviourData.length > 0 ? (
              <ResponsiveContainer width="100%" height={290}>
                <PieChart>
                  <Pie
                    data={behaviourData}
                    dataKey="value"
                    nameKey="name"
                    innerRadius={65}
                    outerRadius={95}
                    paddingAngle={3}
                  >
                    <Cell fill={CHART_COLORS.attentive} />
                    <Cell fill={CHART_COLORS.cheating} />
                    <Cell fill={CHART_COLORS.phone} />
                    <Cell fill={CHART_COLORS.sleeping} />
                    <Cell fill="#64748b" />
                  </Pie>
                  <Tooltip
                    formatter={(value) => `${value}%`}
                    contentStyle={{
                      backgroundColor: "#0b1a2e",
                      border: "1px solid #1e293b",
                      borderRadius: "10px",
                      color: "#fff",
                      fontSize: "12px",
                    }}
                  />
                  <Legend wrapperStyle={{ fontSize: "11px" }} />
                </PieChart>
              </ResponsiveContainer>
            ) : (
              <EmptyChart message="No behavioral records detected." />
            )}
          </div>
        </section>

        {/* Student Table */}
        <section className="bg-[#081526] border border-slate-800 rounded-2xl shadow-xl overflow-hidden">
          <div className="p-5 border-b border-slate-800 flex justify-between items-center">
            <div>
              <h2 className="text-sm font-bold text-white uppercase tracking-wide">
                Classroom Student Index
              </h2>
              <p className="text-xs text-slate-400 mt-0.5">
                Showing {filteredStudents.length} of {students.length} students enrolled
              </p>
            </div>
          </div>

          <div className="overflow-x-auto">
            <table className="w-full min-w-[900px] text-left">
              <thead className="bg-[#0b1a2e] text-xs font-semibold text-slate-400 uppercase tracking-wider">
                <tr>
                  <th className="p-3.5 text-center">Rank</th>
                  <th className="p-3.5">Student</th>
                  <th className="p-3.5">Intake</th>
                  <th className="p-3.5 text-center">Attendance</th>
                  <th className="p-3.5 text-center">Attention</th>
                  <th className="p-3.5 text-center">Aggregate</th>
                  <th className="p-3.5 text-center">Status</th>
                  <th className="p-3.5 text-center">Action</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-800 text-sm">
                {filteredStudents.length > 0 ? (
                  filteredStudents.map((student) => {
                    const actualRank = students.findIndex((item) => item.id === student.id) + 1;
                    return (
                      <tr key={student.id} className="hover:bg-[#0c1e36]/50 transition">
                        <td className="p-3.5 text-center font-mono font-bold text-blue-400">
                          #{actualRank}
                        </td>
                        <td className="p-3.5">
                          <p className="font-semibold text-white">{student.name}</p>
                          <p className="text-xs font-mono text-slate-400">{student.id}</p>
                        </td>
                        <td className="p-3.5 text-slate-300 text-xs">{student.intake}</td>
                        <td className="p-3.5 text-center">
                          <ScoreBadge value={student.attendance} />
                        </td>
                        <td className="p-3.5 text-center">
                          <ScoreBadge value={student.behavior} />
                        </td>
                        <td className={`p-3.5 text-center font-bold ${getScoreClass(student.overall)}`}>
                          {student.overall}%
                        </td>
                        <td className="p-3.5 text-center">
                          <span className={`inline-flex px-2.5 py-0.5 rounded-full text-xs font-bold border ${getStatusClass(student.status)}`}>
                            {getStatusText(student.status)}
                          </span>
                        </td>
                        <td className="p-3.5 text-center">
                          <button
                            onClick={() => setSelected(student)}
                            className="bg-blue-600/20 hover:bg-blue-600 text-blue-400 hover:text-white border border-blue-500/30 px-3 py-1 rounded-lg text-xs font-bold transition"
                          >
                            Details
                          </button>
                        </td>
                      </tr>
                    );
                  })
                ) : (
                  <tr>
                    <td colSpan="8" className="p-10 text-center text-slate-500 text-xs">
                      No matching students found for current classroom filter.
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        </section>

        {/* Appeals Status Log (Read-Only) */}
        <section className="bg-[#081526] border border-slate-800 rounded-2xl p-6 shadow-xl">
          <div className="flex justify-between items-center pb-4 mb-4 border-b border-slate-800">
            <div>
              <h2 className="text-sm font-bold text-white uppercase tracking-wide">
                Student Appeals Log (Classroom Audit)
              </h2>
              <p className="text-xs text-slate-400 mt-0.5">
                Overview of submitted student grievances and administrative resolutions
              </p>
            </div>
            <span className="bg-blue-500/10 text-blue-400 border border-blue-500/20 text-xs font-bold px-3 py-1 rounded-full">
              {appealsList?.length || 0} Total
            </span>
          </div>

          {loadingAppeals ? (
            <div className="text-center py-6 text-slate-500 text-xs">⏳ Loading appeals...</div>
          ) : !appealsList || appealsList.length === 0 ? (
            <div className="text-center py-6 text-slate-500 text-xs bg-[#0b1a2e] rounded-xl border border-dashed border-slate-800">
              No appeals logged for review.
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-left text-xs">
                <thead>
                  <tr className="border-b border-slate-800 text-slate-400 uppercase bg-[#0b1a2e]">
                    <th className="py-2.5 px-3">Student ID</th>
                    <th className="py-2.5 px-3">Appeal Reason</th>
                    <th className="py-2.5 px-3">Date</th>
                    <th className="py-2.5 px-3">Status</th>
                    <th className="py-2.5 px-3">Resolution Remarks</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-800/60">
                  {appealsList.map((appeal, index) => (
                    <tr key={appeal._id || index} className="hover:bg-[#0c1e36]/30">
                      <td className="py-3 px-3 font-mono font-bold text-blue-400">
                        {appeal.student_id || appeal.user_id || "N/A"}
                      </td>
                      <td className="py-3 px-3 text-slate-300 max-w-xs truncate">
                        {appeal.reason || appeal.message || appeal.description}
                      </td>
                      <td className="py-3 px-3 text-slate-400">
                        {appeal.date || appeal.created_at?.substring(0, 10) || "N/A"}
                      </td>
                      <td className="py-3 px-3">
                        <span className={`px-2 py-0.5 rounded-full font-bold border ${appeal.status === "Approved" ? "bg-emerald-950/60 text-emerald-400 border-emerald-500/30" :
                            appeal.status === "Rejected" ? "bg-rose-950/60 text-rose-400 border-rose-500/30" :
                              "bg-amber-950/60 text-amber-400 border-amber-500/30"
                          }`}>
                          {appeal.status || "Pending"}
                        </span>
                      </td>
                      <td className="py-3 px-3 italic text-slate-400">
                        {appeal.admin_response ? `"${appeal.admin_response}"` : "Pending decision..."}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </section>

      </main>

      {/* Student Detail Modal */}
      {selected && (
        <div
          className="fixed inset-0 bg-black/75 backdrop-blur-sm flex items-center justify-center z-50 p-4"
          onClick={() => setSelected(null)}
        >
          <div
            className="bg-[#081526] border border-slate-800 rounded-2xl w-full max-w-lg shadow-2xl overflow-hidden"
            onClick={(e) => e.stopPropagation()}
          >
            <div className="bg-gradient-to-r from-blue-900/40 via-indigo-900/40 to-slate-900 p-6 flex justify-between items-start border-b border-slate-800">
              <div>
                <span className="text-xs font-bold uppercase tracking-wider text-blue-400">
                  Student Verification Record
                </span>
                <h2 className="text-2xl font-black text-white mt-1">{selected.name}</h2>
                <p className="text-xs font-mono text-slate-400">{selected.id}</p>
              </div>

              <button
                onClick={() => setSelected(null)}
                className="w-8 h-8 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-300 transition flex items-center justify-center text-sm font-bold"
              >
                ✕
              </button>
            </div>

            <div className="p-6 space-y-5">
              <div className="grid grid-cols-2 gap-3">
                <DetailItem label="Intake" value={selected.intake} />
                <DetailItem label="Email" value={selected.email} />
                <DetailItem label="Attendance Logs" value={selected.attendanceRecords} />
                <DetailItem label="Behavior Events" value={selected.behaviorRecords} />
              </div>

              <div className="space-y-4 pt-2">
                <ProgressScore label="Attendance Rate" value={selected.attendance} />
                <ProgressScore label="Attention Integrity" value={selected.behavior} />
                <ProgressScore label="Aggregate Score" value={selected.overall} />
              </div>

              <div className="bg-[#0b1a2e] border border-slate-800 rounded-xl p-3.5 flex items-center justify-between">
                <span className="text-xs text-slate-400 font-semibold">Evaluation Status</span>
                <span className={`px-3 py-1 rounded-full text-xs font-bold border ${getStatusClass(selected.status)}`}>
                  {getStatusText(selected.status)}
                </span>
              </div>

              <button
                onClick={() => setSelected(null)}
                className="w-full bg-blue-600 hover:bg-blue-700 py-2.5 rounded-xl text-white font-bold text-xs transition"
              >
                Close Record
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

function SummaryCard({ title, value, subtitle, icon, valueClass = "text-white" }) {
  return (
    <div className="bg-[#081526] border border-slate-800 rounded-2xl p-5 shadow-xl hover:border-slate-700 transition flex flex-col justify-between">
      <div className="flex items-center justify-between">
        <span className="text-xs font-bold uppercase tracking-wider text-slate-400">{title}</span>
        <span className="text-xl p-1.5 bg-slate-900 rounded-xl border border-slate-800">{icon}</span>
      </div>
      <div className={`text-3xl font-black mt-3 mb-1 tracking-tight ${valueClass}`}>{value}</div>
      <span className="text-[11px] text-slate-400 font-semibold">{subtitle}</span>
    </div>
  );
}

function PerformanceCard({ title, value, description }) {
  return (
    <div className="bg-[#081526] border border-slate-800 rounded-2xl p-5 shadow-xl flex flex-col justify-between">
      <div>
        <span className="text-xs font-bold uppercase tracking-wider text-slate-400">{title}</span>
        <div className="text-4xl font-black text-white mt-2">{value}%</div>
      </div>
      <div className="w-full h-2 bg-slate-900 rounded-full mt-4 overflow-hidden border border-slate-800">
        <div className="h-full bg-blue-500 rounded-full transition-all duration-700" style={{ width: `${Math.min(value, 100)}%` }} />
      </div>
      <p className="text-[11px] text-slate-400 mt-2">{description}</p>
    </div>
  );
}

function StatusCard({ title, value, description, type }) {
  const isGood = type === "good";
  return (
    <div className="bg-[#081526] border border-slate-800 rounded-2xl p-5 shadow-xl flex flex-col justify-between">
      <div>
        <span className="text-xs font-bold uppercase tracking-wider text-slate-400">{title}</span>
        <div className={`text-4xl font-black mt-2 ${isGood ? "text-emerald-400" : "text-amber-400"}`}>
          {value}
        </div>
      </div>
      <p className="text-[11px] text-slate-400 mt-4">{description}</p>
    </div>
  );
}

function ClassroomBadge({ label, value }) {
  return (
    <div className="bg-slate-900/90 border border-slate-800 rounded-lg px-3 py-1">
      <span className="text-slate-500 text-[11px]">{label}:</span>{" "}
      <span className="font-semibold text-slate-200 text-xs">{value}</span>
    </div>
  );
}

function ScoreBadge({ value }) {
  let className = "bg-rose-950/60 text-rose-400 border-rose-500/30";
  if (value >= 75) {
    className = "bg-emerald-950/60 text-emerald-400 border-emerald-500/30";
  } else if (value >= 60) {
    className = "bg-amber-950/60 text-amber-400 border-amber-500/30";
  }

  return (
    <span className={`inline-flex min-w-[55px] justify-center px-2.5 py-0.5 rounded-md text-xs font-bold border ${className}`}>
      {value}%
    </span>
  );
}

function DetailItem({ label, value }) {
  return (
    <div className="bg-[#0b1a2e] border border-slate-800 rounded-xl p-3">
      <p className="text-[10px] font-bold uppercase tracking-wider text-slate-400">{label}</p>
      <p className="font-semibold text-white text-xs mt-1 truncate">{value}</p>
    </div>
  );
}

function ProgressScore({ label, value }) {
  let barClass = "bg-rose-500";
  if (value >= 75) barClass = "bg-emerald-500";
  else if (value >= 60) barClass = "bg-amber-500";

  return (
    <div>
      <div className="flex justify-between text-xs mb-1">
        <span className="text-slate-400">{label}</span>
        <span className="font-bold text-white">{value}%</span>
      </div>
      <div className="w-full h-1.5 bg-slate-900 rounded-full overflow-hidden border border-slate-800">
        <div className={`h-full rounded-full ${barClass}`} style={{ width: `${Math.min(value, 100)}%` }} />
      </div>
    </div>
  );
}

function EmptyChart({ message }) {
  return (
    <div className="h-[250px] flex flex-col items-center justify-center text-slate-500 text-xs">
      <div className="text-3xl mb-2">📊</div>
      <p>{message}</p>
    </div>
  );
}