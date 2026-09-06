import logging

from netmiko import ConnectHandler

from config import (
    CISCO_HOST,
    CISCO_USERNAME,
    CISCO_PASSWORD,
    CISCO_PORT,
    EXPECTED_VTP_VERSION,
)

from metrics import (
    switch_up,
    switch_connected_port,
    switch_unused_port,
    switch_disabled_port,
    switch_port_vlan,
    switch_vlan_configured,
    switch_vlan_count,
    switch_svi_up,
    switch_svi_ip_configured,
    switch_static_route,
    switch_static_route_count,
    switch_cpu_usage_percent,
    switch_vtp_version,
    switch_vtp_version_expected,
    switch_vtp_version_mismatch,
    switch_vtp_mode,
    switch_hostname,
    switch_vtp_domain,
    switch_mst_enabled,
    switch_mst_revision,
    switch_mst_region_name,
    switch_mst_instance_vlan,
    switch_stp_mode,
    switch_stp_portfast,
    switch_stp_bpdu_guard,
    switch_interface_portfast,
    switch_interface_bpdu_guard,
    switch_interface_root_guard,
    switch_interface_loop_guard,
    switch_ios_xe_version,
    clear_dynamic_metrics,
)

from parsers import (
    parse_interfaces,
    parse_port_vlans,
    parse_vlans,
    parse_svis,
    parse_vtp,
    parse_hostname,
    parse_cpu,
    parse_stp,
    parse_mst_configuration,
    parse_interface_security,
    parse_static_routes,
    parse_ios_version,
)


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
        logging.info("Connecting to Cisco switch...")

        connection = ConnectHandler(**device)

        logging.info("Connected successfully")

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

        hostname_output = connection.send_command(
            "show running-config | include ^hostname"
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

        vtp_version, vtp_mode, vtp_domain = parse_vtp(
            vtp_output
        )

        hostname = parse_hostname(
            hostname_output
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
        # New successful snapshot
        # ----------------------------------------------------

        clear_dynamic_metrics()

        switch_up.set(1)

        # ----------------------------------------------------
        # Hostname
        # ----------------------------------------------------

        if hostname:
            switch_hostname.labels(
                hostname=hostname
            ).set(1)

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

        switch_vtp_version_expected.set(
            EXPECTED_VTP_VERSION
        )

        if vtp_version is not None:

            switch_vtp_version.set(
                vtp_version
            )

            switch_vtp_version_mismatch.set(
                1
                if vtp_version != EXPECTED_VTP_VERSION
                else 0
            )

        else:

            switch_vtp_version.set(0)

            switch_vtp_version_mismatch.set(1)

        # ----------------------------------------------------
        # VTP operating mode
        # ----------------------------------------------------

        if vtp_mode:

            switch_vtp_mode.labels(
                mode=vtp_mode
            ).set(1)

        # ----------------------------------------------------
        # VTP domain
        # ----------------------------------------------------

        if vtp_domain:

            switch_vtp_domain.labels(
                domain=vtp_domain
            ).set(1)

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

        else:

            switch_mst_revision.set(0)

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

        connected_count = sum(
            1
            for status in interfaces.values()
            if status == "connected"
        )

        unused_count = sum(
            1
            for status in interfaces.values()
            if status == "unused"
        )

        disabled_count = sum(
            1
            for status in interfaces.values()
            if status == "disabled"
        )

        logging.info(
            "Collected: %d interfaces "
            "(%d connected, %d unused, %d disabled) | "
            "%d VLANs | %d SVIs | %d routes | CPU %.1f%%",
            len(interfaces),
            connected_count,
            unused_count,
            disabled_count,
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