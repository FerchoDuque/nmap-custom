import socket
import asyncio
from typing import List, Dict, Tuple, Optional, Callable
from app.models.scan import PortState
import logging

logger = logging.getLogger(__name__)


class PortScanner:
    """Port scanner with multiple scan techniques"""
    
    def __init__(self, timeout: float = 1.0):
        """
        Initialize port scanner.
        
        Args:
            timeout: Socket timeout in seconds
        """
        self.timeout = timeout
    
    async def tcp_connect_scan(
        self,
        host: str,
        ports: List[int],
        progress_callback: Optional[Callable] = None
    ) -> Dict[int, PortState]:
        """
        Perform TCP connect scan on specified ports.
        
        Args:
            host: Target host IP or hostname
            ports: List of ports to scan
            progress_callback: Optional callback for progress updates
            
        Returns:
            Dictionary mapping port numbers to their states
        """
        results = {}
        total_ports = len(ports)
        
        for idx, port in enumerate(ports):
            try:
                # Create socket connection
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.settimeout(self.timeout)
                
                # Attempt connection
                result = sock.connect_ex((host, port))
                
                if result == 0:
                    results[port] = PortState.OPEN
                else:
                    results[port] = PortState.CLOSED
                
                sock.close()
                
            except socket.timeout:
                results[port] = PortState.FILTERED
            except socket.error:
                results[port] = PortState.FILTERED
            except Exception as e:
                logger.error(f"Error scanning port {port} on {host}: {e}")
                results[port] = PortState.UNKNOWN
            
            # Progress callback
            if progress_callback and (idx + 1) % 10 == 0:
                await progress_callback(idx + 1, total_ports)
            
            # Small delay to avoid overwhelming the network
            await asyncio.sleep(0.01)
        
        return results
    
    async def tcp_syn_scan(
        self,
        host: str,
        ports: List[int],
        progress_callback: Optional[Callable] = None
    ) -> Dict[int, PortState]:
        """
        Perform TCP SYN scan (stealth scan) using scapy.
        Requires root/administrator privileges.
        
        Args:
            host: Target host IP or hostname
            ports: List of ports to scan
            progress_callback: Optional callback for progress updates
            
        Returns:
            Dictionary mapping port numbers to their states
        """
        try:
            from scapy.all import IP, TCP, sr1, conf
            conf.verb = 0  # Suppress scapy output
        except ImportError:
            logger.error("Scapy not available for SYN scan")
            # Fallback to TCP connect scan
            return await self.tcp_connect_scan(host, ports, progress_callback)
        except PermissionError:
            logger.warning("Insufficient privileges for SYN scan, falling back to TCP connect")
            return await self.tcp_connect_scan(host, ports, progress_callback)
        
        results = {}
        total_ports = len(ports)
        
        for idx, port in enumerate(ports):
            try:
                # Create SYN packet
                syn_packet = IP(dst=host)/TCP(dport=port, flags="S")
                
                # Send packet and wait for response
                response = sr1(syn_packet, timeout=self.timeout, verbose=0)
                
                if response is None:
                    results[port] = PortState.FILTERED
                elif response.haslayer(TCP):
                    if response[TCP].flags == 0x12:  # SYN-ACK
                        results[port] = PortState.OPEN
                        # Send RST to close connection
                        rst_packet = IP(dst=host)/TCP(dport=port, flags="R")
                        sr1(rst_packet, timeout=0.1, verbose=0)
                    elif response[TCP].flags == 0x14:  # RST-ACK
                        results[port] = PortState.CLOSED
                    else:
                        results[port] = PortState.UNKNOWN
                else:
                    results[port] = PortState.UNKNOWN
                    
            except Exception as e:
                logger.error(f"Error in SYN scan for port {port} on {host}: {e}")
                results[port] = PortState.UNKNOWN
            
            # Progress callback
            if progress_callback and (idx + 1) % 10 == 0:
                await progress_callback(idx + 1, total_ports)
            
            await asyncio.sleep(0.01)
        
        return results
    
    async def udp_scan(
        self,
        host: str,
        ports: List[int],
        progress_callback: Optional[Callable] = None
    ) -> Dict[int, PortState]:
        """
        Perform UDP port scan.
        
        Args:
            host: Target host IP or hostname
            ports: List of ports to scan
            progress_callback: Optional callback for progress updates
            
        Returns:
            Dictionary mapping port numbers to their states
        """
        results = {}
        total_ports = len(ports)
        
        for idx, port in enumerate(ports):
            try:
                sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                sock.settimeout(self.timeout)
                
                # Send empty UDP packet
                sock.sendto(b'', (host, port))
                
                try:
                    # Try to receive response
                    data, addr = sock.recvfrom(1024)
                    results[port] = PortState.OPEN
                except socket.timeout:
                    # No response could mean open or filtered
                    results[port] = PortState.OPEN  # Assume open
                except socket.error:
                    results[port] = PortState.CLOSED
                
                sock.close()
                
            except Exception as e:
                logger.error(f"Error in UDP scan for port {port} on {host}: {e}")
                results[port] = PortState.UNKNOWN
            
            # Progress callback
            if progress_callback and (idx + 1) % 10 == 0:
                await progress_callback(idx + 1, total_ports)
            
            await asyncio.sleep(0.01)
        
        return results
    
    @staticmethod
    def parse_port_range(port_range: Optional[str]) -> List[int]:
        """
        Parse port range string into list of ports.
        
        Args:
            port_range: Port range string (e.g., "1-1000,8080,8443")
            
        Returns:
            List of port numbers
        """
        if not port_range:
            # Default common ports
            return [21, 22, 23, 25, 53, 80, 110, 143, 443, 445, 3306, 3389, 5432, 8080, 8443]
        
        ports = set()
        
        for part in port_range.split(','):
            part = part.strip()
            
            if '-' in part:
                # Range of ports
                try:
                    start, end = part.split('-')
                    start, end = int(start.strip()), int(end.strip())
                    
                    if start < 1 or end > 65535 or start > end:
                        logger.warning(f"Invalid port range: {part}")
                        continue
                    
                    ports.update(range(start, end + 1))
                except ValueError:
                    logger.warning(f"Invalid port range format: {part}")
            else:
                # Single port
                try:
                    port = int(part)
                    if 1 <= port <= 65535:
                        ports.add(port)
                    else:
                        logger.warning(f"Port out of range: {port}")
                except ValueError:
                    logger.warning(f"Invalid port number: {part}")
        
        return sorted(list(ports))
