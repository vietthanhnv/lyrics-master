/**
 * Font Setup Script for Server Rendering
 * Downloads and sets up common fonts for karaoke video rendering
 */

const fs = require("fs-extra");
const path = require("path");
const https = require("https");

class FontSetup {
  constructor() {
    this.fontsDir = path.join(__dirname, "fonts");
    this.fontSources = {
      // Google Fonts (Open Source)
      Roboto:
        "https://fonts.gstatic.com/s/roboto/v30/KFOmCnqEu92Fr1Mu4mxK.woff2",
      "Open Sans":
        "https://fonts.gstatic.com/s/opensans/v34/memSYaGs126MiZpBA-UvWbX2vVnXBbObj2OVZyOOSr4dVJWUgsjZ0B4gaVc.woff2",
      Montserrat:
        "https://fonts.gstatic.com/s/montserrat/v25/JTUHjIg1_i6t8kCHKm4532VJOt5-QNFgpCtr6Hw5aXp-obK4.woff2",
      Poppins:
        "https://fonts.gstatic.com/s/poppins/v20/pxiEyp8kv8JHgFVrJJfecg.woff2",
      Lato: "https://fonts.gstatic.com/s/lato/v23/S6uyw4BMUTPHjx4wXiWtFCc.woff2",
    };
  }

  async setupFonts() {
    console.log("🎨 Setting up fonts for server rendering...\n");

    // Ensure fonts directory exists
    await fs.ensureDir(this.fontsDir);

    // Check for system fonts first
    await this.checkSystemFonts();

    // Download web fonts
    await this.downloadWebFonts();

    console.log("\n✅ Font setup complete!");
    console.log("📁 Fonts directory:", this.fontsDir);
    console.log("🎤 Server rendering now has access to all fonts");
  }

  async checkSystemFonts() {
    console.log("🔍 Checking system fonts...");

    const systemFontPaths = {
      Arial: [
        "C:/Windows/Fonts/arial.ttf",
        "/System/Library/Fonts/Arial.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
      ],
      "Times New Roman": [
        "C:/Windows/Fonts/times.ttf",
        "/System/Library/Fonts/Times.ttc",
      ],
      Helvetica: [
        "/System/Library/Fonts/Helvetica.ttc",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
      ],
      Impact: [
        "C:/Windows/Fonts/impact.ttf",
        "/System/Library/Fonts/Impact.ttf",
      ],
      "Comic Sans MS": [
        "C:/Windows/Fonts/comic.ttf",
        "C:/Windows/Fonts/comicbd.ttf",
      ],
    };

    for (const [fontName, paths] of Object.entries(systemFontPaths)) {
      let found = false;
      for (const fontPath of paths) {
        if (await fs.pathExists(fontPath)) {
          console.log(`   ✅ ${fontName}: ${fontPath}`);
          found = true;
          break;
        }
      }
      if (!found) {
        console.log(`   ❌ ${fontName}: Not found`);
      }
    }
  }

  async downloadWebFonts() {
    console.log("\n📥 Downloading web fonts...");
    console.log(
      "Note: For production use, please ensure you have proper licensing for these fonts.\n"
    );

    for (const [fontName, url] of Object.entries(this.fontSources)) {
      try {
        const fontPath = path.join(
          this.fontsDir,
          `${fontName.replace(/\s+/g, "")}.woff2`
        );

        if (await fs.pathExists(fontPath)) {
          console.log(`   ✅ ${fontName}: Already exists`);
          continue;
        }

        console.log(`   📥 Downloading ${fontName}...`);
        await this.downloadFont(url, fontPath);
        console.log(`   ✅ ${fontName}: Downloaded`);
      } catch (error) {
        console.log(`   ❌ ${fontName}: Failed - ${error.message}`);
      }
    }
  }

  async downloadFont(url, outputPath) {
    return new Promise((resolve, reject) => {
      const file = fs.createWriteStream(outputPath);

      https
        .get(url, (response) => {
          if (response.statusCode !== 200) {
            reject(new Error(`HTTP ${response.statusCode}`));
            return;
          }

          response.pipe(file);

          file.on("finish", () => {
            file.close();
            resolve();
          });

          file.on("error", (error) => {
            fs.unlink(outputPath);
            reject(error);
          });
        })
        .on("error", reject);
    });
  }

  /**
   * Create font installation guide
   */
  createFontGuide() {
    const guide = `# Font Installation Guide

## System Fonts (Automatically Available)
- Arial (Windows/Mac/Linux)
- Times New Roman (Windows/Mac)
- Helvetica (Mac/Linux)
- Impact (Windows/Mac)

## Custom Fonts for Karaoke
For best karaoke video results, consider these font types:

### Bold Display Fonts
- **Impact** - Strong, bold text perfect for karaoke
- **Arial Black** - Clean, readable bold font
- **Bebas Neue** - Modern condensed font

### Script/Decorative Fonts  
- **Pacifico** - Friendly script font
- **Dancing Script** - Elegant handwriting style
- **Fredoka One** - Playful rounded font

### Professional Fonts
- **Montserrat** - Modern geometric font
- **Roboto** - Clean, readable Google font
- **Open Sans** - Versatile sans-serif

## How to Add Custom Fonts

1. **Upload via Web Interface**:
   - Click "Load Font" button in the app
   - Select .ttf, .otf, .woff, or .woff2 file
   - Font will be available in both preview and server render

2. **Manual Installation**:
   - Copy font files to: \`server/fonts/\`
   - Restart the server
   - Font will be automatically registered

## Font Download Links

### Free Fonts:
- **Google Fonts**: https://fonts.google.com/
- **Font Squirrel**: https://www.fontsquirrel.com/
- **DaFont**: https://www.dafont.com/ (check licenses)

### Recommended Karaoke Fonts:
- **Impact**: Usually pre-installed on Windows
- **Bebas Neue**: https://fonts.google.com/specimen/Bebas+Neue
- **Fredoka One**: https://fonts.google.com/specimen/Fredoka+One
- **Pacifico**: https://fonts.google.com/specimen/Pacifico

## Installation Instructions

1. Download font files (.ttf or .otf preferred)
2. Copy to \`server/fonts/\` directory
3. Restart server
4. Font will appear in font selection dropdown
`;

    fs.writeFileSync(path.join(__dirname, "FONT_GUIDE.md"), guide);
    console.log("\n📖 Created FONT_GUIDE.md with installation instructions");
  }
}

// Run font setup if this file is executed directly
if (require.main === module) {
  const fontSetup = new FontSetup();
  fontSetup
    .setupFonts()
    .then(() => fontSetup.createFontGuide())
    .catch(console.error);
}

module.exports = FontSetup;
