"""Demonstration script for testing the Compliance System"""

import os
import json
from datetime import datetime, timedelta
from src.compliance.policy import PolicyChecker
from src.compliance.moderator import ContentModerator
from src.compliance.monitor import RegulatoryMonitor
from src.compliance.reporter import ComplianceReporter

def load_config():
    """Load configuration for all components"""
    with open('config/compliance/config.json', 'r') as f:
        return json.load(f)

def demo_policy_checker(config):
    """Demonstrate PolicyChecker functionality"""
    print("\n=== PolicyChecker Demo ===")
    
    # Initialize PolicyChecker
    checker = PolicyChecker(config['policy_checker'])
    
    # Test content
    content = {
        'type': 'text',
        'text': 'This is a sample advertisement with required disclaimer.',
        'platform': 'facebook'
    }
    
    print("\nChecking valid content...")
    result = checker.check_content(content)
    print(f"Status: {result.status}")
    print(f"Violations: {len(result.violations)}")
    
    # Test invalid content
    content['text'] = 'bad_word without disclaimer'
    print("\nChecking invalid content...")
    result = checker.check_content(content)
    print(f"Status: {result.status}")
    print(f"Violations: {len(result.violations)}")
    for violation in result.violations:
        print(f"- {violation.description}")

def demo_content_moderator(config):
    """Demonstrate ContentModerator functionality"""
    print("\n=== ContentModerator Demo ===")
    
    # Initialize ContentModerator
    moderator = ContentModerator(config['content_moderator'])
    
    # Test text moderation
    text = "This is a positive and friendly advertisement"
    print("\nModerating text content...")
    result = moderator.moderate_text(text)
    print(f"Status: {result.status}")
    print(f"Confidence: {result.confidence:.2f}")
    
    # Test image moderation
    print("\nModerating image content...")
    with open('tests/data/test_image.jpg', 'rb') as f:
        image_data = f.read()
    result = moderator.moderate_image(image_data)
    print(f"Status: {result.status}")
    print(f"Confidence: {result.confidence:.2f}")
    if result.details:
        print("Detected objects:", result.details.get('objects', []))

def demo_regulatory_monitor(config):
    """Demonstrate RegulatoryMonitor functionality"""
    print("\n=== RegulatoryMonitor Demo ===")
    
    # Initialize RegulatoryMonitor
    monitor = RegulatoryMonitor(config['regulatory_monitor'])
    
    # Test content compliance
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
    
    print("\nChecking content compliance...")
    result = monitor.check_content(content)
    print(f"Status: {result.status}")
    if result.violations:
        print("Violations:")
        for violation in result.violations:
            print(f"- {violation.description}")
    
    # Test regulation updates
    print("\nUpdating regulations...")
    monitor.update_regulations()
    print(f"Total regulations: {len(monitor.regulations)}")

def demo_compliance_reporter(config):
    """Demonstrate ComplianceReporter functionality"""
    print("\n=== ComplianceReporter Demo ===")
    
    # Initialize ComplianceReporter
    reporter = ComplianceReporter(config['compliance_reporter'])
    
    # Create some test alerts
    violations = [
        {
            'title': 'Policy Violation',
            'description': 'Content contains prohibited words',
            'content_id': 'content1',
            'type': 'policy',
            'impact_score': 0.9,
            'details': {'policy': 'no_profanity'}
        },
        {
            'title': 'Regulatory Warning',
            'description': 'Missing consent form',
            'content_id': 'content2',
            'type': 'regulatory',
            'impact_score': 0.6,
            'details': {'regulation': 'GDPR'}
        }
    ]
    
    print("\nCreating alerts...")
    for violation in violations:
        reporter.create_alert(violation)
    print(f"Total alerts: {len(reporter.alerts)}")
    
    # Generate report
    print("\nGenerating compliance report...")
    start_date = datetime.now() - timedelta(days=1)
    end_date = datetime.now()
    report = reporter.generate_report(start_date, end_date)
    
    print("\nReport Summary:")
    print(f"Total Alerts: {report.summary['total_alerts']}")
    print(f"Resolved Alerts: {report.summary['resolved_alerts']}")
    print(f"High Severity: {report.summary['high_severity']}")
    print(f"Compliance Rate: {report.summary['compliance_rate']:.2f}%")

def main():
    """Main demonstration function"""
    try:
        print("Loading configuration...")
        config = load_config()
        
        # Run demonstrations
        demo_policy_checker(config)
        demo_content_moderator(config)
        demo_regulatory_monitor(config)
        demo_compliance_reporter(config)
        
        print("\nDemonstration completed successfully!")
        
    except Exception as e:
        print(f"\nError during demonstration: {str(e)}")
        raise

if __name__ == '__main__':
    main()