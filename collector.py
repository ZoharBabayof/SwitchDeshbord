import os
import re
import time

from dotenv import load_dotenv
from netmiko import ConnectHandler

from prometheus_client import start_http_server, Gauge


load_dotenv()


device = {
    "device_type": "cisco_ios",
    "host": os.getenv("CISCO_HOST"),
    "username": os.getenv("CISCO_USERNAME"),
    "password": os.getenv("CISCO_PASSWORD"),
    "port": int(os.getenv("CISCO_PORT", "22")),
}


# =========================
# Prometheus Metrics
# =========================

switch_up = Gauge(
    "switch_up",
    "Whether the switch is reachable"
)

unused_port = Gauge(
    "switch_unused_port",
    "Port is enabled but has no active connection",
    ["interface"]
)

connected_port = Gauge(
    "switch_connected_port",
    "Port currently has an active connection",
    ["interface"]
)

disabled_port = Gauge(
    "switch_disabled_port",
    "Port is administratively disabled",
    ["interface"]
)

interface_errors = Gauge(
    "switch_interface_errors",
    "Interface input/output errors",
    ["interface"]
)

cpu_usage = Gauge(
    "switch_cpu_usage_percent",
    "Switch CPU utilization percentage"
)

vtp_version = Gauge(
    "switch_vtp_version",
    "VTP version configured on the switch"
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
    "BPDU Guard status"
)

stp_portfast = Gauge(
    "switch_stp_portfast",
    "PortFast status"
)


# =========================
# Cisco Collection
# =========================

def collect_switch_data():

    connection = None

    try:
        print("Connecting to Cisco switch...")

        connection = ConnectHandler(**device)

        print("✅ Connected!")

        switch_up.set(1)

        # -------------------------
        # Interfaces
        # -------------------------

        interfaces = connection.send_command(
            "show interfaces status"
        )

        parse_interfaces(interfaces)

        # -------------------------
        # VTP
        # -------------------------

        vtp = connection.send_command(
            "show vtp status"
        )

        parse_vtp(vtp)

        # -------------------------
        # CPU
        # -------------------------

        cpu = connection.send_command(
            "show processes cpu"
        )

        parse_cpu(cpu)

        # -------------------------
        # STP
        # -------------------------

        stp = connection.send_command(
            "show spanning-tree summary"
        )

        parse_stp(stp)

        print("✅ Collection completed")

    except Exception as e:

        print(f"❌ Collection failed: {e}")

        switch_up.set(0)

    finally:

        if connection:
            connection.disconnect()


# =========================
# Interface Parser
# =========================

def parse_interfaces(output):

    for line in output.splitlines():

        line = line.strip()

        # Example:
        # Gi1/0/1    connected    10

        match = re.match(
            r"^(Gi\S+|Fa\S+|Te\S+|Twe\S+)\s+.*?\s+"
            r"(connected|notconnect|disabled)\s+",
            line
        )

        if not match:
            continue

        interface = match.group(1)
        status = match.group(2)

        # Reset values first

        unused_port.labels(interface).set(0)
        connected_port.labels(interface).set(0)
        disabled_port.labels(interface).set(0)

        if status == "connected":

            connected_port.labels(interface).set(1)

        elif status == "notconnect":

            unused_port.labels(interface).set(1)

        elif status == "disabled":

            disabled_port.labels(interface).set(1)


# =========================
# VTP Parser
# =========================

def parse_vtp(output):

    match = re.search(
        r"VTP version\s*:\s*(\d+)",
        output,
        re.IGNORECASE
    )

    if not match:
        return

    version = int(match.group(1))

    expected_version = 2

    vtp_version.set(version)
    vtp_version_expected.set(expected_version)

    if version != expected_version:

        vtp_version_mismatch.set(1)

    else:

        vtp_version_mismatch.set(0)


# =========================
# CPU Parser
# =========================

def parse_cpu(output):

    match = re.search(
        r"CPU utilization.*?(\d+)%\s*\/\s*(\d+)%",
        output
    )

    if match:

        five_second = int(match.group(1))

        cpu_usage.set(five_second)


# =========================
# STP Parser
# =========================

def parse_stp(output):

    bpdu_match = re.search(
        r"BPDU Guard is enabled",
        output,
        re.IGNORECASE
    )

    portfast_match = re.search(
        r"PortFast is enabled",
        output,
        re.IGNORECASE
    )

    stp_bpdu_guard.set(
        1 if bpdu_match else 0
    )

    stp_portfast.set(
        1 if portfast_match else 0
    )


# =========================
# Main
# =========================

if __name__ == "__main__":

    print("Starting Prometheus exporter...")

    # Prometheus will scrape:
    #
    # http://localhost:8000/metrics

    start_http_server(8000)

    print("✅ Metrics available on port 8000")

    while True:

        collect_switch_data()

        # Collect every 30 seconds

        time.sleep(30)