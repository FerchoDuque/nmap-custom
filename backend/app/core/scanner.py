import asyncio
import socket
from typing import Dict, List, Optional, Callable, Tuple
from datetime import datetime
import logging

from app.config import settings
from app.core.port_scanner import PortScanner
from app.core.service_detector import ServiceDetector
from app.core.os_fingerprint import OSFingerprinter
from app.core.network_mapper import NetworkMapper
from app.models.scan import ScanType, PortState

logger = logging.getLogger(__name__)

# Common UDP ports used for comprehensive scans when no explicit UDP range is provided
DEFAULT_UDP_PORTS = [53, 67, 68, 69, 123, 135, 137, 138, 139, 161, 162, 445, 500, 514, 520, 1900, 4500]


class NetworkScanner:
    """Main network scanner orchestrator"""

    def __init__(self, resolve_hostnames: Optional[bool] = None):
        """Initialize network scanner with all components."""
        self.resolve_hostnames = (
            settings.resolve_hostnames
            if resolve_hostnames is None
            else resolve_hostnames
        )
        self.port_scanner = PortScanner(timeout=1.0)
        self.service_detector = ServiceDetector(timeout=2.0)
        self.os_fingerprinter = OSFingerprinter()
        self.network_mapper = NetworkMapper()

    def _resolve_hostname(self, host: str) -> Optional[str]:
        """Best-effort reverse DNS that never raises and can be disabled."""
        if not self.resolve_hostnames:
            return None
        try:
            return socket.gethostbyaddr(host)[0]
        except (OSError, UnicodeError):
            return None
    
    async def scan(
        self,
        target: str,
        scan_type: ScanType,
        port_range: Optional[str] = None,
        service_detection: bool = True,
        os_detection: bool = False,
        progress_callback: Optional[Callable] = None
    ) -> Dict:
        """
        Perform network scan.
        
        Args:
            target: Target IP, CIDR, or hostname
            scan_type: Type of scan to perform
            port_range: Port range string
            service_detection: Enable service detection
            os_detection: Enable OS detection
            progress_callback: Callback for progress updates
            
        Returns:
            Dictionary with scan results
        """
        logger.info(f"Starting {scan_type} scan on {target}")
        
        # Parse target into list of hosts
        hosts = self.network_mapper.parse_target(target)
        
        if not hosts:
            raise ValueError(f"No valid hosts found in target: {target}")
        
        # Discover active hosts
        if progress_callback:
            await progress_callback({
                "status": "discovering",
                "message": f"Discovering hosts in {target}...",
                "progress": 5
            })
        
        active_hosts = await self.network_mapper.discover_hosts(target)
        
        if not active_hosts:
            logger.warning(f"No active hosts found in {target}")
            return {
                "hosts_total": len(hosts),
                "hosts_up": 0,
                "hosts_failed": 0,
                "total_ports_found": 0,
                "results": []
            }
        
        logger.info(f"Found {len(active_hosts)} active hosts")
        
        # Parse port range
        ports = self.port_scanner.parse_port_range(port_range)
        
        # Scan each host
        results = []
        total_ports_found = 0
        hosts_failed = 0
        
        host_step = 80.0 / len(active_hosts)
        
        for idx, host in enumerate(active_hosts):
            base_progress = 10 + int(idx * host_step)
            
            if progress_callback:
                await progress_callback({
                    "status": "scanning",
                    "message": f"Scanning {host}...",
                    "current_host": host,
                    "hosts_scanned": idx,
                    "hosts_total": len(active_hosts),
                    "progress": base_progress
                })
            
            # One failing host must not abort the rest of the scan.
            try:
                host_result = await self._scan_host(
                    host,
                    scan_type,
                    ports,
                    service_detection,
                    os_detection,
                    progress_callback,
                    base_progress,
                    host_step
                )
            except Exception as exc:  # noqa: BLE001 - isolate per-host failures
                hosts_failed += 1
                logger.warning("Host scan failed for %s: %s", host, exc)
                continue
            
            results.append(host_result)
            total_ports_found += len(host_result.get("ports", []))
        
        if progress_callback:
            await progress_callback({
                "status": "completed",
                "message": "Scan completed",
                "progress": 100
            })
        
        return {
            "hosts_total": len(hosts),
            "hosts_up": len(active_hosts),
            "hosts_failed": hosts_failed,
            "total_ports_found": total_ports_found,
            "results": results
        }
    
    async def _scan_host(
        self,
        host: str,
        scan_type: ScanType,
        ports: List[int],
        service_detection: bool,
        os_detection: bool,
        progress_callback: Optional[Callable] = None,
        base_progress: int = 0,
        progress_step: float = 0
    ) -> Dict:
        """
        Scan a single host.
        
        Args:
            host: Target host IP
            scan_type: Type of scan
            ports: List of ports to scan
            service_detection: Enable service detection
            os_detection: Enable OS detection
            
        Returns:
            Host scan results
        """
        result = {
            "ip_address": host,
            "hostname": None,
            "is_up": True,
            "ports": [],
            "os_name": None,
            "os_accuracy": None,
            "os_details": None,
        }
        
        # Try to resolve hostname (best effort, bounded by the scan timeout)
        result["hostname"] = self._resolve_hostname(host)
        
        # Perform port scan(s) and collect open ports with protocol preserved
        scan_results_by_protocol: List[Tuple[str, Dict[int, PortState]]] = []

        if scan_type == ScanType.TCP_CONNECT:
            scan_results_by_protocol.append(
                ("tcp", await self.port_scanner.tcp_connect_scan(host, ports))
            )
        elif scan_type == ScanType.TCP_SYN:
            scan_results_by_protocol.append(
                ("tcp", await self.port_scanner.tcp_syn_scan(host, ports))
            )
        elif scan_type == ScanType.UDP:
            scan_results_by_protocol.append(
                ("udp", await self.port_scanner.udp_scan(host, ports))
            )
        elif scan_type == ScanType.COMPREHENSIVE:
            # TCP uses selected range; UDP uses a common-port baseline
            tcp_results = await self.port_scanner.tcp_syn_scan(host, ports)
            udp_ports = DEFAULT_UDP_PORTS
            udp_results = await self.port_scanner.udp_scan(host, udp_ports)
            scan_results_by_protocol.append(("tcp", tcp_results))
            scan_results_by_protocol.append(("udp", udp_results))

        if progress_callback:
            await progress_callback({
                "status": "scanning",
                "message": f"Scanning {host} (Ports)...",
                "current_host": host,
                "progress": base_progress + int(progress_step * 0.3)
            })

        # Process open ports
        open_ports = []
        for protocol, port_results in scan_results_by_protocol:
            for port_num, state in port_results.items():
                if state == PortState.OPEN:
                    port_info = {
                        "port_number": port_num,
                        "protocol": protocol,
                        "state": state.value,
                        "service_name": None,
                        "service_product": None,
                        "service_version": None,
                        "banner": None,
                    }

                    # Service detection
                    if service_detection:
                        service_info = await self.service_detector.detect_service(
                            host,
                            port_num,
                            protocol
                        )
                        port_info.update(service_info)

                    result["ports"].append(port_info)
                    open_ports.append(port_num)
        
        if progress_callback:
            await progress_callback({
                "status": "scanning",
                "message": f"Scanning {host} (Services)...",
                "current_host": host,
                "progress": base_progress + int(progress_step * 0.6)
            })
        
        # OS detection
        if os_detection and open_ports:
            os_info = await self.os_fingerprinter.detect_os(host, open_ports)
            result["os_name"] = os_info.get("os_name")
            result["os_accuracy"] = os_info.get("os_accuracy")
            result["os_details"] = os_info.get("os_details")

        if progress_callback:
            await progress_callback({
                "status": "scanning",
                "message": f"Scanning {host} (OS)...",
                "current_host": host,
                "progress": base_progress + int(progress_step * 0.9)
            })
        
        return result
