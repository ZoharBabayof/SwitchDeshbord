import os
import re
import time
import logging

from dotenv import load_dotenv
from netmiko import ConnectHandler
from prometheus_client import Gauge, start_http_server


# ============================================================
# Configuration
# ============================================================

load_dotenv()

CISCO_HOST = os.getenv("CISCO_HOST")
CISCO_USERNAME = os.getenv("CISCO_USERNAME")
CISCO_PASSWORD = os.getenv("CISCO_PASSWORD")
CISCO_PORT = int(os.getenv("CISCO_PORT", "22"))

COLLECT_INTERVAL = 15
PROMETHEUS_PORT = 8000
EXPECTED_VTP_VERSION = 2


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)


# ============================================================
# Prometheus Metrics
# ============================================================

switch_up = Gauge(
    "switch_up",
    "Cisco switch connectivity"
)

switch_connected_port = Gauge(
    "switch_connected_port",
    "Whether a physical interface is connected",
    ["interface"]
)

switch_unused_port = Gauge(
    "switch_unused_port",
    "Whether a physical interface is unused/not connected",
    ["interface"]
)

switch_disabled_port = Gauge(
    "switch_disabled_port",
    "Whether a physical interface is disabled",
    ["interface"]
)

switch_port_vlan = Gauge(
    "switch_port_vlan",
    "Access VLAN configured on the interface",
    ["interface", "vlan"]
)

switch_vlan_configured = Gauge(
    "switch_vlan_configured",
    "Configured VLAN",
    ["vlan", "name"]
)

switch_vlan_count = Gauge(
    "switch_vlan_count",
    "Number of configured VLANs"
)

switch_svi_up = Gauge(
    "switch_svi_up",
    "Whether an SVI is operational",
    ["interface"]
)

switch_svi_ip_configured = Gauge(
    "switch_svi_ip_configured",
    "Whether an SVI has an IP configured",
    ["interface", "ip"]
)

switch_static_route = Gauge(
    "switch_static_route",
    "Configured static route",
    ["network", "mask", "next_hop"]
)

switch_static_route_count = Gauge(
    "switch_static_route_count",
    "Number of configured static routes"
)

switch_cpu_usage_percent = Gauge(
    "switch_cpu_usage_percent",
    "Cisco switch CPU utilization percentage"
)

switch_vtp_version = Gauge(
    "switch_vtp_version",
    "VTP version running"
)

switch_vtp_version_expected = Gauge(
    "switch_vtp_version_expected",
    "Expected VTP version"
)

switch_vtp_version_mismatch = Gauge(
    "switch_vtp_version_mismatch",
    "Whether VTP version differs from expected"
)

switch_vtp_client_mode = Gauge(
    "switch_vtp_client_mode",
    "Whether VTP is running in client mode"
)

switch_mst_enabled = Gauge(
    "switch_mst_enabled",
    "Whether MST is enabled"
)

switch_mst_revision = Gauge(
    "switch_mst_revision",
    "MST revision number"
)

switch_mst_region_name = Gauge(
    "switch_mst_region_name",
    "MST region",
    ["region"]
)

switch_mst_instance_vlan = Gauge(
    "switch_mst_instance_vlan",
    "MST instance VLAN mapping",
    ["instance", "mapping"]
)

switch_stp_mode = Gauge(
    "switch_stp_mode",
    "STP operating mode",
    ["mode"]
)

switch_stp_portfast = Gauge(
    "switch_stp_portfast",
    "Global PortFast default"
)

switch_stp_bpdu_guard = Gauge(
    "switch_stp_bpdu_guard",
    "Global BPDU Guard default"
)

switch_interface_portfast = Gauge(
    "switch_interface_portfast",
    "Whether PortFast is configured on interface",
    ["interface"]
)

switch_interface_bpdu_guard = Gauge(
    "switch_interface_bpdu_guard",
    "Whether BPDU Guard is configured on interface",
    ["interface"]
)

switch_interface_root_guard = Gauge(
    "switch_interface_root_guard",
    "Whether Root Guard is configured on interface",
    ["interface"]
)

switch_interface_loop_guard = Gauge(
    "switch_interface_loop_guard",
    "Whether Loop Guard is configured on interface",
    ["interface"]
)

switch_ios_xe_version = Gauge(
    "switch_ios_xe_version",
    "Cisco IOS XE version",
    ["version"]
)


# ============================================================
# Interface Helpers
# ============================================================

def normalize_interface_name(interface):
    """
    Normalize Cisco interface names to their short form.

    Examples:
        GigabitEthernet1/0/1 -> Gi1/0/1
        TenGigabitEthernet1/1 -> Te1/1
        TwentyFiveGigE1/0/1 -> Twe1/0/1
        FastEthernet1/0/1 -> Fa1/0/1
    """

    if interface.startswith("GigabitEthernet"):
        return interface.replace(
            "GigabitEthernet",
            "Gi",
            1
        )

    if interface.startswith("TenGigabitEthernet"):
        return interface.replace(
            "TenGigabitEthernet",
            "Te",
            1
        )

    if interface.startswith("TwentyFiveGigE"):
        return interface.replace(
            "TwentyFiveGigE",
            "Twe",
            1
        )

    if interface.startswith("FastEthernet"):
        return interface.replace(
            "FastEthernet",
            "Fa",
            1
        )

    return interface


def is_physical_interface(interface):
    """
    Determine whether an interface is a physical Ethernet interface.
    """

    return (
        interface.startswith("GigabitEthernet")
        or interface.startswith("Gi")
        or interface.startswith("TenGigabitEthernet")
        or interface.startswith("Te")
        or interface.startswith("TwentyFiveGigE")
        or interface.startswith("Twe")
        or interface.startswith("FastEthernet")
        or interface.startswith("Fa")
    )


# ============================================================
# Parsers
# ============================================================

def parse_interfaces(output):
    """
    Parse:
        show interfaces status

    Returns:
        {
            "Gi1/0/1": "connected",
            "Gi1/0/3": "disabled",
            ...
        }
    """

    interfaces = {}

    for line in output.splitlines():

        line = line.strip()

        if not line:
            continue

        match = re.match(
            r"^(Gi\S+|GigabitEthernet\S+|Te\S+|TenGigabitEthernet\S+|"
            r"Twe\S+|TwentyFiveGigE\S+|Fa\S+|FastEthernet\S+)\s+"
            r"(\S+)\s+(\S+)",
            line
        )

        if not match:
            continue

        interface = normalize_interface_name(
            match.group(1)
        )

        status = match.group(2).lower()

        if status == "connected":

            interfaces[interface] = "connected"

        elif status in ("notconnect", "notconnected"):

            interfaces[interface] = "unused"

        elif status in ("disabled", "err-disabled"):

            interfaces[interface] = "disabled"

    return interfaces


def parse_port_vlans(output):
    """
    Parse access VLANs from:
        show vlan
    """

    port_vlans = {}

    for line in output.splitlines():

        line = line.strip()

        match = re.match(
            r"^(\d+)\s+\S+\s+\S+\s+(.+)$",
            line
        )

        if not match:
            continue

        vlan = match.group(1)
        ports = match.group(2)

        if int(vlan) >= 1002:
            continue

        for port in ports.split():

            if is_physical_interface(port):

                port = normalize_interface_name(port)

                port_vlans[port] = vlan

    return port_vlans


def parse_vlans(output):
    """
    Parse active VLANs from:
        show vlan
    """

    vlans = {}

    for line in output.splitlines():

        line = line.strip()

        match = re.match(
            r"^(\d+)\s+(\S.*?)\s+"
            r"(active|act/unsup|suspended|act/lshut|shutdown)\s*(.*)$",
            line
        )

        if not match:
            continue

        vlan_id = int(match.group(1))
        vlan_name = match.group(2).strip()
        status = match.group(3)

        # Ignore legacy VLANs 1002-1005
        if vlan_id >= 1002:
            continue

        # Only count active VLANs
        if status != "active":
            continue

        vlans[str(vlan_id)] = vlan_name

    return vlans


def parse_svis(output):
    """
    Parse SVI information from:
        show ip interface brief
    """

    svis = {}

    for line in output.splitlines():

        line = line.strip()

        match = re.match(
            r"^(Vlan\d+)\s+(\S+)\s+\S+\s+\S+\s+(\S+)\s+(\S+)$",
            line
        )

        if not match:
            continue

        interface = match.group(1)
        ip = match.group(2)
        status = match.group(3)
        protocol = match.group(4)

        svis[interface] = {
            "ip": ip,
            "status": status,
            "protocol": protocol
        }

    return svis


def parse_vtp(output):
    """
    Parse VTP version and operating mode from:
        show vtp status
    """

    version = None
    client_mode = 0

    match = re.search(
        r"VTP version running\s*:\s*(\d+)",
        output,
        re.IGNORECASE
    )

    if match:
        version = int(match.group(1))

    mode_match = re.search(
        r"VTP Operating Mode\s*:\s*(\S+)",
        output,
        re.IGNORECASE
    )

    if mode_match:

        client_mode = (
            1
            if mode_match.group(1).lower() == "client"
            else 0
        )

    return version, client_mode


def parse_cpu(output):
    """
    Parse CPU utilization from:
        show processes cpu
    """

    patterns = [
        r"CPU utilization for five seconds:\s*(\d+)%?",
        r"CPU utilization for five seconds:\s*([\d.]+)%"
    ]

    for pattern in patterns:

        match = re.search(
            pattern,
            output,
            re.IGNORECASE
        )

        if match:
            return float(match.group(1))

    return 0


def parse_stp(output):
    """
    Parse global STP settings from:
        show spanning-tree summary
    """

    stp_mode = None
    portfast_default = 0
    bpdu_guard_default = 0

    match = re.search(
        r"Switch is in (\S+) mode",
        output,
        re.IGNORECASE
    )

    if match:
        stp_mode = match.group(1).lower()

    match = re.search(
        r"Portfast Default is (\S+)",
        output,
        re.IGNORECASE
    )

    if match:

        portfast_default = (
            1
            if match.group(1).lower() == "enabled"
            else 0
        )

    match = re.search(
        r"PortFast BPDU Guard Default is (\S+)",
        output,
        re.IGNORECASE
    )

    if match:

        bpdu_guard_default = (
            1
            if match.group(1).lower() == "enabled"
            else 0
        )

    return (
        stp_mode,
        portfast_default,
        bpdu_guard_default
    )


def parse_mst_configuration(output):
    """
    Parse MST region name, revision and instance mappings from:
        show spanning-tree mst configuration
    """

    region_name = None
    revision = None
    instances = {}

    match = re.search(
        r"Name\s+\[([^\]]+)\]",
        output
    )

    if match:
        region_name = match.group(1)

    match = re.search(
        r"Revision\s+(\d+)",
        output
    )

    if match:
        revision = int(match.group(1))

    for line in output.splitlines():

        line = line.strip()

        match = re.match(
            r"^(\d+)\s+(.+)$",
            line
        )

        if not match:
            continue

        instance = match.group(1)
        mapping = match.group(2).strip()

        if instance in ("0", "1", "2") and mapping:
            instances[instance] = mapping

    return (
        region_name,
        revision,
        instances
    )


def parse_interface_security(output):
    """
    Parse per-interface STP security settings from:
        show running-config | section interface
    """

    interfaces = {}

    current_interface = None

    for line in output.splitlines():

        if line.startswith("interface "):

            raw_interface = line.split()[1]

            if is_physical_interface(raw_interface):

                current_interface = normalize_interface_name(
                    raw_interface
                )

                interfaces[current_interface] = {
                    "portfast": 0,
                    "bpdu_guard": 0,
                    "root_guard": 0,
                    "loop_guard": 0
                }

            else:

                current_interface = None

            continue

        if current_interface is None:
            continue

        stripped = line.strip()

        if stripped == "spanning-tree portfast":

            interfaces[current_interface]["portfast"] = 1

        if stripped == "spanning-tree bpduguard enable":

            interfaces[current_interface]["bpdu_guard"] = 1

        if "spanning-tree guard root" in stripped:

            interfaces[current_interface]["root_guard"] = 1

        if "spanning-tree guard loop" in stripped:

            interfaces[current_interface]["loop_guard"] = 1

    return interfaces


def parse_static_routes(output):
    """
    Parse IPv4 static routes from:
        show running-config | include ^ip route

    VRF-specific static routes are ignored.
    """

    routes = []

    for line in output.splitlines():

        line = line.strip()

        # Ignore VRF-specific routes.
        #
        # Example:
        # ip route vrf Mgmt-vrf ...
        #
        if re.match(
            r"^ip route\s+vrf\s+",
            line,
            re.IGNORECASE
        ):
            continue

        match = re.match(
            r"^ip route\s+"
            r"(\S+)\s+"
            r"(\S+)\s+"
            r"(\S+)",
            line
        )

        if not match:
            continue

        network = match.group(1)
        mask = match.group(2)
        next_hop = match.group(3)

        routes.append({
            "network": network,
            "mask": mask,
            "next_hop": next_hop
        })

    return routes


def parse_ios_version(output):
    """
    Parse IOS XE version from:
        show version
    """

    match = re.search(
        r"Cisco IOS XE Software.*?Version\s+([\d.]+)",
        output,
        re.IGNORECASE | re.DOTALL
    )

    if match:
        return match.group(1)

    match = re.search(
        r"Version\s+([\d.]+)",
        output,
        re.IGNORECASE
    )

    if match:
        return match.group(1)

    return "unknown"


# ============================================================
# Collect Data
# ============================================================

def collect_switch_data():

    device = {
        "device_type": "cisco_ios",
        "host": CISCO_HOST,
        "username": CISCO_USERNAME,
        "password": CISCO_PASSWORD,
        "port": CISCO_PORT,
        "fast_cli": False,
    }

    connection = None

    try:

        logging.info(
            "Connecting to Cisco switch..."
        )

        connection = ConnectHandler(
            **device
        )

        logging.info(
            "Connected successfully"
        )

        # ----------------------------------------------------
        # Cisco commands
        # ----------------------------------------------------

        interfaces_output = connection.send_command(
            "show interfaces status"
        )

        vlan_output = connection.send_command(
            "show vlan"
        )

        svi_output = connection.send_command(
            "show ip interface brief"
        )

        vtp_output = connection.send_command(
            "show vtp status"
        )

        cpu_output = connection.send_command(
            "show processes cpu"
        )

        stp_output = connection.send_command(
            "show spanning-tree summary"
        )

        mst_output = connection.send_command(
            "show spanning-tree mst configuration"
        )

        interface_config_output = connection.send_command(
            "show running-config | section interface"
        )

        routes_output = connection.send_command(
            "show running-config | include ^ip route"
        )

        version_output = connection.send_command(
            "show version"
        )

        # ----------------------------------------------------
        # Parse command output
        # ----------------------------------------------------

        interfaces = parse_interfaces(
            interfaces_output
        )

        port_vlans = parse_port_vlans(
            vlan_output
        )

        vlans = parse_vlans(
            vlan_output
        )

        svis = parse_svis(
            svi_output
        )

        vtp_version, vtp_client_mode = parse_vtp(
            vtp_output
        )

        cpu = parse_cpu(
            cpu_output
        )

        (
            stp_mode,
            portfast_default,
            bpdu_guard_default
        ) = parse_stp(
            stp_output
        )

        (
            mst_region,
            mst_revision,
            mst_instances
        ) = parse_mst_configuration(
            mst_output
        )

        interface_security = parse_interface_security(
            interface_config_output
        )

        static_routes = parse_static_routes(
            routes_output
        )

        ios_version = parse_ios_version(
            version_output
        )

        # ----------------------------------------------------
        # Switch connectivity
        # ----------------------------------------------------

        switch_up.set(1)

        # ----------------------------------------------------
        # Interface status metrics
        # ----------------------------------------------------

        for interface, status in interfaces.items():

            if status == "connected":

                switch_connected_port.labels(
                    interface=interface
                ).set(1)

                switch_unused_port.labels(
                    interface=interface
                ).set(0)

                switch_disabled_port.labels(
                    interface=interface
                ).set(0)

            elif status == "unused":

                switch_connected_port.labels(
                    interface=interface
                ).set(0)

                switch_unused_port.labels(
                    interface=interface
                ).set(1)

                switch_disabled_port.labels(
                    interface=interface
                ).set(0)

            elif status == "disabled":

                switch_connected_port.labels(
                    interface=interface
                ).set(0)

                switch_unused_port.labels(
                    interface=interface
                ).set(0)

                switch_disabled_port.labels(
                    interface=interface
                ).set(1)

        # ----------------------------------------------------
        # Port VLAN metrics
        # ----------------------------------------------------

        for interface, vlan in port_vlans.items():

            switch_port_vlan.labels(
                interface=interface,
                vlan=vlan
            ).set(1)

        # ----------------------------------------------------
        # VLAN metrics
        # ----------------------------------------------------

        switch_vlan_count.set(
            len(vlans)
        )

        for vlan_id, vlan_name in vlans.items():

            switch_vlan_configured.labels(
                vlan=vlan_id,
                name=vlan_name
            ).set(1)

        # ----------------------------------------------------
        # SVI metrics
        # ----------------------------------------------------

        for interface, data in svis.items():

            is_up = (
                data["status"].lower() == "up"
                and data["protocol"].lower() == "up"
            )

            switch_svi_up.labels(
                interface=interface
            ).set(
                1 if is_up else 0
            )

            if data["ip"].lower() != "unassigned":

                switch_svi_ip_configured.labels(
                    interface=interface,
                    ip=data["ip"]
                ).set(1)

        # ----------------------------------------------------
        # Static route metrics
        # ----------------------------------------------------

        switch_static_route_count.set(
            len(static_routes)
        )

        for route in static_routes:

            switch_static_route.labels(
                network=route["network"],
                mask=route["mask"],
                next_hop=route["next_hop"]
            ).set(1)

        # ----------------------------------------------------
        # CPU metrics
        # ----------------------------------------------------

        switch_cpu_usage_percent.set(
            cpu
        )

        # ----------------------------------------------------
        # VTP metrics
        # ----------------------------------------------------

        if vtp_version is not None:

            switch_vtp_version.set(
                vtp_version
            )

            switch_vtp_version_expected.set(
                EXPECTED_VTP_VERSION
            )

            switch_vtp_version_mismatch.set(
                1
                if vtp_version != EXPECTED_VTP_VERSION
                else 0
            )

        switch_vtp_client_mode.set(
            vtp_client_mode
        )

        # ----------------------------------------------------
        # MST metrics
        # ----------------------------------------------------

        mst_enabled = (
            1
            if stp_mode == "mst"
            else 0
        )

        switch_mst_enabled.set(
            mst_enabled
        )

        if mst_revision is not None:

            switch_mst_revision.set(
                mst_revision
            )

        if mst_region:

            switch_mst_region_name.labels(
                region=mst_region
            ).set(1)

        for instance, mapping in mst_instances.items():

            switch_mst_instance_vlan.labels(
                instance=instance,
                mapping=mapping
            ).set(1)

        # ----------------------------------------------------
        # STP metrics
        # ----------------------------------------------------

        if stp_mode:

            switch_stp_mode.labels(
                mode=stp_mode
            ).set(1)

        switch_stp_portfast.set(
            portfast_default
        )

        switch_stp_bpdu_guard.set(
            bpdu_guard_default
        )

        # ----------------------------------------------------
        # Per-interface STP security
        # ----------------------------------------------------

        for interface, settings in interface_security.items():

            switch_interface_portfast.labels(
                interface=interface
            ).set(
                settings["portfast"]
            )

            switch_interface_bpdu_guard.labels(
                interface=interface
            ).set(
                settings["bpdu_guard"]
            )

            switch_interface_root_guard.labels(
                interface=interface
            ).set(
                settings["root_guard"]
            )

            switch_interface_loop_guard.labels(
                interface=interface
            ).set(
                settings["loop_guard"]
            )

        # ----------------------------------------------------
        # IOS XE version
        # ----------------------------------------------------

        if ios_version != "unknown":

            switch_ios_xe_version.labels(
                version=ios_version
            ).set(1)

        # ----------------------------------------------------
        # Summary
        # ----------------------------------------------------

        logging.info(
            "Collected: %d interfaces | %d VLANs | %d SVIs | "
            "%d routes | CPU %.1f%%",
            len(interfaces),
            len(vlans),
            len(svis),
            len(static_routes),
            cpu
        )

        return True

    except Exception as e:

        logging.error(
            "Collection failed: %s",
            e
        )

        switch_up.set(0)

        return False

    finally:

        if connection:

            connection.disconnect()

            logging.info(
                "Disconnected from Cisco switch"
            )


# ============================================================
# Main
# ============================================================

if __name__ == "__main__":

    logging.info(
        "Starting Cisco Network Health Collector"
    )

    logging.info(
        "Prometheus metrics available on port %d",
        PROMETHEUS_PORT
    )

    start_http_server(
        PROMETHEUS_PORT
    )

    while True:

        collect_switch_data()

        time.sleep(
            COLLECT_INTERVAL
        )