"""Start the packet sniffer via API call."""
import requests

API_BASE = "http://localhost:8000"

# First, check if user is authenticated
# You may need to get the token from the frontend or login first

try:
    # Get current status
    print("Checking sniffer status...")
    response = requests.get(f"{API_BASE}/sniffer/status")
    print(f"Current status: {response.json()}")
    
    # Start the sniffer with default interface
    print("\nStarting packet sniffer...")
    response = requests.post(
        f"{API_BASE}/sniffer/start",
        json={"interface": None}
    )
    
    if response.status_code == 200:
        print("✅ Sniffer started successfully!")
        print(f"Status: {response.json()}")
    else:
        print(f"❌ Failed to start sniffer: {response.status_code}")
        print(f"Error: {response.text}")
        
except Exception as e:
    print(f"Error: {e}")
