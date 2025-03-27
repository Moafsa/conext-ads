"""Regulatory Monitor Module

This module implements automated monitoring of regulatory compliance
for ad campaigns across different regions and industries.
"""

from typing import Dict, List, Optional, Set
import logging
from dataclasses import dataclass
from datetime import datetime
import json
import requests
from pathlib import Path
import yaml
import schedule
import time
import threading

@dataclass
class Regulation:
    """Represents a regulatory requirement"""
    id: str
    region: str
    industry: str
    description: str
    requirements: List[str]
    effective_date: datetime
    expiry_date: Optional[datetime] = None
    is_active: bool = True

@dataclass
class ComplianceCheck:
    """Result of a compliance check"""
    regulation_id: str
    content_id: str
    is_compliant: bool
    missing_requirements: List[str]
    details: Dict[str, any]
    timestamp: datetime

class RegulatoryMonitor:
    """Monitors regulatory compliance for ad campaigns"""
    
    def __init__(self, config: Dict[str, any]):
        """Initialize regulatory monitor
        
        Args:
            config: Configuration dictionary containing:
                - regulations_path: Path to regulations directory
                - update_interval: Update interval in hours
                - api_key: API key for regulatory updates
                - cache_size: Size of results cache
        """
        self.config = config
        self.logger = logging.getLogger(__name__)
        self.regulations: Dict[str, Regulation] = {}
        self.cache: Dict[str, ComplianceCheck] = {}
        self.update_thread = None
        self.running = False
        
        # Load initial regulations
        self._load_regulations()
        
        # Start update scheduler
        self._start_scheduler()
    
    def check_compliance(
        self,
        content: Dict[str, any],
        region: str,
        industry: str
    ) -> List[ComplianceCheck]:
        """Check content for regulatory compliance
        
        Args:
            content: Content to check
            region: Target region
            industry: Industry sector
            
        Returns:
            List of compliance check results
        """
        try:
            results = []
            
            # Get applicable regulations
            regulations = self._get_applicable_regulations(region, industry)
            
            for regulation in regulations:
                # Check cache
                cache_key = f"{content['id']}:{regulation.id}"
                if cache_key in self.cache:
                    results.append(self.cache[cache_key])
                    continue
                
                # Check requirements
                missing = []
                for req in regulation.requirements:
                    if not self._check_requirement(req, content):
                        missing.append(req)
                
                # Create result
                result = ComplianceCheck(
                    regulation_id=regulation.id,
                    content_id=content['id'],
                    is_compliant=len(missing) == 0,
                    missing_requirements=missing,
                    details={
                        'region': region,
                        'industry': industry,
                        'regulation': regulation.description,
                        'content_type': content.get('type')
                    },
                    timestamp=datetime.now()
                )
                
                # Cache result
                self.cache[cache_key] = result
                results.append(result)
            
            return results
            
        except Exception as e:
            self.logger.error(f"Compliance check failed: {str(e)}")
            raise
    
    def check_campaign(
        self,
        campaign: Dict[str, any],
        region: str,
        industry: str
    ) -> Dict[str, List[ComplianceCheck]]:
        """Check campaign for regulatory compliance
        
        Args:
            campaign: Campaign data
            region: Target region
            industry: Industry sector
            
        Returns:
            Dictionary mapping content IDs to compliance results
        """
        try:
            results = {}
            
            # Check campaign settings
            settings_results = self.check_compliance(
                campaign['settings'],
                region,
                industry
            )
            if settings_results:
                results['settings'] = settings_results
            
            # Check each ad
            for ad in campaign.get('ads', []):
                ad_results = self.check_compliance(
                    ad,
                    region,
                    industry
                )
                if ad_results:
                    results[ad['id']] = ad_results
            
            return results
            
        except Exception as e:
            self.logger.error(f"Campaign compliance check failed: {str(e)}")
            raise
    
    def add_regulation(self, regulation: Regulation) -> None:
        """Add new regulation
        
        Args:
            regulation: Regulation to add
        """
        try:
            # Validate regulation
            if not self._validate_regulation(regulation):
                raise ValueError("Invalid regulation format")
            
            # Add to regulations
            self.regulations[regulation.id] = regulation
            
            # Clear cache since regulations changed
            self.cache.clear()
            
            self.logger.info(f"Added regulation {regulation.id}")
            
        except Exception as e:
            self.logger.error(f"Failed to add regulation: {str(e)}")
            raise
    
    def update_regulation(
        self,
        regulation_id: str,
        updates: Dict[str, any]
    ) -> None:
        """Update existing regulation
        
        Args:
            regulation_id: ID of regulation to update
            updates: Dictionary of updates to apply
        """
        try:
            if regulation_id not in self.regulations:
                raise KeyError(f"Regulation {regulation_id} not found")
            
            # Get current regulation
            regulation = self.regulations[regulation_id]
            
            # Apply updates
            for key, value in updates.items():
                if hasattr(regulation, key):
                    setattr(regulation, key, value)
            
            # Validate updated regulation
            if not self._validate_regulation(regulation):
                raise ValueError("Invalid regulation after update")
            
            # Update regulation
            self.regulations[regulation_id] = regulation
            
            # Clear cache
            self.cache.clear()
            
            self.logger.info(f"Updated regulation {regulation_id}")
            
        except Exception as e:
            self.logger.error(f"Failed to update regulation: {str(e)}")
            raise
    
    def _load_regulations(self) -> None:
        """Load regulations from files"""
        try:
            regulations_dir = Path(self.config['regulations_path'])
            
            for file_path in regulations_dir.glob('*.yml'):
                with open(file_path) as f:
                    data = yaml.safe_load(f)
                    
                    for reg_data in data:
                        regulation = Regulation(**reg_data)
                        if self._validate_regulation(regulation):
                            self.regulations[regulation.id] = regulation
            
            self.logger.info(f"Loaded {len(self.regulations)} regulations")
            
        except Exception as e:
            self.logger.error(f"Failed to load regulations: {str(e)}")
            raise
    
    def _start_scheduler(self) -> None:
        """Start regulation update scheduler"""
        def update_job():
            while self.running:
                try:
                    self._update_regulations()
                except Exception as e:
                    self.logger.error(f"Update job failed: {str(e)}")
                time.sleep(self.config['update_interval'] * 3600)
        
        self.running = True
        self.update_thread = threading.Thread(target=update_job)
        self.update_thread.daemon = True
        self.update_thread.start()
    
    def _update_regulations(self) -> None:
        """Update regulations from external source"""
        try:
            # Call regulatory API
            response = requests.get(
                self.config['api_url'],
                headers={'Authorization': f"Bearer {self.config['api_key']}"}
            )
            response.raise_for_status()
            
            # Process updates
            updates = response.json()
            for update in updates:
                regulation = Regulation(**update)
                if self._validate_regulation(regulation):
                    self.regulations[regulation.id] = regulation
            
            self.logger.info("Regulations updated successfully")
            
        except Exception as e:
            self.logger.error(f"Regulations update failed: {str(e)}")
            raise
    
    def _validate_regulation(self, regulation: Regulation) -> bool:
        """Validate regulation
        
        Args:
            regulation: Regulation to validate
            
        Returns:
            bool: True if regulation is valid
        """
        try:
            # Check required fields
            if not all([
                regulation.id,
                regulation.region,
                regulation.industry,
                regulation.requirements
            ]):
                return False
            
            # Check dates
            if regulation.expiry_date and regulation.effective_date > regulation.expiry_date:
                return False
            
            return True
            
        except Exception:
            return False
    
    def _get_applicable_regulations(
        self,
        region: str,
        industry: str
    ) -> List[Regulation]:
        """Get regulations applicable to region and industry
        
        Args:
            region: Target region
            industry: Industry sector
            
        Returns:
            List of applicable regulations
        """
        now = datetime.now()
        return [
            reg for reg in self.regulations.values()
            if reg.is_active and
            reg.region == region and
            reg.industry == industry and
            reg.effective_date <= now and
            (not reg.expiry_date or reg.expiry_date > now)
        ]
    
    def _check_requirement(
        self,
        requirement: str,
        content: Dict[str, any]
    ) -> bool:
        """Check if content meets requirement
        
        Args:
            requirement: Requirement to check
            content: Content to check
            
        Returns:
            bool: True if requirement is met
        """
        try:
            # Parse requirement
            req_parts = requirement.split(':')
            if len(req_parts) != 2:
                return False
            
            field, condition = req_parts
            
            # Get field value
            value = content.get(field)
            if value is None:
                return False
            
            # Check condition
            if condition.startswith('min_length='):
                min_len = int(condition.split('=')[1])
                return len(str(value)) >= min_len
            
            elif condition.startswith('max_length='):
                max_len = int(condition.split('=')[1])
                return len(str(value)) <= max_len
            
            elif condition.startswith('contains='):
                required = condition.split('=')[1]
                return required in str(value)
            
            elif condition.startswith('not_contains='):
                forbidden = condition.split('=')[1]
                return forbidden not in str(value)
            
            elif condition == 'required':
                return bool(value)
            
            return False
            
        except Exception:
            return False