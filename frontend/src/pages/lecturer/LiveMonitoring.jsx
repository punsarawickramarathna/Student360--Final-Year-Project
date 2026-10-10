
<<<<<<< Updated upstream
import React, { useState, useEffect } from "react";
=======
import React, { useEffect, useState, useRef } from "react";
>>>>>>> Stashed changes
import { useNavigate } from "react-router-dom";
import axios from "axios";

const API_BASE = "http://127.0.0.1:8000/api/ai-engine";

export default function LiveMonitoring() {

  const navigate = useNavigate();
  const fileInputRef = useRef(null);

  const [selectedMode, setSelectedMode] = useState(null);
<<<<<<< Updated upstream
=======
  const [inputSource, setInputSource] = useState("camera"); // 'camera' | 'demo' | 'custom_upload'
  const [uploadedVideoFile, setUploadedVideoFile] = useState(null);
>>>>>>> Stashed changes

  const [isRunning, setIsRunning] = useState(false);

  const [loading, setLoading] = useState(false);

  const [streamUrl, setStreamUrl] = useState(null);

  const [streamStatus, setStreamStatus] = useState("inactive");

  const [streamError, setStreamError] = useState("");

  const handleFileChange = (e) => {
    const file = e.target.files[0];
    if (file) {
      if (!file.type.startsWith("video/") && !file.name.match(/\.(mp4|avi|mov|mkv)$/i)) {
        alert("Please select a valid video file (.mp4, .avi, .mkv)");
        return;
      }
      setUploadedVideoFile(file);
    }
  };

  // =====================================
  // START AI CAMERA
  // =====================================

  const startSession = async (mode) => {

    if (!mode || loading) return;

    if (inputSource === "custom_upload" && !uploadedVideoFile) {
      alert("Please choose an MP4 video file from your PC first!");
      fileInputRef.current?.click();
      return;
    }

    try {

      setLoading(true);

      setStreamStatus("connecting");

      setStreamError("");

      setStreamUrl(null);

<<<<<<< Updated upstream
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
=======
      let response;

      if (inputSource === "custom_upload" && uploadedVideoFile) {
        // Upload custom PC video using FormData
        const formData = new FormData();
        formData.append("mode", selectedMode);
        formData.append("source_type", "demo");
        formData.append("video_file", uploadedVideoFile);

        response = await axios.post(`${API_BASE}/start-camera`, formData, {
          headers: { "Content-Type": "multipart/form-data" },
          timeout: 60000,
        });
      } else {
        // Normal JSON payload for webcam or preset demo
        response = await axios.post(
          `${API_BASE}/start-camera`,
          {
            mode: selectedMode,
            source_type: inputSource,
          },
          { timeout: 30000 }
>>>>>>> Stashed changes
        );

      }

<<<<<<< Updated upstream
    } catch (err) {

      console.error("Camera Start Error:", err);

      const message =
        err.response?.data?.detail ||
        err.message ||
        "Unable to start AI camera";
=======
      if (response.data.status !== "success") {
        throw new Error(response.data.message || "AI session failed to start");
      }

      const newStreamUrl = `${API_BASE}/video-feed?t=${Date.now()}`;
      setStreamUrl(newStreamUrl);
      setIsRunning(true);
      setStreamStatus("connecting");
    } catch (err) {
      console.error("AI Session Start Error:", err);
      const message =
        err.response?.data?.detail || err.message || "Unable to start AI session";
>>>>>>> Stashed changes

      setStreamError(message);

      setStreamStatus("error");

      setIsRunning(false);
<<<<<<< Updated upstream

      alert("Camera Error: " + message);

=======
      alert("AI Session Error: " + message);
>>>>>>> Stashed changes
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
<<<<<<< Updated upstream

      const response = await axios.post(
        `${API_BASE}/stop-camera`,
        {},
        { timeout: 60000 }
      );

      console.log("Stop Camera Response:", response.data);
=======
      const response = await axios.post(`${API_BASE}/stop-camera`, {}, { timeout: 60000 });
>>>>>>> Stashed changes

      setIsRunning(false);

      setSelectedMode(null);

      setStreamUrl(null);

      setStreamStatus("inactive");

      setStreamError("");
      setUploadedVideoFile(null);

<<<<<<< Updated upstream
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

=======
      alert(response.data.message || "AI session stopped");
    } catch (err) {
      console.error("AI Session Stop Error:", err);
      alert(err.response?.data?.detail || "Failed to stop AI session");
>>>>>>> Stashed changes
    } finally {

      setLoading(false);

    }

  };

<<<<<<< Updated upstream
  // =====================================
  // CLEANUP WHEN LEAVING PAGE
  // =====================================

=======
>>>>>>> Stashed changes
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
<<<<<<< Updated upstream

    console.log("Video stream connected");

=======
>>>>>>> Stashed changes
    setStreamStatus("connected");

    setStreamError("");

  };

  // =====================================
  // VIDEO STREAM ERROR
  // =====================================

  const handleStreamError = () => {
<<<<<<< Updated upstream

    console.error("Video stream failed");

    setStreamStatus("error");

    setStreamError(
      "Unable to receive camera frames. Check the backend video-feed endpoint."
    );

  };

=======
    setStreamStatus("error");
    setStreamError("Unable to receive AI frames. Check backend video-feed endpoint.");
  };

  const sourceTitle =
    inputSource === "camera"
      ? "Live Camera"
      : inputSource === "custom_upload"
      ? "Uploaded PC Video"
      : "Pre-recorded Demo Video";

  const launchText =
    inputSource === "camera"
      ? "Launch Live AI Camera"
      : inputSource === "custom_upload"
      ? `Launch Uploaded Video (${selectedMode === "exam" ? "Exam" : "Classroom"})`
      : selectedMode === "exam"
      ? "Launch Exam Demo Video"
      : "Launch Classroom Demo Video";

>>>>>>> Stashed changes
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
<<<<<<< Updated upstream

          <h1 className="text-2xl font-bold mt-1">
            Live Surveillance & AI Analytics Console
          </h1>

=======
          <h1 className="text-2xl font-bold mt-1">Live Surveillance & AI Analytics Console</h1>
>>>>>>> Stashed changes
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
<<<<<<< Updated upstream

        {/* LEFT CONTROL PANEL */}

=======
        {/* LEFT CONFIGURATION PANEL */}
>>>>>>> Stashed changes
        <div className="bg-[#0b2236] border border-white/10 rounded-2xl p-6 flex flex-col justify-between">
          <div>
            <h2 className="text-lg font-bold text-gray-200 mb-1">Session Configuration</h2>
            <p className="text-xs text-gray-400 mb-6">
<<<<<<< Updated upstream
              Select appropriate monitoring preset before starting feed.
=======
              Select monitoring preset and input source before starting AI inference.
>>>>>>> Stashed changes
            </p>

            <div className="space-y-4">
<<<<<<< Updated upstream

              {/* CLASSROOM */}

              <div
                onClick={() =>
                  !isRunning &&
                  !loading &&
                  setSelectedMode("classroom")
                }
=======
              {/* CLASSROOM PRESET */}
              <div
                onClick={() => {
                  if (!isRunning && !loading) setSelectedMode("classroom");
                }}
>>>>>>> Stashed changes
                className={`p-5 rounded-2xl border cursor-pointer transition-all ${
                  selectedMode === "classroom"
                    ? "bg-blue-600/20 border-blue-500 shadow-lg shadow-blue-500/20"
                    : "bg-[#071828] border-white/10 hover:border-blue-400/50"
<<<<<<< Updated upstream
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
=======
                } ${isRunning && selectedMode !== "classroom" ? "opacity-40 cursor-not-allowed" : ""}`}
              >
                <div className="text-2xl mb-2">🎓</div>
                <h3 className="font-bold text-base text-white">Smart Classroom Preset</h3>
                <p className="text-xs text-gray-400 mt-1 leading-relaxed">
                  Detects attentive, not-attentive, phone-use and sleeping behavior with automated student identity recognition.
>>>>>>> Stashed changes
                </p>
              </div>

<<<<<<< Updated upstream
              {/* EXAM */}

              <div
                onClick={() =>
                  !isRunning &&
                  !loading &&
                  setSelectedMode("exam")
                }
=======
              {/* EXAM PRESET */}
              <div
                onClick={() => {
                  if (!isRunning && !loading) setSelectedMode("exam");
                }}
>>>>>>> Stashed changes
                className={`p-5 rounded-2xl border cursor-pointer transition-all ${
                  selectedMode === "exam"
                    ? "bg-purple-600/20 border-purple-500 shadow-lg shadow-purple-500/20"
                    : "bg-[#071828] border-white/10 hover:border-purple-400/50"
<<<<<<< Updated upstream
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
=======
                } ${isRunning && selectedMode !== "exam" ? "opacity-40 cursor-not-allowed" : ""}`}
              >
                <div className="text-2xl mb-2">🛡️</div>
                <h3 className="font-bold text-base text-white">Exam Proctor Preset</h3>
                <p className="text-xs text-gray-400 mt-1 leading-relaxed">
                  Detects cheating and non-cheating behavior during examination monitoring.
>>>>>>> Stashed changes
                </p>
              </div>
            </div>

<<<<<<< Updated upstream
=======
            {/* INPUT SOURCE SELECTOR */}
            <div className="mt-6">
              <h3 className="text-sm font-bold text-gray-200 mb-3">Input Source</h3>

              <div className="grid grid-cols-3 gap-2">
                {/* 1. LIVE CAMERA */}
                <button
                  type="button"
                  disabled={isRunning || loading}
                  onClick={() => setInputSource("camera")}
                  className={`p-3 rounded-xl border text-left transition-all ${
                    inputSource === "camera"
                      ? "bg-green-500/15 border-green-500 text-green-300"
                      : "bg-[#071828] border-white/10 text-gray-400 hover:border-green-400/50"
                  } disabled:opacity-50`}
                >
                  <div className="text-base">📹</div>
                  <div className="font-bold text-xs mt-1">Live Camera</div>
                  <div className="text-[9px] opacity-70">Webcam</div>
                </button>

                {/* 2. SERVER DEMO VIDEO */}
                <button
                  type="button"
                  disabled={isRunning || loading}
                  onClick={() => setInputSource("demo")}
                  className={`p-3 rounded-xl border text-left transition-all ${
                    inputSource === "demo"
                      ? "bg-cyan-500/15 border-cyan-500 text-cyan-300"
                      : "bg-[#071828] border-white/10 text-gray-400 hover:border-cyan-400/50"
                  } disabled:opacity-50`}
                >
                  <div className="text-base">🎬</div>
                  <div className="font-bold text-xs mt-1">Demo Video</div>
                  <div className="text-[9px] opacity-70">Server Sample</div>
                </button>

                {/* 3. UPLOAD CUSTOM VIDEO FROM PC */}
                <button
                  type="button"
                  disabled={isRunning || loading}
                  onClick={() => {
                    setInputSource("custom_upload");
                    fileInputRef.current?.click();
                  }}
                  className={`p-3 rounded-xl border text-left transition-all ${
                    inputSource === "custom_upload"
                      ? "bg-purple-500/20 border-purple-500 text-purple-300 shadow-md shadow-purple-500/20"
                      : "bg-[#071828] border-white/10 text-gray-400 hover:border-purple-400/50"
                  } disabled:opacity-50`}
                >
                  <div className="text-base">📁</div>
                  <div className="font-bold text-xs mt-1">Upload Video</div>
                  <div className="text-[9px] opacity-70">From PC</div>
                </button>
              </div>

              {/* Hidden file input for uploading PC video */}
              <input
                ref={fileInputRef}
                type="file"
                accept="video/*"
                onChange={handleFileChange}
                className="hidden"
              />

              {/* DISPLAY SELECTED UPLOADED VIDEO */}
              {inputSource === "custom_upload" && (
                <div className="mt-3 p-3 rounded-xl bg-purple-500/10 border border-purple-500/30">
                  <div className="flex justify-between items-center">
                    <span className="text-[11px] font-bold text-purple-300 uppercase">
                      Chosen PC Video File:
                    </span>
                    <button
                      type="button"
                      disabled={isRunning || loading}
                      onClick={() => fileInputRef.current?.click()}
                      className="text-[10px] text-purple-400 hover:text-white underline font-semibold"
                    >
                      Browse...
                    </button>
                  </div>
                  <p className="text-xs font-mono text-gray-200 mt-1 truncate">
                    {uploadedVideoFile ? `🎬 ${uploadedVideoFile.name}` : "⚠️ No file selected yet (Click to browse)"}
                  </p>
                </div>
              )}

              {inputSource === "demo" && (
                <div className="mt-3 p-3 rounded-xl bg-cyan-500/10 border border-cyan-500/20">
                  <div className="text-xs font-bold text-cyan-300">PRE-RECORDED AI DEMO</div>
                  <p className="text-[11px] text-gray-400 mt-1 leading-relaxed">
                    Uses backend pre-recorded demo video files and processes them frame by frame.
                  </p>
                </div>
              )}
            </div>
>>>>>>> Stashed changes
          </div>

          {/* START / STOP */}

          <div className="pt-6 border-t border-white/10">
            {!isRunning ? (

              <button
<<<<<<< Updated upstream
                onClick={() => startSession(selectedMode)}
                disabled={!selectedMode || loading}
                className="w-full py-4 bg-gradient-to-r from-blue-600 to-indigo-600 hover:from-blue-500 hover:to-indigo-500 disabled:opacity-40 disabled:cursor-not-allowed rounded-xl font-bold uppercase tracking-wider text-sm shadow-xl transition-all"
              >
                {loading
                  ? "Initializing..."
                  : "Launch AI Camera Feed"}
=======
                onClick={startSession}
                disabled={!selectedMode || loading || (inputSource === "custom_upload" && !uploadedVideoFile)}
                className="w-full py-4 bg-gradient-to-r from-blue-600 to-indigo-600 hover:from-blue-500 hover:to-indigo-500 disabled:opacity-40 disabled:cursor-not-allowed rounded-xl font-bold uppercase tracking-wider text-sm shadow-xl transition-all"
              >
                {loading ? "Initializing..." : launchText}
>>>>>>> Stashed changes
              </button>

            ) : (

              <button
                onClick={stopSession}
                disabled={loading}
                className="w-full py-4 bg-red-600 hover:bg-red-700 disabled:opacity-50 rounded-xl font-bold uppercase tracking-wider text-sm shadow-xl transition-all"
              >
<<<<<<< Updated upstream
                {loading
                  ? "Terminating..."
                  : "Terminate & Export Log"}
=======
                {loading ? "Terminating..." : "Terminate & Export Log"}
>>>>>>> Stashed changes
              </button>

            )}
          </div>
        </div>

        {/* RIGHT VIDEO PANEL */}
<<<<<<< Updated upstream

        <div className="lg:col-span-2 bg-[#091d30] border border-white/10 rounded-2xl p-4 flex flex-col">

          <div className="flex justify-between items-center mb-3">

=======
        <div className="lg:col-span-2 bg-[#091d30] border border-white/10 rounded-2xl p-4 flex flex-col">
          <div className="flex justify-between items-center mb-3 gap-3">
>>>>>>> Stashed changes
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
<<<<<<< Updated upstream

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

=======
              Surveillance Stream Output
            </span>

            <div className="flex items-center gap-2 flex-wrap justify-end">
              {isRunning && (
                <span
                  className={`px-3 py-1 text-xs font-mono font-bold rounded-lg border ${
                    inputSource === "camera"
                      ? "bg-green-500/20 text-green-400 border-green-500/30"
                      : inputSource === "custom_upload"
                      ? "bg-purple-500/20 text-purple-300 border-purple-500/30"
                      : "bg-cyan-500/20 text-cyan-300 border-cyan-500/30"
                  }`}
                >
                  {inputSource === "camera"
                    ? "● LIVE CAMERA"
                    : inputSource === "custom_upload"
                    ? "● UPLOADED PC VIDEO"
                    : "● PRESET DEMO VIDEO"}
                </span>
              )}

              {streamStatus === "connected" && (
                <span className="px-3 py-1 bg-green-500/20 text-green-400 text-xs font-mono font-bold rounded-lg border border-green-500/30">
                  ● AI INFERENCE RUNNING
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
          </div>

          {/* VIDEO FEED STREAM */}
          <div className="flex-1 bg-black rounded-xl border border-white/10 flex items-center justify-center overflow-hidden min-h-[420px] relative">
            {streamUrl && streamStatus !== "error" ? (
>>>>>>> Stashed changes
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
<<<<<<< Updated upstream

                  {streamStatus === "error"
                    ? "Camera Stream Failed"
                    : streamStatus === "connecting"
                    ? "Connecting to Camera..."
                    : "Camera Feed Inactive"}

=======
                  {streamStatus === "error"
                    ? "AI Stream Failed"
                    : streamStatus === "connecting"
                    ? `Connecting to ${sourceTitle}...`
                    : "AI Feed Inactive"}
>>>>>>> Stashed changes
                </h3>
                <p className="text-xs text-gray-500 mt-2 max-w-sm mx-auto">
<<<<<<< Updated upstream
                  {streamError ||
                    "Select a preset and launch the AI camera feed."}
=======
                  {streamError || "Choose a preset and input source, then launch the AI feed."}
>>>>>>> Stashed changes
                </p>
              </div>
            )}
          </div>

<<<<<<< Updated upstream
=======
          {/* CURRENT SELECTION BADGES */}
          {selectedMode && !isRunning && (
            <div className="mt-3 text-xs text-gray-500">
              Selected:
              <span className="text-gray-300 font-semibold ml-1">
                {selectedMode === "classroom" ? "Smart Classroom" : "Exam Proctor"}
              </span>
              <span className="mx-2">•</span>
              <span className="text-gray-300 font-semibold">{sourceTitle}</span>
              {inputSource === "custom_upload" && uploadedVideoFile && (
                <span className="text-purple-400 font-mono ml-2">({uploadedVideoFile.name})</span>
              )}
            </div>
          )}
>>>>>>> Stashed changes
        </div>
      </div>

    </div>

  );

}