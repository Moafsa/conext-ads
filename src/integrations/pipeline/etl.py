"""ETL Module

This module implements Extract, Transform, Load processes for
handling ad campaign data across different platforms.
"""

from typing import Dict, List, Optional, Union
import logging
from datetime import datetime
import pandas as pd
import numpy as np
from sqlalchemy import create_engine
from concurrent.futures import ThreadPoolExecutor
import json

from . import DataSource, DataTransformer, DataLoader

class AdPlatformDataSource(DataSource):
    """Data source for ad platform data"""
    
    def __init__(self, platform_connector: any, config: Dict[str, any]):
        """Initialize ad platform data source
        
        Args:
            platform_connector: Platform connector instance
            config: Configuration dictionary
        """
        self.connector = platform_connector
        self.config = config
        self.logger = logging.getLogger(__name__)
    
    def connect(self) -> bool:
        """Connect to ad platform
        
        Returns:
            bool: True if connection successful
        """
        try:
            return self.connector.authenticate()
        except Exception as e:
            self.logger.error(f"Failed to connect to platform: {str(e)}")
            return False
    
    def extract_data(self, query: str) -> List[Dict[str, any]]:
        """Extract data from ad platform
        
        Args:
            query: Query parameters for data extraction
            
        Returns:
            List of extracted data records
        """
        try:
            params = json.loads(query)
            data = []
            
            # Extract campaign data
            if params.get('campaigns'):
                campaigns = self._extract_campaigns(params['date_range'])
                data.extend(campaigns)
            
            # Extract ad data
            if params.get('ads'):
                ads = self._extract_ads(params['date_range'])
                data.extend(ads)
            
            return data
            
        except Exception as e:
            self.logger.error(f"Data extraction failed: {str(e)}")
            raise
    
    def validate_data(self, data: List[Dict[str, any]]) -> bool:
        """Validate extracted data
        
        Args:
            data: Extracted data to validate
            
        Returns:
            bool: True if data is valid
        """
        try:
            required_fields = ['id', 'name', 'status', 'platform']
            
            for record in data:
                if not all(field in record for field in required_fields):
                    return False
                
                if not isinstance(record['id'], str):
                    return False
            
            return True
            
        except Exception as e:
            self.logger.error(f"Data validation failed: {str(e)}")
            return False
    
    def _extract_campaigns(self, date_range: Dict[str, str]) -> List[Dict[str, any]]:
        """Extract campaign data
        
        Args:
            date_range: Date range for data extraction
            
        Returns:
            List of campaign data records
        """
        try:
            # Get active campaigns
            campaigns = self.connector.get_campaigns()
            
            # Get stats for each campaign
            with ThreadPoolExecutor() as executor:
                stats = list(executor.map(
                    self.connector.get_campaign_stats,
                    [c['id'] for c in campaigns]
                ))
            
            # Combine campaign data with stats
            for campaign, stat in zip(campaigns, stats):
                campaign.update(stat)
                campaign['platform'] = self.config['platform_name']
            
            return campaigns
            
        except Exception as e:
            self.logger.error(f"Campaign data extraction failed: {str(e)}")
            raise
    
    def _extract_ads(self, date_range: Dict[str, str]) -> List[Dict[str, any]]:
        """Extract ad data
        
        Args:
            date_range: Date range for data extraction
            
        Returns:
            List of ad data records
        """
        try:
            # Get active ads
            ads = self.connector.get_ads()
            
            # Get stats for each ad
            with ThreadPoolExecutor() as executor:
                stats = list(executor.map(
                    self.connector.get_ad_stats,
                    [a['id'] for a in ads]
                ))
            
            # Combine ad data with stats
            for ad, stat in zip(ads, stats):
                ad.update(stat)
                ad['platform'] = self.config['platform_name']
            
            return ads
            
        except Exception as e:
            self.logger.error(f"Ad data extraction failed: {str(e)}")
            raise

class AdDataTransformer(DataTransformer):
    """Transformer for ad platform data"""
    
    def __init__(self, config: Dict[str, any]):
        """Initialize ad data transformer
        
        Args:
            config: Configuration dictionary
        """
        self.config = config
        self.logger = logging.getLogger(__name__)
    
    def transform(self, data: List[Dict[str, any]]) -> List[Dict[str, any]]:
        """Transform ad platform data
        
        Args:
            data: Raw data to transform
            
        Returns:
            List of transformed data records
        """
        try:
            # Convert to DataFrame for easier manipulation
            df = pd.DataFrame(data)
            
            # Clean data
            df = self.clean_data(df)
            
            # Normalize metrics
            df = self._normalize_metrics(df)
            
            # Add derived metrics
            df = self._add_derived_metrics(df)
            
            # Convert back to records
            return df.to_dict('records')
            
        except Exception as e:
            self.logger.error(f"Data transformation failed: {str(e)}")
            raise
    
    def validate_schema(self, data: List[Dict[str, any]]) -> bool:
        """Validate data schema
        
        Args:
            data: Data to validate
            
        Returns:
            bool: True if schema is valid
        """
        try:
            df = pd.DataFrame(data)
            
            # Check required columns
            required_columns = [
                'id', 'name', 'status', 'platform',
                'impressions', 'clicks', 'spend'
            ]
            
            if not all(col in df.columns for col in required_columns):
                return False
            
            # Check data types
            if not (
                df['impressions'].dtype in ['int64', 'float64'] and
                df['clicks'].dtype in ['int64', 'float64'] and
                df['spend'].dtype in ['float64']
            ):
                return False
            
            return True
            
        except Exception as e:
            self.logger.error(f"Schema validation failed: {str(e)}")
            return False
    
    def clean_data(self, data: Union[pd.DataFrame, List[Dict[str, any]]]) -> pd.DataFrame:
        """Clean and prepare data
        
        Args:
            data: Data to clean
            
        Returns:
            Cleaned DataFrame
        """
        try:
            # Convert to DataFrame if needed
            if isinstance(data, list):
                df = pd.DataFrame(data)
            else:
                df = data.copy()
            
            # Remove duplicates
            df = df.drop_duplicates(subset=['id'])
            
            # Handle missing values
            numeric_cols = df.select_dtypes(include=[np.number]).columns
            df[numeric_cols] = df[numeric_cols].fillna(0)
            
            # Convert date columns
            date_cols = [col for col in df.columns if 'date' in col.lower()]
            for col in date_cols:
                df[col] = pd.to_datetime(df[col])
            
            return df
            
        except Exception as e:
            self.logger.error(f"Data cleaning failed: {str(e)}")
            raise
    
    def _normalize_metrics(self, df: pd.DataFrame) -> pd.DataFrame:
        """Normalize metrics across platforms
        
        Args:
            df: DataFrame to normalize
            
        Returns:
            Normalized DataFrame
        """
        try:
            # Standardize metric names
            metric_mapping = {
                'total_impressions': 'impressions',
                'total_clicks': 'clicks',
                'total_spend': 'spend',
                'total_conversions': 'conversions'
            }
            
            df = df.rename(columns=metric_mapping)
            
            # Convert currency to standard (USD)
            if 'currency' in df.columns:
                df = self._convert_currency(df)
            
            return df
            
        except Exception as e:
            self.logger.error(f"Metric normalization failed: {str(e)}")
            raise
    
    def _add_derived_metrics(self, df: pd.DataFrame) -> pd.DataFrame:
        """Add derived performance metrics
        
        Args:
            df: DataFrame to enhance
            
        Returns:
            Enhanced DataFrame
        """
        try:
            # Calculate CTR
            df['ctr'] = (df['clicks'] / df['impressions']).fillna(0)
            
            # Calculate CPC
            df['cpc'] = (df['spend'] / df['clicks']).fillna(0)
            
            # Calculate CPM
            df['cpm'] = (df['spend'] / df['impressions'] * 1000).fillna(0)
            
            # Calculate conversion rate if possible
            if 'conversions' in df.columns:
                df['conversion_rate'] = (
                    df['conversions'] / df['clicks']
                ).fillna(0)
            
            return df
            
        except Exception as e:
            self.logger.error(f"Adding derived metrics failed: {str(e)}")
            raise
    
    def _convert_currency(self, df: pd.DataFrame) -> pd.DataFrame:
        """Convert currency to USD
        
        Args:
            df: DataFrame with spend data
            
        Returns:
            DataFrame with standardized currency
        """
        try:
            # Get exchange rates
            exchange_rates = self._get_exchange_rates()
            
            # Convert spend to USD
            df['spend'] = df.apply(
                lambda row: row['spend'] * exchange_rates.get(
                    row['currency'], 1
                ),
                axis=1
            )
            
            # Update currency column
            df['currency'] = 'USD'
            
            return df
            
        except Exception as e:
            self.logger.error(f"Currency conversion failed: {str(e)}")
            raise
    
    def _get_exchange_rates(self) -> Dict[str, float]:
        """Get current exchange rates
        
        Returns:
            Dictionary of exchange rates
        """
        # TODO: Implement exchange rate fetching
        return {'USD': 1.0, 'EUR': 1.1, 'GBP': 1.3}

class WarehouseLoader(DataLoader):
    """Data loader for data warehouse"""
    
    def __init__(self, config: Dict[str, any]):
        """Initialize warehouse loader
        
        Args:
            config: Configuration dictionary containing:
                - connection_string: Database connection string
                - schema: Database schema
                - table_prefix: Table name prefix
        """
        self.config = config
        self.logger = logging.getLogger(__name__)
        self.engine = None
    
    def connect(self) -> bool:
        """Connect to data warehouse
        
        Returns:
            bool: True if connection successful
        """
        try:
            self.engine = create_engine(self.config['connection_string'])
            return True
            
        except Exception as e:
            self.logger.error(f"Warehouse connection failed: {str(e)}")
            return False
    
    def load_data(self, data: List[Dict[str, any]]) -> bool:
        """Load data to warehouse
        
        Args:
            data: Data to load
            
        Returns:
            bool: True if load successful
        """
        try:
            df = pd.DataFrame(data)
            
            # Determine table name based on data type
            table_name = self._get_table_name(df)
            
            # Load data
            df.to_sql(
                name=table_name,
                con=self.engine,
                schema=self.config['schema'],
                if_exists='append',
                index=False
            )
            
            return True
            
        except Exception as e:
            self.logger.error(f"Data loading failed: {str(e)}")
            return False
    
    def validate_load(self, data: List[Dict[str, any]]) -> bool:
        """Validate loaded data
        
        Args:
            data: Loaded data to validate
            
        Returns:
            bool: True if validation successful
        """
        try:
            df = pd.DataFrame(data)
            table_name = self._get_table_name(df)
            
            # Query loaded data
            query = f"""
                SELECT COUNT(*)
                FROM {self.config['schema']}.{table_name}
                WHERE id IN %(ids)s
            """
            
            result = pd.read_sql(
                query,
                self.engine,
                params={'ids': tuple(df['id'].tolist())}
            )
            
            return result.iloc[0, 0] == len(df)
            
        except Exception as e:
            self.logger.error(f"Load validation failed: {str(e)}")
            return False
    
    def _get_table_name(self, df: pd.DataFrame) -> str:
        """Determine target table name
        
        Args:
            df: DataFrame to analyze
            
        Returns:
            Target table name
        """
        # Check data type based on columns
        if 'campaign_id' in df.columns:
            return f"{self.config['table_prefix']}_ads"
        else:
            return f"{self.config['table_prefix']}_campaigns"