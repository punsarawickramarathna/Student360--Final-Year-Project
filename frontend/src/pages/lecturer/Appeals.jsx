import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import Navbar from "../../components/Navbar";
import { getAppeals } from "../../api/api";

export default function Appeals() {
  const navigate = useNavigate();
  const [appeals, setAppeals] = useState([]);
  const [loading, setLoading] = useState(true);

  // Load appeals when page opens
  useEffect(() => {
    async function load() {
      try {
        setLoading(true);
        const data = await getAppeals();

        if (Array.isArray(data)) {
          setAppeals(data);
        } else if (data?.data && Array.isArray(data.data)) {
          setAppeals(data.data);
        } else {
          setAppeals([]);
        }
      } catch (err) {
        console.error("Error loading appeals:", err);
        setAppeals([]);
      } finally {
        setLoading(false);
      }
    }

    load();
  }, []);

  // Stats calculate කිරීම
  const totalAppeals = appeals?.length || 0;
  const pendingAppeals = appeals?.filter((a) => a?.status === "Pending").length || 0;

  return (
    <div className="min-h-screen bg-[#020817] text-white">
      {/* Top Navbar */}
      <Navbar />

      <div className="max-w-5xl mx-auto p-4 sm:p-8">
        
        {/* Navigation Header (Lecturer Dashboard එකට විතරක් Back වෙන විදිහට) */}
        <div className="mb-6 flex items-center justify-between">
          <button
            onClick={() => navigate("/lecturer/dashboard")}
            className="text-sm text-gray-400 hover:text-white flex items-center gap-2 transition"
          >
            ← Back to Dashboard
          </button>

          <span className="text-xs bg-blue-500/10 border border-blue-500/20 text-blue-400 px-3.5 py-1.5 rounded-full font-medium">
            Lecturer Review Portal
          </span>
        </div>

        {/* Title & Stats Summary Card */}
        <div className="bg-[#0b2236] border border-white/10 rounded-2xl p-6 mb-8 shadow-xl backdrop-blur-xl flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4">
          <div>
            <h1 className="text-3xl font-bold text-white flex items-center gap-3">
              📩 Student Appeals
            </h1>
            <p className="text-gray-400 text-sm mt-1">
              Review and manage academic complaints and re-evaluation requests submitted by students.
            </p>
          </div>

          {/* Quick Counter Chips */}
          <div className="flex items-center gap-3 w-full sm:w-auto">
            <div className="bg-[#071828] border border-white/10 px-4 py-2 rounded-xl text-center flex-1 sm:flex-none">
              <span className="text-xs text-gray-400 block">Total</span>
              <span className="text-lg font-bold text-blue-400">{totalAppeals}</span>
            </div>
            <div className="bg-[#071828] border border-white/10 px-4 py-2 rounded-xl text-center flex-1 sm:flex-none">
              <span className="text-xs text-gray-400 block">Pending</span>
              <span className="text-lg font-bold text-yellow-400">{pendingAppeals}</span>
            </div>
          </div>
        </div>

        {/* Content Body */}
        {loading ? (
          <div className="bg-[#0b2236] border border-white/10 p-8 rounded-2xl text-center text-gray-400 flex items-center justify-center gap-3">
            <span className="w-5 h-5 border-2 border-blue-400 border-t-transparent rounded-full animate-spin" />
            Loading submitted appeals...
          </div>
        ) : !appeals || appeals.length === 0 ? (
          <div className="bg-[#0b2236] border border-white/10 p-8 rounded-2xl text-center text-gray-400">
            🍃 No student appeals submitted yet.
          </div>
        ) : (
          <div className="space-y-4">
            {appeals.map((appeal, index) => (
              <div
                key={appeal?._id || appeal?.id || index}
                className="bg-[#0b2236] border border-white/10 hover:border-blue-500/30 rounded-2xl p-6 shadow-lg transition"
              >
                <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 border-b border-white/5 pb-4 mb-4">
                  <div>
                    <h2 className="text-lg font-semibold text-blue-400 flex items-center gap-2">
                      👤 Student ID: {appeal?.student_id || "N/A"}
                    </h2>
                    <p className="text-sm text-gray-400 mt-0.5">
                      <strong>Category:</strong> {appeal?.type || "N/A"}
                    </p>
                  </div>

                  {/* Status Badge */}
                  <div>
                    <span
                      className={`inline-block px-3.5 py-1 rounded-full text-xs font-semibold ${
                        appeal?.status === "Pending"
                          ? "bg-yellow-500/10 border border-yellow-500/30 text-yellow-400"
                          : "bg-green-500/10 border border-green-500/30 text-green-400"
                      }`}
                    >
                      {appeal?.status || "Pending"}
                    </span>
                  </div>
                </div>

                {/* Message Body */}
                <div>
                  <p className="text-xs font-medium text-gray-400 uppercase tracking-wider mb-1">
                    Appeal Description
                  </p>
                  <div className="bg-[#071828] border border-white/5 p-4 rounded-xl text-gray-200 text-sm leading-relaxed">
                    {appeal?.message || "No message provided"}
                  </div>
                </div>

                {/* Attachment & Timestamp Footer */}
                <div className="mt-4 pt-3 border-t border-white/5 flex flex-col sm:flex-row items-start sm:items-center justify-between gap-2 text-xs text-gray-400">
                  <div>
                    {appeal?.attachment_name ? (
                      <span className="text-blue-400 flex items-center gap-1 font-medium">
                        📎 Attachment: {appeal.attachment_name}
                      </span>
                    ) : (
                      <span className="text-gray-500">No attachments included</span>
                    )}
                  </div>

                  <div>
                    Submitted on:{" "}
                    {appeal?.created_at
                      ? new Date(appeal.created_at).toLocaleString()
                      : "N/A"}
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}

      </div>
    </div>
  );
}