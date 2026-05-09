# Emobot

Emobot is a trimmed, working fork of the Desk-Emoji robot project for the current build.

## Supported Versions

- PC client: `pc_client/pc_client_v3.0.0`
- Firmware: `firmware/Arduino_Esp32s3/esp32s3_v2.0.1`

All legacy client and firmware versions have been removed from this repository to keep the build focused on the Emobot hardware and software path.

## Repository Layout

- `pc_client/pc_client_v3.0.0`: desktop control app
- `firmware/Arduino_Esp32s3/esp32s3_v2.0.1`: ESP32-S3 firmware
- `doc/`: assembly, firmware, and software guides

## Run The PC Client

On macOS or Linux:

```bash
cd pc_client/pc_client_v3.0.0
./start.sh
```

On Windows:

- open `pc_client/pc_client_v3.0.0`
- run `start.bat`

## Firmware Target

The maintained firmware target is ESP32-S3 only. Audio, gesture, OLED, servo, and network features are wired against the `esp32s3_v2.0.1` pin map and module set.

## License

This repository keeps the upstream GPLv3 license.
