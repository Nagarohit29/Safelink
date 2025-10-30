"""
REAL TRAFFIC GENERATOR - Actually sends packets to trigger SafeLink detection.
⚠️ WARNING: This sends REAL packets on your network!
"""
from scapy.all import IP, TCP, UDP, ICMP, send, conf
import time
import random

print("=" * 70)
print("  SAFELINK - REAL PACKET SENDER")
print("=" * 70)
print("\n⚠️  WARNING: This will send REAL packets to localhost!")
print("   Only for demonstration purposes on your own machine\n")

# Safety: Only target localhost
TARGET = "127.0.0.1"
PACKET_DELAY = 0.05  # seconds between packets

# Disable Scapy warnings
conf.verb = 0

def send_attack_wave_1():
    """Port scan - 100 packets"""
    print("\n[1/4] Sending Port Scan (100 packets)...")
    ports = range(1, 101)
    for i, port in enumerate(ports, 1):
        pkt = IP(dst=TARGET)/TCP(dport=port, flags="S")
        send(pkt, verbose=0)
        if i % 10 == 0:
            print(f"   Sent {i}/100 packets...")
        time.sleep(PACKET_DELAY)
    print("   ✅ Port scan complete")

def send_attack_wave_2():
    """Xmas scan - 50 packets"""
    print("\n[2/4] Sending XMAS Scan (50 packets)...")
    for i in range(50):
        port = random.randint(1, 10000)
        pkt = IP(dst=TARGET)/TCP(dport=port, flags="FPU")  # FIN+PSH+URG
        send(pkt, verbose=0)
        if (i+1) % 10 == 0:
            print(f"   Sent {i+1}/50 packets...")
        time.sleep(PACKET_DELAY)
    print("   ✅ XMAS scan complete")

def send_attack_wave_3():
    """NULL scan - 50 packets"""
    print("\n[3/4] Sending NULL Scan (50 packets)...")
    for i in range(50):
        port = random.randint(1, 10000)
        pkt = IP(dst=TARGET)/TCP(dport=port, flags="")  # No flags
        send(pkt, verbose=0)
        if (i+1) % 10 == 0:
            print(f"   Sent {i+1}/50 packets...")
        time.sleep(PACKET_DELAY)
    print("   ✅ NULL scan complete")

def send_attack_wave_4():
    """Suspicious high ports - 50 packets"""
    print("\n[4/4] Sending Suspicious Traffic (50 packets)...")
    malicious_ports = [31337, 12345, 6666, 4444, 5555, 8888, 9999, 27374]
    for i in range(50):
        port = random.choice(malicious_ports)
        flags = random.choice(["S", "F", "FPU", ""])
        pkt = IP(dst=TARGET)/TCP(dport=port, flags=flags)
        send(pkt, verbose=0)
        if (i+1) % 10 == 0:
            print(f"   Sent {i+1}/50 packets...")
        time.sleep(PACKET_DELAY)
    print("   ✅ Suspicious traffic complete")

if __name__ == "__main__":
    print("\nThis will send 250 attack packets to localhost")
    print("SafeLink sniffer should detect these as anomalous traffic\n")
    
    response = input("Type 'YES' to proceed: ")
    
    if response.upper() == "YES":
        print("\n" + "=" * 70)
        print("Starting packet transmission...")
        print("=" * 70)
        
        start = time.time()
        
        send_attack_wave_1()  # 100 packets
        send_attack_wave_2()  # 50 packets
        send_attack_wave_3()  # 50 packets
        send_attack_wave_4()  # 50 packets
        
        elapsed = time.time() - start
        
        print("\n" + "=" * 70)
        print("  TRANSMISSION COMPLETE!")
        print("=" * 70)
        print(f"\n📊 Statistics:")
        print(f"   Total Packets: 250")
        print(f"   Duration: {elapsed:.1f} seconds")
        print(f"   Rate: {250/elapsed:.1f} packets/second")
        
        print(f"\n🎯 Check SafeLink Now:")
        print(f"   → Alerts Page: http://localhost:5173/alerts")
        print(f"   → Should see ANN detections for suspicious patterns")
        print(f"   → Real-time WebSocket updates")
        
        print("\n" + "=" * 70)
    else:
        print("\n❌ Cancelled. No packets sent.")
