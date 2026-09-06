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

    replacements = {
        "GigabitEthernet": "Gi",
        "TenGigabitEthernet": "Te",
        "TwentyFiveGigE": "Twe",
        "FastEthernet": "Fa",
    }

    for long_name, short_name in replacements.items():
        if interface.startswith(long_name):
            return interface.replace(long_name, short_name, 1)

    return interface


def is_physical_interface(interface):
    """
    Determine whether an interface is a physical Ethernet interface.
    """

    prefixes = (
        "GigabitEthernet",
        "Gi",
        "TenGigabitEthernet",
        "Te",
        "TwentyFiveGigE",
        "Twe",
        "FastEthernet",
        "Fa",
    )

    return interface.startswith(prefixes)