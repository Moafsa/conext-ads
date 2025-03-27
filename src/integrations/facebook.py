"""Facebook Ads Integration Module

This module implements the Facebook Ads API integration for managing
ad campaigns on the Facebook advertising platform.
"""

from typing import Dict, List, Optional, Union
import logging
from datetime import datetime
import facebook_business
from facebook_business.adobjects.adaccount import AdAccount
from facebook_business.adobjects.campaign import Campaign
from facebook_business.adobjects.ad import Ad
from facebook_business.adobjects.adset import AdSet
from facebook_business.api import FacebookAdsApi

from .base import PlatformConnector

class FacebookAdsConnector(PlatformConnector):
    """Facebook Ads platform connector implementation"""
    
    def __init__(self, config: Dict[str, any]):
        """Initialize Facebook Ads connector
        
        Args:
            config: Configuration dictionary containing:
                - app_id: Facebook App ID
                - app_secret: Facebook App Secret
                - access_token: Facebook Access Token
                - account_id: Facebook Ad Account ID
                - api_version: Facebook API Version
        """
        self.config = config
        self.logger = logging.getLogger(__name__)
        self._initialize_api()
        
    def _initialize_api(self):
        """Initialize Facebook Ads API client"""
        try:
            FacebookAdsApi.init(
                app_id=self.config['app_id'],
                app_secret=self.config['app_secret'],
                access_token=self.config['access_token'],
                api_version=self.config['api_version']
            )
            
            self.account = AdAccount(self.config['account_id'])
            
        except Exception as e:
            self.logger.error(f"Error initializing Facebook Ads API: {str(e)}")
            raise
    
    def authenticate(self) -> bool:
        """Authenticate with Facebook Ads
        
        Returns:
            bool: True if authentication successful
        """
        try:
            # Test API connection by getting account details
            self.account.api_get(fields=['name', 'account_status'])
            return True
            
        except Exception as e:
            self.logger.error(f"Authentication failed: {str(e)}")
            return False
    
    def create_campaign(self, campaign_data: Dict[str, any]) -> str:
        """Create a new Facebook ad campaign
        
        Args:
            campaign_data: Campaign configuration including:
                - name: Campaign name
                - objective: Campaign objective
                - status: Campaign status
                - special_ad_categories: Special ad category list
                - bid_strategy: Bidding strategy
                - daily_budget: Daily budget amount
                
        Returns:
            str: Created campaign ID
        """
        try:
            # Create campaign
            campaign = self.account.create_campaign(
                params={
                    'name': campaign_data['name'],
                    'objective': campaign_data['objective'],
                    'status': campaign_data['status'],
                    'special_ad_categories': campaign_data.get('special_ad_categories', []),
                    'bid_strategy': campaign_data.get('bid_strategy', 'LOWEST_COST_WITHOUT_CAP'),
                    'daily_budget': campaign_data.get('daily_budget', 0)
                }
            )
            
            return campaign['id']
            
        except Exception as e:
            self.logger.error(f"Error creating campaign: {str(e)}")
            raise
    
    def update_campaign(self, campaign_id: str, updates: Dict[str, any]) -> bool:
        """Update an existing Facebook ad campaign
        
        Args:
            campaign_id: ID of campaign to update
            updates: Dictionary of fields to update
            
        Returns:
            bool: True if update successful
        """
        try:
            campaign = Campaign(campaign_id)
            campaign.api_update(
                fields=[],
                params=updates
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
            campaign = Campaign(campaign_id)
            stats = campaign.api_get(
                fields=[
                    'name',
                    'objective',
                    'status',
                    'daily_budget',
                    'lifetime_budget',
                    'insights.date_preset(last_30d){' +
                    'impressions,reach,clicks,spend,cpc,ctr' +
                    '}'
                ]
            )
            
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
                - creative: Ad creative details
                - targeting: Ad targeting criteria
                - optimization_goal: Optimization goal
                - billing_event: Billing event type
                - bid_amount: Bid amount
                
        Returns:
            str: Created ad ID
        """
        try:
            # Create ad set first
            ad_set = self._create_ad_set(campaign_id, ad_data)
            
            # Create ad
            ad = ad_set.create_ad(
                params={
                    'name': ad_data['name'],
                    'creative': ad_data['creative'],
                    'status': ad_data.get('status', 'PAUSED')
                }
            )
            
            return ad['id']
            
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
            ad = Ad(ad_id)
            ad.api_update(
                fields=[],
                params=updates
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
            ad = Ad(ad_id)
            stats = ad.api_get(
                fields=[
                    'name',
                    'status',
                    'insights.date_preset(last_30d){' +
                    'impressions,reach,clicks,spend,cpc,ctr,' +
                    'actions,action_values' +
                    '}'
                ]
            )
            
            return stats
            
        except Exception as e:
            self.logger.error(f"Error getting ad stats: {str(e)}")
            raise
    
    def _create_ad_set(self, campaign_id: str, ad_data: Dict[str, any]) -> AdSet:
        """Create an ad set for the ad
        
        Args:
            campaign_id: Campaign ID
            ad_data: Ad configuration data
            
        Returns:
            Created AdSet object
        """
        try:
            ad_set = self.account.create_ad_set(
                params={
                    'campaign_id': campaign_id,
                    'name': f"{ad_data['name']} - Ad Set",
                    'optimization_goal': ad_data['optimization_goal'],
                    'billing_event': ad_data['billing_event'],
                    'bid_amount': ad_data['bid_amount'],
                    'targeting': ad_data['targeting'],
                    'status': ad_data.get('status', 'PAUSED'),
                    'daily_budget': ad_data.get('daily_budget', 0)
                }
            )
            
            return AdSet(ad_set['id'])
            
        except Exception as e:
            self.logger.error(f"Error creating ad set: {str(e)}")
            raise