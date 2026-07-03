const API = "http://127.0.0.1:8000";

// Login
export const loginUser = async (body) => {
  const res = await fetch(`${API}/login`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(body),
  });

  return await res.json();
};

// Students
export const getStudents = async () => {
  const res = await fetch(`${API}/students`);
  return await res.json();
};

// Attendance
export const getAttendance = async () => {
  const res = await fetch(`${API}/attendance`);
  return await res.json();
};

// Behavior
export const getBehavior = async () => {
  const res = await fetch(`${API}/behavior`);
  return await res.json();
};

// Appeals
export const getAppeals = async () => {
  const res = await fetch(`${API}/appeals`);
  return await res.json();
};

export const submitAppeal = async (body) => {
  const res = await fetch(`${API}/appeals`, {
    method: "POST",
    headers: {
      "Content-Type":"application/json"
    },
    body:JSON.stringify(body)
  });

  return await res.json();
};

// Register User
export const registerUser = async (body)=>{
    const res=await fetch(`${API}/register`,{
        method:"POST",
        headers:{
            "Content-Type":"application/json"
        },
        body:JSON.stringify(body)
    });

    return await res.json();
}

// Sessions
export const getSessions = async () => {

    const res = await fetch(`${API}/sessions`);

    return await res.json();

};

export const getEvidence = async (student_id) => {

    const res = await fetch(
        `http://127.0.0.1:8000/evidence/${student_id}`
    );

    return await res.json();
};

export const sendEmail = async (body) => {

    const res = await fetch(`${API}/send-email`, {

        method: "POST",

        headers: {

            "Content-Type": "application/json"

        },

        body: JSON.stringify(body)

    });

    return await res.json();

};

export const uploadSessionCSV = async (file) => {
  const formData = new FormData();
  formData.append("file", file);

  const res = await fetch(`${API}/upload-session`, {
    method: "POST",
    body: formData,
  });

  return await res.json();
};

export const uploadProfileImage = async (file) => {

  const formData = new FormData();
  formData.append("file", file);

  const res = await fetch("http://127.0.0.1:8000/upload-profile-image", {
    method: "POST",
    body: formData
  });

  return await res.json();
};

export const updateProfile = async (student_id, body) => {
  const res = await fetch(`${API}/update-profile/${student_id}`, {
    method: "PUT",
    headers: {
      "Content-Type": "application/json"
    },
    body: JSON.stringify(body)
  });

  return await res.json();
};
