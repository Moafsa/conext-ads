"""Google Ads Integration Module

This module implements the Google Ads API integration for managing
ad campaigns on the Google Ads platform.
"""

from typing import Dict, List, Optional, Union
import logging
from datetime import datetime
from google.ads.googleads.client import GoogleAdsClient
from google.ads.googleads.errors import GoogleAdsException
from google.api_core import protobuf_helpers

from .base import PlatformConnector

class GoogleAdsConnector(PlatformConnector):
    """Google Ads platform connector implementation"""
    
    def __init__(self, config: Dict[str, any]):
        """Initialize Google Ads connector
        
        Args:
            config: Configuration dictionary containing:
                - client_id: OAuth2 client ID
                - client_secret: OAuth2 client secret
                - refresh_token: OAuth2 refresh token
                - developer_token: Google Ads developer token
                - customer_id: Google Ads customer ID
                - login_customer_id: Manager account ID (optional)
        """
        self.config = config
        self.logger = logging.getLogger(__name__)
        self._initialize_client()
    
    def _initialize_client(self):
        """Initialize Google Ads API client"""
        try:
            self.client = GoogleAdsClient.load_from_dict({
                'client_id': self.config['client_id'],
                'client_secret': self.config['client_secret'],
                'refresh_token': self.config['refresh_token'],
                'developer_token': self.config['developer_token'],
                'login_customer_id': self.config.get('login_customer_id'),
                'use_proto_plus': True
            })
            
            self.customer_id = self.config['customer_id']
            
        except Exception as e:
            self.logger.error(f"Error initializing Google Ads client: {str(e)}")
            raise
    
    def authenticate(self) -> bool:
        """Authenticate with Google Ads
        
        Returns:
            bool: True if authentication successful
        """
        try:
            # Test API connection by getting account info
            ga_service = self.client.get_service("GoogleAdsService")
            query = """
                SELECT
                    customer.id,
                    customer.descriptive_name,
                    customer.currency_code
                FROM customer
                LIMIT 1
            """
            
            response = ga_service.search(
                customer_id=self.customer_id,
                query=query
            )
            
            for row in response:
                if row.customer.id == self.customer_id:
                    return True
            return False
            
        except GoogleAdsException as e:
            self.logger.error(f"Authentication failed: {str(e)}")
            return False
    
    def create_campaign(self, campaign_data: Dict[str, any]) -> str:
        """Create a new Google Ads campaign
        
        Args:
            campaign_data: Campaign configuration including:
                - name: Campaign name
                - budget_amount: Daily budget amount
                - advertising_channel_type: Channel type
                - status: Campaign status
                - bidding_strategy: Bidding strategy configuration
                
        Returns:
            str: Created campaign ID
        """
        try:
            # Create campaign budget
            campaign_budget_service = self.client.get_service("CampaignBudgetService")
            campaign_budget_operation = self.client.get_type("CampaignBudgetOperation")
            campaign_budget = campaign_budget_operation.create
            
            campaign_budget.name = f"{campaign_data['name']} Budget"
            campaign_budget.amount_micros = int(campaign_data['budget_amount'] * 1000000)
            campaign_budget.delivery_method = (
                self.client.enums.BudgetDeliveryMethodEnum.STANDARD
            )
            
            # Add campaign budget
            campaign_budget_response = campaign_budget_service.mutate_campaign_budgets(
                customer_id=self.customer_id,
                operations=[campaign_budget_operation]
            )
            
            # Create campaign
            campaign_service = self.client.get_service("CampaignService")
            campaign_operation = self.client.get_type("CampaignOperation")
            campaign = campaign_operation.create
            
            # Set campaign properties
            campaign.name = campaign_data['name']
            campaign.advertising_channel_type = (
                self.client.enums.AdvertisingChannelTypeEnum[
                    campaign_data['advertising_channel_type']
                ]
            )
            campaign.status = self.client.enums.CampaignStatusEnum[
                campaign_data['status']
            ]
            campaign.campaign_budget = campaign_budget_response.results[0].resource_name
            
            # Set bidding strategy
            if campaign_data['bidding_strategy']['type'] == 'MAXIMIZE_CONVERSIONS':
                campaign.maximize_conversions = self.client.get_type(
                    "MaximizeConversions"
                )
            elif campaign_data['bidding_strategy']['type'] == 'TARGET_CPA':
                campaign.target_cpa = self.client.get_type("TargetCpa")
                campaign.target_cpa.target_cpa_micros = int(
                    campaign_data['bidding_strategy']['target_cpa'] * 1000000
                )
            
            # Add campaign
            campaign_response = campaign_service.mutate_campaigns(
                customer_id=self.customer_id,
                operations=[campaign_operation]
            )
            
            return campaign_response.results[0].resource_name.split('/')[-1]
            
        except GoogleAdsException as e:
            self.logger.error(f"Error creating campaign: {str(e)}")
            raise
    
    def update_campaign(self, campaign_id: str, updates: Dict[str, any]) -> bool:
        """Update an existing Google Ads campaign
        
        Args:
            campaign_id: ID of campaign to update
            updates: Dictionary of fields to update
            
        Returns:
            bool: True if update successful
        """
        try:
            campaign_service = self.client.get_service("CampaignService")
            campaign_operation = self.client.get_type("CampaignOperation")
            
            campaign = campaign_operation.update
            campaign.resource_name = (
                f"customers/{self.customer_id}/campaigns/{campaign_id}"
            )
            
            # Apply updates
            for field, value in updates.items():
                if field in ['name', 'status']:
                    setattr(campaign, field, value)
                elif field == 'budget_amount':
                    self._update_campaign_budget(campaign.campaign_budget, value)
            
            # Set field mask
            client = self.client
            field_mask = protobuf_helpers.field_mask(None, campaign._pb)
            campaign_operation.update_mask.CopyFrom(field_mask)
            
            # Update campaign
            response = campaign_service.mutate_campaigns(
                customer_id=self.customer_id,
                operations=[campaign_operation]
            )
            
            return True
            
        except GoogleAdsException as e:
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
            ga_service = self.client.get_service("GoogleAdsService")
            query = f"""
                SELECT
                    campaign.id,
                    campaign.name,
                    campaign.status,
                    metrics.impressions,
                    metrics.clicks,
                    metrics.cost_micros,
                    metrics.conversions,
                    metrics.average_cpc
                FROM campaign
                WHERE campaign.id = {campaign_id}
                AND segments.date DURING LAST_30_DAYS
            """
            
            response = ga_service.search(
                customer_id=self.customer_id,
                query=query
            )
            
            stats = {}
            for row in response:
                campaign = row.campaign
                metrics = row.metrics
                
                stats = {
                    'id': campaign.id,
                    'name': campaign.name,
                    'status': campaign.status.name,
                    'impressions': metrics.impressions,
                    'clicks': metrics.clicks,
                    'cost': metrics.cost_micros / 1000000,
                    'conversions': metrics.conversions,
                    'average_cpc': metrics.average_cpc.value / 1000000
                }
            
            return stats
            
        except GoogleAdsException as e:
            self.logger.error(f"Error getting campaign stats: {str(e)}")
            raise
    
    def create_ad(self, campaign_id: str, ad_data: Dict[str, any]) -> str:
        """Create a new ad in a campaign
        
        Args:
            campaign_id: ID of campaign to create ad in
            ad_data: Ad configuration including:
                - name: Ad name
                - type: Ad type (RESPONSIVE_SEARCH, RESPONSIVE_DISPLAY, etc.)
                - headlines: List of headlines
                - descriptions: List of descriptions
                - final_urls: Landing page URLs
                
        Returns:
            str: Created ad ID
        """
        try:
            # Create ad group first
            ad_group_id = self._create_ad_group(campaign_id, ad_data)
            
            # Create ad
            ad_group_ad_service = self.client.get_service("AdGroupAdService")
            ad_group_ad_operation = self.client.get_type("AdGroupAdOperation")
            
            ad_group_ad = ad_group_ad_operation.create
            ad_group_ad.ad_group = f"customers/{self.customer_id}/adGroups/{ad_group_id}"
            
            # Set ad properties based on type
            if ad_data['type'] == 'RESPONSIVE_SEARCH':
                ad = self._create_responsive_search_ad(ad_data)
            elif ad_data['type'] == 'RESPONSIVE_DISPLAY':
                ad = self._create_responsive_display_ad(ad_data)
            
            ad_group_ad.ad = ad
            
            # Add ad
            response = ad_group_ad_service.mutate_ad_group_ads(
                customer_id=self.customer_id,
                operations=[ad_group_ad_operation]
            )
            
            return response.results[0].resource_name.split('/')[-1]
            
        except GoogleAdsException as e:
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
            ad_group_ad_service = self.client.get_service("AdGroupAdService")
            ad_group_ad_operation = self.client.get_type("AdGroupAdOperation")
            
            ad_group_ad = ad_group_ad_operation.update
            ad_group_ad.resource_name = (
                f"customers/{self.customer_id}/adGroupAds/{ad_id}"
            )
            
            # Apply updates
            for field, value in updates.items():
                if field in ['status']:
                    setattr(ad_group_ad, field, value)
            
            # Set field mask
            client = self.client
            field_mask = protobuf_helpers.field_mask(None, ad_group_ad._pb)
            ad_group_ad_operation.update_mask.CopyFrom(field_mask)
            
            # Update ad
            response = ad_group_ad_service.mutate_ad_group_ads(
                customer_id=self.customer_id,
                operations=[ad_group_ad_operation]
            )
            
            return True
            
        except GoogleAdsException as e:
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
            ga_service = self.client.get_service("GoogleAdsService")
            query = f"""
                SELECT
                    ad_group_ad.ad.id,
                    ad_group_ad.ad.name,
                    ad_group_ad.status,
                    metrics.impressions,
                    metrics.clicks,
                    metrics.cost_micros,
                    metrics.conversions,
                    metrics.average_cpc
                FROM ad_group_ad
                WHERE ad_group_ad.ad.id = {ad_id}
                AND segments.date DURING LAST_30_DAYS
            """
            
            response = ga_service.search(
                customer_id=self.customer_id,
                query=query
            )
            
            stats = {}
            for row in response:
                ad = row.ad_group_ad.ad
                metrics = row.metrics
                
                stats = {
                    'id': ad.id,
                    'name': ad.name,
                    'status': row.ad_group_ad.status.name,
                    'impressions': metrics.impressions,
                    'clicks': metrics.clicks,
                    'cost': metrics.cost_micros / 1000000,
                    'conversions': metrics.conversions,
                    'average_cpc': metrics.average_cpc.value / 1000000
                }
            
            return stats
            
        except GoogleAdsException as e:
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
            ad_group_service = self.client.get_service("AdGroupService")
            ad_group_operation = self.client.get_type("AdGroupOperation")
            
            ad_group = ad_group_operation.create
            ad_group.name = f"{ad_data['name']} - Ad Group"
            ad_group.campaign = f"customers/{self.customer_id}/campaigns/{campaign_id}"
            ad_group.type_ = self.client.enums.AdGroupTypeEnum.SEARCH_STANDARD
            ad_group.status = self.client.enums.AdGroupStatusEnum.ENABLED
            
            # Add ad group
            response = ad_group_service.mutate_ad_groups(
                customer_id=self.customer_id,
                operations=[ad_group_operation]
            )
            
            return response.results[0].resource_name.split('/')[-1]
            
        except GoogleAdsException as e:
            self.logger.error(f"Error creating ad group: {str(e)}")
            raise
    
    def _create_responsive_search_ad(self, ad_data: Dict[str, any]):
        """Create a responsive search ad
        
        Args:
            ad_data: Ad configuration data
            
        Returns:
            Configured responsive search ad
        """
        ad = self.client.get_type("Ad")
        ad.responsive_search_ad.headlines.extend([
            self._create_ad_text_asset(headline)
            for headline in ad_data['headlines']
        ])
        ad.responsive_search_ad.descriptions.extend([
            self._create_ad_text_asset(description)
            for description in ad_data['descriptions']
        ])
        ad.final_urls.extend(ad_data['final_urls'])
        
        return ad
    
    def _create_responsive_display_ad(self, ad_data: Dict[str, any]):
        """Create a responsive display ad
        
        Args:
            ad_data: Ad configuration data
            
        Returns:
            Configured responsive display ad
        """
        ad = self.client.get_type("Ad")
        ad.responsive_display_ad.headlines.extend([
            self._create_ad_text_asset(headline)
            for headline in ad_data['headlines']
        ])
        ad.responsive_display_ad.descriptions.extend([
            self._create_ad_text_asset(description)
            for description in ad_data['descriptions']
        ])
        ad.responsive_display_ad.marketing_images.extend([
            self._create_ad_image_asset(image)
            for image in ad_data['marketing_images']
        ])
        ad.final_urls.extend(ad_data['final_urls'])
        
        return ad
    
    def _create_ad_text_asset(self, text: str):
        """Create an ad text asset
        
        Args:
            text: Asset text
            
        Returns:
            Configured ad text asset
        """
        asset = self.client.get_type("AdTextAsset")
        asset.text = text
        return asset
    
    def _create_ad_image_asset(self, image_data: Dict[str, any]):
        """Create an ad image asset
        
        Args:
            image_data: Image configuration data
            
        Returns:
            Configured ad image asset
        """
        asset = self.client.get_type("AdImageAsset")
        asset.asset = image_data['asset']
        return asset
    
    def _update_campaign_budget(self, budget_resource_name: str, amount: float):
        """Update campaign budget
        
        Args:
            budget_resource_name: Budget resource name
            amount: New budget amount
        """
        try:
            campaign_budget_service = self.client.get_service("CampaignBudgetService")
            campaign_budget_operation = self.client.get_type("CampaignBudgetOperation")
            
            campaign_budget = campaign_budget_operation.update
            campaign_budget.resource_name = budget_resource_name
            campaign_budget.amount_micros = int(amount * 1000000)
            
            field_mask = protobuf_helpers.field_mask(None, campaign_budget._pb)
            campaign_budget_operation.update_mask.CopyFrom(field_mask)
            
            campaign_budget_service.mutate_campaign_budgets(
                customer_id=self.customer_id,
                operations=[campaign_budget_operation]
            )
            
        except GoogleAdsException as e:
            self.logger.error(f"Error updating campaign budget: {str(e)}")
            raise