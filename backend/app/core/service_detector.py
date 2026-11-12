import socket
import asyncio
from typing import Dict, Optional
import logging
import re

logger = logging.getLogger(__name__)


class ServiceDetector:
    """Service and version detection for open ports"""
    
    # Common service signatures
    SERVICE_SIGNATURES = {
        21: {"name": "ftp", "probes": [b""]},
        22: {"name": "ssh", "probes": [b""]},
        23: {"name": "telnet", "probes": [b""]},
        25: {"name": "smtp", "probes": [b"EHLO test\r\n"]},
        53: {"name": "dns", "probes": []},
        80: {"name": "http", "probes": [b"GET / HTTP/1.0\r\n\r\n"]},
        110: {"name": "pop3", "probes": [b""]},
        143: {"name": "imap", "probes": [b""]},
        443: {"name": "https", "probes": []},
        445: {"name": "microsoft-ds", "probes": []},
        3306: {"name": "mysql", "probes": [b""]},
        3389: {"name": "ms-wbt-server", "probes": []},
        5432: {"name": "postgresql", "probes": [b""]},
        8080: {"name": "http-proxy", "probes": [b"GET / HTTP/1.0\r\n\r\n"]},
        8443: {"name": "https-alt", "probes": []},
    }
    
    # Version detection patterns
    VERSION_PATTERNS = {
        "ssh": [
            (r"SSH-([\d.]+)-OpenSSH_([\d.]+)", "OpenSSH", r"\2"),
            (r"SSH-([\d.]+)", "SSH", r"\1"),
        ],
        "http": [
            (r"Server: ([^\r\n]+)", "HTTP", r"\1"),
            (r"Apache/([\d.]+)", "Apache", r"\1"),
            (r"nginx/([\d.]+)", "nginx", r"\1"),
        ],
        "ftp": [
            (r"220[- ].*?FTP.*?([\d.]+)", "FTP", r"\1"),
            (r"220 ([^\r\n]+)", "FTP", r"\1"),
        ],
        "smtp": [
            (r"220[- ]([^\r\n]+)", "SMTP", r"\1"),
        ],
    }
    
    def __init__(self, timeout: float = 2.0):
        """
        Initialize service detector.
        
        Args:
            timeout: Socket timeout in seconds
        """
        self.timeout = timeout
    
    async def detect_service(
        self,
        host: str,
        port: int,
        protocol: str = "tcp"
    ) -> Dict[str, Optional[str]]:
        """
        Detect service and version on an open port.
        
        Args:
            host: Target host
            port: Target port
            protocol: Protocol (tcp or udp)
            
        Returns:
            Dictionary with service_name, service_product, service_version, banner
        """
        result = {
            "service_name": None,
            "service_product": None,
            "service_version": None,
            "banner": None,
        }
        
        # Get default service name for common ports
        if port in self.SERVICE_SIGNATURES:
            result["service_name"] = self.SERVICE_SIGNATURES[port]["name"]
        
        # Try to grab banner
        banner = await self._grab_banner(host, port, protocol)
        
        if banner:
            result["banner"] = banner
            
            # Try to detect version from banner
            service_info = self._parse_banner(banner, result["service_name"])
            result.update(service_info)
        
        return result
    
    async def _grab_banner(
        self,
        host: str,
        port: int,
        protocol: str = "tcp"
    ) -> Optional[str]:
        """
        Grab banner from service.
        
        Args:
            host: Target host
            port: Target port
            protocol: Protocol (tcp or udp)
            
        Returns:
            Banner string or None
        """
        try:
            if protocol.lower() == "tcp":
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            else:
                sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            
            sock.settimeout(self.timeout)
            sock.connect((host, port))
            
            # Send probe if available
            if port in self.SERVICE_SIGNATURES:
                probes = self.SERVICE_SIGNATURES[port]["probes"]
                if probes:
                    sock.send(probes[0])
            
            # Receive banner
            banner = sock.recv(1024)
            sock.close()
            
            return banner.decode('utf-8', errors='ignore').strip()
            
        except socket.timeout:
            logger.debug(f"Timeout grabbing banner from {host}:{port}")
            return None
        except Exception as e:
            logger.debug(f"Error grabbing banner from {host}:{port}: {e}")
            return None
    
    def _parse_banner(
        self,
        banner: str,
        service_name: Optional[str]
    ) -> Dict[str, Optional[str]]:
        """
        Parse banner to extract version information.
        
        Args:
            banner: Banner string
            service_name: Known service name
            
        Returns:
            Dictionary with service_product and service_version
        """
        result = {
            "service_product": None,
            "service_version": None,
        }
        
        if not service_name or service_name not in self.VERSION_PATTERNS:
            return result
        
        patterns = self.VERSION_PATTERNS[service_name]
        
        for pattern, product, version_group in patterns:
            match = re.search(pattern, banner, re.IGNORECASE)
            if match:
                result["service_product"] = product
                try:
                    result["service_version"] = match.expand(version_group)
                except:
                    pass
                break
        
        return result
