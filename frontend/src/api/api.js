// src/api/api.js

const API = "http://127.0.0.1:8000";

// ---------------------------------
// Common response handler
// ---------------------------------

const handleResponse = async (response) => {
  let data = {};

  try {
    data = await response.json();
  } catch {
    data = {};
  }

  if (!response.ok) {
    throw {
      status: response.status,
      response: {
        data,
      },
      message:
        data.detail ||
        data.message ||
        "Request failed",
    };
  }

  return data;
};

// ---------------------------------
// Authorization header
// ---------------------------------

const getAuthHeaders = () => {
  const token = localStorage.getItem("token");

  return {
    Authorization: `Bearer ${token}`,
  };
};

// ---------------------------------
// Login
// ---------------------------------

export const loginUser = async (body) => {
  const response = await fetch(`${API}/login`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(body),
  });

  return handleResponse(response);
};

// ---------------------------------
// Register user
// ---------------------------------

export const registerUser = async (body) => {
  const response = await fetch(`${API}/register`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(body),
  });

  return handleResponse(response);
};

// ---------------------------------
// Students
// ---------------------------------

export const getStudents = async () => {
  const response = await fetch(`${API}/students`);

  return handleResponse(response);
};

// ---------------------------------
// Attendance
// ---------------------------------

export const getAttendance = async () => {
  const response = await fetch(`${API}/attendance`);

  return handleResponse(response);
};

// ---------------------------------
// Behavior
// ---------------------------------

export const getBehavior = async () => {
  const response = await fetch(`${API}/behavior`);

  return handleResponse(response);
};

// ---------------------------------
// Appeals
// ---------------------------------

export const getAppeals = async () => {
  const response = await fetch(`${API}/appeals`);

  return handleResponse(response);
};

export const submitAppeal = async (body) => {
  const response = await fetch(`${API}/appeals`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      ...getAuthHeaders(),
    },
    body: JSON.stringify(body),
  });

  return handleResponse(response);
};

// ---------------------------------
// Sessions
// ---------------------------------

export const getSessions = async () => {
  const response = await fetch(`${API}/sessions`);

  return handleResponse(response);
};

// ---------------------------------
// Evidence
// ---------------------------------

export const getEvidence = async (studentId) => {
  const response = await fetch(
    `${API}/evidence/${studentId}`
  );

  return handleResponse(response);
};

// ---------------------------------
// Email
// ---------------------------------

export const sendEmail = async (body) => {
  const response = await fetch(`${API}/send-email`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      ...getAuthHeaders(),
    },
    body: JSON.stringify(body),
  });

  return handleResponse(response);
};

// ---------------------------------
// Session CSV upload
// ---------------------------------

export const uploadSessionCSV = async (file) => {
  const formData = new FormData();

  formData.append("file", file);

  const response = await fetch(
    `${API}/upload-session`,
    {
      method: "POST",
      headers: {
        ...getAuthHeaders(),
      },
      body: formData,
    }
  );

  return handleResponse(response);
};

// ---------------------------------
// Get logged-in user profile
// ---------------------------------

export const getMyProfile = async () => {
  const response = await fetch(`${API}/profile/me`, {
    method: "GET",
    headers: {
      ...getAuthHeaders(),
    },
  });

  return handleResponse(response);
};

// ---------------------------------
// Update logged-in user profile
// ---------------------------------

export const updateMyProfile = async (body) => {
  const response = await fetch(`${API}/profile/me`, {
    method: "PUT",
    headers: {
      "Content-Type": "application/json",
      ...getAuthHeaders(),
    },
    body: JSON.stringify(body),
  });

  return handleResponse(response);
};

// ---------------------------------
// Upload profile image
// ---------------------------------

export const uploadProfileImage = async (file) => {
  const formData = new FormData();

  formData.append("file", file);

  const response = await fetch(
    `${API}/profile/photo`,
    {
      method: "POST",
      headers: {
        ...getAuthHeaders(),
      },
      body: formData,
    }
  );

  return handleResponse(response);
};

// ---------------------------------
// Delete profile image
// ---------------------------------

export const deleteProfileImage = async () => {
  const response = await fetch(
    `${API}/profile/photo`,
    {
      method: "DELETE",
      headers: {
        ...getAuthHeaders(),
      },
    }
  );

  return handleResponse(response);
};

// ---------------------------------
// Change password
// ---------------------------------

export const changePassword = async (body) => {
  const response = await fetch(
    `${API}/profile/change-password`,
    {
      method: "PUT",
      headers: {
        "Content-Type": "application/json",
        ...getAuthHeaders(),
      },
      body: JSON.stringify(body),
    }
  );

  return handleResponse(response);
};

// ---------------------------------
// Convert backend image path
// ---------------------------------

export const getImageURL = (photoPath) => {
  if (!photoPath) {
    return "";
  }

  if (
    photoPath.startsWith("http://") ||
    photoPath.startsWith("https://")
  ) {
    return photoPath;
  }

  const cleanPath = photoPath
    .replace(/\\/g, "/")
    .replace(/^\/+/, "");

  return `${API}/${cleanPath}`;
};