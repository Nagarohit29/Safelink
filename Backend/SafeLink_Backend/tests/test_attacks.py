"""
Test script to generate various attack patterns for SafeLink detection.
This will send different types of malicious traffic to test the threat detection system.
"""

import subprocess
import time
import sys
from scapy.all import *

def print_section(title):
    """Print a formatted section header."""
    print(f"\n{'='*60}")
    print(f"  {title}")
    print(f"{'='*60}\n")

def test_syn_flood():
    """Generate SYN flood attack packets."""
    print_section("TEST 1: SYN Flood Attack")
    print("Sending SYN flood packets to localhost...")
    
    target_ip = "127.0.0.1"
    target_port = 80
    
    for i in range(50):
        # Create SYN packet with random source port
        ip = IP(dst=target_ip)
        tcp = TCP(sport=RandShort(), dport=target_port, flags="S")
        pkt = ip/tcp
        send(pkt, verbose=0)
        if i % 10 == 0:
            print(f"  Sent {i+1}/50 SYN packets...")
    
    print("✓ SYN flood test complete!\n")
    time.sleep(2)

def test_port_scan():
    """Generate port scanning traffic."""
    print_section("TEST 2: Port Scanning Attack")
    print("Scanning ports 1-100 on localhost...")
    
    target_ip = "127.0.0.1"
    
    for port in range(1, 101):
        # Send SYN packets to sequential ports (typical port scan behavior)
        ip = IP(dst=target_ip)
        tcp = TCP(sport=RandShort(), dport=port, flags="S")
        pkt = ip/tcp
        send(pkt, verbose=0)
        if port % 20 == 0:
            print(f"  Scanned {port}/100 ports...")
    
    print("✓ Port scan test complete!\n")
    time.sleep(2)

def test_xmas_scan():
    """Generate XMAS scan packets."""
    print_section("TEST 3: XMAS Scan Attack")
    print("Sending XMAS scan packets (FIN+PSH+URG flags)...")
    
    target_ip = "127.0.0.1"
    
    for port in [80, 443, 8000, 8080, 3306, 5432, 27017]:
        # XMAS scan sets FIN, PSH, and URG flags
        ip = IP(dst=target_ip)
        tcp = TCP(sport=RandShort(), dport=port, flags="FPU")
        pkt = ip/tcp
        send(pkt, verbose=0)
        print(f"  XMAS scan to port {port}...")
    
    print("✓ XMAS scan test complete!\n")
    time.sleep(2)

def test_null_scan():
    """Generate NULL scan packets."""
    print_section("TEST 4: NULL Scan Attack")
    print("Sending NULL scan packets (no flags set)...")
    
    target_ip = "127.0.0.1"
    
    for port in [21, 22, 23, 25, 53, 80, 110, 143, 443, 3389]:
        # NULL scan has no flags set
        ip = IP(dst=target_ip)
        tcp = TCP(sport=RandShort(), dport=port, flags="")
        pkt = ip/tcp
        send(pkt, verbose=0)
        print(f"  NULL scan to port {port}...")
    
    print("✓ NULL scan test complete!\n")
    time.sleep(2)

def test_fin_scan():
    """Generate FIN scan packets."""
    print_section("TEST 5: FIN Scan Attack")
    print("Sending FIN scan packets...")
    
    target_ip = "127.0.0.1"
    
    for port in range(8000, 8010):
        # FIN scan only has FIN flag set
        ip = IP(dst=target_ip)
        tcp = TCP(sport=RandShort(), dport=port, flags="F")
        pkt = ip/tcp
        send(pkt, verbose=0)
        print(f"  FIN scan to port {port}...")
    
    print("✓ FIN scan test complete!\n")
    time.sleep(2)

def test_ack_scan():
    """Generate ACK scan packets."""
    print_section("TEST 6: ACK Scan Attack")
    print("Sending ACK scan packets (firewall detection)...")
    
    target_ip = "127.0.0.1"
    
    for port in [135, 137, 139, 445, 1433, 3306]:
        # ACK scan only has ACK flag set
        ip = IP(dst=target_ip)
        tcp = TCP(sport=RandShort(), dport=port, flags="A")
        pkt = ip/tcp
        send(pkt, verbose=0)
        print(f"  ACK scan to port {port}...")
    
    print("✓ ACK scan test complete!\n")
    time.sleep(2)

def test_udp_flood():
    """Generate UDP flood packets."""
    print_section("TEST 7: UDP Flood Attack")
    print("Sending UDP flood packets...")
    
    target_ip = "127.0.0.1"
    
    for i in range(30):
        # Send UDP packets to random ports
        ip = IP(dst=target_ip)
        udp = UDP(sport=RandShort(), dport=RandShort())
        payload = Raw(load="X" * 1024)  # 1KB payload
        pkt = ip/udp/payload
        send(pkt, verbose=0)
        if i % 10 == 0:
            print(f"  Sent {i+1}/30 UDP packets...")
    
    print("✓ UDP flood test complete!\n")
    time.sleep(2)

def run_nmap_tests():
    """Run Nmap scans for realistic attack simulation."""
    print_section("TEST 8: Nmap Scan Suite")
    
    scans = [
        ("SYN Scan", ["nmap", "-sS", "127.0.0.1", "-p", "1-1000"]),
        ("XMAS Scan", ["nmap", "-sX", "127.0.0.1", "-p", "1-100"]),
        ("NULL Scan", ["nmap", "-sN", "127.0.0.1", "-p", "1-100"]),
        ("FIN Scan", ["nmap", "-sF", "127.0.0.1", "-p", "80,443,8000"]),
    ]
    
    for scan_name, cmd in scans:
        print(f"Running {scan_name}...")
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            print(f"✓ {scan_name} complete!")
        except subprocess.TimeoutExpired:
            print(f"⚠ {scan_name} timed out (this is okay)")
        except FileNotFoundError:
            print(f"⚠ Nmap not found, skipping {scan_name}")
            break
        except Exception as e:
            print(f"⚠ {scan_name} failed: {e}")
        time.sleep(2)

def main():
    """Run all attack tests."""
    print("\n" + "="*60)
    print("  SafeLink Attack Detection Test Suite")
    print("  This will generate various attack patterns for testing")
    print("="*60)
    
    # Check if sniffer is running
    print("\n⚠ IMPORTANT: Make sure the packet sniffer is running!")
    print("  1. Go to http://localhost:5173/sniffer")
    print("  2. Click 'Start Sniffer'")
    print("  3. Come back here and press ENTER to continue...")
    input()
    
    try:
        # Run Scapy-based tests
        test_syn_flood()
        test_port_scan()
        test_xmas_scan()
        test_null_scan()
        test_fin_scan()
        test_ack_scan()
        test_udp_flood()
        
        # Run Nmap tests
        run_nmap_tests()
        
        print_section("All Tests Complete!")
        print("✓ Attack simulation finished!")
        print("\nCheck the following:")
        print("  • Dashboard: http://localhost:5173/")
        print("  • Alerts: http://localhost:5173/alerts")
        print("  • Attackers: http://localhost:5173/attackers")
        print("  • Database: Check alerts_log.csv in Backend/SafeLink_Backend/logs/")
        print("\nThe ANN classifier should have detected multiple attack patterns!")
        
    except KeyboardInterrupt:
        print("\n\n⚠ Test interrupted by user")
    except Exception as e:
        print(f"\n\n❌ Error during testing: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    # Check if running with admin privileges (required for raw sockets)
    if sys.platform == "win32":
        try:
            import ctypes
            if not ctypes.windll.shell32.IsUserAnAdmin():
                print("⚠ WARNING: This script requires Administrator privileges!")
                print("Please run PowerShell or CMD as Administrator, then run:")
                print("  cd E:\\coreproject\\Backend\\SafeLink_Backend")
                print("  ..\\..\\venv\\Scripts\\activate")
                print("  python test_attacks.py")
                sys.exit(1)
        except:
            pass
    
    main()
