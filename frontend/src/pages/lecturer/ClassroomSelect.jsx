// src/pages/lecturer/ClassroomSelect.jsx

import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";

export default function ClassroomSelect() {
  const navigate = useNavigate();

  const savedClassroom = JSON.parse(
    localStorage.getItem("classroom") || "{}"
  );

  const [year, setYear] = useState(savedClassroom.year || "");
  const [sem, setSem] = useState(savedClassroom.sem || "");
  const [subject, setSubject] = useState(savedClassroom.subject || "");
  const [group, setGroup] = useState(savedClassroom.group || "");

  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  const subjects = {
    1: [
      "Programming Fundamentals",
      "Database Management",
      "Computer Systems",
      "Web Development",
    ],
    2: [
      "Data Structures and Algorithms",
      "Object Oriented Programming",
      "Computer Networks",
      "Software Engineering",
    ],
    3: [
      "Artificial Intelligence",
      "Machine Learning",
      "Information Security",
      "Mobile Application Development",
    ],
    4: [
      "Cloud Computing",
      "Enterprise Resource Planning",
      "Research Project",
      "Final Year Project",
    ],
  };

  useEffect(() => {
    if (
      year &&
      subject &&
      !subjects[year]?.includes(subject)
    ) {
      setSubject("");
    }
  }, [year]);

  const submit = async () => {
    if (!year || !sem || !subject || !group) {
      setError("Please select all classroom details.");
      return;
    }

    setError("");
    setLoading(true);

    const classroomData = {
      year,
      sem,
      subject,
      group,
    };

    localStorage.setItem(
      "classroom",
      JSON.stringify(classroomData)
    );

    await new Promise((resolve) => {
      setTimeout(resolve, 700);
    });

    navigate("/lecturer/dashboard");
  };

  const clearSelection = () => {
    setYear("");
    setSem("");
    setSubject("");
    setGroup("");
    setError("");

    localStorage.removeItem("classroom");
  };

  return (
    <div className="min-h-screen bg-[#050f1d] text-white relative overflow-hidden">

      {/* Background Decorations */}

      <div className="absolute top-[-150px] left-[-150px] w-[400px] h-[400px] bg-blue-600/20 rounded-full blur-[120px]" />

      <div className="absolute bottom-[-150px] right-[-150px] w-[400px] h-[400px] bg-purple-600/20 rounded-full blur-[120px]" />

      <div className="relative z-10 min-h-screen flex flex-col">

        {/* Top Header */}

        <header className="border-b border-white/10 bg-[#071828]/80 backdrop-blur-xl">
          <div className="max-w-7xl mx-auto px-5 md:px-8 py-5 flex items-center justify-between">

            <div className="flex items-center gap-4">
              <div className="w-12 h-12 rounded-xl bg-gradient-to-br from-blue-500 to-purple-600 flex items-center justify-center text-2xl shadow-lg">
                🎓
              </div>

              <div>
                <h1 className="text-xl md:text-2xl font-bold">
                  Student360
                </h1>

                <p className="text-sm text-gray-400">
                  Lecturer Classroom Selection
                </p>
              </div>
            </div>

            <button
              onClick={() => navigate("/lecturer/dashboard")}
              className="px-4 py-2 rounded-lg bg-white/5 hover:bg-white/10 border border-white/10 text-sm transition"
            >
              Back to Dashboard
            </button>

          </div>
        </header>

        {/* Main Content */}

        <main className="flex-1 flex items-center justify-center px-4 py-10">

          <div className="w-full max-w-5xl grid lg:grid-cols-2 gap-7">

            {/* Left Information Panel */}

            <div className="bg-gradient-to-br from-blue-600/20 to-purple-600/20 border border-white/10 rounded-3xl p-7 md:p-10 flex flex-col justify-between">

              <div>
                <span className="inline-flex px-4 py-2 rounded-full bg-blue-500/15 text-blue-300 border border-blue-500/20 text-sm">
                  AI Classroom Analytics
                </span>

                <h2 className="text-3xl md:text-4xl font-bold mt-6 leading-tight">
                  Select Your Classroom
                </h2>

                <p className="text-gray-300 mt-4 leading-relaxed">
                  Choose the academic year, semester, subject and student
                  group before loading classroom analytics.
                </p>
              </div>

              <div className="space-y-4 mt-10">

                <FeatureItem
                  icon="📊"
                  title="Performance Analytics"
                  description="View attendance and behavior scores."
                />

                <FeatureItem
                  icon="🤖"
                  title="AI Monitoring"
                  description="Start classroom behavior detection."
                />

                <FeatureItem
                  icon="⚠️"
                  title="Risk Identification"
                  description="Identify students requiring attention."
                />

              </div>

            </div>

            {/* Selection Form */}

            <div className="bg-[#0b2236]/90 backdrop-blur-xl border border-white/10 rounded-3xl p-6 md:p-9 shadow-2xl">

              <div className="mb-7">
                <p className="text-sm text-blue-300 font-medium">
                  CLASSROOM CONFIGURATION
                </p>

                <h2 className="text-2xl md:text-3xl font-bold mt-2">
                  Classroom Details
                </h2>

                <p className="text-gray-400 mt-2">
                  Complete all fields to continue.
                </p>
              </div>

              {/* Year */}

              <FormGroup
                label="Academic Year"
                number="01"
              >
                <select
                  value={year}
                  onChange={(event) => setYear(event.target.value)}
                  className="form-input"
                >
                  <option value="">
                    Select academic year
                  </option>

                  <option value="1">
                    Year 1
                  </option>

                  <option value="2">
                    Year 2
                  </option>

                  <option value="3">
                    Year 3
                  </option>

                  <option value="4">
                    Year 4
                  </option>
                </select>
              </FormGroup>

              {/* Semester */}

              <FormGroup
                label="Semester"
                number="02"
              >
                <div className="grid grid-cols-2 gap-3">

                  <SelectionButton
                    label="Semester 1"
                    selected={sem === "1"}
                    onClick={() => setSem("1")}
                  />

                  <SelectionButton
                    label="Semester 2"
                    selected={sem === "2"}
                    onClick={() => setSem("2")}
                  />

                </div>
              </FormGroup>

              {/* Subject */}

              <FormGroup
                label="Subject"
                number="03"
              >
                <select
                  value={subject}
                  onChange={(event) =>
                    setSubject(event.target.value)
                  }
                  disabled={!year}
                  className="form-input disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  <option value="">
                    {year
                      ? "Select subject"
                      : "Select academic year first"}
                  </option>

                  {year &&
                    subjects[year]?.map((item) => (
                      <option
                        key={item}
                        value={item}
                      >
                        {item}
                      </option>
                    ))}
                </select>
              </FormGroup>

              {/* Group */}

              <FormGroup
                label="Student Group"
                number="04"
              >
                <div className="grid grid-cols-3 gap-3">

                  {["A", "B", "C"].map((item) => (
                    <SelectionButton
                      key={item}
                      label={`Group ${item}`}
                      selected={group === item}
                      onClick={() => setGroup(item)}
                    />
                  ))}

                </div>
              </FormGroup>

              {/* Error */}

              {error && (
                <div className="bg-red-500/10 border border-red-500/30 text-red-300 rounded-xl p-4 mb-5 flex items-center gap-3">
                  <span>
                    ⚠️
                  </span>

                  <p className="text-sm">
                    {error}
                  </p>
                </div>
              )}

              {/* Selection Preview */}

              {(year || sem || subject || group) && (
                <div className="bg-[#071828] border border-white/10 rounded-2xl p-5 mb-6">

                  <p className="text-sm text-gray-400 mb-4">
                    SELECTED CLASSROOM
                  </p>

                  <div className="grid grid-cols-2 gap-4">

                    <PreviewItem
                      label="Year"
                      value={year ? `Year ${year}` : "Not selected"}
                    />

                    <PreviewItem
                      label="Semester"
                      value={sem ? `Semester ${sem}` : "Not selected"}
                    />

                    <PreviewItem
                      label="Subject"
                      value={subject || "Not selected"}
                    />

                    <PreviewItem
                      label="Group"
                      value={group ? `Group ${group}` : "Not selected"}
                    />

                  </div>

                </div>
              )}

              {/* Buttons */}

              <div className="flex flex-col sm:flex-row gap-3">

                <button
                  type="button"
                  onClick={clearSelection}
                  className="sm:w-1/3 px-5 py-3 rounded-xl bg-white/5 hover:bg-white/10 border border-white/10 transition"
                >
                  Clear
                </button>

                <button
                  type="button"
                  onClick={submit}
                  disabled={loading}
                  className="sm:w-2/3 px-5 py-3 rounded-xl bg-gradient-to-r from-blue-600 to-purple-600 hover:from-blue-700 hover:to-purple-700 disabled:opacity-50 disabled:cursor-not-allowed font-semibold transition flex items-center justify-center gap-2"
                >
                  {loading ? (
                    <>
                      <span className="w-5 h-5 border-2 border-white/40 border-t-white rounded-full animate-spin" />
                      Loading Classroom...
                    </>
                  ) : (
                    <>
                      Load Classroom
                      <span>
                        →
                      </span>
                    </>
                  )}
                </button>

              </div>

            </div>

          </div>

        </main>

      </div>

      <style>
        {`
          .form-input {
            width: 100%;
            background: #071828;
            color: white;
            border: 1px solid rgba(255,255,255,0.1);
            border-radius: 12px;
            padding: 13px 14px;
            outline: none;
            transition: 0.2s;
          }

          .form-input:focus {
            border-color: #3b82f6;
            box-shadow: 0 0 0 3px rgba(59,130,246,0.12);
          }

          .form-input option {
            background: #0b2236;
            color: white;
          }
        `}
      </style>

    </div>
  );
}

function FormGroup({ label, number, children }) {
  return (
    <div className="mb-6">

      <div className="flex items-center gap-3 mb-3">

        <span className="w-7 h-7 rounded-full bg-blue-500/15 text-blue-300 text-xs flex items-center justify-center border border-blue-500/20">
          {number}
        </span>

        <label className="text-sm font-medium text-gray-300">
          {label}
        </label>

      </div>

      {children}

    </div>
  );
}

function SelectionButton({
  label,
  selected,
  onClick,
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      className={`px-4 py-3 rounded-xl border font-medium transition ${
        selected
          ? "bg-blue-600 text-white border-blue-500 shadow-lg shadow-blue-600/20"
          : "bg-[#071828] text-gray-300 border-white/10 hover:border-blue-500/50 hover:bg-blue-500/5"
      }`}
    >
      {label}
    </button>
  );
}

function PreviewItem({ label, value }) {
  return (
    <div>
      <p className="text-xs text-gray-500">
        {label}
      </p>

      <p className="text-sm font-semibold mt-1 truncate">
        {value}
      </p>
    </div>
  );
}

function FeatureItem({
  icon,
  title,
  description,
}) {
  return (
    <div className="flex items-start gap-4">

      <div className="w-11 h-11 rounded-xl bg-white/10 flex items-center justify-center text-xl">
        {icon}
      </div>

      <div>
        <h3 className="font-semibold">
          {title}
        </h3>

        <p className="text-sm text-gray-400 mt-1">
          {description}
        </p>
      </div>

    </div>
  );
}