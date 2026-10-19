#!/usr/bin/env python3
"""
Standalone testing utility to query Microtek MTK GTI Solar Inverters directly from CLI.
Uses the integration's production MicrotekSolarApi engine.

Usage:
    python3 tools/test_logger.py --host 192.168.1.100 --user admin --password "your_password"
"""

import argparse
import asyncio
import os
import sys

# Ensure custom_components is on sys.path
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.abspath(os.path.join(SCRIPT_DIR, ".."))
sys.path.insert(0, os.path.join(REPO_ROOT, "custom_components", "microtek_solar"))

try:
    from api import MicrotekSolarApi
except ImportError as err:
    print(f"Error loading API module: {err}")
    print("Ensure you have aiohttp and cryptography installed:")
    print("  pip install aiohttp cryptography")
    sys.exit(1)


async def async_main():
    parser = argparse.ArgumentParser(description="Query Microtek Solar Inverter directly.")
    parser.add_argument("--host", default="192.168.1.100", help="Inverter IP address (e.g. 192.168.1.16)")
    parser.add_argument("--user", default="admin", help="Configurator username")
    parser.add_argument("--password", required=True, help="Configurator password")
    args = parser.parse_args()

    print(f"[*] Connecting to Microtek Inverter at {args.host}...")
    api = MicrotekSolarApi(args.host, args.user, args.password)
    try:
        data = await api.async_get_data()
        print("\n" + "=" * 55)
        print("          MICROTEK SOLAR INVERTER TELEMETRY")
        print("=" * 55)
        inv = data.get("inverter", {})
        device = data.get("device", {})
        info = {item["key"]: item["value"] for item in inv.get("info", [])}

        print(f"  Inverter S/N:       {inv.get('serialNum', 'N/A')}")
        print(f"  Firmware Version:   {inv.get('mainVersion', 'N/A')}")
        print(f"  Logger Version:     {device.get('firmwareVersion', 'N/A')}")
        print("-" * 55)
        print(f"  Current Power:      {info.get('currentPower', '0 W')}")
        print(f"  Today's Yield:      {info.get('yieldToday', '0 kWh')}")
        print(f"  Lifetime Total:     {info.get('totalYield', '0 kWh')}")
        print(f"  Rated Capacity:     {info.get('ratedPower', '3000 W')}")
        print("-" * 55)
        print(f"  Active Alerts:      {info.get('alerts', '0')}")
        print(f"  Cloud Connected:    {info.get('cloudConnected', '0')}")
        print(f"  WiFi Signal:        {device.get('sta', {}).get('signal', 'N/A')}/5 bars")
        print("=" * 55 + "\n")
    except Exception as err:
        print(f"[-] Failed to query inverter: {err}")
    finally:
        await api.close()


if __name__ == "__main__":
    asyncio.run(async_main())
