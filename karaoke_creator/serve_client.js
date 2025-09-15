/**
 * Simple HTTP server to serve the karaoke client application
 */

const express = require("express");
const path = require("path");

const app = express();
const port = 8080;

// Serve static files from the root directory
app.use(express.static("."));

// Serve the main application
app.get("/", (req, res) => {
  res.sendFile(path.join(__dirname, "index.html"));
});

app.listen(port, () => {
  console.log(`🎤 Karaoke Client Application running at:`);
  console.log(`   📱 Local:    http://localhost:${port}`);
  console.log(`   🌐 Network:  http://127.0.0.1:${port}`);
  console.log(`\n🎬 Server API running at:`);
  console.log(`   🔧 API:      http://localhost:3001`);
  console.log(`   📊 Health:   http://localhost:3001/health`);
  console.log(`\n✨ Ready to test karaoke video rendering!`);
});
