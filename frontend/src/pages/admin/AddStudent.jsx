import { useState } from "react";
import axios from "axios";

export default function AddStudent(){

const [studentId,setId] = useState("");
const [studentName,setName] = useState("");
const [intake,setIntake] = useState("");
const [password,setPassword] = useState("");

const addStudent = async () => {

try{

await axios.post("http://localhost:5000/api/addStudent",{
studentId,
studentName,
intake,
password
});

alert("Student Added");

}catch(err){

console.log(err);

}

};

return(

<div style={{padding:"20px"}}>

<h2>Add Student</h2>

<input placeholder="Student ID"
onChange={(e)=>setId(e.target.value)} />

<br/>

<input placeholder="Student Name"
onChange={(e)=>setName(e.target.value)} />

<br/>

<input placeholder="Intake"
onChange={(e)=>setIntake(e.target.value)} />

<br/>

<input placeholder="Password"
onChange={(e)=>setPassword(e.target.value)} />

<br/>

<button onClick={addStudent}>Add Student</button>

</div>

);

}