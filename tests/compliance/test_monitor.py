"""Unit tests for RegulatoryMonitor module"""

import pytest
from datetime import datetime, timedelta
from unittest.mock import Mock, patch
from src.compliance.monitor import RegulatoryMonitor, Regulation, ComplianceCheck

@pytest.fixture
def regulatory_monitor():
    """Create RegulatoryMonitor instance for testing"""
    config = {
        'regulations_file': 'tests/data/test_regulations.json',
        'cache_enabled': True,
        'cache_ttl': 3600,
        'update_interval': 86400,
        'api_url': 'https://api.regulations.test'
    }
    return RegulatoryMonitor(config)

@pytest.fixture
def sample_regulations():
    """Sample regulations for testing"""
    return [
        Regulation(
            id="reg1",
            name="GDPR",
            description="General Data Protection Regulation",
            region="EU",
            industry="all",
            requirements={
                'data_collection': ['consent', 'purpose'],
                'data_storage': ['encryption', 'retention'],
                'user_rights': ['access', 'deletion']
            },
            effective_date=datetime.now() - timedelta(days=30),
            last_updated=datetime.now()
        ),
        Regulation(
            id="reg2",
            name="CCPA",
            description="California Consumer Privacy Act",
            region="US-CA",
            industry="all",
            requirements={
                'data_collection': ['notice', 'opt_out'],
                'data_sale': ['disclosure', 'opt_out'],
                'user_rights': ['access', 'deletion', 'portability']
            },
            effective_date=datetime.now() - timedelta(days=60),
            last_updated=datetime.now()
        )
    ]

def test_add_regulation(regulatory_monitor, sample_regulations):
    """Test adding new regulations"""
    for reg in sample_regulations:
        regulatory_monitor.add_regulation(reg)
        assert reg.id in regulatory_monitor.regulations

def test_check_content(regulatory_monitor, sample_regulations):
    """Test content compliance checking"""
    regulatory_monitor.regulations = {reg.id: reg for reg in sample_regulations}
    
    # Valid content
    content = {
        'type': 'ad',
        'region': 'EU',
        'data_collection': {
            'consent': True,
            'purpose': 'Marketing'
        },
        'data_storage': {
            'encryption': True,
            'retention_period': '30 days'
        }
    }
    
    result = regulatory_monitor.check_content(content)
    assert result.status == 'compliant'
    assert not result.violations
    
    # Non-compliant content
    content['data_collection']['consent'] = False
    result = regulatory_monitor.check_content(content)
    assert result.status == 'non_compliant'
    assert len(result.violations) > 0

def test_check_campaign(regulatory_monitor, sample_regulations):
    """Test campaign compliance checking"""
    regulatory_monitor.regulations = {reg.id: reg for reg in sample_regulations}
    
    campaign = {
        'id': 'test_campaign',
        'region': 'US-CA',
        'contents': [
            {
                'type': 'ad',
                'data_collection': {
                    'notice': True,
                    'opt_out': True
                }
            }
        ],
        'data_handling': {
            'sale': {
                'disclosure': True,
                'opt_out': True
            }
        }
    }
    
    result = regulatory_monitor.check_campaign(campaign)
    assert result.status == 'compliant'
    assert not result.violations

@patch('src.compliance.monitor.requests.get')
def test_update_regulations(mock_get, regulatory_monitor):
    """Test regulations update from API"""
    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        'regulations': [
            {
                'id': 'new_reg',
                'name': 'New Regulation',
                'description': 'Test regulation',
                'region': 'Global',
                'industry': 'all',
                'requirements': {},
                'effective_date': datetime.now().isoformat(),
                'last_updated': datetime.now().isoformat()
            }
        ]
    }
    mock_get.return_value = mock_response
    
    regulatory_monitor.update_regulations()
    assert 'new_reg' in regulatory_monitor.regulations

def test_regulation_validation(regulatory_monitor):
    """Test regulation validation"""
    # Invalid regulation - missing required fields
    invalid_reg = Regulation(
        id="invalid1",
        name="Invalid regulation"
        # Missing required fields
    )
    
    with pytest.raises(ValueError):
        regulatory_monitor.add_regulation(invalid_reg)
    
    # Invalid regulation - invalid dates
    invalid_reg = Regulation(
        id="invalid2",
        name="Invalid dates",
        description="Test",
        region="Global",
        industry="all",
        requirements={},
        effective_date=datetime.now() + timedelta(days=30),  # Future date
        last_updated=datetime.now() - timedelta(days=30)  # Past date
    )
    
    with pytest.raises(ValueError):
        regulatory_monitor.add_regulation(invalid_reg)

def test_cache(regulatory_monitor, sample_regulations):
    """Test result caching"""
    regulatory_monitor.regulations = {reg.id: reg for reg in sample_regulations}
    
    content = {
        'type': 'ad',
        'region': 'EU',
        'data_collection': {
            'consent': True,
            'purpose': 'Marketing'
        }
    }
    
    # First check should cache result
    result1 = regulatory_monitor.check_content(content)
    
    # Second check should use cached result
    result2 = regulatory_monitor.check_content(content)
    
    assert result1 == result2
    assert regulatory_monitor.cache.get(hash(str(content))) is not None

def test_requirement_validation(regulatory_monitor, sample_regulations):
    """Test requirement validation"""
    reg = sample_regulations[0]
    
    # Test valid requirements
    assert regulatory_monitor._validate_requirements(
        reg.requirements,
        {
            'data_collection': {
                'consent': True,
                'purpose': 'Marketing'
            },
            'data_storage': {
                'encryption': True,
                'retention': '30 days'
            }
        }
    )
    
    # Test invalid requirements
    assert not regulatory_monitor._validate_requirements(
        reg.requirements,
        {
            'data_collection': {
                'consent': False  # Missing consent
            }
        }
    )

def test_region_matching(regulatory_monitor, sample_regulations):
    """Test region matching logic"""
    regulatory_monitor.regulations = {reg.id: reg for reg in sample_regulations}
    
    # Test exact match
    assert regulatory_monitor._get_applicable_regulations('EU')
    
    # Test hierarchical match (US-CA should match US regulations)
    assert regulatory_monitor._get_applicable_regulations('US-CA')
    
    # Test no match
    assert not regulatory_monitor._get_applicable_regulations('INVALID')