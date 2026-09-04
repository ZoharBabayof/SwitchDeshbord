import os
from dotenv import load_dotenv
from netmiko import ConnectHandler

load_dotenv()

device = {
    "device_type": "cisco_ios",
    "host": os.getenv("CISCO_HOST"),
    "username": os.getenv("CISCO_USERNAME"),
    "password": os.getenv("CISCO_PASSWORD"),
    "port": int(os.getenv("CISCO_PORT", "22")),
}

try:
    print("Connecting to Cisco device...")

    connection = ConnectHandler(**device)

    print("✅ Connected successfully!")
    print(f"Device: {connection.find_prompt()}")

    output = connection.send_command("show version")

    print("\n--- SHOW VERSION ---")
    print(output)

    # connection.disconnect()
    # print("\nDisconnected.")

except Exception as e:
    print(f"❌ Connection failed: {e}")