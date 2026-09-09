import logging  # Provides logging functionality for the application
import time  # Provides time-related functions, used here for sleep intervals

from prometheus_client import start_http_server  # Starts an HTTP server that exposes metrics to Prometheus

from config import (
    COLLECT_INTERVAL,  # Time in seconds between each switch data collection
    PROMETHEUS_PORT,  # Port used to expose the Prometheus metrics endpoint
)

from collector import collect_switch_data  # Imports the function responsible for collecting switch data


# ============================================================
# Main
# ============================================================

if __name__ == "__main__":  # Runs the following code only when main file is executed directly

    logging.basicConfig( #basic config = set the default of the logging system. (setting before we start)
        level=logging.INFO,  #level = the kind of logging level we want, and up. Sets the minimum to INFO
        format="%(asctime)s [%(levelname)s] %(message)s"  # Defines the format of each log message
        # placeholder = %, s = string 
        #all of these are placeholder and they gonna be replaced by what's inside the: (). 
        #asctime - time of the log creation. levelname - level of log. message - the log message. 
        # in the next command we gonna see putting a message in logging message:
    )

    logging.info(
        "Starting Cisco Network Health Collector"  # Logs a message indicating that the collector has started
    )

    logging.info(
        "Prometheus metrics available on port %d",  # Logs the port where Prometheus metrics are exposed
        PROMETHEUS_PORT  # Inserts the configured Prometheus port into the log message
    )

    start_http_server(
        PROMETHEUS_PORT  # Starts the HTTP server on the configured port for Prometheus to scrape
    )

    while True:  # Continuously runs the data collection process

        collect_switch_data()  # Collects the current switch data and updates the Prometheus metrics

        time.sleep(
            COLLECT_INTERVAL  # Waits for the configured interval before collecting data again
        )