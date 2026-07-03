export default function BehaviorTable({records}){

return(

<table className="w-full">

<thead>

<tr>

<th>Date</th>

<th>Behavior</th>

</tr>

</thead>

<tbody>

{

records.map((r,i)=>(

<tr key={i}>

<td>{r.date}</td>

<td>{r.behavior}</td>

</tr>

))

}

</tbody>

</table>

);

}