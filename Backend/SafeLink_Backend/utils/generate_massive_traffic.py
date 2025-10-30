"""
Generate massive network traffic to demonstrate SafeLink detection capabilities.
This will create various types of traffic patterns to trigger both DFA and ANN detection.
"""
from scapy.all import IP, TCP, UDP, ICMP, ARP, Ether, send, sr1
import time
import random
from datetime import datetime

print("=" * 70)
print("  SAFELINK NETWORK TRAFFIC GENERATOR - DEMONSTRATION MODE")
print("=" * 70)
print("\nThis script will generate significant network traffic to demonstrate:")
print("  ✓ ARP Spoofing Detection (DFA Filter)")
print("  ✓ Port Scanning Detection (ANN Classifier)")
print("  ✓ Suspicious Packet Detection (ANN Classifier)")
print("  ✓ Real-time Alert Generation")
print("  ✓ WebSocket Broadcasting")
print("=" * 70)

# Configuration
TARGET_IP = "127.0.0.1"  # Localhost for safety
ATTACKER_IPS = [
    "10.0.0.50",
    "172.16.0.99",
    "192.168.100.200",
    "10.10.10.66",
    "192.168.1.250"
]

def print_progress(stage, total, current):
    """Print progress bar"""
    percent = (current / total) * 100
    bar_length = 40
    filled = int(bar_length * current / total)
    bar = '█' * filled + '░' * (bar_length - filled)
    print(f"\r{stage}: [{bar}] {percent:.1f}% ({current}/{total})", end='', flush=True)

def attack_1_arp_spoofing():
    """Generate ARP spoofing attack - DFA should detect this"""
    print("\n\n[ATTACK 1] ARP Spoofing Campaign")
    print("-" * 70)
    print("Simulating ARP cache poisoning attack...")
    print("Expected Detection: DFA Filter (Excessive gratuitous ARPs)")
    
    total_packets = 50
    attacker_mac = "aa:bb:cc:dd:ee:ff"
    
    for i in range(total_packets):
        print_progress("Sending ARP packets", total_packets, i+1)
        
        # Gratuitous ARP (claiming to be gateway)
        arp_pkt = ARP(
            op=2,  # ARP reply
            psrc="192.168.1.1",  # Gateway IP
            pdst="192.168.1.100",  # Victim IP
            hwsrc=attacker_mac,
            hwdst="ff:ff:ff:ff:ff:ff"
        )
        
        # Send without actually transmitting (for demo)
        # To actually send: send(arp_pkt, verbose=0)
        time.sleep(0.05)
    
    print("\n✅ ARP spoofing simulation complete")
    print(f"   Generated: {total_packets} gratuitous ARP packets")

def attack_2_port_scan():
    """Generate port scanning pattern - ANN should detect this"""
    print("\n\n[ATTACK 2] Comprehensive Port Scan")
    print("-" * 70)
    print("Simulating aggressive port scanning...")
    print("Expected Detection: ANN Classifier (Port scan pattern)")
    
    # Scan multiple port ranges
    port_ranges = [
        (20, 25),      # FTP, SSH, Telnet
        (79, 81),      # HTTP
        (135, 140),    # Windows services
        (442, 445),    # HTTPS, SMB
        (3305, 3310),  # MySQL range
        (5430, 5435),  # PostgreSQL range
        (8000, 8010),  # Alt HTTP
        (31335, 31340) # Trojan ports
    ]
    
    total_ports = sum(end - start + 1 for start, end in port_ranges)
    current = 0
    
    for src_ip in random.sample(ATTACKER_IPS, 3):
        for start, end in port_ranges:
            for port in range(start, end + 1):
                current += 1
                print_progress("Scanning ports", total_ports, current)
                
                # SYN scan packet
                syn_pkt = IP(src=src_ip, dst=TARGET_IP)/TCP(dport=port, flags="S")
                # To actually send: send(syn_pkt, verbose=0)
                time.sleep(0.02)
    
    print(f"\n✅ Port scan simulation complete")
    print(f"   Scanned: {total_ports} ports from {len(ATTACKER_IPS)} IPs")

def attack_3_stealth_scans():
    """Generate stealth scanning techniques - ANN should detect unusual flags"""
    print("\n\n[ATTACK 3] Stealth Scan Techniques")
    print("-" * 70)
    print("Simulating advanced scanning with unusual TCP flags...")
    print("Expected Detection: ANN Classifier (Anomalous packet patterns)")
    
    scan_types = [
        ("XMAS Scan", "FPU"),      # FIN + PSH + URG
        ("NULL Scan", ""),          # No flags
        ("FIN Scan", "F"),          # FIN only
        ("ACK Scan", "A"),          # ACK only
        ("Window Scan", "A"),       # ACK with window manipulation
        ("Maimon Scan", "FA"),      # FIN + ACK
        ("All Flags", "FSRPAUEC"),  # All flags set
    ]
    
    total = len(scan_types) * 20
    current = 0
    
    for scan_name, flags in scan_types:
        for i in range(20):
            current += 1
            print_progress(f"Stealth scans ({scan_name})", total, current)
            
            src_ip = random.choice(ATTACKER_IPS)
            port = random.choice([80, 443, 22, 3389, 8080, 31337])
            
            pkt = IP(src=src_ip, dst=TARGET_IP)/TCP(dport=port, flags=flags)
            # To actually send: send(pkt, verbose=0)
            time.sleep(0.03)
    
    print(f"\n✅ Stealth scan simulation complete")
    print(f"   Executed: {len(scan_types)} different scan techniques")

def attack_4_fragmentation():
    """Generate fragmented packets - suspicious behavior"""
    print("\n\n[ATTACK 4] IP Fragmentation Attack")
    print("-" * 70)
    print("Simulating fragmented packet stream...")
    print("Expected Detection: ANN Classifier (Fragmentation anomaly)")
    
    total = 30
    for i in range(total):
        print_progress("Sending fragmented packets", total, i+1)
        
        src_ip = random.choice(ATTACKER_IPS)
        
        # Fragmented packet
        frag_pkt = IP(src=src_ip, dst=TARGET_IP, flags="MF", frag=i*8)/TCP(dport=80)
        # To actually send: send(frag_pkt, verbose=0)
        time.sleep(0.05)
    
    print(f"\n✅ Fragmentation attack simulation complete")
    print(f"   Generated: {total} fragmented packets")

def attack_5_high_rate_traffic():
    """Generate high-volume traffic flood"""
    print("\n\n[ATTACK 5] High-Volume Traffic Flood")
    print("-" * 70)
    print("Simulating traffic flood attack...")
    print("Expected Detection: Volume-based anomaly detection")
    
    protocols = ["TCP", "UDP", "ICMP"]
    total = 100
    
    for i in range(total):
        print_progress("Flooding traffic", total, i+1)
        
        src_ip = random.choice(ATTACKER_IPS)
        proto = random.choice(protocols)
        
        if proto == "TCP":
            pkt = IP(src=src_ip, dst=TARGET_IP)/TCP(dport=random.randint(1, 65535))
        elif proto == "UDP":
            pkt = IP(src=src_ip, dst=TARGET_IP)/UDP(dport=random.randint(1, 65535))
        else:
            pkt = IP(src=src_ip, dst=TARGET_IP)/ICMP()
        
        # To actually send: send(pkt, verbose=0)
        time.sleep(0.01)
    
    print(f"\n✅ Traffic flood simulation complete")
    print(f"   Generated: {total} packets across multiple protocols")

def attack_6_suspicious_ports():
    """Target known malicious ports"""
    print("\n\n[ATTACK 6] Suspicious Port Targeting")
    print("-" * 70)
    print("Targeting known trojan and backdoor ports...")
    print("Expected Detection: ANN Classifier (Suspicious destination ports)")
    
    # Known malicious ports
    malicious_ports = [
        (31337, "Back Orifice"),
        (12345, "NetBus"),
        (6666, "Various trojans"),
        (6667, "IRC botnet"),
        (1080, "SOCKS proxy"),
        (4444, "Metasploit"),
        (5555, "Android Debug"),
        (8888, "Alt HTTP proxy"),
        (9999, "Various backdoors"),
        (27374, "SubSeven")
    ]
    
    total = len(malicious_ports) * 5
    current = 0
    
    for port, name in malicious_ports:
        for i in range(5):
            current += 1
            print_progress("Targeting malicious ports", total, current)
            
            src_ip = random.choice(ATTACKER_IPS)
            pkt = IP(src=src_ip, dst=TARGET_IP)/TCP(dport=port, flags="S")
            # To actually send: send(pkt, verbose=0)
            time.sleep(0.03)
    
    print(f"\n✅ Suspicious port targeting complete")
    print(f"   Targeted: {len(malicious_ports)} known malicious ports")

def generate_normal_traffic():
    """Generate some normal traffic for comparison"""
    print("\n\n[BASELINE] Normal Traffic Pattern")
    print("-" * 70)
    print("Generating legitimate-looking traffic for comparison...")
    
    normal_ports = [80, 443, 22, 53, 3306, 5432]
    total = 20
    
    for i in range(total):
        print_progress("Normal traffic", total, i+1)
        
        port = random.choice(normal_ports)
        pkt = IP(src="192.168.1.10", dst=TARGET_IP)/TCP(dport=port, flags="S")
        # To actually send: send(pkt, verbose=0)
        time.sleep(0.1)
    
    print(f"\n✅ Normal traffic baseline complete")

# Main execution
if __name__ == "__main__":
    try:
        start_time = datetime.now()
        
        print("\n⚠️  SAFETY MODE: Packets are SIMULATED, not actually sent")
        print("    To send real packets, uncomment send() calls in the code\n")
        
        input("Press ENTER to start traffic generation...")
        
        # Execute all attack scenarios
        generate_normal_traffic()
        attack_1_arp_spoofing()
        attack_2_port_scan()
        attack_3_stealth_scans()
        attack_4_fragmentation()
        attack_5_high_rate_traffic()
        attack_6_suspicious_ports()
        
        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()
        
        print("\n\n" + "=" * 70)
        print("  TRAFFIC GENERATION COMPLETE!")
        print("=" * 70)
        print(f"\n📊 Summary:")
        print(f"   Duration: {duration:.1f} seconds")
        print(f"   Total Scenarios: 7 (1 normal + 6 attacks)")
        print(f"   Estimated Packets: ~350")
        
        print(f"\n🎯 Expected SafeLink Detection:")
        print(f"   ✓ DFA Filter: ARP spoofing attacks")
        print(f"   ✓ ANN Classifier: Port scans, stealth scans, fragmentation")
        print(f"   ✓ Real-time Alerts: All suspicious activities")
        print(f"   ✓ WebSocket Updates: Live dashboard updates")
        
        print(f"\n📈 Check Results:")
        print(f"   → Browser: http://localhost:5173/alerts")
        print(f"   → API: http://localhost:8000/alerts/recent")
        print(f"   → Terminal: python check_alerts.py")
        
        print("\n" + "=" * 70)
        
    except KeyboardInterrupt:
        print("\n\n⚠️  Traffic generation interrupted by user")
    except Exception as e:
        print(f"\n\n❌ Error: {e}")
