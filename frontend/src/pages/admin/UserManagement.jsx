import React, { useState, useEffect } from 'react';
import axios from 'axios';

const UserManagement = () => {
  const [activeTab, setActiveTab] = useState('students');
  const [students, setStudents] = useState([]);
  const [lecturers, setLecturers] = useState([]);
  const [loading, setLoading] = useState(true);

  const fetchUsers = async () => {
    try {
      setLoading(true);
      const res = await axios.get('http://localhost:8000/api/users/all');
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

  const handleDelete = async (userType, id) => {
    if (window.confirm(`Are you sure you want to delete this ${userType}?`)) {
      try {
        await axios.delete(`http://localhost:8000/api/users/${userType}/${id}`);
        fetchUsers(); // Refresh the list after deletion
      } catch (err) {
        alert("Error deleting user.");
      }
    }
  };

  if (loading) return <div className="text-white p-4">Loading users...</div>;

  return (
    <div className="bg-[#0f172a] p-6 rounded-xl text-white">
      {/* Tabs */}
      <div className="flex space-x-4 mb-6 border-b border-gray-700 pb-2">
        <button
          onClick={() => setActiveTab('students')}
          className={`px-4 py-2 rounded-md font-semibold transition-colors ${activeTab === 'students' ? 'bg-blue-600 text-white' : 'text-gray-400 hover:text-white'}`}
        >
          Students ({students.length})
        </button>
        <button
          onClick={() => setActiveTab('lecturers')}
          className={`px-4 py-2 rounded-md font-semibold transition-colors ${activeTab === 'lecturers' ? 'bg-blue-600 text-white' : 'text-gray-400 hover:text-white'}`}
        >
          Lecturers ({lecturers.length})
        </button>
      </div>

      {/* Students Table */}
      {activeTab === 'students' && (
        <div className="overflow-x-auto">
          <table className="w-full text-left border-collapse">
            <thead>
              <tr className="bg-gray-800 text-gray-300">
                <th className="p-3 rounded-tl-lg">ID</th>
                <th className="p-3">Name</th>
                <th className="p-3">Email</th>
                <th className="p-3">Intake</th>
                <th className="p-3">AI Model</th>
                <th className="p-3 rounded-tr-lg">Actions</th>
              </tr>
            </thead>
            <tbody>
              {students.map((student) => (
                <tr key={student._id} className="border-b border-gray-800 hover:bg-gray-800/50">
                  <td className="p-3 font-mono text-sm">{student.student_id}</td>
                  <td className="p-3">{student.name}</td>
                  <td className="p-3 text-sm text-gray-400">{student.email}</td>
                  <td className="p-3">{student.intake}</td>
                  <td className="p-3">
                    <span className={`px-2 py-1 rounded text-xs ${student.is_model_trained ? 'bg-green-500/20 text-green-400' : 'bg-yellow-500/20 text-yellow-400'}`}>
                      {student.is_model_trained ? 'Trained' : 'Pending'}
                    </span>
                  </td>
                  <td className="p-3 space-x-2">
                    <button className="px-3 py-1 bg-gray-700 hover:bg-gray-600 rounded text-sm transition-colors">Edit</button>
                    <button onClick={() => handleDelete('student', student._id)} className="px-3 py-1 bg-red-600 hover:bg-red-700 rounded text-sm transition-colors">Delete</button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {/* Lecturers Table */}
      {activeTab === 'lecturers' && (
        <div className="overflow-x-auto">
          <table className="w-full text-left border-collapse">
            <thead>
              <tr className="bg-gray-800 text-gray-300">
                <th className="p-3 rounded-tl-lg">Name</th>
                <th className="p-3">Email</th>
                <th className="p-3">Department</th>
                <th className="p-3 rounded-tr-lg">Actions</th>
              </tr>
            </thead>
            <tbody>
              {lecturers.map((lecturer) => (
                <tr key={lecturer._id} className="border-b border-gray-800 hover:bg-gray-800/50">
                  <td className="p-3">{lecturer.name}</td>
                  <td className="p-3 text-sm text-gray-400">{lecturer.email}</td>
                  <td className="p-3">{lecturer.department}</td>
                  <td className="p-3 space-x-2">
                    <button className="px-3 py-1 bg-gray-700 hover:bg-gray-600 rounded text-sm transition-colors">Edit</button>
                    <button onClick={() => handleDelete('lecturer', lecturer._id)} className="px-3 py-1 bg-red-600 hover:bg-red-700 rounded text-sm transition-colors">Delete</button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
};

export default UserManagement;