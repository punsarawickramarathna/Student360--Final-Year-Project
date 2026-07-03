// src/App.js
import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import Login from "./pages/Login";
import RequireAuth from "./components/RequireAuth";
import AppealForm from "./pages/student/AppealForm";
import AppealsList from "./pages/student/AppealsList";
import Profile from "./pages/student/Profile";
import StudentAppeals from "./pages/student/Appeals";
import LecturerAppeals from "./pages/lecturer/Appeals";

import ClassroomSelect from "./pages/lecturer/ClassroomSelect";
import AddUser from "./pages/admin/AddUser";
import EditProfile from "./pages/student/EditProfile";




// student
import StudentDashboard from "./pages/student/Dashboard";
// lecturer
import LecturerDashboard from "./pages/lecturer/Dashboard";
// admin
import AdminDashboard from "./pages/admin/Dashboard";

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<Navigate to="/login" replace />} />
        <Route path="/login" element={<Login />} />

        <Route path="/student/dashboard" element={
          <RequireAuth allowedRoles={["student"]}><StudentDashboard /></RequireAuth>
        } />

        <Route path="/student/appeals" element={<StudentAppeals />} />

        <Route path="/lecturer/appeals" element={<LecturerAppeals />} />


        <Route path="/lecturer/classroom" element={<ClassroomSelect/>}/>
        

        <Route path="/admin/add-user" element={<AddUser />} />

        <Route path="/" element={<Login />} />

        <Route path="/student/dashboard" element={<StudentDashboard />} />

          <Route path="/student/profile" element={<Profile />} />

        <Route path="/lecturer/dashboard" element={
          <RequireAuth allowedRoles={["lecturer"]}><LecturerDashboard /></RequireAuth>
        } />
        <Route path="/student/appeals" element={<RequireAuth allowedRoles={["student"]}><AppealsList /></RequireAuth>} />
        <Route path="/student/appeal/new" element={<RequireAuth allowedRoles={["student"]}><AppealForm onSubmitted={() => window.location.href = "/student/appeals"} /></RequireAuth>} />
        <Route path="/admin/dashboard" element={
          <RequireAuth allowedRoles={["admin"]}><AdminDashboard /></RequireAuth>
        } />

        <Route path="*" element={<div className="p-8">404 - Not Found</div>} />
        <Route path="/student/profile" element={<Profile />} />
        <Route
    path="/student/edit-profile"
    element={<EditProfile />}
/>
      </Routes>
    </BrowserRouter>
  );
}
