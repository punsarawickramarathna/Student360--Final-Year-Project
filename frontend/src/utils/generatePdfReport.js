// src/utils/generatePdfReport.js

import jsPDF from "jspdf";
import autoTable from "jspdf-autotable";

/**
 * Generates and downloads a formal, print-friendly, black & white academic transcript PDF report.
 *
 * @param {Object} studentProfile - Student information (name, student_id, intake, department, etc.)
 * @param {Array} attendanceRecords - Array of attendance and session log objects
 * @param {Object} behaviorSummary - Aggregated metrics (totalSessions, attendanceRate, behavior scores)
 * @returns {string} The generated filename
 */
export function exportAcademicReportPDF(
  studentProfile = {},
  attendanceRecords = [],
  behaviorSummary = {}
) {
  const doc = new jsPDF({
    orientation: "portrait",
    unit: "mm",
    format: "a4",
  });

  const pageWidth = doc.internal.pageSize.getWidth(); // 210 mm
  const pageHeight = doc.internal.pageSize.getHeight(); // 297 mm
  const margin = 14; // 14 mm margins
  const contentWidth = pageWidth - margin * 2; // 182 mm

  let y = margin + 2;

  // ============================================================
  // 1. HEADER SECTION (Strict Monochrome)
  // ============================================================
  doc.setTextColor(0, 0, 0);

  // Main Institution Header
  doc.setFont("helvetica", "bold");
  doc.setFontSize(16);
  doc.text("HORIZON CAMPUS", pageWidth / 2, y, { align: "center" });

  // Faculty Sub-header
  y += 6;
  doc.setFont("helvetica", "normal");
  doc.setFontSize(10);
  doc.text("Faculty of Information Technology", pageWidth / 2, y, { align: "center" });

  // Official Report Title
  y += 6;
  doc.setFont("helvetica", "bold");
  doc.setFontSize(11);
  doc.text(
    "STUDENT360 - ACADEMIC ATTENDANCE & TELEMETRY REPORT",
    pageWidth / 2,
    y,
    { align: "center" }
  );

  // Horizontal Solid Separator Line
  y += 4.5;
  doc.setDrawColor(0, 0, 0);
  doc.setLineWidth(0.5);
  doc.line(margin, y, pageWidth - margin, y);

  // ============================================================
  // 2. STUDENT METADATA BLOCK (2-Column Layout)
  // ============================================================
  y += 6;
  const leftX = margin;
  const rightX = 116;
  const rowHeight = 5.2;

  const studentName = studentProfile?.name || "Student";
  const studentId =
    studentProfile?.student_id ||
    studentProfile?.user_id ||
    studentProfile?.id ||
    studentProfile?.username ||
    "N/A";

  const degree =
    studentProfile?.degree ||
    studentProfile?.program ||
    (studentProfile?.department
      ? `BSc (Hons) in ${studentProfile.department}`
      : "BSc (Hons) in Information Technology");
  const intakeStr = studentProfile?.intake ? ` (Intake ${studentProfile.intake})` : "";
  const degreeProgram = `${degree}${intakeStr}`;

  const reportDate = new Date().toLocaleDateString("en-GB", {
    year: "numeric",
    month: "short",
    day: "numeric",
  });

  const recordsList = Array.isArray(attendanceRecords) ? attendanceRecords : [];
  const totalSessions = Number(
    behaviorSummary?.totalSessions ??
    behaviorSummary?.total_sessions ??
    recordsList.length ??
    0
  );

  const attendanceRate = Number(
    behaviorSummary?.attendanceRate ??
    behaviorSummary?.percentage ??
    (totalSessions > 0 ? Math.round((recordsList.length / totalSessions) * 100) : 0)
  );

  // Metadata Row 1: Student Name | Report Date
  doc.setFontSize(9);
  doc.setFont("helvetica", "bold");
  doc.text("Student Name:", leftX, y);
  doc.setFont("helvetica", "normal");
  doc.text(studentName, leftX + 28, y);

  doc.setFont("helvetica", "bold");
  doc.text("Report Date:", rightX, y);
  doc.setFont("helvetica", "normal");
  doc.text(reportDate, rightX + 34, y);

  // Metadata Row 2: Student ID | Total Sessions
  y += rowHeight;
  doc.setFont("helvetica", "bold");
  doc.text("Student ID:", leftX, y);
  doc.setFont("helvetica", "normal");
  doc.text(studentId, leftX + 28, y);

  doc.setFont("helvetica", "bold");
  doc.text("Total Sessions:", rightX, y);
  doc.setFont("helvetica", "normal");
  doc.text(String(totalSessions), rightX + 34, y);

  // Metadata Row 3: Degree Program | Attendance Rate
  y += rowHeight;
  doc.setFont("helvetica", "bold");
  doc.text("Degree Program:", leftX, y);
  doc.setFont("helvetica", "normal");
  doc.text(degreeProgram, leftX + 28, y);

  doc.setFont("helvetica", "bold");
  doc.text("Attendance Rate:", rightX, y);
  doc.setFont("helvetica", "normal");
  doc.text(`${attendanceRate}%`, rightX + 34, y);

  // Bottom Horizontal Separator Line
  y += 4.5;
  doc.setDrawColor(0, 0, 0);
  doc.setLineWidth(0.5);
  doc.line(margin, y, pageWidth - margin, y);

  y += 4;

  // ============================================================
  // 3. TABULAR DATA (autoTable)
  // Columns: #, Date, Module / Session, Attendance Status, Attentive Duration, Alerts / Flags
  // ============================================================
  const tableRows =
    recordsList.length > 0
      ? recordsList.map((item, index) => {
          const dateStr =
            item.date ||
            (typeof item.created_at === "string"
              ? item.created_at.substring(0, 10)
              : "-");

          const sessionTitle =
            item.subject ||
            item.module ||
            (item.mode
              ? `Lecture (${item.mode.charAt(0).toUpperCase() + item.mode.slice(1)})`
              : `Session ${item.session_id ? item.session_id.substring(0, 8) : index + 1}`);

          const statusRaw = String(item.status || "Present").trim();
          const status =
            statusRaw.toLowerCase() === "absent" ? "Absent" : "Present";

          // Attentive duration format
          let durationStr = "-";
          if (item.attentive_sec !== undefined && item.attentive_sec !== null) {
            durationStr = `${Number(item.attentive_sec).toFixed(1)}s`;
          } else if (item.attentive !== undefined && item.attentive !== null) {
            durationStr = `${Number(item.attentive).toFixed(1)}s`;
          } else if (status === "Absent") {
            durationStr = "0.0s";
          } else if (item.arrival_time && item.arrival_time !== "-") {
            durationStr = `Arrived: ${item.arrival_time}`;
          } else {
            durationStr = "Present";
          }

          // Alerts & Flags calculation
          const flags = [];
          const cheatingTime = Number(item.cheating_sec ?? item.cheating ?? 0);
          const sleepingTime = Number(item.sleeping_sec ?? item.sleeping ?? 0);
          const phoneTime = Number(item.phone_use_sec ?? item.phone_use ?? 0);

          if (cheatingTime > 0) flags.push(`Irregularity (${cheatingTime.toFixed(0)}s)`);
          if (sleepingTime > 0) flags.push(`Drowsy (${sleepingTime.toFixed(0)}s)`);
          if (phoneTime > 0) flags.push(`Phone Use (${phoneTime.toFixed(0)}s)`);

          const flagsStr = flags.length > 0 ? flags.join(", ") : "None (Clear)";

          return [
            String(index + 1),
            dateStr,
            sessionTitle,
            status,
            durationStr,
            flagsStr,
          ];
        })
      : [
          ["-", "-", "No recorded sessions in academic period", "N/A", "-", "None"],
        ];

  // Invoke autoTable cleanly whether bound to doc or via import
  const invokeTable =
    typeof doc.autoTable === "function"
      ? (options) => doc.autoTable(options)
      : (options) => autoTable(doc, options);

  invokeTable({
    startY: y,
    margin: { left: margin, right: margin, top: margin, bottom: 26 },
    theme: "plain",
    head: [
      [
        "#",
        "Date",
        "Module / Session",
        "Attendance Status",
        "Attentive Duration",
        "Alerts / Flags",
      ],
    ],
    body: tableRows,
    styles: {
      font: "helvetica",
      fontSize: 8.5,
      textColor: [0, 0, 0],
      lineColor: [40, 40, 40],
      lineWidth: 0.15,
      valign: "middle",
      cellPadding: 2.2,
      overflow: "linebreak",
    },
    headStyles: {
      fillColor: [240, 240, 240], // Light grey #f0f0f0 fill
      textColor: [0, 0, 0],
      fontStyle: "bold",
      lineColor: [0, 0, 0],
      lineWidth: 0.25,
      halign: "center",
      valign: "middle",
    },
    columnStyles: {
      0: { halign: "center", cellWidth: 10 },
      1: { halign: "center", cellWidth: 26 },
      2: { halign: "left", cellWidth: 46 },
      3: { halign: "center", cellWidth: 30 },
      4: { halign: "center", cellWidth: 34 },
      5: { halign: "left", cellWidth: 36 },
    },
    alternateRowStyles: {
      fillColor: [255, 255, 255],
    },
  });

  // ============================================================
  // 4. SIGN-OFF BLOCK & PAGE FOOTERS
  // ============================================================
  let finalY =
    doc.lastAutoTable && doc.lastAutoTable.finalY
      ? doc.lastAutoTable.finalY + 10
      : y + 20;

  // If there's not enough room for sign-off block (~34mm needed), add page
  if (finalY + 34 > pageHeight - 18) {
    doc.addPage();
    finalY = margin + 10;
  }

  // Verification note (Left)
  doc.setTextColor(0, 0, 0);
  doc.setFont("helvetica", "bold");
  doc.setFontSize(8.5);
  doc.text("Official Academic Attestation:", margin, finalY);

  doc.setFont("helvetica", "normal");
  doc.setFontSize(8);
  doc.text(
    "This document certifies attendance records and telemetry captured",
    margin,
    finalY + 4.5
  );
  doc.text(
    "via the Student360 AI surveillance and lecture monitoring system.",
    margin,
    finalY + 8.5
  );
  doc.text(
    `Record Reference: ${studentId}-${new Date().getTime().toString().slice(-6)}`,
    margin,
    finalY + 12.5
  );

  // Signature line (Right)
  const sigLineStart = 132;
  const sigLineEnd = pageWidth - margin;
  doc.setLineWidth(0.3);
  doc.setDrawColor(0, 0, 0);
  doc.line(sigLineStart, finalY + 12, sigLineEnd, finalY + 12);

  doc.setFont("helvetica", "bold");
  doc.setFontSize(8.5);
  doc.text(
    "Lecturer / HOD Signature",
    (sigLineStart + sigLineEnd) / 2,
    finalY + 16.5,
    { align: "center" }
  );

  doc.setFont("helvetica", "normal");
  doc.setFontSize(8);
  doc.text(
    "Date: ________________________",
    (sigLineStart + sigLineEnd) / 2,
    finalY + 22,
    { align: "center" }
  );

  // Add system footer to every page
  const totalPages = doc.internal.getNumberOfPages();
  for (let i = 1; i <= totalPages; i++) {
    doc.setPage(i);
    doc.setFont("helvetica", "italic");
    doc.setFontSize(7.5);
    doc.setTextColor(80, 80, 80);
    doc.text(
      "System Generated Report - Verified by Student360 AI Engine",
      margin,
      pageHeight - 8
    );
    doc.text(
      `Page ${i} of ${totalPages}`,
      pageWidth - margin,
      pageHeight - 8,
      { align: "right" }
    );
  }

  // ============================================================
  // 5. DOWNLOAD GENERATED PDF
  // ============================================================
  const cleanId = String(studentId).replace(/[^a-zA-Z0-9_-]/g, "_");
  const filename = `${cleanId}_Academic_Report.pdf`;
  doc.save(filename);

  return filename;
}

export default exportAcademicReportPDF;
