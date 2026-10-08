import React, { useState, useEffect } from "react";
import axios from "axios";

export default function EvidenceLogs() {
  const [students, setStudents] = useState([]);
  const [selectedStudent, setSelectedStudent] = useState(null);
  const [evidenceList, setEvidenceList] = useState([]);
  const [searchQuery, setSearchQuery] = useState("");
  const [loadingStudents, setLoadingStudents] = useState(true);
  const [loadingEvidence, setLoadingEvidence] = useState(false);

  // 1. Fetch all registered students
  useEffect(() => {
    const fetchStudents = async () => {
      try {
        setLoadingStudents(true);
        const res = await axios.get("http://localhost:8000/api/users/all");
        const list = res.data.students || [];
        setStudents(list);
        if (list.length > 0) {
          setSelectedStudent(list[0]);
          loadEvidence(list[0].student_id);
        }
      } catch (err) {
        console.error("Failed to load students:", err);
      } finally {
        setLoadingStudents(false);
      }
    };
    fetchStudents();
  }, []);

  // 2. Fetch real database captured evidence
  const loadEvidence = async (studentId) => {
    if (!studentId) return;
    try {
      setLoadingEvidence(true);
      const res = await axios.get(`http://localhost:8000/api/evidence/${studentId.trim()}`);
      
      // Extracts data array from response safely
      const items = res.data?.data || (Array.isArray(res.data) ? res.data : []);
      setEvidenceList(items);
    } catch (err) {
      console.error("Failed to load evidence images:", err);
      setEvidenceList([]);
    } finally {
      setLoadingEvidence(false);
    }
  };

  const handleSelectStudent = (student) => {
    setSelectedStudent(student);
    loadEvidence(student.student_id);
  };

  // 3. Direct browser download for real captured screenshot
  const handleDownload = async (imageUrl, filename) => {
    try {
      const response = await fetch(imageUrl);
      const blob = await response.blob();
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = filename || `evidence_${Date.now()}.jpg`;
      document.body.appendChild(a);
      a.click();
      window.URL.revokeObjectURL(url);
      document.body.removeChild(a);
    } catch (error) {
      alert("Failed to download image file. Make sure file exists in backend storage.");
    }
  };

  const filteredStudents = students.filter(
    (s) =>
      s.student_id?.toLowerCase().includes(searchQuery.toLowerCase()) ||
      s.name?.toLowerCase().includes(searchQuery.toLowerCase())
  );

  return (
    <div className="bg-[#111a2e] border border-gray-800 rounded-3xl p-6 shadow-2xl">
      {/* HEADER */}
      <div className="pb-6 mb-6 border-b border-gray-800 flex flex-col md:flex-row justify-between items-start md:items-center gap-4">
        <div>
          <h2 className="text-xl font-bold text-white flex items-center gap-2">
            <span>📸</span> Student Violation Evidence Repository
          </h2>
          <p className="text-xs text-gray-400 mt-0.5">
            View authentic webcam bounding-box captures logged in MongoDB & local storage.
          </p>
        </div>

        {/* SEARCH BOX */}
        <div className="w-full md:w-auto">
          <input
            type="text"
            placeholder="Search Student ID or Name..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="w-full md:w-72 bg-[#0b1324] border border-gray-700 rounded-xl px-4 py-2 text-xs text-white placeholder-gray-500 focus:outline-none focus:border-blue-500"
          />
        </div>
      </div>

      {/* 2-COLUMN LAYOUT */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        {/* LEFT: STUDENT SELECTION LIST */}
        <div className="lg:col-span-4 bg-[#0b1324] border border-gray-800 rounded-2xl p-4 max-h-[650px] flex flex-col">
          <span className="text-xs font-bold text-gray-400 uppercase tracking-wider mb-3 px-1">
            Enrolled Students ({filteredStudents.length})
          </span>

          {loadingStudents ? (
            <div className="text-center py-10 text-gray-500 text-xs">Loading students...</div>
          ) : filteredStudents.length === 0 ? (
            <div className="text-center py-10 text-gray-500 text-xs">No students found.</div>
          ) : (
            <div className="space-y-2 overflow-y-auto pr-1">
              {filteredStudents.map((s) => {
                const isSelected = selectedStudent?.student_id === s.student_id;
                return (
                  <button
                    key={s._id}
                    onClick={() => handleSelectStudent(s)}
                    className={`w-full text-left p-3.5 rounded-xl border transition flex items-center justify-between ${
                      isSelected
                        ? "bg-blue-600/20 border-blue-500 text-white shadow-md shadow-blue-500/10"
                        : "bg-[#111a2e]/60 border-gray-800/80 text-gray-300 hover:bg-[#111a2e] hover:border-gray-700"
                    }`}
                  >
                    <div>
                      <p className="font-mono text-xs font-bold text-blue-400">{s.student_id}</p>
                      <p className="text-sm font-semibold truncate max-w-[180px]">{s.name}</p>
                    </div>
                    <span className="text-xs text-gray-400">➔</span>
                  </button>
                );
              })}
            </div>
          )}
        </div>

        {/* RIGHT: REAL CAPTURED EVIDENCE GALLERY */}
        <div className="lg:col-span-8 bg-[#0b1324] border border-gray-800 rounded-2xl p-5 min-h-[400px]">
          {selectedStudent ? (
            <div>
              <div className="flex justify-between items-center pb-4 mb-4 border-b border-gray-800/80">
                <div>
                  <h3 className="text-base font-bold text-white flex items-center gap-2">
                    Evidence Logs for:{" "}
                    <span className="text-blue-400 font-mono">{selectedStudent.student_id}</span>
                  </h3>
                  <span className="text-xs text-gray-400">{selectedStudent.name}</span>
                </div>
                <span className="px-3 py-1 bg-red-500/10 text-red-400 border border-red-500/20 rounded-full text-xs font-bold font-mono">
                  {evidenceList.length} Captures Logged
                </span>
              </div>

              {loadingEvidence ? (
                <div className="text-center py-20 text-gray-400 text-sm">
                  ⏳ Loading real snapshots from database...
                </div>
              ) : evidenceList.length === 0 ? (
                <div className="text-center py-20 text-gray-500 bg-[#111a2e]/40 rounded-2xl border border-dashed border-gray-800 text-sm">
                  🛡️ No behavioral violation captures recorded for this student.
                </div>
              ) : (
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4 max-h-[540px] overflow-y-auto pr-1">
                  {evidenceList.map((ev, index) => (
                    <div
                      key={index}
                      className="bg-[#111a2e] border border-gray-800 rounded-2xl p-3 flex flex-col justify-between hover:border-gray-700 transition"
                    >
                      {/* REAL CAPTURED IMAGE */}
                      <div className="relative rounded-xl overflow-hidden aspect-video bg-black/60 mb-3 border border-gray-800">
                        <img
                          src={ev.image_url}
                          alt="Surveillance Evidence"
                          className="w-full h-full object-cover"
                          onError={(e) => {
                            e.target.onerror = null;
                            e.target.src = "https://placehold.co/600x400/0b1324/red?text=Snapshot+Not+Found";
                          }}
                        />
                        <span className="absolute top-2 left-2 bg-red-600 text-white text-[10px] font-bold uppercase tracking-wider px-2 py-0.5 rounded-full shadow">
                          {ev.behavior}
                        </span>
                        <span className="absolute bottom-2 right-2 bg-black/80 backdrop-blur-sm text-gray-300 text-[10px] font-mono px-2 py-0.5 rounded">
                          {ev.mode}
                        </span>
                      </div>

                      {/* DETAILS & DOWNLOAD BUTTON */}
                      <div className="space-y-3">
                        <div className="flex justify-between items-center text-xs text-gray-400">
                          <span>Captured:</span>
                          <span className="text-gray-200 font-mono text-[11px]">{ev.date}</span>
                        </div>

                        <button
                          type="button"
                          onClick={() => handleDownload(ev.image_url, ev.filename)}
                          className="w-full py-2 bg-blue-600/20 hover:bg-blue-600 text-blue-400 hover:text-white border border-blue-500/30 rounded-xl text-xs font-bold transition flex items-center justify-center gap-2 shadow"
                        >
                          <span>⬇ Download Screenshot</span>
                        </button>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          ) : (
            <div className="text-center py-24 text-gray-500 text-sm">
              Select a student from the left panel to inspect captured evidence.
            </div>
          )}
        </div>
      </div>
    </div>
  );
}