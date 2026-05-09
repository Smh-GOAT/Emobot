# Emobot

这是为当前 Emobot 制作保留下来的精简版本仓库。

## 当前保留版本

- 上位机：`pc_client/pc_client_v3.0.0`
- 固件：`firmware/Arduino_Esp32s3/esp32s3_v2.0.1`

仓库中的历史客户端版本和旧固件版本都已移除，只保留当前 Emobot 需要的版本路径。

## 目录结构

- `pc_client/pc_client_v3.0.0`：桌面控制软件
- `firmware/Arduino_Esp32s3/esp32s3_v2.0.1`：ESP32-S3 固件
- `doc/`：组装、烧录和软件说明

## 启动上位机

macOS 或 Linux：

```bash
cd pc_client/pc_client_v3.0.0
./start.sh
```

Windows：

- 打开 `pc_client/pc_client_v3.0.0`
- 运行 `start.bat`

## 固件目标

当前维护目标仅为 ESP32-S3。音频、手势、OLED、舵机和联网能力都以 `esp32s3_v2.0.1` 这套硬件映射为准。

## 许可证

本仓库继续沿用上游 GPLv3 协议。
