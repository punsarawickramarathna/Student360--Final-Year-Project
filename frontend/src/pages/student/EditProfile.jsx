import { useState } from "react";
import { useNavigate } from "react-router-dom";
import Navbar from "../../components/Navbar";
import { updateProfile } from "../../api/api";

export default function EditProfile() {

    

    const user = JSON.parse(localStorage.getItem("user"));

    const [name, setName] = useState(user.name || "");
    const [department, setDepartment] = useState(user.department || "");
    const [year, setYear] = useState(user.year || "");
    const [intake, setIntake] = useState(user.intake || "");
    const [email, setEmail] = useState(user.email || "");
    const [phone, setPhone] = useState(user.phone || "");
    


         const handleUpdate = async () => {

            const res = await updateProfile(user.student_id, {
            name,
            department,
            year,
            intake,
            email,
            phone

        });

        if (res.message) {
            alert("Profile Updated");

    // update local storage
        localStorage.setItem("user", JSON.stringify({
            ...user,
            name,
            department,
            year,
            intake,
            email,
            phone
        }));
    }
};
    return (

        <div className="min-h-screen bg-[#020817] text-white">

            <Navbar />

            <div className="max-w-xl mx-auto mt-10 bg-[#0b2236] p-8 rounded-xl">

                <h1 className="text-3xl font-bold mb-6">

                    Edit Profile

                </h1>

                <input
                    className="w-full p-3 rounded mb-4 text-black"
                    placeholder="Full Name"
                    value={name}
                    onChange={(e)=>setName(e.target.value)}
                />

                <input
                    className="w-full p-3 rounded mb-4 text-black"
                    placeholder="Department"
                    value={department}
                    onChange={(e)=>setDepartment(e.target.value)}
                />

                <input
                    className="w-full p-3 rounded mb-4 text-black"
                    placeholder="Year"
                    value={year}
                    onChange={(e)=>setYear(e.target.value)}
                />
                <input
                    className="w-full p-3 rounded mb-4 text-black"
                    placeholder="Intake"
                    value={intake}
                    onChange={(e)=>setIntake(e.target.value)}
                />

                <input
                    className="w-full p-3 rounded mb-4 text-black"
                    placeholder="Email"
                    value={email}
                    onChange={(e)=>setEmail(e.target.value)}
                />

                <input
                    className="w-full p-3 rounded mb-4 text-black"
                    placeholder="Phone"
                    value={phone}
                    onChange={(e)=>setPhone(e.target.value)}
                />


                <button
                    onClick={handleUpdate}
                    className="w-full bg-green-600 hover:bg-green-700 py-3 rounded-lg"
                >
                    Save Changes
                </button>

            </div>

        </div>

    );

}