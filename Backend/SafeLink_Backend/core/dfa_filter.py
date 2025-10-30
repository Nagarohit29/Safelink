import time
from collections import defaultdict, deque

class DFAFilter:
    def __init__(self, gratuitous_threshold=5, grat_window=5.0):
        # maps ip -> mac
        self.ip_mac = {}
        # track gratuitous counts: src -> deque(timestamps)
        self.grat_counts = defaultdict(deque)
        self.grat_threshold = gratuitous_threshold
        self.grat_window = grat_window

    def check(self, pkt):
        """
        Returns (is_suspicious:bool, reason:str, details:dict)
        Expects scapy ARP packet or object with .psrc and .hwsrc and .op fields.
        """
        now = time.time()
        try:
            # ARP layer expected
            arp = pkt.getlayer("ARP")
            src_ip = getattr(arp, "psrc", None)
            src_mac = getattr(arp, "hwsrc", None)
            op = int(getattr(arp, "op", 0))
        except Exception:
            return False, "non-arp", {}

        # Rule 1: IP-MAC mapping conflict
        if src_ip in self.ip_mac:
            if self.ip_mac[src_ip] != src_mac:
                prev_mac = self.ip_mac[src_ip]
                reason = f"IP-MAC conflict: {src_ip} previous {prev_mac} now {src_mac}"
                self.ip_mac[src_ip] = src_mac
                return True, reason, {"ip": src_ip, "prev_mac": prev_mac, "new_mac": src_mac}

        else:
            # if new mapping, store it
            self.ip_mac[src_ip] = src_mac

        # Rule 2: gratuitous ARP detection (ARP reply with same sender/target?)
        # For detection, count ARP packets from same source in short time window
        dq = self.grat_counts[src_mac]
        dq.append(now)
        # pop old timestamps
        while dq and (now - dq[0] > self.grat_window):
            dq.popleft()
        if len(dq) > self.grat_threshold:
            return True, f"Excessive gratuitous ARPs from {src_mac} ({len(dq)} in {self.grat_window}s)", {"mac": src_mac, "count": len(dq)}

        # Rule 3: unauthorized ARP reply -- we track recent outgoing requests (this is best-effort)
        # This backend is not integrated into system ARP request tracking; skip or return False
        # For now, we skip this check.
        return False, "ok", {}
