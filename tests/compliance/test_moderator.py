"""Unit tests for ContentModerator module"""

import pytest
from unittest.mock import Mock, patch
from src.compliance.moderator import ContentModerator, ModerationResult

@pytest.fixture
def content_moderator():
    """Create ContentModerator instance for testing"""
    config = {
        'models': {
            'toxicity': 'tests/models/toxicity.pkl',
            'sentiment': 'tests/models/sentiment.pkl',
            'nsfw': 'tests/models/nsfw.pkl',
            'object_detection': 'tests/models/object.pkl'
        },
        'cache_enabled': True,
        'cache_ttl': 3600,
        'confidence_threshold': 0.8
    }
    return ContentModerator(config)

@pytest.fixture
def mock_models():
    """Mock ML models for testing"""
    return {
        'toxicity': Mock(predict=Mock(return_value=[(0.2, 'clean')])),
        'sentiment': Mock(predict=Mock(return_value=[(0.9, 'positive')])),
        'nsfw': Mock(predict=Mock(return_value=[(0.1, 'safe')])),
        'object_detection': Mock(detect=Mock(return_value=[
            ('person', 0.95),
            ('car', 0.85)
        ]))
    }

def test_moderate_text(content_moderator, mock_models):
    """Test text moderation"""
    content_moderator.models = mock_models
    
    # Test clean text
    text = "This is a positive and clean message"
    result = content_moderator.moderate_text(text)
    
    assert result.status == 'approved'
    assert result.confidence > 0.8
    assert not result.violations
    
    # Test toxic text
    mock_models['toxicity'].predict.return_value = [(0.9, 'toxic')]
    result = content_moderator.moderate_text(text)
    
    assert result.status == 'rejected'
    assert 'toxic_content' in result.violations

def test_moderate_image(content_moderator, mock_models):
    """Test image moderation"""
    content_moderator.models = mock_models
    
    # Test safe image
    image_data = b"dummy_image_data"
    result = content_moderator.moderate_image(image_data)
    
    assert result.status == 'approved'
    assert result.confidence > 0.8
    assert not result.violations
    
    # Test NSFW image
    mock_models['nsfw'].predict.return_value = [(0.9, 'nsfw')]
    result = content_moderator.moderate_image(image_data)
    
    assert result.status == 'rejected'
    assert 'nsfw_content' in result.violations

def test_moderate_ad(content_moderator, mock_models):
    """Test complete ad moderation"""
    content_moderator.models = mock_models
    
    ad = {
        'text': 'Great product for everyone!',
        'images': [b"image1", b"image2"],
        'landing_page': 'https://example.com'
    }
    
    result = content_moderator.moderate_ad(ad)
    assert result.status == 'approved'
    assert result.confidence > 0.8
    assert not result.violations
    
    # Test ad with violations
    mock_models['toxicity'].predict.return_value = [(0.9, 'toxic')]
    mock_models['nsfw'].predict.return_value = [(0.9, 'nsfw')]
    
    result = content_moderator.moderate_ad(ad)
    assert result.status == 'rejected'
    assert len(result.violations) == 2

@patch('src.compliance.moderator.requests.get')
def test_landing_page_check(mock_get, content_moderator):
    """Test landing page checking"""
    mock_get.return_value.status_code = 200
    mock_get.return_value.text = "<html>Safe content</html>"
    
    result = content_moderator._check_landing_page("https://example.com")
    assert result.status == 'approved'
    
    # Test malicious landing page
    mock_get.return_value.status_code = 403
    result = content_moderator._check_landing_page("https://example.com")
    assert result.status == 'rejected'

def test_cache(content_moderator, mock_models):
    """Test result caching"""
    content_moderator.models = mock_models
    
    text = "Test message"
    
    # First moderation should cache result
    result1 = content_moderator.moderate_text(text)
    
    # Second moderation should use cached result
    result2 = content_moderator.moderate_text(text)
    
    assert result1 == result2
    assert content_moderator.cache.get(hash(text)) is not None

def test_batch_moderation(content_moderator, mock_models):
    """Test batch moderation"""
    content_moderator.models = mock_models
    
    ads = [
        {
            'text': 'Ad 1',
            'images': [b"image1"],
            'landing_page': 'https://example1.com'
        },
        {
            'text': 'Ad 2',
            'images': [b"image2"],
            'landing_page': 'https://example2.com'
        }
    ]
    
    results = content_moderator.moderate_batch(ads)
    assert len(results) == 2
    assert all(r.status == 'approved' for r in results)

def test_error_handling(content_moderator):
    """Test error handling"""
    # Test with invalid image data
    with pytest.raises(ValueError):
        content_moderator.moderate_image("invalid_data")
    
    # Test with missing models
    content_moderator.models = {}
    with pytest.raises(RuntimeError):
        content_moderator.moderate_text("test")