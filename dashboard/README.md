# SentriX Dashboard

Real-time monitoring frontend for the SentriX security proxy.

## Stack

- **Next.js 14** (App Router) · **React 18** · **TypeScript**
- **Recharts** — pie chart, bar chart for detection distribution
- No Redux, no extra state libraries — local `useState` + polling

## What It Shows

| Panel | Data Source | Refresh |
|---|---|---|
| MQTT / CoAP message counters | `GET /metrics` | Every 2s |
| Detection count + P95 latency | `GET /metrics` | Every 2s |
| Action distribution (forward/drop/rate_limit) | `GET /metrics` | Every 2s |
| Feature vector anomaly stats (min, mean, P95, max) | `GET /feature-stats` | Every 2s |
| Live event feed | `GET /events` | Every 2s |

## Running

Start the metrics API first (see root `README.md`), then:

```bash
npm install
npm run dev
```

Open `http://localhost:3000`.

The dashboard expects the metrics API at `http://localhost:8080`. This is hardcoded in `app/page.tsx` — change `API_BASE` there if your API runs elsewhere.

## API Endpoints Consumed

| Endpoint | Response |
|---|---|
| `GET /health` | `{ "status": "ok" }` |
| `GET /metrics` | `{ mqtt_msgs, coap_msgs, detections, latency_ms_p95 }` |
| `GET /feature-stats` | `{ total_vectors, by_protocol, anomaly_stats }` |
| `GET /events` | Array of event log entries |

## Files

```
dashboard/
├── app/
│   ├── layout.tsx   # Root layout, global CSS import
│   └── page.tsx     # Main dashboard (all components inline)
└── package.json
```
