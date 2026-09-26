import { useNavigate } from "react-router-dom";

export default function RoleSelection() {
  const navigate = useNavigate();

  const selectRole = (role) => {
    localStorage.setItem("selectedRole", role);
    navigate("/login");
  };

  return (
    <div
      className="relative min-h-screen w-full flex items-center justify-center bg-cover bg-center bg-no-repeat overflow-hidden px-4 py-8"
      style={{
        backgroundImage: `url('/assets/horizon-campus-bg.jpg')`,
      }}
    >
      {/* Qhana chhiwphi overlay */}
      <div className="absolute inset-0 bg-black/15 backdrop-blur-[5px]"></div>

      {/* Janq'u glassmorphism tarjeta, juk'a chhiwkhimpi */}
      <div className="relative z-10 w-full max-w-lg p-8 sm:p-10 rounded-3xl bg-white/75 backdrop-blur-md border border-white/80 shadow-lg flex flex-col items-center text-center">

        {/* Horizon Campus Logo llikampi */}
        <a
          href="https://horizoncampus.edu.lk/"
          target="_blank"
          rel="noopener noreferrer"
          className="transition-transform hover:scale-105 duration-200 cursor-pointer mb-5"
          title="Horizon Campus"
        >
          <img
            src="/assets/horizon-logo.png"
            alt="Horizon Campus"
            className="h-28 w-auto object-contain drop-shadow-sm"
          />
        </a>

        {/* Qillqanaka */}
        <h2 className="text-lg sm:text-xl font-bold text-slate-800 tracking-wider uppercase">
          Welcome to Horizon Campus
        </h2>

        <h1 className="text-4xl sm:text-5xl font-black text-slate-900 mt-4 tracking-tight">
          Student<span className="text-blue-600">360</span>
        </h1>

        {/* Jisk'aptata pacha */}
        <p className="text-xs sm:text-sm text-slate-600 font-medium mt-4 mb-6">
          Choose your role to continue
        </p>

        {/* Botonanak kasta ajlliñataki */}
        <div className="grid grid-cols-3 gap-3.5 w-full">

          {/* Yatiqiri (Student) */}
          <div
            onClick={() => selectRole("student")}
            className="group cursor-pointer bg-white/85 hover:bg-white p-4 rounded-2xl border border-white shadow-sm hover:shadow-md hover:-translate-y-1 transition-all duration-200 flex flex-col items-center justify-center"
          >
            <div className="text-3xl sm:text-4xl group-hover:scale-110 transition-transform">
              🎓
            </div>
            <h3 className="text-slate-800 text-xs sm:text-sm font-semibold mt-2 group-hover:text-blue-600">
              Student
            </h3>
          </div>

          {/* Yatichiri (Lecturer) */}
          <div
            onClick={() => selectRole("lecturer")}
            className="group cursor-pointer bg-white/85 hover:bg-white p-4 rounded-2xl border border-white shadow-sm hover:shadow-md hover:-translate-y-1 transition-all duration-200 flex flex-col items-center justify-center"
          >
            <div className="text-3xl sm:text-4xl group-hover:scale-110 transition-transform">
              👨‍🏫
            </div>
            <h3 className="text-slate-800 text-xs sm:text-sm font-semibold mt-2 group-hover:text-blue-600">
              Lecturer
            </h3>
          </div>

          {/* Sarayiri (Admin) */}
          <div
            onClick={() => selectRole("admin")}
            className="group cursor-pointer bg-white/85 hover:bg-white p-4 rounded-2xl border border-white shadow-sm hover:shadow-md hover:-translate-y-1 transition-all duration-200 flex flex-col items-center justify-center"
          >
            <div className="text-3xl sm:text-4xl group-hover:scale-110 transition-transform">
              👨‍💼
            </div>
            <h3 className="text-slate-800 text-xs sm:text-sm font-semibold mt-2 group-hover:text-blue-600">
              Admin
            </h3>
          </div>

        </div>

      </div>

    </div>
  );
}