export default function MetricCard({ title, value, subtitle }) {
  return (
    <div className="bg-[#12172F] p-5 rounded-xl w-full shadow-lg">
      <p className="text-gray-300 text-sm">{title}</p>
      <h2 className="text-white text-3xl font-bold mt-1">{value}</h2>
      <p className="text-gray-400 text-sm mt-2">{subtitle}</p>
    </div>
  );
}
