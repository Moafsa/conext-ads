"""Pipeline Configuration Module

This module manages configuration for the data pipeline,
including environment-specific settings and validation.
"""

from typing import Dict, Any, Optional
import os
import json
import yaml
from pathlib import Path
import logging
from dataclasses import dataclass
from marshmallow import Schema, fields, validate, EXCLUDE

@dataclass
class DatabaseConfig:
    """Database configuration"""
    host: str
    port: int
    database: str
    username: str
    password: str
    schema: str
    
    @property
    def connection_string(self) -> str:
        """Get database connection string
        
        Returns:
            Database connection URL
        """
        return (
            f"postgresql://{self.username}:{self.password}"
            f"@{self.host}:{self.port}/{self.database}"
        )

@dataclass
class KafkaConfig:
    """Kafka configuration"""
    bootstrap_servers: str
    schema_registry_url: str
    consumer_group: str
    topics: list[str]
    security_protocol: str = "PLAINTEXT"
    sasl_mechanism: Optional[str] = None
    sasl_username: Optional[str] = None
    sasl_password: Optional[str] = None

@dataclass
class WebhookConfig:
    """Webhook configuration"""
    webhook_url: str
    auth_token: str
    retry_attempts: int = 3
    retry_delay: int = 5

class DatabaseConfigSchema(Schema):
    """Schema for database configuration"""
    host = fields.Str(required=True)
    port = fields.Int(required=True, validate=validate.Range(min=1, max=65535))
    database = fields.Str(required=True)
    username = fields.Str(required=True)
    password = fields.Str(required=True)
    schema = fields.Str(required=True)
    
    class Meta:
        unknown = EXCLUDE

class KafkaConfigSchema(Schema):
    """Schema for Kafka configuration"""
    bootstrap_servers = fields.Str(required=True)
    schema_registry_url = fields.Str(required=True)
    consumer_group = fields.Str(required=True)
    topics = fields.List(fields.Str(), required=True)
    security_protocol = fields.Str(
        validate=validate.OneOf(["PLAINTEXT", "SASL_SSL"]),
        default="PLAINTEXT"
    )
    sasl_mechanism = fields.Str(allow_none=True)
    sasl_username = fields.Str(allow_none=True)
    sasl_password = fields.Str(allow_none=True)
    
    class Meta:
        unknown = EXCLUDE

class WebhookConfigSchema(Schema):
    """Schema for webhook configuration"""
    webhook_url = fields.Str(required=True)
    auth_token = fields.Str(required=True)
    retry_attempts = fields.Int(validate=validate.Range(min=1), default=3)
    retry_delay = fields.Int(validate=validate.Range(min=1), default=5)
    
    class Meta:
        unknown = EXCLUDE

class PipelineConfig:
    """Pipeline configuration manager"""
    
    def __init__(
        self,
        config_path: Optional[str] = None,
        env: Optional[str] = None
    ):
        """Initialize pipeline configuration
        
        Args:
            config_path: Path to config file/directory
            env: Environment name (dev/test/prod)
        """
        self.logger = logging.getLogger(__name__)
        self.config_path = config_path or os.getenv(
            'PIPELINE_CONFIG_PATH',
            'config'
        )
        self.env = env or os.getenv('ENV', 'dev')
        self.config: Dict[str, Any] = {}
        
        # Load and validate configuration
        self._load_config()
    
    def get_database_config(self) -> DatabaseConfig:
        """Get database configuration
        
        Returns:
            Database configuration object
        """
        schema = DatabaseConfigSchema()
        config_dict = self.config.get('database', {})
        validated = schema.load(config_dict)
        return DatabaseConfig(**validated)
    
    def get_kafka_config(self) -> KafkaConfig:
        """Get Kafka configuration
        
        Returns:
            Kafka configuration object
        """
        schema = KafkaConfigSchema()
        config_dict = self.config.get('kafka', {})
        validated = schema.load(config_dict)
        return KafkaConfig(**validated)
    
    def get_webhook_config(self) -> WebhookConfig:
        """Get webhook configuration
        
        Returns:
            Webhook configuration object
        """
        schema = WebhookConfigSchema()
        config_dict = self.config.get('webhook', {})
        validated = schema.load(config_dict)
        return WebhookConfig(**validated)
    
    def _load_config(self) -> None:
        """Load configuration from file/environment"""
        try:
            # Load base config
            base_config = self._load_config_file('base')
            
            # Load environment config
            env_config = self._load_config_file(self.env)
            
            # Merge configurations
            self.config = self._merge_configs(base_config, env_config)
            
            # Override with environment variables
            self._override_from_env()
            
        except Exception as e:
            self.logger.error(f"Failed to load configuration: {str(e)}")
            raise
    
    def _load_config_file(self, name: str) -> Dict[str, Any]:
        """Load configuration file
        
        Args:
            name: Configuration name/environment
            
        Returns:
            Configuration dictionary
        """
        config_file = Path(self.config_path) / f"{name}.yml"
        
        if not config_file.exists():
            self.logger.warning(f"Config file not found: {config_file}")
            return {}
        
        try:
            with open(config_file) as f:
                return yaml.safe_load(f)
                
        except Exception as e:
            self.logger.error(f"Failed to load {name} config: {str(e)}")
            return {}
    
    def _merge_configs(
        self,
        base: Dict[str, Any],
        override: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Merge configuration dictionaries
        
        Args:
            base: Base configuration
            override: Override configuration
            
        Returns:
            Merged configuration
        """
        result = base.copy()
        
        for key, value in override.items():
            if (
                key in result and
                isinstance(result[key], dict) and
                isinstance(value, dict)
            ):
                result[key] = self._merge_configs(result[key], value)
            else:
                result[key] = value
        
        return result
    
    def _override_from_env(self) -> None:
        """Override configuration with environment variables"""
        prefix = 'PIPELINE_'
        
        for key, value in os.environ.items():
            if not key.startswith(prefix):
                continue
            
            # Convert environment variable to config path
            config_path = key[len(prefix):].lower().split('_')
            
            # Update config value
            current = self.config
            for part in config_path[:-1]:
                current = current.setdefault(part, {})
            
            try:
                # Try to parse as JSON for complex values
                current[config_path[-1]] = json.loads(value)
            except json.JSONDecodeError:
                # Use raw string if not valid JSON
                current[config_path[-1]] = value

def create_config(
    config_path: Optional[str] = None,
    env: Optional[str] = None
) -> PipelineConfig:
    """Create pipeline configuration
    
    Args:
        config_path: Path to config file/directory
        env: Environment name
        
    Returns:
        Pipeline configuration object
    """
    return PipelineConfig(config_path, env)