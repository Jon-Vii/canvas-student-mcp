#!/usr/bin/env python
"""
Installation script for Canvas Student MCP with PDF support.

This script simplifies the installation process by:
1. Detecting if uv or pip should be used
2. Installing the package with PDF support
3. Providing feedback to the user
"""
import os
import sys
import subprocess
import platform

def main():
    """Install Canvas Student MCP with PDF support."""
    print("Canvas Student MCP Installer")
    print("============================")
    
    # Detect if we're in the correct directory
    if not os.path.isfile("pyproject.toml") and not os.path.isfile("setup.py"):
        print("Error: Please run this script from the canvas-student directory")
        print(f"Current directory: {os.getcwd()}")
        return 1
    
    # Detect if uv is available
    try:
        subprocess.run(["uv", "--version"], stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True)
        use_uv = True
        print("✅ UV package manager detected")
    except (subprocess.SubprocessError, FileNotFoundError):
        use_uv = False
        print("ℹ️ UV not found, using pip instead")
    
    # Install the package with PDF support
    print("\nInstalling Canvas Student MCP with PDF support...")
    try:
        if use_uv:
            subprocess.run(["uv", "pip", "install", "-e", ".[pdf]"], check=True)
        else:
            subprocess.run([sys.executable, "-m", "pip", "install", "-e", ".[pdf]"], check=True)
        
        print("\n✅ Installation successful!")
        
        # Show configuration instructions
        print("\nNext steps:")
        print("1. Create a .env file with your Canvas credentials (see .env.example)")
        print("2. Configure Claude Desktop to use this server:")
        
        if platform.system() == "Windows":
            config_path = "%APPDATA%\\Claude\\claude_desktop_config.json"
        else:  # macOS and Linux
            config_path = "~/Library/Application Support/Claude/claude_desktop_config.json"
            
        print(f"   - Edit {config_path}")
        print("   - Add this server to your configuration (see README.md for details)")
        print("3. Restart Claude Desktop")
        
        return 0
    except subprocess.SubprocessError as e:
        print(f"\n❌ Installation failed: {e}")
        return 1

if __name__ == "__main__":
    sys.exit(main()) 