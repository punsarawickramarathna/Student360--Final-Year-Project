import Navbar from "../../components/Navbar";
import { useNavigate } from "react-router-dom";
export default function Profile() {

  // 🔹 Get logged-in user from localStorage
  const student = JSON.parse(localStorage.getItem("user")) || {};
  const navigate = useNavigate();
  return (
    <div className="min-h-screen bg-[#071a2c] text-white">

      <Navbar />

      <div className="max-w-3xl mx-auto p-8">

        <h1 className="text-3xl font-bold mb-6">
          Student Profile
        </h1>

        {/* PROFILE CARD */}
        <div className="bg-[#0b2236] p-6 rounded-xl shadow-lg">

          {/* PHOTO SECTION */}
          <div className="flex items-center gap-6 mb-6">

            <img
              src={
                student.photo
                  ? student.photo
                  : "https://cdn-icons-png.flaticon.com/512/3135/3135715.png"
              }
              alt="profile"
              className="w-28 h-28 rounded-full border-2 border-blue-500 object-cover"
            />

            <div>
              <h2 className="text-xl font-bold">
                {student?.name}
              </h2>
              <p className="text-green-400">
                Student Active ✔
              </p>
              <p className="text-gray-400">
                {student?.reg}
              </p>
            </div>

          </div>

          {/* DETAILS */}
          <div className="space-y-3 text-lg">
              <p>
              <b>Student ID :</b> {student.student_id}
            </p>

            <p>
              <b>Department:</b>  {student.department || "Information Technology"}

            </p>

            <p>
              <b>Year:</b> {student.year || "4"}
            </p>
            <p>

            <b>Intake :</b>{student.intake || "11"}
            </p>
            <p>
              <b>Email:</b> {student?.email}
            </p>

            <p>
              <b>Phone:</b> {student?.phone || ""}
            </p>

          </div>
          <button
            onClick={() => window.location.href = "/student/edit-profile"}
            className="mt-6 bg-blue-600 hover:bg-blue-700 px-5 py-2 rounded-lg"
          >
            Edit Profile
          </button>
        </div>

      </div>

    </div>
  );
}

