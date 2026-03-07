# gps_mapper.py — AIRSS Drone System

import time
import threading
import requests
import folium
from folium.plugins import MarkerCluster, Fullscreen, MiniMap, HeatMap
from datetime import datetime
import os

import config
from shared_state import state


class GPSMapper:

    def __init__(self):
        self._marker_count    = 0
        self._markers         = []
        self._heat_points     = []
        self._geocode_cache   = {}
        self._rebuild_needed  = False
        self._rebuild_lock    = threading.Lock()

        print(f"[GPSMapper] Initialised. Base: {config.BASE_LOCATION}")
        print(f"[GPSMapper] ℹ️  Testing mode — using BASE_LOCATION as GPS source.")

        self._rebuild_and_render()
        threading.Thread(target=self._map_builder_loop, daemon=True).start()

    # ══════════════════════════════════════════════════
    # Background map builder — fires every 3s
    # ══════════════════════════════════════════════════

    def _map_builder_loop(self):
        while True:
            time.sleep(3)
            with self._rebuild_lock:
                needed = self._rebuild_needed
                self._rebuild_needed = False
            if needed:
                self._rebuild_and_render()

    # ══════════════════════════════════════════════════
    # GPS
    # ══════════════════════════════════════════════════

    def get_real_gps(self) -> tuple:
        return self._fetch_gps()

    def _fetch_gps(self) -> tuple:
        # ── Testing mode: always use BASE_LOCATION ────────────────────────
        # Phone = drone, not moving far → BASE_LOCATION is accurate enough.
        # To switch to live phone GPS later, replace this method with the
        # full _fetch_ipwebcam_gps() version.
        lat     = config.BASE_LOCATION[0]
        lon     = config.BASE_LOCATION[1]
        address = self._reverse_geocode(lat, lon)
        return lat, lon, address, "Base Location (Testing Mode)"

    def _reverse_geocode(self, lat: float, lon: float) -> str:
        key = (round(lat, 3), round(lon, 3))
        if key in self._geocode_cache:
            return self._geocode_cache[key]
        try:
            resp = requests.get(
                f"https://nominatim.openstreetmap.org/reverse"
                f"?lat={lat}&lon={lon}&format=json",
                headers={"User-Agent": "AIRSSDroneSystem/1.0"},
                timeout=5,
            )
            if resp.status_code == 200:
                address = resp.json().get("display_name", f"{lat}, {lon}")
                self._geocode_cache[key] = address
                return address
        except Exception:
            pass
        return f"{lat:.6f}, {lon:.6f}"

    # ══════════════════════════════════════════════════
    # Add Markers
    # ══════════════════════════════════════════════════

    def add_survivor_marker(
        self,
        lat        : float,
        lon        : float,
        count      : int,
        screenshot : str  = "",
        timestamp  : str  = "",
        address    : str  = "",
        source     : str  = "",
        confidences: list = None,
    ):
        self._marker_count += 1
        conf_str = (
            ", ".join(str(round(c, 2)) for c in confidences)
            if confidences else "N/A"
        )
        self._markers.append({
            "lat"       : lat,
            "lon"       : lon,
            "count"     : count,
            "timestamp" : timestamp or datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "address"   : (address or f"{lat},{lon}")[:65],
            "source"    : source,
            "conf_str"  : conf_str,
            "marker_id" : self._marker_count,
            "type"      : "drone",
            "screenshot": screenshot,
        })
        self._heat_points.append([lat, lon, max(1, count)])
        print(
            f"[GPSMapper] Marker #{self._marker_count} "
            f"({lat}, {lon}) | {count} survivor(s) | {source}"
        )
        with self._rebuild_lock:
            self._rebuild_needed = True

    def add_self_reported_marker(
        self,
        lat      : float,
        lon      : float,
        timestamp: str = "",
    ):
        self._marker_count += 1
        self._markers.append({
            "lat"       : lat,
            "lon"       : lon,
            "count"     : 1,
            "timestamp" : timestamp or datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "address"   : f"{lat:.5f}, {lon:.5f}",
            "source"    : "Rescue Portal (Self-Reported)",
            "conf_str"  : "N/A",
            "marker_id" : self._marker_count,
            "type"      : "self_reported",
            "screenshot": "",
        })
        self._heat_points.append([lat, lon, 1])
        print(f"[GPSMapper] Self-reported pin: ({lat}, {lon})")
        with self._rebuild_lock:
            self._rebuild_needed = True

    # ══════════════════════════════════════════════════
    # Map Rebuild
    # ══════════════════════════════════════════════════

    def _rebuild_and_render(self):
        try:
            if self._markers:
                latest = self._markers[-1]
                center = [latest["lat"], latest["lon"]]
                zoom   = 17
            else:
                center = config.BASE_LOCATION
                zoom   = 15

            m = folium.Map(
                location   = center,
                zoom_start = zoom,
                tiles      = "OpenStreetMap",
            )

            folium.TileLayer(
                tiles=(
                    "https://server.arcgisonline.com/ArcGIS/rest/"
                    "services/World_Imagery/MapServer/tile/{z}/{y}/{x}"
                ),
                attr    = "Esri World Imagery",
                name    = "Satellite",
                overlay = False,
                control = True,
            ).add_to(m)

            Fullscreen(position="topright").add_to(m)
            MiniMap(toggle_display=True).add_to(m)

            cluster = MarkerCluster(name="Detections").add_to(m)

            for mk in self._markers:
                if mk["type"] == "drone":
                    color   = "red"
                    icon_nm = "user"
                    title   = f"Survivor(s) Detected: {mk['count']}"
                else:
                    color   = "orange"
                    icon_nm = "flag"
                    title   = "Self-Reported Rescue"

                ss_html = ""
                if mk.get("screenshot") and os.path.isfile(mk["screenshot"]):
                    ss_html = (
                        f'<br><img src="/screenshots/'
                        f'{os.path.basename(mk["screenshot"])}" '
                        f'style="max-width:260px;margin-top:6px;'
                        f'border-radius:6px;border:1px solid #333;">'
                    )

                popup_html = (
                    f"<b>#{mk['marker_id']} — {title}</b><br>"
                    f"<b>Time:</b> {mk['timestamp']}<br>"
                    f"<b>GPS Source:</b> {mk['source']}<br>"
                    f"<b>Address:</b> {mk['address']}<br>"
                    f"<b>Confidence:</b> {mk['conf_str']}"
                    f"{ss_html}"
                )

                folium.Marker(
                    location = [mk["lat"], mk["lon"]],
                    popup    = folium.Popup(popup_html, max_width=300),
                    tooltip  = title,
                    icon     = folium.Icon(color=color, icon=icon_nm, prefix="fa"),
                ).add_to(cluster)

            if self._heat_points:
                HeatMap(
                    self._heat_points,
                    radius      = 35,
                    blur        = 20,
                    min_opacity = 0.4,
                    gradient    = {
                        "0.0": "blue",  "0.4": "cyan",
                        "0.6": "lime",  "0.8": "yellow", "1.0": "red",
                    },
                    name = "Heat Map",
                ).add_to(m)

            folium.LayerControl().add_to(m)

            state.update_map_html(m._repr_html_())
            print(f"[GPSMapper] Map rebuilt — {len(self._markers)} markers.")

        except Exception as e:
            print(f"[GPSMapper] Map build error: {e}")
