"""
SIEM integration module for exporting alerts to external systems.
Supports Syslog (RFC 5424), CEF (Common Event Format), and JSON formats.
"""
from __future__ import annotations

import json
import socket
from datetime import datetime
from typing import Optional, Dict, Any, List
from enum import Enum
from config.logger_config import setup_logger

logger = setup_logger("SIEMExporter")


class SyslogSeverity(int, Enum):
    """Syslog severity levels (RFC 5424)."""
    EMERGENCY = 0
    ALERT = 1
    CRITICAL = 2
    ERROR = 3
    WARNING = 4
    NOTICE = 5
    INFORMATIONAL = 6
    DEBUG = 7


class SyslogFacility(int, Enum):
    """Syslog facility codes."""
    KERNEL = 0
    USER = 1
    MAIL = 2
    DAEMON = 3
    AUTH = 4
    SYSLOG = 5
    LPR = 6
    NEWS = 7
    UUCP = 8
    CRON = 9
    AUTHPRIV = 10
    FTP = 11
    LOCAL0 = 16
    LOCAL1 = 17
    LOCAL2 = 18
    LOCAL3 = 19
    LOCAL4 = 20
    LOCAL5 = 21
    LOCAL6 = 22
    LOCAL7 = 23


class ExportFormat(str, Enum):
    """Supported export formats."""
    SYSLOG = "syslog"
    CEF = "cef"
    JSON = "json"
    JSONL = "jsonl"


class SyslogExporter:
    """Export alerts to Syslog."""
    
    def __init__(
        self,
        host: str = "localhost",
        port: int = 514,
        protocol: str = "udp",
        facility: SyslogFacility = SyslogFacility.LOCAL0,
        severity: SyslogSeverity = SyslogSeverity.WARNING
    ):
        self.host = host
        self.port = port
        self.protocol = protocol.lower()
        self.facility = facility
        self.severity = severity
        self.hostname = socket.gethostname()
    
    def _calculate_priority(self) -> int:
        """Calculate syslog priority value."""
        return (self.facility.value * 8) + self.severity.value
    
    def format_message(self, alert: Dict[str, Any]) -> str:
        """Format alert as RFC 5424 syslog message."""
        priority = self._calculate_priority()
        version = 1
        timestamp = alert.get('timestamp', datetime.now().isoformat())
        app_name = "SafeLink"
        proc_id = "-"
        msg_id = alert.get('module', 'ALERT')
        
        # Structured data
        structured_data = f"[alert id=\"{alert.get('id', '-')}\" " \
                         f"src_ip=\"{alert.get('src_ip', '-')}\" " \
                         f"src_mac=\"{alert.get('src_mac', '-')}\" " \
                         f"module=\"{alert.get('module', '-')}\"]"
        
        # Message
        message = alert.get('reason', 'ARP spoofing detected')
        
        # RFC 5424 format
        syslog_msg = f"<{priority}>{version} {timestamp} {self.hostname} " \
                    f"{app_name} {proc_id} {msg_id} {structured_data} {message}"
        
        return syslog_msg
    
    def send(self, alert: Dict[str, Any]) -> bool:
        """Send alert to syslog server."""
        try:
            message = self.format_message(alert)
            
            if self.protocol == "udp":
                sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                sock.sendto(message.encode('utf-8'), (self.host, self.port))
                sock.close()
            elif self.protocol == "tcp":
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.connect((self.host, self.port))
                sock.send((message + '\n').encode('utf-8'))
                sock.close()
            else:
                raise ValueError(f"Unsupported protocol: {self.protocol}")
            
            logger.debug(f"Sent syslog message to {self.host}:{self.port}")
            return True
        except Exception as e:
            logger.error(f"Error sending syslog message: {e}")
            return False


class CEFExporter:
    """Export alerts in Common Event Format (CEF)."""
    
    def __init__(
        self,
        host: str = "localhost",
        port: int = 514,
        protocol: str = "udp",
        device_vendor: str = "SafeLink",
        device_product: str = "Network Defense",
        device_version: str = "1.0"
    ):
        self.host = host
        self.port = port
        self.protocol = protocol.lower()
        self.device_vendor = device_vendor
        self.device_product = device_product
        self.device_version = device_version
    
    def format_message(self, alert: Dict[str, Any]) -> str:
        """Format alert as CEF message."""
        # CEF Header
        cef_version = 0
        signature_id = alert.get('id', '0')
        name = alert.get('module', 'ARP Spoofing')
        severity = self._map_severity(alert.get('module', ''))
        
        # CEF Extension (key-value pairs)
        extensions = {
            'src': alert.get('src_ip', ''),
            'smac': alert.get('src_mac', ''),
            'msg': alert.get('reason', ''),
            'rt': alert.get('timestamp', datetime.now().isoformat()),
            'cat': 'Network Security',
            'act': 'detected',
        }
        
        extension_str = ' '.join([f"{k}={v}" for k, v in extensions.items() if v])
        
        # CEF format: CEF:Version|Device Vendor|Device Product|Device Version|Signature ID|Name|Severity|Extension
        cef_msg = f"CEF:{cef_version}|{self.device_vendor}|{self.device_product}|" \
                 f"{self.device_version}|{signature_id}|{name}|{severity}|{extension_str}"
        
        return cef_msg
    
    def _map_severity(self, module: str) -> int:
        """Map alert module to CEF severity (0-10)."""
        severity_map = {
            'ANN': 8,
            'DFA': 7,
            'HYBRID': 9,
        }
        return severity_map.get(module, 5)
    
    def send(self, alert: Dict[str, Any]) -> bool:
        """Send alert in CEF format."""
        try:
            message = self.format_message(alert)
            
            if self.protocol == "udp":
                sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                sock.sendto(message.encode('utf-8'), (self.host, self.port))
                sock.close()
            elif self.protocol == "tcp":
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.connect((self.host, self.port))
                sock.send((message + '\n').encode('utf-8'))
                sock.close()
            else:
                raise ValueError(f"Unsupported protocol: {self.protocol}")
            
            logger.debug(f"Sent CEF message to {self.host}:{self.port}")
            return True
        except Exception as e:
            logger.error(f"Error sending CEF message: {e}")
            return False


class JSONExporter:
    """Export alerts in JSON/JSONL format to file or network."""
    
    def __init__(
        self,
        output_path: Optional[str] = None,
        host: Optional[str] = None,
        port: Optional[int] = None,
        jsonl: bool = True
    ):
        self.output_path = output_path
        self.host = host
        self.port = port
        self.jsonl = jsonl
    
    def format_message(self, alert: Dict[str, Any]) -> str:
        """Format alert as JSON."""
        # Enhance alert data for SIEM
        enhanced = {
            'event_type': 'security_alert',
            'product': 'SafeLink',
            'version': '1.0',
            'timestamp': alert.get('timestamp', datetime.now().isoformat()),
            'alert': alert
        }
        return json.dumps(enhanced)
    
    def send(self, alert: Dict[str, Any]) -> bool:
        """Export alert as JSON."""
        try:
            message = self.format_message(alert)
            
            # Write to file
            if self.output_path:
                with open(self.output_path, 'a') as f:
                    f.write(message + '\n')
                logger.debug(f"Wrote JSON alert to {self.output_path}")
            
            # Send over network
            if self.host and self.port:
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.connect((self.host, self.port))
                sock.send((message + '\n').encode('utf-8'))
                sock.close()
                logger.debug(f"Sent JSON alert to {self.host}:{self.port}")
            
            return True
        except Exception as e:
            logger.error(f"Error exporting JSON alert: {e}")
            return False


class SIEMIntegration:
    """Main SIEM integration service managing multiple exporters."""
    
    def __init__(self):
        self.exporters: List[Any] = []
        logger.info("SIEMIntegration initialized")
    
    def add_exporter(self, exporter):
        """Add an exporter to the integration."""
        self.exporters.append(exporter)
        logger.info(f"Added exporter: {exporter.__class__.__name__}")
    
    def add_syslog_exporter(
        self,
        host: str,
        port: int = 514,
        protocol: str = "udp"
    ):
        """Add a Syslog exporter."""
        exporter = SyslogExporter(host=host, port=port, protocol=protocol)
        self.add_exporter(exporter)
    
    def add_cef_exporter(
        self,
        host: str,
        port: int = 514,
        protocol: str = "udp"
    ):
        """Add a CEF exporter."""
        exporter = CEFExporter(host=host, port=port, protocol=protocol)
        self.add_exporter(exporter)
    
    def add_json_exporter(
        self,
        output_path: Optional[str] = None,
        host: Optional[str] = None,
        port: Optional[int] = None
    ):
        """Add a JSON exporter."""
        exporter = JSONExporter(output_path=output_path, host=host, port=port)
        self.add_exporter(exporter)
    
    def export_alert(self, alert: Dict[str, Any]) -> Dict[str, bool]:
        """Export alert to all configured exporters."""
        results = {}
        for exporter in self.exporters:
            exporter_name = exporter.__class__.__name__
            try:
                success = exporter.send(alert)
                results[exporter_name] = success
            except Exception as e:
                logger.error(f"Error in {exporter_name}: {e}")
                results[exporter_name] = False
        
        return results
    
    def export_batch(self, alerts: List[Dict[str, Any]]) -> int:
        """Export multiple alerts."""
        success_count = 0
        for alert in alerts:
            results = self.export_alert(alert)
            if any(results.values()):
                success_count += 1
        
        logger.info(f"Exported {success_count}/{len(alerts)} alerts")
        return success_count


# Global SIEM integration instance
siem_integration = SIEMIntegration()
