@echo off
echo ================================================
echo   AIRSS - Starting Drone WiFi Hotspot
echo ================================================
echo.

netsh wlan set hostednetwork mode=allow ssid="AIRSS-RESCUE" key="rescue123"
netsh wlan start hostednetwork

netsh advfirewall firewall delete rule name="AIRSS Flask" >nul 2>&1
netsh advfirewall firewall delete rule name="AIRSS DNS"   >nul 2>&1

netsh advfirewall firewall add rule name="AIRSS Flask" ^
    dir=in action=allow protocol=TCP localport=5000

netsh advfirewall firewall add rule name="AIRSS DNS" ^
    dir=in action=allow protocol=UDP localport=53

echo.
echo Hotspot "AIRSS-RESCUE" is running.
echo Password : rescue123
echo.
echo Next step: py -3.10 main_v2.py  (run as Administrator)
echo.
pause
