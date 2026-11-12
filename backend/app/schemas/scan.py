from croniter import croniter
from pydantic import BaseModel, Field, validator
from typing import Optional, List, Dict, Any
from datetime import datetime
from app.models.scan import ScanType, ScanStatus, PortState


# ============================================================================
# Scan Schemas
# ============================================================================

class ScanCreate(BaseModel):
    """Schema for creating a new scan"""
    name: Optional[str] = Field(None, max_length=255)
    target: str = Field(..., description="IP address, CIDR range, or hostname")
    scan_type: ScanType = Field(default=ScanType.TCP_CONNECT)
    port_range: Optional[str] = Field(None, description="e.g., '1-1000,8080,8443'")
    service_detection: bool = Field(default=True)
    os_detection: bool = Field(default=False)
    aggressive: bool = Field(default=False)
    
    @validator("target")
    def validate_target(cls, v):
        """Validate target format"""
        if not v or len(v.strip()) == 0:
            raise ValueError("Target cannot be empty")
        # Basic validation - could be enhanced with IP/CIDR validation
        return v.strip()
    
    @validator("port_range")
    def validate_port_range(cls, v):
        """Validate port range format"""
        if v is None:
            return v
        # Basic validation - could be enhanced with proper port range parsing
        return v.strip()


class ScanUpdate(BaseModel):
    """Schema for updating a scan"""
    name: Optional[str] = None
    status: Optional[ScanStatus] = None


class PortInfo(BaseModel):
    """Schema for port information"""
    port_number: int
    protocol: str
    state: PortState
    service_name: Optional[str] = None
    service_product: Optional[str] = None
    service_version: Optional[str] = None
    service_extra_info: Optional[str] = None
    banner: Optional[str] = None
    
    class Config:
        from_attributes = True


class ScanResultResponse(BaseModel):
    """Schema for scan result response"""
    id: int
    scan_id: int
    ip_address: str
    hostname: Optional[str] = None
    mac_address: Optional[str] = None
    is_up: bool
    os_name: Optional[str] = None
    os_accuracy: Optional[int] = None
    os_details: Optional[Dict[str, Any]] = None
    latency: Optional[int] = None
    scanned_at: datetime
    ports: List[PortInfo] = []
    
    class Config:
        from_attributes = True


class ScanSummaryResponse(BaseModel):
    """Schema for scan summary (list views)"""
    id: int
    name: Optional[str] = None
    target: str
    scan_type: ScanType
    status: ScanStatus
    port_range: Optional[str] = None
    service_detection: bool
    os_detection: bool
    aggressive: bool
    progress: int
    current_host: Optional[str] = None
    hosts_total: int
    hosts_scanned: int
    created_at: datetime
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    total_hosts_up: int
    total_ports_found: int
    error_message: Optional[str] = None
    task_id: Optional[str] = None

    class Config:
        from_attributes = True


class ScanResponse(ScanSummaryResponse):
    """Schema for scan detail response"""
    results: List[ScanResultResponse] = []


class ScanProgress(BaseModel):
    """Schema for real-time scan progress updates"""
    scan_id: int
    status: ScanStatus
    progress: int
    current_host: Optional[str] = None
    hosts_scanned: int
    hosts_total: int
    ports_found: int
    message: Optional[str] = None


# ============================================================================
# Schedule Schemas
# ============================================================================

class ScheduleCreate(BaseModel):
    """Schema for creating a schedule"""
    name: str = Field(..., max_length=255)
    description: Optional[str] = None
    scan_config: Dict[str, Any] = Field(..., description="Scan configuration as JSON")
    cron_expression: str = Field(..., description="Cron expression for scheduling")
    enabled: bool = Field(default=True)
    
    @validator("cron_expression")
    def validate_cron(cls, v):
        """Validate a standard 5-field cron expression"""
        expression = v.strip()
        if not croniter.is_valid(expression):
            raise ValueError("Invalid cron expression")
        return expression


class ScheduleUpdate(BaseModel):
    """Schema for updating a schedule"""
    name: Optional[str] = None
    description: Optional[str] = None
    scan_config: Optional[Dict[str, Any]] = None
    cron_expression: Optional[str] = None
    enabled: Optional[bool] = None

    @validator("cron_expression")
    def validate_cron(cls, v):
        """Validate an optional 5-field cron expression"""
        if v is None:
            return v
        expression = v.strip()
        if not croniter.is_valid(expression):
            raise ValueError("Invalid cron expression")
        return expression


class ScheduleResponse(BaseModel):
    """Schema for schedule response"""
    id: int
    name: str
    description: Optional[str] = None
    scan_config: Dict[str, Any]
    cron_expression: str
    enabled: bool
    created_at: datetime
    updated_at: datetime
    last_run_at: Optional[datetime] = None
    next_run_at: Optional[datetime] = None
    total_runs: int
    successful_runs: int
    failed_runs: int
    
    class Config:
        from_attributes = True


# ============================================================================
# Export Schemas
# ============================================================================

class ExportFormat(str):
    """Export format enumeration"""
    JSON = "json"
    XML = "xml"
    CSV = "csv"


class ExportRequest(BaseModel):
    """Schema for export request"""
    format: str = Field(..., description="Export format: json, xml, or csv")
    
    @validator("format")
    def validate_format(cls, v):
        """Validate export format"""
        if v.lower() not in ["json", "xml", "csv"]:
            raise ValueError("Format must be json, xml, or csv")
        return v.lower()
