// src/components/AttendanceTable.jsx

import React from "react";

export default function AttendanceTable({ records }) {

  return (

    <div className="bg-[#0b2236] rounded-xl p-5 shadow">

      <h2 className="text-xl font-bold text-white mb-4">

        Attendance History

      </h2>

      <table className="w-full text-white border-collapse">

        <thead>

          <tr className="border-b border-gray-600">

            <th className="text-left p-3">

              Date

            </th>

            <th className="text-left p-3">

              Status

            </th>

          </tr>

        </thead>

        <tbody>

          {

            records.length > 0 ?

            records.map((record, index) => (

              <tr
                key={index}
                className="border-b border-gray-700 hover:bg-[#123041]"
              >

                <td className="p-3">

                  {record.date}

                </td>

                <td className="p-3">

                  {

                    record.status === "Present"

                    ?

                    <span className="bg-green-600 px-3 py-1 rounded">

                      Present

                    </span>

                    :

                    <span className="bg-red-600 px-3 py-1 rounded">

                      Absent

                    </span>

                  }

                </td>

              </tr>

            ))

            :

            <tr>

              <td
                colSpan="2"
                className="text-center p-5 text-gray-400"
              >

                No Attendance Records Found

              </td>

            </tr>

          }

        </tbody>

      </table>

    </div>

  );

}