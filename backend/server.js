/**
 * server.js - Express.js API Gateway
 *
 * Acts as the single entry point for the frontend.
 * Calls the FastAPI ML microservice internally for predictions.
 * Serves precomputed cache for heatmaps and business stats.
 *
 * Install:
 *   npm install express axios node-cache cors dotenv
 *
 * Run:
 *   node server.js
 *   (make sure ml_service.py is running on port 8001 first)
 */

const express  = require("express");
const axios    = require("axios");
const NodeCache = require("node-cache");
const cors     = require("cors");
const fs       = require("fs");
const path     = require("path");
require("dotenv").config();

const app    = express();
const PORT   = process.env.PORT   || 5000;
const ML_URL = process.env.ML_URL || "http://localhost:8001";

// ── Cache: TTL 24 hours for precomputed results ───────────────────────────────
const cache = new NodeCache({ stdTTL: 86400, checkperiod: 3600 });

app.use(cors());
app.use(express.json());

// ── Load precomputed cache from disk on startup ───────────────────────────────
const CACHE_FILE = path.join(__dirname, "precomputed_cache.json");

function loadPrecomputedCache() {
  if (fs.existsSync(CACHE_FILE)) {
    const data = JSON.parse(fs.readFileSync(CACHE_FILE, "utf8"));
    Object.entries(data).forEach(([key, value]) => cache.set(key, value));
    console.log(`✅ Loaded ${Object.keys(data).length} precomputed entries from disk`);
  } else {
    console.log("⚠️  No precomputed cache found. Run precompute_cache.py first.");
  }
}
loadPrecomputedCache();


// ═══════════════════════════════════════════════════════════════════════════════
// ENDPOINT 1 - GET /api/recommendations
// Returns top 3 posting times for a given platform, follower count, content type.
//
// Query params:
//   platform     : "instagram" | "tiktok"
//   followers    : number
//   content      : "Reel" | "Image" | "Carousel" | "Video"
//   month        : 1–12 (optional, default 5)
//   top_n        : 1–10 (optional, default 3)
//
// Example:
//   GET /api/recommendations?platform=instagram&followers=5000&content=Reel
// ═══════════════════════════════════════════════════════════════════════════════
app.get("/api/recommendations", async (req, res) => {
  const { platform, followers, content, month = 5, top_n = 3 } = req.query;

  // Validation
  if (!platform || !followers || !content) {
    return res.status(400).json({
      error: "Missing required params: platform, followers, content"
    });
  }

  const followerCount = parseInt(followers);
  if (isNaN(followerCount) || followerCount < 0) {
    return res.status(400).json({ error: "followers must be a positive number" });
  }

  // Auto-correct content_type: TikTok only supports Video
  const correctedContent = "Video"; // TikTok only

  // Check cache first (key based on inputs)
  const cacheKey = `rec:${platform}:${followerCount}:${correctedContent}:${month}`;
  const cached   = cache.get(cacheKey);
  if (cached) {
    return res.json({ ...cached, cached: true });
  }

  try {
    const mlRes = await axios.get(`${ML_URL}/predict/recommendations`, {
      params: {
        platform,
        followers    : followerCount,
        content_type : correctedContent,
        month,
        top_n,
      },
      timeout: 10000,
    });

    const result = mlRes.data;
    cache.set(cacheKey, result);
    return res.json({ ...result, cached: false });

  } catch (err) {
    console.error("ML service error:", err.message);
    if (err.response?.data?.detail) {
      return res.status(400).json({ error: err.response.data.detail });
    }
    return res.status(503).json({ error: "ML service unavailable. Is ml_service.py running?" });
  }
});


// ═══════════════════════════════════════════════════════════════════════════════
// ENDPOINT 2 - GET /api/heatmap
// Returns 24×7 engagement score matrix (hour × day) for a platform.
// Used by the frontend to render the heatmap visualization.
//
// Query params:
//   platform     : "instagram" | "tiktok"
//   followers    : number  (optional, default 5000)
//   content      : content type (optional)
//   month        : 1–12   (optional, default 5)
//
// Example:
//   GET /api/heatmap?platform=instagram
// ═══════════════════════════════════════════════════════════════════════════════
app.get("/api/heatmap", async (req, res) => {
  const { platform, followers = 5000, content = "Reel", month = 5 } = req.query;

  if (!platform) {
    return res.status(400).json({ error: "Missing required param: platform" });
  }

  // Check precomputed cache first (heatmaps are expensive, precomputed at startup)
  const cacheKey = `heatmap:${platform}:${content}:${month}`;
  const cached   = cache.get(cacheKey);
  if (cached) {
    return res.json({ ...cached, cached: true });
  }

  const heatmapContent = "Video"; // TikTok only

  try {
    const mlRes = await axios.get(`${ML_URL}/predict/heatmap`, {
      params: { platform, followers: parseInt(followers), content_type: heatmapContent, month },
      timeout: 15000,
    });

    const result = mlRes.data;
    cache.set(cacheKey, result);
    return res.json({ ...result, cached: false });

  } catch (err) {
    console.error("ML heatmap error:", err.message);
    return res.status(503).json({ error: "ML service unavailable. Is ml_service.py running?" });
  }
});


// ═══════════════════════════════════════════════════════════════════════════════
// ENDPOINT 3 - GET /api/businesses
// Returns list of all businesses with their platform, follower count,
// post count, avg engagement score, and peak posting hour.
// Served purely from precomputed cache - no ML call needed.
//
// Example:
//   GET /api/businesses
//   GET /api/businesses?platform=instagram
// ═══════════════════════════════════════════════════════════════════════════════
app.get("/api/businesses", (req, res) => {
  const { platform } = req.query;

  const cacheKey = "businesses:all";
  let businesses = cache.get(cacheKey);

  if (!businesses) {
    return res.status(503).json({
      error: "Business stats not loaded. Run precompute_cache.py first."
    });
  }

  // Filter by platform if requested
  if (platform) {
    businesses = businesses.filter(
      b => b.platform.toLowerCase() === platform.toLowerCase()
    );
  }

  return res.json({
    count     : businesses.length,
    businesses,
    cached    : true,
  });
});


// ── Health check ──────────────────────────────────────────────────────────────
app.get("/api/health", async (req, res) => {
  let mlStatus = "unreachable";
  try {
    const r = await axios.get(`${ML_URL}/health`, { timeout: 3000 });
    mlStatus = r.data;
  } catch (_) {}

  res.json({
    express : "ok",
    ml_service: mlStatus,
    cache_keys: cache.keys().length,
  });
});


// ── 404 handler ───────────────────────────────────────────────────────────────
app.use((req, res) => {
  res.status(404).json({
    error: `Route ${req.method} ${req.path} not found`,
    available: [
      "GET /api/recommendations?platform=&followers=&content=",
      "GET /api/heatmap?platform=",
      "GET /api/businesses",
      "GET /api/health",
    ]
  });
});


app.listen(PORT, () => {
  console.log(`\n🚀 Express API running on http://localhost:${PORT}`);
  console.log(`   ML service expected at: ${ML_URL}`);
  console.log("\n   Endpoints:");
  console.log("   GET /api/recommendations?platform=instagram&followers=5000&content=Reel");
  console.log("   GET /api/heatmap?platform=instagram");
  console.log("   GET /api/businesses");
  console.log("   GET /api/health\n");
});