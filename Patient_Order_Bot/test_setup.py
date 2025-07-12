#!/usr/bin/env python3
"""
Test Setup Script for Sannidhay & Pranav's Bot System
=====================================================

This script verifies that all dependencies and configurations are properly set up.
"""

import sys
import os
from pathlib import Path

def test_imports():
    """Test that all required modules can be imported"""
    print("🔍 Testing imports...")
    
    try:
        import selenium
        print("✅ Selenium imported successfully")
    except ImportError as e:
        print(f"❌ Selenium import failed: {e}")
        return False
    
    try:
        import requests
        print("✅ Requests imported successfully")
    except ImportError as e:
        print(f"❌ Requests import failed: {e}")
        return False
    
    try:
        from azure.ai.documentintelligence import DocumentIntelligenceClient
        print("✅ Azure Document Intelligence imported successfully")
    except ImportError as e:
        print(f"❌ Azure Document Intelligence import failed: {e}")
        print("   Install with: pip install azure-ai-documentintelligence")
        return False
    
    try:
        from dotenv import load_dotenv
        print("✅ Python-dotenv imported successfully")
    except ImportError as e:
        print(f"❌ Python-dotenv import failed: {e}")
        return False
    
    return True

def test_directory_structure():
    """Test that all required directories exist"""
    print("\n📁 Testing directory structure...")
    
    base_dir = Path(__file__).parent
    required_dirs = ["Inbox", "Reports", "Downloads", "Downloads/PDFs", "Logs"]
    
    all_good = True
    for dir_name in required_dirs:
        dir_path = base_dir / dir_name
        if dir_path.exists():
            print(f"✅ {dir_name}/ exists")
        else:
            print(f"❌ {dir_name}/ missing")
            all_good = False
    
    return all_good

def test_configuration():
    """Test configuration settings"""
    print("\n⚙️ Testing configuration...")
    
    try:
        from config import validate_config, PG_CONFIG, AZURE_CONFIG
        
        # Test PG config
        if PG_CONFIG["api_key"] == "your_pg_api_key":
            print("⚠️  PG API key needs to be configured")
        else:
            print("✅ PG API key is configured")
        
        # Test Azure config
        if not AZURE_CONFIG["endpoint"]:
            print("⚠️  Azure endpoint needs to be configured")
        else:
            print("✅ Azure endpoint is configured")
        
        if not AZURE_CONFIG["key"]:
            print("⚠️  Azure key needs to be configured")
        else:
            print("✅ Azure key is configured")
        
        return validate_config()
        
    except ImportError as e:
        print(f"❌ Configuration import failed: {e}")
        return False

def test_bot_files():
    """Test that all bot files exist"""
    print("\n🤖 Testing bot files...")
    
    base_dir = Path(__file__).parent
    required_files = [
        "Final_All_Inboxed.py",
        "Final_patient_bot.py", 
        "Final_signed_bot.py",
        "ai_extract_fields.py",
        "main_orchestrator.py",
        "config.py",
        "ReadConfig.py",
        "CommonUtil.py"
    ]
    
    all_good = True
    for file_name in required_files:
        file_path = base_dir / file_name
        if file_path.exists():
            print(f"✅ {file_name} exists")
        else:
            print(f"❌ {file_name} missing")
            all_good = False
    
    return all_good

def main():
    """Run all tests"""
    print("🧪 Testing Sannidhay & Pranav's Bot System Setup")
    print("=" * 50)
    
    tests = [
        ("Imports", test_imports),
        ("Directory Structure", test_directory_structure),
        ("Bot Files", test_bot_files),
        ("Configuration", test_configuration)
    ]
    
    results = []
    for test_name, test_func in tests:
        try:
            result = test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"❌ {test_name} test failed with error: {e}")
            results.append((test_name, False))
    
    print("\n" + "=" * 50)
    print("📊 Test Results Summary:")
    
    all_passed = True
    for test_name, passed in results:
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"   {status} - {test_name}")
        if not passed:
            all_passed = False
    
    print("\n" + "=" * 50)
    if all_passed:
        print("🎉 All tests passed! The bot system is ready to use.")
        print("\nNext steps:")
        print("1. Update config.py with your actual API keys")
        print("2. Run: python main_orchestrator.py")
    else:
        print("⚠️  Some tests failed. Please fix the issues above.")
        print("\nCommon fixes:")
        print("1. Install dependencies: pip install -r requirements.txt")
        print("2. Update config.py with your API keys")
        print("3. Ensure all bot files are present")
    
    return all_passed

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)