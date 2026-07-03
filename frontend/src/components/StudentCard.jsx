// src/components/StudentCard.jsx
import React from "react";

export default function StudentCard({ initials, name, id, year, attention, onView }) {
  return (
    <div className="flex items-center justify-between bg-[var(--card)] p-4 rounded-xl mb-3 border border-[#132034]">
      <div className="flex items-center gap-4">
        <div className="w-12 h-12 rounded-full bg-gradient-to-br from-[var(--accent-from)] to-[var(--accent-to)] text-white flex items-center justify-center font-bold">
          {initials}
        </div>
        <div>
          <div className="font-semibold">{name}</div>
          <div className="text-sm text-[var(--muted)]">{id} • {year}</div>
        </div>
      </div>
      <div className="text-right">
        <div className="text-sm text-[var(--muted)]">Attention</div>
        <div className="font-bold text-lg text-blue-300">{attention}%</div>
        <button
          onClick={() => onView?.()}
          className="mt-2 px-3 py-1 rounded-md bg-gradient-to-r from-[var(--accent-from)] to-[var(--accent-to)] text-white text-sm"
        >
          View
        </button>
      </div>
    </div>
  );
}
