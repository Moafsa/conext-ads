"""Data Pipeline Module

This module handles ETL processes, data warehouse integration, and
real-time data streaming for the ad automation system.
"""

from typing import Dict, List, Optional, Union
from abc import ABC, abstractmethod
import logging
from datetime import datetime

class DataSource(ABC):
    """Abstract base class for data sources"""
    
    @abstractmethod
    def connect(self) -> bool:
        """Connect to data source"""
        pass
    
    @abstractmethod
    def extract_data(self, query: str) -> List[Dict[str, any]]:
        """Extract data from source"""
        pass
    
    @abstractmethod
    def validate_data(self, data: List[Dict[str, any]]) -> bool:
        """Validate extracted data"""
        pass

class DataTransformer(ABC):
    """Abstract base class for data transformers"""
    
    @abstractmethod
    def transform(self, data: List[Dict[str, any]]) -> List[Dict[str, any]]:
        """Transform data"""
        pass
    
    @abstractmethod
    def validate_schema(self, data: List[Dict[str, any]]) -> bool:
        """Validate data schema"""
        pass
    
    @abstractmethod
    def clean_data(self, data: List[Dict[str, any]]) -> List[Dict[str, any]]:
        """Clean and prepare data"""
        pass

class DataLoader(ABC):
    """Abstract base class for data loaders"""
    
    @abstractmethod
    def connect(self) -> bool:
        """Connect to data destination"""
        pass
    
    @abstractmethod
    def load_data(self, data: List[Dict[str, any]]) -> bool:
        """Load data to destination"""
        pass
    
    @abstractmethod
    def validate_load(self, data: List[Dict[str, any]]) -> bool:
        """Validate loaded data"""
        pass

class StreamProcessor(ABC):
    """Abstract base class for stream processors"""
    
    @abstractmethod
    def process_stream(self, stream_data: Dict[str, any]) -> Dict[str, any]:
        """Process streaming data"""
        pass
    
    @abstractmethod
    def handle_error(self, error: Exception) -> bool:
        """Handle stream processing error"""
        pass
    
    @abstractmethod
    def emit_event(self, event: Dict[str, any]) -> bool:
        """Emit processed event"""
        pass

# Export classes
__all__ = [
    'DataSource',
    'DataTransformer',
    'DataLoader',
    'StreamProcessor'
]