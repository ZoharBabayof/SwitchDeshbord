import os

from dotenv import load_dotenv


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