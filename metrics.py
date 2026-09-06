from prometheus_client import Gauge


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

switch_vtp_mode = Gauge(
    "switch_vtp_mode",
    "VTP operating mode",
    ["mode"]
)

switch_hostname = Gauge(
    "switch_hostname",
    "Cisco switch hostname",
    ["hostname"]
)

switch_vtp_domain = Gauge(
    "switch_vtp_domain",
    "Cisco VTP domain name",
    ["domain"]
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
# Metric Cleanup
# ============================================================

def clear_dynamic_metrics():
    """
    Clear labelled metrics before publishing a new successful
    snapshot.
    """

    switch_connected_port.clear()
    switch_unused_port.clear()
    switch_disabled_port.clear()
    switch_port_vlan.clear()
    switch_vlan_configured.clear()
    switch_svi_up.clear()
    switch_svi_ip_configured.clear()
    switch_static_route.clear()
    switch_mst_region_name.clear()
    switch_mst_instance_vlan.clear()
    switch_vtp_mode.clear()
    switch_hostname.clear()
    switch_vtp_domain.clear()
    switch_stp_mode.clear()
    switch_interface_portfast.clear()
    switch_interface_bpdu_guard.clear()
    switch_interface_root_guard.clear()
    switch_interface_loop_guard.clear()
    switch_ios_xe_version.clear()