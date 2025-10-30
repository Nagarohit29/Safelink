"""
MAC Vendor Lookup and Consistency Checking

Provides MAC address vendor identification and consistency validation
to detect spoofed or anomalous MAC addresses.
"""

import logging
from typing import Optional, Dict, Tuple

logger = logging.getLogger(__name__)


class MACVendorChecker:
    """
    MAC Vendor lookup and consistency validation.
    Uses OUI (Organizationally Unique Identifier) database.
    """
    
    # Common MAC vendor OUI prefixes (first 3 octets)
    # Format: "XX:XX:XX" -> "Vendor Name"
    OUI_DATABASE = {
        # Major network equipment vendors
        "00:00:0C": "Cisco",
        "00:01:42": "Cisco",
        "00:01:43": "Cisco",
        "00:01:63": "Cisco",
        "00:01:64": "Cisco",
        "00:01:96": "Cisco",
        "00:01:97": "Cisco",
        "00:01:C7": "Cisco",
        "00:02:16": "Cisco",
        "00:02:17": "Cisco",
        "00:02:3D": "Cisco",
        "00:02:4A": "Cisco",
        "00:02:4B": "Cisco",
        "00:02:B9": "Cisco",
        "00:02:BA": "Cisco",
        "00:02:FC": "Cisco",
        "00:02:FD": "Cisco",
        "00:03:31": "Cisco",
        "00:03:32": "Cisco",
        "00:03:6B": "Cisco",
        "00:03:6C": "Cisco",
        "00:03:9F": "Cisco",
        "00:03:A0": "Cisco",
        "00:03:E3": "Cisco",
        "00:03:E4": "Cisco",
        "00:03:FD": "Cisco",
        "00:03:FE": "Cisco",
        
        # HP/Aruba
        "00:00:0D": "HP",
        "00:01:E6": "HP",
        "00:01:E7": "HP",
        "00:02:A5": "HP",
        "00:04:EA": "HP",
        "00:08:02": "HP",
        "00:08:83": "HP",
        "00:0B:CD": "HP",
        "00:0E:7F": "HP",
        "00:0F:20": "HP",
        "00:10:83": "HP",
        "00:11:0A": "HP",
        "00:12:79": "HP",
        "00:13:21": "HP",
        "00:14:38": "HP",
        "00:14:C2": "HP",
        "00:15:60": "HP",
        "00:16:35": "HP",
        "00:17:08": "HP",
        "00:17:A4": "HP",
        "00:18:FE": "HP",
        "00:19:BB": "HP",
        "00:1A:4B": "HP",
        "00:1B:3F": "HP",
        "00:1C:2E": "HP",
        "00:1E:0B": "HP",
        "00:1F:29": "HP",
        "00:21:5A": "HP",
        "00:22:64": "HP",
        "00:23:7D": "HP",
        "00:24:81": "HP",
        "00:25:B3": "HP",
        "00:26:55": "HP",
        
        # Dell
        "00:06:5B": "Dell",
        "00:08:74": "Dell",
        "00:0B:DB": "Dell",
        "00:0D:56": "Dell",
        "00:0F:1F": "Dell",
        "00:11:43": "Dell",
        "00:12:3F": "Dell",
        "00:13:72": "Dell",
        "00:14:22": "Dell",
        "00:15:C5": "Dell",
        "00:16:F0": "Dell",
        "00:18:8B": "Dell",
        "00:19:B9": "Dell",
        "00:1A:A0": "Dell",
        "00:1C:23": "Dell",
        "00:1D:09": "Dell",
        "00:1E:4F": "Dell",
        "00:21:70": "Dell",
        "00:21:9B": "Dell",
        "00:22:19": "Dell",
        "00:23:AE": "Dell",
        "00:24:E8": "Dell",
        "00:25:64": "Dell",
        "00:26:B9": "Dell",
        
        # Intel
        "00:02:B3": "Intel",
        "00:03:47": "Intel",
        "00:04:23": "Intel",
        "00:07:E9": "Intel",
        "00:0C:F1": "Intel",
        "00:0E:0C": "Intel",
        "00:11:11": "Intel",
        "00:12:F0": "Intel",
        "00:13:02": "Intel",
        "00:13:20": "Intel",
        "00:13:CE": "Intel",
        "00:13:E8": "Intel",
        "00:15:00": "Intel",
        "00:15:17": "Intel",
        "00:16:6F": "Intel",
        "00:16:76": "Intel",
        "00:16:EA": "Intel",
        "00:16:EB": "Intel",
        "00:18:DE": "Intel",
        "00:19:D1": "Intel",
        "00:19:D2": "Intel",
        "00:1B:21": "Intel",
        "00:1B:77": "Intel",
        "00:1C:BF": "Intel",
        "00:1D:E0": "Intel",
        "00:1D:E1": "Intel",
        "00:1E:64": "Intel",
        "00:1E:65": "Intel",
        "00:1E:67": "Intel",
        "00:1F:3A": "Intel",
        "00:1F:3B": "Intel",
        "00:1F:3C": "Intel",
        
        # Broadcom
        "00:10:18": "Broadcom",
        "00:14:A4": "Broadcom",
        "00:17:42": "Broadcom",
        "00:19:A6": "Broadcom",
        "00:1C:C0": "Broadcom",
        "00:1E:8C": "Broadcom",
        "00:21:91": "Broadcom",
        "00:23:CD": "Broadcom",
        "00:25:9C": "Broadcom",
        
        # Realtek
        "00:E0:4C": "Realtek",
        "52:54:00": "Realtek",
        "00:01:6C": "Realtek",
        "00:0B:6A": "Realtek",
        "00:0C:76": "Realtek",
        "00:0E:2E": "Realtek",
        "00:11:D8": "Realtek",
        "00:13:46": "Realtek",
        "00:15:E9": "Realtek",
        "00:19:21": "Realtek",
        "00:1C:4A": "Realtek",
        "00:1D:60": "Realtek",
        "00:1F:1F": "Realtek",
        "00:21:27": "Realtek",
        "00:24:1D": "Realtek",
        
        # Apple
        "00:03:93": "Apple",
        "00:0A:27": "Apple",
        "00:0A:95": "Apple",
        "00:0D:93": "Apple",
        "00:10:FA": "Apple",
        "00:11:24": "Apple",
        "00:14:51": "Apple",
        "00:16:CB": "Apple",
        "00:17:F2": "Apple",
        "00:19:E3": "Apple",
        "00:1B:63": "Apple",
        "00:1C:B3": "Apple",
        "00:1D:4F": "Apple",
        "00:1E:52": "Apple",
        "00:1E:C2": "Apple",
        "00:1F:5B": "Apple",
        "00:1F:F3": "Apple",
        "00:21:E9": "Apple",
        "00:22:41": "Apple",
        "00:23:12": "Apple",
        "00:23:32": "Apple",
        "00:23:6C": "Apple",
        "00:23:DF": "Apple",
        "00:24:36": "Apple",
        "00:25:00": "Apple",
        "00:25:4B": "Apple",
        "00:25:BC": "Apple",
        "00:26:08": "Apple",
        "00:26:4A": "Apple",
        "00:26:B0": "Apple",
        "00:26:BB": "Apple",
        
        # VMware
        "00:0C:29": "VMware",
        "00:05:69": "VMware",
        "00:1C:14": "VMware",
        "00:50:56": "VMware",
        
        # VirtualBox
        "08:00:27": "VirtualBox",
        
        # Microsoft
        "00:03:FF": "Microsoft",
        "00:0D:3A": "Microsoft",
        "00:12:5A": "Microsoft",
        "00:15:5D": "Microsoft",
        "00:17:FA": "Microsoft",
        "00:1D:D8": "Microsoft",
        "00:22:48": "Microsoft",
        "00:25:AE": "Microsoft",
        
        # D-Link
        "00:05:5D": "D-Link",
        "00:0D:88": "D-Link",
        "00:11:95": "D-Link",
        "00:13:46": "D-Link",
        "00:15:E9": "D-Link",
        "00:17:9A": "D-Link",
        "00:19:5B": "D-Link",
        "00:1B:11": "D-Link",
        "00:1C:F0": "D-Link",
        "00:1E:58": "D-Link",
        "00:21:91": "D-Link",
        "00:22:B0": "D-Link",
        "00:24:01": "D-Link",
        "00:26:5A": "D-Link",
        
        # TP-Link
        "00:27:19": "TP-Link",
        "10:FE:ED": "TP-Link",
        "14:CF:92": "TP-Link",
        "18:D6:C7": "TP-Link",
        "1C:3B:F3": "TP-Link",
        "24:A4:3C": "TP-Link",
        "50:C7:BF": "TP-Link",
        "54:A0:50": "TP-Link",
        "64:66:B3": "TP-Link",
        "84:16:F9": "TP-Link",
        "90:F6:52": "TP-Link",
        "C0:25:E9": "TP-Link",
        "E8:DE:27": "TP-Link",
        "F4:F2:6D": "TP-Link",
        "F8:1A:67": "TP-Link",
    }
    
    def __init__(self):
        """Initialize MAC vendor checker."""
        self.cache: Dict[str, Optional[str]] = {}
        logger.info(f"MACVendorChecker initialized with {len(self.OUI_DATABASE)} OUI entries")
    
    def normalize_mac(self, mac: str) -> str:
        """
        Normalize MAC address to standard format (XX:XX:XX:XX:XX:XX).
        
        Args:
            mac: MAC address in various formats
            
        Returns:
            Normalized MAC address
        """
        # Remove common separators
        mac_clean = mac.replace(":", "").replace("-", "").replace(".", "").upper()
        
        # Add colons every 2 characters
        if len(mac_clean) == 12:
            return ":".join([mac_clean[i:i+2] for i in range(0, 12, 2)])
        
        return mac
    
    def get_oui(self, mac: str) -> str:
        """
        Extract OUI (first 3 octets) from MAC address.
        
        Args:
            mac: MAC address
            
        Returns:
            OUI in XX:XX:XX format
        """
        normalized = self.normalize_mac(mac)
        parts = normalized.split(":")
        
        if len(parts) >= 3:
            return ":".join(parts[:3]).upper()
        
        return ""
    
    def lookup_vendor(self, mac: str) -> Optional[str]:
        """
        Look up vendor name from MAC address.
        
        Args:
            mac: MAC address
            
        Returns:
            Vendor name or None if not found
        """
        # Check cache first
        if mac in self.cache:
            return self.cache[mac]
        
        oui = self.get_oui(mac)
        
        if not oui:
            return None
        
        vendor = self.OUI_DATABASE.get(oui)
        
        # Cache result
        self.cache[mac] = vendor
        
        return vendor
    
    def check_consistency(self, mac: str, expected_vendor: Optional[str] = None) -> Tuple[bool, str]:
        """
        Check MAC address vendor consistency.
        
        Args:
            mac: MAC address to check
            expected_vendor: Expected vendor name (optional)
            
        Returns:
            Tuple of (is_consistent, message)
        """
        vendor = self.lookup_vendor(mac)
        
        if vendor is None:
            return False, f"Unknown vendor for MAC {mac} (OUI: {self.get_oui(mac)})"
        
        if expected_vendor and vendor.lower() != expected_vendor.lower():
            return False, f"Vendor mismatch for MAC {mac}: expected {expected_vendor}, got {vendor}"
        
        return True, f"MAC {mac} vendor: {vendor}"
    
    def is_known_vendor(self, mac: str) -> bool:
        """
        Check if MAC address has a known vendor.
        
        Args:
            mac: MAC address
            
        Returns:
            True if vendor is known
        """
        return self.lookup_vendor(mac) is not None
    
    def detect_anomalies(self, src_mac: str, dst_mac: str, src_ip: str, dst_ip: str) -> Dict[str, any]:
        """
        Detect MAC vendor anomalies that could indicate spoofing.
        
        Args:
            src_mac: Source MAC address
            dst_mac: Destination MAC address
            src_ip: Source IP address
            dst_ip: Destination IP address
            
        Returns:
            Dictionary with anomaly detection results
        """
        result = {
            "has_anomaly": False,
            "anomalies": [],
            "src_vendor": None,
            "dst_vendor": None,
            "confidence": 0.0
        }
        
        # Lookup vendors
        src_vendor = self.lookup_vendor(src_mac)
        dst_vendor = self.lookup_vendor(dst_mac)
        
        result["src_vendor"] = src_vendor
        result["dst_vendor"] = dst_vendor
        
        # Check for unknown vendors (potential spoofing)
        if src_vendor is None:
            result["anomalies"].append(f"Unknown source MAC vendor (OUI: {self.get_oui(src_mac)})")
            result["confidence"] += 0.3
        
        if dst_vendor is None:
            result["anomalies"].append(f"Unknown destination MAC vendor (OUI: {self.get_oui(dst_mac)})")
            result["confidence"] += 0.1
        
        # Check for broadcast/multicast anomalies
        if src_mac.startswith("FF:FF") or src_mac.startswith("01:00"):
            result["anomalies"].append("Source MAC is broadcast/multicast (spoofing indicator)")
            result["confidence"] += 0.4
        
        # Check for locally administered addresses (bit 1 of first octet)
        first_octet = int(src_mac.split(":")[0], 16)
        if first_octet & 0x02:
            result["anomalies"].append("Source MAC is locally administered (potential spoofing)")
            result["confidence"] += 0.2
        
        # Set anomaly flag
        if len(result["anomalies"]) > 0:
            result["has_anomaly"] = True
        
        # Cap confidence at 1.0
        result["confidence"] = min(result["confidence"], 1.0)
        
        return result
    
    def get_statistics(self) -> Dict[str, any]:
        """
        Get MAC vendor checker statistics.
        
        Returns:
            Statistics dictionary
        """
        return {
            "total_oui_entries": len(self.OUI_DATABASE),
            "cache_size": len(self.cache),
            "unique_vendors": len(set(self.OUI_DATABASE.values()))
        }


# Global instance
_mac_vendor_checker = None


def get_mac_vendor_checker() -> MACVendorChecker:
    """Get singleton MAC vendor checker instance."""
    global _mac_vendor_checker
    if _mac_vendor_checker is None:
        _mac_vendor_checker = MACVendorChecker()
    return _mac_vendor_checker
