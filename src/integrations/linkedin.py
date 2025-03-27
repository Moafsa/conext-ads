"""LinkedIn Ads Integration Module

This module implements the LinkedIn Ads API integration for managing
ad campaigns on the LinkedIn advertising platform.
"""

from typing import Dict, List, Optional, Union
import logging
from datetime import datetime, timedelta
import requests
import json
from urllib.parse import urljoin

from .base import PlatformConnector

class LinkedInAdsConnector(PlatformConnector):
    """LinkedIn Ads platform connector implementation"""
    
    BASE_URL = "https://api.linkedin.com/v2/"
    
    def __init__(self, config: Dict[str, any]):
        """Initialize LinkedIn Ads connector
        
        Args:
            config: Configuration dictionary containing:
                - access_token: LinkedIn access token
                - account_id: LinkedIn account ID
                - organization_id: LinkedIn organization ID
        """
        self.config = config
        self.logger = logging.getLogger(__name__)
        self._initialize_client()
    
    def _initialize_client(self):
        """Initialize LinkedIn Ads API client"""
        try:
            self.headers = {
                "Authorization": f"Bearer {self.config['access_token']}",
                "Content-Type": "application/json",
                "X-Restli-Protocol-Version": "2.0.0"
            }
            self.account_id = self.config['account_id']
            self.organization_id = self.config['organization_id']
            
        except Exception as e:
            self.logger.error(f"Error initializing LinkedIn Ads client: {str(e)}")
            raise
    
    def _make_request(self,
                     endpoint: str,
                     method: str = "GET",
                     params: Dict = None,
                     data: Dict = None) -> Dict:
        """Make HTTP request to LinkedIn Ads API
        
        Args:
            endpoint: API endpoint
            method: HTTP method
            params: Query parameters
            data: Request body data
            
        Returns:
            API response data
        """
        try:
            url = urljoin(self.BASE_URL, endpoint)
            
            response = requests.request(
                method=method,
                url=url,
                headers=self.headers,
                params=params,
                json=data
            )
            
            response.raise_for_status()
            return response.json()
            
        except requests.exceptions.RequestException as e:
            self.logger.error(f"API request failed: {str(e)}")
            raise
    
    def authenticate(self) -> bool:
        """Authenticate with LinkedIn Ads
        
        Returns:
            bool: True if authentication successful
        """
        try:
            # Test API connection by getting account info
            response = self._make_request(
                endpoint=f"adAccountsV2/{self.account_id}"
            )
            
            return bool(response.get("id"))
            
        except Exception as e:
            self.logger.error(f"Authentication failed: {str(e)}")
            return False
    
    def create_campaign(self, campaign_data: Dict[str, any]) -> str:
        """Create a new LinkedIn ad campaign
        
        Args:
            campaign_data: Campaign configuration including:
                - name: Campaign name
                - objective: Campaign objective
                - type: Campaign type
                - status: Campaign status
                - daily_budget: Daily budget configuration
                - start_date: Campaign start date
                - end_date: Campaign end date (optional)
                
        Returns:
            str: Created campaign ID
        """
        try:
            data = {
                "account": f"urn:li:sponsoredAccount:{self.account_id}",
                "name": campaign_data['name'],
                "objective": campaign_data['objective'],
                "type": campaign_data['type'],
                "status": campaign_data['status'],
                "runSchedule": {
                    "start": campaign_data['start_date'],
                    "end": campaign_data.get('end_date')
                },
                "dailyBudget": {
                    "amount": str(campaign_data['daily_budget']['amount']),
                    "currencyCode": campaign_data['daily_budget']['currency']
                },
                "costType": "CPM",
                "unitCost": {
                    "amount": "10",
                    "currencyCode": campaign_data['daily_budget']['currency']
                }
            }
            
            response = self._make_request(
                endpoint="adCampaignsV2",
                method="POST",
                data=data
            )
            
            return response["id"]
            
        except Exception as e:
            self.logger.error(f"Error creating campaign: {str(e)}")
            raise
    
    def update_campaign(self, campaign_id: str, updates: Dict[str, any]) -> bool:
        """Update an existing LinkedIn ad campaign
        
        Args:
            campaign_id: ID of campaign to update
            updates: Dictionary of fields to update
            
        Returns:
            bool: True if update successful
        """
        try:
            response = self._make_request(
                endpoint=f"adCampaignsV2/{campaign_id}",
                method="PATCH",
                data=updates
            )
            
            return True
            
        except Exception as e:
            self.logger.error(f"Error updating campaign {campaign_id}: {str(e)}")
            return False
    
    def get_campaign_stats(self, campaign_id: str) -> Dict[str, any]:
        """Get campaign performance statistics
        
        Args:
            campaign_id: ID of campaign to get stats for
            
        Returns:
            Dictionary of campaign statistics
        """
        try:
            # Get campaign details
            campaign = self._make_request(
                endpoint=f"adCampaignsV2/{campaign_id}"
            )
            
            # Get campaign analytics
            start_date = (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d")
            end_date = datetime.now().strftime("%Y-%m-%d")
            
            analytics = self._make_request(
                endpoint="adAnalyticsV2",
                params={
                    "q": "analytics",
                    "pivot": "CAMPAIGN",
                    "dateRange.start.day": start_date,
                    "dateRange.end.day": end_date,
                    "campaigns[0]": f"urn:li:sponsoredCampaign:{campaign_id}",
                    "fields": (
                        "impressions,clicks,totalEngagements," +
                        "videoViews,likes,comments,shares,costInLocalCurrency," +
                        "conversionValueInLocalCurrency"
                    )
                }
            )
            
            # Combine campaign details with analytics
            stats = {
                "id": campaign["id"],
                "name": campaign["name"],
                "status": campaign["status"],
                "objective": campaign["objective"],
                "type": campaign["type"],
                "daily_budget": campaign["dailyBudget"],
                "metrics": analytics["elements"][0] if analytics["elements"] else {}
            }
            
            return stats
            
        except Exception as e:
            self.logger.error(f"Error getting campaign stats: {str(e)}")
            raise
    
    def create_ad(self, campaign_id: str, ad_data: Dict[str, any]) -> str:
        """Create a new ad in a campaign
        
        Args:
            campaign_id: ID of campaign to create ad in
            ad_data: Ad configuration including:
                - name: Ad name
                - type: Ad type
                - status: Ad status
                - creative: Creative configuration
                - targeting: Targeting criteria
                
        Returns:
            str: Created ad ID
        """
        try:
            # Create ad creative first
            creative_id = self._create_ad_creative(ad_data['creative'])
            
            # Create ad group
            ad_group_id = self._create_ad_group(
                campaign_id,
                ad_data,
                creative_id
            )
            
            return ad_group_id
            
        except Exception as e:
            self.logger.error(f"Error creating ad: {str(e)}")
            raise
    
    def update_ad(self, ad_id: str, updates: Dict[str, any]) -> bool:
        """Update an existing ad
        
        Args:
            ad_id: ID of ad to update
            updates: Dictionary of fields to update
            
        Returns:
            bool: True if update successful
        """
        try:
            response = self._make_request(
                endpoint=f"adGroupsV2/{ad_id}",
                method="PATCH",
                data=updates
            )
            
            return True
            
        except Exception as e:
            self.logger.error(f"Error updating ad {ad_id}: {str(e)}")
            return False
    
    def get_ad_stats(self, ad_id: str) -> Dict[str, any]:
        """Get ad performance statistics
        
        Args:
            ad_id: ID of ad to get stats for
            
        Returns:
            Dictionary of ad statistics
        """
        try:
            # Get ad details
            ad = self._make_request(
                endpoint=f"adGroupsV2/{ad_id}"
            )
            
            # Get ad analytics
            start_date = (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d")
            end_date = datetime.now().strftime("%Y-%m-%d")
            
            analytics = self._make_request(
                endpoint="adAnalyticsV2",
                params={
                    "q": "analytics",
                    "pivot": "CREATIVE",
                    "dateRange.start.day": start_date,
                    "dateRange.end.day": end_date,
                    "creatives[0]": ad["creatives"][0],
                    "fields": (
                        "impressions,clicks,totalEngagements," +
                        "videoViews,likes,comments,shares,costInLocalCurrency," +
                        "conversionValueInLocalCurrency"
                    )
                }
            )
            
            # Combine ad details with analytics
            stats = {
                "id": ad["id"],
                "name": ad["name"],
                "status": ad["status"],
                "type": ad["type"],
                "metrics": analytics["elements"][0] if analytics["elements"] else {}
            }
            
            return stats
            
        except Exception as e:
            self.logger.error(f"Error getting ad stats: {str(e)}")
            raise
    
    def _create_ad_creative(self, creative_data: Dict[str, any]) -> str:
        """Create an ad creative
        
        Args:
            creative_data: Creative configuration
            
        Returns:
            Created creative ID
        """
        try:
            data = {
                "account": f"urn:li:sponsoredAccount:{self.account_id}",
                "type": creative_data['type'],
                "name": creative_data['name'],
                "status": creative_data.get('status', 'ACTIVE')
            }
            
            # Add type-specific creative content
            if creative_data['type'] == 'SPONSORED_STATUS_UPDATE':
                data.update({
                    "content": {
                        "title": creative_data['content']['title'],
                        "description": creative_data['content']['description'],
                        "landingPage": creative_data['content']['landing_page']
                    }
                })
            elif creative_data['type'] == 'SPONSORED_VIDEO':
                data.update({
                    "content": {
                        "video": creative_data['content']['video_urn'],
                        "title": creative_data['content']['title'],
                        "description": creative_data['content']['description']
                    }
                })
            
            response = self._make_request(
                endpoint="adCreativesV2",
                method="POST",
                data=data
            )
            
            return response["id"]
            
        except Exception as e:
            self.logger.error(f"Error creating ad creative: {str(e)}")
            raise
    
    def _create_ad_group(self,
                        campaign_id: str,
                        ad_data: Dict[str, any],
                        creative_id: str) -> str:
        """Create an ad group
        
        Args:
            campaign_id: Campaign ID
            ad_data: Ad configuration data
            creative_id: Creative ID
            
        Returns:
            Created ad group ID
        """
        try:
            data = {
                "account": f"urn:li:sponsoredAccount:{self.account_id}",
                "campaign": f"urn:li:sponsoredCampaign:{campaign_id}",
                "creatives": [f"urn:li:sponsoredCreative:{creative_id}"],
                "name": ad_data['name'],
                "status": ad_data.get('status', 'ACTIVE'),
                "targeting": ad_data['targeting']
            }
            
            response = self._make_request(
                endpoint="adGroupsV2",
                method="POST",
                data=data
            )
            
            return response["id"]
            
        except Exception as e:
            self.logger.error(f"Error creating ad group: {str(e)}")
            raise