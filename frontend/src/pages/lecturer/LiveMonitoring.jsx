import React, { useState } from "react";
import { useNavigate } from "react-router-dom";
import axios from "axios";

export default function LiveMonitoring() {
  const navigate = useNavigate();
  const [selectedMode, setSelectedMode] = useState(null);
  const [isRunning, setIsRunning] = useState(false);
  const [loading, setLoading] = useState(false);

  const startSession = async (mode) => {
    try {
      setLoading(true);
      await axios.post("http://localhost:8000/api/ai-engine/start-camera", { mode });
      setSelectedMode(mode);
      setIsRunning(true);
    } catch (err) {
      alert("Backend AI Engine connect karanna bari wuna!");
    } finally {
      setLoading(false);
    }
  };

  const stopSession = async () => {
    try {
      setLoading(true);
      await axios.post("http://localhost:8000/api/ai-engine/stop-camera");
      setIsRunning(false);
      setSelectedMode(null);
      alert("Session completed! Attendance & Behavior log exported.");
    } catch (err) {
      alert("Failed to stop camera session");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-[#071828] text-white p-6 flex flex-col justify-between">
      {/* Top Header */}
      <header className="flex justify-between items-center bg-[#091d30] border border-white/10 p-5 rounded-2xl">
        <div>
          <div className="flex items-center gap-2">
            <span className="w-3 h-3 rounded-full bg-blue-500 animate-pulse"></span>
            <span className="text-xs uppercase tracking-widest text-blue-400 font-bold">Student360 Vision Console</span>
          </div>
          <h1 className="text-2xl font-bold mt-1">Live Surveillance & AI Analytics Console</h1>
        </div>

        <button
          onClick={() => navigate("/lecturer/dashboard")}
          className="px-5 py-2.5 bg-gray-800 hover:bg-gray-700 border border-white/10 rounded-xl text-sm font-semibold transition"
        >
          ← Return to Dashboard
        </button>
      </header>

      {/* Main Content Area */}
      <div className="my-6 grid grid-cols-1 lg:grid-cols-3 gap-6 flex-1">
        
        {/* Left Control Panel: Mode Selection */}
        <div className="bg-[#0b2236] border border-white/10 rounded-2xl p-6 flex flex-col justify-between">
          <div>
            <h2 className="text-lg font-bold text-gray-200 mb-1">Session Configuration</h2>
            <p className="text-xs text-gray-400 mb-6">Select appropriate monitoring preset before starting feed.</p>

            <div className="space-y-4">
              {/* Classroom Mode Card */}
              <div
                onClick={() => !isRunning && setSelectedMode("classroom")}
                className={`p-5 rounded-2xl border cursor-pointer transition-all ${
                  selectedMode === "classroom"
                    ? "bg-blue-600/20 border-blue-500 shadow-lg shadow-blue-500/20"
                    : "bg-[#071828] border-white/10 hover:border-blue-400/50"
                } ${isRunning && selectedMode !== "classroom" ? "opacity-40 cursor-not-allowed" : ""}`}
              >
                <div className="text-2xl mb-2">🎓</div>
                <h3 className="font-bold text-base text-white">Smart Classroom Preset</h3>
                <p className="text-xs text-gray-400 mt-1 leading-relaxed">
                  Focuses on lecture engagement: detects sleeping, phone usage, attentiveness, and automated attendance.
                </p>
              </div>

              {/* Exam Hall Mode Card */}
              <div
                onClick={() => !isRunning && setSelectedMode("exam")}
                className={`p-5 rounded-2xl border cursor-pointer transition-all ${
                  selectedMode === "exam"
                    ? "bg-purple-600/20 border-purple-500 shadow-lg shadow-purple-500/20"
                    : "bg-[#071828] border-white/10 hover:border-purple-400/50"
                } ${isRunning && selectedMode !== "exam" ? "opacity-40 cursor-not-allowed" : ""}`}
              >
                <div className="text-2xl mb-2">🛡️</div>
                <h3 className="font-bold text-base text-white">Exam Proctor Preset</h3>
                <p className="text-xs text-gray-400 mt-1 leading-relaxed">
                  Strict invigilation: flags suspicious head movement, turning around, passing items, and malpractice cues.
                </p>
              </div>
            </div>
          </div>

          {/* Action Trigger Buttons */}
          <div className="pt-6 border-t border-white/10">
            {!isRunning ? (
              <button
                onClick={() => startSession(selectedMode)}
                disabled={!selectedMode || loading}
                className="w-full py-4 bg-gradient-to-r from-blue-600 to-indigo-600 hover:from-blue-500 hover:to-indigo-500 disabled:opacity-40 disabled:cursor-not-allowed rounded-xl font-bold uppercase tracking-wider text-sm shadow-xl transition-all"
              >
                {loading ? "Initializing..." : "Launch AI Camera Feed"}
              </button>
            ) : (
              <button
                onClick={stopSession}
                disabled={loading}
                className="w-full py-4 bg-red-600 hover:bg-red-700 rounded-xl font-bold uppercase tracking-wider text-sm shadow-xl transition-all animate-pulse"
              >
                {loading ? "Terminating..." : "Terminate & Export Log"}
              </button>
            )}
          </div>
        </div>

        {/* Right Video Preview Screen */}
        <div className="lg:col-span-2 bg-[#091d30] border border-white/10 rounded-2xl p-4 flex flex-col justify-between">
          <div className="flex justify-between items-center mb-3">
            <span className="text-xs font-bold uppercase text-gray-400 flex items-center gap-2">
              <span className={`w-2.5 h-2.5 rounded-full ${isRunning ? "bg-green-500 animate-ping" : "bg-gray-500"}`}></span>
              Surveillance Stream Output
            </span>
            {isRunning && (
              <span className="px-3 py-1 bg-green-500/20 text-green-400 text-xs font-mono font-bold rounded-lg border border-green-500/30">
                ● LIVE INFERENCE RUNNING
              </span>
            )}
          </div>

          {/* Video Stream Container */}
          <div className="flex-1 bg-black/80 rounded-xl border border-white/10 flex items-center justify-center overflow-hidden min-h-[420px] relative">
            {isRunning ? (
              <img
                src="http://localhost:8000/api/ai-engine/video-feed"
                alt="AI Detection Feed"
                className="w-full h-full object-cover rounded-xl"
              />
            ) : (
              <div className="text-center p-8">
                <div className="text-5xl mb-4 opacity-50">📹</div>
                <h3 className="text-lg font-bold text-gray-300">Camera Feed Inactive</h3>
                <p className="text-xs text-gray-500 mt-1 max-w-sm mx-auto">
                  Select a preset on the left and click 'Launch AI Camera Feed' to view live student detection.
                </p>
              </div>
            )}
          </div>
        </div>

      </div>
    </div>
  );
}