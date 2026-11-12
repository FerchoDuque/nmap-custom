import ipaddress
import asyncio
from typing import List, Dict, Tuple
import logging

logger = logging.getLogger(__name__)


class NetworkMapper:
    """Network topology discovery and mapping"""
    
    def __init__(self):
        """Initialize network mapper"""
        pass
    
    async def discover_hosts(self, target: str) -> List[str]:
        """
        Discover active hosts in network range.
        
        Args:
            target: IP address, CIDR range, or hostname
            
        Returns:
            List of active host IPs
        """
        hosts = self.parse_target(target)
        active_hosts = []
        
        # Ping sweep to find active hosts
        tasks = [self._ping_host(host) for host in hosts]
        results = await asyncio.gather(*tasks)
        
        for host, is_up in zip(hosts, results):
            if is_up:
                active_hosts.append(host)
        
        logger.info(f"Discovered {len(active_hosts)} active hosts out of {len(hosts)}")
        return active_hosts
    
    async def _ping_host(self, host: str, timeout: float = 0.1) -> bool:
        """
        Check if host is up using TCP ping.
        
        Args:
            host: Target host IP
            timeout: Timeout in seconds
            
        Returns:
            True if host is up, False otherwise
        """
        import socket
        
        # Try common ports for TCP ping
        # Reduced list and timeout for faster scanning
        common_ports = [80, 443, 22]
        
        for port in common_ports:
            try:
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.settimeout(timeout)
                result = sock.connect_ex((host, port))
                sock.close()
                
                if result == 0:
                    return True
                    
            except:
                continue
        
        return False
    
    @staticmethod
    def parse_target(target: str) -> List[str]:
        """
        Parse target string into list of IP addresses.
        
        Args:
            target: IP address, CIDR range, IP range, or hostname
            
        Returns:
            List of IP addresses to scan
        """
        hosts = []
        
        try:
            # Try to parse as CIDR notation
            if '/' in target:
                network = ipaddress.ip_network(target, strict=False)
                hosts = [str(ip) for ip in network.hosts()]
                
                # Limit to reasonable size for local networks
                if len(hosts) > 1024:
                    logger.warning(f"Large network range ({len(hosts)} hosts), limiting to first 1024")
                    hosts = hosts[:1024]
            
            # Try to parse as IP range (e.g., 192.168.1.1-192.168.1.254)
            elif '-' in target and '.' in target:
                parts = target.split('-')
                if len(parts) == 2:
                    start_ip = ipaddress.ip_address(parts[0].strip())
                    end_ip = ipaddress.ip_address(parts[1].strip())
                    
                    current = int(start_ip)
                    end = int(end_ip)
                    
                    while current <= end and len(hosts) < 1024:
                        hosts.append(str(ipaddress.ip_address(current)))
                        current += 1
            
            # Single IP or hostname
            else:
                # Try to resolve hostname
                import socket
                try:
                    ip = socket.gethostbyname(target)
                    hosts = [ip]
                except socket.gaierror:
                    # Try as direct IP
                    try:
                        ipaddress.ip_address(target)
                        hosts = [target]
                    except ValueError:
                        logger.error(f"Invalid target: {target}")
                        hosts = []
        
        except Exception as e:
            logger.error(f"Error parsing target {target}: {e}")
            hosts = []
        
        return hosts
    
    @staticmethod
    def get_network_info(ip: str) -> Dict[str, str]:
        """
        Get network information for an IP address.
        
        Args:
            ip: IP address
            
        Returns:
            Dictionary with network information
        """
        try:
            addr = ipaddress.ip_address(ip)
            
            return {
                "ip": str(addr),
                "version": f"IPv{addr.version}",
                "is_private": addr.is_private,
                "is_loopback": addr.is_loopback,
                "is_multicast": addr.is_multicast,
            }
        except Exception as e:
            logger.error(f"Error getting network info for {ip}: {e}")
            return {}
