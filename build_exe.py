# EyeGuard Windows Executable Builder
# This script packages the Django project into a standalone .exe file
# 
# Prerequisites:
# 1. Install PyInstaller: pip install pyinstaller
# 2. Run this script from the project directory
#
# Usage:
#   python build_exe.py
#   or
#   python build_exe.py --onedir  (creates folder instead of single file)

import subprocess
import sys
import os
from pathlib import Path

def build_exe():
    """Build standalone .exe using PyInstaller"""
    
    project_dir = Path(__file__).parent.absolute()
    dist_dir = project_dir / "dist"
    
    print("=" * 60)
    print("🔨 Building EyeGuard Executable")
    print("=" * 60)
    print()
    
    # Check if PyInstaller is installed
    try:
        import PyInstaller
    except ImportError:
        print("❌ PyInstaller not found!")
        print()
        print("Install it with:")
        print("   pip install pyinstaller")
        print()
        return False
    
    # Build command
    cmd = [
        sys.executable,
        "-m", "PyInstaller",
        "--onefile",  # Single .exe file
        "--console",  # Show console window (so we see errors)
        "--name", "EyeGuard",
    ]
    
    # Add data files
    data_dirs = [
        ("eyeguard", "eyeguard"),
        ("templates", "templates"),
        ("media", "media"),
        ("staticfiles", "staticfiles"),
    ]
    
    for src, dst in data_dirs:
        src_path = project_dir / src
        if src_path.exists():
            cmd.extend(["--add-data", f"{src_path}{os.pathsep}{dst}"])
    
    # Add hidden imports
    hidden_imports = [
        "django",
        "rest_framework",
        "corsheaders",
        "daphne",
        "cv2",
        "torch",
        "torchvision",
        "numpy",
        "ultralytics",
        "channels",
        "channels_redis",
        "whitenoise",
        "whitenoise.middleware",
        "whitenoise.runserver_nostatic",
        "django_filters",
        "PIL",
        "psycopg2",
        "psycopg2._psycopg",
        "dotenv",
        "asgiref",
        "asgiref.sync",
        "asgiref.wsgi",
        "twisted",
        "rest_framework.authentication",
        "rest_framework.permissions",
        "rest_framework.filters",
        "corsheaders.middleware",
        "django.contrib.staticfiles",
        "django.contrib.staticfiles.management.commands.runserver",
    ]

    # Collect all submodules for packages referenced as strings in settings
    collect_all_pkgs = [
        "whitenoise",
        "corsheaders",
        "rest_framework",
        "django_filters",
        "psycopg2",
        "eyeguard",
    ]
    
    for imp in hidden_imports:
        cmd.extend(["--hidden-import", imp])

    for pkg in collect_all_pkgs:
        cmd.extend(["--collect-all", pkg])

    # Add icon if exists
    icon_path = project_dir / "favicon.ico"
    if icon_path.exists():
        cmd.extend(["--icon", str(icon_path)])
    
    # Add the launcher script
    cmd.append(str(project_dir / "launcher.py"))
    
    print("📦 Running PyInstaller...")
    print()
    
    try:
        result = subprocess.run(cmd, cwd=project_dir)
        
        if result.returncode == 0:
            print()
            print("=" * 60)
            print("✅ Build successful!")
            print("=" * 60)
            print()
            print(f"📁 Output: {dist_dir}")
            print()
            print("You can now:")
            print(f"1. Find EyeGuard.exe in: {dist_dir}")
            print("2. Copy it to another Windows machine")
            print("3. Double-click to run (no dependencies needed!)")
            print()
            return True
        else:
            print()
            print("❌ Build failed!")
            return False
            
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

if __name__ == "__main__":
    success = build_exe()
    sys.exit(0 if success else 1)
