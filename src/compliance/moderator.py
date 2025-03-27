"""Content Moderator Module

This module implements automated content moderation for ad content,
including text analysis, image moderation, and brand safety checks.
"""

from typing import Dict, List, Optional, Tuple
import logging
from dataclasses import dataclass
from datetime import datetime
import json
import numpy as np
from PIL import Image
import io
import requests
from transformers import pipeline

@dataclass
class ModerationResult:
    """Result of content moderation"""
    content_id: str
    content_type: str
    is_approved: bool
    confidence: float
    categories: List[str]
    details: Dict[str, any]
    timestamp: datetime

class ContentModerator:
    """Moderates ad content for policy compliance and brand safety"""
    
    def __init__(self, config: Dict[str, any]):
        """Initialize content moderator
        
        Args:
            config: Configuration dictionary containing:
                - api_key: API key for external services
                - model_path: Path to local models
                - confidence_threshold: Minimum confidence for approval
                - cache_size: Size of results cache
        """
        self.config = config
        self.logger = logging.getLogger(__name__)
        self.cache: Dict[str, ModerationResult] = {}
        
        # Initialize models
        self._init_models()
    
    def moderate_text(
        self,
        text: str,
        content_id: str,
        context: Optional[Dict[str, any]] = None
    ) -> ModerationResult:
        """Moderate text content
        
        Args:
            text: Text to moderate
            content_id: Content identifier
            context: Optional context information
            
        Returns:
            Moderation result
        """
        try:
            # Check cache
            cache_key = f"text:{content_id}"
            if cache_key in self.cache:
                return self.cache[cache_key]
            
            # Analyze text
            toxicity = self._analyze_toxicity(text)
            sentiment = self._analyze_sentiment(text)
            categories = self._classify_content(text)
            
            # Check against thresholds
            is_approved = all([
                toxicity['score'] < self.config['toxicity_threshold'],
                sentiment['score'] > self.config['sentiment_threshold'],
                not any(cat in self.config['forbidden_categories']
                       for cat in categories)
            ])
            
            # Create result
            result = ModerationResult(
                content_id=content_id,
                content_type='text',
                is_approved=is_approved,
                confidence=min(
                    toxicity['confidence'],
                    sentiment['confidence']
                ),
                categories=categories,
                details={
                    'toxicity': toxicity,
                    'sentiment': sentiment,
                    'context': context
                },
                timestamp=datetime.now()
            )
            
            # Cache result
            self.cache[cache_key] = result
            
            return result
            
        except Exception as e:
            self.logger.error(f"Text moderation failed: {str(e)}")
            raise
    
    def moderate_image(
        self,
        image: bytes,
        content_id: str,
        context: Optional[Dict[str, any]] = None
    ) -> ModerationResult:
        """Moderate image content
        
        Args:
            image: Image bytes to moderate
            content_id: Content identifier
            context: Optional context information
            
        Returns:
            Moderation result
        """
        try:
            # Check cache
            cache_key = f"image:{content_id}"
            if cache_key in self.cache:
                return self.cache[cache_key]
            
            # Convert bytes to PIL Image
            img = Image.open(io.BytesIO(image))
            
            # Analyze image
            nsfw_score = self._check_nsfw(img)
            objects = self._detect_objects(img)
            text = self._extract_text(img)
            
            # Check text if found
            text_results = None
            if text:
                text_results = self.moderate_text(
                    text,
                    f"{content_id}_text",
                    context
                )
            
            # Check against thresholds
            is_approved = all([
                nsfw_score < self.config['nsfw_threshold'],
                not any(obj in self.config['forbidden_objects']
                       for obj in objects),
                text_results.is_approved if text_results else True
            ])
            
            # Create result
            result = ModerationResult(
                content_id=content_id,
                content_type='image',
                is_approved=is_approved,
                confidence=1 - nsfw_score,
                categories=[obj['category'] for obj in objects],
                details={
                    'nsfw_score': nsfw_score,
                    'objects': objects,
                    'text_results': text_results.details if text_results else None,
                    'context': context
                },
                timestamp=datetime.now()
            )
            
            # Cache result
            self.cache[cache_key] = result
            
            return result
            
        except Exception as e:
            self.logger.error(f"Image moderation failed: {str(e)}")
            raise
    
    def moderate_ad(
        self,
        ad: Dict[str, any]
    ) -> Dict[str, ModerationResult]:
        """Moderate complete ad content
        
        Args:
            ad: Ad content dictionary
            
        Returns:
            Dictionary mapping content types to moderation results
        """
        try:
            results = {}
            
            # Moderate text components
            for field in ['title', 'description', 'cta']:
                if field in ad:
                    results[field] = self.moderate_text(
                        ad[field],
                        f"{ad['id']}_{field}",
                        {'field': field}
                    )
            
            # Moderate images
            for idx, image in enumerate(ad.get('images', [])):
                results[f"image_{idx}"] = self.moderate_image(
                    image['data'],
                    f"{ad['id']}_image_{idx}",
                    {'image_type': image.get('type')}
                )
            
            return results
            
        except Exception as e:
            self.logger.error(f"Ad moderation failed: {str(e)}")
            raise
    
    def _init_models(self) -> None:
        """Initialize ML models"""
        try:
            # Load toxicity model
            self.toxicity_model = pipeline(
                "text-classification",
                model=f"{self.config['model_path']}/toxicity"
            )
            
            # Load sentiment model
            self.sentiment_model = pipeline(
                "sentiment-analysis",
                model=f"{self.config['model_path']}/sentiment"
            )
            
            # Load classification model
            self.classification_model = pipeline(
                "zero-shot-classification",
                model=f"{self.config['model_path']}/classification"
            )
            
            # Load image models
            self.nsfw_model = pipeline(
                "image-classification",
                model=f"{self.config['model_path']}/nsfw"
            )
            
            self.object_detection_model = pipeline(
                "object-detection",
                model=f"{self.config['model_path']}/detection"
            )
            
            self.ocr_model = pipeline(
                "image-to-text",
                model=f"{self.config['model_path']}/ocr"
            )
            
        except Exception as e:
            self.logger.error(f"Model initialization failed: {str(e)}")
            raise
    
    def _analyze_toxicity(self, text: str) -> Dict[str, any]:
        """Analyze text toxicity
        
        Args:
            text: Text to analyze
            
        Returns:
            Toxicity analysis results
        """
        result = self.toxicity_model(text)[0]
        return {
            'score': result['score'],
            'confidence': result['score'] if result['label'] == 'toxic' else 1 - result['score']
        }
    
    def _analyze_sentiment(self, text: str) -> Dict[str, any]:
        """Analyze text sentiment
        
        Args:
            text: Text to analyze
            
        Returns:
            Sentiment analysis results
        """
        result = self.sentiment_model(text)[0]
        return {
            'score': result['score'] if result['label'] == 'POSITIVE' else -result['score'],
            'confidence': result['score']
        }
    
    def _classify_content(self, text: str) -> List[str]:
        """Classify content categories
        
        Args:
            text: Text to classify
            
        Returns:
            List of content categories
        """
        result = self.classification_model(
            text,
            candidate_labels=self.config['content_categories']
        )
        
        # Return categories above threshold
        return [
            label for label, score in zip(result['labels'], result['scores'])
            if score > self.config['category_threshold']
        ]
    
    def _check_nsfw(self, image: Image) -> float:
        """Check image for NSFW content
        
        Args:
            image: PIL Image to check
            
        Returns:
            NSFW probability score
        """
        result = self.nsfw_model(image)[0]
        return result['score'] if result['label'] == 'NSFW' else 0.0
    
    def _detect_objects(self, image: Image) -> List[Dict[str, any]]:
        """Detect objects in image
        
        Args:
            image: PIL Image to analyze
            
        Returns:
            List of detected objects
        """
        return self.object_detection_model(image)
    
    def _extract_text(self, image: Image) -> Optional[str]:
        """Extract text from image
        
        Args:
            image: PIL Image to process
            
        Returns:
            Extracted text if any
        """
        result = self.ocr_model(image)
        return result[0]['generated_text'] if result else None