#!/usr/bin/env python3
"""
Verification script to check if the RAG system is properly set up.
Run this before starting to ensure everything is in place.
"""

import sys
from pathlib import Path
import subprocess

def check_python_version():
    """Check if Python version is adequate."""
    version = sys.version_info
    if version.major >= 3 and version.minor >= 10:
        print(f"✅ Python version: {version.major}.{version.minor}.{version.micro}")
        return True
    else:
        print(f"❌ Python version: {version.major}.{version.minor}.{version.micro} (need 3.10+)")
        return False

def check_file_exists(filepath, description):
    """Check if a file exists."""
    if Path(filepath).exists():
        print(f"✅ {description}: {filepath}")
        return True
    else:
        print(f"❌ {description} missing: {filepath}")
        return False

def check_directory_exists(dirpath, description):
    """Check if a directory exists."""
    path = Path(dirpath)
    if path.exists() and path.is_dir():
        print(f"✅ {description}: {dirpath}")
        return True
    else:
        print(f"❌ {description} missing: {dirpath}")
        return False

def check_venv():
    """Check if virtual environment exists."""
    venv_path = Path(".venv")
    if venv_path.exists():
        print(f"✅ Virtual environment: .venv/")
        # Check if it has required packages
        pip_path = venv_path / "bin" / "pip"
        if pip_path.exists():
            print("✅ pip installed in virtual environment")
            return True
        else:
            print("⚠️  Virtual environment exists but pip not found")
            return False
    else:
        print("❌ Virtual environment not found: .venv/")
        return False

def check_dependencies():
    """Check if key dependencies can be imported."""
    print("\n📦 Checking key dependencies...")
    dependencies = [
        ("fastapi", "FastAPI"),
        ("lancedb", "LanceDB"),
        ("sentence_transformers", "Sentence Transformers"),
        ("tiktoken", "tiktoken"),
    ]
    
    all_ok = True
    for module, name in dependencies:
        try:
            __import__(module)
            print(f"✅ {name} installed")
        except ImportError:
            print(f"❌ {name} not installed")
            all_ok = False
    
    return all_ok

def check_lm_studio():
    """Check if LM Studio is accessible."""
    try:
        import requests
        response = requests.get("http://localhost:1234/v1/models", timeout=2)
        if response.status_code == 200:
            print("✅ LM Studio is running and accessible")
            return True
        else:
            print("⚠️  LM Studio responded but may have issues")
            return False
    except:
        print("⚠️  LM Studio not accessible (this is OK if you haven't started it yet)")
        return False

def main():
    print("=" * 60)
    print("  RAG System Verification")
    print("=" * 60)
    print()
    
    checks = []
    
    # Basic checks
    print("🔍 Basic System Checks\n")
    checks.append(check_python_version())
    
    # File structure checks
    print("\n📁 File Structure Checks\n")
    checks.append(check_file_exists("requirements.txt", "Requirements file"))
    checks.append(check_file_exists(".env.example", "Environment template"))
    checks.append(check_file_exists("README.md", "README"))
    checks.append(check_file_exists("QUICK_START.md", "Quick Start guide"))
    checks.append(check_file_exists("phase1_extract.py", "Phase 1 script"))
    checks.append(check_file_exists("phase2_embed.py", "Phase 2 script"))
    checks.append(check_file_exists("test_retrieval.py", "Test script"))
    checks.append(check_file_exists("setup.sh", "Setup script"))
    checks.append(check_file_exists("run.sh", "Run script"))
    
    # Directory checks
    print("\n📂 Directory Checks\n")
    checks.append(check_directory_exists("app", "App directory"))
    checks.append(check_directory_exists("app/templates", "Templates directory"))
    checks.append(check_directory_exists("documents", "Documents directory"))
    checks.append(check_directory_exists("data", "Data directory"))
    
    # App files
    print("\n🎯 Application Files\n")
    checks.append(check_file_exists("app/__init__.py", "App init"))
    checks.append(check_file_exists("app/main.py", "Main application"))
    checks.append(check_file_exists("app/rag_backend.py", "RAG backend"))
    checks.append(check_file_exists("app/templates/index.html", "UI template"))
    
    # Virtual environment
    print("\n🐍 Python Environment\n")
    venv_ok = check_venv()
    if venv_ok:
        checks.append(True)
    else:
        checks.append(False)
        print("\n💡 To create virtual environment, run: ./setup.sh")
    
    # Check if in virtual environment
    if hasattr(sys, 'real_prefix') or (hasattr(sys, 'base_prefix') and sys.base_prefix != sys.prefix):
        print("✅ Running in virtual environment")
        
        # Check dependencies if in venv
        deps_ok = check_dependencies()
        checks.append(deps_ok)
        
        if not deps_ok:
            print("\n💡 To install dependencies, run:")
            print("   source .venv/bin/activate")
            print("   pip install -r requirements.txt")
    else:
        print("⚠️  Not running in virtual environment")
        print("💡 Activate with: source .venv/bin/activate")
    
    # Optional: Check LM Studio
    print("\n🤖 LM Studio Check (Optional)\n")
    lm_studio_ok = check_lm_studio()
    # Don't fail on this
    
    # Summary
    print("\n" + "=" * 60)
    passed = sum(checks)
    total = len(checks)
    
    if passed == total:
        print(f"✅ All checks passed ({passed}/{total})")
        print("\n🎉 System is ready to use!")
        print("\n📖 Next steps:")
        print("   1. Place documents in documents/")
        print("   2. Run: python phase1_extract.py --all")
        print("   3. Run: python phase2_embed.py --all")
        print("   4. Start LM Studio")
        print("   5. Run: ./run.sh")
    else:
        print(f"⚠️  Some checks failed ({passed}/{total} passed)")
        print("\n💡 Please run: ./setup.sh")
        print("   Or see QUICK_START.md for manual setup")
    
    print("=" * 60)
    
    return passed == total

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
