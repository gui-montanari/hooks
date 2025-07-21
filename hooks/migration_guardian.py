#!/usr/bin/env python3
"""
Migration Guardian Hook Entry Point
"""

import sys
import json

# Add hooks directory to path to import the module
sys.path.insert(0, 'hooks')

from migration_guardian.main import MigrationGuardian


def main():
    """Hook entry point"""
    # Read hook data from stdin
    hook_data = json.loads(sys.stdin.read())
    
    # Run Migration Guardian
    guardian = MigrationGuardian()
    guardian.run(hook_data)


if __name__ == "__main__":
    main()