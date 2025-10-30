"""
Quick Attack Test - Simple traffic generation for SafeLink testing
Run this after starting the packet sniffer in the web interface.
"""

import subprocess
import time

def print_header(msg):
    print(f"\n{'='*60}")
    print(f"  {msg}")
    print(f"{'='*60}\n")

def quick_test():
    """Run quick attack tests using Nmap."""
    print_header("SafeLink Quick Attack Test")
    
    print("This will run 3 Nmap scans to generate attack traffic:")
    print("  1. SYN Scan (ports 1-1000)")
    print("  2. XMAS Scan (ports 1-100)")
    print("  3. NULL Scan (ports 1-100)")
    print("\nMake sure the sniffer is running at http://localhost:5173/sniffer")
    print("\nPress ENTER to start...")
    input()
    
    tests = [
        ("SYN Scan", ["nmap", "-sS", "127.0.0.1", "-p", "1-1000"]),
        ("XMAS Scan", ["nmap", "-sX", "127.0.0.1", "-p", "1-100"]),
        ("NULL Scan", ["nmap", "-sN", "127.0.0.1", "-p", "1-100"]),
    ]
    
    for i, (name, cmd) in enumerate(tests, 1):
        print(f"\n[{i}/3] Running {name}...")
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
            print(f"✓ {name} complete!")
            if result.stdout:
                lines = result.stdout.split('\n')[:10]  # Show first 10 lines
                print('\n'.join(lines))
        except subprocess.TimeoutExpired:
            print(f"⚠ {name} timed out")
        except FileNotFoundError:
            print("❌ Nmap not found! Please install Nmap from https://nmap.org/download.html")
            return
        except Exception as e:
            print(f"❌ Error: {e}")
        
        time.sleep(2)
    
    print_header("Tests Complete!")
    print("✓ All attack simulations finished!")
    print("\nCheck your dashboard for detected threats:")
    print("  • Dashboard: http://localhost:5173/")
    print("  • Alerts: http://localhost:5173/alerts")
    print("  • Attackers: http://localhost:5173/attackers")
    print("\nThe ANN should have classified these as attacks!")

if __name__ == "__main__":
    quick_test()
