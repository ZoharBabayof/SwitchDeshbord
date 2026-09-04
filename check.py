import os
import re
import time

from dotenv import load_dotenv
from netmiko import ConnectHandler
from prometheus_client import start_http_server, Gauge


# ============================================================
# Environment
# ============================================================

load_dotenv()

device = {
    "device_type": "cisco_ios",
    "host": os.getenv("CISCO_HOST"),
    "username": os.getenv("CISCO_USERNAME"),
    "password": os.getenv("CISCO_PASSWORD"),
    "port": int(os.getenv("CISCO_PORT", "22")),
}


# ============================================================
# Prometheus Metrics
# ============================================================

switch_up = Gauge(
    "switch_up",
    "Whether the switch is reachable"
)

connected_port = Gauge(
    "switch_connected_port",
    "Port currently has an active connection",
    ["interface"]
)

unused_port = Gauge(
    "switch_unused_port",
    "Port is enabled but has no active connection",
    ["interface"]
)

disabled_port = Gauge(
    "switch_disabled_port",
    "Port is administratively disabled",
    ["interface"]
)

cpu_usage = Gauge(
    "switch_cpu_usage_percent",
    "Switch CPU utilization percentage"
)

vtp_version = Gauge(
    "switch_vtp_version",
    "VTP version currently running on the switch"
)

vtp_version_expected = Gauge(
    "switch_vtp_version_expected",
    "Expected VTP version"
)

vtp_version_mismatch = Gauge(
    "switch_vtp_version_mismatch",
    "VTP version does not match expected version"
)

stp_bpdu_guard = Gauge(
    "switch_stp_bpdu_guard",
    "Whether BPDU Guard Default is enabled"
)

stp_portfast = Gauge(
    "switch_stp_portfast",
    "Whether PortFast Default is enabled"
)


# ============================================================
# Interface Parser
# ============================================================

def parse_interfaces(output):

    for line in output.splitlines():

        line = line.strip()

        match = re.match(
            r"^(Gi\S+|Fa\S+|Te\S+|Twe\S+)\s+.*?\s+"
            r"(connected|notconnect|disabled)\s+",
            line,
            re.IGNORECASE
        )

        if not match:
            continue

        interface = match.group(1)
        status = match.group(2).lower()

        # Reset all states
        connected_port.labels(interface).set(0)
        unused_port.labels(interface).set(0)
        disabled_port.labels(interface).set(0)

        if status == "connected":

            connected_port.labels(interface).set(1)

        elif status == "notconnect":

            unused_port.labels(interface).set(1)

        elif status == "disabled":

            disabled_port.labels(interface).set(1)


# ============================================================
# VTP Parser
# ============================================================

def parse_vtp(output):

    match = re.search(
        r"VTP version running\s*:\s*(\d+)",
        output,
        re.IGNORECASE
    )

    expected_version = 2

    vtp_version_expected.set(expected_version)

    if not match:

        print("⚠️ Could not detect VTP version")

        vtp_version.set(0)
        vtp_version_mismatch.set(1)

        return

    version = int(match.group(1))

    vtp_version.set(version)

    if version != expected_version:

        vtp_version_mismatch.set(1)

        print(
            f"⚠️ VTP mismatch: "
            f"found {version}, expected {expected_version}"
        )

    else:

        vtp_version_mismatch.set(0)

        print(
            f"✅ VTP version OK: {version}"
        )


# ============================================================
# CPU Parser
# ============================================================

def parse_cpu(output):

    match = re.search(
        r"CPU utilization.*?(\d+)%\s*/\s*(\d+)%",
        output,
        re.IGNORECASE
    )

    if not match:

        print("⚠️ Could not detect CPU utilization")

        return

    five_second_cpu = int(match.group(1))

    cpu_usage.set(five_second_cpu)

    print(
        f"CPU utilization: {five_second_cpu}%"
    )


# ============================================================
# STP Parser
# ============================================================

def parse_stp(output):

    # --------------------------------------------------------
    # PortFast Default
    # --------------------------------------------------------

    portfast_match = re.search(
        r"Portfast Default\s+is\s+(enabled|disabled)",
        output,
        re.IGNORECASE
    )

    if portfast_match:

        portfast_value = (
            1
            if portfast_match.group(1).lower() == "enabled"
            else 0
        )

        stp_portfast.set(portfast_value)

        print(
            f"STP PortFast Default: "
            f"{portfast_match.group(1)}"
        )

    else:

        print(
            "⚠️ Could not detect PortFast Default"
        )


    # --------------------------------------------------------
    # BPDU Guard Default
    # --------------------------------------------------------

    bpdu_guard_match = re.search(
        r"PortFast BPDU Guard Default\s+is\s+(enabled|disabled)",
        output,
        re.IGNORECASE
    )

    if bpdu_guard_match:

        bpdu_guard_value = (
            1
            if bpdu_guard_match.group(1).lower() == "enabled"
            else 0
        )

        stp_bpdu_guard.set(bpdu_guard_value)

        print(
            f"STP BPDU Guard Default: "
            f"{bpdu_guard_match.group(1)}"
        )

    else:

        print(
            "⚠️ Could not detect BPDU Guard Default"
        )


# ============================================================
# Collect Data
# ============================================================

def collect_switch_data():

    connection = None

    try:

        print("\nConnecting to Cisco switch...")

        connection = ConnectHandler(**device)

        print("✅ Connected!")

        switch_up.set(1)


        # ----------------------------------------------------
        # Interfaces
        # ----------------------------------------------------

        interfaces = connection.send_command(
            "show interfaces status"
        )

        parse_interfaces(interfaces)


        # ----------------------------------------------------
        # VTP
        # ----------------------------------------------------

        vtp = connection.send_command(
            "show vtp status"
        )

        parse_vtp(vtp)


        # ----------------------------------------------------
        # CPU
        # ----------------------------------------------------

        cpu = connection.send_command(
            "show processes cpu"
        )

        parse_cpu(cpu)


        # ----------------------------------------------------
        # STP
        # ----------------------------------------------------

        stp = connection.send_command(
            "show spanning-tree summary"
        )

        print("\n--- STP OUTPUT ---")
        print(stp)
        print("-----------------")

        parse_stp(stp)


        print("✅ Collection completed")


    except Exception as e:

        print(f"❌ Collection failed: {e}")

        switch_up.set(0)


    finally:

        if connection:

            connection.disconnect()

            print("Disconnected.")


# ============================================================
# Main
# ============================================================

if __name__ == "__main__":

    print("Starting Prometheus exporter...")

    start_http_server(8000)

    print("✅ Metrics available on port 8000")

    while True:

        collect_switch_data()

        # Collect every 30 seconds
        time.sleep(30)