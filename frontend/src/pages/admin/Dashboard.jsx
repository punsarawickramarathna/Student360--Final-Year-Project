// src/pages/admin/Dashboard.jsx

import React, { useEffect, useState } from "react";
import Navbar from "../../components/Navbar";
import {
  getStudents,
  getAttendance,
  getBehavior,
  getAppeals,
  getSessions
} from "../../api/api";
import { uploadSessionCSV } from "../../api/api";

export default function AdminDashboard() {

  const [students, setStudents] = useState([]);
  const [attendance, setAttendance] = useState([]);
  const [behavior, setBehavior] = useState([]);
  const [appeals, setAppeals] = useState([]);
  const [sessions, setSessions] = useState({
  count: 0,
  data: []
});
const handleCSVUpload = async (e) => {
  const file = e.target.files[0];

  if (!file) return;

  try {
    const res = await uploadSessionCSV(file);
    alert("Upload Success: " + res.message);
  } catch (err) {
    console.log(err);
    alert("Upload Failed");
  }
};

  useEffect(() => {

    async function loadData() {

      try {

        const stu = await getStudents();
        const att = await getAttendance();
        const beh = await getBehavior();
        const app = await getAppeals();
        const ses = await getSessions();


        setStudents(stu.data);
        setAttendance(att.data);
        setBehavior(beh.data);
        setAppeals(app.data);
        setSessions(ses.data);

      } catch (err) {

        console.log(err);

      }

    }

    loadData();

  }, []);

  function Card({

  title,

  value,

  color

}) {

  return (

    <div className="bg-[#0b2236] rounded-xl p-5 shadow-lg border border-[#17344d]">

      <h3 className="text-gray-400 text-sm">

        {title}

      </h3>

      <h1 className={`text-3xl font-bold mt-3 ${color}`}>

        {value}

      </h1>

    </div>

  );

}  

// ===============================
// Admin Analytics
// ===============================

// Total Students
const totalStudents = students.length;

// Pending Appeals
const pendingAppeals =
  appeals.filter(
    (a) => a.status === "Pending"
  ).length;

// Risk Students
const riskStudents =
  behavior.filter((b) => {

    const badTime =
      (b.phone_use || 0) +
      (b.sleeping || 0) +
      (b.cheating || 0);

    return badTime > 20;

  }).length;


// ===============================
// Average Attendance
// ===============================

// Total sessions (safe fallback)
const totalSessions = sessions?.data?.length || 1;

// Count attendance per student
const attendanceMap = {};

attendance.forEach((a) => {
  attendanceMap[a.student_id] =
    (attendanceMap[a.student_id] || 0) + 1;
});

// Convert to percentages per student
const percentages = Object.values(attendanceMap).map(
  (present) =>
    Math.min((present / totalSessions) * 100, 100)
);

// Final average attendance
const averageAttendance =
  percentages.length === 0
    ? 0
    : Math.round(
        percentages.reduce((a, b) => a + b, 0) /
        percentages.length
      );
      
// ===============================
// Average Behaviour
// ===============================

let behaviourScore = 0;

behavior.forEach((b) => {

  const badTime =
    (b.phone_use || 0) +
    (b.sleeping || 0) +
    (b.cheating || 0);

  behaviourScore +=
    Math.max(100 - badTime, 0);

});

const averageBehaviour =
  behavior.length === 0
    ? 100
    : Math.round(
        behaviourScore /
        behavior.length
      );


// ===============================
// Most Common Violation
// ===============================

let cheating = 0;
let sleeping = 0;
let phone = 0;

behavior.forEach((b) => {

  if ((b.cheating || 0) > 0)
    cheating++;

  if ((b.sleeping || 0) > 0)
    sleeping++;

  if ((b.phone_use || 0) > 0)
    phone++;

});

const violations = [

  {
    name: "Phone Use",
    count: phone
  },

  {
    name: "Sleeping",
    count: sleeping
  },

  {
    name: "Cheating",
    count: cheating
  }

];

violations.sort(
  (a, b) => b.count - a.count
);

const mostCommonViolation =
  violations[0]?.name || "None";


  return (

    <div className="min-h-screen bg-[#071a2c] text-white">

      <Navbar />

      <div className="max-w-7xl mx-auto px-6 py-8">

        <h1 className="text-3xl font-bold mb-6">
          Admin Dashboard
        </h1>

        {/* Statistics */}

<div className="grid grid-cols-1 md:grid-cols-3 lg:grid-cols-6 gap-5">

  <Card
    title="Students"
    value={totalStudents}
    color="text-blue-400"
  />

  <Card
    title="Avg Attendance"
    value={`${averageAttendance}%`}
    color="text-green-400"
  />

  <Card
    title="Avg Behaviour"
    value={`${averageBehaviour}%`}
    color="text-yellow-400"
  />

  <Card
    title="Top Violation"
    value={mostCommonViolation}
    color="text-red-400"
  />

  <Card
    title="Risk Students"
    value={riskStudents}
    color="text-red-500"
  />

  <Card
    title="Pending Appeals"
    value={pendingAppeals}
    color="text-purple-400"
  />

</div>

        {/* Actions */}

        <div className="grid md:grid-cols-2 gap-6 mt-8">

          <div className="bg-[#0b2236] rounded-xl p-6">

            <h2 className="text-xl font-semibold">
              User Management
            </h2>

            <p className="text-gray-400 mt-2">
              Register new students or lecturers into Student360.
            </p>

            <button
              onClick={() => window.location = "/admin/add-user"}
              className="mt-5 bg-green-600 hover:bg-green-700 px-5 py-3 rounded-lg"
            >
              Add User
            </button>

          </div>

          <div className="bg-[#0b2236] rounded-xl p-6">

            <h2 className="text-xl font-semibold">
              AI Engine
            </h2>

            <p className="text-gray-400 mt-2">
              Upload classroom session summaries generated by the AI Engine.
            </p>

            <label className="cursor-pointer bg-blue-600 hover:bg-blue-700 px-5 py-3 rounded-lg inline-block mt-5">
            Upload CSV
            <input
              type="file"
              accept=".csv"
              onChange={handleCSVUpload}
              className="hidden"
            />
          </label>

          </div>

        </div>

        {/* Appeals */}

        <div className="bg-[#0b2236] rounded-xl p-6 mt-8">

          <h2 className="text-xl font-semibold mb-4">
            Latest Appeals
          </h2>

          {
            appeals.length === 0 ? (

              <p>No appeals available.</p>

            ) : (

              <table className="w-full">

                <thead>

                  <tr className="border-b border-gray-600">

                    <th className="text-left p-2">
                      Student
                    </th>

                    <th className="text-left p-2">
                      Type
                    </th>

                    <th className="text-left p-2">
                      Status
                    </th>

                  </tr>

                </thead>

                <tbody>

                  {

                    appeals.map((item, index) => (

                      <tr
                        key={index}
                        className="border-b border-gray-700"
                      >

                        <td className="p-2">
                          {item.student_id}
                        </td>

                        <td className="p-2">
                          {item.type}
                        </td>

                        <td className="p-2">
                          {item.status}
                        </td>

                      </tr>

                    ))

                  }

                </tbody>

              </table>

            )

          }

        </div>

      </div>

    </div>

  );

  

}