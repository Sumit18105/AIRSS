# captive_portal.py — AIRSS Drone System
# DNS server that redirects ALL queries to drone IP
# Triggers captive portal popup on Android / iOS / Windows

import socket
import threading

import config


class CaptivePortalDNS:
    """
    Minimal DNS server that answers every A-record query
    with the drone hotspot IP, triggering the OS captive
    portal popup automatically on connected phones.

    Supports:
      Android  → connectivitycheck.gstatic.com / gen_204
      iOS      → captive.apple.com
      Windows  → www.msftconnecttest.com
      Any browser navigating to any URL
    """

    def __init__(self, host: str = "0.0.0.0", port: int = 53):
        self.host     = host
        self.port     = port
        self.redirect = config.HOTSPOT_IP
        self._running = False
        self._sock    = None

    def _build_response(self, data: bytes) -> bytes:
        try:
            transaction_id = data[:2]
            flags          = b'\x81\x80'
            qdcount        = data[4:6]
            ancount        = b'\x00\x01'
            nscount        = b'\x00\x00'
            arcount        = b'\x00\x00'

            header = (transaction_id + flags + qdcount +
                      ancount + nscount + arcount)

            question = data[12:]

            ip_bytes = bytes(map(int, self.redirect.split('.')))
            answer   = (
                b'\xc0\x0c'
                + b'\x00\x01'
                + b'\x00\x01'
                + b'\x00\x00\x00\x3c'
                + b'\x00\x04'
                + ip_bytes
            )

            return header + question + answer

        except Exception:
            return b''

    def _serve(self):
        while self._running:
            try:
                data, addr = self._sock.recvfrom(512)
                response   = self._build_response(data)
                if response:
                    self._sock.sendto(response, addr)
            except Exception:
                pass

    def start(self):
        try:
            self._sock = socket.socket(
                socket.AF_INET, socket.SOCK_DGRAM
            )
            self._sock.setsockopt(
                socket.SOL_SOCKET, socket.SO_REUSEADDR, 1
            )
            self._sock.settimeout(1.0)
            self._sock.bind((self.host, self.port))
            self._running = True
            t = threading.Thread(target=self._serve, daemon=True)
            t.start()
            print(
                f"[CaptivePortal] DNS running on port {self.port} "
                f"-> all queries redirect to {self.redirect}"
            )
        except PermissionError:
            print(
                "[CaptivePortal] Port 53 needs Administrator.\n"
                "               Right-click cmd -> Run as Administrator\n"
                "               then: py -3.10 main_v2.py"
            )
        except Exception as e:
            print(f"[CaptivePortal] DNS start error: {e}")

    def stop(self):
        self._running = False
        if self._sock:
            try:
                self._sock.close()
            except Exception:
                pass


dns_server = CaptivePortalDNS()
