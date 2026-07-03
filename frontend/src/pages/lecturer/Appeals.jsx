import { useEffect, useState } from "react";
import { getAppeals } from "../../api/api";

export default function Appeals() {

  const [appeals, setAppeals] = useState([]);

  // Load appeals when page opens
  useEffect(() => {

    async function load() {

      try {

        const res = await getAppeals();

        setAppeals(res.data);

      } catch (err) {

        console.log(err);

      }

    }

    load();

  }, []);

  return (

    <div className="min-h-screen p-8 text-white">

      <h1 className="text-3xl font-bold mb-6">

        Student Appeals

      </h1>

      {appeals.length === 0 ? (

        <div className="bg-[#0b2236] p-5 rounded-lg">

          No appeals submitted.

        </div>

      ) : (

        appeals.map((appeal, index) => (

          <div
            key={index}
            className="bg-[#0b2236] rounded-xl p-5 mb-4 shadow"
          >

            <h2 className="text-xl font-semibold">

              {appeal.student_id}

            </h2>

            <p className="mt-2">

              <strong>Type:</strong> {appeal.type}

            </p>

            <p className="mt-2">

              <strong>Message:</strong>

            </p>

            <p className="bg-[#071828] p-3 rounded mt-1">

              {appeal.message}

            </p>

            <p className="mt-3">

              <strong>Status:</strong>

              <span
                className={`ml-2 px-3 py-1 rounded ${
                  appeal.status === "Pending"
                    ? "bg-yellow-600"
                    : "bg-green-600"
                }`}
              >

                {appeal.status}

              </span>

            </p>

            <p className="text-sm text-gray-400 mt-3">

              {appeal.created_at}

            </p>

          </div>

        ))

      )}

    </div>

  );

}