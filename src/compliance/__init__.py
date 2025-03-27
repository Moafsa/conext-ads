"""Automated Compliance System

This module implements automated compliance checking and monitoring
for ad content and campaigns across different platforms.

The system ensures that all ad content and campaigns comply with:
1. Platform-specific policies
2. Regional regulations
3. Industry standards
4. Brand guidelines
"""

from typing import List

__all__ = [
    'PolicyChecker',
    'ContentModerator',
    'RegulatoryMonitor',
    'ComplianceReporter'
]

# Import core components
from .policy import PolicyChecker
from .moderator import ContentModerator
from .monitor import RegulatoryMonitor
from .reporter import ComplianceReporter

# Version info
__version__ = '1.0.0'
__author__ = 'Conext Ads Team'