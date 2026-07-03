// src/pages/student/AppealForm.jsx
import React, { useState } from "react";

const SUBJECTS = [
  "Algorithms",
  "Operating Systems",
  "Database Systems",
  "Computer Networks",
  "Software Engineering",
];

export default function AppealForm({ onSubmitted }) {
  const [type, setType] = useState("complaint"); // complaint | marks-appeal
  const [subject, setSubject] = useState(SUBJECTS[0]);
  const [message, setMessage] = useState("");
  const [attachmentName, setAttachmentName] = useState("");
  const [sending, setSending] = useState(false);

  const handleFile = (e) => {
    const f = e.target.files[0];
    if (f) setAttachmentName(f.name);
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setSending(true);

    const user = JSON.parse(localStorage.getItem("user") || "{}");
    const payload = {
      id: "appeal-" + Date.now(),
      type,
      subject: type === "marks-appeal" ? subject : null,
      message,
      studentName: user?.name || "Unknown",
      studentReg: user?.regNo || "Unknown",
      status: "Pending",
      createdAt: new Date().toISOString(),
      attachmentName,
    };

    // Try to send to backend (replace URL when backend ready)
    try {
      await fetch("http://localhost:8000/api/appeals", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });
      // on success push to localStorage as well
    } catch (err) {
      // fallback: save locally
      const stored = JSON.parse(localStorage.getItem("appeals") || "[]");
      stored.unshift(payload);
      localStorage.setItem("appeals", JSON.stringify(stored));
    }

    setMessage("");
    setAttachmentName("");
    setSending(false);
    alert("Your appeal has been submitted (demo). Status: Pending.");
    onSubmitted?.();
  };

  return (
    <form className="space-y-4" onSubmit={handleSubmit}>
      <div>
        <label className="text-sm text-[var(--muted)]">Type</label>
        <select value={type} onChange={(e) => setType(e.target.value)}
          className="mt-1 w-full bg-[#071828] border border-[#122236] rounded-lg p-3 text-white">
          <option value="complaint">Complaint / Feedback</option>
          <option value="marks-appeal">Marks Appeal</option>
        </select>
      </div>

      {type === "marks-appeal" && (
        <div>
          <label className="text-sm text-[var(--muted)]">Subject</label>
          <select value={subject} onChange={(e) => setSubject(e.target.value)}
            className="mt-1 w-full bg-[#071828] border border-[#122236] rounded-lg p-3 text-white">
            {SUBJECTS.map((s) => <option key={s} value={s}>{s}</option>)}
          </select>
        </div>
      )}

      <div>
        <label className="text-sm text-[var(--muted)]">Message</label>
        <textarea value={message} onChange={(e) => setMessage(e.target.value)}
          placeholder={type === "marks-appeal" ? "Explain why you think the mark is incorrect..." : "Describe the issue..."}
          className="mt-1 w-full bg-[#071828] border border-[#122236] rounded-lg p-3 text-white h-32" required />
      </div>

      <div>
        <label className="text-sm text-[var(--muted)]">Attach file (optional)</label>
        <input type="file" onChange={handleFile} className="mt-1 w-full text-sm text-gray-300" />
        {attachmentName && <div className="text-xs text-[var(--muted)] mt-1">Selected: {attachmentName}</div>}
      </div>

      <div className="flex gap-3">
        <button type="submit" disabled={sending}
          className="px-4 py-2 rounded-md bg-gradient-to-r from-[var(--accent-from)] to-[var(--accent-to)] hover:opacity-95 transition">
          {sending ? "Submitting..." : "Submit Appeal"}
        </button>

        <button type="button" onClick={() => { setMessage(""); setAttachmentName(""); }}
          className="px-4 py-2 rounded-md bg-[#1b2b3a]">
          Reset
        </button>
      </div>
    </form>
  );
}
