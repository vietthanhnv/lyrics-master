# Building Lyric-to-Subtitle App

This document provides comprehensive instructions for building standalone executables of the Lyric-to-Subtitle App for Windows, macOS, and Linux.

## Prerequisites

### System Requirements

- **Python 3.9 or later** (3.11 recommended)
- **4GB RAM minimum** (8GB recommended for building)
- **10GB free disk space** (for dependencies and build artifacts)
- **Internet connection** (for downloading dependencies)

### Platform-Specific Requirements

#### Windows

- Windows 10 or later
- Visual Studio Build Tools or Visual Studio Community (for some Python packages)
- Windows SDK (optional, for code signing)

#### macOS

- macOS 10.15 (Catalina) or later
- Xcode Command Line Tools: `xcode-select --install`
- Homebrew (recommended): `/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"`

#### Linux

- Ubuntu 20.04+, Fedora 35+, Debian 11+, or equivalent
- Build tools: `sudo apt install build-essential` (Ubuntu/Debian)
- Audio libraries: `sudo apt install libasound2-dev libportaudio2 libsndfile1`

## Quick Start

### 1. Clone and Setup

```bash
git clone <repository-url>
cd lyric-to-subtitle-app

# Create virtual environment (recommended)
python -m venv venv

# Activate virtual environment
# Windows:
venv\Scripts\activate
# macOS/Linux:
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
pip install -r requirements-build.txt
```

### 2. Build for Your Platform

#### Windows

```cmd
build_scripts\build_windows.bat
```

#### macOS

```bash
chmod +x build_scripts/build_macos.sh
./build_scripts/build_macos.sh
```

#### Linux

```bash
chmod +x build_scripts/build_linux.sh
./build_scripts/build_linux.sh
```

## Advanced Building

### Using the Python Build Script

For more control over the build process, use the Python build script directly:

```bash
python build_scripts/build.py [options]

Options:
  --debug         Enable debug mode (larger executable, more verbose output)
  --no-clean      Skip cleaning build directories (faster rebuilds)
```

### Customizing the Build

#### Modifying the Spec File

The `lyric_to_subtitle_app.spec` file controls how PyInstaller builds the executable. Key sections:

- **`hiddenimports`**: Add modules that PyInstaller might miss
- **`datas`**: Include additional data files
- **`excludes`**: Exclude unnecessary modules to reduce size

#### Build Configuration

Edit `build_config.yaml` to customize:

- Application metadata
- Dependencies to include/exclude
- Platform-specific settings
- Optimization options

### Build Optimization

#### Reducing Executable Size

1. **Enable UPX compression** (if available):

   ```bash
   # Install UPX
   # Windows: Download from https://upx.github.io/
   # macOS: brew install upx
   # Linux: sudo apt install upx-ucl
   ```

2. **Exclude unnecessary dependencies**:
   Edit the `excludes` list in `lyric_to_subtitle_app.spec`

3. **Use one-directory mode** (default):
   Faster startup than one-file mode

#### Improving Startup Time

1. **Disable UPX compression**:
   Set `upx=False` in the spec file

2. **Use one-directory distribution**:
   Default setting, faster than one-file

3. **Optimize imports**:
   Use lazy imports in the application code

## Distribution

### Windows

The build creates `dist/LyricToSubtitleApp.exe` along with supporting files.

**Distribution options:**

- Zip the entire `dist` folder
- Create an installer using tools like NSIS or Inno Setup
- Use Windows Store packaging (MSIX)

### macOS

The build creates `dist/LyricToSubtitleApp.app`.

**Distribution options:**

- Create a DMG: `hdiutil create -volname "Lyric-to-Subtitle App" -srcfolder dist/LyricToSubtitleApp.app -ov -format UDZO LyricToSubtitleApp.dmg`
- Zip the .app bundle
- Submit to Mac App Store (requires Apple Developer account)

### Linux

The build creates `dist/LyricToSubtitleApp/` directory with the executable.

**Distribution options:**

- Create a tarball: `tar -czf LyricToSubtitleApp-linux.tar.gz -C dist LyricToSubtitleApp/`
- Create a .deb package (Debian/Ubuntu)
- Create a .rpm package (Fedora/RHEL)
- Use AppImage format
- Create a Flatpak package

## Code Signing and Notarization

### Windows Code Signing

1. Obtain a code signing certificate
2. Install the certificate
3. Modify the spec file to include signing:
   ```python
   exe = EXE(
       # ... other parameters ...
       codesign_identity="Your Certificate Name",
   )
   ```

### macOS Code Signing and Notarization

1. Join the Apple Developer Program
2. Create certificates in Xcode or Developer Portal
3. Sign the app:
   ```bash
   codesign --deep --force --verify --verbose --sign "Developer ID Application: Your Name" dist/LyricToSubtitleApp.app
   ```
4. Notarize with Apple:
   ```bash
   xcrun notarytool submit LyricToSubtitleApp.dmg --apple-id your@email.com --password app-specific-password --team-id TEAMID
   ```

### Linux Package Signing

For distribution through repositories:

```bash
# Sign with GPG
gpg --armor --sign --detach-sig LyricToSubtitleApp-linux.tar.gz
```

## Troubleshooting

### Common Build Issues

#### Missing Dependencies

```
ImportError: No module named 'module_name'
```

**Solution:** Add the module to `hiddenimports` in the spec file

#### Large Executable Size

**Solutions:**

- Enable UPX compression
- Exclude unnecessary modules
- Use virtual environment with minimal dependencies

#### Slow Startup

**Solutions:**

- Disable UPX compression
- Use one-directory mode
- Optimize application imports

#### Platform-Specific Issues

**Windows:**

- "MSVCP140.dll not found": Install Visual C++ Redistributable
- Antivirus false positives: Submit to antivirus vendors for whitelisting

**macOS:**

- "App is damaged": Code sign the application
- Gatekeeper warnings: Notarize with Apple

**Linux:**

- Missing shared libraries: Install system dependencies
- Permission denied: Make executable with `chmod +x`

### Debug Mode

Build with debug mode for troubleshooting:

```bash
python build_scripts/build.py --debug
```

This creates a more verbose executable that shows import information and error details.

### Build Logs

Check build logs in:

- `build/` directory for PyInstaller logs
- Console output during build process
- `dist/` directory for final artifacts

## Continuous Integration

### GitHub Actions Example

```yaml
name: Build Executables

on: [push, pull_request]

jobs:
  build:
    strategy:
      matrix:
        os: [windows-latest, macos-latest, ubuntu-latest]

    runs-on: ${{ matrix.os }}

    steps:
      - uses: actions/checkout@v3

      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: "3.11"

      - name: Install dependencies
        run: |
          pip install -r requirements.txt
          pip install -r requirements-build.txt

      - name: Build executable
        run: python build_scripts/build.py

      - name: Upload artifacts
        uses: actions/upload-artifact@v3
        with:
          name: executable-${{ matrix.os }}
          path: dist/
```

## Support

For build-related issues:

1. Check this documentation
2. Review the troubleshooting section
3. Check existing issues on GitHub
4. Create a new issue with:
   - Operating system and version
   - Python version
   - Complete error message
   - Build command used

## Contributing

When contributing build improvements:

1. Test on all supported platforms
2. Update this documentation
3. Update the build configuration files
4. Ensure backward compatibility
5. Add appropriate error handling
