import { useEffect } from "react";

export default function SplashScreen({ onFinish }) {
  useEffect(() => {
    const timer = setTimeout(() => {
      onFinish();
    }, 3000);

    return () => clearTimeout(timer);
  }, [onFinish]);

  return (
    <div className="fixed inset-0 flex items-center justify-center bg-slate-50 px-4 z-50">

      {/* Clean White Card */}
      <div className="w-full max-w-md p-8 sm:p-10 rounded-3xl bg-white border border-slate-200/80 shadow-xl flex flex-col items-center text-center">

        {/* Horizon Campus Logo */}
        <div className="mb-4">
          <img
            src="/assets/horizon-logo.png"
            alt="Horizon Campus"
            className="h-24 w-auto object-contain mx-auto drop-shadow-sm"
          />
        </div>

        {/* Sub Header */}
        <h2 className="text-xs sm:text-sm font-bold text-slate-500 tracking-wider uppercase">
          Welcome to Horizon Campus
        </h2>

        {/* Project Name */}
        <h1 className="text-4xl sm:text-5xl font-black text-slate-900 mt-2 tracking-tight">
          Student<span className="text-blue-600">360</span>
        </h1>

        {/* Subtitle */}
        <p className="text-xs sm:text-sm text-slate-500 font-medium mt-2 mb-8">
          AI-Based Student Behaviour Detection System
        </p>

        {/* Modern Clean Loading Bar */}
        <div className="w-64 h-2 bg-slate-100 rounded-full overflow-hidden border border-slate-200">
          <div
            className="h-full bg-blue-600 animate-pulse"
            style={{ width: "100%" }}
          ></div>
        </div>

        <p className="text-xs text-blue-600 font-bold mt-4 tracking-wide">
          Loading...
        </p>

      </div>
    </div>
  );
}