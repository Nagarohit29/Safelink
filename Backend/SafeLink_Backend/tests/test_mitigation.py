"""
Test script for SafeLink Mitigation System
This script demonstrates how to test and verify mitigation functionality.
"""

import requests
import json
import time
from datetime import datetime

# Configuration
API_BASE = "http://127.0.0.1:8000"
USERNAME = "admin"  # Change to your username
PASSWORD = "admin"  # Change to your password

def login():
    """Login and get access token."""
    print("🔐 Logging in...")
    response = requests.post(f"{API_BASE}/auth/login", json={
        "username": USERNAME,
        "password": PASSWORD
    })
    
    if response.status_code == 200:
        token = response.json()["access_token"]
        print("✅ Login successful!")
        return token
    else:
        print(f"❌ Login failed: {response.text}")
        return None

def get_headers(token):
    """Get headers with authorization token."""
    return {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }

def test_create_mitigation_request(token):
    """Test creating a mitigation request."""
    print("\n📝 Creating mitigation request...")
    
    request_data = {
        "action_type": "block_ip",
        "target_ip": "192.168.1.100",
        "target_mac": "aa:bb:cc:dd:ee:99",
        "device_id": "switch-01",
        "reason": "Test: Detected ARP spoofing attack",
        "auto_approve": False  # Set True for automatic approval
    }
    
    response = requests.post(
        f"{API_BASE}/mitigation/request",
        headers=get_headers(token),
        json=request_data
    )
    
    if response.status_code == 200:
        result = response.json()
        action_id = result["id"]
        print(f"✅ Mitigation request created! ID: {action_id}")
        print(f"   Status: {result['status']}")
        print(f"   Target IP: {result['target_ip']}")
        print(f"   Reason: {result['reason']}")
        return action_id
    else:
        print(f"❌ Failed to create request: {response.text}")
        return None

def test_get_pending_actions(token):
    """Test retrieving pending mitigation actions."""
    print("\n📋 Fetching pending mitigation actions...")
    
    response = requests.get(
        f"{API_BASE}/mitigation/pending",
        headers=get_headers(token)
    )
    
    if response.status_code == 200:
        actions = response.json()
        print(f"✅ Found {len(actions)} pending actions:")
        for action in actions:
            print(f"   - ID: {action['id']} | Type: {action['action_type']} | Target: {action['target_ip']}")
        return actions
    else:
        print(f"❌ Failed to fetch pending actions: {response.text}")
        return []

def test_approve_mitigation(token, action_id):
    """Test approving a mitigation action."""
    print(f"\n✅ Approving mitigation action {action_id}...")
    
    response = requests.post(
        f"{API_BASE}/mitigation/approve/{action_id}",
        headers=get_headers(token)
    )
    
    if response.status_code == 200:
        print(f"✅ Action {action_id} approved!")
        return True
    else:
        print(f"❌ Failed to approve: {response.text}")
        return False

def test_execute_mitigation(token, action_id, backend="snmp"):
    """Test executing a mitigation action."""
    print(f"\n⚡ Executing mitigation action {action_id} with backend: {backend}...")
    
    response = requests.post(
        f"{API_BASE}/mitigation/execute/{action_id}",
        headers=get_headers(token),
        params={"backend": backend}
    )
    
    if response.status_code == 200:
        result = response.json()
        print(f"✅ Execution completed!")
        print(f"   Success: {result.get('success')}")
        print(f"   Message: {result.get('message', 'N/A')}")
        return result.get('success')
    else:
        print(f"❌ Failed to execute: {response.text}")
        return False

def test_get_mitigation_history(token):
    """Test retrieving mitigation history."""
    print("\n📊 Fetching mitigation history...")
    
    response = requests.get(
        f"{API_BASE}/mitigation/history",
        headers=get_headers(token),
        params={"limit": 10}
    )
    
    if response.status_code == 200:
        history = response.json()
        print(f"✅ Found {len(history)} historical actions:")
        for action in history[:5]:  # Show first 5
            print(f"   - ID: {action['id']} | Status: {action['status']} | Type: {action['action_type']}")
            print(f"     Target: {action['target_ip']} | Reason: {action['reason']}")
        return history
    else:
        print(f"❌ Failed to fetch history: {response.text}")
        return []

def test_add_to_whitelist(token):
    """Test adding an IP to the whitelist."""
    print("\n🛡️ Adding IP to whitelist...")
    
    whitelist_data = {
        "ip_address": "192.168.1.50",
        "reason": "Test: Trusted server - should not be blocked"
    }
    
    response = requests.post(
        f"{API_BASE}/mitigation/whitelist",
        headers=get_headers(token),
        json=whitelist_data
    )
    
    if response.status_code == 200:
        result = response.json()
        print(f"✅ IP whitelisted!")
        print(f"   IP: {result['ip_address']}")
        print(f"   Reason: {result['reason']}")
        return True
    else:
        print(f"❌ Failed to whitelist: {response.text}")
        return False

def test_get_whitelist(token):
    """Test retrieving the whitelist."""
    print("\n📋 Fetching whitelist...")
    
    response = requests.get(
        f"{API_BASE}/mitigation/whitelist",
        headers=get_headers(token)
    )
    
    if response.status_code == 200:
        whitelist = response.json()
        print(f"✅ Found {len(whitelist)} whitelisted entries:")
        for entry in whitelist:
            print(f"   - IP: {entry.get('ip_address', 'N/A')} | Reason: {entry.get('reason', 'N/A')}")
        return whitelist
    else:
        print(f"❌ Failed to fetch whitelist: {response.text}")
        return []

def test_get_all_actions(token):
    """Test retrieving all mitigation actions."""
    print("\n📊 Fetching all mitigation actions...")
    
    response = requests.get(
        f"{API_BASE}/mitigation/actions",
        headers=get_headers(token)
    )
    
    if response.status_code == 200:
        actions = response.json()
        print(f"✅ Found {len(actions)} total actions:")
        
        status_counts = {}
        for action in actions:
            status = action['status']
            status_counts[status] = status_counts.get(status, 0) + 1
        
        print("   Status breakdown:")
        for status, count in status_counts.items():
            print(f"     - {status}: {count}")
        
        return actions
    else:
        print(f"❌ Failed to fetch actions: {response.text}")
        return []

def run_full_mitigation_workflow(token):
    """Run a complete mitigation workflow test."""
    print("\n" + "="*60)
    print("🚀 RUNNING FULL MITIGATION WORKFLOW TEST")
    print("="*60)
    
    # Step 1: Create a mitigation request
    action_id = test_create_mitigation_request(token)
    if not action_id:
        print("❌ Workflow failed at request creation")
        return
    
    time.sleep(1)
    
    # Step 2: Check pending actions
    test_get_pending_actions(token)
    
    time.sleep(1)
    
    # Step 3: Approve the action
    if not test_approve_mitigation(token, action_id):
        print("❌ Workflow failed at approval")
        return
    
    time.sleep(1)
    
    # Step 4: Execute the action
    test_execute_mitigation(token, action_id, backend="snmp")
    
    time.sleep(1)
    
    # Step 5: Check history
    test_get_mitigation_history(token)
    
    print("\n" + "="*60)
    print("✅ FULL WORKFLOW TEST COMPLETED!")
    print("="*60)

def main():
    """Main test function."""
    print("="*60)
    print("🔬 SafeLink Mitigation System Test Suite")
    print("="*60)
    
    # Login
    token = login()
    if not token:
        print("❌ Cannot proceed without authentication")
        return
    
    # Test menu
    while True:
        print("\n" + "="*60)
        print("Choose a test:")
        print("1. Run full mitigation workflow")
        print("2. Create mitigation request")
        print("3. View pending actions")
        print("4. View mitigation history")
        print("5. View all actions")
        print("6. Add to whitelist")
        print("7. View whitelist")
        print("8. Exit")
        print("="*60)
        
        choice = input("\nEnter choice (1-8): ").strip()
        
        if choice == "1":
            run_full_mitigation_workflow(token)
        elif choice == "2":
            test_create_mitigation_request(token)
        elif choice == "3":
            test_get_pending_actions(token)
        elif choice == "4":
            test_get_mitigation_history(token)
        elif choice == "5":
            test_get_all_actions(token)
        elif choice == "6":
            test_add_to_whitelist(token)
        elif choice == "7":
            test_get_whitelist(token)
        elif choice == "8":
            print("\n👋 Goodbye!")
            break
        else:
            print("❌ Invalid choice")

if __name__ == "__main__":
    main()
