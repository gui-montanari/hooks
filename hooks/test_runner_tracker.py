#!/usr/bin/env python3
"""
Test Runner & Tracker
Executes tests and tracks results for analysis
"""

import json
import sys
import argparse
from pathlib import Path

# Add hooks directory to path
sys.path.insert(0, 'hooks')

from test_automation.runner import TestRunner


def main():
    """Main entry point for test runner"""
    parser = argparse.ArgumentParser(description='Run automated tests with tracking')
    
    # Add arguments
    parser.add_argument('command', nargs='?', default='run_tests', 
                       help='Command to execute')
    parser.add_argument('--module', help='Run tests for specific module')
    parser.add_argument('--failed', action='store_true', 
                       help='Run only failed tests')
    parser.add_argument('--not-tested', action='store_true', 
                       help='Run only untested files')
    parser.add_argument('--file', help='Run specific test file')
    parser.add_argument('--since', help='Run tests modified since date')
    parser.add_argument('--pattern', help='Pattern to match test files')
    
    args = parser.parse_args()
    
    # Create runner
    runner = TestRunner()
    
    # Execute based on command
    if args.command == 'run_tests':
        runner.run_tests(
            module=args.module,
            failed_only=args.failed,
            not_tested_only=args.not_tested,
            file_path=args.file,
            since=args.since,
            pattern=args.pattern
        )
    elif args.command == 'status':
        runner.show_status()
    elif args.command == 'analyze':
        runner.analyze_failures()
    else:
        print(f"Unknown command: {args.command}")
        sys.exit(1)


if __name__ == "__main__":
    main()