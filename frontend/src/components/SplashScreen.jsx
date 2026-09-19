import { useEffect } from "react";

export default function SplashScreen({ onFinish }) {

  useEffect(() => {
    const timer = setTimeout(() => {
      onFinish();
    }, 3000);

    return () => clearTimeout(timer);
  }, [onFinish]);

  return (
    <div className="fixed inset-0 bg-[#020817] flex flex-col justify-center items-center">

      {/* Logo */}
      <div className="text-6xl mb-5">🎓</div>

      {/* Project Name */}
      <h1 className="text-5xl font-bold text-white">
        Student360
      </h1>

      {/* Subtitle */}
      <p className="text-gray-400 mt-3">
        AI-Based Student Behaviour Detection System
      </p>

      {/* Loading */}
      <div className="mt-10 w-64 h-2 bg-gray-700 rounded-full overflow-hidden">

        <div
          className="h-full bg-blue-500 animate-pulse"
          style={{ width: "100%" }}
        ></div>

      </div>

      <p className="text-blue-400 mt-4">
        Loading...
      </p>

    </div>
  );
}