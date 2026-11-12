from fastapi import APIRouter, Depends, HTTPException, status, Response
from sqlalchemy.orm import Session
from typing import List
import json
import csv
import io
from datetime import datetime

from app.database import get_db
from app.models.scan import Scan, ScanResult, Port, ScanStatus
from app.schemas.scan import (
    ScanCreate,
    ScanUpdate,
    ScanSummaryResponse,
    ScanResponse,
    ScanResultResponse,
    ExportRequest
)
from app.tasks import perform_scan_task

router = APIRouter(prefix="/api/scans", tags=["scans"])


@router.post("", response_model=ScanResponse, status_code=status.HTTP_201_CREATED)
def create_scan(scan_data: ScanCreate, db: Session = Depends(get_db)):
    """
    Create and start a new network scan.
    
    Args:
        scan_data: Scan configuration
        db: Database session
        
    Returns:
        Created scan object
    """
    # Create scan in database
    scan = Scan(
        name=scan_data.name,
        target=scan_data.target,
        scan_type=scan_data.scan_type,
        port_range=scan_data.port_range,
        service_detection=scan_data.service_detection,
        os_detection=scan_data.os_detection,
        aggressive=scan_data.aggressive,
        status=ScanStatus.PENDING
    )
    
    db.add(scan)
    db.commit()
    db.refresh(scan)
    
    # Start scan task
    task = perform_scan_task.delay(scan.id)
    
    # Update scan with task ID
    scan.task_id = task.id
    db.commit()
    db.refresh(scan)
    
    return scan


@router.get("", response_model=List[ScanSummaryResponse])
def list_scans(
    skip: int = 0,
    limit: int = 100,
    status_filter: ScanStatus = None,
    db: Session = Depends(get_db)
):
    """
    List all scans with optional filtering.
    
    Args:
        skip: Number of records to skip
        limit: Maximum number of records to return
        status_filter: Filter by scan status
        db: Database session
        
    Returns:
        List of scans
    """
    query = db.query(Scan)
    
    if status_filter:
        query = query.filter(Scan.status == status_filter)
    
    scans = query.order_by(Scan.created_at.desc()).offset(skip).limit(limit).all()
    
    return scans


@router.get("/{scan_id}", response_model=ScanResponse)
def get_scan(scan_id: int, db: Session = Depends(get_db)):
    """
    Get scan details by ID.
    
    Args:
        scan_id: Scan ID
        db: Database session
        
    Returns:
        Scan object with results
    """
    scan = db.query(Scan).filter(Scan.id == scan_id).first()
    
    if not scan:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Scan {scan_id} not found"
        )
    
    return scan


@router.patch("/{scan_id}", response_model=ScanResponse)
def update_scan(
    scan_id: int,
    scan_update: ScanUpdate,
    db: Session = Depends(get_db)
):
    """
    Update scan details.

    Args:
        scan_id: Scan ID
        scan_update: Update data
        db: Database session

    Returns:
        Updated scan object
    """
    scan = db.query(Scan).filter(Scan.id == scan_id).first()

    if not scan:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Scan {scan_id} not found"
        )

    # Update fields
    if scan_update.name is not None:
        scan.name = scan_update.name
    if scan_update.status is not None:
        # Normalize lifecycle transitions for cancellation
        if scan_update.status == ScanStatus.CANCELLED and scan.status in {ScanStatus.PENDING, ScanStatus.RUNNING}:
            if scan.task_id:
                from app.celery_app import celery_app
                celery_app.control.revoke(scan.task_id, terminate=True)
            scan.status = ScanStatus.CANCELLED
            if not scan.completed_at:
                scan.completed_at = datetime.utcnow()
            if not scan.error_message:
                scan.error_message = "Scan cancelled by user"
        else:
            scan.status = scan_update.status

    db.commit()
    db.refresh(scan)

    return scan


@router.delete("/{scan_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_scan(scan_id: int, db: Session = Depends(get_db)):
    """
    Delete a scan and its results.

    Args:
        scan_id: Scan ID
        db: Database session
    """
    scan = db.query(Scan).filter(Scan.id == scan_id).first()

    if not scan:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Scan {scan_id} not found"
        )

    # Cancel task if running/pending before deletion
    if scan.status in {ScanStatus.RUNNING, ScanStatus.PENDING} and scan.task_id:
        from app.celery_app import celery_app
        celery_app.control.revoke(scan.task_id, terminate=True)

    db.delete(scan)
    db.commit()

    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/{scan_id}/export")
def export_scan(
    scan_id: int,
    export_request: ExportRequest,
    db: Session = Depends(get_db)
):
    """
    Export scan results in various formats.
    
    Args:
        scan_id: Scan ID
        export_request: Export format specification
        db: Database session
        
    Returns:
        Exported data in requested format
    """
    scan = db.query(Scan).filter(Scan.id == scan_id).first()
    
    if not scan:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Scan {scan_id} not found"
        )
    
    export_format = export_request.format.lower()
    
    if export_format == "json":
        return _export_json(scan)
    elif export_format == "csv":
        return _export_csv(scan)
    elif export_format == "xml":
        return _export_xml(scan)
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported export format: {export_format}"
        )


def _export_json(scan: Scan):
    """Export scan as JSON"""
    data = {
        "scan": {
            "id": scan.id,
            "name": scan.name,
            "target": scan.target,
            "scan_type": scan.scan_type.value,
            "status": scan.status.value,
            "created_at": scan.created_at.isoformat(),
            "completed_at": scan.completed_at.isoformat() if scan.completed_at else None,
        },
        "results": []
    }
    
    for result in scan.results:
        result_data = {
            "ip_address": result.ip_address,
            "hostname": result.hostname,
            "is_up": result.is_up,
            "os_name": result.os_name,
            "ports": []
        }
        
        for port in result.ports:
            result_data["ports"].append({
                "port": port.port_number,
                "protocol": port.protocol,
                "state": port.state.value,
                "service": port.service_name,
                "version": port.service_version,
            })
        
        data["results"].append(result_data)
    
    return Response(
        content=json.dumps(data, indent=2),
        media_type="application/json",
        headers={"Content-Disposition": f"attachment; filename=scan_{scan.id}.json"}
    )


def _export_csv(scan: Scan):
    """Export scan as CSV"""
    output = io.StringIO()
    writer = csv.writer(output)
    
    # Header
    writer.writerow(["IP Address", "Hostname", "Port", "Protocol", "State", "Service", "Version"])
    
    # Data
    for result in scan.results:
        for port in result.ports:
            writer.writerow([
                result.ip_address,
                result.hostname or "",
                port.port_number,
                port.protocol,
                port.state.value,
                port.service_name or "",
                port.service_version or "",
            ])
    
    return Response(
        content=output.getvalue(),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename=scan_{scan.id}.csv"}
    )


def _export_xml(scan: Scan):
    """Export scan as XML (nmap-style)"""
    xml_lines = ['<?xml version="1.0"?>']
    xml_lines.append(f'<nmaprun scanner="network-scanner" start="{scan.created_at.timestamp()}">')
    
    for result in scan.results:
        xml_lines.append(f'  <host>')
        xml_lines.append(f'    <address addr="{result.ip_address}" addrtype="ipv4"/>')
        
        if result.hostname:
            xml_lines.append(f'    <hostnames><hostname name="{result.hostname}"/></hostnames>')
        
        xml_lines.append(f'    <ports>')
        for port in result.ports:
            xml_lines.append(f'      <port protocol="{port.protocol}" portid="{port.port_number}">')
            xml_lines.append(f'        <state state="{port.state.value}"/>')
            if port.service_name:
                xml_lines.append(f'        <service name="{port.service_name}" product="{port.service_product or ""}" version="{port.service_version or ""}"/>')
            xml_lines.append(f'      </port>')
        xml_lines.append(f'    </ports>')
        
        xml_lines.append(f'  </host>')
    
    xml_lines.append('</nmaprun>')
    
    return Response(
        content='\n'.join(xml_lines),
        media_type="application/xml",
        headers={"Content-Disposition": f"attachment; filename=scan_{scan.id}.xml"}
    )
