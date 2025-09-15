/**
 * GPU-Accelerated Karaoke Renderer using WebGL
 * Provides hardware-accelerated text rendering and effects
 */

class GPURenderer {
  constructor(karaokeApp) {
    this.app = karaokeApp;
    this.gl = null;
    this.canvas = null;
    this.programs = {};
    this.buffers = {};
    this.textures = {};
    this.isInitialized = false;
  }

  /**
   * Initialize WebGL context and shaders
   */
  async initialize() {
    if (this.isInitialized) return;

    // Create offscreen canvas for GPU rendering
    this.canvas = new OffscreenCanvas(1920, 1080);
    this.gl =
      this.canvas.getContext("webgl2") || this.canvas.getContext("webgl");

    if (!this.gl) {
      throw new Error("WebGL not supported");
    }

    console.log("GPU Renderer: WebGL context created");

    // Initialize shaders and programs
    await this.initializeShaders();

    // Setup buffers and textures
    this.initializeBuffers();

    this.isInitialized = true;
    console.log("GPU Renderer: Initialization complete");
  }

  /**
   * Initialize WebGL shaders for text rendering and effects
   */
  async initializeShaders() {
    const gl = this.gl;

    // Vertex shader for text rendering
    const vertexShaderSource = `
      attribute vec2 a_position;
      attribute vec2 a_texCoord;
      
      uniform vec2 u_resolution;
      uniform mat3 u_transform;
      
      varying vec2 v_texCoord;
      
      void main() {
        vec3 position = u_transform * vec3(a_position, 1.0);
        
        // Convert from pixels to clip space
        vec2 clipSpace = ((position.xy / u_resolution) * 2.0) - 1.0;
        
        gl_Position = vec4(clipSpace * vec2(1, -1), 0, 1);
        v_texCoord = a_texCoord;
      }
    `;

    // Fragment shader for karaoke text effects
    const fragmentShaderSource = `
      precision mediump float;
      
      uniform sampler2D u_texture;
      uniform vec4 u_primaryColor;
      uniform vec4 u_highlightColor;
      uniform float u_progress;
      uniform int u_effectMode;
      uniform float u_time;
      uniform vec2 u_textBounds;
      
      varying vec2 v_texCoord;
      
      vec4 highlightMode(vec4 textColor, float progress) {
        if (progress > 0.0 && progress < 1.0) {
          return u_highlightColor * textColor.a;
        }
        return u_primaryColor * textColor.a;
      }
      
      vec4 gradientMode(vec4 textColor, float progress) {
        vec4 color = mix(u_primaryColor, u_highlightColor, progress);
        return color * textColor.a;
      }
      
      vec4 fillMode(vec4 textColor, float progress) {
        float fillPosition = v_texCoord.x;
        if (fillPosition < progress) {
          return u_highlightColor * textColor.a;
        }
        return u_primaryColor * textColor.a;
      }
      
      vec4 bounceMode(vec4 textColor, float progress) {
        float bounce = sin(progress * 3.14159) * 0.3 + 1.0;
        vec4 color = mix(u_primaryColor, u_highlightColor, progress);
        return color * textColor.a * bounce;
      }
      
      vec4 waveMode(vec4 textColor, float progress) {
        float wave = sin(v_texCoord.x * 10.0 + u_time * 5.0) * 0.1 + 1.0;
        vec4 color = mix(u_primaryColor, u_highlightColor, progress);
        return color * textColor.a * wave;
      }
      
      void main() {
        vec4 textColor = texture2D(u_texture, v_texCoord);
        
        if (textColor.a < 0.1) {
          discard;
        }
        
        vec4 finalColor;
        
        if (u_effectMode == 0) {
          finalColor = highlightMode(textColor, u_progress);
        } else if (u_effectMode == 1) {
          finalColor = gradientMode(textColor, u_progress);
        } else if (u_effectMode == 2) {
          finalColor = fillMode(textColor, u_progress);
        } else if (u_effectMode == 3) {
          finalColor = bounceMode(textColor, u_progress);
        } else if (u_effectMode == 4) {
          finalColor = waveMode(textColor, u_progress);
        } else {
          finalColor = u_primaryColor * textColor.a;
        }
        
        gl_FragColor = finalColor;
      }
    `;

    // Compile shaders
    const vertexShader = this.compileShader(
      gl.VERTEX_SHADER,
      vertexShaderSource
    );
    const fragmentShader = this.compileShader(
      gl.FRAGMENT_SHADER,
      fragmentShaderSource
    );

    // Create shader program
    this.programs.text = this.createProgram(vertexShader, fragmentShader);

    // Get attribute and uniform locations
    this.programs.text.attributes = {
      position: gl.getAttribLocation(this.programs.text, "a_position"),
      texCoord: gl.getAttribLocation(this.programs.text, "a_texCoord"),
    };

    this.programs.text.uniforms = {
      resolution: gl.getUniformLocation(this.programs.text, "u_resolution"),
      transform: gl.getUniformLocation(this.programs.text, "u_transform"),
      texture: gl.getUniformLocation(this.programs.text, "u_texture"),
      primaryColor: gl.getUniformLocation(this.programs.text, "u_primaryColor"),
      highlightColor: gl.getUniformLocation(
        this.programs.text,
        "u_highlightColor"
      ),
      progress: gl.getUniformLocation(this.programs.text, "u_progress"),
      effectMode: gl.getUniformLocation(this.programs.text, "u_effectMode"),
      time: gl.getUniformLocation(this.programs.text, "u_time"),
      textBounds: gl.getUniformLocation(this.programs.text, "u_textBounds"),
    };
  }

  /**
   * Initialize WebGL buffers
   */
  initializeBuffers() {
    const gl = this.gl;

    // Create vertex buffer for quad rendering
    this.buffers.position = gl.createBuffer();
    this.buffers.texCoord = gl.createBuffer();
    this.buffers.indices = gl.createBuffer();

    // Quad vertices (for text rendering)
    const positions = new Float32Array([0, 0, 1, 0, 0, 1, 1, 1]);

    const texCoords = new Float32Array([0, 0, 1, 0, 0, 1, 1, 1]);

    const indices = new Uint16Array([0, 1, 2, 1, 2, 3]);

    // Upload buffer data
    gl.bindBuffer(gl.ARRAY_BUFFER, this.buffers.position);
    gl.bufferData(gl.ARRAY_BUFFER, positions, gl.STATIC_DRAW);

    gl.bindBuffer(gl.ARRAY_BUFFER, this.buffers.texCoord);
    gl.bufferData(gl.ARRAY_BUFFER, texCoords, gl.STATIC_DRAW);

    gl.bindBuffer(gl.ELEMENT_ARRAY_BUFFER, this.buffers.indices);
    gl.bufferData(gl.ELEMENT_ARRAY_BUFFER, indices, gl.STATIC_DRAW);
  }

  /**
   * Render frame using GPU acceleration
   */
  async renderFrameGPU(
    timestamp,
    effects,
    subtitles,
    wordSegments,
    width,
    height
  ) {
    if (!this.isInitialized) {
      await this.initialize();
    }

    const gl = this.gl;

    // Resize canvas if needed
    if (this.canvas.width !== width || this.canvas.height !== height) {
      this.canvas.width = width;
      this.canvas.height = height;
      gl.viewport(0, 0, width, height);
    }

    // Clear canvas
    gl.clearColor(0, 0, 0, 1);
    gl.clear(gl.COLOR_BUFFER_BIT);

    // Find active subtitle
    const activeSubtitle = subtitles.find(
      (sub) => timestamp >= sub.start_time && timestamp <= sub.end_time
    );

    if (!activeSubtitle) {
      return this.getFrameData();
    }

    // Get words for this subtitle
    const words = wordSegments.filter(
      (word) =>
        word.start_time >= activeSubtitle.start_time &&
        word.end_time <= activeSubtitle.end_time
    );

    if (words.length === 0) {
      return this.getFrameData();
    }

    // Render words with GPU acceleration
    await this.renderWordsGPU(words, timestamp, effects, width, height);

    return this.getFrameData();
  }

  /**
   * Render words using GPU shaders
   */
  async renderWordsGPU(words, currentTime, effects, width, height) {
    const gl = this.gl;

    // Use text shader program
    gl.useProgram(this.programs.text);

    // Set uniforms
    gl.uniform2f(this.programs.text.uniforms.resolution, width, height);
    gl.uniform1f(this.programs.text.uniforms.time, currentTime);

    // Convert colors to WebGL format
    const primaryColor = this.hexToRgba(effects.primaryColor);
    const highlightColor = this.hexToRgba(effects.highlightColor);

    gl.uniform4f(this.programs.text.uniforms.primaryColor, ...primaryColor);
    gl.uniform4f(this.programs.text.uniforms.highlightColor, ...highlightColor);

    // Map karaoke mode to shader effect mode
    const effectModeMap = {
      highlight: 0,
      gradient: 1,
      fill: 2,
      bounce: 3,
      wave: 4,
    };

    gl.uniform1i(
      this.programs.text.uniforms.effectMode,
      effectModeMap[effects.karaokeMode] || 0
    );

    // Enable blending for text transparency
    gl.enable(gl.BLEND);
    gl.blendFunc(gl.SRC_ALPHA, gl.ONE_MINUS_SRC_ALPHA);

    // Calculate layout
    const centerX = effects.positionX;
    const baseY = effects.positionY;

    // Render each word
    for (let i = 0; i < words.length; i++) {
      const word = words[i];
      const progress = this.getWordProgress(
        word,
        currentTime,
        effects.animationSpeed
      );

      // Create text texture for this word
      const textTexture = await this.createTextTexture(word.word, effects);

      // Calculate word position
      const wordX = centerX + i * (effects.fontSize + effects.wordSpacing);
      const wordY = baseY;

      // Set word-specific uniforms
      gl.uniform1f(this.programs.text.uniforms.progress, progress);

      // Create transform matrix for word positioning
      const transform = this.createTransformMatrix(
        wordX,
        wordY,
        effects.fontSize,
        effects.fontSize
      );
      gl.uniformMatrix3fv(
        this.programs.text.uniforms.transform,
        false,
        transform
      );

      // Bind text texture
      gl.activeTexture(gl.TEXTURE0);
      gl.bindTexture(gl.TEXTURE_2D, textTexture);
      gl.uniform1i(this.programs.text.uniforms.texture, 0);

      // Bind buffers and draw
      this.bindBuffersAndDraw();

      // Clean up texture
      gl.deleteTexture(textTexture);
    }

    gl.disable(gl.BLEND);
  }

  /**
   * Create text texture from word
   */
  async createTextTexture(text, effects) {
    const gl = this.gl;

    // Create temporary canvas for text rendering
    const textCanvas = document.createElement("canvas");
    const textCtx = textCanvas.getContext("2d");

    // Set canvas size based on text
    const fontSize = effects.fontSize;
    textCanvas.width = fontSize * text.length * 0.8; // Approximate width
    textCanvas.height = fontSize * 1.5;

    // Setup text rendering
    textCtx.font = `${effects.fontWeight} ${fontSize}px ${effects.fontFamily}`;
    textCtx.textAlign = "left";
    textCtx.textBaseline = "middle";
    textCtx.fillStyle = "#ffffff"; // White for texture, color applied in shader

    // Clear canvas
    textCtx.clearRect(0, 0, textCanvas.width, textCanvas.height);

    // Draw text
    textCtx.fillText(text, 0, textCanvas.height / 2);

    // Create WebGL texture
    const texture = gl.createTexture();
    gl.bindTexture(gl.TEXTURE_2D, texture);

    // Upload canvas to texture
    gl.texImage2D(
      gl.TEXTURE_2D,
      0,
      gl.RGBA,
      gl.RGBA,
      gl.UNSIGNED_BYTE,
      textCanvas
    );

    // Set texture parameters
    gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_WRAP_S, gl.CLAMP_TO_EDGE);
    gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_WRAP_T, gl.CLAMP_TO_EDGE);
    gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_MIN_FILTER, gl.LINEAR);
    gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_MAG_FILTER, gl.LINEAR);

    return texture;
  }

  /**
   * Bind buffers and draw quad
   */
  bindBuffersAndDraw() {
    const gl = this.gl;

    // Bind position buffer
    gl.bindBuffer(gl.ARRAY_BUFFER, this.buffers.position);
    gl.enableVertexAttribArray(this.programs.text.attributes.position);
    gl.vertexAttribPointer(
      this.programs.text.attributes.position,
      2,
      gl.FLOAT,
      false,
      0,
      0
    );

    // Bind texture coordinate buffer
    gl.bindBuffer(gl.ARRAY_BUFFER, this.buffers.texCoord);
    gl.enableVertexAttribArray(this.programs.text.attributes.texCoord);
    gl.vertexAttribPointer(
      this.programs.text.attributes.texCoord,
      2,
      gl.FLOAT,
      false,
      0,
      0
    );

    // Bind index buffer and draw
    gl.bindBuffer(gl.ELEMENT_ARRAY_BUFFER, this.buffers.indices);
    gl.drawElements(gl.TRIANGLES, 6, gl.UNSIGNED_SHORT, 0);
  }

  /**
   * Create 3x3 transform matrix
   */
  createTransformMatrix(x, y, width, height) {
    return new Float32Array([width, 0, x, 0, height, y, 0, 0, 1]);
  }

  /**
   * Get word progress for animation
   */
  getWordProgress(wordData, currentTime, animationSpeed) {
    if (currentTime < wordData.start_time) return 0;
    if (currentTime > wordData.end_time) return 1;

    const duration = wordData.end_time - wordData.start_time;
    const elapsed = currentTime - wordData.start_time;
    return Math.min(1, (elapsed / duration) * animationSpeed);
  }

  /**
   * Convert hex color to RGBA array
   */
  hexToRgba(hex, alpha = 1) {
    const result = /^#?([a-f\d]{2})([a-f\d]{2})([a-f\d]{2})$/i.exec(hex);
    if (!result) return [1, 1, 1, alpha];

    return [
      parseInt(result[1], 16) / 255,
      parseInt(result[2], 16) / 255,
      parseInt(result[3], 16) / 255,
      alpha,
    ];
  }

  /**
   * Get frame data as ImageData
   */
  getFrameData() {
    const gl = this.gl;
    const width = this.canvas.width;
    const height = this.canvas.height;

    // Read pixels from WebGL context
    const pixels = new Uint8Array(width * height * 4);
    gl.readPixels(0, 0, width, height, gl.RGBA, gl.UNSIGNED_BYTE, pixels);

    // Flip Y axis (WebGL has origin at bottom-left)
    const flippedPixels = new Uint8Array(width * height * 4);
    for (let y = 0; y < height; y++) {
      const srcRow = (height - 1 - y) * width * 4;
      const dstRow = y * width * 4;
      flippedPixels.set(pixels.subarray(srcRow, srcRow + width * 4), dstRow);
    }

    return {
      data: Array.from(flippedPixels),
      width,
      height,
    };
  }

  /**
   * Compile WebGL shader
   */
  compileShader(type, source) {
    const gl = this.gl;
    const shader = gl.createShader(type);

    gl.shaderSource(shader, source);
    gl.compileShader(shader);

    if (!gl.getShaderParameter(shader, gl.COMPILE_STATUS)) {
      const error = gl.getShaderInfoLog(shader);
      gl.deleteShader(shader);
      throw new Error(`Shader compilation error: ${error}`);
    }

    return shader;
  }

  /**
   * Create WebGL program
   */
  createProgram(vertexShader, fragmentShader) {
    const gl = this.gl;
    const program = gl.createProgram();

    gl.attachShader(program, vertexShader);
    gl.attachShader(program, fragmentShader);
    gl.linkProgram(program);

    if (!gl.getProgramParameter(program, gl.LINK_STATUS)) {
      const error = gl.getProgramInfoLog(program);
      gl.deleteProgram(program);
      throw new Error(`Program linking error: ${error}`);
    }

    return program;
  }

  /**
   * Cleanup GPU resources
   */
  cleanup() {
    if (!this.gl) return;

    const gl = this.gl;

    // Delete programs
    Object.values(this.programs).forEach((program) => {
      if (program) gl.deleteProgram(program);
    });

    // Delete buffers
    Object.values(this.buffers).forEach((buffer) => {
      if (buffer) gl.deleteBuffer(buffer);
    });

    // Delete textures
    Object.values(this.textures).forEach((texture) => {
      if (texture) gl.deleteTexture(texture);
    });

    this.programs = {};
    this.buffers = {};
    this.textures = {};
    this.isInitialized = false;
  }
}

// Export for use in main application
if (typeof module !== "undefined" && module.exports) {
  module.exports = GPURenderer;
} else if (typeof window !== "undefined") {
  window.GPURenderer = GPURenderer;
}
