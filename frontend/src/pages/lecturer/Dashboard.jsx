import React, { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import {
  getStudents,
  getAttendance,
  getBehavior,
  getSessions,
  sendEmail
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
  YAxis
} from "recharts";

export default function LecturerDashboard() {

  const navigate = useNavigate();

  const classroom =
    JSON.parse(localStorage.getItem("classroom")) || {
      year: "",
      sem: "",
      subject: "",
      group: "",
    };

  const [students, setStudents] = useState([]);
  const [attendance, setAttendance] = useState([]);
  const [behavior, setBehavior] = useState([]);

  const [selected, setSelected] = useState(null);

  const [search, setSearch] = useState("");

  useEffect(() => {
    loadDashboard();
  }, []);

  async function loadDashboard() {

    try {

      const stu = await getStudents();
      const att = await getAttendance();
      const beh = await getBehavior();
      const ses = await getSessions();
      setAttendance(att.data);
      setBehavior(beh.data);

      const finalStudents = stu.data.map((student) => {

        const attRecords = att.data.filter(
          (a) => a.student_id === student.student_id
        );

        const behRecords = beh.data.filter(
          (b) => b.student_id === student.student_id
        );

        const totalSessions = Number(ses.count || 0);

const attendanceRate =
totalSessions === 0
  ? 0
  : Math.min(
      Math.round((attRecords.length / totalSessions) * 100),
      100
    );

let attentive = 0;
let cheating = 0;
let sleeping = 0;
let phone = 0;
let notAttentive = 0;

behRecords.forEach((r) => {

  attentive += Number(r.attentive || 0);
  cheating += Number(r.cheating || 0);
  sleeping += Number(r.sleeping || 0);
  phone += Number(r.phone_use || 0);
  notAttentive += Number(r.not_attentive || 0);

});

const totalTime =
  attentive +
  cheating +
  sleeping +
  phone +
  notAttentive;

const goodTime = attentive;

const behaviorScore =
  totalTime === 0
    ? 100
    : Math.round((goodTime / totalTime) * 100);

      const overall = Math.round(

      attendanceRate * 0.4 +

      behaviorScore * 0.6

      );

        return {

          id: student.student_id || "",

          name: student.name || "Unknown",

          intake: student.intake || "",

          attendance: attendanceRate,

          behavior: behaviorScore,

          overall,

          email:
            (student.student_id || "").toLowerCase() +
            "@gmail.com",

        };

      });

      finalStudents.sort(
        (a, b) => b.overall - a.overall
      );

      setStudents(finalStudents);

    } catch (err) {

      console.log(err);

    }

  }

  const riskyStudents = students.filter(
    (s) => s.overall < 60
  );

  // ===========================
  // Attendance vs Behaviour Chart
  // ===========================

const performanceData = students.map((student) => ({

  name: student.name,

  Attendance: student.attendance,

  Behaviour: student.behavior

}));


// ===========================
// Risk Pie Chart
// ===========================

const riskData = [

  {

    name: "Good",

    value: students.length - riskyStudents.length

  },

  {

    name: "Risk",

    value: riskyStudents.length

  }

];


// ===========================
// Behaviour Distribution
// ===========================

let attentive = 0;
let cheating = 0;
let sleeping = 0;
let phone = 0;

behavior.forEach((item) => {

  attentive += Number(item.attentive || 0);

  cheating += Number(item.cheating || 0);

  sleeping += Number(item.sleeping || 0);

  phone += Number(item.phone_use || 0);

});

const totalBehaviourTime =
  attentive +
  cheating +
  sleeping +
  phone;

  const attentivePercent =
  totalBehaviourTime === 0
    ? 0
    : Number(
        ((attentive / totalBehaviourTime) * 100).toFixed(1)
      );

const cheatingPercent =
  totalBehaviourTime === 0
    ? 0
    : Number(
        ((cheating / totalBehaviourTime) * 100).toFixed(1)
      );

const phonePercent =
  totalBehaviourTime === 0
    ? 0
    : Number(
        ((phone / totalBehaviourTime) * 100).toFixed(1)
      );

const sleepingPercent =
  totalBehaviourTime === 0
    ? 0
    : Number(
        ((sleeping / totalBehaviourTime) * 100).toFixed(1)
      );

const behaviourData = [

  {
    name: "Attentive",
    value: attentivePercent
  },

  {
    name: "Cheating",
    value: cheatingPercent
  },

  {
    name: "Phone",
    value: phonePercent
  },

  {
    name: "Sleeping",
    value: sleepingPercent
  }

];

const COLORS = [

  "#22c55e",

  "#3b82f6",

  "#ef4444",

  "#f59e0b"

];

  // ============================
  // Export CSV
  // ============================

  const exportCSV = () => {

    let csv =
      "Student ID,Name,Attendance,Behavior,Overall\n";

    students.forEach((s) => {

      csv += `${s.id},${s.name},${s.attendance},${s.behavior},${s.overall}\n`;

    });

    const blob = new Blob([csv], {
      type: "text/csv",
    });

    const url = window.URL.createObjectURL(blob);

    const link = document.createElement("a");

    link.href = url;

    link.download = "Student360_Report.csv";

    link.click();

  };

  // ============================
  // Notify Students
  // ============================

  const notifyStudents = async () => {

    if (riskyStudents.length === 0) {

        alert("No Risk Students");

        return;

    }

    const emails = riskyStudents.map(s => s.email);

    const htmlBody = `

<!DOCTYPE html>

<html>

<head>

<meta charset="UTF-8">

</head>

<body style="margin:0;padding:0;background:#f3f4f6;font-family:Arial,sans-serif;">

<table width="100%" cellpadding="0" cellspacing="0">

<tr>

<td align="center">

<table width="650" cellpadding="0" cellspacing="0"

style="background:white;border-radius:12px;overflow:hidden;box-shadow:0 0 15px rgba(0,0,0,.1);">

<tr>

<td

style="background:#0f172a;padding:25px;color:white;text-align:center;">

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

Our AI Classroom Monitoring System has identified

that your classroom performance requires attention.

</p>

<table

width="100%"

style="border-collapse:collapse;margin-top:20px;">

<tr>

<th

align="left"

style="padding:12px;background:#e5e7eb;">

Areas to Improve

</th>

</tr>

<tr>

<td style="padding:12px;">

✅ Attendance

</td>

</tr>

<tr>

<td style="padding:12px;">

✅ Classroom Behaviour

</td>

</tr>

<tr>

<td style="padding:12px;">

✅ Participation

</td>

</tr>

<tr>

<td style="padding:12px;">

✅ Focus During Lectures

</td>

</tr>

</table>

<div

style="margin-top:25px;
background:#fef3c7;
padding:18px;
border-left:6px solid #f59e0b;">

<strong>

AI Recommendation

</strong>

<p>

Attend lectures regularly,

avoid phone usage,

stay attentive,

and actively participate in classroom activities.

</p>

</div>

<p style="margin-top:25px;">

This notification was automatically generated by

<b>Student360 AI Analytics</b>.

</p>

</td>

</tr>

<tr>

<td

style="background:#0f172a;color:white;padding:18px;text-align:center;">

Student360 AI

<br>

Faculty of Computing

<br>

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

        const res = await sendEmail({

            emails,

            subject: "Student360 AI - Academic Performance Alert",

            body: htmlBody

        });

        alert(res.message);

    }

    catch (err) {

        console.log(err);

        alert("Email Sending Failed");

    }

};

  // ============================
  // Logout
  // ============================

  const logout = () => {

    localStorage.removeItem("token");
    localStorage.removeItem("user");
    localStorage.removeItem("classroom");

    navigate("/");

  };

  return (

  <div className="min-h-screen bg-[#071828] text-white p-8">

    {/* Header */}

    <div className="flex justify-between items-center mb-2">

      <div>

        <h1 className="text-3xl font-bold">

          Lecturer Dashboard

        </h1>

        <p className="text-gray-400 mt-2">

          Year {classroom.year} | Semester {classroom.sem} | {classroom.subject} | Group {classroom.group}

        </p>

      </div>

      <button

        onClick={logout}

        className="px-3 py-1 text-sm rounded-md bg-gradient-to-r from-[var(--accent-from)] to-[var(--accent-to)] shadow-md hover:scale-105 transition-transform"

      >

        Sign Out

      </button>

    </div>

    {/* Dashboard Cards */}

    <div className="grid grid-cols-1 md:grid-cols-4 gap-5 mb-6 mt-6">

      <div className="bg-[#0b2236] rounded-xl p-5">

        <h3>Total Students</h3>

        <h1 className="text-3xl font-bold">

          {students.length}

        </h1>

      </div>

      <div className="bg-[#0b2236] rounded-xl p-5">

        <h3>Attendance Records</h3>

        <h1 className="text-3xl font-bold">

          {attendance.length}

        </h1>

      </div>

      <div className="bg-[#0b2236] rounded-xl p-5">

        <h3>Behavior Logs</h3>

        <h1 className="text-3xl font-bold">

          {behavior.length}

        </h1>

      </div>

      <div className="bg-[#0b2236] rounded-xl p-5">

        <h3>Risk Students</h3>

        <h1 className="text-3xl font-bold text-red-400">

          {riskyStudents.length}

        </h1>

      </div>

    </div>

    {/* Buttons */}

    <div className="flex gap-3 mb-5">

      <button

        onClick={exportCSV}

        className="bg-green-600 hover:bg-green-700 px-5 py-2 rounded"

      >

        Export CSV

      </button>

      <button

        onClick={notifyStudents}

        className="bg-red-600 hover:bg-red-700 px-5 py-2 rounded"

      >

        Notify Risk Students

      </button>

    </div>

    {/* Search */}

    <input

      type="text"

      placeholder="Search Student by ID, Name or Intake..."

      className="w-full bg-[#0b2236] p-3 rounded mb-5"

      value={search}

      onChange={(e) => setSearch(e.target.value)}

    />
{/* ========================= */}
{/* Analytics */}
{/* ========================= */}

<div className="grid md:grid-cols-2 gap-6 mb-8">

  {/* Attendance vs Behaviour */}

  <div className="bg-[#0b2236] rounded-xl p-5">

    <h2 className="text-xl font-bold mb-4">

      Attendance vs Behaviour

    </h2>

    <ResponsiveContainer
      width="100%"
      height={300}
    >

      <BarChart data={performanceData}>

        <CartesianGrid strokeDasharray="3 3"/>

        <XAxis dataKey="name"/>

        <YAxis/>

        <Tooltip/>

        <Legend/>

        <Bar
          dataKey="Attendance"
          fill="#3b82f6"
        />

        <Bar
          dataKey="Behaviour"
          fill="#22c55e"
        />

      </BarChart>

    </ResponsiveContainer>

  </div>


  {/* Behaviour Distribution */}

  <div className="bg-[#0b2236] rounded-xl p-5">

    <h2 className="text-xl font-bold mb-4">

      Behaviour Distribution

    </h2>

    <ResponsiveContainer
      width="100%"
      height={300}
    >

      <PieChart>

      <Pie

          data={behaviourData}
          dataKey="value"
          outerRadius={100}
          label={({ name, percent }) =>
              `${name} ${(percent * 100).toFixed(1)}%`
          }
          

      >

      <Cell fill="#22c55e"/>
      <Cell fill="#3b82f6"/>
      <Cell fill="#ef4444"/>
      <Cell fill="#f59e0b"/>


      </Pie>

        <Tooltip
          formatter={(value) => `${value}%`}
        />

        <Legend/>

      </PieChart>

    </ResponsiveContainer>

  </div>

</div>

<div className="bg-[#0b2236] rounded-xl p-5 mb-6">

<h2 className="text-xl font-bold mb-4">

Risk Student Distribution

</h2>

<ResponsiveContainer
width="100%"
height={300}
>

<PieChart>

<Pie
      data={riskData}
      dataKey="value"
      outerRadius={120}
      label={({ name, value }) => `${name} (${value})`}
    >

      <Cell fill="#22c55e" />

      <Cell fill="#ef4444" />

    </Pie>


<Tooltip/>

<Legend/>

</PieChart>


</ResponsiveContainer>

</div>

    {/* Student Table */}

    <div className="overflow-x-auto">

      <table className="w-full bg-[#0b2236] rounded-xl">

        <thead>

          <tr className="border-b border-gray-700">

            <th className="p-3">Rank</th>

            <th className="p-3">Student ID</th>

            <th className="p-3">Name</th>

            <th className="p-3">Attendance</th>

            <th className="p-3">Behavior</th>

            <th className="p-3">Overall</th>

            <th className="p-3">Status</th>

          </tr>

        </thead>

        <tbody>

          {students

            .filter((s) => {

              const id = (s.id || "").toLowerCase();

              const name = (s.name || "").toLowerCase();

              const intake = (s.intake || "").toLowerCase();

              const query = search.toLowerCase();

              return (

                id.includes(query) ||

                name.includes(query) ||

                intake.includes(query)

              );

            })

            .map((student, index) => (

              <tr

                key={student.id}

                className="border-b border-gray-700 hover:bg-[#123041] cursor-pointer"

                onClick={() => setSelected(student)}

              >

                <td className="p-3 text-center">

                  #{index + 1}

                </td>

                <td className="p-3">

                  {student.id}

                </td>

                <td className="p-3">

                  {student.name}

                </td>

                <td className="p-3 text-center">

                  {student.attendance}%

                </td>

                <td className="p-3 text-center">

                  {student.behavior}%

                </td>

                <td className="p-3 text-center font-bold">

                  {student.overall}%

                </td>

                <td className="p-3 text-center">

                  {student.overall >= 60 ? (

                    <span className="bg-green-600 px-3 py-1 rounded">

                      Good

                    </span>

                  ) : (

                    <span className="bg-red-600 px-3 py-1 rounded">

                      Risk

                    </span>

                  )}

                </td>

              </tr>

            ))}

        </tbody>

      </table>

    </div>

    {/* Student Details Popup */}

    {selected && (

      <div className="fixed inset-0 bg-black/70 flex justify-center items-center">

        <div className="bg-[#0b2236] rounded-xl p-8 w-[420px]">

          <h2 className="text-2xl font-bold mb-5">

            Student Details

          </h2>

          <p>

            <b>Student ID :</b> {selected.id}

          </p>

          <p>

            <b>Name :</b> {selected.name}

          </p>

          <p>

            <b>Intake :</b> {selected.intake}

          </p>

          <hr className="my-4" />

          <p>

            Attendance :

            <b> {selected.attendance}%</b>

          </p>

          <p>

            Behavior :

            <b> {selected.behavior}%</b>

          </p>

          <p>

            Overall Score :

            <b> {selected.overall}%</b>

          </p>

          <div className="mt-6 text-right">

            <button

              onClick={() => setSelected(null)}

              className="bg-blue-600 hover:bg-blue-700 px-6 py-2 rounded"

            >

              Close

            </button>

          </div>

        </div>

      </div>

    )}

  </div>

);

}