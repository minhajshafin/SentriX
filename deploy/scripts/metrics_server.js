#!/usr/bin/env node

/**
 * Metrics API Server
 * Serves real-time proxy metrics and feature statistics to the dashboard
 * Listens on http://localhost:8080
 * Uses only Node.js built-in modules (no dependencies)
 */

const http = require('http');
const fs = require('fs');
const path = require('path');
const { URL } = require('url');

const PORT = 8080;
const METRICS_FILE = '/tmp/sentrix-week8/metrics.json';
const FEATURES_FILE = '/tmp/sentrix-week8/features.jsonl';

// Helper: Read metrics JSON
function readMetrics() {
  try {
    if (fs.existsSync(METRICS_FILE)) {
      return JSON.parse(fs.readFileSync(METRICS_FILE, 'utf-8'));
    }
    return { mqtt_msgs: 0, coap_msgs: 0, detections: 0, latency_ms_p95: 0 };
  } catch (err) {
    console.error('Error reading metrics:', err.message);
    return { mqtt_msgs: 0, coap_msgs: 0, detections: 0, latency_ms_p95: 0 };
  }
}

// Helper: Read and aggregate feature statistics from JSONL synchronously
function readFeatureStats() {
  const stats = {
    total_vectors: 0,
    by_protocol: { mqtt: 0, coap: 0, unknown: 0 },
    anomaly_stats: { min: 1, max: 0, mean: 0, p95: 0 },
  };

  const anomalyScores = [];

  try {
    if (!fs.existsSync(FEATURES_FILE)) {
      return stats;
    }

    const content = fs.readFileSync(FEATURES_FILE, 'utf-8');
    const lines = content.split('\n').filter(line => line.trim());

    for (const line of lines) {
      try {
        const feature = JSON.parse(line);
        stats.total_vectors += 1;

        // Count by protocol
        if (feature.protocol === 'mqtt') stats.by_protocol.mqtt += 1;
        else if (feature.protocol === 'coap') stats.by_protocol.coap += 1;
        else stats.by_protocol.unknown += 1;

        // Track anomaly scores (nested in decision object)
        if (feature.decision && typeof feature.decision.anomaly_score === 'number') {
          anomalyScores.push(feature.decision.anomaly_score);
        }
      } catch {
        // Skip malformed lines
      }
    }

    // Compute anomaly statistics
    if (anomalyScores.length > 0) {
      stats.anomaly_stats.min = Math.min(...anomalyScores);
      stats.anomaly_stats.max = Math.max(...anomalyScores);
      stats.anomaly_stats.mean = anomalyScores.reduce((a, b) => a + b, 0) / anomalyScores.length;

      // Compute p95
      const sorted = anomalyScores.sort((a, b) => a - b);
      const p95Idx = Math.ceil(sorted.length * 0.95) - 1;
      stats.anomaly_stats.p95 = sorted[Math.max(0, p95Idx)];
    }
  } catch (err) {
    console.error('Error reading feature stats:', err.message);
  }

  return stats;
}

// Simple JSON response helper
function sendJSON(res, data, statusCode = 200) {
  res.writeHead(statusCode, {
    'Content-Type': 'application/json',
    'Access-Control-Allow-Origin': '*',
    'Access-Control-Allow-Methods': 'GET, OPTIONS',
    'Access-Control-Allow-Headers': 'Content-Type',
  });
  res.end(JSON.stringify(data));
}

// Create and start the server
const server = http.createServer((req, res) => {
  const url = new URL(req.url, `http://${req.headers.host}`);
  const pathname = url.pathname;

  // CORS preflight
  if (req.method === 'OPTIONS') {
    res.writeHead(200, {
      'Access-Control-Allow-Origin': '*',
      'Access-Control-Allow-Methods': 'GET, OPTIONS',
      'Access-Control-Allow-Headers': 'Content-Type',
    });
    res.end();
    return;
  }

  // Routes
  if (req.method === 'GET') {
    if (pathname === '/' || pathname === '') {
      sendJSON(res, {
        service: 'SentriX Metrics API',
        endpoints: ['/metrics', '/features/stats', '/health'],
      });
    } else if (pathname === '/metrics') {
      sendJSON(res, readMetrics());
    } else if (pathname === '/features/stats') {
      sendJSON(res, readFeatureStats());
    } else if (pathname === '/health') {
      sendJSON(res, { status: 'ok', timestamp: new Date().toISOString() });
    } else {
      sendJSON(res, { error: 'Not found' }, 404);
    }
  } else {
    sendJSON(res, { error: 'Method not allowed' }, 405);
  }
});

server.listen(PORT, () => {
  console.log(`✅ Metrics server listening on http://localhost:${PORT}`);
  console.log(`   GET /metrics - Proxy metrics (MQTT msgs, CoAP msgs, detections, latency)`);
  console.log(`   GET /features/stats - Feature statistics (vector counts, anomaly distribution)`);
  console.log(`   GET /health - Health check`);
  console.log();
  console.log(`📊 Data source: ${METRICS_FILE}`);
  console.log(`📈 Features: ${FEATURES_FILE}`);
});
