/**
 * Unified Text Renderer - Shared between client preview and server rendering
 * This ensures perfect consistency between preview and final output
 */

class UnifiedTextRenderer {
  constructor(ctx, effects) {
    this.ctx = ctx;
    this.effects = effects;
    this.gradientColors = null;
  }

  /**
   * Update effects and recalculate cached values
   */
  updateEffects(effects) {
    this.effects = effects;
    this.preCalculateGradientColors();
  }

  /**
   * Pre-calculate gradient colors for performance
   */
  preCalculateGradientColors() {
    if (!this.gradientColors) {
      this.gradientColors = new Array(101);
    }

    const primary = this.hexToRgb(this.effects.primaryColor);
    const highlight = this.hexToRgb(this.effects.highlightColor);

    for (let i = 0; i <= 100; i++) {
      const progress = i / 100;
      const r = Math.round(primary.r + (highlight.r - primary.r) * progress);
      const g = Math.round(primary.g + (highlight.g - primary.g) * progress);
      const b = Math.round(primary.b + (highlight.b - primary.b) * progress);
      this.gradientColors[i] = `rgb(${r}, ${g}, ${b})`;
    }
  }

  /**
   * Render karaoke text with effects (unified for client and server)
   */
  renderKaraokeText(words, currentTime, canvasWidth, canvasHeight) {
    // Setup text rendering
    const fontFamily = this.getFontFamily();
    this.ctx.font = `${this.effects.fontWeight} ${this.effects.fontSize}px ${fontFamily}`;
    this.ctx.textAlign = "left";
    this.ctx.textBaseline = "middle";

    // Apply base text effects
    this.applyTextEffects();

    // Break words into lines if auto-break is enabled
    const lines = this.effects.autoBreak ? this.breakIntoLines(words) : [words];

    // Calculate position
    const centerX = this.effects.positionX || canvasWidth / 2;
    const baseY = this.effects.positionY || canvasHeight - 150;

    // Calculate total height for centering
    const lineHeight = this.effects.fontSize * (this.effects.lineHeight || 1.2);
    const totalHeight = lines.length * lineHeight;
    let currentY = baseY - totalHeight / 2 + lineHeight / 2;

    // Render each line
    lines.forEach((lineWords) => {
      // Calculate total width for centering this line
      const wordWidths = lineWords.map(
        (word) => this.ctx.measureText(word.word).width
      );
      const totalSpacing =
        (lineWords.length - 1) * (this.effects.wordSpacing || 10);
      const totalWidth =
        wordWidths.reduce((sum, width) => sum + width, 0) + totalSpacing;

      let currentX = centerX - totalWidth / 2;

      // Render each word in the line
      lineWords.forEach((word, index) => {
        const progress = this.getWordProgress(word, currentTime);

        // Render word with effects based on karaoke mode
        this.renderWordWithEffects(word, currentX, currentY, progress);

        currentX += wordWidths[index] + (this.effects.wordSpacing || 10);
      });

      currentY += lineHeight;
    });
  }

  /**
   * Get font family (matching server logic)
   */
  getFontFamily() {
    if (this.effects.fontFamily === "custom" && this.effects.customFontName) {
      return this.effects.customFontName;
    }
    return this.effects.fontFamily || "Arial";
  }

  /**
   * Apply base text effects to canvas context (reset state)
   */
  applyTextEffects() {
    // Reset all effects to clean state
    this.ctx.shadowBlur = 0;
    this.ctx.shadowOffsetX = 0;
    this.ctx.shadowOffsetY = 0;
    this.ctx.shadowColor = "transparent";
    this.ctx.lineWidth = 0;
    this.ctx.strokeStyle = "transparent";

    // Note: Individual effects are applied in proper layer order within each render function
    // This ensures borders appear as outer borders, not overlays
  }

  /**
   * Render text with proper effect layering (optimized for performance)
   */
  renderTextWithLayers(text, x, y, color, glowColor = null, glowIntensity = 0) {
    // Combine all effects into a single render pass for better performance
    this.ctx.save();

    // Apply shadow if enabled
    if (this.effects.enableShadow) {
      this.ctx.shadowColor = this.effects.shadowColor || "#000000";
      this.ctx.shadowBlur = this.effects.shadowBlur || 4;
      this.ctx.shadowOffsetX = this.effects.shadowOffsetX || 2;
      this.ctx.shadowOffsetY = this.effects.shadowOffsetY || 2;
    }

    // Apply glow if specified (combines with shadow)
    if (glowIntensity > 0 && glowColor) {
      const finalGlowColor = this.effects.glowColor || glowColor;
      const glowOpacity = this.effects.glowOpacity || 0.8;
      const glowColorWithOpacity = this.addOpacityToColor(
        finalGlowColor,
        glowOpacity
      );

      // Combine glow with existing shadow
      this.ctx.shadowColor = glowColorWithOpacity;
      this.ctx.shadowBlur = Math.max(this.ctx.shadowBlur, glowIntensity);
    }

    // Render border first (outer border)
    if (this.effects.enableBorder) {
      this.ctx.strokeStyle = this.effects.borderColor || "#000000";
      this.ctx.lineWidth = this.effects.borderWidth || 2;
      this.ctx.strokeText(text, x, y);
    }

    // Render main text with all effects applied
    this.ctx.fillStyle = color;
    this.ctx.fillText(text, x, y);

    this.ctx.restore();
  }

  /**
   * Break words into lines based on maxLineWidth
   */
  breakIntoLines(words) {
    if (!this.effects.autoBreak || !this.effects.maxLineWidth) {
      return [words];
    }

    const lines = [];
    let currentLine = [];
    let currentWidth = 0;
    const wordSpacing = this.effects.wordSpacing || 10;

    words.forEach((word) => {
      const wordWidth = this.ctx.measureText(word.word).width;
      const spaceWidth = currentLine.length > 0 ? wordSpacing : 0;

      if (
        currentWidth + spaceWidth + wordWidth > this.effects.maxLineWidth &&
        currentLine.length > 0
      ) {
        lines.push(currentLine);
        currentLine = [word];
        currentWidth = wordWidth;
      } else {
        currentLine.push(word);
        currentWidth += spaceWidth + wordWidth;
      }
    });

    if (currentLine.length > 0) {
      lines.push(currentLine);
    }

    return lines.length > 0 ? lines : [words];
  }

  /**
   * Render a single word with effects
   */
  renderWordWithEffects(word, x, y, progress) {
    const karaokeMode = this.effects.karaokeMode || "highlight";

    switch (karaokeMode) {
      case "highlight":
        this.renderHighlightWord(word, x, y, progress);
        break;
      case "gradient":
        this.renderGradientWord(word, x, y, progress);
        break;
      case "fill":
        this.renderFillWord(word, x, y, progress);
        break;
      case "bounce":
        this.renderBounceWord(word, x, y, progress);
        break;
      default:
        this.renderHighlightWord(word, x, y, progress);
    }
  }

  /**
   * Render word with highlight effect (optimized layering)
   */
  renderHighlightWord(word, x, y, progress) {
    const isHighlighted = progress > 0 && progress < 1;
    const color = isHighlighted
      ? this.effects.highlightColor
      : this.effects.primaryColor;

    // Use layered rendering for proper effect order
    const glowIntensity = isHighlighted ? this.effects.glowIntensity : 0;
    const glowColor = isHighlighted
      ? this.effects.glowColor || this.effects.highlightColor
      : null;

    this.renderTextWithLayers(word.word, x, y, color, glowColor, glowIntensity);
  }

  /**
   * Render word with gradient effect (optimized layering)
   */
  renderGradientWord(word, x, y, progress) {
    const colorIndex = Math.floor(progress * 100);
    const color = this.gradientColors[colorIndex] || this.effects.primaryColor;

    // Use layered rendering for proper effect order
    const glowIntensity = progress > 0 ? this.effects.glowIntensity : 0;
    const glowColor = progress > 0 ? this.effects.glowColor || color : null;

    this.renderTextWithLayers(word.word, x, y, color, glowColor, glowIntensity);
  }

  /**
   * Render word with fill effect (optimized layering)
   */
  renderFillWord(word, x, y, progress) {
    const wordWidth = this.ctx.measureText(word.word).width;

    // First render the complete word with all base effects
    this.renderTextWithLayers(word.word, x, y, this.effects.primaryColor);

    // Then render the filled portion with clipping
    if (progress > 0) {
      this.ctx.save();

      // Create clipping region for fill effect
      this.ctx.beginPath();
      this.ctx.rect(
        x,
        y - this.effects.fontSize / 2,
        wordWidth * progress,
        this.effects.fontSize
      );
      this.ctx.clip();

      // Render filled part with glow (no border - already drawn)
      const glowIntensity = this.effects.glowIntensity;
      const glowColor = this.effects.highlightColor;

      if (glowIntensity > 0) {
        this.ctx.shadowColor = glowColor;
        this.ctx.shadowBlur = glowIntensity;
        this.ctx.shadowOffsetX = 0;
        this.ctx.shadowOffsetY = 0;
        this.ctx.fillStyle = this.effects.highlightColor;
        this.ctx.fillText(word.word, x, y);
        this.ctx.shadowBlur = 0;
      } else {
        this.ctx.fillStyle = this.effects.highlightColor;
        this.ctx.fillText(word.word, x, y);
      }

      this.ctx.restore();
    }
  }

  /**
   * Render word with bounce effect
   */
  renderBounceWord(word, x, y, progress) {
    const bounceHeight = progress > 0 ? Math.sin(progress * Math.PI) * 20 : 0;
    const scale = progress > 0 ? 1 + Math.sin(progress * Math.PI) * 0.3 : 1;

    this.ctx.save();

    const wordWidth = this.ctx.measureText(word.word).width;
    this.ctx.translate(x + wordWidth / 2, y - bounceHeight);
    this.ctx.scale(scale, scale);
    this.ctx.translate(-wordWidth / 2, 0);

    const color =
      progress > 0 ? this.effects.highlightColor : this.effects.primaryColor;

    // Use layered rendering for proper effect order
    const glowIntensity = progress > 0 ? this.effects.glowIntensity : 0;
    const glowColor = progress > 0 ? this.effects.highlightColor : null;

    this.renderTextWithLayers(word.word, 0, 0, color, glowColor, glowIntensity);

    this.ctx.restore();
  }

  /**
   * Get word progress for animation
   */
  getWordProgress(wordData, currentTime) {
    if (currentTime < wordData.start_time) return 0;
    if (currentTime > wordData.end_time) return 1;

    const duration = wordData.end_time - wordData.start_time;
    const elapsed = currentTime - wordData.start_time;
    return Math.min(
      1,
      (elapsed / duration) * (this.effects.animationSpeed || 1)
    );
  }

  /**
   * Convert hex color to RGB
   */
  hexToRgb(hex) {
    const result = /^#?([a-f\d]{2})([a-f\d]{2})([a-f\d]{2})$/i.exec(hex);
    return result
      ? {
          r: parseInt(result[1], 16),
          g: parseInt(result[2], 16),
          b: parseInt(result[3], 16),
        }
      : { r: 255, g: 255, b: 255 };
  }

  /**
   * Add opacity to a hex color, converting to rgba
   */
  addOpacityToColor(hexColor, opacity) {
    const rgb = this.hexToRgb(hexColor);
    return `rgba(${rgb.r}, ${rgb.g}, ${rgb.b}, ${opacity})`;
  }
}

// Export for both browser and Node.js
if (typeof module !== "undefined" && module.exports) {
  module.exports = UnifiedTextRenderer;
} else if (typeof window !== "undefined") {
  window.UnifiedTextRenderer = UnifiedTextRenderer;
}
