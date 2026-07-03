import { useState } from "react";
import { submitAppeal } from "../../api/api";

export default function Appeals() {

  const [message, setMessage] = useState("");

  const [type, setType] = useState("Behavior");

  const submit = async () => {

    if (!message) {

      alert("Enter appeal");

      return;
    }

    const user = JSON.parse(localStorage.getItem("user"));

    try {

      await submitAppeal({

        student_id: user.student_id,

        message: message,

        type: type

      });

      alert("Appeal Submitted Successfully");

      setMessage("");

    } catch (err) {

      console.log(err);

      alert("Error submitting appeal");

    }

  };

  return (

    <div className="p-8 text-white">

      <h1 className="text-2xl font-bold mb-4">
        Submit Appeal
      </h1>

      <div className="bg-[#0b2236] p-6 rounded-xl">

        <label>Appeal Type</label>

        <select
          className="w-full bg-black p-3 rounded mt-2 mb-4"
          value={type}
          onChange={(e)=>setType(e.target.value)}
        >
          <option>Behavior</option>
          <option>Attendance</option>
          <option>Exam</option>
        </select>

        <textarea

          className="w-full bg-black p-3 rounded"

          rows="6"

          placeholder="Write your appeal..."

          value={message}

          onChange={(e)=>setMessage(e.target.value)}

        />

        <button

          onClick={submit}

          className="mt-4 bg-blue-600 px-6 py-2 rounded"

        >

          Submit Appeal

        </button>

      </div>

    </div>

  );

}