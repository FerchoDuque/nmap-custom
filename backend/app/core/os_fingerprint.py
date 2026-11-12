from typing import Dict, Optional
import logging
import platform

logger = logging.getLogger(__name__)


class OSFingerprinter:
    """Operating system detection and fingerprinting"""
    
    def __init__(self):
        """Initialize OS fingerprinter"""
        self.nmap_available = self._check_nmap_available()
    
    def _check_nmap_available(self) -> bool:
        """Check if nmap is available"""
        try:
            import nmap
            return True
        except ImportError:
            logger.warning("python-nmap not available, OS detection will be limited")
            return False
    
    async def detect_os(
        self,
        host: str,
        open_ports: list = None
    ) -> Dict[str, any]:
        """
        Detect operating system of target host.
        
        Args:
            host: Target host IP
            open_ports: List of known open ports (helps with detection)
            
        Returns:
            Dictionary with os_name, os_accuracy, os_details
        """
        result = {
            "os_name": None,
            "os_accuracy": 0,
            "os_details": {},
        }
        
        if self.nmap_available:
            result = await self._nmap_os_detection(host)
        else:
            result = await self._basic_os_detection(host, open_ports)
        
        return result
    
    async def _nmap_os_detection(self, host: str) -> Dict[str, any]:
        """
        Use nmap for OS detection.
        
        Args:
            host: Target host
            
        Returns:
            OS detection results
        """
        try:
            import nmap
            
            nm = nmap.PortScanner()
            
            # Run OS detection scan
            # Note: This requires root/admin privileges
            nm.scan(host, arguments='-O')
            
            if host in nm.all_hosts():
                if 'osmatch' in nm[host]:
                    osmatch = nm[host]['osmatch']
                    if osmatch:
                        best_match = osmatch[0]
                        return {
                            "os_name": best_match.get('name'),
                            "os_accuracy": int(best_match.get('accuracy', 0)),
                            "os_details": {
                                "matches": osmatch[:3],  # Top 3 matches
                            }
                        }
            
        except PermissionError:
            logger.warning("Insufficient privileges for nmap OS detection")
        except Exception as e:
            logger.error(f"Error in nmap OS detection: {e}")
        
        return {
            "os_name": None,
            "os_accuracy": 0,
            "os_details": {},
        }
    
    async def _basic_os_detection(
        self,
        host: str,
        open_ports: list = None
    ) -> Dict[str, any]:
        """
        Basic OS detection using heuristics.
        
        Args:
            host: Target host
            open_ports: List of open ports
            
        Returns:
            OS detection results
        """
        # Simple heuristics based on common port combinations
        if not open_ports:
            return {
                "os_name": "Unknown",
                "os_accuracy": 0,
                "os_details": {},
            }
        
        os_hints = []
        
        # Windows indicators
        if 445 in open_ports or 3389 in open_ports or 135 in open_ports:
            os_hints.append(("Windows", 60))
        
        # Linux indicators
        if 22 in open_ports:
            os_hints.append(("Linux", 40))
        
        # Web server indicators
        if 80 in open_ports or 443 in open_ports:
            os_hints.append(("Web Server", 30))
        
        # Database indicators
        if 3306 in open_ports:
            os_hints.append(("MySQL Server", 30))
        if 5432 in open_ports:
            os_hints.append(("PostgreSQL Server", 30))
        
        if os_hints:
            # Return the hint with highest confidence
            os_hints.sort(key=lambda x: x[1], reverse=True)
            return {
                "os_name": os_hints[0][0],
                "os_accuracy": os_hints[0][1],
                "os_details": {
                    "method": "heuristic",
                    "hints": os_hints,
                }
            }
        
        return {
            "os_name": "Unknown",
            "os_accuracy": 0,
            "os_details": {},
        }
