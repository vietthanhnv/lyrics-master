#!/usr/bin/env python3
"""
Cross-platform build script for Lyric-to-Subtitle App.

This script handles building standalone executables for Windows, macOS, and Linux
using PyInstaller with platform-specific configurations.
"""

import os
import sys
import shutil
import subprocess
import platform
import argparse
from pathlib import Path
from typing import List, Optional


class BuildError(Exception):
    """Custom exception for build errors."""
    pass


class AppBuilder:
    """Handles building the application for different platforms."""
    
    def __init__(self, project_root: Path):
        self.project_root = project_root
        self.build_dir = project_root / "build"
        self.dist_dir = project_root / "dist"
        self.spec_file = project_root / "lyric_to_subtitle_app.spec"
        
    def clean_build_dirs(self) -> None:
        """Clean previous build artifacts."""
        print("🧹 Cleaning previous build artifacts...")
        
        for dir_path in [self.build_dir, self.dist_dir]:
            if dir_path.exists():
                shutil.rmtree(dir_path)
                print(f"   Removed {dir_path}")
        
        # Clean __pycache__ directories
        for pycache in self.project_root.rglob("__pycache__"):
            shutil.rmtree(pycache)
            print(f"   Removed {pycache}")
    
    def check_dependencies(self) -> None:
        """Check if required build dependencies are installed."""
        print("🔍 Checking build dependencies...")
        
        required_packages = ["pyinstaller", "PyQt6"]
        missing_packages = []
        
        for package in required_packages:
            try:
                __import__(package.lower().replace("-", "_"))
                print(f"   ✅ {package} is installed")
            except ImportError:
                missing_packages.append(package)
                print(f"   ❌ {package} is missing")
        
        if missing_packages:
            raise BuildError(
                f"Missing required packages: {', '.join(missing_packages)}\n"
                f"Install with: pip install {' '.join(missing_packages)}"
            )
    
    def run_pyinstaller(self, debug: bool = False) -> None:
        """Run PyInstaller with the spec file."""
        print("🔨 Running PyInstaller...")
        
        cmd = [
            sys.executable, "-m", "PyInstaller",
            "--clean",
            "--noconfirm",
        ]
        
        if debug:
            cmd.append("--debug=all")
        
        cmd.append(str(self.spec_file))
        
        print(f"   Command: {' '.join(cmd)}")
        
        try:
            result = subprocess.run(
                cmd,
                cwd=self.project_root,
                check=True,
                capture_output=True,
                text=True
            )
            print("   ✅ PyInstaller completed successfully")
            
        except subprocess.CalledProcessError as e:
            print(f"   ❌ PyInstaller failed with return code {e.returncode}")
            print(f"   stdout: {e.stdout}")
            print(f"   stderr: {e.stderr}")
            raise BuildError(f"PyInstaller failed: {e}")
    
    def get_output_info(self) -> dict:
        """Get information about the built executable."""
        system = platform.system().lower()
        
        if system == "windows":
            exe_name = "LyricToSubtitleApp.exe"
            exe_path = self.dist_dir / exe_name
        elif system == "darwin":
            exe_name = "LyricToSubtitleApp.app"
            exe_path = self.dist_dir / exe_name
        else:  # Linux
            exe_name = "LyricToSubtitleApp"
            exe_path = self.dist_dir / "LyricToSubtitleApp" / exe_name
        
        return {
            "name": exe_name,
            "path": exe_path,
            "exists": exe_path.exists(),
            "size": exe_path.stat().st_size if exe_path.exists() else 0
        }
    
    def create_installer_info(self) -> None:
        """Create installer information and instructions."""
        system = platform.system().lower()
        output_info = self.get_output_info()
        
        info_file = self.dist_dir / "INSTALLATION_INFO.txt"
        
        with open(info_file, "w") as f:
            f.write("Lyric-to-Subtitle App - Installation Information\n")
            f.write("=" * 50 + "\n\n")
            
            f.write(f"Platform: {platform.system()} {platform.release()}\n")
            f.write(f"Architecture: {platform.machine()}\n")
            f.write(f"Built on: {platform.node()}\n\n")
            
            if system == "windows":
                f.write("Windows Installation:\n")
                f.write("1. Extract the executable to your desired location\n")
                f.write("2. Run LyricToSubtitleApp.exe\n")
                f.write("3. On first run, Windows may show a security warning\n")
                f.write("4. Click 'More info' then 'Run anyway' if prompted\n\n")
                
            elif system == "darwin":
                f.write("macOS Installation:\n")
                f.write("1. Drag LyricToSubtitleApp.app to your Applications folder\n")
                f.write("2. Right-click the app and select 'Open' for first run\n")
                f.write("3. Click 'Open' when macOS asks about unidentified developer\n")
                f.write("4. Subsequent runs can use normal double-click\n\n")
                
            else:  # Linux
                f.write("Linux Installation:\n")
                f.write("1. Extract the LyricToSubtitleApp folder to your desired location\n")
                f.write("2. Make the executable file executable: chmod +x LyricToSubtitleApp\n")
                f.write("3. Run ./LyricToSubtitleApp from the extracted folder\n")
                f.write("4. You may need to install additional system dependencies\n\n")
            
            f.write("System Requirements:\n")
            f.write("- 4GB RAM minimum (8GB recommended)\n")
            f.write("- 2GB free disk space for models\n")
            f.write("- Internet connection for initial model download\n")
            f.write("- Audio device for playback (optional)\n\n")
            
            f.write("First Run:\n")
            f.write("- The app will download AI models on first use\n")
            f.write("- This may take several minutes depending on your connection\n")
            f.write("- Models are cached locally for future use\n\n")
            
            f.write("Troubleshooting:\n")
            f.write("- If the app fails to start, check system requirements\n")
            f.write("- Ensure you have sufficient disk space for model downloads\n")
            f.write("- Check firewall settings if model downloads fail\n")
            f.write("- For support, visit: https://github.com/lyric-to-subtitle-app/issues\n")
        
        print(f"📄 Created installation info: {info_file}")
    
    def build(self, debug: bool = False, clean: bool = True) -> None:
        """Build the application."""
        print(f"🚀 Building Lyric-to-Subtitle App for {platform.system()}...")
        
        try:
            if clean:
                self.clean_build_dirs()
            
            self.check_dependencies()
            self.run_pyinstaller(debug=debug)
            
            output_info = self.get_output_info()
            
            if output_info["exists"]:
                size_mb = output_info["size"] / (1024 * 1024)
                print(f"✅ Build completed successfully!")
                print(f"   Output: {output_info['path']}")
                print(f"   Size: {size_mb:.1f} MB")
                
                self.create_installer_info()
                
            else:
                raise BuildError(f"Expected output not found: {output_info['path']}")
                
        except Exception as e:
            print(f"❌ Build failed: {e}")
            raise


def main():
    """Main build script entry point."""
    parser = argparse.ArgumentParser(
        description="Build Lyric-to-Subtitle App for current platform"
    )
    parser.add_argument(
        "--debug", 
        action="store_true", 
        help="Enable debug mode for PyInstaller"
    )
    parser.add_argument(
        "--no-clean", 
        action="store_true", 
        help="Skip cleaning build directories"
    )
    
    args = parser.parse_args()
    
    # Get project root directory
    script_dir = Path(__file__).parent
    project_root = script_dir.parent
    
    try:
        builder = AppBuilder(project_root)
        builder.build(debug=args.debug, clean=not args.no_clean)
        
        print("\n🎉 Build process completed successfully!")
        print(f"📦 Executable available in: {builder.dist_dir}")
        
    except BuildError as e:
        print(f"\n💥 Build failed: {e}")
        sys.exit(1)
    except KeyboardInterrupt:
        print("\n⏹️  Build cancelled by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n💥 Unexpected error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()