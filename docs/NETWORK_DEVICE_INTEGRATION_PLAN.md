# Real Network Device Integration Guide for SafeLink

## Overview
This document outlines how to integrate SafeLink with real network equipment to enable actual threat mitigation capabilities (blocking IPs, shutting down ports, etc.) instead of just simulated actions.

---

## Current Status
- ✅ Mitigation workflow engine fully functional
- ✅ Request/Approval/Execution pipeline complete
- ⚠️ **Network commands are SIMULATED (placeholders)**
- ❌ No actual switch/router configuration changes

---

## What You Need

### Hardware Options

#### Option 1: Physical Network Equipment (Production-Ready)

**Managed Network Switch Requirements:**
- SNMP v2c/v3 support (for automated control)
- SSH/Telnet CLI access (alternative method)
- ACL (Access Control List) support
- Port shutdown capability
- VLAN support (optional, for isolation)

**Compatible Device Examples:**

**Budget-Friendly ($100-$300):**
- TP-Link T1600G-28TS (~$150-200)
  - 24 Gigabit ports
  - SNMP v1/v2c/v3
  - SSH + Web interface
  - ACL support
  - Perfect for testing/small deployments

- Netgear GS724T (~$200)
  - 24 Gigabit ports
  - SNMP support
  - CLI access
  - Good documentation

- D-Link DGS-1210 series (~$150-250)
  - SNMP support
  - Web/CLI management
  - VLAN support

**Mid-Range ($500-$1500):**
- Cisco Small Business SG300 series
  - Enterprise-grade features
  - Excellent SNMP support
  - Full CLI access
  - Reliable and well-documented

- HP 1920 series
  - SNMP v3 support
  - SSH access
  - Good management interface

**Enterprise ($2000+):**
- Cisco Catalyst 2960/3750 series
  - Full Cisco IOS
  - Advanced ACL support
  - Enterprise reliability
  - Extensive documentation

- Juniper EX series
  - JunOS support
  - Advanced security features
  - High performance

---

#### Option 2: Virtual Network Lab (FREE - Recommended for Testing)

**Using GNS3 (Graphical Network Simulator):**

**Advantages:**
- ✅ **Completely FREE** (no hardware purchase)
- ✅ Emulates real network devices
- ✅ Supports actual SNMP/SSH commands
- ✅ Safe testing environment
- ✅ Can simulate complex topologies
- ✅ Easy to reset/rebuild
- ✅ Multiple vendor support (Cisco, Juniper, Arista, etc.)

**Requirements:**
- Windows/Linux/macOS computer
- 8GB+ RAM (16GB recommended)
- 50GB+ free disk space
- CPU with virtualization support (VT-x/AMD-V)

**Software Needed:**
- GNS3 (Free): https://www.gns3.com/
- VirtualBox or VMware (Free/Paid)
- Cisco IOS images (requires Cisco account or educational license)
  - Alternatives: Cisco VIRL images, Open vSwitch

**What You Can Emulate:**
- Cisco routers (ISR, ASR series)
- Cisco switches (Catalyst, Nexus)
- Juniper routers
- Arista switches
- Open vSwitch (completely free, no licensing)

---

#### Option 3: EVE-NG (Emulated Virtual Environment)

**Similar to GNS3 but server-based:**
- Community edition: FREE
- Professional edition: Paid
- Web-based interface
- Supports multiple device types
- Good for larger topologies

**Installation:**
- Install on dedicated server or VM
- Import network device images
- Create network topology
- Connect SafeLink via API

---

### Software Requirements

**Python Libraries to Install:**

```bash
# SNMP support
pip install pysnmp pysnmp-hlapi

# SSH support for network devices
pip install paramiko netmiko

# Optional: Advanced networking libraries
pip install napalm  # Network Automation and Programmability Abstraction Layer
pip install ncclient  # NETCONF client
```

**Library Descriptions:**

- **pysnmp**: Low-level SNMP protocol implementation
- **pysnmp-hlapi**: High-level API for easier SNMP operations
- **paramiko**: SSH protocol implementation for Python
- **netmiko**: Multi-vendor library for SSH connections (Cisco, Juniper, HP, etc.)
- **napalm** (optional): Unified API for multiple vendors
- **ncclient** (optional): For NETCONF-based device management

---

## Implementation Architecture

### Current Architecture (Simulated)
```
SafeLink Backend
    ↓
MitigationService
    ↓
SNMP/SSH Backend (Placeholder)
    ↓
Log message: "[SNMP] Would execute command..."
    ↓
Return success (no actual execution)
```

### Target Architecture (Real Integration)
```
SafeLink Backend
    ↓
MitigationService
    ↓
Device Configuration Manager
    ↓
    ├── SNMP Backend → Real Network Switch
    ├── SSH Backend → Router/Firewall
    └── NETCONF Backend → Modern Devices
    ↓
Actual Configuration Changes
    ↓
Verification & Logging
```

---

## Configuration Requirements

### Switch/Router Setup

#### For SNMP Access:

**Cisco IOS Example:**
```
enable
configure terminal

! Configure SNMP community (read-write access)
snmp-server community safelink RW
snmp-server location "SafeLink Lab"
snmp-server contact "admin@safelink.local"

! Enable SNMP traps (optional)
snmp-server enable traps

! Configure ACL for SNMP access (security)
access-list 50 permit host 192.168.1.10  ! SafeLink server IP
snmp-server community safelink RW 50

exit
write memory
```

**TP-Link Web Interface:**
1. Login to switch web interface
2. Navigate to: System → SNMP
3. Enable SNMP
4. Set Community Name: `safelink`
5. Set Access Mode: `Read-Write`
6. Save configuration

---

#### For SSH Access:

**Cisco IOS Example:**
```
enable
configure terminal

! Set hostname and domain
hostname SafeSwitch
ip domain-name lab.local

! Generate RSA keys for SSH
crypto key generate rsa modulus 2048

! Create local user
username safelink privilege 15 secret SafeLink@2025

! Enable SSH
ip ssh version 2
ip ssh authentication-retries 3
ip ssh time-out 60

! Configure VTY lines for SSH access
line vty 0 15
 login local
 transport input ssh
 exec-timeout 15 0
exit

! Optional: ACL for SSH access
access-list 51 permit host 192.168.1.10
line vty 0 15
 access-class 51 in
exit

write memory
```

**TP-Link/HP Example:**
```
# Via CLI or Web Interface
1. Enable SSH service
2. Create admin user: safelink
3. Set password: SafeLink@2025
4. Configure allowed IP addresses
5. Save configuration
```

---

### SafeLink Configuration

**Add to `config/settings.py`:**

```python
# Network Device Management Settings
NETWORK_DEVICES = {
    "switch-01": {
        "ip": "192.168.1.100",
        "type": "cisco_ios",
        "snmp": {
            "community": "safelink",
            "version": "2c",  # or "3" for SNMPv3
            "port": 161
        },
        "ssh": {
            "username": "safelink",
            "password": "SafeLink@2025",  # Use env variable in production
            "port": 22,
            "device_type": "cisco_ios"
        }
    },
    "router-01": {
        "ip": "192.168.1.1",
        "type": "cisco_ios",
        "ssh": {
            "username": "admin",
            "password": os.getenv("ROUTER_PASSWORD"),
            "port": 22,
            "device_type": "cisco_ios"
        }
    }
}

# Mitigation Settings
MITIGATION_ENABLED = False  # Set to True to enable real mitigation
MITIGATION_REQUIRE_APPROVAL = True  # Always require manual approval
MITIGATION_DRY_RUN = True  # Test mode: log commands but don't execute
```

---

## Code Implementation

### Files That Need Modification

**1. `core/mitigation.py`:**
- Replace placeholder SNMP commands with real pysnmp calls
- Replace placeholder SSH commands with real paramiko/netmiko calls
- Add error handling for network timeouts
- Add device connectivity checks
- Implement rollback functionality

**2. `config/settings.py`:**
- Add device configuration section
- Add credentials management
- Add feature flags for enabling/disabling real mitigation

**3. New file: `core/device_manager.py`:**
- Device inventory management
- Connection pooling
- Health checks
- Configuration backup/restore

---

## SNMP Implementation Example

### Current Code (Placeholder):
```python
async def block_ip(self, ip: str, device_id: Optional[str] = None) -> bool:
    logger.warning("[SNMP] Using placeholder - actual SNMP commands not implemented")
    logger.info(f"[SNMP] Would create ACL: deny ip host {ip} any")
    return True
```

### Real Implementation:
```python
from pysnmp.hlapi import *

async def block_ip(self, ip: str, device_id: Optional[str] = None) -> bool:
    """Block IP address using SNMP ACL configuration."""
    try:
        device_config = NETWORK_DEVICES.get(device_id)
        if not device_config:
            logger.error(f"Device {device_id} not found in configuration")
            return False
        
        snmp_config = device_config['snmp']
        target_ip = device_config['ip']
        community = snmp_config['community']
        
        # OID for creating ACL entry (device-specific)
        # This is a simplified example - actual OIDs vary by vendor
        acl_oid = '1.3.6.1.4.1.9.9.179.1.3.1.1.3'  # Cisco ACL table
        
        # Create ACL to block IP
        errorIndication, errorStatus, errorIndex, varBinds = next(
            setCmd(
                SnmpEngine(),
                CommunityData(community, mpModel=1),  # SNMPv2c
                UdpTransportTarget((target_ip, snmp_config['port']), timeout=5.0, retries=3),
                ContextData(),
                ObjectType(ObjectIdentity(acl_oid), OctetString(f'deny ip host {ip} any'))
            )
        )
        
        if errorIndication:
            logger.error(f"[SNMP] Error: {errorIndication}")
            return False
        elif errorStatus:
            logger.error(f"[SNMP] Error: {errorStatus.prettyPrint()}")
            return False
        else:
            logger.info(f"[SNMP] Successfully blocked IP {ip} on {device_id}")
            return True
            
    except Exception as e:
        logger.error(f"[SNMP] Exception blocking IP {ip}: {e}")
        return False
```

---

## SSH Implementation Example

### Current Code (Placeholder):
```python
async def block_ip(self, ip: str, device_id: Optional[str] = None) -> bool:
    logger.warning("[SSH] Using placeholder - actual SSH execution not implemented")
    logger.info(f"[SSH] Would execute: access-list 100 deny ip host {ip} any")
    return True
```

### Real Implementation:
```python
from netmiko import ConnectHandler

async def block_ip(self, ip: str, device_id: Optional[str] = None) -> bool:
    """Block IP address using SSH CLI commands."""
    try:
        device_config = NETWORK_DEVICES.get(device_id)
        if not device_config:
            logger.error(f"Device {device_id} not found")
            return False
        
        ssh_config = device_config['ssh']
        
        # Connection parameters
        device = {
            'device_type': ssh_config['device_type'],
            'host': device_config['ip'],
            'username': ssh_config['username'],
            'password': ssh_config['password'],
            'port': ssh_config['port'],
            'timeout': 10,
        }
        
        # Connect to device
        logger.info(f"[SSH] Connecting to {device_id} ({device_config['ip']})")
        connection = ConnectHandler(**device)
        
        # Commands to block IP (Cisco IOS example)
        commands = [
            'configure terminal',
            f'access-list 100 deny ip host {ip} any',
            f'access-list 100 permit ip any any',  # Keep existing traffic
            'interface GigabitEthernet0/1',  # Apply to interface
            'ip access-group 100 in',
            'end',
            'write memory'
        ]
        
        # Execute commands
        output = connection.send_config_set(commands)
        logger.info(f"[SSH] Command output:\n{output}")
        
        # Verify configuration
        verify = connection.send_command('show access-lists 100')
        logger.info(f"[SSH] Verification:\n{verify}")
        
        connection.disconnect()
        logger.info(f"[SSH] Successfully blocked IP {ip} on {device_id}")
        return True
        
    except Exception as e:
        logger.error(f"[SSH] Error blocking IP {ip}: {e}")
        return False
```

---

## Testing Procedure

### Step 1: Setup Test Environment

**Option A - Physical Switch:**
1. Connect switch to network
2. Assign static IP: 192.168.1.100
3. Enable SNMP/SSH as shown above
4. Test connectivity: `ping 192.168.1.100`

**Option B - GNS3 Virtual Lab:**
1. Install GNS3
2. Import Cisco IOS image
3. Create simple topology: PC → Switch → SafeLink Server
4. Configure virtual switch with SNMP/SSH
5. Test connectivity within GNS3

### Step 2: Install Python Libraries

```powershell
cd E:\coreproject\venv\Scripts
.\pip.exe install pysnmp paramiko netmiko
```

### Step 3: Update SafeLink Configuration

Edit `config/settings.py`:
```python
MITIGATION_DRY_RUN = True  # Start with dry-run mode
MITIGATION_ENABLED = True
```

Add device configuration as shown above.

### Step 4: Test SNMP Connectivity

Create test script: `test_snmp_connection.py`
```python
from pysnmp.hlapi import *

# Test SNMP connection
iterator = getCmd(
    SnmpEngine(),
    CommunityData('safelink'),
    UdpTransportTarget(('192.168.1.100', 161)),
    ContextData(),
    ObjectType(ObjectIdentity('SNMPv2-MIB', 'sysDescr', 0))
)

errorIndication, errorStatus, errorIndex, varBinds = next(iterator)

if errorIndication:
    print(f"Error: {errorIndication}")
else:
    for varBind in varBinds:
        print(f"Device: {varBind[1]}")
```

Run:
```powershell
..\..\venv\Scripts\python.exe test_snmp_connection.py
```

### Step 5: Test SSH Connectivity

Create test script: `test_ssh_connection.py`
```python
from netmiko import ConnectHandler

device = {
    'device_type': 'cisco_ios',
    'host': '192.168.1.100',
    'username': 'safelink',
    'password': 'SafeLink@2025',
    'port': 22,
}

try:
    connection = ConnectHandler(**device)
    output = connection.send_command('show version')
    print(f"Connected successfully!\n{output}")
    connection.disconnect()
except Exception as e:
    print(f"Error: {e}")
```

Run:
```powershell
..\..\venv\Scripts\python.exe test_ssh_connection.py
```

### Step 6: Enable Real Mitigation

After successful connectivity tests:

1. Update `mitigation.py` with real SNMP/SSH code
2. Set `MITIGATION_DRY_RUN = False`
3. Create test mitigation request via UI
4. Monitor switch configuration changes
5. Verify ACLs are created
6. Test rollback functionality

---

## Security Considerations

### 1. Credentials Management
- **Never hardcode passwords in code**
- Use environment variables: `os.getenv('SWITCH_PASSWORD')`
- Consider using HashiCorp Vault or AWS Secrets Manager
- Encrypt passwords in configuration files

### 2. Network Security
- **Use SNMP v3** (encrypted) instead of v2c when possible
- **Enable SSH only**, disable Telnet
- **Use ACLs** to restrict SNMP/SSH access to SafeLink server IP only
- **Use strong passwords** and key-based SSH authentication

### 3. Safeguards
- **Always require manual approval** for critical actions
- **Implement whitelist** for protected devices/IPs
- **Enable audit logging** for all mitigation actions
- **Test in isolated environment** first
- **Implement rollback** for all actions
- **Set timeouts** to prevent hanging connections
- **Rate limiting** to prevent flooding devices with commands

### 4. Change Control
- **Backup device configs** before making changes
- **Verify changes** after execution
- **Monitor device health** after mitigation
- **Document all changes** in audit trail

---

## Cost Analysis

### Budget Breakdown

**Virtual Lab (FREE):**
- GNS3: $0
- VirtualBox: $0
- Network images: $0 (if using open-source alternatives)
- **Total: $0**

**Basic Physical Lab ($200-400):**
- TP-Link T1600G-28TS: $150-200
- Cat6 Ethernet cables: $20
- Power strip: $15
- Old laptop/Raspberry Pi for testing: $50-100
- **Total: ~$235-335**

**Production Setup ($1000-3000):**
- 2x Cisco SG300-28 switches: $1000-1400
- Cisco ISR router: $500-800
- Rack mount equipment: $200
- UPS backup: $150
- Cabling and accessories: $100
- **Total: ~$1950-2650**

---

## Recommended Path Forward

### Phase 1: Virtual Testing (Week 1-2)
1. Install GNS3
2. Set up virtual network topology
3. Implement real SNMP/SSH code in SafeLink
4. Test all mitigation actions in virtual environment
5. Debug and refine implementation

**Cost: $0**

### Phase 2: Physical Testing (Week 3-4)
1. Purchase budget managed switch (~$150)
2. Set up small lab network
3. Test SafeLink with real hardware
4. Validate all mitigation scenarios
5. Performance testing

**Cost: ~$200**

### Phase 3: Production Deployment (Month 2+)
1. Acquire production-grade equipment
2. Deploy in staging environment
3. Comprehensive security audit
4. User training
5. Phased rollout to production

**Cost: $1000-3000 depending on scale**

---

## Vendor-Specific Guides

### Cisco IOS
- Command reference: https://www.cisco.com/c/en/us/support/ios-nx-os-software/ios-15-4m-t/products-command-reference-list.html
- SNMP MIBs: Standard Cisco MIBs
- Device types for netmiko: `cisco_ios`, `cisco_xe`, `cisco_nxos`

### TP-Link
- Web-based management + limited CLI
- SNMP v1/v2c support
- Simpler MIB structure
- Good for learning/testing

### HP/Aruba
- ProCurve switches use HP MIBs
- CLI similar to Cisco but different syntax
- Good SNMP support
- Device type: `hp_procurve`

### Juniper
- JunOS with NETCONF support
- Advanced security features
- Different CLI structure
- Device type: `juniper_junos`

---

## Alternative Approaches

### 1. Using NAPALM (Network Automation Library)
- Vendor-agnostic API
- Supports Cisco, Juniper, Arista, etc.
- Easier than raw SSH/SNMP
- Recommended for multi-vendor environments

### 2. Using Ansible
- Automate device configuration
- Playbooks for common tasks
- Can be integrated with SafeLink
- Good for bulk operations

### 3. Using Network Controller APIs
- Cisco DNA Center
- Aruba ClearPass
- Meraki Dashboard API
- Easier integration, but requires controller

---

## Support Resources

### Documentation
- pysnmp: http://snmplabs.com/pysnmp/
- netmiko: https://github.com/ktbyers/netmiko
- GNS3: https://docs.gns3.com/
- Cisco IOS: https://www.cisco.com/c/en/us/support/docs

### Communities
- Reddit: r/networking, r/homelab
- NetworkEngineering Discord
- GNS3 Community Forums
- Stack Overflow (network-programming tag)

### Learning Resources
- Free CCNA videos on YouTube
- GNS3 Academy (free courses)
- Network Automation with Python (book)
- Cisco DevNet (free learning tracks)

---

## Decision Checklist

Before implementing real device integration, consider:

- [ ] Do you have budget for hardware? (~$200-2000)
- [ ] Are you comfortable with network device configuration?
- [ ] Do you have a safe test environment?
- [ ] Can you dedicate time to learning SNMP/SSH protocols?
- [ ] Is your deployment scale worth the complexity?
- [ ] Do you have network security expertise on team?
- [ ] Can you handle potential misconfiguration risks?
- [ ] Do you need multi-vendor support?

**If mostly YES:** Proceed with real integration
**If mostly NO:** Virtual lab first, physical later
**If UNSURE:** Start with GNS3 virtual lab (no cost, low risk)

---

## Next Steps

When ready to proceed:

1. **Choose your approach**:
   - Virtual Lab (GNS3) - FREE, no risk
   - Budget Switch (~$150) - Real hardware experience
   - Full Production Setup ($1000+) - Enterprise deployment

2. **Inform developer** (me) which option you choose

3. **I will provide**:
   - Complete code implementation for chosen approach
   - Step-by-step setup guide
   - Configuration templates
   - Test procedures
   - Troubleshooting guide

4. **Timeline estimate**:
   - Virtual Lab: 1-2 weeks
   - Physical Lab: 2-4 weeks
   - Production Ready: 1-3 months

---

**Status:** Ready to implement when decision is made
**Risk Level:** Low (virtual) to Medium (physical)
**Cost:** $0 (virtual) to $200-3000 (physical)
**Time Investment:** 20-100 hours depending on scope
