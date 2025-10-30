"""
Threat intelligence integration module.
Provides IP/MAC reputation lookups and enrichment from external sources.
"""
from __future__ import annotations

import aiohttp
import asyncio
from typing import Optional, Dict, Any
from datetime import datetime, timedelta
from functools import lru_cache
from config.logger_config import setup_logger

logger = setup_logger("ThreatIntel")


class ThreatIntelCache:
    """Simple in-memory cache for threat intelligence lookups."""
    
    def __init__(self, ttl_seconds: int = 3600):
        self.cache: Dict[str, Dict[str, Any]] = {}
        self.ttl = ttl_seconds
    
    def get(self, key: str) -> Optional[Dict[str, Any]]:
        """Get cached value if not expired."""
        if key in self.cache:
            entry = self.cache[key]
            if datetime.now() < entry['expires']:
                return entry['data']
            else:
                del self.cache[key]
        return None
    
    def set(self, key: str, value: Dict[str, Any]):
        """Set cached value with expiration."""
        self.cache[key] = {
            'data': value,
            'expires': datetime.now() + timedelta(seconds=self.ttl)
        }
    
    def clear(self):
        """Clear the cache."""
        self.cache.clear()


class AbuseIPDBClient:
    """Client for AbuseIPDB API."""
    
    BASE_URL = "https://api.abuseipdb.com/api/v2"
    
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key
        self.cache = ThreatIntelCache()
        self.enabled = bool(api_key)
    
    async def check_ip(self, ip: str) -> Optional[Dict[str, Any]]:
        """Check IP reputation on AbuseIPDB."""
        if not self.enabled:
            logger.debug("AbuseIPDB API key not configured, skipping lookup")
            return None
        
        # Check cache first
        cached = self.cache.get(f"abuseipdb:{ip}")
        if cached:
            logger.debug(f"AbuseIPDB cache hit for {ip}")
            return cached
        
        try:
            url = f"{self.BASE_URL}/check"
            headers = {
                'Key': self.api_key,
                'Accept': 'application/json'
            }
            params = {
                'ipAddress': ip,
                'maxAgeInDays': 90,
                'verbose': ''
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.get(url, headers=headers, params=params, timeout=5) as response:
                    if response.status == 200:
                        data = await response.json()
                        result = {
                            'source': 'AbuseIPDB',
                            'ip': ip,
                            'abuse_confidence_score': data.get('data', {}).get('abuseConfidenceScore', 0),
                            'is_whitelisted': data.get('data', {}).get('isWhitelisted', False),
                            'total_reports': data.get('data', {}).get('totalReports', 0),
                            'country_code': data.get('data', {}).get('countryCode'),
                            'usage_type': data.get('data', {}).get('usageType'),
                            'isp': data.get('data', {}).get('isp'),
                            'last_reported': data.get('data', {}).get('lastReportedAt')
                        }
                        self.cache.set(f"abuseipdb:{ip}", result)
                        logger.info(f"AbuseIPDB lookup for {ip}: score={result['abuse_confidence_score']}")
                        return result
                    else:
                        logger.warning(f"AbuseIPDB API error: {response.status}")
                        return None
        except asyncio.TimeoutError:
            logger.warning(f"AbuseIPDB lookup timeout for {ip}")
            return None
        except Exception as e:
            logger.error(f"AbuseIPDB lookup error for {ip}: {e}")
            return None


class MACVendorLookup:
    """MAC address vendor lookup service."""
    
    # Using macvendors.com API (free, no key required)
    API_URL = "https://api.macvendors.com"
    
    def __init__(self):
        self.cache = ThreatIntelCache(ttl_seconds=86400)  # 24 hour cache
    
    async def lookup(self, mac: str) -> Optional[Dict[str, Any]]:
        """Lookup MAC vendor information."""
        # Normalize MAC address
        mac_normalized = mac.replace(':', '').replace('-', '').upper()
        
        # Check cache
        cached = self.cache.get(f"mac:{mac_normalized}")
        if cached:
            return cached
        
        try:
            url = f"{self.API_URL}/{mac}"
            
            async with aiohttp.ClientSession() as session:
                async with session.get(url, timeout=5) as response:
                    if response.status == 200:
                        vendor = await response.text()
                        result = {
                            'source': 'MACVendors',
                            'mac': mac,
                            'vendor': vendor.strip(),
                            'oui': mac_normalized[:6]
                        }
                        self.cache.set(f"mac:{mac_normalized}", result)
                        logger.info(f"MAC vendor lookup for {mac}: {vendor}")
                        return result
                    elif response.status == 404:
                        logger.debug(f"MAC vendor not found for {mac}")
                        return {'source': 'MACVendors', 'mac': mac, 'vendor': 'Unknown', 'oui': mac_normalized[:6]}
                    else:
                        logger.warning(f"MAC vendor lookup error: {response.status}")
                        return None
        except asyncio.TimeoutError:
            logger.warning(f"MAC vendor lookup timeout for {mac}")
            return None
        except Exception as e:
            logger.error(f"MAC vendor lookup error for {mac}: {e}")
            return None


class ThreatIntelService:
    """Main threat intelligence service coordinating multiple sources."""
    
    def __init__(self, abuseipdb_key: Optional[str] = None):
        self.abuseipdb = AbuseIPDBClient(api_key=abuseipdb_key)
        self.mac_vendor = MACVendorLookup()
        logger.info("ThreatIntelService initialized")
    
    async def enrich_alert(
        self, 
        ip: Optional[str] = None, 
        mac: Optional[str] = None
    ) -> Dict[str, Any]:
        """Enrich alert data with threat intelligence."""
        enrichment = {
            'ip_reputation': None,
            'mac_vendor': None,
            'risk_score': 0,
            'enriched_at': datetime.now().isoformat()
        }
        
        tasks = []
        
        # IP reputation lookup
        if ip:
            tasks.append(self.abuseipdb.check_ip(ip))
        else:
            tasks.append(asyncio.sleep(0))  # Placeholder
        
        # MAC vendor lookup
        if mac:
            tasks.append(self.mac_vendor.lookup(mac))
        else:
            tasks.append(asyncio.sleep(0))  # Placeholder
        
        try:
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            if ip and isinstance(results[0], dict):
                enrichment['ip_reputation'] = results[0]
                # Calculate risk score based on abuse confidence
                abuse_score = results[0].get('abuse_confidence_score', 0)
                enrichment['risk_score'] = max(enrichment['risk_score'], abuse_score)
            
            if mac and isinstance(results[1], dict):
                enrichment['mac_vendor'] = results[1]
        
        except Exception as e:
            logger.error(f"Error enriching alert: {e}")
        
        return enrichment
    
    async def bulk_enrich(self, targets: list) -> Dict[str, Any]:
        """Enrich multiple targets in bulk."""
        results = {}
        tasks = []
        
        for target in targets:
            ip = target.get('ip')
            mac = target.get('mac')
            task_id = f"{ip or ''}_{mac or ''}"
            tasks.append((task_id, self.enrich_alert(ip, mac)))
        
        enriched = await asyncio.gather(*[task for _, task in tasks])
        
        for (task_id, _), result in zip(tasks, enriched):
            results[task_id] = result
        
        return results
    
    def get_risk_level(self, risk_score: int) -> str:
        """Convert risk score to risk level."""
        if risk_score >= 75:
            return "CRITICAL"
        elif risk_score >= 50:
            return "HIGH"
        elif risk_score >= 25:
            return "MEDIUM"
        else:
            return "LOW"


# Singleton instance (can be initialized with API key from settings)
threat_intel_service = ThreatIntelService()
