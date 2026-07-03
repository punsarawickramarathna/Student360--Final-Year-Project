import { useState } from "react";
import { useNavigate } from "react-router-dom";

export default function ClassroomSelect() {

const nav = useNavigate();

const [year,setYear]=useState("");
const [sem,setSem]=useState("");
const [subject,setSubject]=useState("");
const [group,setGroup]=useState("");

const submit=()=>{

if(!year||!sem||!subject||!group){
alert("Fill all fields");
return;
}

localStorage.setItem("classroom",
JSON.stringify({year,sem,subject,group}));

nav("/lecturer/dashboard");
};

return(

<div className="min-h-screen flex justify-center items-center">

<div className="bg-[#0b2236] text-white p-8 rounded-xl w-[380px]">

<h2 className="text-xl mb-4">Select Classroom</h2>

<select onChange={e=>setYear(e.target.value)} className="w-full mb-2 p-2 bg-black">
<option value="">Year</option>
<option>1</option>
<option>2</option>
<option>3</option>
<option>4</option>
</select>

<select onChange={e=>setSem(e.target.value)} className="w-full mb-2 p-2 bg-black">
<option value="">Semester</option>
<option>1</option>
<option>2</option>
</select>

<input placeholder="Subject" onChange={e=>setSubject(e.target.value)} className="w-full mb-2 p-2 bg-black"/>

<select onChange={e=>setGroup(e.target.value)} className="w-full mb-4 p-2 bg-black">
<option value="">Group</option>
<option>A</option>
<option>B</option>
<option>C</option>
</select>

<button onClick={submit} className="bg-blue-600 w-full p-2 rounded">
Load Classroom
</button>

</div>

</div>
);
}
