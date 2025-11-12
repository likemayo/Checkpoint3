"""
RMA (Return Merchandise Authorization) Module

This module implements a complete 7-step RMA workflow:
1. RMA Request Submission
2. Validation & Authorization
3. Return Shipping
4. Inspection & Diagnosis
5. Disposition Decision
6. Repair / Replacement / Refund
7. Closure & Reporting
"""

from .manager import RMAManager
from .routes import bp as rma_bp

__all__ = ["RMAManager", "rma_bp"]
