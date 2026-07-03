// src/utils/download.js
export function downloadCSV(dataArray, filename = "export.csv") {
  if (!dataArray || !dataArray.length) {
    alert("No data to download");
    return;
  }
  const headers = Object.keys(dataArray[0]);
  const rows = dataArray.map(row => headers.map(h => JSON.stringify(row[h] ?? "")).join(","));
  const csv = [headers.join(","), ...rows].join("\n");
  const blob = new Blob([csv], { type: "text/csv;charset=utf-8;" });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  a.click();
  URL.revokeObjectURL(url);
}
