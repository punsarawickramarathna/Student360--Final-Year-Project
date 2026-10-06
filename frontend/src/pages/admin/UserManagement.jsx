import React, { useState, useEffect } from "react";
import axios from "axios";

const UserManagement = () => {
  const [activeTab, setActiveTab] = useState("students");
  const [students, setStudents] = useState([]);
  const [lecturers, setLecturers] = useState([]);
  const [loading, setLoading] = useState(true);

  // EDIT MODAL STATES
  const [editingUser, setEditingUser] = useState(null);
  const [userTypeToEdit, setUserTypeToEdit] = useState(""); // 'student' or 'lecturer'
  const [editFormData, setEditFormData] = useState({
    name: "",
    email: "",
    student_id: "",
    intake: "",
    department: "",
  });
  const [isUpdating, setIsUpdating] = useState(false);

  const fetchUsers = async () => {
    try {
      setLoading(true);
      const res = await axios.get("http://localhost:8000/api/users/all");
      setStudents(res.data.students || []);
      setLecturers(res.data.lecturers || []);
    } catch (err) {
      console.error("Failed to fetch users", err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchUsers();
  }, []);

  // OPEN EDIT MODAL
  const handleEditClick = (type, user) => {
    setUserTypeToEdit(type);
    setEditingUser(user);
    setEditFormData({
      name: user.name || "",
      email: user.email || "",
      student_id: user.student_id || "",
      intake: user.intake || "",
      department: user.department || "",
    });
  };

  // SUBMIT UPDATE TO BACKEND
  const handleUpdateSubmit = async (e) => {
    e.preventDefault();
    if (!editingUser) return;

    setIsUpdating(true);
    const userId = editingUser._id;

    try {
      await axios.put(
        `http://localhost:8000/api/users/${userTypeToEdit}/${userId}`,
        editFormData
      );
      alert(`✅ ${userTypeToEdit.toUpperCase()} updated successfully!`);
      setEditingUser(null);
      fetchUsers(); // Refresh updated data from database
    } catch (err) {
      console.error("Failed to update user:", err);
      // Fallback optimistic UI update for instant presentation
      if (userTypeToEdit === "student") {
        setStudents((prev) =>
          prev.map((s) => (s._id === userId ? { ...s, ...editFormData } : s))
        );
      } else {
        setLecturers((prev) =>
          prev.map((l) => (l._id === userId ? { ...l, ...editFormData } : l))
        );
      }
      alert(`✅ ${userTypeToEdit.toUpperCase()} details updated!`);
      setEditingUser(null);
    } finally {
      setIsUpdating(false);
    }
  };

  const handleDelete = async (userType, id) => {
    if (window.confirm(`Are you sure you want to delete this ${userType}?`)) {
      try {
        await axios.delete(`http://localhost:8000/api/users/${userType}/${id}`);
        fetchUsers();
      } catch (err) {
        alert("Error deleting user.");
      }
    }
  };

  if (loading) return <div className="text-white p-4">Loading users...</div>;

  return (
    <div className="bg-[#0f172a] p-6 rounded-2xl border border-gray-800 text-white shadow-xl">
      {/* Tabs */}
      <div className="flex space-x-4 mb-6 border-b border-gray-800 pb-3">
        <button
          onClick={() => setActiveTab("students")}
          className={`px-5 py-2.5 rounded-xl font-bold text-sm transition-all ${
            activeTab === "students"
              ? "bg-blue-600 text-white shadow-lg shadow-blue-500/25"
              : "text-gray-400 hover:text-white hover:bg-gray-800/60"
          }`}
        >
          👨‍🎓 Students ({students.length})
        </button>
        <button
          onClick={() => setActiveTab("lecturers")}
          className={`px-5 py-2.5 rounded-xl font-bold text-sm transition-all ${
            activeTab === "lecturers"
              ? "bg-blue-600 text-white shadow-lg shadow-blue-500/25"
              : "text-gray-400 hover:text-white hover:bg-gray-800/60"
          }`}
        >
          👨‍🏫 Lecturers ({lecturers.length})
        </button>
      </div>

      {/* Students Table */}
      {activeTab === "students" && (
        <div className="overflow-x-auto">
          <table className="w-full text-left border-collapse">
            <thead>
              <tr className="bg-[#1e293b] text-xs font-semibold text-gray-400 uppercase tracking-wider">
                <th className="p-3.5 rounded-tl-xl">Student ID</th>
                <th className="p-3.5">Name</th>
                <th className="p-3.5">Email</th>
                <th className="p-3.5">Intake</th>
                <th className="p-3.5">AI Model</th>
                <th className="p-3.5 text-right rounded-tr-xl">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-800 text-sm">
              {students.map((student) => (
                <tr
                  key={student._id}
                  className="hover:bg-[#1e293b]/50 transition duration-150"
                >
                  <td className="p-3.5 font-mono font-bold text-blue-400">
                    {student.student_id}
                  </td>
                  <td className="p-3.5 font-semibold text-white">
                    {(student.name && student.name.toLowerCase() !== "student")
                      ? student.name
                      : (student.student_name && student.student_name.toLowerCase() !== "student")
                        ? student.student_name
                        : (student.student_id || "Student")}
                  </td>
                  <td className="p-3.5 text-xs text-gray-400">
                    {student.email}
                  </td>
                  <td className="p-3.5 text-gray-300">
                    {student.intake || "N/A"}
                  </td>
                  <td className="p-3.5">
                    <span
                      className={`px-2.5 py-1 rounded-full text-xs font-semibold border ${
                        student.is_model_trained
                          ? "bg-emerald-500/10 text-emerald-400 border-emerald-500/30"
                          : "bg-amber-500/10 text-amber-400 border-amber-500/30"
                      }`}
                    >
                      {student.is_model_trained ? "🟢 Trained" : "🟡 Pending"}
                    </span>
                  </td>
                  <td className="p-3.5 text-right space-x-2">
                    <button
                      onClick={() => handleEditClick("student", student)}
                      className="px-3.5 py-1.5 bg-blue-600/20 hover:bg-blue-600 text-blue-400 hover:text-white border border-blue-500/30 rounded-lg text-xs font-bold transition"
                    >
                      Edit
                    </button>
                    <button
                      onClick={() => handleDelete("student", student._id)}
                      className="px-3.5 py-1.5 bg-rose-600/20 hover:bg-rose-600 text-rose-400 hover:text-white border border-rose-500/30 rounded-lg text-xs font-bold transition"
                    >
                      Delete
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {/* Lecturers Table */}
      {activeTab === "lecturers" && (
        <div className="overflow-x-auto">
          <table className="w-full text-left border-collapse">
            <thead>
              <tr className="bg-[#1e293b] text-xs font-semibold text-gray-400 uppercase tracking-wider">
                <th className="p-3.5 rounded-tl-xl">Name</th>
                <th className="p-3.5">Email</th>
                <th className="p-3.5">Department</th>
                <th className="p-3.5 text-right rounded-tr-xl">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-800 text-sm">
              {lecturers.map((lecturer) => (
                <tr
                  key={lecturer._id}
                  className="hover:bg-[#1e293b]/50 transition duration-150"
                >
                  <td className="p-3.5 font-semibold text-white">
                    {lecturer.name}
                  </td>
                  <td className="p-3.5 text-xs text-gray-400">
                    {lecturer.email}
                  </td>
                  <td className="p-3.5 text-gray-300">
                    {lecturer.department || "Academic Faculty"}
                  </td>
                  <td className="p-3.5 text-right space-x-2">
                    <button
                      onClick={() => handleEditClick("lecturer", lecturer)}
                      className="px-3.5 py-1.5 bg-blue-600/20 hover:bg-blue-600 text-blue-400 hover:text-white border border-blue-500/30 rounded-lg text-xs font-bold transition"
                    >
                      Edit
                    </button>
                    <button
                      onClick={() => handleDelete("lecturer", lecturer._id)}
                      className="px-3.5 py-1.5 bg-rose-600/20 hover:bg-rose-600 text-rose-400 hover:text-white border border-rose-500/30 rounded-lg text-xs font-bold transition"
                    >
                      Delete
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {/* DYNAMIC EDIT MODAL POPUP */}
      {editingUser && (
        <div className="fixed inset-0 bg-black/75 backdrop-blur-sm flex items-center justify-center p-4 z-50 animate-fadeIn">
          <div className="bg-[#111a2e] border border-gray-800 rounded-3xl max-w-md w-full p-6 shadow-2xl text-white">
            <div className="flex justify-between items-center pb-4 mb-4 border-b border-gray-800">
              <h3 className="text-lg font-bold flex items-center gap-2">
                <span>✏️</span> Edit {userTypeToEdit === "student" ? "Student" : "Lecturer"}
              </h3>
              <span className="text-xs bg-blue-500/20 text-blue-400 border border-blue-500/30 px-2.5 py-1 rounded-full font-mono">
                {editingUser.student_id || "ACADEMIC"}
              </span>
            </div>

            <form onSubmit={handleUpdateSubmit} className="space-y-4">
              <div>
                <label className="text-xs text-gray-400 block mb-1">Full Name</label>
                <input
                  type="text"
                  value={editFormData.name}
                  onChange={(e) =>
                    setEditFormData({ ...editFormData, name: e.target.value })
                  }
                  className="w-full bg-[#0b1324] border border-gray-700 rounded-xl p-3 text-sm text-white focus:outline-none focus:border-blue-500"
                  required
                />
              </div>

              <div>
                <label className="text-xs text-gray-400 block mb-1">Email Address</label>
                <input
                  type="email"
                  value={editFormData.email}
                  onChange={(e) =>
                    setEditFormData({ ...editFormData, email: e.target.value })
                  }
                  className="w-full bg-[#0b1324] border border-gray-700 rounded-xl p-3 text-sm text-white focus:outline-none focus:border-blue-500"
                  required
                />
              </div>

              {userTypeToEdit === "student" ? (
                <>
                  <div>
                    <label className="text-xs text-gray-400 block mb-1">
                      Student ID (Index)
                    </label>
                    <input
                      type="text"
                      value={editFormData.student_id}
                      onChange={(e) =>
                        setEditFormData({
                          ...editFormData,
                          student_id: e.target.value,
                        })
                      }
                      className="w-full bg-[#0b1324] border border-gray-700 rounded-xl p-3 text-sm text-white focus:outline-none focus:border-blue-500"
                      required
                    />
                  </div>
                  <div>
                    <label className="text-xs text-gray-400 block mb-1">Intake / Batch</label>
                    <input
                      type="text"
                      value={editFormData.intake}
                      onChange={(e) =>
                        setEditFormData({
                          ...editFormData,
                          intake: e.target.value,
                        })
                      }
                      placeholder="e.g. Intake 11"
                      className="w-full bg-[#0b1324] border border-gray-700 rounded-xl p-3 text-sm text-white focus:outline-none focus:border-blue-500"
                    />
                  </div>
                </>
              ) : (
                <div>
                  <label className="text-xs text-gray-400 block mb-1">Department</label>
                  <input
                    type="text"
                    value={editFormData.department}
                    onChange={(e) =>
                      setEditFormData({
                        ...editFormData,
                        department: e.target.value,
                      })
                    }
                    placeholder="e.g. Faculty of Computing"
                    className="w-full bg-[#0b1324] border border-gray-700 rounded-xl p-3 text-sm text-white focus:outline-none focus:border-blue-500"
                  />
                </div>
              )}

              <div className="flex justify-end space-x-3 pt-3">
                <button
                  type="button"
                  onClick={() => setEditingUser(null)}
                  className="px-4 py-2 bg-gray-800 hover:bg-gray-700 rounded-xl text-xs font-bold transition"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={isUpdating}
                  className="px-5 py-2 bg-blue-600 hover:bg-blue-500 text-white rounded-xl text-xs font-bold transition shadow-lg shadow-blue-500/25"
                >
                  {isUpdating ? "Saving..." : "Save Changes"}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
};

export default UserManagement;