import { useNavigate } from "react-router-dom";

export default function RoleSelection() {

  const navigate = useNavigate();

  const selectRole = (role) => {
    localStorage.setItem("selectedRole", role);
    navigate("/login");
  };

  return (
    <div className="min-h-screen bg-[#08111f] flex items-center justify-center">

      <div className="text-center">

        <h1 className="text-5xl font-bold text-white">
          Student360
        </h1>

        <p className="text-gray-400 mt-3 mb-10">
          Choose your role to continue
        </p>

        <div className="grid md:grid-cols-3 gap-8">

          <div
            onClick={() => selectRole("student")}
            className="cursor-pointer bg-[#122232] p-8 rounded-xl hover:scale-105 transition"
          >
            <div className="text-6xl">🎓</div>
            <h2 className="text-white text-2xl mt-4">Student</h2>
          </div>

          <div
            onClick={() => selectRole("lecturer")}
            className="cursor-pointer bg-[#122232] p-8 rounded-xl hover:scale-105 transition"
          >
            <div className="text-6xl">👨‍🏫</div>
            <h2 className="text-white text-2xl mt-4">Lecturer</h2>
          </div>

          <div
            onClick={() => selectRole("admin")}
            className="cursor-pointer bg-[#122232] p-8 rounded-xl hover:scale-105 transition"
          >
            <div className="text-6xl">👨‍💼</div>
            <h2 className="text-white text-2xl mt-4">Admin</h2>
          </div>

        </div>

      </div>

    </div>
  );
}