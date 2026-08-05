// src/pages/lecturer/Dashboard.jsx

import React, { useEffect, useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";

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
  behavior: "#22c55e",
  attentive: "#22c55e",
  cheating: "#ef4444",
  phone: "#f59e0b",
  sleeping: "#8b5cf6",
  good: "#22c55e",
  warning: "#f59e0b",
  risk: "#ef4444",
};

export default function LecturerDashboard() {
  const navigate = useNavigate();

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

  const [aiRunning, setAiRunning] = useState(false);
  const [aiLoading, setAiLoading] = useState(false);

  

  useEffect(() => {
    loadDashboard();
  }, []);

  const getArrayData = (response) => {
    if (Array.isArray(response)) {
      return response;
    }

    if (Array.isArray(response?.data)) {
      return response.data;
    }

    if (Array.isArray(response?.data?.data)) {
      return response.data.data;
    }

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

      const studentData = getArrayData(studentResponse);
      const attendanceData = getArrayData(attendanceResponse);
      const behaviorData = getArrayData(behaviorResponse);
      const totalSessions = getSessionCount(sessionResponse);

      setAttendance(attendanceData);
      setBehavior(behaviorData);

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
          attentiveTime +
          cheatingTime +
          sleepingTime +
          phoneTime +
          notAttentiveTime;

        const behaviorScore =
          totalBehaviorTime === 0
            ? 0
            : Math.round((attentiveTime / totalBehaviorTime) * 100);

        const overall = Math.round(
          attendanceRate * 0.4 + behaviorScore * 0.6
        );

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
          email:
            student.email ||
            `${String(studentId).toLowerCase()}@gmail.com`,
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

  const riskyStudents = students.filter(
    (student) => student.status === "risk"
  );

  const warningStudents = students.filter(
    (student) => student.status === "warning"
  );

  const goodStudents = students.filter(
    (student) => student.status === "good"
  );

  const performanceData = students.slice(0, 10).map((student) => ({
    name:
      student.name.length > 12
        ? `${student.name.substring(0, 12)}...`
        : student.name,
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

  const totalBehaviourTime =
    attentive + cheating + sleeping + phone + notAttentive;

  const calculatePercentage = (value) => {
    if (totalBehaviourTime === 0) {
      return 0;
    }

    return Number(((value / totalBehaviourTime) * 100).toFixed(1));
  };

  const behaviourData = [
    {
      name: "Attentive",
      value: calculatePercentage(attentive),
    },
    {
      name: "Cheating",
      value: calculatePercentage(cheating),
    },
    {
      name: "Phone Use",
      value: calculatePercentage(phone),
    },
    {
      name: "Sleeping",
      value: calculatePercentage(sleeping),
    },
    {
      name: "Not Attentive",
      value: calculatePercentage(notAttentive),
    },
  ].filter((item) => item.value > 0);

  const riskData = [
    {
      name: "Good",
      value: goodStudents.length,
    },
    {
      name: "Warning",
      value: warningStudents.length,
    },
    {
      name: "Risk",
      value: riskyStudents.length,
    },
  ];

  const filteredStudents = students.filter((student) => {
    const query = search.trim().toLowerCase();

    const matchesSearch =
      student.id.toLowerCase().includes(query) ||
      student.name.toLowerCase().includes(query) ||
      student.intake.toLowerCase().includes(query);

    const matchesStatus =
      statusFilter === "all" || student.status === statusFilter;

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

    const blob = new Blob([csvContent], {
      type: "text/csv;charset=utf-8;",
    });

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
    const toggleAIModel = async () => {
  try {
    setAiLoading(true);

    if (!aiRunning) {
      // Backend endpoint එක ready වුණාම මෙතන API call එක දාන්න
      // await startAIModel();

      setAiRunning(true);
      alert("AI Model started successfully");
    } else {
      // Backend endpoint එක ready වුණාම මෙතන API call එක දාන්න
      // await stopAIModel();

      setAiRunning(false);
      alert("AI Model stopped successfully");
    }
  } catch (err) {
    console.error("AI model error:", err);
    alert("Unable to change AI model status");
  } finally {
    setAiLoading(false);
  }
};

    const emails = riskyStudents
      .map((student) => student.email)
      .filter(Boolean);

    if (emails.length === 0) {
      alert("Risk students do not have valid email addresses.");
      return;
    }

    const studentList = riskyStudents
      .map(
        (student) => `
          <tr>
            <td style="padding:10px;border-bottom:1px solid #e5e7eb;">
              ${student.name}
            </td>

            <td style="padding:10px;border-bottom:1px solid #e5e7eb;">
              ${student.id}
            </td>

            <td style="padding:10px;border-bottom:1px solid #e5e7eb;color:#ef4444;font-weight:bold;">
              ${student.overall}%
            </td>
          </tr>
        `
      )
      .join("");

    const htmlBody = `
      <!DOCTYPE html>

      <html>
        <head>
          <meta charset="UTF-8" />
        </head>

        <body style="margin:0;padding:0;background:#f3f4f6;font-family:Arial,sans-serif;">

          <table width="100%" cellpadding="0" cellspacing="0">
            <tr>
              <td align="center" style="padding:30px 10px;">

                <table
                  width="650"
                  cellpadding="0"
                  cellspacing="0"
                  style="max-width:650px;background:white;border-radius:12px;overflow:hidden;box-shadow:0 0 15px rgba(0,0,0,.1);"
                >

                  <tr>
                    <td style="background:#0f172a;padding:25px;color:white;text-align:center;">
                      <h1 style="margin:0;">
                        🎓 Student360 AI
                      </h1>

                      <p style="margin-top:8px;">
                        AI Classroom Analytics System
                      </p>
                    </td>
                  </tr>

                  <tr>
                    <td style="padding:35px;">

                      <h2 style="color:#ef4444;">
                        Academic Performance Alert
                      </h2>

                      <p>
                        Dear Student,
                      </p>

                      <p>
                        The Student360 AI Classroom Monitoring System has identified
                        that your classroom performance requires attention.
                      </p>

                      <table
                        width="100%"
                        style="border-collapse:collapse;margin-top:20px;"
                      >
                        <tr>
                          <th
                            align="left"
                            style="padding:12px;background:#e5e7eb;"
                          >
                            Areas to Improve
                          </th>
                        </tr>

                        <tr>
                          <td style="padding:12px;">
                            ✅ Attend lectures regularly
                          </td>
                        </tr>

                        <tr>
                          <td style="padding:12px;">
                            ✅ Improve classroom attention
                          </td>
                        </tr>

                        <tr>
                          <td style="padding:12px;">
                            ✅ Avoid unnecessary phone usage
                          </td>
                        </tr>

                        <tr>
                          <td style="padding:12px;">
                            ✅ Participate actively during lectures
                          </td>
                        </tr>
                      </table>

                      <div
                        style="
                          margin-top:25px;
                          background:#fef3c7;
                          padding:18px;
                          border-left:6px solid #f59e0b;
                        "
                      >
                        <strong>
                          AI Recommendation
                        </strong>

                        <p>
                          Attend lectures regularly, stay attentive, avoid phone
                          usage and actively participate in classroom activities.
                        </p>
                      </div>

                      <h3 style="margin-top:25px;">
                        Students Requiring Attention
                      </h3>

                      <table
                        width="100%"
                        style="border-collapse:collapse;margin-top:10px;"
                      >
                        <tr style="background:#f3f4f6;">
                          <th align="left" style="padding:10px;">
                            Name
                          </th>

                          <th align="left" style="padding:10px;">
                            Student ID
                          </th>

                          <th align="left" style="padding:10px;">
                            Overall
                          </th>
                        </tr>

                        ${studentList}
                      </table>

                      <p style="margin-top:25px;">
                        This notification was automatically generated by
                        <b> Student360 AI Analytics</b>.
                      </p>
                    </td>
                  </tr>

                  <tr>
                    <td style="background:#0f172a;color:white;padding:18px;text-align:center;">
                      Student360 AI
                      <br />
                      Faculty of Computing
                      <br />
                      AI-Based Classroom Monitoring System
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

      alert(
        response?.message ||
          response?.data?.message ||
          "Notifications sent successfully."
      );
    } catch (err) {
      console.error("Email sending error:", err);

      alert(
        err?.response?.data?.detail ||
          "Email sending failed. Please check the backend."
      );
    } finally {
      setNotifying(false);
    }
  };
  const toggleAIModel = async () => {
  try {
    setAiLoading(true);

    await new Promise((resolve) => {
      setTimeout(resolve, 800);
    });

    if (aiRunning) {
      setAiRunning(false);
      alert("AI Model stopped successfully");
    } else {
      setAiRunning(true);
      alert("AI Model started successfully");
    }
  } catch (error) {
    console.error("AI model error:", error);
    alert("Unable to change AI model status");
  } finally {
    setAiLoading(false);
  }
};

  const logout = () => {
    localStorage.removeItem("token");
    localStorage.removeItem("user");
    localStorage.removeItem("classroom");
    localStorage.removeItem("selectedRole");

    navigate("/roles");
  };

  function getStatusText(status) {
    if (status === "good") {
      return "Good";
    }

    if (status === "warning") {
      return "Warning";
    }

    return "Risk";
  }

  function getStatusClass(status) {
    if (status === "good") {
      return "bg-green-500/15 text-green-400 border-green-500/30";
    }

    if (status === "warning") {
      return "bg-yellow-500/15 text-yellow-400 border-yellow-500/30";
    }

    return "bg-red-500/15 text-red-400 border-red-500/30";
  }

  function getScoreClass(score) {
    if (score >= 75) {
      return "text-green-400";
    }

    if (score >= 60) {
      return "text-yellow-400";
    }

    return "text-red-400";
  }

  if (loading) {
    return (
      <div className="min-h-screen bg-[#071828] flex flex-col items-center justify-center text-white">
        <div className="w-12 h-12 border-4 border-gray-700 border-t-blue-500 rounded-full animate-spin" />

        <h2 className="text-xl font-semibold mt-5">
          Loading Lecturer Dashboard
        </h2>

        <p className="text-gray-400 mt-2">
          Fetching student analytics...
        </p>
      </div>
    );
  }

  if (error) {
    return (
      <div className="min-h-screen bg-[#071828] flex items-center justify-center text-white p-6">
        <div className="max-w-md w-full bg-[#0b2236] border border-red-500/30 rounded-2xl p-8 text-center">
          <div className="text-5xl mb-4">
            ⚠️
          </div>

          <h2 className="text-2xl font-bold">
            Dashboard Loading Failed
          </h2>

          <p className="text-gray-400 mt-3">
            {error}
          </p>

          <button
            onClick={loadDashboard}
            className="mt-6 bg-blue-600 hover:bg-blue-700 px-6 py-3 rounded-lg font-semibold transition"
          >
            Try Again
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-[#071828] text-white">

      {/* Header */}

      <header className="bg-[#091d30] border-b border-white/10 sticky top-0 z-30">
        <div className="max-w-[1600px] mx-auto px-4 md:px-8 py-4 flex flex-col md:flex-row md:items-center justify-between gap-4">

          <div className="flex items-center gap-4">
            <div className="w-12 h-12 bg-blue-600 rounded-xl flex items-center justify-center text-2xl shadow-lg">
              👨‍🏫
            </div>

            <div>
              <h1 className="text-2xl md:text-3xl font-bold">
                Lecturer Dashboard
              </h1>

              <p className="text-gray-400 text-sm mt-1">
                Student360 AI Classroom Analytics
              </p>
            </div>
          </div>

          <div className="flex flex-wrap items-center gap-3">

  {/* AI MODEL BUTTON */}
  <button
    onClick={toggleAIModel}
    disabled={aiLoading}
    className={`px-4 py-2 rounded-lg font-semibold border transition flex items-center gap-2 ${
      aiRunning
        ? "bg-green-500/20 text-green-300 border-green-500/40 hover:bg-green-500/30"
        : "bg-purple-500/20 text-purple-300 border-purple-500/40 hover:bg-purple-500/30"
    } disabled:opacity-50 disabled:cursor-not-allowed`}
  >
    <span
      className={`w-2.5 h-2.5 rounded-full ${
        aiRunning
          ? "bg-green-400 animate-pulse"
          : "bg-gray-400"
      }`}
    />

    {aiLoading
      ? "Processing..."
      : aiRunning
      ? "Stop AI Model"
      : "Start AI Model"}
  </button>

  {/* CHANGE CLASSROOM BUTTON */}
  <button
    onClick={() => navigate("/lecturer/classroom")}
    className="px-4 py-2 rounded-lg bg-white/5 hover:bg-white/10 border border-white/10 transition"
  >
    Change Classroom
  </button>

  {/* APPEALS BUTTON */}
  <button
    onClick={() => navigate("/lecturer/appeals")}
    className="px-4 py-2 rounded-lg bg-blue-600/20 text-blue-300 hover:bg-blue-600/30 border border-blue-500/30 transition"
  >
    View Appeals
  </button>

  {/* LOGOUT BUTTON */}
  <button
    onClick={logout}
    className="px-4 py-2 rounded-lg bg-red-600 hover:bg-red-700 transition"
  >
    Sign Out
  </button>

</div>
        </div>
      </header>

      <main className="max-w-[1600px] mx-auto p-4 md:p-8">

        {/* Classroom Information */}

        <section className="bg-gradient-to-r from-blue-600/20 to-purple-600/20 border border-blue-500/20 rounded-2xl p-5 mb-7">
          <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-4">

            <div>
              <p className="text-sm text-blue-300 font-medium">
                CURRENT CLASSROOM
              </p>

              <h2 className="text-xl md:text-2xl font-bold mt-1">
                {classroom.subject || "Subject Not Selected"}
              </h2>
            </div>

            <div className="flex flex-wrap gap-3 text-sm">
              <ClassroomBadge
                label="Year"
                value={classroom.year || "N/A"}
              />

              <ClassroomBadge
                label="Semester"
                value={classroom.sem || "N/A"}
              />

              <ClassroomBadge
                label="Group"
                value={classroom.group || "N/A"}
              />
            </div>
          </div>
        </section>

        {/* Summary Cards */}

        <section className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-4 gap-5 mb-7">
          <SummaryCard
            title="Total Students"
            value={students.length}
            subtitle="Registered students"
            icon="👥"
          />

          <SummaryCard
            title="Average Attendance"
            value={`${averageAttendance}%`}
            subtitle={`${attendance.length} attendance records`}
            icon="📅"
            valueClass={getScoreClass(averageAttendance)}
          />

          <SummaryCard
            title="Average Behavior"
            value={`${averageBehavior}%`}
            subtitle={`${behavior.length} behavior logs`}
            icon="🧠"
            valueClass={getScoreClass(averageBehavior)}
          />

          <SummaryCard
            title="Risk Students"
            value={riskyStudents.length}
            subtitle="Immediate attention required"
            icon="⚠️"
            valueClass="text-red-400"
          />
        </section>

        {/* Overall Class Performance */}

        <section className="grid grid-cols-1 lg:grid-cols-3 gap-5 mb-7">
          <PerformanceCard
            title="Class Overall Score"
            value={averageOverall}
            description="Combined attendance and behavior"
          />

          <StatusCard
            title="Good Students"
            value={goodStudents.length}
            description="Overall score 75% or above"
            type="good"
          />

          <StatusCard
            title="Warning Students"
            value={warningStudents.length}
            description="Overall score between 60% and 74%"
            type="warning"
          />
        </section>

        {/* Risk Alert */}

        {riskyStudents.length > 0 && (
          <section className="bg-red-500/10 border border-red-500/30 rounded-2xl p-5 mb-7 flex flex-col md:flex-row md:items-center justify-between gap-4">
            <div className="flex items-start gap-4">
              <div className="text-3xl">
                🚨
              </div>

              <div>
                <h3 className="text-lg font-bold text-red-300">
                  Student Risk Alert
                </h3>

                <p className="text-gray-300 mt-1">
                  {riskyStudents.length} student
                  {riskyStudents.length !== 1 ? "s have" : " has"} an overall
                  score below 60%.
                </p>
              </div>
            </div>

            <button
              onClick={notifyStudents}
              disabled={notifying}
              className="bg-red-600 hover:bg-red-700 disabled:opacity-50 disabled:cursor-not-allowed px-5 py-3 rounded-lg font-semibold transition"
            >
              {notifying ? "Sending Notifications..." : "Notify Risk Students"}
            </button>
          </section>
        )}

        {/* Actions */}

        <section className="flex flex-col lg:flex-row justify-between gap-4 mb-7">
          <div className="flex flex-col sm:flex-row gap-3 flex-1">
            <input
              type="text"
              placeholder="Search by student ID, name or intake..."
              value={search}
              onChange={(event) => setSearch(event.target.value)}
              className="flex-1 bg-[#0b2236] border border-white/10 p-3 rounded-xl outline-none focus:border-blue-500 transition"
            />

            <select
              value={statusFilter}
              onChange={(event) => setStatusFilter(event.target.value)}
              className="bg-[#0b2236] border border-white/10 p-3 rounded-xl outline-none focus:border-blue-500"
            >
              <option value="all">
                All Students
              </option>

              <option value="good">
                Good Students
              </option>

              <option value="warning">
                Warning Students
              </option>

              <option value="risk">
                Risk Students
              </option>
            </select>
          </div>

          <div className="flex gap-3">
            <button
              onClick={loadDashboard}
              className="px-5 py-3 rounded-xl bg-white/5 hover:bg-white/10 border border-white/10 transition"
            >
              Refresh
            </button>

            <button
              onClick={exportCSV}
              className="px-5 py-3 rounded-xl bg-green-600 hover:bg-green-700 font-semibold transition"
            >
              Export CSV
            </button>
          </div>
        </section>

        {/* Analytics */}

        <section className="grid grid-cols-1 xl:grid-cols-2 gap-6 mb-7">

          {/* Attendance and Behavior Chart */}

          <div className="bg-[#0b2236] border border-white/10 rounded-2xl p-5">
            <div className="mb-5">
              <h2 className="text-xl font-bold">
                Attendance vs Behavior
              </h2>

              <p className="text-sm text-gray-400 mt-1">
                Top 10 students based on overall ranking
              </p>
            </div>

            {performanceData.length > 0 ? (
              <ResponsiveContainer width="100%" height={320}>
                <BarChart
                  data={performanceData}
                  margin={{
                    top: 10,
                    right: 10,
                    left: -20,
                    bottom: 30,
                  }}
                >
                  <CartesianGrid
                    strokeDasharray="3 3"
                    stroke="#334155"
                    vertical={false}
                  />

                  <XAxis
                    dataKey="name"
                    stroke="#94a3b8"
                    angle={-20}
                    textAnchor="end"
                    height={70}
                    tick={{
                      fontSize: 11,
                    }}
                  />

                  <YAxis
                    domain={[0, 100]}
                    stroke="#94a3b8"
                  />

                  <Tooltip
                    contentStyle={{
                      backgroundColor: "#0f172a",
                      border: "1px solid #334155",
                      borderRadius: "10px",
                    }}
                  />

                  <Legend />

                  <Bar
                    dataKey="Attendance"
                    fill={CHART_COLORS.attendance}
                    radius={[5, 5, 0, 0]}
                  />

                  <Bar
                    dataKey="Behaviour"
                    fill={CHART_COLORS.behavior}
                    radius={[5, 5, 0, 0]}
                  />
                </BarChart>
              </ResponsiveContainer>
            ) : (
              <EmptyChart message="No performance data available." />
            )}
          </div>

          {/* Behavior Distribution */}

          <div className="bg-[#0b2236] border border-white/10 rounded-2xl p-5">
            <div className="mb-5">
              <h2 className="text-xl font-bold">
                Behavior Distribution
              </h2>

              <p className="text-sm text-gray-400 mt-1">
                Overall classroom behavior analysis
              </p>
            </div>

            {behaviourData.length > 0 ? (
              <ResponsiveContainer width="100%" height={320}>
                <PieChart>
                  <Pie
                    data={behaviourData}
                    dataKey="value"
                    nameKey="name"
                    innerRadius={65}
                    outerRadius={105}
                    paddingAngle={3}
                    label={({ name, value }) => `${name} ${value}%`}
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
                      backgroundColor: "#0f172a",
                      border: "1px solid #334155",
                      borderRadius: "10px",
                    }}
                  />

                  <Legend />
                </PieChart>
              </ResponsiveContainer>
            ) : (
              <EmptyChart message="No behavior records available." />
            )}
          </div>
        </section>

        {/* Risk Distribution */}

        <section className="bg-[#0b2236] border border-white/10 rounded-2xl p-5 mb-7">
          <div className="mb-5">
            <h2 className="text-xl font-bold">
              Student Performance Distribution
            </h2>

            <p className="text-sm text-gray-400 mt-1">
              Good, warning and risk student categories
            </p>
          </div>

          {students.length > 0 ? (
            <ResponsiveContainer width="100%" height={300}>
              <PieChart>
                <Pie
                  data={riskData}
                  dataKey="value"
                  nameKey="name"
                  innerRadius={70}
                  outerRadius={110}
                  paddingAngle={4}
                  label={({ name, value }) => `${name} (${value})`}
                >
                  <Cell fill={CHART_COLORS.good} />
                  <Cell fill={CHART_COLORS.warning} />
                  <Cell fill={CHART_COLORS.risk} />
                </Pie>

                <Tooltip
                  contentStyle={{
                    backgroundColor: "#0f172a",
                    border: "1px solid #334155",
                    borderRadius: "10px",
                  }}
                />

                <Legend />
              </PieChart>
            </ResponsiveContainer>
          ) : (
            <EmptyChart message="No student data available." />
          )}
        </section>

        {/* Student Table */}

        <section className="bg-[#0b2236] border border-white/10 rounded-2xl overflow-hidden">
          <div className="p-5 border-b border-white/10 flex flex-col sm:flex-row sm:items-center justify-between gap-3">
            <div>
              <h2 className="text-xl font-bold">
                Student Performance Ranking
              </h2>

              <p className="text-sm text-gray-400 mt-1">
                Showing {filteredStudents.length} of {students.length} students
              </p>
            </div>
          </div>

          <div className="overflow-x-auto">
            <table className="w-full min-w-[900px]">
              <thead className="bg-[#091d30]">
                <tr className="text-left text-gray-300">
                  <th className="p-4 text-center">
                    Rank
                  </th>

                  <th className="p-4">
                    Student
                  </th>

                  <th className="p-4">
                    Intake
                  </th>

                  <th className="p-4 text-center">
                    Attendance
                  </th>

                  <th className="p-4 text-center">
                    Behavior
                  </th>

                  <th className="p-4 text-center">
                    Overall
                  </th>

                  <th className="p-4 text-center">
                    Status
                  </th>

                  <th className="p-4 text-center">
                    Action
                  </th>
                </tr>
              </thead>

              <tbody>
                {filteredStudents.length > 0 ? (
                  filteredStudents.map((student) => {
                    const actualRank =
                      students.findIndex((item) => item.id === student.id) + 1;

                    return (
                      <tr
                        key={student.id}
                        className="border-t border-white/5 hover:bg-white/5 transition"
                      >
                        <td className="p-4 text-center">
                          <span className="font-bold text-blue-300">
                            #{actualRank}
                          </span>
                        </td>

                        <td className="p-4">
                          <div>
                            <p className="font-semibold">
                              {student.name}
                            </p>

                            <p className="text-sm text-gray-400 mt-1">
                              {student.id}
                            </p>
                          </div>
                        </td>

                        <td className="p-4 text-gray-300">
                          {student.intake}
                        </td>

                        <td className="p-4 text-center">
                          <ScoreBadge value={student.attendance} />
                        </td>

                        <td className="p-4 text-center">
                          <ScoreBadge value={student.behavior} />
                        </td>

                        <td
                          className={`p-4 text-center text-lg font-bold ${getScoreClass(
                            student.overall
                          )}`}
                        >
                          {student.overall}%
                        </td>

                        <td className="p-4 text-center">
                          <span
                            className={`inline-flex px-3 py-1 rounded-full text-sm font-medium border ${getStatusClass(
                              student.status
                            )}`}
                          >
                            {getStatusText(student.status)}
                          </span>
                        </td>

                        <td className="p-4 text-center">
                          <button
                            onClick={() => setSelected(student)}
                            className="bg-blue-600/20 hover:bg-blue-600/30 text-blue-300 border border-blue-500/30 px-4 py-2 rounded-lg transition"
                          >
                            View Details
                          </button>
                        </td>
                      </tr>
                    );
                  })
                ) : (
                  <tr>
                    <td
                      colSpan="8"
                      className="p-12 text-center text-gray-400"
                    >
                      No students match your search or filter.
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        </section>
      </main>

      {/* Student Detail Modal */}

      {selected && (
        <div
          className="fixed inset-0 bg-black/75 backdrop-blur-sm flex items-center justify-center z-50 p-4"
          onClick={() => setSelected(null)}
        >
          <div
            className="bg-[#0b2236] border border-white/10 rounded-2xl w-full max-w-lg shadow-2xl overflow-hidden"
            onClick={(event) => event.stopPropagation()}
          >
            <div className="bg-gradient-to-r from-blue-600/30 to-purple-600/30 p-6 flex justify-between items-start">
              <div>
                <p className="text-sm text-blue-300">
                  STUDENT PROFILE
                </p>

                <h2 className="text-2xl font-bold mt-1">
                  {selected.name}
                </h2>

                <p className="text-gray-300 mt-1">
                  {selected.id}
                </p>
              </div>

              <button
                onClick={() => setSelected(null)}
                className="w-9 h-9 rounded-full bg-black/20 hover:bg-black/40 transition"
              >
                ✕
              </button>
            </div>

            <div className="p-6">
              <div className="grid grid-cols-2 gap-4 mb-6">
                <DetailItem
                  label="Intake"
                  value={selected.intake}
                />

                <DetailItem
                  label="Email"
                  value={selected.email}
                />

                <DetailItem
                  label="Attendance Records"
                  value={selected.attendanceRecords}
                />

                <DetailItem
                  label="Behavior Records"
                  value={selected.behaviorRecords}
                />
              </div>

              <div className="space-y-5">
                <ProgressScore
                  label="Attendance"
                  value={selected.attendance}
                />

                <ProgressScore
                  label="Behavior"
                  value={selected.behavior}
                />

                <ProgressScore
                  label="Overall Performance"
                  value={selected.overall}
                />
              </div>

              <div className="mt-6 bg-[#071828] rounded-xl p-4 flex items-center justify-between">
                <span className="text-gray-400">
                  Student Status
                </span>

                <span
                  className={`px-4 py-2 rounded-full text-sm font-semibold border ${getStatusClass(
                    selected.status
                  )}`}
                >
                  {getStatusText(selected.status)}
                </span>
              </div>

              {selected.status === "risk" && (
                <div className="mt-5 bg-red-500/10 border border-red-500/30 rounded-xl p-4">
                  <h3 className="font-semibold text-red-300">
                    AI Recommendation
                  </h3>

                  <p className="text-sm text-gray-300 mt-2">
                    The student should improve lecture attendance, reduce phone
                    usage, remain attentive and actively participate during
                    classroom sessions.
                  </p>
                </div>
              )}

              <button
                onClick={() => setSelected(null)}
                className="w-full mt-6 bg-blue-600 hover:bg-blue-700 py-3 rounded-xl font-semibold transition"
              >
                Close Details
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

function SummaryCard({
  title,
  value,
  subtitle,
  icon,
  valueClass = "text-white",
}) {
  return (
    <div className="bg-[#0b2236] border border-white/10 rounded-2xl p-5 hover:-translate-y-1 transition">
      <div className="flex items-start justify-between">
        <div>
          <p className="text-gray-400 text-sm">
            {title}
          </p>

          <h2 className={`text-3xl font-bold mt-3 ${valueClass}`}>
            {value}
          </h2>

          <p className="text-gray-500 text-sm mt-2">
            {subtitle}
          </p>
        </div>

        <div className="w-12 h-12 bg-white/5 rounded-xl flex items-center justify-center text-2xl">
          {icon}
        </div>
      </div>
    </div>
  );
}

function PerformanceCard({ title, value, description }) {
  return (
    <div className="bg-[#0b2236] border border-white/10 rounded-2xl p-5">
      <p className="text-gray-400">
        {title}
      </p>

      <div className="flex items-end gap-2 mt-3">
        <h2 className="text-4xl font-bold">
          {value}%
        </h2>

        <span className="text-gray-400 mb-1">
          average
        </span>
      </div>

      <div className="w-full h-2 bg-[#071828] rounded-full mt-5 overflow-hidden">
        <div
          className="h-full bg-blue-500 rounded-full transition-all duration-700"
          style={{
            width: `${Math.min(value, 100)}%`,
          }}
        />
      </div>

      <p className="text-sm text-gray-500 mt-3">
        {description}
      </p>
    </div>
  );
}

function StatusCard({ title, value, description, type }) {
  const classNames =
    type === "good"
      ? "text-green-400 bg-green-500/10 border-green-500/20"
      : "text-yellow-400 bg-yellow-500/10 border-yellow-500/20";

  return (
    <div className={`border rounded-2xl p-5 ${classNames}`}>
      <p className="text-gray-300">
        {title}
      </p>

      <h2 className="text-4xl font-bold mt-3">
        {value}
      </h2>

      <p className="text-sm text-gray-400 mt-3">
        {description}
      </p>
    </div>
  );
}

function ClassroomBadge({ label, value }) {
  return (
    <div className="bg-black/20 border border-white/10 rounded-lg px-4 py-2">
      <span className="text-gray-400">
        {label}:
      </span>

      <span className="ml-2 font-semibold text-white">
        {value}
      </span>
    </div>
  );
}

function ScoreBadge({ value }) {
  let className = "bg-red-500/10 text-red-400";

  if (value >= 75) {
    className = "bg-green-500/10 text-green-400";
  } else if (value >= 60) {
    className = "bg-yellow-500/10 text-yellow-400";
  }

  return (
    <span
      className={`inline-flex min-w-[65px] justify-center px-3 py-1 rounded-lg font-semibold ${className}`}
    >
      {value}%
    </span>
  );
}

function DetailItem({ label, value }) {
  return (
    <div className="bg-[#071828] rounded-xl p-4">
      <p className="text-xs text-gray-500">
        {label}
      </p>

      <p className="font-semibold mt-1 break-all">
        {value}
      </p>
    </div>
  );
}

function ProgressScore({ label, value }) {
  let barClass = "bg-red-500";

  if (value >= 75) {
    barClass = "bg-green-500";
  } else if (value >= 60) {
    barClass = "bg-yellow-500";
  }

  return (
    <div>
      <div className="flex justify-between mb-2">
        <span className="text-gray-300">
          {label}
        </span>

        <span className="font-semibold">
          {value}%
        </span>
      </div>

      <div className="w-full h-2 bg-[#071828] rounded-full overflow-hidden">
        <div
          className={`h-full rounded-full ${barClass}`}
          style={{
            width: `${Math.min(value, 100)}%`,
          }}
        />
      </div>
    </div>
  );
}

function EmptyChart({ message }) {
  return (
    <div className="h-[300px] flex flex-col items-center justify-center text-gray-500">
      <div className="text-4xl mb-3">
        📊
      </div>

      <p>
        {message}
      </p>
    </div>
  );
}