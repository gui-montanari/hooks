#!/usr/bin/env python3
"""
Test script for Migration Guardian hook
"""

import json
import subprocess
import sys


def test_hook():
    """Test the Migration Guardian hook with sample data"""
    
    # Sample hook data simulating a model change
    hook_data = {
        "tool": "Edit",
        "params": {
            "file_path": "app/auth/models/user.py",
            "old_string": "class User(Base):\n    __tablename__ = \"users\"\n    id = Column(Integer, primary_key=True)",
            "new_string": "class User(Base):\n    __tablename__ = \"users\"\n    id = Column(Integer, primary_key=True)\n    is_verified = Column(Boolean, default=False)"
        }
    }
    
    print("🧪 Testing Migration Guardian Hook...")
    print("="*60)
    print(f"Simulating edit to: {hook_data['params']['file_path']}")
    print("="*60)
    
    # Run the hook
    try:
        process = subprocess.Popen(
            ['python', 'hooks/migration_guardian.py'],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        
        stdout, stderr = process.communicate(input=json.dumps(hook_data))
        
        if stdout:
            print("📤 Output:")
            print(stdout)
            
        if stderr:
            print("❌ Errors:")
            print(stderr)
            
        if process.returncode == 0:
            print("\n✅ Hook executed successfully!")
        else:
            print(f"\n❌ Hook failed with return code: {process.returncode}")
            
    except Exception as e:
        print(f"❌ Error running hook: {e}")
        

def test_config():
    """Test configuration loading"""
    print("\n🔧 Testing Configuration...")
    print("="*60)
    
    try:
        from migration_guardian.utils.config import load_config
        config = load_config()
        
        print("✅ Configuration loaded successfully!")
        print(f"   Auto-generate: {config.get('auto_generate', False)}")
        print(f"   Require review: {config.get('require_review', True)}")
        print(f"   Monitored paths: {len(config.get('monitored_paths', []))}")
        
    except Exception as e:
        print(f"❌ Error loading config: {e}")


def test_detectors():
    """Test the detector modules"""
    print("\n🔍 Testing Detectors...")
    print("="*60)
    
    try:
        from migration_guardian.detectors.model_detector import ModelChangeDetector
        from migration_guardian.detectors.dependency_detector import DependencyDetector
        from migration_guardian.utils.config import load_config
        
        config = load_config()
        
        model_detector = ModelChangeDetector(config)
        dep_detector = DependencyDetector(config)
        
        print("✅ Detectors initialized successfully!")
        
    except Exception as e:
        print(f"❌ Error initializing detectors: {e}")


if __name__ == "__main__":
    print("🛡️  MIGRATION GUARDIAN TEST SUITE")
    print("="*60)
    
    # Add hooks to path
    sys.path.insert(0, 'hooks')
    
    # Run tests
    test_config()
    test_detectors()
    test_hook()
    
    print("\n🏁 Test complete!")