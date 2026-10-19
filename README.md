# Microtek MTK GTI Solar Inverter (Deye OEM) — Home Assistant Integration

[![hacs_badge](https://img.shields.io/badge/HACS-Custom-orange.svg)](https://github.com/hacs/integration)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Home Assistant](https://img.shields.io/badge/Home%20Assistant-2024.1%2B-blue)](https://www.home-assistant.io/)

A custom Home Assistant component for reading live solar production, yield statistics, and diagnostics locally from **Microtek MTK GTI Series** (e.g. 3kW D11, 5kW, etc.) and compatible **Deye OEM** solar inverters equipped with WiFi/BLE loggers (`DYDB_WiBLE` firmware).

---

## ⚡ Highlights

- **100% Local & Cloud-Independent**: Communicates directly with your inverter's data logger over your local WiFi/LAN. No cloud account or internet connectivity required.
- **Reverse-Engineered Cryptography**: Fully implements the logger's proprietary hybrid RSA-2048 key exchange and zero-padded AES-128-CBC encryption.
- **Home Assistant Energy Dashboard Native**: `daily_production` and `total_production` sensors are fully compatible with Home Assistant's Energy Dashboard (`device_class: energy`, `state_class: total_increasing`).
- **Negligible Resource Usage**: Async non-blocking I/O via `aiohttp` and `DataUpdateCoordinator`. Consumes **~0.01% CPU** and **~1.5 MB RAM**.
- **Embedded Socket Protection**: Implements `force_close=True` and `Connection: close` to prevent socket starvation on the logger's single-threaded HTTP/1.0 microkernel.
- **UI Config Flow**: Interactive setup directly through Home Assistant UI (**Settings → Devices & Services → Add Integration**).

---

## 📊 Provided Entities

| Entity ID | Friendly Name | Unit | Class / State Class | Description |
|---|---|---|---|---|
| `sensor.microtek_solar_current_power` | Current Power | `W` | `power` / `measurement` | Realtime output power |
| `sensor.microtek_solar_daily_production` | Daily Production | `kWh` | `energy` / `total_increasing` | Today's accumulated solar yield |
| `sensor.microtek_solar_total_production` | Total Production | `kWh` | `energy` / `total_increasing` | Total lifetime solar yield |
| `sensor.microtek_solar_rated_power` | Rated Power | `W` | `power` | Inverter rated capacity (e.g. 3000 W) |
| `sensor.microtek_solar_alert_count` | Alert Count | — | `measurement` | Count of active error/alert codes |
| `sensor.microtek_solar_wifi_signal_level` | WiFi Signal Level | bars | `measurement` | Logger WiFi signal strength (1–5) |
| `binary_sensor.microtek_solar_cloud_connected` | Cloud Connected | — | `connectivity` | Cloud sync status |
| `binary_sensor.microtek_solar_fault_alert` | Fault Alert | — | `problem` | Hardware fault indicator |

---

## 🚀 Implementation Guide for Other Users

Setting this integration up takes less than 5 minutes:

### 1. Identify Inverter Logger IP & Credentials
1. Find your inverter logger's IP in your router's DHCP list (e.g. `192.168.1.100`).
2. *Tip:* Assign a static DHCP lease to ensure the IP does not change.
3. Verify access by browsing to `http://<YOUR_INVERTER_IP>/`.
4. Your login credentials are the administrator username and password configured during your inverter's initial WiFi setup (default is usually `admin` / `admin`).

### 2. Install the Integration

#### Method A: Manual Installation
1. Clone this repository or download the ZIP:
   ```bash
   git clone https://github.com/<your-username>/microtek-solar-ha.git
   ```
2. Copy the `custom_components/microtek_solar` folder into your Home Assistant `/config/custom_components/` directory:
   ```bash
   cp -r custom_components/microtek_solar /config/custom_components/
   ```
3. Restart Home Assistant:
   - Navigate to **Developer Tools → YAML → Restart Home Assistant**.

#### Method B: HACS (Custom Repository)
1. Open **HACS** in Home Assistant.
2. Click the top-right menu (`...`) and select **Custom repositories**.
3. Add this repository URL, choose category **Integration**, and download.
4. Restart Home Assistant.

### 3. Add Integration via UI
1. Navigate to **Settings → Devices & Services → Add Integration**.
2. Search for **Microtek Solar**.
3. Enter your parameters:
   - **Host / IP**: `192.168.1.X` (your inverter's local IP)
   - **Username**: `admin` (or your configurator username)
   - **Password**: `your_inverter_password`
   - **Update Interval**: `30` (seconds)
4. Click **Submit**. All entities and the inverter device will be added instantly!

---

## ☀️ Home Assistant Energy Dashboard Setup

1. In Home Assistant, open **Settings → Dashboards → Energy**.
2. Under **Solar Panels**, click **Add Solar Production**.
3. Select `sensor.microtek_solar_inverter_microtek_solar_daily_production` (or `total_production`).
4. Click **Save**.

---

## 🖥️ Standalone CLI Tool (Without Home Assistant)

A standalone script is included in [`tools/test_logger.py`](tools/test_logger.py) to test querying the inverter directly from any terminal on your local network:

```bash
pip install aiohttp cryptography
python3 tools/test_logger.py --host 192.168.1.100 --user admin --password "your_password"
```

---

## 📚 Technical Documentation

- **[Implementation & Setup Guide](docs/SETUP_GUIDE.md)**: Detailed step-by-step setup instructions, network configuration, and FAQ.
- **[Reverse Engineering Guide](docs/REVERSE_ENGINEERING.md)**: Technical breakdown of the logger firmware, RSA-2048 + zero-padded AES-128-CBC protocol, and JSON telemetry schemas.
- **[Resource & Performance Analysis](docs/RESOURCE_ANALYSIS.md)**: In-depth measurement of CPU, memory, socket, and network overhead.
- **[Dashboard Configurations](dashboards/)**: Ready-to-use Lovelace YAML for both Overview cards and dedicated Section dashboards.

---

## ⚖️ License
Released under the [MIT License](LICENSE).
