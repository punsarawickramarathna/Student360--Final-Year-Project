import React, { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import Navbar from "../../components/Navbar";
import { getAppeals } from "../../api/api";

export default function AppealsList() {
  const navigate = useNavigate();
  const [appeals, setAppeals] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  const fetchUserAppeals = async () => {
    try {
      setLoading(true);
      setError("");

      const user = JSON.parse(localStorage.getItem("user") || "{}");
      const currentStudentId = String(
        user?.student_id || user?.id || user?.username || ""
      ).trim().toLowerCase();

      // Backend API call එක හරහා appeals ලබා ගැනීම
      const response = await getAppeals();
      
      // Backend response handler (Array vs Object extract)
      let allAppeals = [];
      if (Array.isArray(response)) {
        allAppeals = response;
      } else if (Array.isArray(response?.data)) {
        allAppeals = response.data;
      }

      // ලොග් වුණු student ට අදාළ appeals පමණක් filter කිරීම
      const myAppeals = allAppeals.filter((a) => {
        const appealStudentId = String(
          a?.student_id || a?.studentId || a?.studentReg || ""
        ).trim().toLowerCase();
        
        return appealStudentId === currentStudentId;
      });

      setAppeals(myAppeals);
    } catch (err) {
      console.error("Failed to fetch appeals:", err);
      setError("Unable to load your appeals. Please check your network.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchUserAppeals();
  }, []);

  return (
    <div className="min-h-screen bg-[#020817] text-white">
      <Navbar />

      <div className="max-w-5xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        
        {/* Header Navigation */}
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 mb-8">
          <div>
            <button
              onClick={() => navigate("/student/dashboard")}
              className="text-xs text-gray-400 hover:text-white flex items-center gap-1 transition mb-2"
            >
              ← Back to Dashboard
            </button>
            <h1 className="text-3xl font-bold tracking-tight text-white">
              My Submitted Appeals
            </h1>
            <p className="text-gray-400 text-sm mt-1">
              Track the status of your submitted academic appeals and complaints.
            </p>
          </div>

          <button
            onClick={() => navigate("/student/appeal/new")}
            className="bg-blue-600 hover:bg-blue-700 text-white font-semibold px-5 py-2.5 rounded-xl transition shadow-lg flex items-center justify-center gap-2 self-start sm:self-auto"
          >
            + Submit New Appeal
          </button>
        </div>

        {/* Loading State */}
        {loading && (
          <div className="py-20 flex flex-col items-center justify-center text-center">
            <div className="w-10 h-10 border-4 border-gray-700 border-t-blue-500 rounded-full animate-spin" />
            <p className="text-gray-400 text-sm mt-4">Loading your appeals...</p>
          </div>
        )}

        {/* Error State */}
        {error && !loading && (
          <div className="bg-red-500/10 border border-red-500/30 text-red-300 rounded-2xl p-6 text-center">
            <p>{error}</p>
            <button
              onClick={fetchUserAppeals}
              className="mt-4 bg-red-600/20 border border-red-500/40 text-red-200 px-4 py-2 rounded-xl text-sm font-semibold hover:bg-red-600/30 transition"
            >
              Try Again
            </button>
          </div>
        )}

        {/* Empty State */}
        {!loading && !error && appeals.length === 0 && (
          <div className="bg-[#0b2236] border border-white/10 rounded-2xl p-12 text-center my-6">
            <div className="text-5xl mb-4">📨</div>
            <h3 className="text-lg font-semibold text-white">No Appeals Found</h3>
            <p className="text-gray-400 text-sm mt-1 max-w-md mx-auto">
              You haven't submitted any appeals yet. Click the button below if you need to submit one.
            </p>
            <button
              onClick={() => navigate("/student/appeal/new")}
              className="mt-6 bg-blue-600 hover:bg-blue-700 text-white font-semibold px-6 py-2.5 rounded-xl transition text-sm"
            >
              Submit Appeal Now
            </button>
          </div>
        )}

        {/* Appeals Cards List */}
        {!loading && !error && appeals.length > 0 && (
          <div className="space-y-4">
            {appeals.map((a, index) => {
              const status = a?.status || "Pending";
              let statusStyle = "bg-yellow-500/15 text-yellow-400 border-yellow-500/30";
              if (status.toLowerCase() === "approved" || status.toLowerCase() === "accepted") {
                statusStyle = "bg-green-500/15 text-green-400 border-green-500/30";
              } else if (status.toLowerCase() === "rejected" || status.toLowerCase() === "declined") {
                statusStyle = "bg-red-500/15 text-red-400 border-red-500/30";
              }

              return (
                <div
                  key={a?._id || index}
                  className="bg-[#0b2236] border border-white/10 hover:border-white/20 rounded-2xl p-6 transition shadow-xl"
                >
                  <div className="flex flex-col sm:flex-row sm:items-start justify-between gap-4">
                    
                    <div className="space-y-2 flex-1">
                      <div className="flex flex-wrap items-center gap-2">
                        <span className="text-xs font-semibold text-blue-400 uppercase tracking-wider bg-blue-500/10 border border-blue-500/20 px-2.5 py-1 rounded-md">
                          {a?.type || "Student Appeal"}
                        </span>
                        
                        {a?.created_at && (
                          <span className="text-xs text-gray-400">
                            • {new Date(a.created_at).toLocaleDateString()} at {new Date(a.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                          </span>
                        )}
                      </div>

                      <p className="text-gray-200 text-sm leading-relaxed pt-1">
                        {a?.message || "No message provided."}
                      </p>

                      {a?.attachment_name && (
                        <div className="text-xs text-gray-400 flex items-center gap-1 pt-1">
                          📎 Attachment: <span className="text-gray-300 font-medium">{a.attachment_name}</span>
                        </div>
                      )}
                    </div>

                    {/* Status Badge */}
                    <div className="self-start sm:self-auto">
                      <span className={`inline-flex px-3.5 py-1.5 rounded-full text-xs font-semibold border ${statusStyle}`}>
                        {status}
                      </span>
                    </div>

                  </div>
                </div>
              );
            })}
          </div>
        )}

      </div>
    </div>
  );
}