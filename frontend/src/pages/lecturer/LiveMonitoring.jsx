
import React, { useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import axios from "axios";

const API_BASE = "http://127.0.0.1:8000/api/ai-engine";

export default function LiveMonitoring() {

  const navigate = useNavigate();

  const [selectedMode, setSelectedMode] = useState(null);

  const [isRunning, setIsRunning] = useState(false);

  const [loading, setLoading] = useState(false);

  const [streamUrl, setStreamUrl] = useState(null);

  const [streamStatus, setStreamStatus] = useState("inactive");

  const [streamError, setStreamError] = useState("");

  // =====================================
  // START AI CAMERA
  // =====================================

  const startSession = async (mode) => {

    if (!mode || loading) return;

    try {

      setLoading(true);

      setStreamStatus("connecting");

      setStreamError("");

      setStreamUrl(null);

      console.log("Starting AI Camera:", mode);

      const response = await axios.post(
        `${API_BASE}/start-camera`,
        { mode },
        { timeout: 30000 }
      );

      console.log("Start Camera Response:", response.data);

      if (response.data.status === "success") {

        setSelectedMode(mode);

        // Generate a unique URL to avoid cached streams
        const newStreamUrl =
          `${API_BASE}/video-feed?t=${Date.now()}`;

        setStreamUrl(newStreamUrl);

        setIsRunning(true);

        setStreamStatus("connecting");

      } else {

        throw new Error(
          response.data.message || "Camera failed to start"
        );

      }

    } catch (err) {

      console.error("Camera Start Error:", err);

      const message =
        err.response?.data?.detail ||
        err.message ||
        "Unable to start AI camera";

      setStreamError(message);

      setStreamStatus("error");

      setIsRunning(false);

      alert("Camera Error: " + message);

    } finally {

      setLoading(false);

    }

  };

  // =====================================
  // STOP AI CAMERA
  // =====================================

  const stopSession = async () => {

    try {

      setLoading(true);

      const response = await axios.post(
        `${API_BASE}/stop-camera`,
        {},
        { timeout: 60000 }
      );

      console.log("Stop Camera Response:", response.data);

      setIsRunning(false);

      setSelectedMode(null);

      setStreamUrl(null);

      setStreamStatus("inactive");

      setStreamError("");

      alert(
        response.data.message ||
        "AI session stopped"
      );

    } catch (err) {

      console.error("Camera Stop Error:", err);

      alert(
        err.response?.data?.detail ||
        "Failed to stop camera session"
      );

    } finally {

      setLoading(false);

    }

  };

  // =====================================
  // CLEANUP WHEN LEAVING PAGE
  // =====================================

  useEffect(() => {

    return () => {

      // Stop displaying the browser stream.
      // The backend session should be stopped explicitly
      // using the Terminate button.

      setStreamUrl(null);

    };

  }, []);

  // =====================================
  // VIDEO STREAM LOADED
  // =====================================

  const handleStreamLoad = () => {

    console.log("Video stream connected");

    setStreamStatus("connected");

    setStreamError("");

  };

  // =====================================
  // VIDEO STREAM ERROR
  // =====================================

  const handleStreamError = () => {

    console.error("Video stream failed");

    setStreamStatus("error");

    setStreamError(
      "Unable to receive camera frames. Check the backend video-feed endpoint."
    );

  };

  return (

    <div className="min-h-screen bg-[#071828] text-white p-6 flex flex-col justify-between">

      {/* HEADER */}

      <header className="flex justify-between items-center bg-[#091d30] border border-white/10 p-5 rounded-2xl">

        <div>

          <div className="flex items-center gap-2">

            <span className="w-3 h-3 rounded-full bg-blue-500 animate-pulse"></span>

            <span className="text-xs uppercase tracking-widest text-blue-400 font-bold">
              Student360 Vision Console
            </span>

          </div>

          <h1 className="text-2xl font-bold mt-1">
            Live Surveillance & AI Analytics Console
          </h1>

        </div>

        <button
          onClick={() => navigate("/lecturer/dashboard")}
          className="px-5 py-2.5 bg-gray-800 hover:bg-gray-700 border border-white/10 rounded-xl text-sm font-semibold transition"
        >
          ← Return to Dashboard
        </button>

      </header>

      {/* MAIN CONTENT */}

      <div className="my-6 grid grid-cols-1 lg:grid-cols-3 gap-6 flex-1">

        {/* LEFT CONTROL PANEL */}

        <div className="bg-[#0b2236] border border-white/10 rounded-2xl p-6 flex flex-col justify-between">

          <div>

            <h2 className="text-lg font-bold text-gray-200 mb-1">
              Session Configuration
            </h2>

            <p className="text-xs text-gray-400 mb-6">
              Select appropriate monitoring preset before starting feed.
            </p>

            <div className="space-y-4">

              {/* CLASSROOM */}

              <div
                onClick={() =>
                  !isRunning &&
                  !loading &&
                  setSelectedMode("classroom")
                }
                className={`p-5 rounded-2xl border cursor-pointer transition-all ${
                  selectedMode === "classroom"
                    ? "bg-blue-600/20 border-blue-500 shadow-lg shadow-blue-500/20"
                    : "bg-[#071828] border-white/10 hover:border-blue-400/50"
                } ${
                  isRunning && selectedMode !== "classroom"
                    ? "opacity-40 cursor-not-allowed"
                    : ""
                }`}
              >

                <div className="text-2xl mb-2">🎓</div>

                <h3 className="font-bold text-base text-white">
                  Smart Classroom Preset
                </h3>

                <p className="text-xs text-gray-400 mt-1 leading-relaxed">
                  Focuses on lecture engagement: detects sleeping,
                  phone usage, attentiveness, and automated attendance.
                </p>

              </div>

              {/* EXAM */}

              <div
                onClick={() =>
                  !isRunning &&
                  !loading &&
                  setSelectedMode("exam")
                }
                className={`p-5 rounded-2xl border cursor-pointer transition-all ${
                  selectedMode === "exam"
                    ? "bg-purple-600/20 border-purple-500 shadow-lg shadow-purple-500/20"
                    : "bg-[#071828] border-white/10 hover:border-purple-400/50"
                } ${
                  isRunning && selectedMode !== "exam"
                    ? "opacity-40 cursor-not-allowed"
                    : ""
                }`}
              >

                <div className="text-2xl mb-2">🛡️</div>

                <h3 className="font-bold text-base text-white">
                  Exam Proctor Preset
                </h3>

                <p className="text-xs text-gray-400 mt-1 leading-relaxed">
                  Strict invigilation: flags suspicious head movement,
                  turning around, passing items, and malpractice cues.
                </p>

              </div>

            </div>

          </div>

          {/* START / STOP */}

          <div className="pt-6 border-t border-white/10">

            {!isRunning ? (

              <button
                onClick={() => startSession(selectedMode)}
                disabled={!selectedMode || loading}
                className="w-full py-4 bg-gradient-to-r from-blue-600 to-indigo-600 hover:from-blue-500 hover:to-indigo-500 disabled:opacity-40 disabled:cursor-not-allowed rounded-xl font-bold uppercase tracking-wider text-sm shadow-xl transition-all"
              >
                {loading
                  ? "Initializing..."
                  : "Launch AI Camera Feed"}
              </button>

            ) : (

              <button
                onClick={stopSession}
                disabled={loading}
                className="w-full py-4 bg-red-600 hover:bg-red-700 disabled:opacity-50 rounded-xl font-bold uppercase tracking-wider text-sm shadow-xl transition-all"
              >
                {loading
                  ? "Terminating..."
                  : "Terminate & Export Log"}
              </button>

            )}

          </div>

        </div>

        {/* RIGHT VIDEO PANEL */}

        <div className="lg:col-span-2 bg-[#091d30] border border-white/10 rounded-2xl p-4 flex flex-col">

          <div className="flex justify-between items-center mb-3">

            <span className="text-xs font-bold uppercase text-gray-400 flex items-center gap-2">

              <span
                className={`w-2.5 h-2.5 rounded-full ${
                  streamStatus === "connected"
                    ? "bg-green-500 animate-pulse"
                    : streamStatus === "error"
                    ? "bg-red-500"
                    : "bg-gray-500"
                }`}
              ></span>

              Surveillance Stream Output

            </span>

            {streamStatus === "connected" && (

              <span className="px-3 py-1 bg-green-500/20 text-green-400 text-xs font-mono font-bold rounded-lg border border-green-500/30">
                ● LIVE INFERENCE RUNNING
              </span>

            )}

            {streamStatus === "connecting" && (

              <span className="px-3 py-1 bg-yellow-500/20 text-yellow-400 text-xs font-mono rounded-lg">
                CONNECTING...
              </span>

            )}

            {streamStatus === "error" && (

              <span className="px-3 py-1 bg-red-500/20 text-red-400 text-xs font-mono rounded-lg">
                STREAM ERROR
              </span>

            )}

          </div>

          {/* VIDEO DISPLAY */}

          <div className="flex-1 bg-black rounded-xl border border-white/10 flex items-center justify-center overflow-hidden min-h-[420px] relative">

            {streamUrl && streamStatus !== "error" ? (

              <img
                key={streamUrl}
                src={streamUrl}
                alt="Student360 AI Detection Feed"
                onLoad={handleStreamLoad}
                onError={handleStreamError}
                className="absolute inset-0 w-full h-full object-contain"
              />

            ) : (

              <div className="text-center p-8">

                <div className="text-5xl mb-4 opacity-50">
                  {streamStatus === "error" ? "⚠️" : "📹"}
                </div>

                <h3 className="text-lg font-bold text-gray-300">

                  {streamStatus === "error"
                    ? "Camera Stream Failed"
                    : streamStatus === "connecting"
                    ? "Connecting to Camera..."
                    : "Camera Feed Inactive"}

                </h3>

                <p className="text-xs text-gray-500 mt-2 max-w-sm mx-auto">
                  {streamError ||
                    "Select a preset and launch the AI camera feed."}
                </p>

              </div>

            )}

          </div>

        </div>

      </div>

    </div>

  );

}