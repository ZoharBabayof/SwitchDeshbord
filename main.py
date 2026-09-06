import logging
import time

from prometheus_client import start_http_server

from config import (
    COLLECT_INTERVAL,
    PROMETHEUS_PORT,
)

from collector import collect_switch_data


# ============================================================
# Main
# ============================================================

if __name__ == "__main__":

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s"
    )

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