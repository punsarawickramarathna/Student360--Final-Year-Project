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
  LineChart,
  Line,
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
  "#22c55e",
  "#ef4444",
  "#f59e0b",
  "#8b5cf6",
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
  const [sessions, setSessions] = useState({
    count: 0,
    data: [],
  });

  const [loading, setLoading] = useState(true);
  const [downloading, setDownloading] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    loadData();
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

  const getSessionData = (response) => {
    if (Array.isArray(response?.data)) {
      return {
        count: response.data.length,
        data: response.data,
      };
    }

    if (response?.data && typeof response.data === "object") {
      return {
        count: Number(
          response.data.count ||
            response.data.total ||
            response.data.data?.length ||
            0
        ),
        data: Array.isArray(response.data.data)
          ? response.data.data
          : [],
      };
    }

    if (response && typeof response === "object") {
      return {
        count: Number(
          response.count ||
            response.total ||
            response.data?.length ||
            0
        ),
        data: Array.isArray(response.data)
          ? response.data
          : [],
      };
    }

    return {
      count: 0,
      data: [],
    };
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
    return (
      String(record?.student_id || record?.id || "")
        .trim()
        .toLowerCase() ===
      String(studentId).trim().toLowerCase()
    );
  };

  const myAttendance = attendance.filter(sameStudent);
  const myBehavior = behavior.filter(sameStudent);
  const myAppeals = appeals.filter(sameStudent);

  const isExamRecord = (item) => {
    const sessionType = String(
      item.session_type ||
        item.type ||
        item.session_category ||
        ""
    ).toLowerCase();

    if (sessionType) {
      return (
        sessionType === "exam" ||
        sessionType === "examination"
      );
    }

    const nonCheating = Number(
      item.non_cheating ??
        item.non_cheating_sec ??
        0
    );

    return nonCheating > 0;
  };

  const myExamBehavior = myBehavior.filter(isExamRecord);

  const myLectureBehavior = myBehavior.filter(
    (item) => !isExamRecord(item)
  );

  const totalSessions = Number(
    sessions.count || sessions.data?.length || 0
  );

  const attendanceRate =
    totalSessions > 0
      ? Math.min(
          Math.round(
            (myAttendance.length / totalSessions) * 100
          ),
          100
        )
      : 0;

  let attentiveTime = 0;
  let sleepingTime = 0;
  let phoneUseTime = 0;
  let notAttentiveTime = 0;
  let lectureCheatingTime = 0;

  myLectureBehavior.forEach((item) => {
    attentiveTime += Number(
      item.attentive ??
        item.attentive_sec ??
        0
    );

    sleepingTime += Number(
      item.sleeping ??
        item.sleeping_sec ??
        0
    );

    phoneUseTime += Number(
      item.phone_use ??
        item.phone_use_sec ??
        0
    );

    notAttentiveTime += Number(
      item.not_attentive ??
        item.not_attentive_sec ??
        0
    );

    lectureCheatingTime += Number(
      item.cheating ??
        item.cheating_sec ??
        0
    );
  });

  const totalLectureBehaviorTime =
    attentiveTime +
    sleepingTime +
    phoneUseTime +
    notAttentiveTime +
    lectureCheatingTime;

  const behaviorScore =
    totalLectureBehaviorTime === 0
      ? 0
      : Math.round(
          (attentiveTime /
            totalLectureBehaviorTime) *
            100
        );

  let examCheatingTime = 0;
  let nonCheatingTime = 0;

  myExamBehavior.forEach((item) => {
    examCheatingTime += Number(
      item.cheating ??
        item.cheating_sec ??
        0
    );

    nonCheatingTime += Number(
      item.non_cheating ??
        item.non_cheating_sec ??
        0
    );
  });

  const totalExamBehaviorTime =
    examCheatingTime + nonCheatingTime;

  const hasExamData = totalExamBehaviorTime > 0;

  const examBehaviorScore = hasExamData
    ? Math.round(
        (nonCheatingTime /
          totalExamBehaviorTime) *
          100
      )
    : null;

  const latestExamRecord =
    myExamBehavior.length > 0
      ? [...myExamBehavior].sort((a, b) => {
          const firstDate = new Date(
            a.created_at || a.date || 0
          );

          const secondDate = new Date(
            b.created_at || b.date || 0
          );

          return secondDate - firstDate;
        })[0]
      : null;

  let examStatus = "No Data";

  if (examBehaviorScore !== null) {
    if (examBehaviorScore >= 80) {
      examStatus = "Good";
    } else if (examBehaviorScore >= 60) {
      examStatus = "Warning";
    } else {
      examStatus = "Suspicious";
    }
  }

  const scoreValues = [
    attendanceRate,
    behaviorScore,
  ];

  if (examBehaviorScore !== null) {
    scoreValues.push(examBehaviorScore);
  }

  const overallScore =
    scoreValues.length === 0
      ? 0
      : Math.round(
          scoreValues.reduce(
            (total, value) => total + value,
            0
          ) / scoreValues.length
        );

  let badge = "";
  let badgeColor = "";

  if (overallScore >= 80) {
    badge = "Excellent Student 🏆";
    badgeColor = "text-green-400";
  } else if (overallScore >= 60) {
    badge = "Good Student 👍";
    badgeColor = "text-yellow-400";
  } else {
    badge = "Needs Improvement ⚠️";
    badgeColor = "text-red-400";
  }

  const attendanceTrendData = myAttendance.map(
    (item, index) => {
      const status = String(
        item.status || "Present"
      ).toLowerCase();

      return {
        label:
          item.date ||
          `Session ${index + 1}`,
        score:
          status === "absent" ? 0 : 100,
      };
    }
  );

  const scoreComparisonData = [
    {
      name: "Attendance",
      value: attendanceRate,
    },
    {
      name: "Lecture Behaviour",
      value: behaviorScore,
    },
    {
      name: "Exam Behaviour",
      value:
        examBehaviorScore === null
          ? 0
          : examBehaviorScore,
    },
  ];

  const lectureBehaviorData = [
    {
      name: "Attentive",
      value: Number(attentiveTime.toFixed(2)),
    },
    {
      name: "Sleeping",
      value: Number(sleepingTime.toFixed(2)),
    },
    {
      name: "Phone Use",
      value: Number(phoneUseTime.toFixed(2)),
    },
    {
      name: "Not Attentive",
      value: Number(
        notAttentiveTime.toFixed(2)
      ),
    },
    {
      name: "Suspicious",
      value: Number(
        lectureCheatingTime.toFixed(2)
      ),
    },
  ].filter((item) => item.value > 0);

  const attendanceRecords = myAttendance.map(
    (item) => ({
      date:
        item.date ||
        item.created_at ||
        "-",
      status: item.status || "Present",
    })
  );

  const downloadPDF = async () => {
    if (!dashboardRef.current) {
      return;
    }

    try {
      setDownloading(true);

      const canvas = await html2canvas(
        dashboardRef.current,
        {
          scale: 2,
          useCORS: true,
          backgroundColor: "#020817",
        }
      );

      const imageData =
        canvas.toDataURL("image/png");

      const pdf = new jsPDF(
        "p",
        "mm",
        "a4"
      );

      const pdfWidth =
        pdf.internal.pageSize.getWidth();

      const pageHeight =
        pdf.internal.pageSize.getHeight();

      const imageHeight =
        (canvas.height * pdfWidth) /
        canvas.width;

      let heightLeft = imageHeight;
      let position = 0;

      pdf.addImage(
        imageData,
        "PNG",
        0,
        position,
        pdfWidth,
        imageHeight
      );

      heightLeft -= pageHeight;

      while (heightLeft > 0) {
        position =
          heightLeft - imageHeight;

        pdf.addPage();

        pdf.addImage(
          imageData,
          "PNG",
          0,
          position,
          pdfWidth,
          imageHeight
        );

        heightLeft -= pageHeight;
      }

      pdf.save(
        `Student360_${studentId || "Student"}_Report.pdf`
      );
    } catch (err) {
      console.error("PDF error:", err);
      alert("Unable to download PDF report.");
    } finally {
      setDownloading(false);
    }
  };

  const getScoreClass = (score) => {
    if (score >= 80) {
      return "text-green-400";
    }

    if (score >= 60) {
      return "text-yellow-400";
    }

    return "text-red-400";
  };

  const getExamStatusClass = () => {
    if (examStatus === "Good") {
      return "bg-green-500/15 text-green-400 border-green-500/30";
    }

    if (examStatus === "Warning") {
      return "bg-yellow-500/15 text-yellow-400 border-yellow-500/30";
    }

    if (examStatus === "Suspicious") {
      return "bg-red-500/15 text-red-400 border-red-500/30";
    }

    return "bg-gray-500/15 text-gray-400 border-gray-500/30";
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-[#020817] text-white flex flex-col items-center justify-center">

        <div className="w-12 h-12 rounded-full border-4 border-gray-700 border-t-blue-500 animate-spin" />

        <h2 className="text-xl font-semibold mt-5">
          Loading Student Dashboard
        </h2>

        <p className="text-gray-400 mt-2">
          Fetching your performance records...
        </p>

      </div>
    );
  }

  if (error) {
    return (
      <div className="min-h-screen bg-[#020817] text-white flex items-center justify-center p-6">

        <div className="w-full max-w-md bg-[#0b2236] border border-red-500/30 rounded-2xl p-8 text-center">

          <div className="text-5xl">
            ⚠️
          </div>

          <h2 className="text-2xl font-bold mt-4">
            Dashboard Loading Failed
          </h2>

          <p className="text-gray-400 mt-3">
            {error}
          </p>

          <button
            onClick={loadData}
            className="mt-6 bg-blue-600 hover:bg-blue-700 px-6 py-3 rounded-xl font-semibold"
          >
            Try Again
          </button>

        </div>

      </div>
    );
  }

  return (
    <div className="min-h-screen bg-[#020817] text-white">

      <Navbar />

      <div
        ref={dashboardRef}
        className="max-w-7xl mx-auto p-4 md:p-8"
      >

        {/* Welcome Header */}

        <section className="bg-gradient-to-r from-blue-600/20 to-purple-600/20 border border-white/10 rounded-2xl p-6 md:p-8">

          <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-5">

            <div>

              <p className="text-blue-300 text-sm font-medium">
                STUDENT PERFORMANCE PORTAL
              </p>

              <h1 className="text-3xl md:text-4xl font-bold mt-2">
                Welcome, {student.name || "Student"}
              </h1>

              <p className="text-gray-300 mt-2">
                {studentId || "Student ID not available"}
                {student.intake
                  ? ` • Intake ${student.intake}`
                  : ""}
              </p>

              <p
                className={`mt-4 font-semibold ${badgeColor}`}
              >
                {badge}
              </p>

            </div>

            <div className="flex flex-wrap gap-3">

              <button
                onClick={() =>
                  navigate("/student/profile")
                }
                className="px-5 py-3 rounded-xl bg-white/5 hover:bg-white/10 border border-white/10 transition"
              >
                View Profile
              </button>

              <button
                onClick={() =>
                  navigate("/student/appeal/new")
                }
                className="px-5 py-3 rounded-xl bg-blue-600 hover:bg-blue-700 font-semibold transition"
              >
                Submit Appeal
              </button>

            </div>

          </div>

        </section>

        {/* Risk Alert */}

        {overallScore < 60 && (
          <section className="mt-6 bg-red-500/10 border border-red-500/30 rounded-2xl p-5">

            <div className="flex items-start gap-4">

              <div className="text-3xl">
                🚨
              </div>

              <div>

                <h2 className="text-lg font-bold text-red-300">
                  Performance Alert
                </h2>

                <p className="text-gray-300 mt-2">
                  Your current overall performance is below
                  the recommended level. Improve attendance,
                  classroom attention and follow examination
                  rules.
                </p>

              </div>

            </div>

          </section>
        )}

        {/* Metric Cards */}

        <section className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-4 gap-5 mt-7">

          <MetricCard
            title="Attendance"
            value={`${attendanceRate}%`}
            subtitle={`${myAttendance.length} attendance records`}
            icon="📅"
            valueClass={getScoreClass(
              attendanceRate
            )}
          />

          <MetricCard
            title="Lecture Behaviour"
            value={`${behaviorScore}%`}
            subtitle={`${myLectureBehavior.length} lecture records`}
            icon="🧠"
            valueClass={getScoreClass(
              behaviorScore
            )}
          />

          <MetricCard
            title="Exam Behaviour"
            value={
              examBehaviorScore === null
                ? "No Data"
                : `${examBehaviorScore}%`
            }
            subtitle={`${myExamBehavior.length} exam records`}
            icon="📝"
            valueClass={
              examBehaviorScore === null
                ? "text-gray-400"
                : getScoreClass(
                    examBehaviorScore
                  )
            }
          />

          <MetricCard
            title="Overall Score"
            value={`${overallScore}%`}
            subtitle="Combined performance"
            icon="📊"
            valueClass={getScoreClass(
              overallScore
            )}
          />

        </section>

        {/* Charts */}

        <section className="grid grid-cols-1 xl:grid-cols-2 gap-6 mt-7">

          {/* Attendance Trend */}

          <div className="bg-[#0b2236] border border-white/10 rounded-2xl p-5">

            <h2 className="text-xl font-bold">
              Attendance Trend
            </h2>

            <p className="text-gray-400 text-sm mt-1 mb-5">
              Session-by-session attendance records
            </p>

            {attendanceTrendData.length > 0 ? (
              <ResponsiveContainer
                width="100%"
                height={300}
              >

                <LineChart
                  data={attendanceTrendData}
                >

                  <CartesianGrid
                    strokeDasharray="3 3"
                    stroke="#334155"
                  />

                  <XAxis
                    dataKey="label"
                    stroke="#94a3b8"
                  />

                  <YAxis
                    domain={[0, 100]}
                    stroke="#94a3b8"
                  />

                  <Tooltip
                    contentStyle={{
                      backgroundColor: "#0f172a",
                      border:
                        "1px solid #334155",
                      borderRadius: "10px",
                    }}
                  />

                  <Line
                    type="monotone"
                    dataKey="score"
                    stroke="#3b82f6"
                    strokeWidth={3}
                    dot={{
                      r: 5,
                    }}
                  />

                </LineChart>

              </ResponsiveContainer>
            ) : (
              <EmptyState
                icon="📅"
                message="No attendance records available."
              />
            )}

          </div>

          {/* Score Comparison */}

          <div className="bg-[#0b2236] border border-white/10 rounded-2xl p-5">

            <h2 className="text-xl font-bold">
              Score Comparison
            </h2>

            <p className="text-gray-400 text-sm mt-1 mb-5">
              Attendance, lecture and exam performance
            </p>

            <ResponsiveContainer
              width="100%"
              height={300}
            >

              <BarChart
                data={scoreComparisonData}
              >

                <CartesianGrid
                  strokeDasharray="3 3"
                  stroke="#334155"
                  vertical={false}
                />

                <XAxis
                  dataKey="name"
                  stroke="#94a3b8"
                />

                <YAxis
                  domain={[0, 100]}
                  stroke="#94a3b8"
                />

                <Tooltip
                  contentStyle={{
                    backgroundColor: "#0f172a",
                    border:
                      "1px solid #334155",
                    borderRadius: "10px",
                  }}
                />

                <Bar
                  dataKey="value"
                  fill="#22c55e"
                  radius={[8, 8, 0, 0]}
                />

              </BarChart>

            </ResponsiveContainer>

          </div>

        </section>

        {/* Lecture Behavior Analysis */}

        <section className="bg-[#0b2236] border border-white/10 rounded-2xl p-5 mt-7">

          <div className="mb-6">

            <h2 className="text-xl font-bold">
              Lecture Behaviour Analysis
            </h2>

            <p className="text-gray-400 text-sm mt-1">
              AI-detected classroom behaviour summary
            </p>

          </div>

          {totalLectureBehaviorTime > 0 ? (
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">

              <div className="grid grid-cols-2 gap-4">

                <BehaviorCard
                  title="Attentive"
                  value={attentiveTime}
                  icon="👀"
                  positive
                />

                <BehaviorCard
                  title="Sleeping"
                  value={sleepingTime}
                  icon="😴"
                />

                <BehaviorCard
                  title="Phone Use"
                  value={phoneUseTime}
                  icon="📱"
                />

                <BehaviorCard
                  title="Not Attentive"
                  value={notAttentiveTime}
                  icon="↗️"
                />

              </div>

              <ResponsiveContainer
                width="100%"
                height={300}
              >

                <PieChart>

                  <Pie
                    data={lectureBehaviorData}
                    dataKey="value"
                    nameKey="name"
                    innerRadius={60}
                    outerRadius={100}
                    paddingAngle={3}
                    label={({ name }) => name}
                  >

                    {lectureBehaviorData.map(
                      (item, index) => (
                        <Cell
                          key={item.name}
                          fill={
                            BEHAVIOR_COLORS[
                              index %
                                BEHAVIOR_COLORS.length
                            ]
                          }
                        />
                      )
                    )}

                  </Pie>

                  <Tooltip
                    formatter={(value) =>
                      `${Number(value).toFixed(
                        2
                      )} seconds`
                    }
                    contentStyle={{
                      backgroundColor: "#0f172a",
                      border:
                        "1px solid #334155",
                      borderRadius: "10px",
                    }}
                  />

                  <Legend />

                </PieChart>

              </ResponsiveContainer>

            </div>
          ) : (
            <EmptyState
              icon="🧠"
              message="No lecture behaviour records available."
            />
          )}

        </section>

        {/* Exam Behaviour */}

        <section className="bg-[#0b2236] border border-white/10 rounded-2xl p-5 mt-7">

          <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 mb-6">

            <div>

              <h2 className="text-xl font-bold">
                Exam Behaviour Analysis
              </h2>

              <p className="text-gray-400 text-sm mt-1">
                AI-detected examination behaviour
              </p>

            </div>

            <span
              className={`inline-flex px-4 py-2 rounded-full text-sm font-semibold border ${getExamStatusClass()}`}
            >
              {examStatus}
              {examBehaviorScore !== null
                ? ` • ${examBehaviorScore}%`
                : ""}
            </span>

          </div>

          {!hasExamData ? (
            <EmptyState
              icon="📝"
              message="No exam behaviour records are available yet."
            />
          ) : (
            <>

              <div className="grid grid-cols-1 md:grid-cols-3 gap-4">

                <ExamMetricCard
                  title="Non-Cheating Time"
                  value={nonCheatingTime}
                  icon="✅"
                  type="good"
                />

                <ExamMetricCard
                  title="Suspicious Time"
                  value={examCheatingTime}
                  icon="⚠️"
                  type="risk"
                />

                <ExamMetricCard
                  title="Exam Behaviour Score"
                  value={`${examBehaviorScore}%`}
                  icon="📊"
                  showSeconds={false}
                  type={
                    examBehaviorScore >= 80
                      ? "good"
                      : examBehaviorScore >= 60
                      ? "warning"
                      : "risk"
                  }
                />

              </div>

              <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mt-5">

                <InfoCard
                  label="Latest Exam Date"
                  value={
                    latestExamRecord?.date ||
                    latestExamRecord?.created_at ||
                    "Not available"
                  }
                />

                <InfoCard
                  label="Exam Records"
                  value={myExamBehavior.length}
                />

                <InfoCard
                  label="Detected Status"
                  value={examStatus}
                />

              </div>

              <div className="mt-6 bg-blue-500/10 border border-blue-500/30 rounded-xl p-5">

                <h3 className="font-semibold text-blue-300">
                  🤖 AI Exam Recommendation
                </h3>

                <p className="text-gray-300 mt-2">

                  {examBehaviorScore >= 80
                    ? "Excellent exam behaviour. No significant suspicious activity was detected."
                    : examBehaviorScore >= 60
                    ? "Some unusual behaviour was detected. Stay focused and avoid unnecessary movements during examinations."
                    : "A high level of suspicious behaviour was detected. Follow examination rules and avoid actions that may be interpreted as cheating."}

                </p>

              </div>

            </>
          )}

        </section>

        {/* Attendance History */}

        <section className="bg-[#0b2236] border border-white/10 rounded-2xl p-5 mt-7">

          <h2 className="text-xl font-bold">
            Attendance History
          </h2>

          <p className="text-gray-400 text-sm mt-1 mb-5">
            Your recorded classroom attendance
          </p>

          {attendanceRecords.length > 0 ? (
            <AttendanceTable
              records={attendanceRecords}
            />
          ) : (
            <EmptyState
              icon="📋"
              message="No attendance history available."
            />
          )}

        </section>

        {/* Appeals */}

        <section className="bg-[#0b2236] border border-white/10 rounded-2xl p-5 mt-7">

          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 mb-5">

            <div>

              <h2 className="text-xl font-bold">
                My Appeals
              </h2>

              <p className="text-gray-400 text-sm mt-1">
                Track your submitted appeals
              </p>

            </div>

            <button
              onClick={() =>
                navigate("/student/appeal/new")
              }
              className="bg-blue-600 hover:bg-blue-700 px-5 py-2.5 rounded-xl font-semibold transition"
            >
              New Appeal
            </button>

          </div>

          {myAppeals.length === 0 ? (
            <EmptyState
              icon="📨"
              message="No appeals submitted."
            />
          ) : (
            <div className="space-y-4">

              {myAppeals.map((item, index) => (
                <div
                  key={item._id || index}
                  className="bg-[#071828] border border-white/10 rounded-xl p-5"
                >

                  <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">

                    <div>

                      <p className="font-semibold">
                        {item.type ||
                          "Student Appeal"}
                      </p>

                      <p className="text-gray-400 text-sm mt-2">
                        {item.message ||
                          item.description ||
                          "No message provided."}
                      </p>

                    </div>

                    <AppealStatus
                      status={
                        item.status || "Pending"
                      }
                    />

                  </div>

                </div>
              ))}

            </div>
          )}

        </section>

        {/* Overall Recommendation */}

        <section className="bg-gradient-to-r from-blue-600/15 to-purple-600/15 border border-blue-500/20 rounded-2xl p-6 mt-7">

          <h2 className="text-xl font-bold">
            AI Performance Recommendation
          </h2>

          <p className="text-gray-300 mt-3 leading-relaxed">

            {overallScore >= 80
              ? "Excellent performance. Continue maintaining strong attendance, attentive classroom behaviour and responsible examination conduct."
              : overallScore >= 60
              ? "Your performance is good, but there is room for improvement. Attend lectures regularly and remain more focused during classroom and examination sessions."
              : "Your performance requires attention. Improve attendance, avoid phone usage, remain attentive and follow examination rules carefully."}

          </p>

        </section>

      </div>

      {/* Download PDF */}

      <div className="text-center py-8">

        <button
          onClick={downloadPDF}
          disabled={downloading}
          className="bg-blue-600 hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed px-7 py-3 rounded-xl text-white font-semibold transition"
        >
          {downloading
            ? "Generating PDF..."
            : "Download Dashboard PDF"}
        </button>

      </div>

    </div>
  );
}

function MetricCard({
  title,
  value,
  subtitle,
  icon,
  valueClass = "text-white",
}) {
  return (
    <div className="bg-[#0b2236] rounded-2xl p-5 shadow-lg border border-white/10 hover:-translate-y-1 transition">

      <div className="flex items-start justify-between">

        <div>

          <h3 className="text-gray-400 text-sm">
            {title}
          </h3>

          <h2
            className={`text-3xl font-bold mt-3 ${valueClass}`}
          >
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

function BehaviorCard({
  title,
  value,
  icon,
  positive = false,
}) {
  return (
    <div className="bg-[#071828] border border-white/10 rounded-xl p-4">

      <div className="text-2xl">
        {icon}
      </div>

      <p className="text-gray-400 text-sm mt-3">
        {title}
      </p>

      <h3
        className={`text-2xl font-bold mt-2 ${
          positive
            ? "text-green-400"
            : Number(value) > 0
            ? "text-red-400"
            : "text-gray-400"
        }`}
      >
        {Number(value).toFixed(2)}
      </h3>

      <p className="text-xs text-gray-500 mt-1">
        seconds
      </p>

    </div>
  );
}

function ExamMetricCard({
  title,
  value,
  icon,
  type,
  showSeconds = true,
}) {
  let valueClass = "text-red-400";
  let borderClass = "border-red-500/20";

  if (type === "good") {
    valueClass = "text-green-400";
    borderClass = "border-green-500/20";
  } else if (type === "warning") {
    valueClass = "text-yellow-400";
    borderClass = "border-yellow-500/20";
  }

  return (
    <div
      className={`bg-[#071828] border ${borderClass} rounded-xl p-5`}
    >

      <div className="text-2xl">
        {icon}
      </div>

      <p className="text-sm text-gray-400 mt-3">
        {title}
      </p>

      <h3
        className={`text-2xl font-bold mt-2 ${valueClass}`}
      >
        {typeof value === "number"
          ? value.toFixed(2)
          : value}
      </h3>

      {showSeconds && (
        <p className="text-xs text-gray-500 mt-1">
          seconds
        </p>
      )}

    </div>
  );
}

function InfoCard({ label, value }) {
  return (
    <div className="bg-[#071828] border border-white/10 rounded-xl p-4">

      <p className="text-xs text-gray-500">
        {label}
      </p>

      <p className="font-semibold mt-2 break-words">
        {value}
      </p>

    </div>
  );
}

function AppealStatus({ status }) {
  const normalizedStatus = String(
    status
  ).toLowerCase();

  let className =
    "bg-yellow-500/15 text-yellow-400 border-yellow-500/30";

  if (
    normalizedStatus === "approved" ||
    normalizedStatus === "accepted"
  ) {
    className =
      "bg-green-500/15 text-green-400 border-green-500/30";
  } else if (
    normalizedStatus === "rejected" ||
    normalizedStatus === "declined"
  ) {
    className =
      "bg-red-500/15 text-red-400 border-red-500/30";
  }

  return (
    <span
      className={`inline-flex px-4 py-2 rounded-full text-sm font-semibold border ${className}`}
    >
      {status}
    </span>
  );
}

function EmptyState({ icon, message }) {
  return (
    <div className="min-h-[180px] flex flex-col items-center justify-center text-center text-gray-500">

      <div className="text-4xl mb-3">
        {icon}
      </div>

      <p>
        {message}
      </p>

    </div>
  );
}