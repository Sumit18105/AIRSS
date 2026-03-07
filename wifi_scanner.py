# wifi_scanner.py
# Simulates passive WiFi phone detection for demo.
# In production: replace _simulate_scan() with scapy monitor mode sniffing.
# Logic, data structures and dashboard integration are identical.

import time
import random
import threading
from datetime import datetime
from shared_state import state


class PassivePhoneDetector:
    """
    Simulates passive WiFi probe request detection.
    Each 'device' represents a phone broadcasting WiFi probe requests.

    Real hardware replacement:
        from scapy.all import sniff, Dot11ProbeReq
        sniff(iface="wlan0mon", prn=handler, store=False)
    """

    PHONE_VENDORS = [
        "Samsung", "Apple", "Xiaomi", "Realme",
        "OnePlus", "Vivo", "Oppo", "Motorola",
    ]

    def __init__(self, scan_interval: int = 15):
        self.scan_interval  = scan_interval
        self._devices       = {}       # MAC → device info
        self._running       = False
        self._lock          = threading.Lock()
        self._thread        = None
        self._scan_count    = 0

    def start(self):
        self._running = True
        self._thread  = threading.Thread(
            target = self._scan_loop,
            daemon = True,
        )
        self._thread.start()
        print("[WiFiScanner] 🔍 Passive WiFi scanning started (simulation mode).")
        print("[WiFiScanner] ℹ️  Replace _simulate_scan() with scapy for real hardware.")

    def stop(self):
        self._running = False
        print("[WiFiScanner] Scanning stopped.")

    def _scan_loop(self):
        while self._running:
            self._simulate_scan()
            self._push_to_state()
            time.sleep(self.scan_interval)

    def _simulate_scan(self):
        """
        Simulates phones broadcasting WiFi probe requests.
        In production: scapy sniffs real Dot11ProbeReq packets.
        """
        self._scan_count += 1

        # Simulate 1-4 devices detected per scan
        n_devices = random.randint(1, 4)

        for _ in range(n_devices):
            mac    = self._random_mac()
            rssi   = random.randint(-85, -40)   # Realistic RSSI range
            vendor = random.choice(self.PHONE_VENDORS)

            with self._lock:
                if mac not in self._devices:
                    self._devices[mac] = {
                        "mac"       : mac,
                        "vendor"    : vendor,
                        "first_seen": datetime.now().strftime("%H:%M:%S"),
                        "last_seen" : datetime.now().strftime("%H:%M:%S"),
                        "rssi"      : rssi,
                        "distance"  : self.estimate_distance(rssi),
                        "probes"    : 1,
                        "status"    : "ACTIVE",
                    }
                    print(
                        f"[WiFiScanner] 📱 New device: {mac} | "
                        f"{vendor} | RSSI: {rssi} dBm | "
                        f"{self.estimate_distance(rssi)}"
                    )
                else:
                    self._devices[mac]["rssi"]      = rssi
                    self._devices[mac]["distance"]  = self.estimate_distance(rssi)
                    self._devices[mac]["last_seen"] = datetime.now().strftime("%H:%M:%S")
                    self._devices[mac]["probes"]   += 1

        # Mark stale devices as LOST
        with self._lock:
            for mac, dev in self._devices.items():
                if dev["probes"] < self._scan_count - 3:
                    dev["status"] = "LOST"

    def _push_to_state(self):
        """Push device list to SharedState for dashboard display."""
        with self._lock:
            devices_list = list(self._devices.values())
        state.update_wifi_devices(devices_list)

    def get_devices(self) -> list:
        with self._lock:
            return list(self._devices.values())

    def get_active_count(self) -> int:
        with self._lock:
            return sum(
                1 for d in self._devices.values()
                if d["status"] == "ACTIVE"
            )

    @staticmethod
    def estimate_distance(rssi: int) -> str:
        if rssi >= -50: return "Very Close  (<5m)"
        if rssi >= -65: return "Close       (5–15m)"
        if rssi >= -75: return "Medium      (15–40m)"
        if rssi >= -85: return "Far         (40–100m)"
        return                 "Very Far    (>100m)"

    @staticmethod
    def _random_mac() -> str:
        return ":".join(
            f"{random.randint(0, 255):02X}" for _ in range(6)
        )


# Global instance
scanner = PassivePhoneDetector(scan_interval=15)
