"""TikTok Ads Integration Module

This module implements the TikTok Ads API integration for managing
ad campaigns on the TikTok advertising platform.
"""

from typing import Dict, List, Optional, Union
import logging
from datetime import datetime
import requests
import json
from urllib.parse import urljoin

from .base import PlatformConnector

class TikTokAdsConnector(PlatformConnector):
    """TikTok Ads platform connector implementation"""
    
    BASE_URL = "https://business-api.tiktok.com/open_api/v1.3/"
    
    def __init__(self, config: Dict[str, any]):
        """Initialize TikTok Ads connector
        
        Args:
            config: Configuration dictionary containing:
                - access_token: TikTok Ads access token
                - advertiser_id: TikTok advertiser ID
                - app_id: TikTok app ID
                - secret: TikTok app secret
        """
        self.config = config
        self.logger = logging.getLogger(__name__)
        self._initialize_client()
    
    def _initialize_client(self):
        """Initialize TikTok Ads API client"""
        try:
            self.headers = {
                "Access-Token": self.config['access_token'],
                "Content-Type": "application/json"
            }
            self.advertiser_id = self.config['advertiser_id']
            
        except Exception as e:
            self.logger.error(f"Error initializing TikTok Ads client: {str(e)}")
            raise
    
    def _make_request(self,
                     endpoint: str,
                     method: str = "GET",
                     params: Dict = None,
                     data: Dict = None) -> Dict:
        """Make HTTP request to TikTok Ads API
        
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
        """Authenticate with TikTok Ads
        
        Returns:
            bool: True if authentication successful
        """
        try:
            # Test API connection by getting advertiser info
            response = self._make_request(
                endpoint="advertiser/info/",
                params={"advertiser_id": self.advertiser_id}
            )
            
            return response.get("code") == 0
            
        except Exception as e:
            self.logger.error(f"Authentication failed: {str(e)}")
            return False
    
    def create_campaign(self, campaign_data: Dict[str, any]) -> str:
        """Create a new TikTok ad campaign
        
        Args:
            campaign_data: Campaign configuration including:
                - name: Campaign name
                - objective_type: Campaign objective
                - budget_mode: Budget mode (BUDGET_MODE_DAY or BUDGET_MODE_TOTAL)
                - budget: Budget amount
                - status: Campaign status
                
        Returns:
            str: Created campaign ID
        """
        try:
            data = {
                "advertiser_id": self.advertiser_id,
                "campaign_name": campaign_data['name'],
                "objective_type": campaign_data['objective_type'],
                "budget_mode": campaign_data['budget_mode'],
                "budget": campaign_data['budget'],
                "status": campaign_data['status']
            }
            
            response = self._make_request(
                endpoint="campaign/create/",
                method="POST",
                data=data
            )
            
            if response.get("code") == 0:
                return response["data"]["campaign_id"]
            else:
                raise Exception(f"Failed to create campaign: {response.get('message')}")
            
        except Exception as e:
            self.logger.error(f"Error creating campaign: {str(e)}")
            raise
    
    def update_campaign(self, campaign_id: str, updates: Dict[str, any]) -> bool:
        """Update an existing TikTok ad campaign
        
        Args:
            campaign_id: ID of campaign to update
            updates: Dictionary of fields to update
            
        Returns:
            bool: True if update successful
        """
        try:
            data = {
                "advertiser_id": self.advertiser_id,
                "campaign_id": campaign_id,
                **updates
            }
            
            response = self._make_request(
                endpoint="campaign/update/",
                method="POST",
                data=data
            )
            
            return response.get("code") == 0
            
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
            params = {
                "advertiser_id": self.advertiser_id,
                "campaign_ids": [campaign_id],
                "fields": [
                    "campaign_id",
                    "campaign_name",
                    "objective_type",
                    "status",
                    "budget",
                    "budget_mode",
                    "spend",
                    "impressions",
                    "clicks",
                    "ctr",
                    "conversion",
                    "cost_per_conversion"
                ],
                "start_date": (
                    datetime.now() - timedelta(days=30)
                ).strftime("%Y-%m-%d"),
                "end_date": datetime.now().strftime("%Y-%m-%d")
            }
            
            response = self._make_request(
                endpoint="campaign/get/",
                params=params
            )
            
            if response.get("code") == 0 and response["data"]["list"]:
                return response["data"]["list"][0]
            else:
                raise Exception(f"Failed to get campaign stats: {response.get('message')}")
            
        except Exception as e:
            self.logger.error(f"Error getting campaign stats: {str(e)}")
            raise
    
    def create_ad(self, campaign_id: str, ad_data: Dict[str, any]) -> str:
        """Create a new ad in a campaign
        
        Args:
            campaign_id: ID of campaign to create ad in
            ad_data: Ad configuration including:
                - name: Ad name
                - status: Ad status
                - creative_info: Creative configuration
                - placements: Ad placement settings
                - targeting: Targeting criteria
                
        Returns:
            str: Created ad ID
        """
        try:
            # Create ad group first
            ad_group_id = self._create_ad_group(campaign_id, ad_data)
            
            # Create ad
            data = {
                "advertiser_id": self.advertiser_id,
                "ad_group_id": ad_group_id,
                "creative_info": ad_data['creative_info'],
                "status": ad_data.get('status', 'DISABLE')
            }
            
            response = self._make_request(
                endpoint="ad/create/",
                method="POST",
                data=data
            )
            
            if response.get("code") == 0:
                return response["data"]["ad_id"]
            else:
                raise Exception(f"Failed to create ad: {response.get('message')}")
            
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
            data = {
                "advertiser_id": self.advertiser_id,
                "ad_id": ad_id,
                **updates
            }
            
            response = self._make_request(
                endpoint="ad/update/",
                method="POST",
                data=data
            )
            
            return response.get("code") == 0
            
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
            params = {
                "advertiser_id": self.advertiser_id,
                "ad_ids": [ad_id],
                "fields": [
                    "ad_id",
                    "ad_name",
                    "status",
                    "spend",
                    "impressions",
                    "clicks",
                    "ctr",
                    "conversion",
                    "cost_per_conversion",
                    "engagement_rate",
                    "video_play_actions",
                    "video_watched_2s",
                    "video_watched_6s"
                ],
                "start_date": (
                    datetime.now() - timedelta(days=30)
                ).strftime("%Y-%m-%d"),
                "end_date": datetime.now().strftime("%Y-%m-%d")
            }
            
            response = self._make_request(
                endpoint="ad/get/",
                params=params
            )
            
            if response.get("code") == 0 and response["data"]["list"]:
                return response["data"]["list"][0]
            else:
                raise Exception(f"Failed to get ad stats: {response.get('message')}")
            
        except Exception as e:
            self.logger.error(f"Error getting ad stats: {str(e)}")
            raise
    
    def _create_ad_group(self, campaign_id: str, ad_data: Dict[str, any]) -> str:
        """Create an ad group for the ad
        
        Args:
            campaign_id: Campaign ID
            ad_data: Ad configuration data
            
        Returns:
            Created ad group ID
        """
        try:
            data = {
                "advertiser_id": self.advertiser_id,
                "campaign_id": campaign_id,
                "ad_group_name": f"{ad_data['name']} - Ad Group",
                "placement": ad_data['placements'],
                "audience": ad_data['targeting'],
                "budget": ad_data.get('budget', 0),
                "schedule_type": "SCHEDULE_FROM_NOW",
                "status": ad_data.get('status', 'DISABLE')
            }
            
            response = self._make_request(
                endpoint="ad_group/create/",
                method="POST",
                data=data
            )
            
            if response.get("code") == 0:
                return response["data"]["ad_group_id"]
            else:
                raise Exception(f"Failed to create ad group: {response.get('message')}")
            
        except Exception as e:
            self.logger.error(f"Error creating ad group: {str(e)}")
            raise