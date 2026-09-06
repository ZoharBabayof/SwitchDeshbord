import re

from utils import is_physical_interface, normalize_interface_name


# ============================================================
# Parsers
# ============================================================

def parse_interfaces(output):
    """
    Parse:

        show interfaces status

    The interface name is always the first field.

    The status is detected explicitly instead of assuming
    that the interface name, description and status occupy
    fixed columns.
    """

    interfaces = {}

    valid_statuses = {
        "connected": "connected",
        "notconnect": "unused",
        "notconnected": "unused",
        "disabled": "disabled",
        "err-disabled": "disabled",
    }

    for line in output.splitlines():
        line = line.strip()

        if not line:
            continue

        parts = line.split()

        if not parts:
            continue

        raw_interface = parts[0]

        if not is_physical_interface(raw_interface):
            continue

        interface = normalize_interface_name(
            raw_interface.rstrip(",")
        )

        status = None

        for token in parts[1:]:
            normalized_token = token.lower().rstrip(",")

            if normalized_token in valid_statuses:
                status = valid_statuses[normalized_token]
                break

        if status is not None:
            interfaces[interface] = status

    return interfaces


def parse_port_vlans(output):
    """
    Parse access VLANs from:

        show vlan
    """

    port_vlans = {}

    for line in output.splitlines():
        line = line.strip()

        if not line:
            continue

        match = re.match(
            r"^(\d+)\s+(.+?)\s+"
            r"(active|act/unsup|suspended|act/lshut|shutdown)\s*(.*)$",
            line,
            re.IGNORECASE
        )

        if not match:
            continue

        vlan = match.group(1)
        ports = match.group(4)

        if int(vlan) >= 1002:
            continue

        for port in ports.split(","):
            port = port.strip().rstrip(",")

            for candidate in port.split():
                candidate = candidate.strip().rstrip(",")

                if is_physical_interface(candidate):
                    normalized = normalize_interface_name(candidate)
                    port_vlans[normalized] = vlan

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
            line,
            re.IGNORECASE
        )

        if not match:
            continue

        vlan_id = int(match.group(1))
        vlan_name = match.group(2).strip()
        status = match.group(3).lower()

        if vlan_id >= 1002:
            continue

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
    Parse VTP version, operating mode and domain from:

        show vtp status
    """

    version = None
    mode = None
    domain = None

    version_match = re.search(
        r"VTP version running\s*:\s*(\d+)",
        output,
        re.IGNORECASE
    )

    if version_match:
        version = int(version_match.group(1))

    mode_match = re.search(
        r"VTP Operating Mode\s*:\s*(Server|Client|Transparent)",
        output,
        re.IGNORECASE
    )

    if mode_match:
        mode = mode_match.group(1).lower()

    domain_match = re.search(
        r"VTP Domain Name\s*:\s*(\S+)",
        output,
        re.IGNORECASE
    )

    if domain_match:
        domain = domain_match.group(1).strip()

    return version, mode, domain


def parse_hostname(output):
    """
    Parse Cisco hostname from:

        show running-config | include ^hostname
    """

    match = re.search(
        r"^hostname\s+(\S+)",
        output,
        re.IGNORECASE | re.MULTILINE
    )

    if match:
        return match.group(1).strip()

    return None


def parse_cpu(output):
    """
    Parse the five-second CPU utilization from:

        show processes cpu
    """

    match = re.search(
        r"CPU utilization for five seconds:\s*(\d+(?:\.\d+)?)%",
        output,
        re.IGNORECASE
    )

    if match:
        return float(match.group(1))

    return 0.0


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
        output,
        re.IGNORECASE
    )

    if match:
        region_name = match.group(1).strip()

    match = re.search(
        r"Revision\s+(\d+)",
        output,
        re.IGNORECASE
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

        if instance.isdigit() and mapping:
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
            parts = line.split()

            if len(parts) < 2:
                current_interface = None
                continue

            raw_interface = parts[1]

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
            line,
            re.IGNORECASE
        )

        if not match:
            continue

        routes.append({
            "network": match.group(1),
            "mask": match.group(2),
            "next_hop": match.group(3)
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