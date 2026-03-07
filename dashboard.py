# dashboard.py — AIRSS Drone System

import os
import cv2
from flask import (
    Flask, Response, render_template, jsonify,
    send_file, send_from_directory, request,
    make_response, redirect as flask_redirect,
)

from triage_bot import triage_reply

from shared_state import state
import config

app = Flask(__name__, template_folder="templates", static_folder="static")

RESCUE_URL = f"http://{config.HOTSPOT_IP}:{config.DASHBOARD_PORT}/rescue"

# ══════════════════════════════════════════════════════
# Captive Portal Detection Routes
# ══════════════════════════════════════════════════════

@app.route("/generate_204")
@app.route("/gen_204")
def android_captive_204():
    return flask_redirect(RESCUE_URL, code=302)
@app.route("/api/chat", methods=["POST"])
def api_chat():
    data = request.get_json(silent=True) or {}
    user_msg = (data.get("message") or "").strip()

    reply = triage_reply(user_msg)
    return jsonify({"reply": reply})


@app.route("/hotspot-detect.html")
@app.route("/library/test/success.html")
def ios_captive():
    return (
        f"<html><head>"
        f"<meta http-equiv='refresh' content='0;url={RESCUE_URL}'>"
        f"</head><body>"
        f"<script>window.location='{RESCUE_URL}'</script>"
        f"</body></html>"
    ), 200

@app.route("/connecttest.txt")
@app.route("/ncsi.txt")
def windows_captive():
    return flask_redirect(RESCUE_URL, code=302)

@app.route("/<path:anypath>")
def catchall(anypath):
    skip = (
        "video_feed", "map", "api", "rescue",
        "download-report", "screenshots", "static",
        "generate_204", "gen_204", "hotspot-detect.html",
        "library", "connecttest.txt", "ncsi.txt",
    )
    if any(anypath.startswith(s) for s in skip):
        from flask import abort
        abort(404)
    return flask_redirect(RESCUE_URL, code=302)

# ══════════════════════════════════════════════════════
# MJPEG Live Feed
# ══════════════════════════════════════════════════════

def generate_frames():
    import time
    jpeg_quality = getattr(config, "JPEG_QUALITY", 80)
    while True:
        frame = state.get_frame()
        if frame is None:
            time.sleep(0.05)
            continue
        ret, buffer = cv2.imencode(
            ".jpg", frame,
            [cv2.IMWRITE_JPEG_QUALITY, jpeg_quality]
        )
        if not ret:
            continue
        yield (
            b"--frame\r\n"
            b"Content-Type: image/jpeg\r\n\r\n"
            + buffer.tobytes()
            + b"\r\n"
        )
        time.sleep(0.033)   # ~30 fps ceiling

@app.route("/video_feed")
def video_feed():
    return Response(
        generate_frames(),
        mimetype="multipart/x-mixed-replace; boundary=frame",
    )

# ══════════════════════════════════════════════════════
# Dashboard
# ══════════════════════════════════════════════════════

@app.route("/")
def dashboard():
    return render_template("dashboard.html")

@app.route("/map")
def survivor_map():
    html = state.get_map_html()
    if html:
        return html, 200, {"Content-Type": "text/html; charset=utf-8"}
    return (
        "<html><body style='background:#1a1a2e;color:#555;"
        "font-family:Arial;display:flex;align-items:center;"
        "justify-content:center;height:100vh;margin:0'>"
        "<div style='text-align:center'>"
        "<div style='font-size:3em'>🗺️</div>"
        "<h3>Map loading — waiting for first detection...</h3>"
        "</div></body></html>"
    ), 200

# ══════════════════════════════════════════════════════
# API Endpoints
# ══════════════════════════════════════════════════════

@app.route("/api/stats")
def api_stats():
    return jsonify(state.get_stats())

@app.route("/api/logs")
def api_logs():
    return jsonify(state.get_log(20))

@app.route("/api/gps")
def api_gps():
    return jsonify(state.get_gps_points())

@app.route("/api/wifi")
def api_wifi():
    return jsonify(state.get_wifi_devices())

@app.route("/api/rescue")
def api_rescue():
    """Dedicated endpoint for rescue portal submissions."""
    return jsonify(state.get_rescue_requests(50))

# ══════════════════════════════════════════════════════
# Report Download
# ══════════════════════════════════════════════════════

@app.route("/download-report")
def download_report():
    try:
        from report_generator import generate_report
        path = generate_report(output_dir="reports")
        return send_file(
            path,
            as_attachment   = True,
            download_name   = os.path.basename(path),
            mimetype        = "application/pdf",
        )
    except Exception as e:
        return (
            f"<h3 style='font-family:Arial;color:red;padding:20px'>"
            f"Report error: {e}</h3>"
        ), 500

# ══════════════════════════════════════════════════════
# Rescue Portal Page
# ══════════════════════════════════════════════════════

@app.route("/rescue")
def rescue_portal():
    return """<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>AIRSS - Emergency Rescue</title>
<style>
*{box-sizing:border-box;margin:0;padding:0}
body{font-family:Arial,sans-serif;background:linear-gradient(135deg,#1a1a2e,#16213e);
     min-height:100vh;padding:16px;color:white}
.card{background:rgba(255,255,255,0.05);border:2px solid #e74c3c;border-radius:16px;
      padding:22px 18px;max-width:460px;margin:0 auto;
      box-shadow:0 0 40px rgba(231,76,60,0.3)}
.logo{text-align:center;font-size:2.2em;margin-bottom:4px}
h1{text-align:center;color:#e74c3c;font-size:1.25em;margin-bottom:4px}
.subtitle{text-align:center;color:#aaa;font-size:0.78em;margin-bottom:18px;line-height:1.5}
.sec{background:rgba(231,76,60,0.15);border-left:3px solid #e74c3c;padding:6px 12px;
     font-size:0.8em;font-weight:bold;color:#e74c3c;margin:14px 0 8px;text-transform:uppercase}
.grid2{display:grid;grid-template-columns:1fr 1fr;gap:8px;margin-bottom:12px}
.opt{background:rgba(255,255,255,0.06);border:1.5px solid rgba(255,255,255,0.12);
     border-radius:10px;padding:11px 8px;text-align:center;cursor:pointer;
     font-size:0.82em;color:#ccc;transition:all 0.15s;user-select:none}
.opt .e{font-size:1.4em;display:block;margin-bottom:3px}
.opt.on{background:rgba(231,76,60,0.3);border-color:#e74c3c;color:white;font-weight:bold}
.counter{display:flex;align-items:center;gap:12px;margin-bottom:12px}
.cbtn{background:rgba(231,76,60,0.2);border:1.5px solid #e74c3c;color:white;
      width:36px;height:36px;border-radius:50%;font-size:1.2em;cursor:pointer;
      display:flex;align-items:center;justify-content:center}
.cval{font-size:1.7em;font-weight:bold;color:#e74c3c;min-width:36px;text-align:center}
.checks{display:grid;grid-template-columns:1fr 1fr;gap:6px;margin-bottom:12px}
.chk{display:flex;align-items:center;gap:7px;font-size:0.82em;color:#ccc}
.chk input{accent-color:#e74c3c;width:15px;height:15px}
textarea{width:100%;background:rgba(255,255,255,0.07);border:1px solid rgba(255,255,255,0.15);
         border-radius:8px;color:white;padding:9px;font-size:0.84em;resize:vertical;
         margin-bottom:12px;font-family:Arial}
textarea:focus{outline:none;border-color:#e74c3c}
textarea::placeholder{color:#555}
.gps-box{background:rgba(0,200,200,0.07);border:1px solid rgba(0,200,200,0.2);
         border-radius:10px;padding:10px 12px;margin-bottom:14px;font-size:0.8em}
.gps-row{display:flex;justify-content:space-between;align-items:center;margin-bottom:4px}
.gps-label{color:#aaa}
.gps-val{color:white;font-family:monospace}
.acc-good{color:#2ecc71}
.acc-ok{color:#f39c12}
.acc-bad{color:#e74c3c}
.gps-hint{font-size:0.75em;color:#555;margin-top:5px}
.sbtn{background:#e74c3c;color:white;border:none;width:100%;padding:15px;
      font-size:1em;font-weight:bold;border-radius:12px;cursor:pointer}
.sbtn:disabled{background:#444;cursor:not-allowed}
.errmsg{display:none;background:rgba(231,76,60,0.15);border:1px solid #e74c3c;
        border-radius:8px;padding:10px;color:#e74c3c;font-size:0.82em;
        margin-top:10px;text-align:center}
#ok{display:none;text-align:center;padding:30px 10px}
#ok .big{font-size:4em;margin-bottom:14px}
#ok h2{color:#2ecc71;margin-bottom:8px}
#ok p{color:#aaa;font-size:0.88em;line-height:1.7}
.brand{text-align:center;color:#444;font-size:0.68em;margin-top:18px}
</style>
</head>
<body>
<div class="card">
  <div id="form">
    <div class="logo">🆘</div>
    <h1>AIRSS RESCUE REQUEST</h1>
    <p class="subtitle">You are connected to an
      <b style="color:#e74c3c">AIRSS AI Rescue Drone</b>.<br>
      Fill this form so the rescue team reaches you faster.
    </p>

    <div class="sec">1. What do you need?</div>
    <div class="grid2">
      <div class="opt" onclick="tog(this)" data-v="medical"><span class="e">🏥</span>Medical Help</div>
      <div class="opt" onclick="tog(this)" data-v="trapped"><span class="e">🆘</span>Trapped / Stuck</div>
      <div class="opt" onclick="tog(this)" data-v="water"><span class="e">💧</span>Water / Food</div>
      <div class="opt" onclick="tog(this)" data-v="evacuate"><span class="e">🚁</span>Evacuation</div>
      <div class="opt" onclick="tog(this)" data-v="fire"><span class="e">🔥</span>Fire Nearby</div>
      <div class="opt" onclick="tog(this)" data-v="safe"><span class="e">✅</span>Safe, Need Pickup</div>
    </div>

    <div class="sec">2. How many people are with you?</div>
    <div class="counter">
      <button class="cbtn" onclick="chg(-1)">−</button>
      <div class="cval" id="cnt">1</div>
      <button class="cbtn" onclick="chg(1)">+</button>
      <span style="color:#aaa;font-size:0.82em">total persons</span>
    </div>

    <div class="sec">3. Is anyone injured?</div>
    <div class="checks">
      <label class="chk"><input type="checkbox" id="c1"> Bleeding</label>
      <label class="chk"><input type="checkbox" id="c2"> Fracture</label>
      <label class="chk"><input type="checkbox" id="c3"> Unconscious</label>
      <label class="chk"><input type="checkbox" id="c4"> Burns</label>
      <label class="chk"><input type="checkbox" id="c5"> Breathing difficulty</label>
      <label class="chk"><input type="checkbox" id="c6"> No injuries</label>
    </div>

    <div class="sec">4. Describe your exact location</div>
    <textarea id="loc" rows="2"
      placeholder="e.g. 3rd floor, collapsed wall west side, near red door..."></textarea>

    <div class="sec">5. Other important info</div>
    <textarea id="ext" rows="2"
      placeholder="e.g. Elderly person, infant, need stretcher..."></textarea>

    <div class="gps-box">
      <div class="gps-row">
        <span class="gps-label">GPS Status</span>
        <span id="gStat" style="color:#00d2d3">Acquiring...</span>
      </div>
      <div class="gps-row">
        <span class="gps-label">Latitude</span>
        <span class="gps-val" id="gLat">---</span>
      </div>
      <div class="gps-row">
        <span class="gps-label">Longitude</span>
        <span class="gps-val" id="gLon">---</span>
      </div>
      <div id="gAcc"></div>
      <div class="gps-hint">
        GPS improves over 10–15 seconds. Wait for
        <span style="color:#2ecc71">GPS Ready</span> before submitting.
      </div>
    </div>

    <button class="sbtn" id="sbtn" onclick="send()">🆘 &nbsp;SEND RESCUE REQUEST</button>
    <div class="errmsg" id="err"></div>
  </div>

  <div id="ok">
    <div class="big">✅</div>
    <h2>Help is Coming!</h2>
    <p>Your rescue request has been sent.<br>
       <b style="color:white">Stay calm. Stay visible.</b><br><br>
       Keep this page open — the team has your GPS.
    </p>
    <p id="gpsConf" style="color:#00d2d3;font-size:0.78em;margin-top:12px"></p>
  </div>

  <div class="brand">AIRSS - AI-Integrated Rescue &amp; Surveillance System</div>
</div>

<script>
var needs = [], cnt = 1;
var bestLat = null, bestLon = null, bestAcc = 9999;
var watchId = null;

function startGPS() {
  if (!navigator.geolocation) {
    document.getElementById('gStat').textContent = 'GPS not supported';
    return;
  }
  watchId = navigator.geolocation.watchPosition(
    function(pos) {
      var la = pos.coords.latitude;
      var lo = pos.coords.longitude;
      var ac = pos.coords.accuracy;
      if (ac < bestAcc) { bestLat = la; bestLon = lo; bestAcc = ac; }
      document.getElementById('gLat').textContent = la.toFixed(6);
      document.getElementById('gLon').textContent = lo.toFixed(6);
      var cls = ac <= 20 ? 'acc-good' : ac <= 60 ? 'acc-ok' : 'acc-bad';
      var msg = ac <= 10 ? 'Excellent' : ac <= 30 ? 'Good' : ac <= 80 ? 'Fair' : 'Poor';
      document.getElementById('gAcc').innerHTML =
        '<span class="' + cls + '">Accuracy: ~' + Math.round(ac) + 'm (' + msg + ')</span>';
      document.getElementById('gStat').innerHTML =
        ac <= 50
          ? '<b style="color:#2ecc71">GPS Ready ✓</b>'
          : 'Improving... ' + Math.round(ac) + 'm';
    },
    function(err) {
      var msgs = {1:'Permission denied — tap Allow',
                  2:'GPS unavailable — go to open area',
                  3:'GPS timeout — retrying...'};
      document.getElementById('gStat').textContent = msgs[err.code] || 'GPS error';
      if (err.code === 3) setTimeout(startGPS, 3000);
    },
    {enableHighAccuracy: true, timeout: 20000, maximumAge: 0}
  );
}

function tog(el) {
  var v = el.dataset.v;
  if (el.classList.contains('on')) {
    el.classList.remove('on');
    needs = needs.filter(function(x) { return x !== v; });
  } else {
    el.classList.add('on');
    needs.push(v);
  }
}

function chg(d) {
  cnt = Math.max(1, Math.min(50, cnt + d));
  document.getElementById('cnt').textContent = cnt;
}

function showErr(m) {
  var e = document.getElementById('err');
  e.textContent = m; e.style.display = 'block';
}

function send() {
  document.getElementById('err').style.display = 'none';
  if (needs.length === 0) { showErr('Please select what you need (Section 1).'); return; }
  var injuries = [];
  [['c1','Bleeding'],['c2','Fracture'],['c3','Unconscious'],
   ['c4','Burns'],['c5','Breathing difficulty'],['c6','No injuries']
  ].forEach(function(p) {
    if (document.getElementById(p[0]).checked) injuries.push(p[1]);
  });
  var btn = document.getElementById('sbtn');
  btn.disabled = true; btn.textContent = 'Sending...';

  var payload = {
    lat: bestLat, lon: bestLon,
    accuracy: bestAcc < 9999 ? bestAcc : null,
    needs: needs, personcount: cnt, injuries: injuries,
    locationdesc: document.getElementById('loc').value.trim(),
    extrainfo:    document.getElementById('ext').value.trim(),
  };

  var xhr = new XMLHttpRequest();
  xhr.open('POST', '/rescue-submit', true);
  xhr.setRequestHeader('Content-Type', 'application/json');
  xhr.timeout = 10000;
  xhr.onreadystatechange = function() {
    if (xhr.readyState !== 4) return;
    try {
      var data = JSON.parse(xhr.responseText);
      if (data.ok) {
        if (watchId !== null) navigator.geolocation.clearWatch(watchId);
        document.getElementById('form').style.display = 'none';
        document.getElementById('ok').style.display   = 'block';
        if (bestLat)
          document.getElementById('gpsConf').textContent =
            'GPS sent: ' + bestLat.toFixed(6) + ', ' + bestLon.toFixed(6) +
            ' — ±' + Math.round(bestAcc) + 'm';
      } else {
        showErr('Error: ' + (data.error || 'Unknown'));
        btn.disabled = false; btn.textContent = 'Retry';
      }
    } catch(e) {
      showErr('Response error. Try again.');
      btn.disabled = false; btn.textContent = 'Retry';
    }
  };
  xhr.ontimeout = function() {
    showErr('Timeout. Stay on AIRSS-RESCUE WiFi and retry.');
    btn.disabled = false; btn.textContent = 'Retry';
  };
  xhr.onerror = function() {
    showErr('Network error. Connect to AIRSS-RESCUE WiFi.');
    btn.disabled = false; btn.textContent = 'Retry';
  };
  xhr.send(JSON.stringify(payload));
}

window.addEventListener('load', startGPS);
</script>
</body>
</html>"""


# ══════════════════════════════════════════════════════
# Rescue Submit (POST handler)
# ══════════════════════════════════════════════════════

@app.route("/rescue-submit", methods=["POST", "OPTIONS"])
def rescue_submit():
    def respond(data, status=200):
        resp = make_response(jsonify(data), status)
        resp.headers["Access-Control-Allow-Origin"]  = "*"
        resp.headers["Access-Control-Allow-Headers"] = "Content-Type"
        resp.headers["Access-Control-Allow-Methods"] = "POST, OPTIONS"
        return resp

    if request.method == "OPTIONS":
        return respond({"ok": True})

    try:
        from datetime import datetime
        data = request.get_json(force=True, silent=True)
        if not data:
            return respond({"ok": False, "error": "No data"}, 400)

        lat         = data.get("lat")
        lon         = data.get("lon")
        acc         = data.get("accuracy") or 0
        needs       = data.get("needs", [])
        personcount = int(data.get("personcount", 1))
        injuries    = data.get("injuries", [])
        locdesc     = data.get("locationdesc", "")
        extra       = data.get("extrainfo", "")
        timestamp   = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        print(f"[RescuePortal] NEW RESCUE REQUEST")
        print(f"  Time      : {timestamp}")
        print(f"  Needs     : {', '.join(needs)}")
        print(f"  People    : {personcount}")
        print(f"  Injuries  : {', '.join(injuries) if injuries else 'None'}")
        print(f"  Location  : {locdesc or 'Not provided'}")
        print(f"  Extra     : {extra or 'None'}")

        log_entry = {
            "timestamp"     : timestamp,
            "survivor_count": personcount,
            "lat"           : lat,
            "lon"           : lon,
            "accuracy_m"    : acc,
            "gps_source"    : "Rescue Portal (Self-Reported)",
            "needs"         : needs,
            "injuries"      : injuries,
            "location_desc" : locdesc,
            "extra_info"    : extra,
            "confidences"   : [],
            "screenshot"    : "",
            "address"       : (
                f"{float(lat):.5f}, {float(lon):.5f}"
                if lat and lon else "No GPS"
            ),
        }

        if lat and lon:
            print(f"  GPS       : {float(lat):.6f}, {float(lon):.6f}  ±{acc}m")
            print(f"  Maps      : https://www.google.com/maps?q={lat},{lon}")
            state.add_gps_point(float(lat), float(lon), log_entry)
            mapper = state.get_mapper()
            if mapper:
                mapper.add_self_reported_marker(
                    float(lat), float(lon), timestamp
                )

        # Store in BOTH places:
        # 1. detection_log (shows in main log table)
        state.add_log_entry(log_entry)
        # 2. rescue_requests (dedicated — shown in rescue tab)
        state.add_rescue_request(log_entry)
        state.log_event(personcount)

        return respond({"ok": True})

    except Exception as e:
        print(f"[RescuePortal] Error: {e}")
        return respond({"ok": False, "error": str(e)}, 500)


# ══════════════════════════════════════════════════════
# Screenshots
# ══════════════════════════════════════════════════════

@app.route("/screenshots/<path:filename>")
def screenshots(filename):
    folder = os.path.join(os.path.dirname(os.path.abspath(__file__)), "screenshots")
    return send_from_directory(folder, filename)


def run_dashboard(host: str = "0.0.0.0", port: int = 5000):
    app.run(
        host         = host,
        port         = port,
        debug        = False,
        use_reloader = False,
        threaded     = True,
    )
