"""Compliance Reporter Module

This module implements automated compliance reporting for ad campaigns,
generating detailed reports and alerts for compliance issues.
"""

from typing import Dict, List, Optional, Union
import logging
from dataclasses import dataclass
from datetime import datetime, timedelta
import json
import pandas as pd
import plotly.graph_objects as go
from jinja2 import Environment, FileSystemLoader
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.application import MIMEApplication

@dataclass
class ComplianceAlert:
    """Represents a compliance alert"""
    id: str
    severity: str
    title: str
    description: str
    content_id: str
    violation_type: str
    details: Dict[str, any]
    timestamp: datetime
    is_resolved: bool = False
    resolution_notes: Optional[str] = None

@dataclass
class ComplianceReport:
    """Represents a compliance report"""
    id: str
    period_start: datetime
    period_end: datetime
    summary: Dict[str, any]
    alerts: List[ComplianceAlert]
    metrics: Dict[str, float]
    charts: Dict[str, str]
    timestamp: datetime

class ComplianceReporter:
    """Generates compliance reports and alerts"""
    
    def __init__(self, config: Dict[str, any]):
        """Initialize compliance reporter
        
        Args:
            config: Configuration dictionary containing:
                - templates_path: Path to report templates
                - smtp_config: Email configuration
                - alert_thresholds: Alert severity thresholds
                - report_schedule: Report generation schedule
        """
        self.config = config
        self.logger = logging.getLogger(__name__)
        self.alerts: List[ComplianceAlert] = []
        self.template_env = Environment(
            loader=FileSystemLoader(config['templates_path'])
        )
    
    def create_alert(
        self,
        violation: Union[Dict[str, any], List[Dict[str, any]]]
    ) -> None:
        """Create compliance alert(s)
        
        Args:
            violation: Violation data or list of violations
        """
        try:
            if isinstance(violation, list):
                for v in violation:
                    self._process_violation(v)
            else:
                self._process_violation(violation)
            
        except Exception as e:
            self.logger.error(f"Alert creation failed: {str(e)}")
            raise
    
    def resolve_alert(
        self,
        alert_id: str,
        resolution_notes: str
    ) -> None:
        """Mark alert as resolved
        
        Args:
            alert_id: ID of alert to resolve
            resolution_notes: Notes about resolution
        """
        try:
            alert = next(
                (a for a in self.alerts if a.id == alert_id),
                None
            )
            
            if not alert:
                raise ValueError(f"Alert {alert_id} not found")
            
            alert.is_resolved = True
            alert.resolution_notes = resolution_notes
            
            self.logger.info(f"Resolved alert {alert_id}")
            
        except Exception as e:
            self.logger.error(f"Alert resolution failed: {str(e)}")
            raise
    
    def generate_report(
        self,
        start_date: datetime,
        end_date: datetime,
        report_type: str = 'full'
    ) -> ComplianceReport:
        """Generate compliance report
        
        Args:
            start_date: Report period start
            end_date: Report period end
            report_type: Type of report to generate
            
        Returns:
            Generated compliance report
        """
        try:
            # Get alerts for period
            period_alerts = [
                alert for alert in self.alerts
                if start_date <= alert.timestamp <= end_date
            ]
            
            # Calculate metrics
            metrics = self._calculate_metrics(period_alerts)
            
            # Generate charts
            charts = self._generate_charts(period_alerts)
            
            # Create summary
            summary = {
                'total_alerts': len(period_alerts),
                'resolved_alerts': len([a for a in period_alerts if a.is_resolved]),
                'high_severity': len([
                    a for a in period_alerts
                    if a.severity == 'high'
                ]),
                'compliance_rate': metrics['compliance_rate']
            }
            
            # Create report
            report = ComplianceReport(
                id=f"REP_{start_date.strftime('%Y%m%d')}_{end_date.strftime('%Y%m%d')}",
                period_start=start_date,
                period_end=end_date,
                summary=summary,
                alerts=period_alerts,
                metrics=metrics,
                charts=charts,
                timestamp=datetime.now()
            )
            
            # Export report
            self._export_report(report, report_type)
            
            return report
            
        except Exception as e:
            self.logger.error(f"Report generation failed: {str(e)}")
            raise
    
    def send_report(
        self,
        report: ComplianceReport,
        recipients: List[str]
    ) -> None:
        """Send compliance report via email
        
        Args:
            report: Report to send
            recipients: Email recipients
        """
        try:
            # Create message
            msg = MIMEMultipart()
            msg['Subject'] = f"Compliance Report {report.id}"
            msg['From'] = self.config['smtp_config']['sender']
            msg['To'] = ', '.join(recipients)
            
            # Add report content
            template = self.template_env.get_template('report_email.html')
            html = template.render(report=report)
            msg.attach(MIMEText(html, 'html'))
            
            # Add PDF attachment
            pdf_path = f"reports/{report.id}.pdf"
            with open(pdf_path, 'rb') as f:
                pdf = MIMEApplication(f.read(), _subtype='pdf')
                pdf.add_header(
                    'Content-Disposition',
                    'attachment',
                    filename=f"{report.id}.pdf"
                )
                msg.attach(pdf)
            
            # Send email
            with smtplib.SMTP_SSL(
                self.config['smtp_config']['host'],
                self.config['smtp_config']['port']
            ) as server:
                server.login(
                    self.config['smtp_config']['username'],
                    self.config['smtp_config']['password']
                )
                server.send_message(msg)
            
            self.logger.info(f"Sent report {report.id} to {len(recipients)} recipients")
            
        except Exception as e:
            self.logger.error(f"Report sending failed: {str(e)}")
            raise
    
    def _process_violation(self, violation: Dict[str, any]) -> None:
        """Process violation and create alert
        
        Args:
            violation: Violation data
        """
        # Determine severity
        severity = self._determine_severity(violation)
        
        # Create alert
        alert = ComplianceAlert(
            id=f"ALT_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            severity=severity,
            title=violation['title'],
            description=violation['description'],
            content_id=violation['content_id'],
            violation_type=violation['type'],
            details=violation.get('details', {}),
            timestamp=datetime.now()
        )
        
        # Add to alerts
        self.alerts.append(alert)
        
        # Send immediate alert if high severity
        if severity == 'high':
            self._send_immediate_alert(alert)
    
    def _determine_severity(self, violation: Dict[str, any]) -> str:
        """Determine alert severity
        
        Args:
            violation: Violation data
            
        Returns:
            Severity level
        """
        thresholds = self.config['alert_thresholds']
        
        if violation.get('impact_score', 0) >= thresholds['high']:
            return 'high'
        elif violation.get('impact_score', 0) >= thresholds['medium']:
            return 'medium'
        else:
            return 'low'
    
    def _send_immediate_alert(self, alert: ComplianceAlert) -> None:
        """Send immediate alert for high severity issues
        
        Args:
            alert: Alert to send
        """
        try:
            # Create message
            msg = MIMEMultipart()
            msg['Subject'] = f"High Severity Compliance Alert: {alert.title}"
            msg['From'] = self.config['smtp_config']['sender']
            msg['To'] = ', '.join(self.config['alert_recipients'])
            
            # Add alert content
            template = self.template_env.get_template('alert_email.html')
            html = template.render(alert=alert)
            msg.attach(MIMEText(html, 'html'))
            
            # Send email
            with smtplib.SMTP_SSL(
                self.config['smtp_config']['host'],
                self.config['smtp_config']['port']
            ) as server:
                server.login(
                    self.config['smtp_config']['username'],
                    self.config['smtp_config']['password']
                )
                server.send_message(msg)
            
        except Exception as e:
            self.logger.error(f"Immediate alert sending failed: {str(e)}")
    
    def _calculate_metrics(
        self,
        alerts: List[ComplianceAlert]
    ) -> Dict[str, float]:
        """Calculate compliance metrics
        
        Args:
            alerts: List of alerts to analyze
            
        Returns:
            Dictionary of metrics
        """
        total = len(alerts)
        if total == 0:
            return {
                'compliance_rate': 100.0,
                'resolution_rate': 100.0,
                'avg_resolution_time': 0.0
            }
        
        resolved = len([a for a in alerts if a.is_resolved])
        
        # Calculate resolution times
        resolution_times = []
        for alert in alerts:
            if alert.is_resolved:
                resolution_time = (
                    datetime.now() - alert.timestamp
                ).total_seconds() / 3600  # hours
                resolution_times.append(resolution_time)
        
        return {
            'compliance_rate': (1 - (total / self.config['baseline_volume'])) * 100,
            'resolution_rate': (resolved / total) * 100,
            'avg_resolution_time': sum(resolution_times) / len(resolution_times) if resolution_times else 0
        }
    
    def _generate_charts(
        self,
        alerts: List[ComplianceAlert]
    ) -> Dict[str, str]:
        """Generate charts for report
        
        Args:
            alerts: List of alerts to visualize
            
        Returns:
            Dictionary mapping chart names to HTML
        """
        charts = {}
        
        # Severity distribution
        severity_counts = pd.Series([a.severity for a in alerts]).value_counts()
        fig = go.Figure(data=[
            go.Pie(
                labels=severity_counts.index,
                values=severity_counts.values,
                hole=.3
            )
        ])
        charts['severity_distribution'] = fig.to_html(
            full_html=False,
            include_plotlyjs='cdn'
        )
        
        # Alert trend
        dates = pd.date_range(
            min(a.timestamp for a in alerts),
            max(a.timestamp for a in alerts),
            freq='D'
        )
        daily_counts = pd.Series(
            [a.timestamp.date() for a in alerts]
        ).value_counts().reindex(dates.date, fill_value=0)
        
        fig = go.Figure(data=[
            go.Scatter(
                x=daily_counts.index,
                y=daily_counts.values,
                mode='lines+markers'
            )
        ])
        charts['alert_trend'] = fig.to_html(
            full_html=False,
            include_plotlyjs='cdn'
        )
        
        return charts
    
    def _export_report(
        self,
        report: ComplianceReport,
        report_type: str
    ) -> None:
        """Export report to file
        
        Args:
            report: Report to export
            report_type: Type of report
        """
        try:
            # Get template
            template = self.template_env.get_template(f"{report_type}_report.html")
            
            # Render report
            html = template.render(report=report)
            
            # Save HTML
            with open(f"reports/{report.id}.html", 'w') as f:
                f.write(html)
            
            # Convert to PDF
            # TODO: Implement PDF conversion
            
            self.logger.info(f"Exported report {report.id}")
            
        except Exception as e:
            self.logger.error(f"Report export failed: {str(e)}")
            raise