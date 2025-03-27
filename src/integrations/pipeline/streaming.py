"""Streaming Module

This module implements real-time data streaming and processing
for ad campaign data across different platforms.
"""

from typing import Dict, List, Optional, Callable
import logging
from datetime import datetime
import json
import asyncio
from aiohttp import ClientSession
from confluent_kafka import Producer, Consumer, KafkaError
import avro.schema
from avro.io import DatumWriter, DatumReader

from . import StreamProcessor

class KafkaStreamProcessor(StreamProcessor):
    """Kafka-based stream processor for real-time ad data"""
    
    def __init__(self, config: Dict[str, any]):
        """Initialize Kafka stream processor
        
        Args:
            config: Configuration dictionary containing:
                - bootstrap_servers: Kafka bootstrap servers
                - schema_registry_url: Avro schema registry URL
                - consumer_group: Consumer group ID
                - topics: List of topics to process
        """
        self.config = config
        self.logger = logging.getLogger(__name__)
        self.producer = None
        self.consumer = None
        self.running = False
        self.processors: Dict[str, List[Callable]] = {}
    
    async def connect(self) -> bool:
        """Connect to Kafka cluster
        
        Returns:
            bool: True if connection successful
        """
        try:
            # Create producer
            producer_config = {
                'bootstrap.servers': self.config['bootstrap_servers'],
                'schema.registry.url': self.config['schema_registry_url']
            }
            self.producer = Producer(producer_config)
            
            # Create consumer
            consumer_config = {
                'bootstrap.servers': self.config['bootstrap_servers'],
                'group.id': self.config['consumer_group'],
                'auto.offset.reset': 'latest'
            }
            self.consumer = Consumer(consumer_config)
            
            # Subscribe to topics
            self.consumer.subscribe(self.config['topics'])
            
            return True
            
        except Exception as e:
            self.logger.error(f"Kafka connection failed: {str(e)}")
            return False
    
    async def start_processing(self) -> None:
        """Start processing messages from Kafka topics"""
        try:
            self.running = True
            
            while self.running:
                msg = self.consumer.poll(1.0)
                
                if msg is None:
                    continue
                
                if msg.error():
                    if msg.error().code() == KafkaError._PARTITION_EOF:
                        continue
                    else:
                        self.logger.error(f"Kafka error: {msg.error()}")
                        break
                
                # Process message
                await self._process_message(msg.topic(), msg.value())
                
        except Exception as e:
            self.logger.error(f"Stream processing failed: {str(e)}")
            raise
            
        finally:
            self.consumer.close()
    
    async def stop_processing(self) -> None:
        """Stop processing messages"""
        self.running = False
    
    def register_processor(
        self,
        topic: str,
        processor: Callable[[Dict[str, any]], None]
    ) -> None:
        """Register a message processor for a topic
        
        Args:
            topic: Kafka topic
            processor: Callback function to process messages
        """
        if topic not in self.processors:
            self.processors[topic] = []
        
        self.processors[topic].append(processor)
    
    async def send_message(
        self,
        topic: str,
        message: Dict[str, any],
        key: Optional[str] = None
    ) -> None:
        """Send message to Kafka topic
        
        Args:
            topic: Target topic
            message: Message to send
            key: Optional message key
        """
        try:
            # Serialize message using Avro
            schema = self._get_avro_schema(topic)
            writer = DatumWriter(schema)
            encoded = self._encode_message(message, writer)
            
            # Send to Kafka
            self.producer.produce(
                topic=topic,
                value=encoded,
                key=key,
                callback=self._delivery_callback
            )
            
            # Wait for any outstanding messages
            self.producer.flush()
            
        except Exception as e:
            self.logger.error(f"Failed to send message: {str(e)}")
            raise
    
    async def _process_message(self, topic: str, message: bytes) -> None:
        """Process a single message
        
        Args:
            topic: Message topic
            message: Raw message bytes
        """
        try:
            # Deserialize message
            schema = self._get_avro_schema(topic)
            reader = DatumReader(schema)
            decoded = self._decode_message(message, reader)
            
            # Process with registered processors
            if topic in self.processors:
                for processor in self.processors[topic]:
                    try:
                        await processor(decoded)
                    except Exception as e:
                        self.logger.error(
                            f"Processor failed for topic {topic}: {str(e)}"
                        )
            
        except Exception as e:
            self.logger.error(f"Message processing failed: {str(e)}")
    
    def _delivery_callback(self, err, msg):
        """Callback for message delivery results
        
        Args:
            err: Error if any
            msg: Produced message
        """
        if err:
            self.logger.error(f'Message delivery failed: {str(err)}')
        else:
            self.logger.debug(f'Message delivered to {msg.topic()}')
    
    def _get_avro_schema(self, topic: str) -> avro.schema.Schema:
        """Get Avro schema for topic
        
        Args:
            topic: Kafka topic
            
        Returns:
            Avro schema
        """
        # TODO: Implement schema registry client
        return avro.schema.parse(self._get_schema_json(topic))
    
    def _get_schema_json(self, topic: str) -> str:
        """Get schema JSON for topic
        
        Args:
            topic: Kafka topic
            
        Returns:
            Schema JSON string
        """
        # TODO: Load from schema registry
        return {
            'ad_events': {
                "type": "record",
                "name": "AdEvent",
                "fields": [
                    {"name": "event_id", "type": "string"},
                    {"name": "event_type", "type": "string"},
                    {"name": "ad_id", "type": "string"},
                    {"name": "campaign_id", "type": "string"},
                    {"name": "platform", "type": "string"},
                    {"name": "timestamp", "type": "long"},
                    {"name": "data", "type": "string"}
                ]
            }
        }.get(topic)
    
    def _encode_message(
        self,
        message: Dict[str, any],
        writer: DatumWriter
    ) -> bytes:
        """Encode message using Avro
        
        Args:
            message: Message to encode
            writer: Avro DatumWriter
            
        Returns:
            Encoded message bytes
        """
        # TODO: Implement Avro encoding
        return json.dumps(message).encode('utf-8')
    
    def _decode_message(
        self,
        message: bytes,
        reader: DatumReader
    ) -> Dict[str, any]:
        """Decode Avro message
        
        Args:
            message: Raw message bytes
            reader: Avro DatumReader
            
        Returns:
            Decoded message dictionary
        """
        # TODO: Implement Avro decoding
        return json.loads(message.decode('utf-8'))

class WebhookStreamProcessor(StreamProcessor):
    """Webhook-based stream processor for real-time ad data"""
    
    def __init__(self, config: Dict[str, any]):
        """Initialize webhook stream processor
        
        Args:
            config: Configuration dictionary containing:
                - webhook_url: Webhook endpoint URL
                - auth_token: Authentication token
                - retry_attempts: Number of retry attempts
                - retry_delay: Delay between retries in seconds
        """
        self.config = config
        self.logger = logging.getLogger(__name__)
        self.session = None
        self.running = False
        self.processors: List[Callable] = []
    
    async def connect(self) -> bool:
        """Initialize HTTP session
        
        Returns:
            bool: True if connection successful
        """
        try:
            self.session = ClientSession(
                headers={'Authorization': f"Bearer {self.config['auth_token']}"}
            )
            return True
            
        except Exception as e:
            self.logger.error(f"Session initialization failed: {str(e)}")
            return False
    
    async def start_processing(self) -> None:
        """Start processing webhook events"""
        try:
            self.running = True
            
            while self.running:
                try:
                    async with self.session.get(
                        self.config['webhook_url']
                    ) as response:
                        if response.status == 200:
                            data = await response.json()
                            await self._process_events(data)
                        else:
                            self.logger.error(
                                f"Webhook request failed: {response.status}"
                            )
                    
                    # Wait before next poll
                    await asyncio.sleep(1)
                    
                except Exception as e:
                    self.logger.error(f"Event processing failed: {str(e)}")
                    await asyncio.sleep(self.config['retry_delay'])
            
        except Exception as e:
            self.logger.error(f"Stream processing failed: {str(e)}")
            raise
            
        finally:
            await self.session.close()
    
    async def stop_processing(self) -> None:
        """Stop processing webhook events"""
        self.running = False
    
    def register_processor(
        self,
        processor: Callable[[Dict[str, any]], None]
    ) -> None:
        """Register an event processor
        
        Args:
            processor: Callback function to process events
        """
        self.processors.append(processor)
    
    async def send_message(
        self,
        message: Dict[str, any]
    ) -> None:
        """Send message via webhook
        
        Args:
            message: Message to send
        """
        try:
            retry_count = 0
            
            while retry_count < self.config['retry_attempts']:
                try:
                    async with self.session.post(
                        self.config['webhook_url'],
                        json=message
                    ) as response:
                        if response.status == 200:
                            return
                        else:
                            self.logger.error(
                                f"Webhook send failed: {response.status}"
                            )
                    
                except Exception as e:
                    self.logger.error(f"Send attempt failed: {str(e)}")
                
                retry_count += 1
                await asyncio.sleep(self.config['retry_delay'])
            
            raise Exception("Max retry attempts reached")
            
        except Exception as e:
            self.logger.error(f"Failed to send message: {str(e)}")
            raise
    
    async def _process_events(self, events: List[Dict[str, any]]) -> None:
        """Process webhook events
        
        Args:
            events: List of events to process
        """
        for event in events:
            for processor in self.processors:
                try:
                    await processor(event)
                except Exception as e:
                    self.logger.error(f"Event processor failed: {str(e)}")