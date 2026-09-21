import React, { useState } from "react";
import { useNavigate } from "react-router-dom";
import Navbar from "../../components/Navbar";
import { submitAppeal } from "../../api/api";

const SUBJECTS = [
  "Algorithms",
  "Operating Systems",
  "Database Systems",
  "Computer Networks",
  "Software Engineering",
];

export default function AppealForm({ onSubmitted }) {
  const navigate = useNavigate();

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

    if (!message.trim()) {
      alert("Please enter a message for your appeal.");
      return;
    }

    setSending(true);

    try {
      const user = JSON.parse(localStorage.getItem("user") || "{}");
      
      // Student ID එක නිවැරදිව Fallback සහිතව ලබා ගැනීම
      const studentId = user?.student_id || user?.id || user?.username || "";

      if (!studentId) {
        alert("Student ID missing. Please log in again.");
        setSending(false);
        return;
      }

      // Backend API call හරහා appeal එක submit කිරීම
      await submitAppeal({
        student_id: studentId,
        type: type === "marks-appeal" ? `Marks Appeal - ${subject}` : "Complaint / Feedback",
        message: message,
        attachment_name: attachmentName || null,
      });

      alert("Your appeal has been submitted successfully!");

      // Form reset කිරීම
      setMessage("");
      setAttachmentName("");

      // Callback තිබේ නම් එය run කර Dashboard එකට Navigate කිරීම
      if (onSubmitted) {
        onSubmitted();
      } else {
        navigate("/student/dashboard");
      }
    } catch (err) {
      console.error("Submission error:", err);
      alert("Failed to submit appeal to server. Please try again.");
    } finally {
      setSending(false);
    }
  };

  return (
    <div className="min-h-screen bg-[#020817] text-white">
      <Navbar />

      <div className="max-w-3xl mx-auto p-4 sm:p-8">
        
        {/* Back Button & Header */}
        <div className="mb-6 flex items-center justify-between">
          <button
            onClick={() => navigate("/student/dashboard")}
            className="text-sm text-gray-400 hover:text-white flex items-center gap-2 transition"
          >
            ← Back to Dashboard
          </button>
          
          <span className="text-xs bg-blue-500/10 border border-blue-500/20 text-blue-400 px-3 py-1 rounded-full font-medium">
            Student Support Portal
          </span>
        </div>

        {/* Form Card */}
        <div className="bg-[#0b2236] border border-white/10 rounded-2xl p-6 sm:p-8 shadow-2xl backdrop-blur-xl">
          
          <div className="mb-6 border-b border-white/10 pb-4">
            <h1 className="text-2xl font-bold text-white flex items-center gap-2">
              📝 Submit New Appeal
            </h1>
            <p className="text-gray-400 text-sm mt-1">
              Submit your academic complaints or marks re-evaluation requests directly to the faculty.
            </p>
          </div>

          <form className="space-y-6" onSubmit={handleSubmit}>
            
            {/* Appeal Type */}
            <div>
              <label className="block text-sm font-medium text-gray-300 mb-2">
                Appeal Type
              </label>
              <select
                value={type}
                onChange={(e) => setType(e.target.value)}
                className="w-full bg-[#071828] border border-white/10 rounded-xl p-3.5 text-white outline-none focus:border-blue-500 transition"
              >
                <option value="complaint">Complaint / Feedback</option>
                <option value="marks-appeal">Marks Appeal</option>
              </select>
            </div>

            {/* Subject Dropdown (Conditional) */}
            {type === "marks-appeal" && (
              <div className="animate-fadeIn">
                <label className="block text-sm font-medium text-gray-300 mb-2">
                  Select Subject
                </label>
                <select
                  value={subject}
                  onChange={(e) => setSubject(e.target.value)}
                  className="w-full bg-[#071828] border border-white/10 rounded-xl p-3.5 text-white outline-none focus:border-blue-500 transition"
                >
                  {SUBJECTS.map((s) => (
                    <option key={s} value={s}>
                      {s}
                    </option>
                  ))}
                </select>
              </div>
            )}

            {/* Message Area */}
            <div>
              <label className="block text-sm font-medium text-gray-300 mb-2">
                Appeal Message / Description
              </label>
              <textarea
                value={message}
                onChange={(e) => setMessage(e.target.value)}
                placeholder={
                  type === "marks-appeal"
                    ? "Explain why you think the mark is incorrect or need re-checking..."
                    : "Describe your issue or feedback in detail..."
                }
                className="w-full bg-[#071828] border border-white/10 rounded-xl p-3.5 text-white outline-none focus:border-blue-500 transition h-36 resize-none"
                required
              />
            </div>

            {/* File Upload */}
            <div>
              <label className="block text-sm font-medium text-gray-300 mb-2">
                Attach File / Proof (Optional)
              </label>
              <div className="relative border border-dashed border-white/20 hover:border-blue-500/50 bg-[#071828] rounded-xl p-4 transition">
                <input
                  type="file"
                  onChange={handleFile}
                  className="absolute inset-0 w-full h-full opacity-0 cursor-pointer"
                />
                <div className="text-center text-sm text-gray-400">
                  {attachmentName ? (
                    <span className="text-blue-400 font-medium">
                      📎 Selected: {attachmentName}
                    </span>
                  ) : (
                    <span>Click to browse or drag and drop files here</span>
                  )}
                </div>
              </div>
            </div>

            {/* Actions */}
            <div className="flex items-center gap-4 pt-2">
              <button
                type="submit"
                disabled={sending}
                className="flex-1 bg-gradient-to-r from-blue-600 to-purple-600 hover:from-blue-700 hover:to-purple-700 disabled:opacity-50 font-semibold py-3.5 px-6 rounded-xl transition text-white shadow-lg flex items-center justify-center gap-2"
              >
                {sending && (
                  <span className="w-5 h-5 border-2 border-white/40 border-t-white rounded-full animate-spin" />
                )}
                {sending ? "Submitting Appeal..." : "Submit Appeal"}
              </button>

              <button
                type="button"
                onClick={() => {
                  setMessage("");
                  setAttachmentName("");
                }}
                disabled={sending}
                className="bg-white/5 hover:bg-white/10 text-gray-300 py-3.5 px-6 rounded-xl font-medium transition"
              >
                Reset
              </button>
            </div>

          </form>

        </div>

      </div>
    </div>
  );
}