"""Generate simulated attack traffic to test SafeLink detection."""
from scapy.all import ARP, IP, TCP, get_if_list
import time
import random

print("=" * 60)
print("SAFELINK ATTACK TRAFFIC GENERATOR")
print("=" * 60)
print("\nThis will generate various types of attack traffic")
print("SafeLink should detect and alert on these packets\n")

# Get available interfaces
print("Available network interfaces:")
ifaces = get_if_list()
for i, iface in enumerate(ifaces[:5], 1):
    print(f"{i}. {iface}")

print("\nGenerating attack traffic...\n")

def generate_arp_spoof_attack():
    """Simulate ARP spoofing attack - DFA should catch this"""
    print("1.  Generating ARP Spoofing Attack...")
    print("   (This should trigger DFA filter)")
    
    # Send multiple gratuitous ARP packets (classic ARP spoofing)
    target_mac = "aa:bb:cc:dd:ee:ff"
    for i in range(10):
        arp_pkt = ARP(
            op=2,  # ARP reply
            psrc="192.168.1.1",  # Claiming to be gateway
            pdst="192.168.1.100",  # Target victim
            hwsrc=target_mac,  # Attacker MAC
            hwdst="ff:ff:ff:ff:ff:ff"
        )
        # Don't actually send - just log
        print(f"   Generated ARP packet {i+1}/10: {target_mac} claiming to be 192.168.1.1")
        time.sleep(0.1)
    
    print("    ARP spoofing simulation complete\n")

def generate_port_scan():
    """Simulate port scanning - ANN should detect pattern"""
    print("2.  Generating Port Scan Attack...")
    print("   (This should trigger ANN classifier)")
    
    # Simulate SYN scan pattern
    src_ip = "10.0.0.50"
    dst_ip = "192.168.1.10"
    
    for port in [22, 80, 443, 3306, 5432, 8080, 8443, 31337]:
        syn_pkt = IP(src=src_ip, dst=dst_ip)/TCP(dport=port, flags="S")
        print(f"   Generated SYN scan to port {port}")
        time.sleep(0.1)
    
    print("    Port scan simulation complete\n")

def generate_suspicious_traffic():
    """Generate packets with unusual flags/patterns"""
    print("3.  Generating Suspicious TCP Traffic...")
    print("   (Unusual flags should trigger ANN)")
    
    patterns = [
        ("FIN+URG+PSH", "FPU"),
        ("All Flags", "FSRPAUEC"),
        ("Null Scan", ""),
        ("Xmas Scan", "FPU"),
    ]
    
    for name, flags in patterns:
        pkt = IP(src="172.16.0.99", dst="192.168.1.5")/TCP(dport=31337, flags=flags)
        print(f"   Generated {name} packet: flags={flags}")
        time.sleep(0.1)
    
    print("    Suspicious traffic simulation complete\n")

# Run the simulations
try:
    generate_arp_spoof_attack()
    generate_port_scan()
    generate_suspicious_traffic()
    
    print("=" * 60)
    print(" ATTACK SIMULATION COMPLETE!")
    print("=" * 60)
    print("\n  NOTE: Packets were generated but NOT sent to avoid")
    print("   affecting your real network.")
    print("\n To see real detections:")
    print("   1. Check the Alerts page in your browser")
    print("   2. The sniffer is monitoring real network traffic")
    print("   3. Any actual attacks on your network will be detected")
    print("\n Alternative: Use 'nmap' or other tools to generate")
    print("   real traffic that SafeLink will detect:")
    print("   - nmap -sS <target_ip>  (SYN scan)")
    print("   - nmap -sN <target_ip>  (Null scan)")
    print("   - nmap -sX <target_ip>  (Xmas scan)")
    print("=" * 60)
    
except Exception as e:
    print(f" Error: {e}")
