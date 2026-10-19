# Microtek Solar Inverter — Setup & Implementation Guide

This guide walks you through setting up the local **Microtek Solar Inverter** integration in Home Assistant, configuring entities, and adding solar production metrics to your dashboards.

---

## 📋 Compatibility

This integration is designed for:
- **Microtek MTK GTI Series** (Single-Phase & Three-Phase Grid-Tie Inverters, e.g., 3kW D11, 5kW, etc.).
- **Deye / I-Grid OEM** inverters equipped with `DYDB_WiBLE` or similar web-configured WiFi/BLE data loggers.
- Any Home Assistant instance (Home Assistant OS, Container, or Supervised 2024.1+).

---

## 🔎 Step 1: Find Your Inverter Logger IP & Web Credentials

1. **Find the Local IP Address**:
   - Log into your home router's admin page.
   - Check the **DHCP Client List** / **Connected Devices**.
   - Look for a device named `DYDB_WiBLE`, `Wi-Fi_Kit`, or an unknown device with an active IP (e.g., `192.168.1.100`).
   - *Recommendation:* Assign a **Static DHCP Lease / Reserved IP** to the logger so its IP address never changes.

2. **Verify Web Access**:
   - Open a browser and navigate to `http://<YOUR_INVERTER_IP>/`.
   - You should see the login prompt: `.::Welcome to the Web-Based Configurator::.`.

3. **Determine Your Credentials**:
   - Default factory credentials:
     - **Username**: `admin`
     - **Password**: `admin`
   - If changed during commissioning (e.g. via the installer or solar app), use the administrative username and password you configured.

---

## 📦 Step 2: Install the Integration

### Method A: Manual Installation (Recommended)
1. Download or clone this repository:
   ```bash
   git clone https://github.com/<your-username>/microtek-solar-ha.git
   ```
2. Copy the `custom_components/microtek_solar` folder into your Home Assistant config folder:
   ```bash
   # Example paths:
   # Home Assistant OS / Supervised:
   cp -r custom_components/microtek_solar /config/custom_components/

   # Home Assistant Container (Docker):
   cp -r custom_components/microtek_solar /var/lib/homeassistant/homeassistant/custom_components/
   ```
3. Restart Home Assistant:
   - Navigate to **Developer Tools → YAML → Restart Home Assistant** (or restart your Docker container).

### Method B: HACS (Custom Repository)
1. Open **HACS** in Home Assistant.
2. Click the three dots in the top right corner and select **Custom repositories**.
3. Enter the repository URL, select **Integration** as category, and click **Add**.
4. Search for **Microtek Solar** and click **Download**.
5. Restart Home Assistant.

---

## ⚙️ Step 3: Add the Integration in Home Assistant

1. In Home Assistant, navigate to **Settings → Devices & Services**.
2. Click **+ Add Integration** in the bottom right corner.
3. Search for **Microtek Solar** and select it.
4. Fill in the configuration dialog:
   - **IP Address**: Enter your logger's IP (e.g., `192.168.1.100`).
   - **Web UI Username**: Your configurator username (e.g., `admin`).
   - **Web UI Password**: Your configurator password (e.g., `your_password`).
   - **Update Interval**: `30` seconds (recommended 30–60s).
5. Click **Submit**.
6. Home Assistant will perform the RSA/AES cryptographic handshake, authenticate, and register your inverter device with all 8 telemetry sensors!

---

## ☀️ Step 4: Configure the Energy Dashboard

This integration exports sensors with native `device_class: energy` and `state_class: total_increasing` so Home Assistant can track solar generation automatically:

1. Open **Settings → Dashboards → Energy**.
2. Under **Solar Panels**, click **+ Add Solar Production**.
3. Select `sensor.microtek_solar_inverter_microtek_solar_daily_production` (or `total_production`).
4. Click **Save**.

Your solar generation will now appear on Home Assistant's official Energy graphs!

---

## 📊 Step 5: Dashboard Cards (Lovelace)

Pre-built YAML configurations are provided in the [`dashboards/`](../dashboards/) folder:

### 1. Overview Dashboard Live Widgets
To add the live power gauge and yield tiles to your existing dashboard, edit your dashboard and add the card configuration from [`dashboards/overview_cards.yaml`](../dashboards/overview_cards.yaml):

```yaml
type: horizontal-stack
cards:
  - type: gauge
    name: Live Solar Power
    entity: sensor.microtek_solar_inverter_microtek_solar_current_power
    min: 0
    max: 3000
    needle: true
    severity:
      green: 1500
      yellow: 600
      red: 0
  - type: vertical-stack
    cards:
      - type: tile
        entity: sensor.microtek_solar_inverter_microtek_solar_current_power
        name: Realtime Output
        icon: mdi:solar-power
        color: amber
      - type: tile
        entity: sensor.microtek_solar_inverter_microtek_solar_daily_production
        name: Today's Yield
        icon: mdi:calendar-today
        color: green
      - type: tile
        entity: sensor.microtek_solar_inverter_microtek_solar_total_production
        name: Total Lifetime Yield
        icon: mdi:counter
        color: blue
```

### 2. Dedicated Full-Page Solar Dashboard
If you want a complete, dedicated section dashboard with live power, 24-hour historical generation curve, and hardware health diagnostics, copy [`dashboards/solar_energy_dashboard.yaml`](../dashboards/solar_energy_dashboard.yaml) into a new dashboard view.

---

## 🛠️ Step 6: Standalone Terminal Verification Tool

If you want to test communication with your inverter without Home Assistant, use the included CLI tool:

```bash
# 1. Install dependencies
pip install aiohttp cryptography

# 2. Run test query
python3 tools/test_logger.py --host 192.168.1.100 --user admin --password "your_password"
```

---

## ❓ Frequently Asked Questions (FAQ)

### Q: Why not use Modbus port 8899?
**A:** On firmware `DYDB_WiBLE_1.2.1`, external Modbus TCP/UDP port `8899` is closed in Station mode. The web interface on port 80 is the only open local communication port.

### Q: Does this require internet access?
**A:** **No.** All queries occur directly across your local network. Your inverter can be completely blocked from the WAN / cloud if you prefer an air-gapped solar installation.

### Q: Will rapid polling crash the inverter?
**A:** The integration uses `force_close=True` and `Connection: close` on every request. This cleanly terminates TCP connections after each poll, ensuring the logger's microcontroller socket pool never exhausts.
