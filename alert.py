# alert.py — UPDATED: GPS coordinates in email

import threading
import smtplib
import os
import time
from email.mime.multipart import MIMEMultipart
from email.mime.text      import MIMEText
from email.mime.base      import MIMEBase
from email                import encoders
from datetime             import datetime

import config


class CooldownManager:
    def __init__(self, cooldown_seconds: int):
        self.cooldown   = cooldown_seconds
        self._last_time = 0
        self._lock      = threading.Lock()

    def is_ready(self) -> bool:
        with self._lock:
            return (time.time() - self._last_time) >= self.cooldown

    def reset(self):
        with self._lock:
            self._last_time = time.time()


def _speak(message: str):
    try:
        import pyttsx3
        engine = pyttsx3.init()
        engine.setProperty('rate',   config.VOICE_RATE)
        engine.setProperty('volume', config.VOICE_VOLUME)
        engine.say(message)
        engine.runAndWait()
        engine.stop()
    except Exception as e:
        print(f"[VoiceAlert] Error: {e}")


def send_voice_alert(survivor_count: int):
    msg = (
        "1 survivor detected. Rescue team please respond."
        if survivor_count == 1
        else f"{survivor_count} survivors detected. Rescue team please respond."
    )
    print(f"[VoiceAlert] Speaking: '{msg}'")
    threading.Thread(target=_speak, args=(msg,), daemon=True).start()


def _send_email(
    survivor_count : int,
    screenshot_path: str,
    lat            : float = None,
    lon            : float = None,
    address        : str   = "",
    gps_source     : str   = "",
):
    try:
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        lat_str   = f"{lat:.6f}" if lat else "N/A"
        lon_str   = f"{lon:.6f}" if lon else "N/A"
        maps_link = (
            f"https://www.google.com/maps?q={lat},{lon}"
            if lat and lon else "N/A"
        )

        msg            = MIMEMultipart()
        msg["From"]    = config.EMAIL_SENDER
        msg["To"]      = config.EMAIL_RECEIVER
        msg["Subject"] = (
            f"🚨 SURVIVOR ALERT — {survivor_count} Detected | "
            f"📍 {lat_str}, {lon_str}"
        )

        body = (
            f"DRONE RESCUE SYSTEM — SURVIVOR ALERT\n"
            f"{'─' * 45}\n"
            f"Survivors Detected : {survivor_count}\n"
            f"Detection Time     : {timestamp}\n"
            f"{'─' * 45}\n"
            f"📍 GPS LOCATION\n"
            f"  Latitude         : {lat_str}\n"
            f"  Longitude        : {lon_str}\n"
            f"  Address          : {address or 'N/A'}\n"
            f"  GPS Source       : {gps_source or 'N/A'}\n"
            f"  Google Maps      : {maps_link}\n"
            f"{'─' * 45}\n"
            f"📸 Screenshot      : {os.path.basename(screenshot_path)}\n"
            f"{'─' * 45}\n"
            f"Please dispatch the rescue team immediately.\n\n"
            f"— AI Rescue Drone System"
        )
        msg.attach(MIMEText(body, "plain"))

        # Attach screenshot
        if screenshot_path and os.path.exists(screenshot_path):
            with open(screenshot_path, "rb") as f:
                part = MIMEBase("application", "octet-stream")
                part.set_payload(f.read())
            encoders.encode_base64(part)
            part.add_header(
                "Content-Disposition",
                f"attachment; filename={os.path.basename(screenshot_path)}"
            )
            msg.attach(part)
            print(f"[EmailAlert] Screenshot attached: {screenshot_path}")

        # ✅ FIXED: port 587 uses STARTTLS, not SMTP_SSL
        with smtplib.SMTP(config.SMTP_SERVER, config.SMTP_PORT) as server:
            server.ehlo()
            server.starttls()
            server.ehlo()
            server.login(config.EMAIL_SENDER, config.EMAIL_PASSWORD)
            server.sendmail(
                config.EMAIL_SENDER,
                config.EMAIL_RECEIVER,
                msg.as_string()
            )
        print(f"[EmailAlert] ✅ Email sent → {config.EMAIL_RECEIVER}")

    except smtplib.SMTPAuthenticationError:
        print("[EmailAlert] ❌ Auth failed. Check Gmail App Password.")
    except Exception as e:
        print(f"[EmailAlert] ❌ Error: {e}")


def send_email_alert(
    survivor_count : int,
    screenshot_path: str,
    lat            : float = None,
    lon            : float = None,
    address        : str   = "",
    gps_source     : str   = "",
):
    threading.Thread(
        target = _send_email,
        args   = (survivor_count, screenshot_path, lat, lon, address, gps_source),
        daemon = True,
    ).start()


cooldown_manager = CooldownManager(config.ALERT_COOLDOWN_SECONDS)


def trigger_alert(
    survivor_count : int,
    screenshot_path: str,
    lat            : float = None,
    lon            : float = None,
    address        : str   = "",
    gps_source     : str   = "",
):
    if survivor_count <= 0:
        return
    if not cooldown_manager.is_ready():
        remaining = config.ALERT_COOLDOWN_SECONDS - (time.time() - cooldown_manager._last_time)
        print(f"[Alert] Cooldown active. Next alert in {remaining:.1f}s.")
        return
    cooldown_manager.reset()
    send_voice_alert(survivor_count)
    send_email_alert(survivor_count, screenshot_path, lat, lon, address, gps_source)
