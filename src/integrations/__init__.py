"""Technical Integrations Module

This module handles integrations with various ad platforms and data services,
providing a unified interface for managing ad campaigns across platforms.
"""

from typing import Dict, List, Optional, Union
from abc import ABC, abstractmethod

class PlatformConnector(ABC):
    """Abstract base class for platform connectors"""
    
    @abstractmethod
    def authenticate(self) -> bool:
        """Authenticate with the platform"""
        pass
    
    @abstractmethod
    def create_campaign(self, campaign_data: Dict[str, any]) -> str:
        """Create a new campaign"""
        pass
    
    @abstractmethod
    def update_campaign(self, campaign_id: str, updates: Dict[str, any]) -> bool:
        """Update an existing campaign"""
        pass
    
    @abstractmethod
    def get_campaign_stats(self, campaign_id: str) -> Dict[str, any]:
        """Get campaign performance statistics"""
        pass
    
    @abstractmethod
    def create_ad(self, campaign_id: str, ad_data: Dict[str, any]) -> str:
        """Create a new ad in a campaign"""
        pass
    
    @abstractmethod
    def update_ad(self, ad_id: str, updates: Dict[str, any]) -> bool:
        """Update an existing ad"""
        pass
    
    @abstractmethod
    def get_ad_stats(self, ad_id: str) -> Dict[str, any]:
        """Get ad performance statistics"""
        pass

class DataPipeline(ABC):
    """Abstract base class for data pipelines"""
    
    @abstractmethod
    def extract_data(self, source: str, params: Dict[str, any]) -> List[Dict[str, any]]:
        """Extract data from source"""
        pass
    
    @abstractmethod
    def transform_data(self, data: List[Dict[str, any]]) -> List[Dict[str, any]]:
        """Transform extracted data"""
        pass
    
    @abstractmethod
    def load_data(self, data: List[Dict[str, any]], destination: str) -> bool:
        """Load transformed data to destination"""
        pass

class APIGateway(ABC):
    """Abstract base class for API gateway"""
    
    @abstractmethod
    def authenticate_request(self, request: Dict[str, any]) -> bool:
        """Authenticate incoming request"""
        pass
    
    @abstractmethod
    def validate_request(self, request: Dict[str, any]) -> bool:
        """Validate request format and content"""
        pass
    
    @abstractmethod
    def route_request(self, request: Dict[str, any]) -> Dict[str, any]:
        """Route request to appropriate handler"""
        pass
    
    @abstractmethod
    def format_response(self, response: Dict[str, any]) -> Dict[str, any]:
        """Format response according to API standards"""
        pass

# Export classes
__all__ = ['PlatformConnector', 'DataPipeline', 'APIGateway']