import asyncio
from datetime import datetime
from sqlalchemy.orm import Session
import logging

from app.database import SessionLocal
from app.models.scan import Scan, ScanResult, Port, ScanStatus
from app.core.scanner import NetworkScanner

logger = logging.getLogger(__name__)

try:
    from app.celery_app import celery_app
except Exception:  # pragma: no cover - test fallback
    celery_app = None


def _task_decorator(*dargs, **dkwargs):
    if celery_app is not None and hasattr(celery_app, "task"):
        return celery_app.task(*dargs, **dkwargs)

    def decorator(func):
        return func

    return decorator


@_task_decorator(bind=True)
def perform_scan_task(self, scan_id: int):
    """
    Celery task to perform network scan.
    
    Args:
        scan_id: ID of the scan to perform
    """
    db = SessionLocal()
    
    try:
        # Get scan from database
        scan = db.query(Scan).filter(Scan.id == scan_id).first()
        
        if not scan:
            logger.error(f"Scan {scan_id} not found")
            return
        
        # Update scan status
        scan.status = ScanStatus.RUNNING
        scan.started_at = datetime.utcnow()
        scan.task_id = self.request.id
        db.commit()
        
        # Create scanner
        scanner = NetworkScanner()
        
        # Progress callback
        async def progress_callback(update: dict):
            """Update scan progress in database"""
            try:
                scan.progress = update.get("progress", scan.progress)
                scan.current_host = update.get("current_host", scan.current_host)
                scan.hosts_scanned = update.get("hosts_scanned", scan.hosts_scanned)
                db.commit()
                
                # Update Celery task state
                self.update_state(
                    state='PROGRESS',
                    meta={
                        'progress': scan.progress,
                        'current_host': scan.current_host,
                        'message': update.get("message", "")
                    }
                )
            except Exception as e:
                logger.error(f"Error updating progress: {e}")
        
        # Run scan
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        results = loop.run_until_complete(
            scanner.scan(
                target=scan.target,
                scan_type=scan.scan_type,
                port_range=scan.port_range,
                service_detection=scan.service_detection,
                os_detection=scan.os_detection,
                progress_callback=progress_callback
            )
        )
        
        loop.close()
        
        # Save results to database
        scan.hosts_total = results["hosts_total"]
        scan.total_hosts_up = results["hosts_up"]
        scan.total_ports_found = results["total_ports_found"]
        
        for host_result in results["results"]:
            # Create scan result
            scan_result = ScanResult(
                scan_id=scan.id,
                ip_address=host_result["ip_address"],
                hostname=host_result.get("hostname"),
                is_up=host_result["is_up"],
                os_name=host_result.get("os_name"),
                os_accuracy=host_result.get("os_accuracy"),
                os_details=host_result.get("os_details"),
                scanned_at=datetime.utcnow()
            )
            db.add(scan_result)
            db.flush()  # Get scan_result.id
            
            # Add ports
            for port_info in host_result.get("ports", []):
                port = Port(
                    result_id=scan_result.id,
                    port_number=port_info["port_number"],
                    protocol=port_info["protocol"],
                    state=port_info["state"],
                    service_name=port_info.get("service_name"),
                    service_product=port_info.get("service_product"),
                    service_version=port_info.get("service_version"),
                    banner=port_info.get("banner")
                )
                db.add(port)
        
        # Update scan status
        scan.status = ScanStatus.COMPLETED
        scan.completed_at = datetime.utcnow()
        scan.progress = 100
        db.commit()
        
        logger.info(f"Scan {scan_id} completed successfully")
        
        return {
            "scan_id": scan_id,
            "status": "completed",
            "hosts_up": results["hosts_up"],
            "ports_found": results["total_ports_found"]
        }
        
    except Exception as e:
        logger.error(f"Error performing scan {scan_id}: {e}")
        
        # Update scan status to failed
        scan = db.query(Scan).filter(Scan.id == scan_id).first()
        if scan:
            scan.status = ScanStatus.FAILED
            scan.error_message = str(e)
            scan.completed_at = datetime.utcnow()
            db.commit()
        
        raise
        
    finally:
        db.close()


@_task_decorator
def dispatch_due_schedules_task():
    """Celery Beat entrypoint that dispatches due scheduled scans (DEC-008)."""
    # Imported lazily so the task module and scheduler stay import-cycle free.
    from app.core.scheduler import dispatch_due_schedules

    db = SessionLocal()
    try:
        return {"dispatched": dispatch_due_schedules(db)}
    finally:
        db.close()
