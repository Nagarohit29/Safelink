from scapy.all import sniff, ARP, AsyncSniffer

from core.dfa_filter import DFAFilter
from core.alert_system import AlertSystem
from core.mac_vendor import get_mac_vendor_checker
from core.arp_analyzer import get_arp_analyzer

def _handle_pkt(pkt, dfa, ann_detector, alert_system):
    try:
        # only ARP
        if not pkt.haslayer(ARP):
            return

        arp = pkt.getlayer(ARP)
        src_ip = getattr(arp, "psrc", None)
        dst_ip = getattr(arp, "pdst", None)
        src_mac = getattr(arp, "hwsrc", None)
        dst_mac = getattr(arp, "hwdst", None)
        opcode = getattr(arp, "op", 0)
        
        # Get analyzers
        mac_checker = get_mac_vendor_checker()
        arp_analyzer = get_arp_analyzer()
        
        # Analyze ARP packet for advanced features
        packet_info = arp_analyzer.analyze_packet(
            src_mac, dst_mac, src_ip, dst_ip, opcode
        )
        
        # Check for ARP anomalies
        arp_anomalies = arp_analyzer.detect_anomalies(packet_info)
        
        # Check MAC vendor consistency
        vendor_anomalies = mac_checker.detect_anomalies(
            src_mac, dst_mac, src_ip, dst_ip
        )
        
        # Enhanced details for alerts
        enhanced_details = {
            "opcode": opcode,
            "is_gratuitous": packet_info.is_gratuitous,
            "is_probe": packet_info.is_probe,
            "inter_arrival_time": packet_info.inter_arrival_time,
            "src_vendor": vendor_anomalies.get("src_vendor"),
            "dst_vendor": vendor_anomalies.get("dst_vendor"),
            "arp_anomaly_severity": arp_anomalies.get("severity", 0.0),
            "vendor_anomaly_confidence": vendor_anomalies.get("confidence", 0.0)
        }

        # DFA check (primary detection)
        is_bad, reason, details = dfa.check(pkt)
        if is_bad:
            ip = details.get("ip")
            mac = details.get("new_mac") or details.get("mac")
            # Merge enhanced details
            details.update(enhanced_details)
            alert_system.alert("DFA", reason, ip=ip, mac=mac, details=details)
            return

        # Check for high-severity ARP anomalies
        if arp_anomalies.get("has_anomaly") and arp_anomalies.get("severity", 0) > 0.5:
            reason = f"ARP anomaly: {', '.join(arp_anomalies['anomalies'])}"
            enhanced_details["arp_anomalies"] = arp_anomalies["anomalies"]
            alert_system.alert("ARP_ANOMALY", reason, ip=src_ip, mac=src_mac, details=enhanced_details)
            return

        # Check for vendor anomalies
        if vendor_anomalies.get("has_anomaly") and vendor_anomalies.get("confidence", 0) > 0.4:
            reason = f"MAC vendor anomaly: {', '.join(vendor_anomalies['anomalies'])}"
            enhanced_details["vendor_anomalies"] = vendor_anomalies["anomalies"]
            alert_system.alert("VENDOR_ANOMALY", reason, ip=src_ip, mac=src_mac, details=enhanced_details)
            return

        # Pass to ANN (secondary detection)
        predicted, prob = ann_detector.predict_from_scapy(pkt)
        if predicted == 1:
            # suspicious
            enhanced_details["ann_prob"] = prob
            alert_system.alert("ANN", f"Model predicted spoof (prob={prob:.4f})", ip=src_ip, mac=src_mac, details=enhanced_details)
    except Exception as e:
        print("Error handling packet:", e)

def _build_sniffer_args(interface, dfa_callback, ann_detector, alert_system):
    if ann_detector is None:
        raise ValueError("ANN detector instance required for packet processing")
    dfa = dfa_callback if dfa_callback is not None else DFAFilter()
    alert_system = alert_system or AlertSystem()

    def handler(pkt):
        _handle_pkt(pkt, dfa, ann_detector, alert_system)

    return {
        "filter": "arp",
        "prn": handler,
        "store": False,
        "iface": interface,
    }


def start_sniffer(interface=None, dfa_callback=None, ann_detector=None, alert_system=None):
    """
    interface: network interface name string; None -> defaults
    dfa_callback: optional custom DFAFilter instance
    ann_detector: ANNDetector instance
    alert_system: AlertSystem instance
    """
    print("Starting ARP sniffer on interface:", interface)
    sniff(**_build_sniffer_args(interface, dfa_callback, ann_detector, alert_system))


def create_async_sniffer(interface=None, dfa_callback=None, ann_detector=None, alert_system=None):
    """Return an AsyncSniffer configured with SafeLink's packet handler."""
    return AsyncSniffer(**_build_sniffer_args(interface, dfa_callback, ann_detector, alert_system))
