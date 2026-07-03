// src/pages/student/AppealsList.jsx
import React, { useEffect, useState } from "react";

export default function AppealsList() {
  const [appeals, setAppeals] = useState([]);

  useEffect(() => {
    const stored = JSON.parse(localStorage.getItem("appeals") || "[]");
    setAppeals(stored);
  }, []);

  function removeLocal(id) {
    const filtered = appeals.filter((a) => a.id !== id);
    localStorage.setItem("appeals", JSON.stringify(filtered));
    setAppeals(filtered);
  }

  return (
    <div className="max-w-4xl mx-auto">
      <h2 className="text-2xl font-semibold mb-4">My Submitted Appeals</h2>

      {appeals.length === 0 && <div className="text-[var(--muted)]">No appeals submitted yet.</div>}

      <div className="space-y-4">
        {appeals.map((a) => (
          <div key={a.id} className="bg-[var(--card)] p-4 rounded-xl border border-[#122232] flex justify-between items-start">
            <div>
              <div className="flex items-center gap-3">
                <div className="text-sm font-semibold">{a.type === "marks-appeal" ? "Marks Appeal" : "Complaint"}</div>
                <div className="text-xs text-[var(--muted)]">{new Date(a.createdAt).toLocaleString()}</div>
                {a.subject && <div className="text-xs ml-2 px-2 py-0.5 bg-[#0b1c2b] rounded text-[var(--muted)]">{a.subject}</div>}
              </div>

              <p className="mt-2 text-[var(--muted)]">{a.message}</p>

              {a.attachmentName && <div className="text-xs text-[var(--muted)] mt-2">Attachment: {a.attachmentName}</div>}
            </div>

            <div className="text-right">
              <div className={`font-semibold ${a.status === "Pending" ? "text-yellow-400" : "text-green-400"}`}>{a.status}</div>
              <div className="text-xs text-[var(--muted)] mt-2">{a.studentName}</div>
              <button onClick={() => removeLocal(a.id)} className="mt-3 text-sm px-3 py-1 rounded-md bg-[#1b2b3a]">Remove</button>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
