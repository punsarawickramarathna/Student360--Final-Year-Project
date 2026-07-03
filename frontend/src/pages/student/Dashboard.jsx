// src/pages/student/Dashboard.jsx

import React, { useEffect, useState, useRef } from "react";
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
  Bar
} from "recharts";

import {
  getAttendance,
  getBehavior,
  getAppeals,
  getSessions
} from "../../api/api";

export default function StudentDashboard() {

  const dashboardRef = useRef();

  // Logged user
  const student =
    JSON.parse(localStorage.getItem("user")) || {};

  // States
  const [attendance, setAttendance] = useState([]);
  const [behavior, setBehavior] = useState([]);
  const [appeals, setAppeals] = useState([]);
  const [sessions, setSessions] = useState({
      count: 0,
      data: []
  });
  const [loading, setLoading] = useState(true);

  // Load backend data
  useEffect(() => {

    async function loadData() {

      try {

        const attRes = await getAttendance();
        const behRes = await getBehavior();
        const appRes = await getAppeals();
        const sesRes = await getSessions();

console.log(JSON.stringify(sesRes, null, 2));
console.log("Sessions State:", sessions);


        setAttendance(attRes.data);
        setBehavior(behRes.data);
        setAppeals(appRes.data);
        setSessions(sesRes.data);
        

      } catch (err) {

        console.log(err);

      }

      setLoading(false);

    }

    loadData();

  }, []);

  if (loading) {

    return (
      <div className="text-center mt-10 text-white">
        Loading Dashboard...
      </div>
    );

  }

  // Student Attendance
  const myAttendance = attendance.filter(
    (a) => a.student_id === student.student_id
  );

  // Student Behavior
  const myBehavior = behavior.filter(
    (b) => b.student_id === student.student_id
  );

  // Student Appeals
  const myAppeals = appeals.filter(
    (a) => a.student_id === student.student_id
  );

  // Attendance %
const totalSessions = sessions.length;

const attendanceRate =
    totalSessions > 0
        ? Math.round((myAttendance.length / totalSessions) * 100)
        : 0;


  // Behavior %
  let totalPenalty = 0;

myBehavior.forEach((b) => {
    totalPenalty +=
        (b.phone_use || 0) +
        (b.sleeping || 0) +
        (b.cheating || 0);
});

const behaviorScore = Math.max(100 - totalPenalty, 0);
  // Exam (temporary until backend sends it)
  const examBehaviorScore = 90;

  // Overall
  const overallScore = Math.round(
    (
      attendanceRate +
      behaviorScore +
      examBehaviorScore
    ) / 3
  );

  // Badge

  let badge = "";
  let badgeColor = "";

  if (overallScore >= 80) {

    badge = "Excellent Student 🏆";
    badgeColor = "text-green-400";

  }

  else if (overallScore >= 60) {

    badge = "Good Student 👍";
    badgeColor = "text-yellow-400";

  }

  else {

    badge = "Needs Improvement ⚠";
    badgeColor = "text-red-400";

  }

  // Attendance Chart

  const attentionData = myAttendance.map((item, index) => ({

    week: `Week ${index + 1}`,

    score: attendanceRate

  }));

  // Bar Chart

  const behaviorData = [

    {

      name: "Attendance",

      value: attendanceRate

    },

    {

      name: "Behavior",

      value: behaviorScore

    },

    {

      name: "Exam",

      value: examBehaviorScore

    }

  ];

  // Attendance Table

  const attendanceRecords = myAttendance.map((item) => ({

    date: item.date || "-",

    status: item.status || "Present"

  }));

    // PDF Download

  const downloadPDF = async () => {

    const canvas = await html2canvas(
      dashboardRef.current,
      {
        scale: 2,
        useCORS: true
      }
    );

    const imgData = canvas.toDataURL("image/png");

    const pdf = new jsPDF(
      "p",
      "mm",
      "a4"
    );

    const pdfWidth =
      pdf.internal.pageSize.getWidth();

    const pdfHeight =
      (canvas.height * pdfWidth) /
      canvas.width;

    pdf.addImage(
      imgData,
      "PNG",
      0,
      0,
      pdfWidth,
      pdfHeight
    );

    pdf.save(
      "Student360_Report.pdf"
    );

  };

  return (

    <div className="min-h-screen bg-[#020817] text-white">

      <Navbar />

      <div
        ref={dashboardRef}
        className="max-w-6xl mx-auto p-6"
      >

        <h1 className="text-3xl font-bold">

          Welcome {student.name}

        </h1>

        <p
          className={`mt-2 font-semibold ${badgeColor}`}
        >
          {badge}
        </p>

        {/* Metric Cards */}

        <div className="grid grid-cols-1 md:grid-cols-4 gap-5 mt-8">

          <MetricCard
            title="Attendance"
            value={`${attendanceRate}%`}
          />

          <MetricCard
            title="Behavior"
            value={`${behaviorScore}%`}
          />

          <MetricCard
            title="Exam"
            value={`${examBehaviorScore}%`}
          />

          <MetricCard
            title="Overall"
            value={`${overallScore}%`}
          />

        </div>

        {/* Attendance Trend */}

        <div className="bg-[#0b2236] rounded-xl p-6 mt-8">

          <h2 className="text-xl font-bold mb-4">

            Attendance Trend

          </h2>

          <ResponsiveContainer
            width="100%"
            height={300}
          >

            <LineChart
              data={attentionData}
            >

              <CartesianGrid strokeDasharray="3 3"/>

              <XAxis dataKey="week"/>

              <YAxis/>

              <Tooltip/>

              <Line
                type="monotone"
                dataKey="score"
                stroke="#3b82f6"
                strokeWidth={3}
              />

            </LineChart>

          </ResponsiveContainer>

        </div>

        {/* Score Chart */}

        <div className="bg-[#0b2236] rounded-xl p-6 mt-8">

          <h2 className="text-xl font-bold mb-4">

            Score Comparison

          </h2>

          <ResponsiveContainer
            width="100%"
            height={300}
          >

            <BarChart
              data={behaviorData}
            >

              <XAxis dataKey="name"/>

              <YAxis/>

              <Tooltip/>

              <Bar
                dataKey="value"
                fill="#22c55e"
              />

            </BarChart>

          </ResponsiveContainer>

        </div>

        {/* Attendance Table */}

        <div className="bg-[#0b2236] rounded-xl p-6 mt-8">

          <h2 className="text-xl font-bold mb-4">

            Attendance History

          </h2>

          <AttendanceTable
            records={attendanceRecords}
          />

        </div>

        {/* Appeals */}

        <div className="bg-[#0b2236] rounded-xl p-6 mt-8">

          <h2 className="text-xl font-bold mb-4">

            My Appeals

          </h2>

          {

            myAppeals.length === 0 ?

            (

              <p>

                No appeals submitted.

              </p>

            )

            :

            (

              myAppeals.map((item,index)=>(

                <div
                  key={index}
                  className="border-b py-3"
                >

                  <p>

                    <b>Type :</b>

                    {item.type}

                  </p>

                  <p>

                    {item.message}

                  </p>

                  <p>

                    Status :

                    {item.status}

                  </p>

                </div>

              ))

            )

          }

        </div>

        {/* AI Recommendation */}

        <div className="bg-[#0b2236] rounded-xl p-6 mt-8">

          <h2 className="text-xl font-bold mb-3">

            AI Recommendation

          </h2>

          {

            overallScore>=80 ?

            (

              <p>

                Excellent performance.
                Keep maintaining your attendance and behaviour.

              </p>

            )

            :

            overallScore>=60 ?

            (

              <p>

                Good work.
                Improve attendance to reach Excellent level.

              </p>

            )

            :

            (

              <p>

                Your attendance and classroom behaviour need improvement.

              </p>

            )

          }

        </div>


              </div>

      {/* Download PDF Button */}

      <div className="text-center py-8">

        <button
          onClick={downloadPDF}
          className="bg-blue-600 hover:bg-blue-700 px-6 py-3 rounded-lg text-white font-semibold"
        >
          Download Dashboard PDF
        </button>

      </div>

    </div>

  );

}

// ============================
// Metric Card Component
// ============================

function MetricCard({

  title,

  value

}) {

  return (

    <div className="bg-[#0b2236] rounded-xl p-5 shadow-lg border border-[#18374f]">

      <h3 className="text-gray-400 text-sm">

        {title}

      </h3>

      <h1 className="text-3xl font-bold mt-3">

        {value}

      </h1>

    </div>

  );

}