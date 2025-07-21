#!/usr/bin/env python3
"""
Test Generator Hook
Automatically generates tests when code is created or modified
"""

import json
import sys
import os
from pathlib import Path
from typing import Dict, Any

# Add hooks directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from test_automation.main import TestGenerator


def main():
    """Hook entry point"""
    try:
        # Read hook data from stdin
        hook_data = json.loads(sys.stdin.read())
        
        # Create and run test generator
        generator = TestGenerator()
        generator.run(hook_data)
        
    except Exception as e:
        print(f"❌ Test Generator Error: {e}", file=sys.stderr)


if __name__ == "__main__":
    main()