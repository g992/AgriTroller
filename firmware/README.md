# Firmware Block

This directory holds the ESP32-S2 firmware that exposes two channels:

- **USB HID** – pushes key presses from the front panel to the SBC.
- **UART command channel** – receives register writes/reads from the Python host and toggles GPIO/backlight accordingly.

Organize source code using PlatformIO or ESP-IDF. Keep build artifacts inside `.pio/` or `build/` so Git stays clean. The Python service expects compiled images to land in this folder for staging OTA updates.
