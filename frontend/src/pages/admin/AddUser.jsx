import { useState } from "react";
import Navbar from "../../components/Navbar";
import { registerUser } from "../../api/api";

export default function AddUser() {

  const [studentId, setStudentId] = useState("");
  const [name, setName] = useState("");
  const [intake, setIntake] = useState("");
  const [password, setPassword] = useState("");

  // Video states
  const [videoPreview, setVideoPreview] = useState(null);

  // Upload Preview
  const handleVideoUpload = (e) => {

    const file = e.target.files[0];

    if (!file) return;

    setVideoPreview(URL.createObjectURL(file));

  };

  // Register User
  const addUser = async () => {

    if (
      !studentId ||
      !name ||
      !intake ||
      !password
    ) {

      alert("Fill all fields");

      return;

    }

    try {

      const res = await registerUser({

        student_id: studentId,

        name: name,

        intake: intake,

        password: password,

        role: "student"

      });

      if (res.detail) {

        alert(res.detail);

        return;

      }

      alert("Student Registered Successfully");

      setStudentId("");
      setName("");
      setIntake("");
      setPassword("");

      setVideoPreview(null);

    } catch (err) {

      console.log(err);

      alert("Server Error");

    }

  };

  return (

    <div className="min-h-screen bg-[#071a2c]">

      <Navbar />

      <div className="max-w-xl mx-auto mt-10 bg-[#0b2236] p-8 rounded-xl">

        <h1 className="text-2xl font-bold text-white mb-6">

          Add Student

        </h1>

        <input

          className="w-full p-3 mb-3 rounded text-black"

          placeholder="Student ID"

          value={studentId}

          onChange={(e)=>setStudentId(e.target.value)}

        />

        <input

          className="w-full p-3 mb-3 rounded text-black"

          placeholder="Student Name"

          value={name}

          onChange={(e)=>setName(e.target.value)}

        />

        <input

          className="w-full p-3 mb-3 rounded text-black"

          placeholder="Intake"

          value={intake}

          onChange={(e)=>setIntake(e.target.value)}

        />

        <input

          type="password"

          className="w-full p-3 mb-4 rounded text-black"

          placeholder="Password"

          value={password}

          onChange={(e)=>setPassword(e.target.value)}

        />

        <div className="mb-4">

          <p className="text-white mb-2">

            Upload Student Video (Optional)

          </p>

          <input

            type="file"

            accept="video/*"

            onChange={handleVideoUpload}

            className="text-white"

          />

        </div>

        {

          videoPreview && (

            <video

              src={videoPreview}

              controls

              className="w-full rounded mb-4"

            />

          )

        }

        <button

          onClick={addUser}

          className="w-full bg-green-600 p-3 rounded text-white text-lg"

        >

          Register Student

        </button>

      </div>

    </div>

  );

}