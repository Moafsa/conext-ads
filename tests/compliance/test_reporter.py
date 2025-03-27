"""Unit tests for ComplianceReporter module"""

import pytest
from datetime import datetime, timedelta
from unittest.mock import Mock, patch
from src.compliance.reporter import ComplianceReporter, ComplianceAlert, ComplianceReport

@pytest.fixture
def compliance_reporter():
    """Create ComplianceReporter instance for testing"""
    config = {
        'templates_path': 'tests/templates',
        'smtp_config': {
            'host': 'smtp.test.com',
            'port': 465,
            'username': 'test@test.com',
            'password': 'test_pass',
            'sender': 'reporter@test.com'
        },
        'alert_thresholds': {
            'high': 0.8,
            'medium': 0.5
        },
        'report_schedule': {
            'daily': '00:00',
            'weekly': 'MON 00:00'
        },
        'alert_recipients': ['admin@test.com']
    }
    return ComplianceReporter(config)

@pytest.fixture
def sample_alerts():
    """Sample alerts for testing"""
    return [
        ComplianceAlert(
            id="alert1",
            severity="high",
            title="Policy violation",
            description="Content violates policy",
            content_id="content1",
            violation_type="policy",
            details={'policy': 'no_profanity'},
            timestamp=datetime.now() - timedelta(hours=2)
        ),
        ComplianceAlert(
            id="alert2",
            severity="medium",
            title="Regulatory warning",
            description="Missing consent form",
            content_id="content2",
            violation_type="regulatory",
            details={'regulation': 'GDPR'},
            timestamp=datetime.now() - timedelta(hours=1),
            is_resolved=True,
            resolution_notes="Added consent form"
        )
    ]

def test_create_alert(compliance_reporter):
    """Test alert creation"""
    violation = {
        'title': 'Test violation',
        'description': 'Test description',
        'content_id': 'test_content',
        'type': 'test',
        'impact_score': 0.9,
        'details': {}
    }
    
    compliance_reporter.create_alert(violation)
    assert len(compliance_reporter.alerts) == 1
    assert compliance_reporter.alerts[0].severity == 'high'

def test_resolve_alert(compliance_reporter, sample_alerts):
    """Test alert resolution"""
    compliance_reporter.alerts = sample_alerts
    
    compliance_reporter.resolve_alert(
        "alert1",
        "Fixed policy violation"
    )
    
    alert = next(a for a in compliance_reporter.alerts if a.id == "alert1")
    assert alert.is_resolved
    assert alert.resolution_notes == "Fixed policy violation"

def test_generate_report(compliance_reporter, sample_alerts):
    """Test report generation"""
    compliance_reporter.alerts = sample_alerts
    
    start_date = datetime.now() - timedelta(days=1)
    end_date = datetime.now()
    
    report = compliance_reporter.generate_report(
        start_date,
        end_date
    )
    
    assert report.id.startswith("REP_")
    assert len(report.alerts) == 2
    assert report.summary['total_alerts'] == 2
    assert report.summary['resolved_alerts'] == 1
    assert report.summary['high_severity'] == 1
    assert 'compliance_rate' in report.summary

@patch('smtplib.SMTP_SSL')
def test_send_report(mock_smtp, compliance_reporter, sample_alerts):
    """Test report sending"""
    # Create report
    start_date = datetime.now() - timedelta(days=1)
    end_date = datetime.now()
    report = compliance_reporter.generate_report(start_date, end_date)
    
    # Mock SMTP connection
    mock_smtp_instance = Mock()
    mock_smtp.return_value.__enter__.return_value = mock_smtp_instance
    
    # Send report
    compliance_reporter.send_report(
        report,
        ['test@example.com']
    )
    
    # Verify SMTP calls
    mock_smtp_instance.login.assert_called_once()
    mock_smtp_instance.send_message.assert_called_once()

def test_metrics_calculation(compliance_reporter, sample_alerts):
    """Test metrics calculation"""
    compliance_reporter.alerts = sample_alerts
    
    start_date = datetime.now() - timedelta(days=1)
    end_date = datetime.now()
    
    report = compliance_reporter.generate_report(
        start_date,
        end_date
    )
    
    assert 'compliance_rate' in report.metrics
    assert 'resolution_rate' in report.metrics
    assert 'avg_resolution_time' in report.metrics

def test_chart_generation(compliance_reporter, sample_alerts):
    """Test chart generation"""
    compliance_reporter.alerts = sample_alerts
    
    start_date = datetime.now() - timedelta(days=1)
    end_date = datetime.now()
    
    report = compliance_reporter.generate_report(
        start_date,
        end_date
    )
    
    assert 'severity_distribution' in report.charts
    assert 'alert_trend' in report.charts

def test_immediate_alerts(compliance_reporter):
    """Test immediate alert sending for high severity"""
    violation = {
        'title': 'Critical violation',
        'description': 'Immediate attention needed',
        'content_id': 'test_content',
        'type': 'critical',
        'impact_score': 0.9,
        'details': {}
    }
    
    with patch('smtplib.SMTP_SSL') as mock_smtp:
        mock_smtp_instance = Mock()
        mock_smtp.return_value.__enter__.return_value = mock_smtp_instance
        
        compliance_reporter.create_alert(violation)
        
        # Verify immediate alert was sent
        mock_smtp_instance.send_message.assert_called_once()

def test_report_export(compliance_reporter, sample_alerts):
    """Test report export functionality"""
    compliance_reporter.alerts = sample_alerts
    
    start_date = datetime.now() - timedelta(days=1)
    end_date = datetime.now()
    
    with patch('builtins.open', create=True) as mock_open:
        report = compliance_reporter.generate_report(
            start_date,
            end_date
        )
        
        # Verify file operations
        mock_open.assert_called()

def test_error_handling(compliance_reporter):
    """Test error handling"""
    # Test invalid alert resolution
    with pytest.raises(ValueError):
        compliance_reporter.resolve_alert(
            "nonexistent_alert",
            "test"
        )
    
    # Test invalid report dates
    with pytest.raises(ValueError):
        compliance_reporter.generate_report(
            datetime.now(),  # Start after end
            datetime.now() - timedelta(days=1)
        )
    
    # Test invalid email configuration
    compliance_reporter.config['smtp_config']['host'] = None
    with pytest.raises(ValueError):
        compliance_reporter.send_report(
            Mock(spec=ComplianceReport),
            ['test@example.com']
        )