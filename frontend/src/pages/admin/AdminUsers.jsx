// src/pages/admin/AdminUsers.jsx

import React from "react";
import Navbar from "../../components/Navbar";
import UserManagement from "./UserManagement";

export default function AdminUsers() {
    return (
        <div className="min-h-screen bg-[#070d18] text-gray-100 font-sans pb-16">
            <Navbar />

            <main className="max-w-7xl mx-auto px-6 pt-8 space-y-6">
                {/* Header Banner */}
                <section className="bg-gradient-to-r from-[#111c33] via-[#0d1629] to-[#111c33] border border-gray-800 rounded-3xl p-7 shadow-2xl relative overflow-hidden">
                    <div className="absolute -top-20 -right-20 w-80 h-80 bg-blue-500/10 rounded-full blur-3xl pointer-events-none" />

                    <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 relative z-10">
                        <div>
                            <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-blue-500/15 border border-blue-500/30 text-blue-400 text-xs font-bold uppercase tracking-wider mb-2">
                                <span className="w-1.5 h-1.5 rounded-full bg-blue-400 animate-pulse" />
                                Administrative Access
                            </div>
                            <h1 className="text-3xl font-extrabold text-white tracking-tight">
                                User Management Portal
                            </h1>
                            <p className="text-sm text-gray-400 mt-1">
                                Manage and register students, lecturers, and facial biometric profiles.
                            </p>
                        </div>
                    </div>
                </section>

                {/* UserManagement Component එක මෙතනින් පෙන්වනවා */}
                <section className="bg-[#111a2e] border border-gray-800 rounded-3xl p-6 shadow-2xl">
                    <UserManagement />
                </section>
            </main>
        </div>
    );
}