# SafeLink Mitigation System - Testing & Verification Guide

## Overview

The SafeLink mitigation system provides **automated threat response** capabilities to block or isolate detected attackers. However, **the actual network device integration (SNMP/SSH) uses placeholders** - it simulates the commands but doesn't execute them on real hardware.

## Current Implementation Status

### ✅ Fully Functional:
1. **Mitigation Request Management** - Create, track, approve requests
2. **Workflow Engine** - Pending → Approved → Executing → Success/Failed
3. **Whitelist System** - Protect trusted IPs/MACs from blocking
4. **Audit Trail** - Complete history of all mitigation actions
5. **Role-based Access** - Permission-based approval system
6. **API Integration** - Full REST API for mitigation operations
7. **Frontend UI** - Mitigation page with request/approval interface

### ⚠️ Placeholder/Simulated:
1. **SNMP Commands** - Logs what WOULD be sent, doesn't actually execute
2. **SSH Commands** - Logs commands, doesn't connect to real devices
3. **Network Device Integration** - No actual router/switch control

---

## How the Mitigation System Works

### Architecture:

```
Threat Detected (Alert) 
    ↓
Mitigation Request Created
    ↓
[PENDING] - Awaits approval (if required)
    ↓
Admin Approves
    ↓
[APPROVED] - Ready for execution
    ↓
Execute with Backend (SNMP/SSH)
    ↓
[EXECUTING] - Running commands
    ↓
[SUCCESS] or [FAILED]
    ↓
Audit Log Entry Created
```

### Mitigation Types:

1. **BLOCK_IP** - Block traffic from specific IP address
2. **BLOCK_MAC** - Block traffic from specific MAC address
3. **PORT_SHUTDOWN** - Shutdown network switch port
4. **VLAN_ISOLATION** - Move device to quarantine VLAN
5. **RATE_LIMIT** - Apply bandwidth restrictions

### Backends:

1. **SNMP Backend** - For switches/routers with SNMP support
   - Sends SNMP SET commands to modify device configuration
   - Examples: Shutdown port, modify ACL, change VLAN
   
2. **SSH Backend** - For devices with CLI access
   - Executes CLI commands via SSH
   - Examples: Cisco IOS commands, Linux iptables

---

## How to Test Mitigation (Step-by-Step)

### Method 1: Using the Test Script

1. **Start the backend** (if not already running):
   ```powershell
   cd E:\coreproject\Backend\SafeLink_Backend
   ..\..\venv\Scripts\python.exe -m uvicorn api:app --reload --port 8000
   ```

2. **Run the test script**:
   ```powershell
   cd E:\coreproject\Backend\SafeLink_Backend
   ..\..\venv\Scripts\python.exe test_mitigation.py
   ```

3. **Follow the interactive menu**:
   - Choose option `1` for full workflow test
   - Or test individual features (2-7)

4. **Observe the output**:
   ```
   ✅ Mitigation request created! ID: 1
   ✅ Action 1 approved!
   ⚡ Executing mitigation action 1 with backend: snmp...
   ```

### Method 2: Using the Frontend UI

1. **Navigate to Mitigation page** in the web interface

2. **Create a mitigation request**:
   - Click "Request Mitigation"
   - Fill in:
     - IP Address: `192.168.1.100`
     - Reason: "Test ARP spoofing mitigation"
     - Backend: `SNMP`
   - Submit

3. **View pending actions**:
   - Check the "Pending Actions" tab
   - You should see your request with status "PENDING"

4. **Approve the request** (if you have permission):
   - Click "Approve" button
   - Status changes to "APPROVED"

5. **Execute the mitigation**:
   - Click "Execute" button
   - Select backend (SNMP/SSH)
   - Watch status change: EXECUTING → SUCCESS

6. **Check history**:
   - Go to "History" tab
   - See complete audit trail

### Method 3: Using API Directly (curl/Postman)

1. **Login to get token**:
   ```powershell
   $response = Invoke-RestMethod -Uri "http://127.0.0.1:8000/auth/login" -Method POST -Body (@{username="admin"; password="admin"} | ConvertTo-Json) -ContentType "application/json"
   $token = $response.access_token
   ```

2. **Create mitigation request**:
   ```powershell
   $headers = @{Authorization="Bearer $token"; "Content-Type"="application/json"}
   $body = @{
       action_type="block_ip"
       target_ip="192.168.1.100"
       target_mac="aa:bb:cc:dd:ee:99"
       device_id="switch-01"
       reason="Test mitigation"
       auto_approve=$false
   } | ConvertTo-Json
   
   Invoke-RestMethod -Uri "http://127.0.0.1:8000/mitigation/request" -Method POST -Headers $headers -Body $body
   ```

3. **View pending actions**:
   ```powershell
   Invoke-RestMethod -Uri "http://127.0.0.1:8000/mitigation/pending" -Headers $headers
   ```

4. **Approve action** (replace `1` with actual action ID):
   ```powershell
   Invoke-RestMethod -Uri "http://127.0.0.1:8000/mitigation/approve/1" -Method POST -Headers $headers
   ```

5. **Execute mitigation**:
   ```powershell
   Invoke-RestMethod -Uri "http://127.0.0.1:8000/mitigation/execute/1?backend=snmp" -Method POST -Headers $headers
   ```

---

## Verification Points

### ✅ What You CAN Verify:

1. **Request Creation**:
   - Mitigation request appears in database
   - Status is correctly set to PENDING
   - All fields (IP, MAC, reason) are stored

2. **Approval Workflow**:
   - Status changes from PENDING → APPROVED
   - Timestamp and approver are recorded
   - Approval requires correct permissions

3. **Execution Flow**:
   - Status changes: APPROVED → EXECUTING → SUCCESS
   - Execution timestamp is recorded
   - Logs show simulated SNMP/SSH commands

4. **Whitelist Protection**:
   - Whitelisted IPs/MACs cannot be blocked
   - Error message: "Target is whitelisted"

5. **Audit Trail**:
   - All actions logged in `mitigation_actions` table
   - Complete history accessible via API/UI
   - Includes who created, approved, executed

6. **Permission System**:
   - Users without `mitigation:create` cannot create requests
   - Users without `mitigation:approve` cannot approve
   - Returns 403 Forbidden for unauthorized attempts

### ❌ What You CANNOT Verify (Placeholders):

1. **Actual Network Changes**:
   - No real switch ports are shutdown
   - No actual ACLs are modified
   - No real devices are contacted

2. **SNMP/SSH Connectivity**:
   - No authentication to real devices
   - No network errors from devices
   - No device status feedback

---

## Backend Logs to Check

When mitigation is executed, check the backend console for logs:

### SNMP Backend Logs:
```
INFO | MitigationService | Mitigation 1 approved by admin
[SNMP] Blocking IP 192.168.1.100 on device switch-01
[SNMP] Using placeholder - actual SNMP commands not implemented
[SNMP] Would create ACL: deny ip host 192.168.1.100 any
```

### SSH Backend Logs:
```
[SSH] Blocking IP 192.168.1.100 on device router-01
[SSH] Using placeholder - actual SSH execution not implemented
[SSH] Would execute: conf t
[SSH] Would execute: access-list 100 deny ip host 192.168.1.100 any
```

---

## Database Tables to Check

### Check mitigation_actions table:
```sql
sqlite3 safelink.db
SELECT id, action_type, target_ip, status, reason, created_at FROM mitigation_actions;
```

### Check whitelist table:
```sql
SELECT id, ip_address, mac_address, reason, added_at FROM whitelist;
```

---

## Integration with Real Devices (Future Enhancement)

To make mitigation actually work with real network equipment:

### For SNMP Backend:
1. Install actual network device (Cisco switch, etc.)
2. Enable SNMP write community on device
3. Update `SNMPMitigationBackend` class:
   - Remove placeholder comments
   - Uncomment actual `pysnmp` commands
   - Configure community string and device IPs

### For SSH Backend:
1. Install paramiko: `pip install paramiko`
2. Configure device credentials in settings
3. Update `SSHMitigationBackend` class:
   - Implement actual SSH connection
   - Execute real CLI commands
   - Handle device-specific command syntax

---

## Summary

**Current Status**: The mitigation system is **fully functional as a workflow engine** but uses **simulated network commands**.

**What Works**:
- ✅ Complete request/approval/execution workflow
- ✅ Database tracking and audit logs
- ✅ Frontend UI for management
- ✅ Whitelist protection
- ✅ Permission-based access control
- ✅ API endpoints

**What's Simulated**:
- ⚠️ SNMP commands (logged but not sent)
- ⚠️ SSH commands (logged but not executed)
- ⚠️ Actual device configuration changes

**How to Verify It's Working**:
1. Run `test_mitigation.py` and check console output
2. Use the frontend Mitigation page
3. Check database tables for action records
4. Review backend logs for simulated commands

The system is **production-ready for testing workflows** but would need **real device integration** for actual network enforcement.
