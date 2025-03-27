"""Analytics Module

This module handles cross-platform analytics, attribution modeling,
and automated reporting.
"""

from .dashboard import UnifiedDashboard
from .attribution import AttributionModel
from .reporting import AutomatedReporting

__all__ = ['UnifiedDashboard', 'AttributionModel', 'AutomatedReporting']