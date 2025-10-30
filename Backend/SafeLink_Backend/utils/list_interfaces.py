"""List available network interfaces for packet sniffing."""
from scapy.arch import get_if_list

print("Available network interfaces:")
print("-" * 50)
interfaces = get_if_list()
for idx, iface in enumerate(interfaces, 1):
    print(f"{idx}. {iface}")

print("\nNote: On Windows, you may need to use the full interface name or None to use default.")
