import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { submitAppeal } from "../../api/api";

export default function Appeals() {
  const navigate = useNavigate();

  const [message, setMessage] = useState("");
  const [type, setType] = useState("Behavior");
  const [loading, setLoading] = useState(false);

  const submit = async () => {
    if (!message.trim()) {
      alert("Please enter appeal message");
      return;
    }

    try {
      setLoading(true);
      const user = JSON.parse(localStorage.getItem("user")) || {};

      // Student ID එක හරියටම ගන්නවා (Fallback එක්ක)
      const studentId = user.student_id || user.id || user.username || "";

      if (!studentId) {
        alert("Student ID not found. Please log in again.");
        return;
      }

      await submitAppeal({
        student_id: studentId,
        message: message,
        type: type,
      });

      alert("Appeal Submitted Successfully");
      setMessage("");

      // Submit වුණ ගමන් auto Dashboard එකට Redirect වෙනවා
      navigate("/student/dashboard");
    } catch (err) {
      console.error("Error submitting appeal:", err);
      alert("Error submitting appeal. Please try again.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="p-8 text-white max-w-4xl mx-auto">
      <h1 className="text-2xl font-bold mb-4">
        Submit Appeal
      </h1>

      <div className="bg-[#0b2236] p-6 rounded-xl border border-white/10">
        <label className="block mb-2 text-sm text-gray-300">Appeal Type</label>

        <select
          className="w-full bg-[#071828] border border-white/10 p-3 rounded-xl mt-1 mb-4 text-white outline-none focus:border-blue-500"
          value={type}
          onChange={(e) => setType(e.target.value)}
        >
          <option value="Behavior">Behavior</option>
          <option value="Attendance">Attendance</option>
          <option value="Exam">Exam</option>
        </select>

        <label className="block mb-2 text-sm text-gray-300">Appeal Message</label>

        <textarea
          className="w-full bg-[#071828] border border-white/10 p-3 rounded-xl text-white outline-none focus:border-blue-500"
          rows="6"
          placeholder="Write your appeal..."
          value={message}
          onChange={(e) => setMessage(e.target.value)}
        />

        <div className="flex gap-4 mt-6">
          <button
            onClick={submit}
            disabled={loading}
            className="bg-blue-600 hover:bg-blue-700 disabled:opacity-50 px-6 py-3 rounded-xl font-semibold transition"
          >
            {loading ? "Submitting..." : "Submit Appeal"}
          </button>

          <button
            onClick={() => navigate("/student/dashboard")}
            disabled={loading}
            className="bg-white/5 hover:bg-white/10 px-6 py-3 rounded-xl transition text-gray-300"
          >
            Cancel
          </button>
        </div>
      </div>
    </div>
  );
}