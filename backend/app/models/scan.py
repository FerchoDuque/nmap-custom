from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Enum, JSON, Boolean, Text
from sqlalchemy.orm import relationship
from datetime import datetime
import enum
from app.database import Base


class ScanType(str, enum.Enum):
    """Scan type enumeration"""
    TCP_CONNECT = "tcp_connect"
    TCP_SYN = "tcp_syn"
    UDP = "udp"
    COMPREHENSIVE = "comprehensive"


class ScanStatus(str, enum.Enum):
    """Scan status enumeration"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class PortState(str, enum.Enum):
    """Port state enumeration"""
    OPEN = "open"
    CLOSED = "closed"
    FILTERED = "filtered"
    UNKNOWN = "unknown"


class Scan(Base):
    """Scan model - represents a network scan operation"""
    
    __tablename__ = "scans"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=True)
    target = Column(String(255), nullable=False, index=True)
    scan_type = Column(Enum(ScanType), nullable=False)
    status = Column(Enum(ScanStatus), default=ScanStatus.PENDING, index=True)
    
    # Port configuration
    port_range = Column(String(255), nullable=True)  # e.g., "1-1000,8080,8443"
    
    # Scan options
    service_detection = Column(Boolean, default=True)
    os_detection = Column(Boolean, default=False)
    aggressive = Column(Boolean, default=False)
    
    # Progress tracking
    progress = Column(Integer, default=0)  # 0-100
    current_host = Column(String(255), nullable=True)
    hosts_total = Column(Integer, default=0)
    hosts_scanned = Column(Integer, default=0)
    
    # Timing
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    
    # Results summary
    total_hosts_up = Column(Integer, default=0)
    total_ports_found = Column(Integer, default=0)
    
    # Error information
    error_message = Column(Text, nullable=True)
    
    # Celery task ID
    task_id = Column(String(255), nullable=True, index=True)
    
    # Relationships
    results = relationship("ScanResult", back_populates="scan", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<Scan(id={self.id}, target={self.target}, status={self.status})>"


class ScanResult(Base):
    """Scan result model - represents results for a single host"""
    
    __tablename__ = "scan_results"
    
    id = Column(Integer, primary_key=True, index=True)
    scan_id = Column(Integer, ForeignKey("scans.id"), nullable=False, index=True)
    
    # Host information
    ip_address = Column(String(45), nullable=False, index=True)  # IPv4 or IPv6
    hostname = Column(String(255), nullable=True)
    mac_address = Column(String(17), nullable=True)
    
    # Status
    is_up = Column(Boolean, default=False)
    
    # OS Detection
    os_name = Column(String(255), nullable=True)
    os_accuracy = Column(Integer, nullable=True)  # 0-100
    os_details = Column(JSON, nullable=True)
    
    # Additional information
    latency = Column(Integer, nullable=True)  # in milliseconds
    
    # Timestamps
    scanned_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    scan = relationship("Scan", back_populates="results")
    ports = relationship("Port", back_populates="result", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<ScanResult(id={self.id}, ip={self.ip_address}, is_up={self.is_up})>"


class Port(Base):
    """Port model - represents a single port on a host"""
    
    __tablename__ = "ports"
    
    id = Column(Integer, primary_key=True, index=True)
    result_id = Column(Integer, ForeignKey("scan_results.id"), nullable=False, index=True)
    
    # Port information
    port_number = Column(Integer, nullable=False, index=True)
    protocol = Column(String(10), nullable=False)  # tcp, udp
    state = Column(Enum(PortState), nullable=False)
    
    # Service information
    service_name = Column(String(255), nullable=True)
    service_product = Column(String(255), nullable=True)
    service_version = Column(String(255), nullable=True)
    service_extra_info = Column(Text, nullable=True)
    
    # Banner
    banner = Column(Text, nullable=True)
    
    # Relationships
    result = relationship("ScanResult", back_populates="ports")
    
    def __repr__(self):
        return f"<Port(port={self.port_number}, protocol={self.protocol}, state={self.state})>"


class Schedule(Base):
    """Schedule model - represents a scheduled scan"""
    
    __tablename__ = "schedules"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    
    # Scan configuration (stored as JSON)
    scan_config = Column(JSON, nullable=False)
    
    # Schedule configuration
    cron_expression = Column(String(100), nullable=False)
    enabled = Column(Boolean, default=True, index=True)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    last_run_at = Column(DateTime, nullable=True)
    next_run_at = Column(DateTime, nullable=True)
    
    # Statistics
    total_runs = Column(Integer, default=0)
    successful_runs = Column(Integer, default=0)
    failed_runs = Column(Integer, default=0)
    
    def __repr__(self):
        return f"<Schedule(id={self.id}, name={self.name}, enabled={self.enabled})>"
