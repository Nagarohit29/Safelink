"""
Advanced ARP Packet Analysis

Provides detailed ARP packet analysis including gratuitous ARP detection,
opcode analysis, and timing-based anomaly detection.
"""

import logging
import time
from collections import defaultdict, deque
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, field
from datetime import datetime

logger = logging.getLogger(__name__)


@dataclass
class ARPPacketInfo:
    """Information about an ARP packet."""
    timestamp: float
    src_mac: str
    dst_mac: str
    src_ip: str
    dst_ip: str
    opcode: int  # 1=request, 2=reply
    is_gratuitous: bool = False
    is_probe: bool = False
    inter_arrival_time: float = 0.0


class ARPAnalyzer:
    """
    Advanced ARP packet analyzer for detecting anomalies.
    
    Features:
    - Gratuitous ARP detection
    - ARP probe detection
    - Timing analysis (inter-arrival times)
    - Request-reply correlation
    - Opcode validation
    """
    
    def __init__(self, max_history: int = 1000, timing_window: int = 60):
        """
        Initialize ARP analyzer.
        
        Args:
            max_history: Maximum packets to keep in history
            timing_window: Time window in seconds for timing analysis
        """
        self.max_history = max_history
        self.timing_window = timing_window
        
        # Packet history per IP
        self.packet_history: Dict[str, deque] = defaultdict(lambda: deque(maxlen=max_history))
        
        # Last packet timestamp per IP
        self.last_packet_time: Dict[str, float] = {}
        
        # Pending requests (for request-reply matching)
        self.pending_requests: Dict[Tuple[str, str], float] = {}
        
        # Statistics
        self.stats = {
            "total_packets": 0,
            "gratuitous_count": 0,
            "probe_count": 0,
            "request_count": 0,
            "reply_count": 0,
            "unmatched_replies": 0,
            "avg_inter_arrival": 0.0
        }
        
        logger.info("ARPAnalyzer initialized")
    
    def analyze_packet(self, src_mac: str, dst_mac: str, src_ip: str, 
                       dst_ip: str, opcode: int) -> ARPPacketInfo:
        """
        Analyze an ARP packet for anomalies.
        
        Args:
            src_mac: Source MAC address
            dst_mac: Destination MAC address
            src_ip: Source IP address (sender protocol address)
            dst_ip: Destination IP address (target protocol address)
            opcode: ARP opcode (1=request, 2=reply)
            
        Returns:
            ARPPacketInfo with analysis results
        """
        current_time = time.time()
        
        # Calculate inter-arrival time
        inter_arrival = 0.0
        if src_ip in self.last_packet_time:
            inter_arrival = current_time - self.last_packet_time[src_ip]
        
        self.last_packet_time[src_ip] = current_time
        
        # Create packet info
        packet_info = ARPPacketInfo(
            timestamp=current_time,
            src_mac=src_mac,
            dst_mac=dst_mac,
            src_ip=src_ip,
            dst_ip=dst_ip,
            opcode=opcode,
            inter_arrival_time=inter_arrival
        )
        
        # Detect gratuitous ARP
        packet_info.is_gratuitous = self._is_gratuitous_arp(
            src_ip, dst_ip, opcode, dst_mac
        )
        
        # Detect ARP probe
        packet_info.is_probe = self._is_arp_probe(src_ip, opcode)
        
        # Update statistics
        self._update_statistics(packet_info, opcode)
        
        # Store in history
        self.packet_history[src_ip].append(packet_info)
        
        # Track requests for reply matching
        if opcode == 1:  # Request
            self.pending_requests[(src_ip, dst_ip)] = current_time
        elif opcode == 2:  # Reply
            # Check if there was a matching request
            if (dst_ip, src_ip) not in self.pending_requests:
                self.stats["unmatched_replies"] += 1
            else:
                # Remove matched request
                del self.pending_requests[(dst_ip, src_ip)]
        
        return packet_info
    
    def _is_gratuitous_arp(self, src_ip: str, dst_ip: str, 
                           opcode: int, dst_mac: str) -> bool:
        """
        Detect gratuitous ARP packets.
        
        Gratuitous ARP characteristics:
        1. ARP reply (opcode=2) where sender IP == target IP
        2. OR ARP request (opcode=1) where sender IP == target IP
        3. Often sent to broadcast address (FF:FF:FF:FF:FF:FF)
        
        Args:
            src_ip: Source IP
            dst_ip: Destination IP
            opcode: ARP opcode
            dst_mac: Destination MAC
            
        Returns:
            True if packet is gratuitous ARP
        """
        # Check if sender IP == target IP
        if src_ip == dst_ip:
            return True
        
        # Additional check: ARP reply to broadcast
        if opcode == 2 and dst_mac.upper() == "FF:FF:FF:FF:FF:FF":
            return True
        
        return False
    
    def _is_arp_probe(self, src_ip: str, opcode: int) -> bool:
        """
        Detect ARP probe packets (used in IPv4 address conflict detection).
        
        ARP probe characteristics:
        - ARP request (opcode=1)
        - Sender IP address is 0.0.0.0
        
        Args:
            src_ip: Source IP address
            opcode: ARP opcode
            
        Returns:
            True if packet is ARP probe
        """
        return opcode == 1 and src_ip == "0.0.0.0"
    
    def _update_statistics(self, packet_info: ARPPacketInfo, opcode: int):
        """Update analyzer statistics."""
        self.stats["total_packets"] += 1
        
        if packet_info.is_gratuitous:
            self.stats["gratuitous_count"] += 1
        
        if packet_info.is_probe:
            self.stats["probe_count"] += 1
        
        if opcode == 1:
            self.stats["request_count"] += 1
        elif opcode == 2:
            self.stats["reply_count"] += 1
        
        # Update average inter-arrival time
        if packet_info.inter_arrival_time > 0:
            total = self.stats["total_packets"]
            avg = self.stats["avg_inter_arrival"]
            self.stats["avg_inter_arrival"] = (
                (avg * (total - 1) + packet_info.inter_arrival_time) / total
            )
    
    def get_timing_features(self, src_ip: str) -> Dict[str, float]:
        """
        Extract timing-based features for a source IP.
        
        Args:
            src_ip: Source IP address
            
        Returns:
            Dictionary of timing features
        """
        if src_ip not in self.packet_history:
            return {
                "min_inter_arrival": 0.0,
                "max_inter_arrival": 0.0,
                "avg_inter_arrival": 0.0,
                "std_inter_arrival": 0.0,
                "packet_rate": 0.0
            }
        
        packets = list(self.packet_history[src_ip])
        
        if len(packets) < 2:
            return {
                "min_inter_arrival": 0.0,
                "max_inter_arrival": 0.0,
                "avg_inter_arrival": 0.0,
                "std_inter_arrival": 0.0,
                "packet_rate": 0.0
            }
        
        # Extract inter-arrival times
        inter_arrivals = [p.inter_arrival_time for p in packets if p.inter_arrival_time > 0]
        
        if not inter_arrivals:
            return {
                "min_inter_arrival": 0.0,
                "max_inter_arrival": 0.0,
                "avg_inter_arrival": 0.0,
                "std_inter_arrival": 0.0,
                "packet_rate": 0.0
            }
        
        # Calculate statistics
        min_iat = min(inter_arrivals)
        max_iat = max(inter_arrivals)
        avg_iat = sum(inter_arrivals) / len(inter_arrivals)
        
        # Standard deviation
        variance = sum((x - avg_iat) ** 2 for x in inter_arrivals) / len(inter_arrivals)
        std_iat = variance ** 0.5
        
        # Packet rate (packets per second)
        time_span = packets[-1].timestamp - packets[0].timestamp
        packet_rate = len(packets) / time_span if time_span > 0 else 0.0
        
        return {
            "min_inter_arrival": min_iat,
            "max_inter_arrival": max_iat,
            "avg_inter_arrival": avg_iat,
            "std_inter_arrival": std_iat,
            "packet_rate": packet_rate
        }
    
    def detect_anomalies(self, packet_info: ARPPacketInfo) -> Dict[str, any]:
        """
        Detect anomalies in ARP packet.
        
        Args:
            packet_info: Packet information
            
        Returns:
            Dictionary with anomaly detection results
        """
        result = {
            "has_anomaly": False,
            "anomalies": [],
            "severity": 0.0,  # 0.0 to 1.0
            "features": {}
        }
        
        # Check for gratuitous ARP (suspicious activity)
        if packet_info.is_gratuitous:
            result["anomalies"].append("Gratuitous ARP detected")
            result["severity"] += 0.4
        
        # Check for ARP probe (usually benign but worth noting)
        if packet_info.is_probe:
            result["anomalies"].append("ARP probe detected")
            result["severity"] += 0.1
        
        # Check for rapid packet rate (potential ARP storm/attack)
        timing_features = self.get_timing_features(packet_info.src_ip)
        result["features"] = timing_features
        
        if timing_features["packet_rate"] > 10.0:  # More than 10 packets/second
            result["anomalies"].append(f"High packet rate: {timing_features['packet_rate']:.2f} pkt/s")
            result["severity"] += 0.3
        
        # Check for very fast inter-arrival times (< 100ms)
        if packet_info.inter_arrival_time > 0 and packet_info.inter_arrival_time < 0.1:
            result["anomalies"].append(f"Rapid packets: {packet_info.inter_arrival_time*1000:.1f}ms interval")
            result["severity"] += 0.2
        
        # Check for unsolicited replies
        if packet_info.opcode == 2:  # Reply
            key = (packet_info.dst_ip, packet_info.src_ip)
            if key not in self.pending_requests:
                result["anomalies"].append("Unsolicited ARP reply (no matching request)")
                result["severity"] += 0.5
        
        # Cap severity at 1.0
        result["severity"] = min(result["severity"], 1.0)
        
        # Set anomaly flag
        if len(result["anomalies"]) > 0:
            result["has_anomaly"] = True
        
        return result
    
    def get_statistics(self) -> Dict[str, any]:
        """
        Get analyzer statistics.
        
        Returns:
            Statistics dictionary
        """
        stats = self.stats.copy()
        stats.update({
            "tracked_ips": len(self.packet_history),
            "pending_requests": len(self.pending_requests),
            "gratuitous_percentage": (
                self.stats["gratuitous_count"] / max(self.stats["total_packets"], 1) * 100
            ),
            "probe_percentage": (
                self.stats["probe_count"] / max(self.stats["total_packets"], 1) * 100
            )
        })
        return stats
    
    def cleanup_old_entries(self, max_age: int = 300):
        """
        Clean up old entries from pending requests.
        
        Args:
            max_age: Maximum age in seconds for pending requests
        """
        current_time = time.time()
        to_remove = []
        
        for key, timestamp in self.pending_requests.items():
            if current_time - timestamp > max_age:
                to_remove.append(key)
        
        for key in to_remove:
            del self.pending_requests[key]
        
        if to_remove:
            logger.debug(f"Cleaned up {len(to_remove)} old pending requests")


# Global instance
_arp_analyzer = None


def get_arp_analyzer() -> ARPAnalyzer:
    """Get singleton ARP analyzer instance."""
    global _arp_analyzer
    if _arp_analyzer is None:
        _arp_analyzer = ARPAnalyzer()
    return _arp_analyzer
