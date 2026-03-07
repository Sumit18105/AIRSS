# report_generator.py — AIRSS Drone System

import os
from datetime import datetime
from fpdf     import FPDF, XPos, YPos

import config
from shared_state import state


def _safe(text: str) -> str:
    if not text:
        return ""
    replacements = {
        "\u2014": "-", "\u2013": "-",
        "\u2018": "'", "\u2019": "'",
        "\u201C": '"', "\u201D": '"',
        "\u2026": "...", "\u00B0": " deg",
        "\u00e9": "e",  "\u00e0": "a",
        "\u00e8": "e",  "\u00ea": "e",
        "\u00f9": "u",
    }
    for char, repl in replacements.items():
        text = text.replace(char, repl)
    return text.encode("latin-1", errors="ignore").decode("latin-1")


class AIRSSReportPDF(FPDF):
    RED        = (220, 50,  50)
    DARK       = (20,  20,  40)
    WHITE      = (255, 255, 255)
    LIGHT_GREY = (245, 245, 245)
    MID_GREY   = (160, 160, 160)
    GREEN      = (39,  174, 96)

    def header(self):
        self.set_fill_color(*self.DARK)
        self.rect(0, 0, 210, 18, "F")
        self.set_text_color(*self.WHITE)
        self.set_font("Helvetica", "B", 11)
        self.set_y(5)
        self.cell(
            0, 8,
            "AIRSS - AI-Integrated Rescue & Support System System",
            align="C",
        )
        self.ln(14)

    def footer(self):
        self.set_y(-12)
        self.set_font("Helvetica", "I", 7)
        self.set_text_color(*self.MID_GREY)
        self.cell(
            0, 6,
            f"AIRSS Drone System  |  Page {self.page_no()}  |  "
            f"Generated {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            align="C",
        )


def _section(pdf, title):
    pdf.set_fill_color(*AIRSSReportPDF.RED)
    pdf.set_text_color(*AIRSSReportPDF.WHITE)
    pdf.set_font("Helvetica", "B", 10)
    pdf.cell(
        0, 7, _safe(f"  {title}"),
        new_x=XPos.LMARGIN, new_y=YPos.NEXT,
        fill=True,
    )
    pdf.ln(2)
    pdf.set_text_color(0, 0, 0)


def _row(pdf, key, value, shade=False):
    pdf.set_fill_color(
        *(AIRSSReportPDF.LIGHT_GREY if shade else AIRSSReportPDF.WHITE)
    )
    pdf.set_font("Helvetica", "B", 8)
    pdf.cell(55, 6, _safe(f"  {key}"), fill=True)
    pdf.set_font("Helvetica", "", 8)
    pdf.cell(
        0, 6, _safe(f"  {str(value)[:90]}"),
        new_x=XPos.LMARGIN, new_y=YPos.NEXT,
        fill=True,
    )


def generate_report(output_dir: str = "reports") -> str:
    os.makedirs(output_dir, exist_ok=True)

    try:
        stats      = state.get_stats()
        logs       = state.get_log()        or []
        gps_points = state.get_gps_points() or []
    except Exception as e:
        print(f"[Report] State read error: {e}")
        stats, logs, gps_points = {}, [], []

    ts       = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = os.path.join(output_dir, f"AIRSS_mission_{ts}.pdf")

    pdf = AIRSSReportPDF()
    pdf.set_auto_page_break(auto=True, margin=14)
    pdf.add_page()

    # Cover
    pdf.set_fill_color(*AIRSSReportPDF.RED)
    pdf.set_text_color(*AIRSSReportPDF.WHITE)
    pdf.set_font("Helvetica", "B", 22)
    pdf.cell(
        0, 18, "AIRSS MISSION REPORT",
        new_x=XPos.LMARGIN, new_y=YPos.NEXT,
        fill=True, align="C",
    )
    pdf.set_font("Helvetica", "", 9)
    pdf.set_fill_color(180, 35, 35)
    pdf.cell(
        0, 7,
        _safe(
            f"AI-Integrated Rescue & Support System System  |  "
            f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        ),
        new_x=XPos.LMARGIN, new_y=YPos.NEXT,
        fill=True, align="C",
    )
    pdf.ln(6)

    # Section 1
    _section(pdf, "1.  MISSION SUMMARY")
    rows = [
        ("System Name",       "AIRSS - AI-Integrated Rescue & Support System"),
        ("AI Model",          "YOLOv8n - Real-time Person Detection"),
        ("Mission Start",     stats.get("mission_start", "-")),
        ("Report Generated",  datetime.now().strftime("%Y-%m-%d %H:%M:%S")),
        ("Mission Status",    "COMPLETED" if not stats.get("is_active") else "ACTIVE"),
        ("Total Survivors",   str(stats.get("total_survivors", 0))),
        ("Detection Events",  str(stats.get("total_events", len(logs)))),
        ("GPS Points Logged", str(len(gps_points))),
        ("WiFi Devices Seen", str(stats.get("wifi_devices", 0))),
        ("Average FPS",       f"{stats.get('fps', 0):.1f}"),
        ("Alert System",      "Voice (pyttsx3) + Email (Gmail SMTP)"),
        ("Dashboard",         "Flask + Folium + Heatmap + WiFi Scanner"),
    ]
    for i, (k, v) in enumerate(rows):
        _row(pdf, k, v, shade=(i % 2 == 0))
    pdf.ln(5)

    # Section 2
    _section(pdf, "2.  SURVIVOR DETECTION LOG")
    if not logs:
        pdf.set_font("Helvetica", "I", 9)
        pdf.set_text_color(*AIRSSReportPDF.MID_GREY)
        pdf.cell(0, 8, "  No detection events recorded.")
        pdf.set_text_color(0, 0, 0)
        pdf.ln(5)
    else:
        pdf.set_fill_color(*AIRSSReportPDF.DARK)
        pdf.set_text_color(*AIRSSReportPDF.WHITE)
        pdf.set_font("Helvetica", "B", 7)
        col_w   = [8, 40, 12, 28, 28, 40, 20]
        headers = ["#", "Timestamp", "Count", "Latitude",
                   "Longitude", "GPS Source", "Conf."]
        for w, h in zip(col_w, headers):
            pdf.cell(w, 6, h, fill=True, align="C")
        pdf.ln()
        pdf.set_text_color(0, 0, 0)

        for i, entry in enumerate(logs[:60]):
            pdf.set_fill_color(
                *(AIRSSReportPDF.LIGHT_GREY if i % 2 == 0
                  else AIRSSReportPDF.WHITE)
            )
            pdf.set_font("Helvetica", "", 6)
            conf_raw = entry.get("confidences", [])
            conf_str = (
                ", ".join(f"{c:.2f}" for c in conf_raw)
                if isinstance(conf_raw, list) and conf_raw else "-"
            )
            lat_str = (
                f"{float(entry['lat']):.5f}"
                if entry.get("lat") else "-"
            )
            lon_str = (
                f"{float(entry['lon']):.5f}"
                if entry.get("lon") else "-"
            )
            vals = [
                str(i + 1),
                _safe(str(entry.get("timestamp", "-"))[:22]),
                str(entry.get("survivor_count", 1)),
                lat_str, lon_str,
                _safe(str(entry.get("gps_source", "-"))[:18]),
                _safe(conf_str[:12]),
            ]
            for w, v in zip(col_w, vals):
                pdf.cell(w, 5, v, fill=True, align="C")
            pdf.ln()

        if len(logs) > 60:
            pdf.set_font("Helvetica", "I", 7)
            pdf.set_text_color(*AIRSSReportPDF.MID_GREY)
            pdf.cell(0, 5, f"  ... and {len(logs)-60} more (see CSV log).")
            pdf.set_text_color(0, 0, 0)
    pdf.ln(5)

    # Section 3
    _section(pdf, "3.  UNIQUE GPS COORDINATES")
    if not gps_points:
        pdf.set_font("Helvetica", "I", 9)
        pdf.set_text_color(*AIRSSReportPDF.MID_GREY)
        pdf.cell(0, 8, "  No GPS coordinates recorded.")
        pdf.set_text_color(0, 0, 0)
        pdf.ln(5)
    else:
        seen, idx = set(), 1
        for pt in gps_points:
            try:
                lat = float(pt["lat"])
                lon = float(pt["lon"])
            except (KeyError, ValueError, TypeError):
                continue
            key = f"{lat:.4f},{lon:.4f}"
            if key in seen:
                continue
            seen.add(key)
            pdf.set_fill_color(
                *(AIRSSReportPDF.LIGHT_GREY if idx % 2 == 0
                  else AIRSSReportPDF.WHITE)
            )
            maps_url = f"https://maps.google.com/?q={lat},{lon}"
            pdf.set_font("Helvetica", "B", 7)
            pdf.cell(8,  5, f" {idx}",    fill=True)
            pdf.set_font("Helvetica", "", 7)
            pdf.cell(32, 5, f"{lat:.6f}", fill=True)
            pdf.cell(32, 5, f"{lon:.6f}", fill=True)
            pdf.set_text_color(0, 0, 200)
            pdf.cell(0, 5, maps_url,
                     new_x=XPos.LMARGIN, new_y=YPos.NEXT,
                     fill=True, link=maps_url)
            pdf.set_text_color(0, 0, 0)
            idx += 1
    pdf.ln(5)

    # Section 4
    screenshot_dir = "screenshots"
    images = []
    if os.path.exists(screenshot_dir):
        images = sorted([
            f for f in os.listdir(screenshot_dir)
            if f.lower().endswith((".jpg", ".jpeg", ".png"))
        ])[:15]

    if images:
        pdf.add_page()
        _section(pdf, "4.  DETECTION SCREENSHOTS")
        x_positions = [10, 75, 140]
        col, y = 0, pdf.get_y() + 2
        for img_file in images:
            img_path = os.path.join(screenshot_dir, img_file)
            try:
                if os.path.getsize(img_path) > 0:
                    pdf.image(img_path, x=x_positions[col],
                              y=y, w=58, h=44)
                    pdf.set_xy(x_positions[col], y + 45)
                    pdf.set_font("Helvetica", "", 5)
                    pdf.set_text_color(*AIRSSReportPDF.MID_GREY)
                    short = (img_file[:26] +
                             ("..." if len(img_file) > 26 else ""))
                    pdf.cell(58, 4, _safe(short), align="C")
                    pdf.set_text_color(0, 0, 0)
                    col += 1
                    if col == 3:
                        col = 0
                        y  += 55
                        if y > 248:
                            pdf.add_page()
                            _section(pdf,
                                "4.  DETECTION SCREENSHOTS (cont.)")
                            y = pdf.get_y() + 2
            except Exception as img_err:
                print(f"[Report] Skipping {img_file}: {img_err}")
    else:
        _section(pdf, "4.  DETECTION SCREENSHOTS")
        pdf.set_font("Helvetica", "I", 9)
        pdf.set_text_color(*AIRSSReportPDF.MID_GREY)
        pdf.cell(0, 8, "  No screenshots found.")
        pdf.set_text_color(0, 0, 0)

    # Section 5
    pdf.add_page()
    _section(pdf, "5.  SYSTEM INFORMATION")
    sys_rows = [
        ("System",        "AIRSS - AI-Integrated Rescue & Support System"),
        ("AI Model",      "YOLOv8n (Ultralytics)"),
        ("GPS Method",    "IP Webcam GPS -> IP Geolocation -> Fallback"),
        ("Alerts",        "Voice (pyttsx3) + Email (Gmail SMTP)"),
        ("Dashboard",     "Flask + Folium + HeatMap + WiFi Scanner"),
        ("Map Layers",    "OpenStreetMap + Satellite + Heatmap + Clusters"),
        ("Rescue Portal", "Captive Portal DNS -> Auto-popup -> Rescue Form"),
        ("WiFi Scanner",  "Passive Probe Request Scan (Scapy-ready)"),
        ("Hotspot IP",    config.HOTSPOT_IP),
        ("Frame Skip",    str(config.FRAME_SKIP)),
        ("Confidence",    str(config.CONFIDENCE_THRESHOLD)),
    ]
    for i, (k, v) in enumerate(sys_rows):
        _row(pdf, k, v, shade=(i % 2 == 0))

    pdf.ln(8)
    pdf.set_fill_color(*AIRSSReportPDF.GREEN)
    pdf.set_text_color(*AIRSSReportPDF.WHITE)
    pdf.set_font("Helvetica", "B", 10)
    pdf.cell(
        0, 10,
        "  AIRSS Mission Report Generated Successfully",
        new_x=XPos.LMARGIN, new_y=YPos.NEXT,
        fill=True, align="C",
    )

    try:
        pdf.output(filename)
        print(f"[Report] PDF saved: {filename}")
        return filename
    except Exception as e:
        print(f"[Report] Save error: {e}")
        fallback = f"AIRSS_mission_{ts}.pdf"
        pdf.output(fallback)
        return fallback
