// src/components/AttendanceTable.jsx

import React from "react";

export default function AttendanceTable({ records = [] }) {
  const safeRecords = Array.isArray(records) ? records : [];

  return (
    <div className="bg-[#0b2236] rounded-xl p-5 shadow">
      <h2 className="text-xl font-bold text-white mb-4">
        Attendance History
      </h2>

      <table className="w-full text-white border-collapse">
        <thead>
          <tr className="border-b border-gray-600">
            <th className="text-left p-3">Date</th>
            <th className="text-left p-3">Arrival Time</th>
            <th className="text-left p-3">Status</th>
          </tr>
        </thead>

        <tbody>
          {safeRecords.length > 0 ? (
            safeRecords.map((record, index) => {
              const isPresent =
                String(record?.status || "Present")
                  .trim()
                  .toLowerCase() === "present";

              return (
                <tr
                  key={record._id || index}
                  className="border-b border-gray-700 hover:bg-[#123041] transition-colors"
                >
                  <td className="p-3 font-medium text-slate-200">
                    {record.date || "-"}
                  </td>
                  <td className="p-3 font-mono text-xs text-slate-400">
                    {record.arrival_time || "-"}
                  </td>
                  <td className="p-3">
                    {isPresent ? (
                      <span className="bg-emerald-600/90 text-white font-semibold text-xs px-3 py-1 rounded-full border border-emerald-500/30">
                        Present
                      </span>
                    ) : (
                      <span className="bg-rose-600/90 text-white font-semibold text-xs px-3 py-1 rounded-full border border-rose-500/30">
                        Absent
                      </span>
                    )}
                  </td>
                </tr>
              );
            })
          ) : (
            <tr>
              <td
                colSpan="3"
                className="text-center p-5 text-gray-400"
              >
                No Attendance Records Found
              </td>
            </tr>
          )}
        </tbody>
      </table>
    </div>
  );
}