"""Policy Checker Module

This module implements automated policy checking for ad content
and campaigns across different advertising platforms.
"""

from typing import Dict, List, Optional, Set
import logging
from dataclasses import dataclass
from datetime import datetime
import json
import re

@dataclass
class PolicyRule:
    """Represents a policy rule"""
    id: str
    platform: str
    category: str
    description: str
    regex_patterns: List[str]
    forbidden_words: Set[str]
    required_elements: Set[str]
    max_length: Optional[int] = None
    min_length: Optional[int] = None
    is_active: bool = True

@dataclass
class PolicyViolation:
    """Represents a policy violation"""
    rule_id: str
    description: str
    severity: str
    location: str
    context: str
    timestamp: datetime

class PolicyChecker:
    """Checks ad content and campaigns for policy compliance"""
    
    def __init__(self, config: Dict[str, any]):
        """Initialize policy checker
        
        Args:
            config: Configuration dictionary containing:
                - rules_path: Path to policy rules file
                - update_interval: Rules update interval in seconds
                - cache_size: Size of results cache
        """
        self.config = config
        self.logger = logging.getLogger(__name__)
        self.rules: Dict[str, PolicyRule] = {}
        self.violation_cache: Dict[str, List[PolicyViolation]] = {}
        
        # Load initial rules
        self._load_rules()
    
    def check_content(
        self,
        content: Dict[str, any],
        platform: str,
        categories: Optional[List[str]] = None
    ) -> List[PolicyViolation]:
        """Check content for policy violations
        
        Args:
            content: Content to check
            platform: Target platform
            categories: Optional list of rule categories to check
            
        Returns:
            List of policy violations
        """
        try:
            violations = []
            content_str = self._prepare_content(content)
            
            # Get applicable rules
            rules = self._get_applicable_rules(platform, categories)
            
            # Check each rule
            for rule in rules:
                # Check regex patterns
                for pattern in rule.regex_patterns:
                    matches = re.finditer(pattern, content_str)
                    for match in matches:
                        violations.append(
                            PolicyViolation(
                                rule_id=rule.id,
                                description=f"Matched forbidden pattern: {pattern}",
                                severity="high",
                                location=f"pos {match.start()}-{match.end()}",
                                context=match.group(0),
                                timestamp=datetime.now()
                            )
                        )
                
                # Check forbidden words
                words = set(re.findall(r'\w+', content_str.lower()))
                forbidden = words.intersection(rule.forbidden_words)
                if forbidden:
                    violations.append(
                        PolicyViolation(
                            rule_id=rule.id,
                            description=f"Found forbidden words: {', '.join(forbidden)}",
                            severity="medium",
                            location="text",
                            context=", ".join(forbidden),
                            timestamp=datetime.now()
                        )
                    )
                
                # Check required elements
                missing = rule.required_elements - set(content.keys())
                if missing:
                    violations.append(
                        PolicyViolation(
                            rule_id=rule.id,
                            description=f"Missing required elements: {', '.join(missing)}",
                            severity="high",
                            location="structure",
                            context=f"Missing: {', '.join(missing)}",
                            timestamp=datetime.now()
                        )
                    )
                
                # Check length constraints
                if rule.max_length and len(content_str) > rule.max_length:
                    violations.append(
                        PolicyViolation(
                            rule_id=rule.id,
                            description=f"Content exceeds max length of {rule.max_length}",
                            severity="medium",
                            location="length",
                            context=f"Length: {len(content_str)}",
                            timestamp=datetime.now()
                        )
                    )
                
                if rule.min_length and len(content_str) < rule.min_length:
                    violations.append(
                        PolicyViolation(
                            rule_id=rule.id,
                            description=f"Content below min length of {rule.min_length}",
                            severity="medium",
                            location="length",
                            context=f"Length: {len(content_str)}",
                            timestamp=datetime.now()
                        )
                    )
            
            # Cache results
            content_hash = self._hash_content(content)
            self.violation_cache[content_hash] = violations
            
            return violations
            
        except Exception as e:
            self.logger.error(f"Policy check failed: {str(e)}")
            raise
    
    def check_campaign(
        self,
        campaign: Dict[str, any],
        platform: str
    ) -> Dict[str, List[PolicyViolation]]:
        """Check entire campaign for policy violations
        
        Args:
            campaign: Campaign data
            platform: Target platform
            
        Returns:
            Dictionary mapping content IDs to violations
        """
        try:
            results = {}
            
            # Check campaign settings
            settings_violations = self.check_content(
                campaign['settings'],
                platform,
                categories=['campaign_settings']
            )
            if settings_violations:
                results['settings'] = settings_violations
            
            # Check each ad
            for ad in campaign.get('ads', []):
                ad_violations = self.check_content(
                    ad,
                    platform,
                    categories=['ad_content']
                )
                if ad_violations:
                    results[ad['id']] = ad_violations
            
            return results
            
        except Exception as e:
            self.logger.error(f"Campaign check failed: {str(e)}")
            raise
    
    def add_rule(self, rule: PolicyRule) -> None:
        """Add new policy rule
        
        Args:
            rule: Rule to add
        """
        try:
            # Validate rule
            if not self._validate_rule(rule):
                raise ValueError("Invalid rule format")
            
            # Add to rules
            self.rules[rule.id] = rule
            
            # Clear cache since rules changed
            self.violation_cache.clear()
            
            self.logger.info(f"Added rule {rule.id}")
            
        except Exception as e:
            self.logger.error(f"Failed to add rule: {str(e)}")
            raise
    
    def update_rule(self, rule_id: str, updates: Dict[str, any]) -> None:
        """Update existing policy rule
        
        Args:
            rule_id: ID of rule to update
            updates: Dictionary of updates to apply
        """
        try:
            if rule_id not in self.rules:
                raise KeyError(f"Rule {rule_id} not found")
            
            # Get current rule
            rule = self.rules[rule_id]
            
            # Apply updates
            for key, value in updates.items():
                if hasattr(rule, key):
                    setattr(rule, key, value)
            
            # Validate updated rule
            if not self._validate_rule(rule):
                raise ValueError("Invalid rule after update")
            
            # Update rule
            self.rules[rule_id] = rule
            
            # Clear cache
            self.violation_cache.clear()
            
            self.logger.info(f"Updated rule {rule_id}")
            
        except Exception as e:
            self.logger.error(f"Failed to update rule: {str(e)}")
            raise
    
    def delete_rule(self, rule_id: str) -> None:
        """Delete policy rule
        
        Args:
            rule_id: ID of rule to delete
        """
        try:
            if rule_id not in self.rules:
                raise KeyError(f"Rule {rule_id} not found")
            
            # Remove rule
            del self.rules[rule_id]
            
            # Clear cache
            self.violation_cache.clear()
            
            self.logger.info(f"Deleted rule {rule_id}")
            
        except Exception as e:
            self.logger.error(f"Failed to delete rule: {str(e)}")
            raise
    
    def _load_rules(self) -> None:
        """Load policy rules from file"""
        try:
            with open(self.config['rules_path']) as f:
                rules_data = json.load(f)
            
            for rule_data in rules_data:
                rule = PolicyRule(**rule_data)
                if self._validate_rule(rule):
                    self.rules[rule.id] = rule
            
            self.logger.info(f"Loaded {len(self.rules)} rules")
            
        except Exception as e:
            self.logger.error(f"Failed to load rules: {str(e)}")
            raise
    
    def _validate_rule(self, rule: PolicyRule) -> bool:
        """Validate policy rule
        
        Args:
            rule: Rule to validate
            
        Returns:
            bool: True if rule is valid
        """
        try:
            # Check required fields
            if not all([rule.id, rule.platform, rule.category]):
                return False
            
            # Validate regex patterns
            for pattern in rule.regex_patterns:
                re.compile(pattern)
            
            # Validate lengths
            if rule.max_length is not None and rule.max_length < 0:
                return False
            if rule.min_length is not None and rule.min_length < 0:
                return False
            if (
                rule.max_length is not None and
                rule.min_length is not None and
                rule.max_length < rule.min_length
            ):
                return False
            
            return True
            
        except Exception:
            return False
    
    def _get_applicable_rules(
        self,
        platform: str,
        categories: Optional[List[str]] = None
    ) -> List[PolicyRule]:
        """Get rules applicable to platform and categories
        
        Args:
            platform: Target platform
            categories: Optional list of rule categories
            
        Returns:
            List of applicable rules
        """
        rules = [
            rule for rule in self.rules.values()
            if rule.is_active and rule.platform == platform
        ]
        
        if categories:
            rules = [
                rule for rule in rules
                if rule.category in categories
            ]
        
        return rules
    
    def _prepare_content(self, content: Dict[str, any]) -> str:
        """Prepare content for checking
        
        Args:
            content: Content dictionary
            
        Returns:
            Prepared content string
        """
        # Convert to string for text-based checks
        if isinstance(content, dict):
            return json.dumps(content)
        return str(content)
    
    def _hash_content(self, content: Dict[str, any]) -> str:
        """Generate hash for content
        
        Args:
            content: Content to hash
            
        Returns:
            Content hash
        """
        return str(hash(json.dumps(content, sort_keys=True)))