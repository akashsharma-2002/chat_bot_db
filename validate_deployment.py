#!/usr/bin/env python3
"""
Deployment Validation Script for Smart DBA Bot
==============================================

This script validates that all components are ready for Streamlit Cloud deployment.
Run this before deploying to catch any configuration issues.

Usage: python validate_deployment.py
"""

import os
import sys
import importlib.util
from pathlib import Path
import traceback

def check_file_exists(filepath, description):
    """Check if a file exists and report"""
    if Path(filepath).exists():
        print(f"✅ {description}: {filepath}")
        return True
    else:
        print(f"❌ {description}: {filepath} - NOT FOUND")
        return False

def check_import(module_name, description):
    """Check if a module can be imported"""
    try:
        __import__(module_name)
        print(f"✅ {description}: {module_name}")
        return True
    except ImportError as e:
        print(f"❌ {description}: {module_name} - IMPORT ERROR: {e}")
        return False

def check_requirements():
    """Validate requirements.txt"""
    print("\n📦 Checking Requirements...")
    
    if not check_file_exists("requirements.txt", "Requirements file"):
        return False
    
    with open("requirements.txt", "r") as f:
        requirements = f.read()
    
    critical_packages = [
        "streamlit",
        "pandas", 
        "psycopg2-binary",
        "openai",
        "plotly",
        "openpyxl"
    ]
    
    missing_packages = []
    for package in critical_packages:
        if package not in requirements:
            missing_packages.append(package)
    
    if missing_packages:
        print(f"❌ Missing critical packages: {missing_packages}")
        return False
    else:
        print("✅ All critical packages present")
        return True

def check_streamlit_config():
    """Check Streamlit configuration files"""
    print("\n⚙️ Checking Streamlit Configuration...")
    
    streamlit_dir_exists = check_file_exists(".streamlit", "Streamlit config directory")
    config_exists = check_file_exists(".streamlit/config.toml", "Streamlit config file")
    
    # secrets.toml should exist for local dev but not be committed
    if Path(".streamlit/secrets.toml").exists():
        print("⚠️ .streamlit/secrets.toml exists (ensure it's in .gitignore)")
    else:
        print("✅ .streamlit/secrets.toml not present (will use Streamlit Cloud secrets)")
    
    return streamlit_dir_exists and config_exists

def check_source_files():
    """Check all source files can be imported"""
    print("\n📁 Checking Source Files...")
    
    # Check main application file
    app_exists = check_file_exists("app.py", "Main application file")
    
    # Check source directory
    src_exists = check_file_exists("src", "Source directory")
    
    # Check source modules
    src_modules = [
        ("src.env_helper", "Environment helper"),
        ("src.intelligent_live_query", "Query system"),
        ("src.excel_exporter", "Excel exporter"),
    ]
    
    # Add src to path for testing
    sys.path.insert(0, str(Path.cwd()))
    
    all_imports_ok = True
    for module, description in src_modules:
        if not check_import(module, description):
            all_imports_ok = False
    
    return app_exists and src_exists and all_imports_ok

def check_authentication():
    """Check authentication configuration"""
    print("\n🔐 Checking Authentication...")
    
    config_exists = check_file_exists("config.yaml", "Authentication config")
    auth_exists = check_file_exists("simple_auth.py", "Authentication module")
    
    return config_exists and auth_exists

def check_environment_compatibility():
    """Check environment variable handling"""
    print("\n🌍 Checking Environment Compatibility...")
    
    try:
        from src.env_helper import get_env_var, load_database_config
        
        # Test the functions
        test_var = get_env_var("TEST_VAR", "default_value")
        if test_var == "default_value":
            print("✅ Environment helper: get_env_var working")
        
        config = load_database_config()
        if isinstance(config, dict):
            print("✅ Environment helper: load_database_config working")
        
        return True
    except Exception as e:
        print(f"❌ Environment helper error: {e}")
        return False

def check_gitignore():
    """Check .gitignore file"""
    print("\n🙈 Checking .gitignore...")
    
    if not check_file_exists(".gitignore", "Git ignore file"):
        return False
    
    with open(".gitignore", "r") as f:
        gitignore_content = f.read()
    
    critical_ignores = [
        ".env",
        ".streamlit/secrets.toml",
        "__pycache__",
        "*.pyc"
    ]
    
    missing_ignores = []
    for ignore_pattern in critical_ignores:
        if ignore_pattern not in gitignore_content:
            missing_ignores.append(ignore_pattern)
    
    if missing_ignores:
        print(f"⚠️ Missing .gitignore patterns: {missing_ignores}")
        return False
    else:
        print("✅ All critical patterns in .gitignore")
        return True

def main():
    """Run all validation checks"""
    print("🚀 Smart DBA Bot - Streamlit Cloud Deployment Validation")
    print("=" * 60)
    
    checks = [
        check_requirements,
        check_streamlit_config,
        check_source_files,
        check_authentication,
        check_environment_compatibility,
        check_gitignore
    ]
    
    results = []
    for check in checks:
        try:
            result = check()
            results.append(result)
        except Exception as e:
            print(f"❌ Check failed with error: {e}")
            print(traceback.format_exc())
            results.append(False)
    
    print("\n" + "=" * 60)
    print("📊 VALIDATION SUMMARY")
    print("=" * 60)
    
    passed = sum(results)
    total = len(results)
    
    if passed == total:
        print(f"✅ All checks passed! ({passed}/{total})")
        print("\n🎉 Your application is ready for Streamlit Cloud deployment!")
        print("\nNext steps:")
        print("1. Commit and push your changes to GitHub")
        print("2. Create a new app on https://share.streamlit.io")
        print("3. Configure your secrets in Streamlit Cloud dashboard")
        print("4. Deploy and enjoy!")
        return 0
    else:
        print(f"❌ {total - passed} checks failed ({passed}/{total} passed)")
        print("\n🔧 Please fix the issues above before deploying.")
        return 1

if __name__ == "__main__":
    sys.exit(main())
