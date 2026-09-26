// src/App.js

import { useState } from "react";
import {
  BrowserRouter,
  Routes,
  Route,
  Navigate,
} from "react-router-dom";

import SplashScreen from "./components/SplashScreen";
import RequireAuth from "./components/RequireAuth";

// General pages
import RoleSelection from "./pages/RoleSelection";
import Login from "./pages/Login";

// Student pages
import StudentDashboard from "./pages/student/Dashboard";
import AppealForm from "./pages/student/AppealForm";
import AppealsList from "./pages/student/AppealsList";
import Profile from "./pages/student/Profile";
import EditProfile from "./pages/student/EditProfile";
import ChangePassword from "./pages/student/ChangePassword";

// Lecturer pages
import LecturerDashboard from "./pages/lecturer/Dashboard";
import LecturerAppeals from "./pages/lecturer/Appeals";
import ClassroomSelect from "./pages/lecturer/ClassroomSelect";

// Admin pages
import AdminDashboard from "./pages/admin/Dashboard";
import AddUser from "./pages/admin/AddUser";

export default function App() {
  const [loading, setLoading] = useState(true);

  if (loading) {
    return <SplashScreen onFinish={() => setLoading(false)} />;
  }

  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<Navigate to="/roles" replace />} />
        <Route path="/roles" element={<RoleSelection />} />
        <Route path="/login" element={<Login />} />

        {/* Student routes */}
        <Route path="/student/dashboard" element={<RequireAuth allowedRoles={["student"]}><StudentDashboard /></RequireAuth>} />
        <Route path="/student/profile" element={<RequireAuth allowedRoles={["student"]}><Profile /></RequireAuth>} />
        <Route path="/student/edit-profile" element={<RequireAuth allowedRoles={["student"]}><EditProfile /></RequireAuth>} />
        <Route path="/student/appeals" element={<RequireAuth allowedRoles={["student"]}><AppealsList /></RequireAuth>} />
        <Route path="/student/appeal/new" element={<RequireAuth allowedRoles={["student"]}><AppealForm onSubmitted={() => { window.location.href = "/student/appeals"; }} /></RequireAuth>} />
        <Route path="/student/change-password" element={<RequireAuth allowedRoles={["student"]}><ChangePassword /></RequireAuth>} />

        {/* Lecturer routes */}
        <Route path="/lecturer/dashboard" element={<RequireAuth allowedRoles={["lecturer"]}><LecturerDashboard /></RequireAuth>} />
        <Route path="/lecturer/appeals" element={<RequireAuth allowedRoles={["lecturer"]}><LecturerAppeals /></RequireAuth>} />
        <Route path="/lecturer/classroom" element={<RequireAuth allowedRoles={["lecturer"]}><ClassroomSelect /></RequireAuth>} />

        {/* Admin routes */}
        {/* FIX: Add this redirect so /admin goes to /admin/dashboard automatically */}
        <Route path="/admin" element={<Navigate to="/admin/dashboard" replace />} />
        
        <Route path="/admin/dashboard" element={<RequireAuth allowedRoles={["admin"]}><AdminDashboard /></RequireAuth>} />
        <Route path="/admin/add-user" element={<RequireAuth allowedRoles={["admin"]}><AddUser /></RequireAuth>} />

        {/* 404 route */}
        <Route path="*" element={
          <div className="min-h-screen bg-[#08111f] text-white flex items-center justify-center">
            <div className="text-center">
              <h1 className="text-4xl font-bold">404</h1>
              <p className="mt-3 text-gray-400">Page Not Found</p>
            </div>
          </div>
        } />
      </Routes>
    </BrowserRouter>
  );
}