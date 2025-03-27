"""Unit tests for PolicyChecker module"""

import pytest
from datetime import datetime
from src.compliance.policy import PolicyChecker, PolicyRule, PolicyViolation

@pytest.fixture
def policy_checker():
    """Create PolicyChecker instance for testing"""
    config = {
        'rules_file': 'tests/data/test_rules.json',
        'cache_enabled': True,
        'cache_ttl': 3600
    }
    return PolicyChecker(config)

@pytest.fixture
def sample_rules():
    """Sample policy rules for testing"""
    return [
        PolicyRule(
            id="rule1",
            name="No profanity",
            description="Checks for prohibited words",
            prohibited_words=["bad_word1", "bad_word2"],
            regex_patterns=[r"\bbad\s*word\b"],
            required_elements=["disclaimer"],
            min_length=10,
            max_length=1000,
            platform="all"
        ),
        PolicyRule(
            id="rule2", 
            name="Image requirements",
            description="Checks image specifications",
            min_width=400,
            min_height=400,
            max_size_kb=500,
            allowed_formats=["jpg", "png"],
            platform="facebook"
        )
    ]

def test_add_rule(policy_checker, sample_rules):
    """Test adding new rules"""
    for rule in sample_rules:
        policy_checker.add_rule(rule)
        assert rule.id in policy_checker.rules
        
def test_check_content_text(policy_checker, sample_rules):
    """Test content checking for text"""
    policy_checker.rules = {rule.id: rule for rule in sample_rules}
    
    # Valid content
    content = {
        'type': 'text',
        'text': 'Good content with disclaimer',
        'platform': 'all'
    }
    result = policy_checker.check_content(content)
    assert not result.violations
    
    # Invalid content
    content = {
        'type': 'text',
        'text': 'bad_word1 without disclaimer',
        'platform': 'all'
    }
    result = policy_checker.check_content(content)
    assert len(result.violations) == 2  # Prohibited word and missing disclaimer

def test_check_content_image(policy_checker, sample_rules):
    """Test content checking for images"""
    policy_checker.rules = {rule.id: rule for rule in sample_rules}
    
    # Valid image
    content = {
        'type': 'image',
        'width': 500,
        'height': 500,
        'size_kb': 400,
        'format': 'jpg',
        'platform': 'facebook'
    }
    result = policy_checker.check_content(content)
    assert not result.violations
    
    # Invalid image
    content = {
        'type': 'image',
        'width': 300,  # Too small
        'height': 300,  # Too small
        'size_kb': 600,  # Too large
        'format': 'gif',  # Invalid format
        'platform': 'facebook'
    }
    result = policy_checker.check_content(content)
    assert len(result.violations) == 4

def test_check_campaign(policy_checker, sample_rules):
    """Test campaign checking"""
    policy_checker.rules = {rule.id: rule for rule in sample_rules}
    
    campaign = {
        'id': 'test_campaign',
        'platform': 'facebook',
        'contents': [
            {
                'type': 'text',
                'text': 'Good content with disclaimer',
            },
            {
                'type': 'image',
                'width': 500,
                'height': 500,
                'size_kb': 400,
                'format': 'jpg'
            }
        ]
    }
    
    result = policy_checker.check_campaign(campaign)
    assert not result.violations

def test_rule_validation(policy_checker):
    """Test rule validation"""
    # Invalid rule - missing required fields
    invalid_rule = PolicyRule(
        id="invalid1",
        name="Invalid rule"
        # Missing description and other required fields
    )
    
    with pytest.raises(ValueError):
        policy_checker.add_rule(invalid_rule)
        
    # Invalid rule - invalid regex pattern
    invalid_rule = PolicyRule(
        id="invalid2",
        name="Invalid regex",
        description="Has invalid regex",
        regex_patterns=["[invalid regex"]
    )
    
    with pytest.raises(ValueError):
        policy_checker.add_rule(invalid_rule)

def test_cache(policy_checker, sample_rules):
    """Test result caching"""
    policy_checker.rules = {rule.id: rule for rule in sample_rules}
    
    content = {
        'type': 'text',
        'text': 'Test content with disclaimer',
        'platform': 'all'
    }
    
    # First check should cache result
    result1 = policy_checker.check_content(content)
    
    # Second check should use cached result
    result2 = policy_checker.check_content(content)
    
    assert result1 == result2
    assert policy_checker.cache.get(hash(str(content))) is not None