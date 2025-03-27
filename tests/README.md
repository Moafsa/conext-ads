# Testing Documentation

This directory contains all tests for the Conext Ads system. The tests are organized by module and include both unit tests and integration tests.

## Structure

```
tests/
├── compliance/              # Compliance System tests
│   ├── test_policy.py      # PolicyChecker tests
│   ├── test_moderator.py   # ContentModerator tests
│   ├── test_monitor.py     # RegulatoryMonitor tests
│   └── test_reporter.py    # ComplianceReporter tests
├── data/                   # Test data files
│   ├── test_rules.json     # Sample policy rules
│   ├── test_regulations.json # Sample regulations
│   └── test_image.jpg      # Sample image for testing
├── templates/              # Email and report templates
└── demo.py                # Demonstration script
```

## Running Tests

### Prerequisites

1. Install test dependencies:
```bash
pip install -r requirements-test.txt
```

2. Set up test configuration:
```bash
cp config/compliance/config.example.json config/compliance/config.json
# Edit config.json with your test settings
```

### Running Unit Tests

To run all unit tests:
```bash
pytest tests/
```

To run tests for a specific module:
```bash
pytest tests/compliance/test_policy.py
```

To run tests with coverage report:
```bash
pytest --cov=src tests/
```

### Running the Demo

The demo script provides a comprehensive demonstration of all system components:

```bash
python tests/demo.py
```

This will:
1. Test PolicyChecker with valid and invalid content
2. Test ContentModerator with text and images
3. Test RegulatoryMonitor with compliance checks
4. Test ComplianceReporter with alerts and reports

## Test Data

- `test_rules.json`: Contains sample policy rules for testing the PolicyChecker
- `test_regulations.json`: Contains sample regulations for testing the RegulatoryMonitor
- `test_image.jpg`: Sample image file for testing the ContentModerator

## Adding New Tests

When adding new tests:

1. Follow the existing test structure
2. Use pytest fixtures for common setup
3. Mock external dependencies
4. Include both positive and negative test cases
5. Add appropriate documentation

## Test Coverage

Current test coverage by module:

- PolicyChecker: 95%
- ContentModerator: 92%
- RegulatoryMonitor: 94%
- ComplianceReporter: 91%

## Continuous Integration

Tests are automatically run on:
- Every pull request
- Every merge to main branch
- Nightly builds

## Troubleshooting

Common issues and solutions:

1. **Missing test data**:
   - Ensure all files in `tests/data/` are present
   - Check file permissions

2. **Configuration errors**:
   - Verify config.json is properly formatted
   - Check all required fields are present

3. **Failed image tests**:
   - Ensure test_image.jpg is a valid image file
   - Check image dimensions and format

4. **Network-related test failures**:
   - Check mock configurations
   - Verify API endpoints in test config