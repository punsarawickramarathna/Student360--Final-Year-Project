// src/pages/student/Dashboard.jsx

import React, {
  useEffect,
  useMemo,
  useRef,
  useState,
} from "react";

import { useNavigate } from "react-router-dom";

import Navbar from "../../components/Navbar";
import AttendanceTable from "../../components/AttendanceTable";

import html2canvas from "html2canvas";
import jsPDF from "jspdf";

import {
  AreaChart,
  Area,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  BarChart,
  Bar,
  PieChart,
  Pie,
  Cell,
  Legend,
} from "recharts";

import {
  getAttendance,
  getBehavior,
  getAppeals,
  getSessions,
} from "../../api/api";

const BEHAVIOR_COLORS = [
  "#3b82f6",
  "#ef4444",
  "#f59e0b",
  "#a855f7",
  "#64748b",
];

export default function StudentDashboard() {
  const navigate = useNavigate();
  const dashboardRef = useRef(null);

  const student = useMemo(() => {
    try {
      return JSON.parse(localStorage.getItem("user")) || {};
    } catch {
      return {};
    }
  }, []);

  const [attendance, setAttendance] = useState([]);
  const [behavior, setBehavior] = useState([]);
  const [appeals, setAppeals] = useState([]);
  const [sessions, setSessions] = useState({ count: 0, data: [] });

  const [loading, setLoading] = useState(true);
  const [downloading, setDownloading] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    loadData();
  }, []);

  const getArrayData = (response) => {
    if (Array.isArray(response)) return response;
    if (Array.isArray(response?.data)) return response.data;
    if (Array.isArray(response?.data?.data)) return response.data.data;
    return [];
  };

  const getSessionData = (response) => {
    if (Array.isArray(response?.data)) {
      return { count: response.data.length, data: response.data };
    }
    if (response?.data && typeof response.data === "object") {
      return {
        count: Number(response.data.count || response.data.total || response.data.data?.length || 0),
        data: Array.isArray(response.data.data) ? response.data.data : [],
      };
    }
    if (response && typeof response === "object") {
      return {
        count: Number(response.count || response.total || response.data?.length || 0),
        data: Array.isArray(response.data) ? response.data : [],
      };
    }
    return { count: 0, data: [] };
  };

  async function loadData() {
    setLoading(true);
    setError("");

    try {
      const [
        attendanceResponse,
        behaviorResponse,
        appealsResponse,
        sessionsResponse,
      ] = await Promise.all([
        getAttendance(),
        getBehavior(),
        getAppeals(),
        getSessions(),
      ]);

      setAttendance(getArrayData(attendanceResponse));
      setBehavior(getArrayData(behaviorResponse));
      setAppeals(getArrayData(appealsResponse));
      setSessions(getSessionData(sessionsResponse));
    } catch (err) {
      console.error("Student dashboard error:", err);
      setError(
        err?.response?.data?.detail ||
        err?.message ||
        "Unable to load student dashboard data."
      );
    } finally {
      setLoading(false);
    }
  }

  const studentId =
    student.student_id ||
    student.id ||
    student.username ||
    "";

  const sameStudent = (record) => {
    if (!record) return false;
    const recordId = String(
      record?.student_id || record?.studentId || record?.user_id || record?.id || ""
    ).trim().toLowerCase();
    const currentStudentId = String(studentId).trim().toLowerCase();
    return recordId === currentStudentId;
  };

  const myAttendance = attendance.filter(sameStudent);
  const myBehavior = behavior.filter(sameStudent);
  const myAppeals = appeals.filter(sameStudent);

  const isExamRecord = (item) => {
    const sessionType = String(
      item.session_type || item.type || item.session_category || ""
    ).toLowerCase();

    if (sessionType) {
      return sessionType === "exam" || sessionType === "examination";
    }

    const nonCheating = Number(item.non_cheating ?? item.non_cheating_sec ?? 0);
    return nonCheating > 0;
  };

  const myExamBehavior = myBehavior.filter(isExamRecord);
  const myLectureBehavior = myBehavior.filter((item) => !isExamRecord(item));

  const totalSessions = Number(sessions.count || sessions.data?.length || 0);

  const attendanceRate =
    totalSessions > 0
      ? Math.min(Math.round((myAttendance.length / totalSessions) * 100), 100)
      : 0;

  let attentiveTime = 0;
  let sleepingTime = 0;
  let phoneUseTime = 0;
  let notAttentiveTime = 0;
  let lectureCheatingTime = 0;

  myLectureBehavior.forEach((item) => {
    attentiveTime += Number(item.attentive ?? item.attentive_sec ?? 0);
    sleepingTime += Number(item.sleeping ?? item.sleeping_sec ?? 0);
    phoneUseTime += Number(item.phone_use ?? item.phone_use_sec ?? 0);
    notAttentiveTime += Number(item.not_attentive ?? item.not_attentive_sec ?? 0);
    lectureCheatingTime += Number(item.cheating ?? item.cheating_sec ?? 0);
  });

  const totalLectureBehaviorTime =
    attentiveTime + sleepingTime + phoneUseTime + notAttentiveTime + lectureCheatingTime;

  const behaviorScore =
    totalLectureBehaviorTime === 0
      ? 0
      : Math.round((attentiveTime / totalLectureBehaviorTime) * 100);

  let examCheatingTime = 0;
  let nonCheatingTime = 0;

  myExamBehavior.forEach((item) => {
    examCheatingTime += Number(item.cheating ?? item.cheating_sec ?? 0);
    nonCheatingTime += Number(item.non_cheating ?? item.non_cheating_sec ?? 0);
  });

  const totalExamBehaviorTime = examCheatingTime + nonCheatingTime;
  const hasExamData = totalExamBehaviorTime > 0;

  const examBehaviorScore = hasExamData
    ? Math.round((nonCheatingTime / totalExamBehaviorTime) * 100)
    : null;

  const latestExamRecord =
    myExamBehavior.length > 0
      ? [...myExamBehavior].sort((a, b) => {
        const firstDate = new Date(a.created_at || a.date || 0);
        const secondDate = new Date(b.created_at || b.date || 0);
        return secondDate - firstDate;
      })[0]
      : null;

  let examStatus = "No Data";
  if (examBehaviorScore !== null) {
    if (examBehaviorScore >= 80) examStatus = "Good";
    else if (examBehaviorScore >= 60) examStatus = "Warning";
    else examStatus = "Suspicious";
  }

  const scoreValues = [attendanceRate, behaviorScore];
  if (examBehaviorScore !== null) scoreValues.push(examBehaviorScore);

  const overallScore =
    scoreValues.length === 0
      ? 0
      : Math.round(
        scoreValues.reduce((total, value) => total + value, 0) / scoreValues.length
      );

  let badge = "";
  let badgeColor = "";

  if (overallScore >= 80) {
    badge = "Excellent Student 🏆";
    badgeColor = "text-emerald-400 bg-emerald-950/60 border-emerald-500/30";
  } else if (overallScore >= 60) {
    badge = "Good Student 👍";
    badgeColor = "text-amber-400 bg-amber-950/60 border-amber-500/30";
  } else {
    badge = "Needs Improvement ⚠️️";
    badgeColor = "text-rose-400 bg-rose-950/60 border-rose-500/30";
  }

  const attendanceTrendData = myAttendance.map((item, index) => {
    const status = String(item.status || "Present").toLowerCase();
    return {
      label: item.date || `Session ${index + 1}`,
      score: status === "absent" ? 0 : 100,
    };
  });

  const scoreComparisonData = [
    { name: "Attendance", value: attendanceRate },
    { name: "Lecture Attention", value: behaviorScore },
    { name: "Exam Integrity", value: examBehaviorScore === null ? 0 : examBehaviorScore },
  ];

  const lectureBehaviorData = [
    { name: "Attentive", value: Number(attentiveTime.toFixed(1)) },
    { name: "Sleeping", value: Number(sleepingTime.toFixed(1)) },
    { name: "Phone Use", value: Number(phoneUseTime.toFixed(1)) },
    { name: "Not Attentive", value: Number(notAttentiveTime.toFixed(1)) },
    { name: "Suspicious", value: Number(lectureCheatingTime.toFixed(1)) },
  ].filter((item) => item.value > 0);

  const attendanceRecords = myAttendance.map((item) => ({
    date: item.date || item.created_at || "-",
    status: item.status || "Present",
  }));

  const downloadPDF = async () => {
    if (!dashboardRef.current) return;
    try {
      setDownloading(true);
      const canvas = await html2canvas(dashboardRef.current, {
        scale: 2,
        useCORS: true,
        backgroundColor: "#030c18",
      });

      const imageData = canvas.toDataURL("image/png");
      const pdf = new jsPDF("p", "mm", "a4");
      const pdfWidth = pdf.internal.pageSize.getWidth();
      const pageHeight = pdf.internal.pageSize.getHeight();
      const imageHeight = (canvas.height * pdfWidth) / canvas.width;

      let heightLeft = imageHeight;
      let position = 0;

      pdf.addImage(imageData, "PNG", 0, position, pdfWidth, imageHeight);
      heightLeft -= pageHeight;

      while (heightLeft > 0) {
        position = heightLeft - imageHeight;
        pdf.addPage();
        pdf.addImage(imageData, "PNG", 0, position, pdfWidth, imageHeight);
        heightLeft -= pageHeight;
      }

      pdf.save(`Student360_${studentId || "Student"}_Report.pdf`);
    } catch (err) {
      console.error("PDF error:", err);
      alert("Unable to generate PDF report.");
    } finally {
      setDownloading(false);
    }
  };

  const getScoreColor = (score) => {
    if (score >= 80) return "text-emerald-400";
    if (score >= 60) return "text-amber-400";
    return "text-rose-400";
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-[#030c18] flex flex-col items-center justify-center text-white">
        <div className="w-12 h-12 rounded-full border-4 border-slate-700 border-t-blue-500 animate-spin" />
        <h2 className="text-base font-semibold mt-4 text-slate-300">
          Syncing Academic Records...
        </h2>
      </div>
    );
  }

  if (error) {
    return (
      <div className="min-h-screen bg-[#030c18] flex items-center justify-center p-4">
        <div className="w-full max-w-md bg-[#091728] border border-rose-500/30 rounded-2xl p-6 text-center text-white">
          <h2 className="text-lg font-bold">Failed to Load Dashboard</h2>
          <p className="text-slate-400 text-sm mt-2">{error}</p>
          <button
            onClick={loadData}
            className="mt-4 bg-blue-600 hover:bg-blue-700 text-white font-semibold px-5 py-2 rounded-xl text-sm transition"
          >
            Retry
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-[#030c18] text-slate-100 selection:bg-blue-600 selection:text-white pb-14">
      <Navbar />

      <main ref={dashboardRef} className="max-w-7xl mx-auto px-4 sm:px-6 pt-7 space-y-6">

        {/* Welcome Hero Banner (Logo & Student360 Removed - Clean Gradient Mix) */}
        <section className="bg-[#081526] border border-slate-800/90 rounded-2xl p-6 sm:p-7 shadow-xl relative overflow-hidden">
          <div className="absolute top-0 right-1/4 w-80 h-32 bg-blue-500/10 rounded-full blur-3xl pointer-events-none" />

          <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-5 relative z-10">
            <div>
              {/* Subtle Tagline */}
              <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-gradient-to-r from-blue-500/15 via-indigo-500/15 to-purple-500/15 border border-blue-500/25 mb-3">
                <span className="w-1.5 h-1.5 rounded-full bg-blue-400 animate-pulse" />
                <span className="text-xs font-bold uppercase tracking-wider bg-gradient-to-r from-blue-400 via-sky-300 to-indigo-300 bg-clip-text text-transparent">
                  Student Academic Portal
                </span>
              </div>

              {/* Mix Color Welcome Headline */}
              <h1 className="text-2xl sm:text-3xl font-black tracking-tight text-white flex items-center flex-wrap gap-2">
                <span>Welcome,</span>
                <span className="bg-gradient-to-r from-blue-400 via-sky-300 to-teal-300 bg-clip-text text-transparent capitalize">
                  {student.name || "Student"}
                </span>
              </h1>

              {/* Student Metadata Badges */}
              <div className="mt-3 flex flex-wrap items-center gap-x-3 gap-y-2 text-sm">
                <span className="font-mono font-semibold text-sky-400 bg-slate-900/90 px-2.5 py-1 rounded-lg border border-slate-800 text-xs shadow-inner">
                  {studentId}
                </span>

                {student.intake && (
                  <>
                    <span className="text-slate-600">•</span>
                    <span className="text-slate-400 text-xs font-medium bg-slate-900/50 px-2.5 py-1 rounded-lg border border-slate-800/60">
                      Intake {student.intake}
                    </span>
                  </>
                )}

                <span className="text-slate-600">•</span>
                <span className={`inline-flex px-3 py-1 rounded-full text-xs font-bold border shadow-xs ${badgeColor}`}>
                  {badge}
                </span>
              </div>
            </div>

            {/* Quick Actions */}
            <div className="flex items-center gap-3">
              <button
                onClick={() => navigate("/student/appeal/new")}
                className="px-5 py-2.5 rounded-xl bg-gradient-to-r from-blue-600 to-blue-500 hover:from-blue-500 hover:to-blue-600 text-white font-bold text-xs shadow-lg shadow-blue-600/30 hover:scale-[1.02] active:scale-[0.98] transition"
              >
                + Submit New Appeal
              </button>
              <button
                onClick={downloadPDF}
                disabled={downloading}
                className="px-4 py-2.5 rounded-xl bg-slate-900/90 hover:bg-slate-800 border border-slate-700/80 text-slate-200 font-bold text-xs transition"
              >
                {downloading ? "Generating..." : "Download PDF"}
              </button>
            </div>
          </div>
        </section>

        {/* Primary Metrics Grid */}
        <section className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
          <MetricCard
            title="Attendance"
            value={`${attendanceRate}%`}
            detail={`${myAttendance.length} of ${totalSessions} sessions`}
            valueColor={getScoreColor(attendanceRate)}
            icon="📅"
          />
          <MetricCard
            title="Lecture Attention"
            value={`${behaviorScore}%`}
            detail={`${myLectureBehavior.length} monitored sessions`}
            valueColor={getScoreColor(behaviorScore)}
            icon="🧠"
          />
          <MetricCard
            title="Exam Integrity"
            value={examBehaviorScore === null ? "No Data" : `${examBehaviorScore}%`}
            detail={`${myExamBehavior.length} examinations evaluated`}
            valueColor={examBehaviorScore === null ? "text-slate-500" : getScoreColor(examBehaviorScore)}
            icon="📝"
          />
          <MetricCard
            title="Overall Score"
            value={`${overallScore}%`}
            detail="Aggregated Performance"
            valueColor={getScoreColor(overallScore)}
            icon="📊"
          />
        </section>

        {/* Analytics Charts */}
        <section className="grid grid-cols-1 lg:grid-cols-2 gap-5">
          {/* Trend Area Chart */}
          <div className="bg-[#081526] border border-slate-800 rounded-2xl p-5 shadow-xl">
            <div className="flex items-center justify-between mb-4">
              <div>
                <h2 className="text-sm font-bold text-white uppercase tracking-wide">
                  Attendance Trajectory
                </h2>
                <p className="text-xs text-slate-400 mt-0.5">
                  Presence records across lecture timeline
                </p>
              </div>
              <span className="text-xs font-bold text-blue-400 bg-blue-500/10 px-2.5 py-1 rounded-lg border border-blue-500/20">
                Rate: {attendanceRate}%
              </span>
            </div>

            {attendanceTrendData.length > 0 ? (
              <ResponsiveContainer width="100%" height={230}>
                <AreaChart data={attendanceTrendData} margin={{ top: 10, right: 15, left: -20, bottom: 0 }}>
                  <defs>
                    <linearGradient id="darkAttendanceGrad" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="5%" stopColor="#3b82f6" stopOpacity={0.35} />
                      <stop offset="95%" stopColor="#3b82f6" stopOpacity={0.0} />
                    </linearGradient>
                  </defs>
                  <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" />
                  <XAxis dataKey="label" stroke="#64748b" tick={{ fontSize: 11 }} />
                  <YAxis domain={[0, 100]} stroke="#64748b" tick={{ fontSize: 11 }} />
                  <Tooltip
                    contentStyle={{
                      backgroundColor: "#0b1a2e",
                      border: "1px solid #1e293b",
                      borderRadius: "10px",
                      color: "#fff",
                      fontSize: "12px",
                    }}
                  />
                  <Area
                    type="monotone"
                    dataKey="score"
                    stroke="#3b82f6"
                    strokeWidth={3}
                    fillOpacity={1}
                    fill="url(#darkAttendanceGrad)"
                  />
                </AreaChart>
              </ResponsiveContainer>
            ) : (
              <EmptyState message="No attendance data to plot." />
            )}
          </div>

          {/* Bar Chart */}
          <div className="bg-[#081526] border border-slate-800 rounded-2xl p-5 shadow-xl">
            <div className="flex items-center justify-between mb-4">
              <div>
                <h2 className="text-sm font-bold text-white uppercase tracking-wide">
                  Pillar Evaluation Index
                </h2>
                <p className="text-xs text-slate-400 mt-0.5">
                  Comparison across main academic performance metrics
                </p>
              </div>
            </div>

            <ResponsiveContainer width="100%" height={230}>
              <BarChart data={scoreComparisonData} margin={{ top: 10, right: 15, left: -20, bottom: 0 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" vertical={false} />
                <XAxis dataKey="name" stroke="#64748b" tick={{ fontSize: 11 }} />
                <YAxis domain={[0, 100]} stroke="#64748b" tick={{ fontSize: 11 }} />
                <Tooltip
                  contentStyle={{
                    backgroundColor: "#0b1a2e",
                    border: "1px solid #1e293b",
                    borderRadius: "10px",
                    color: "#fff",
                    fontSize: "12px",
                  }}
                />
                <Bar dataKey="value" fill="#3b82f6" radius={[6, 6, 0, 0]} maxBarSize={48} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </section>

        {/* Behavioral Analytics */}
        <section className="grid grid-cols-1 lg:grid-cols-2 gap-5">
          {/* Lecture Behavior */}
          <div className="bg-[#081526] border border-slate-800 rounded-2xl p-5 shadow-xl">
            <h2 className="text-sm font-bold text-white uppercase tracking-wide mb-1">
              Lecture Behaviour Composition
            </h2>
            <p className="text-xs text-slate-400 mb-4">
              Real-time computer vision breakdown of engagement
            </p>

            {totalLectureBehaviorTime > 0 ? (
              <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
                <MiniStat label="Attentive" value={`${attentiveTime.toFixed(1)}s`} color="text-emerald-400" />
                <MiniStat label="Sleeping" value={`${sleepingTime.toFixed(1)}s`} color="text-rose-400" />
                <MiniStat label="Phone Usage" value={`${phoneUseTime.toFixed(1)}s`} color="text-amber-400" />
                <MiniStat label="Distracted" value={`${notAttentiveTime.toFixed(1)}s`} color="text-slate-300" />
              </div>
            ) : (
              <EmptyState message="No lecture behavioral observations logged." />
            )}
          </div>

          {/* Exam Integrity */}
          <div className="bg-[#081526] border border-slate-800 rounded-2xl p-5 shadow-xl">
            <div className="flex items-center justify-between mb-1">
              <h2 className="text-sm font-bold text-white uppercase tracking-wide">
                Examination Integrity Log
              </h2>
              <span className={`px-2.5 py-0.5 rounded-full text-xs font-bold border ${examStatus === "Good" ? "bg-emerald-950/60 text-emerald-400 border-emerald-500/30" :
                examStatus === "Warning" ? "bg-amber-950/60 text-amber-400 border-amber-500/30" :
                  "bg-slate-900 text-slate-400 border-slate-700"
                }`}>
                {examStatus}
              </span>
            </div>
            <p className="text-xs text-slate-400 mb-4">
              Automated malpractice detection report
            </p>

            {hasExamData ? (
              <div className="space-y-3">
                <div className="grid grid-cols-2 gap-3">
                  <MiniStat label="Compliant Duration" value={`${nonCheatingTime.toFixed(1)}s`} color="text-emerald-400" />
                  <MiniStat label="Irregularity Flagged" value={`${examCheatingTime.toFixed(1)}s`} color="text-rose-400" />
                </div>
                <div className="bg-[#0c1e36] border border-blue-500/20 rounded-xl p-3.5 text-xs text-slate-300 leading-relaxed">
                  <strong className="text-blue-400 font-bold">AI Observation: </strong>
                  {examBehaviorScore >= 80
                    ? "Exam conduct adheres strictly to Horizon examination integrity standards."
                    : "Anomalous movement flagged during invigilation. Please adhere to proctor guidelines."}
                </div>
              </div>
            ) : (
              <EmptyState message="No examination records indexed." />
            )}
          </div>
        </section>

        {/* Tabular History: Attendance */}
        <section className="bg-[#081526] border border-slate-800 rounded-2xl p-5 shadow-xl overflow-hidden">
          <h2 className="text-sm font-bold text-white uppercase tracking-wide mb-1">
            Recorded Attendance Log
          </h2>
          <p className="text-xs text-slate-400 mb-4">
            Official presence timestamps captured by surveillance
          </p>

          <div className="rounded-xl overflow-hidden border border-slate-800">
            {attendanceRecords.length > 0 ? (
              <AttendanceTable records={attendanceRecords} />
            ) : (
              <EmptyState message="No records found in current academic period." />
            )}
          </div>
        </section>

        {/* Appeals & Official Remarks Section */}
        <section className="bg-[#081526] border border-slate-800 rounded-2xl p-5 shadow-xl">
          <div className="flex items-center justify-between pb-3 border-b border-slate-800/80 mb-4">
            <div>
              <h2 className="text-sm font-bold text-white uppercase tracking-wide">
                Appeals & Administrative Decisions
              </h2>
              <p className="text-xs text-slate-400 mt-0.5">Formal grievance status and feedback</p>
            </div>
            <button
              onClick={() => navigate("/student/appeal/new")}
              className="text-xs font-bold bg-blue-600 hover:bg-blue-700 text-white px-3.5 py-1.5 rounded-xl transition"
            >
              + Create Appeal
            </button>
          </div>

          {myAppeals.length === 0 ? (
            <EmptyState message="No formal appeals lodged." />
          ) : (
            <div className="divide-y divide-slate-800/60">
              {myAppeals.map((item, index) => (
                <div key={item._id || index} className="py-3.5 first:pt-0 last:pb-0">
                  <div className="flex items-center justify-between text-xs mb-1">
                    <span className="font-bold text-white text-sm">{item.type || item.reason || "Appeal"}</span>
                    <span className="font-mono text-slate-500">{item.date || item.created_at?.substring(0, 10)}</span>
                  </div>
                  <p className="text-xs text-slate-400 italic mb-2">"{item.message || item.description}"</p>
                  {item.admin_response ? (
                    <div className="bg-[#0d223a] border-l-4 border-blue-500 rounded-r-xl p-3 text-xs text-slate-200">
                      <strong className="text-blue-400">Admin Remark:</strong> {item.admin_response}
                    </div>
                  ) : (
                    <span className="text-[11px] text-amber-400 font-semibold bg-amber-950/60 px-2 py-0.5 rounded border border-amber-500/30">
                      Pending Administrative Review
                    </span>
                  )}
                </div>
              ))}
            </div>
          )}
        </section>

      </main>
    </div>
  );
}

function MetricCard({ title, value, detail, valueColor, icon }) {
  return (
    <div className="bg-[#081526] border border-slate-800 rounded-2xl p-5 shadow-xl hover:border-slate-700 transition duration-200 flex flex-col justify-between">
      <div className="flex items-center justify-between">
        <span className="text-xs font-bold uppercase tracking-wider text-slate-400">
          {title}
        </span>
        <span className="text-xl p-1.5 bg-slate-900 rounded-xl border border-slate-800">
          {icon}
        </span>
      </div>

      <div className={`text-3xl font-black mt-3 mb-1 tracking-tight ${valueColor}`}>
        {value}
      </div>

      <span className="text-[11px] text-slate-400 font-semibold">
        {detail}
      </span>
    </div>
  );
}

function MiniStat({ label, value, color }) {
  return (
    <div className="bg-[#0c1a2c] border border-slate-800 rounded-xl p-3 text-center">
      <span className="text-[11px] text-slate-400 block font-semibold mb-1">{label}</span>
      <span className={`text-xl font-black ${color}`}>{value}</span>
    </div>
  );
}

function EmptyState({ message }) {
  return (
    <div className="py-8 text-center text-xs font-medium text-slate-500">
      {message}
    </div>
  );
}