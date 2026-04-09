'use client';

import { useEffect, useState, useCallback } from 'react';
import {
  PieChart, Pie, Cell,
  BarChart, Bar,
  XAxis, YAxis, CartesianGrid, Tooltip,
  ResponsiveContainer,
} from 'recharts';

/* ── Types ──────────────────────────────────────────────────────────── */
type Metrics = {
  mqtt_msgs: number;
  coap_msgs: number;
  detections: number;
  latency_ms_p95: number;
};

type FeatureStats = {
  total_vectors: number;
  by_protocol: { mqtt: number; coap: number; unknown: number };
  anomaly_stats: { min: number; max: number; mean: number; p95: number };
};

type EventEntry = {
  ts?: string;
  timestamp?: string;
  type?: string;
  level?: string;
  msg?: string;
  message?: string;
  protocol?: string;
  source_id?: string;
  anomaly_score?: number;
  action?: string;
  [key: string]: unknown;
};

/* ── Custom Tooltip ─────────────────────────────────────────────────── */
function CustomTooltip({ active, payload, label }: { active?: boolean; payload?: Array<{ value: number; name: string }>; label?: string }) {
  if (!active || !payload?.length) return null;
  return (
    <div className="custom-tooltip">
      {label && <div className="label">{label}</div>}
      {payload.map((p, i) => (
        <div className="value" key={i}>
          {typeof p.value === 'number' ? p.value.toFixed(4) : p.value}
        </div>
      ))}
    </div>
  );
}

/* ── Main Dashboard ─────────────────────────────────────────────────── */
export default function Dashboard() {
  const [metrics, setMetrics] = useState<Metrics | null>(null);
  const [featureStats, setFeatureStats] = useState<FeatureStats | null>(null);
  const [events, setEvents] = useState<EventEntry[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [lastUpdate, setLastUpdate] = useState<string>('');

  const base = process.env.NEXT_PUBLIC_METRICS_BASE_URL ?? 'http://localhost:8080';

  const fetchData = useCallback(async () => {
    try {
      setError(null);

      const [metricsRes, statsRes, eventsRes] = await Promise.allSettled([
        fetch(`${base}/metrics`),
        fetch(`${base}/features/stats`),
        fetch(`${base}/events`),
      ]);

      if (metricsRes.status === 'fulfilled' && metricsRes.value.ok) {
        setMetrics(await metricsRes.value.json() as Metrics);
      }
      if (statsRes.status === 'fulfilled' && statsRes.value.ok) {
        setFeatureStats(await statsRes.value.json() as FeatureStats);
      }
      if (eventsRes.status === 'fulfilled' && eventsRes.value.ok) {
        const data = await eventsRes.value.json();
        setEvents(Array.isArray(data?.events) ? data.events : []);
      }

      setLastUpdate(new Date().toLocaleTimeString());
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setLoading(false);
    }
  }, [base]);

  useEffect(() => {
    fetchData();
    const interval = setInterval(fetchData, 5000);
    return () => clearInterval(interval);
  }, [fetchData]);

  /* ── Loading state ────────────────────────────────────────────────── */
  if (loading && !metrics) {
    return (
      <main className="dashboard">
        <div className="loading-screen">
          <div className="loading-spinner" />
          <div className="loading-text">Connecting to SentriX metrics…</div>
        </div>
      </main>
    );
  }

  /* ── Error state ──────────────────────────────────────────────────── */
  if (error && !metrics) {
    return (
      <main className="dashboard">
        <div className="error-screen">
          <div className="error-icon">⚠️</div>
          <div className="error-title">Connection Failed</div>
          <div className="error-detail">
            Unable to reach the metrics server. Make sure it&apos;s running and accessible.
          </div>
          <code className="error-code">python deploy/scripts/metrics_api_stub.py</code>
        </div>
      </main>
    );
  }

  /* ── No data ──────────────────────────────────────────────────────── */
  if (!metrics) {
    return (
      <main className="dashboard">
        <div className="error-screen">
          <div className="error-icon">📡</div>
          <div className="error-title">No Data</div>
          <div className="error-detail">
            The metrics server is reachable but returned no data. Run a scenario script to generate traffic.
          </div>
        </div>
      </main>
    );
  }

  /* ── Derived data ─────────────────────────────────────────────────── */
  const totalMessages = metrics.mqtt_msgs + metrics.coap_msgs;

  const protocolData = [
    { name: 'MQTT', value: metrics.mqtt_msgs, color: '#38bdf8' },
    { name: 'CoAP', value: metrics.coap_msgs, color: '#fbbf24' },
  ];

  const anomalyData = featureStats
    ? [
        { name: 'Min', value: featureStats.anomaly_stats.min },
        { name: 'Mean', value: featureStats.anomaly_stats.mean },
        { name: 'P95', value: featureStats.anomaly_stats.p95 },
        { name: 'Max', value: featureStats.anomaly_stats.max },
      ]
    : [];

  /* ── Event helpers ────────────────────────────────────────────────── */
  function getEventBadge(ev: EventEntry): { label: string; className: string } {
    const t = (ev.type ?? ev.level ?? '').toLowerCase();
    if (t.includes('detect') || t.includes('attack') || t.includes('anomal')) {
      return { label: 'Detection', className: 'event-badge detection' };
    }
    if (t.includes('warn')) {
      return { label: 'Warning', className: 'event-badge warning' };
    }
    return { label: 'Info', className: 'event-badge info' };
  }

  function getEventTime(ev: EventEntry): string {
    const raw = ev.ts ?? ev.timestamp ?? '';
    if (!raw) return '—';
    try {
      return new Date(raw).toLocaleTimeString();
    } catch {
      return String(raw).slice(0, 19);
    }
  }

  function getEventMessage(ev: EventEntry): string {
    return ev.msg ?? ev.message ?? JSON.stringify(ev).slice(0, 120);
  }

  /* ── Render ───────────────────────────────────────────────────────── */
  return (
    <main className="dashboard">
      {/* ─── Header ──────────────────────────────────────────────────── */}
      <header className="header">
        <div className="header-left">
          <div className="logo-area">
            <div className="logo-icon">S</div>
            <h1>SentriX Dashboard</h1>
          </div>
          <p className="header-subtitle">
            Real-time IoT security proxy metrics &amp; detection telemetry
          </p>
        </div>
        <div className="header-right">
          <div className={`status-badge ${error ? 'error' : ''}`}>
            <span className="status-dot" />
            {error ? 'Degraded' : 'Live'}
          </div>
          {lastUpdate && (
            <span className="update-time">{lastUpdate}</span>
          )}
        </div>
      </header>

      {/* ─── KPI Metric Cards ────────────────────────────────────────── */}
      <section className="metrics-grid">
        <div className="card metric-card cyan" style={{ animationDelay: '0.05s' }}>
          <div className="metric-label">📨 MQTT Messages</div>
          <div className="metric-value cyan">{metrics.mqtt_msgs.toLocaleString()}</div>
          <div className="metric-detail">
            {totalMessages > 0
              ? `${((metrics.mqtt_msgs / totalMessages) * 100).toFixed(1)}% of total traffic`
              : 'No traffic yet'}
          </div>
        </div>

        <div className="card metric-card amber" style={{ animationDelay: '0.1s' }}>
          <div className="metric-label">📡 CoAP Messages</div>
          <div className="metric-value amber">{metrics.coap_msgs.toLocaleString()}</div>
          <div className="metric-detail">
            {totalMessages > 0
              ? `${((metrics.coap_msgs / totalMessages) * 100).toFixed(1)}% of total traffic`
              : 'No traffic yet'}
          </div>
        </div>

        <div className="card metric-card rose" style={{ animationDelay: '0.15s' }}>
          <div className="metric-label">🛡️ Detection Events</div>
          <div className="metric-value rose">{metrics.detections.toLocaleString()}</div>
          <div className="metric-detail">
            {totalMessages > 0
              ? `${((metrics.detections / totalMessages) * 100).toFixed(2)}% detection rate`
              : 'Awaiting traffic'}
          </div>
        </div>

        <div className="card metric-card violet" style={{ animationDelay: '0.2s' }}>
          <div className="metric-label">⚡ Latency P95</div>
          <div className="metric-value violet">
            {metrics.latency_ms_p95.toFixed(1)}
            <span className="metric-unit">ms</span>
          </div>
          <div className="metric-detail">95th percentile response time</div>
        </div>
      </section>

      {/* ─── Charts Row ──────────────────────────────────────────────── */}
      <section className="content-grid">
        {/* Protocol Distribution */}
        <div className="card" style={{ animationDelay: '0.25s' }}>
          <div className="card-title">
            <span className="card-title-icon">📊</span> Protocol Distribution
          </div>
          <div className="chart-wrapper">
            <ResponsiveContainer width="100%" height={240}>
              <PieChart>
                <Pie
                  data={protocolData}
                  cx="50%"
                  cy="50%"
                  innerRadius={55}
                  outerRadius={90}
                  paddingAngle={4}
                  dataKey="value"
                  label={({ name, percent }: { name?: string; percent?: number }) => `${name ?? ''} ${((percent ?? 0) * 100).toFixed(0)}%`}
                  labelLine={false}
                  stroke="none"
                >
                  {protocolData.map((entry, i) => (
                    <Cell key={i} fill={entry.color} />
                  ))}
                </Pie>
                <Tooltip content={<CustomTooltip />} />
              </PieChart>
            </ResponsiveContainer>
          </div>
          <div style={{ display: 'flex', justifyContent: 'center', gap: '1.5rem', marginTop: '0.5rem' }}>
            {protocolData.map((p) => (
              <div key={p.name} style={{ display: 'flex', alignItems: 'center', gap: '0.4rem', fontSize: '0.78rem' }}>
                <span style={{ width: 10, height: 10, borderRadius: '50%', background: p.color, display: 'inline-block' }} />
                <span style={{ color: 'var(--text-secondary)' }}>{p.name}</span>
                <span style={{ fontWeight: 700, color: 'var(--text-primary)', fontVariantNumeric: 'tabular-nums' }}>
                  {p.value.toLocaleString()}
                </span>
              </div>
            ))}
          </div>
        </div>

        {/* Feature Vector Stats */}
        <div className="card" style={{ animationDelay: '0.3s' }}>
          <div className="card-title">
            <span className="card-title-icon">🧬</span> Feature Vectors
          </div>
          {featureStats ? (
            <div className="stats-grid">
              <div className="stat-item">
                <div className="stat-label">Total Vectors</div>
                <div className="stat-value" style={{ color: 'var(--text-primary)' }}>
                  {featureStats.total_vectors.toLocaleString()}
                </div>
              </div>
              <div className="stat-item">
                <div className="stat-label">MQTT Vectors</div>
                <div className="stat-value" style={{ color: 'var(--accent-cyan)' }}>
                  {featureStats.by_protocol.mqtt.toLocaleString()}
                </div>
              </div>
              <div className="stat-item">
                <div className="stat-label">CoAP Vectors</div>
                <div className="stat-value" style={{ color: 'var(--accent-amber)' }}>
                  {featureStats.by_protocol.coap.toLocaleString()}
                </div>
              </div>
              <div className="stat-item">
                <div className="stat-label">Unknown Protocol</div>
                <div className="stat-value" style={{ color: 'var(--text-muted)' }}>
                  {featureStats.by_protocol.unknown.toLocaleString()}
                </div>
              </div>
            </div>
          ) : (
            <div className="empty-state">
              <div className="empty-state-icon">🔬</div>
              <div className="empty-state-text">Feature stats unavailable — run a scenario to generate vectors</div>
            </div>
          )}
        </div>
      </section>

      {/* ─── Anomaly Chart + Events ──────────────────────────────────── */}
      <section className="content-grid">
        {/* Anomaly Score Distribution */}
        <div className="card" style={{ animationDelay: '0.35s' }}>
          <div className="card-title">
            <span className="card-title-icon">📈</span> Anomaly Score Distribution
          </div>
          {anomalyData.length > 0 ? (
            <div className="chart-wrapper">
              <ResponsiveContainer width="100%" height={260}>
                <BarChart data={anomalyData} barSize={36}>
                  <CartesianGrid strokeDasharray="3 3" vertical={false} />
                  <XAxis
                    dataKey="name"
                    tick={{ fill: '#8b9dc3', fontSize: 12 }}
                    axisLine={{ stroke: 'rgba(56,89,138,0.20)' }}
                    tickLine={false}
                  />
                  <YAxis
                    domain={[0, 1]}
                    tick={{ fill: '#8b9dc3', fontSize: 12 }}
                    axisLine={false}
                    tickLine={false}
                    tickFormatter={(v: number) => v.toFixed(1)}
                  />
                  <Tooltip content={<CustomTooltip />} cursor={{ fill: 'rgba(56,189,248,0.06)' }} />
                  <defs>
                    <linearGradient id="barGrad" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="0%" stopColor="#a78bfa" stopOpacity={1} />
                      <stop offset="100%" stopColor="#8b5cf6" stopOpacity={0.7} />
                    </linearGradient>
                  </defs>
                  <Bar dataKey="value" fill="url(#barGrad)" radius={[6, 6, 0, 0]} />
                </BarChart>
              </ResponsiveContainer>
            </div>
          ) : (
            <div className="empty-state">
              <div className="empty-state-icon">📉</div>
              <div className="empty-state-text">No anomaly data available yet</div>
            </div>
          )}
        </div>

        {/* Live Event Log */}
        <div className="card" style={{ animationDelay: '0.4s' }}>
          <div className="card-title">
            <span className="card-title-icon">📋</span> Event Log
            {events.length > 0 && (
              <span style={{
                marginLeft: 'auto',
                fontSize: '0.65rem',
                color: 'var(--text-muted)',
                fontWeight: 500,
                fontVariantNumeric: 'tabular-nums',
              }}>
                {events.length} events
              </span>
            )}
          </div>
          {events.length > 0 ? (
            <div className="events-list">
              {[...events].reverse().slice(0, 50).map((ev, i) => {
                const badge = getEventBadge(ev);
                return (
                  <div className="event-item" key={i} style={{ animationDelay: `${i * 0.03}s` }}>
                    <div className="event-header">
                      <span className="event-time">{getEventTime(ev)}</span>
                      <span className={badge.className}>{badge.label}</span>
                    </div>
                    <div className="event-message">{getEventMessage(ev)}</div>
                    {(ev.protocol || ev.source_id || ev.anomaly_score !== undefined) && (
                      <div className="event-detail">
                        {ev.protocol && <span>protocol={ev.protocol} </span>}
                        {ev.source_id && <span>src={ev.source_id} </span>}
                        {ev.anomaly_score !== undefined && (
                          <span>score={Number(ev.anomaly_score).toFixed(4)}</span>
                        )}
                      </div>
                    )}
                  </div>
                );
              })}
            </div>
          ) : (
            <div className="empty-state">
              <div className="empty-state-icon">📭</div>
              <div className="empty-state-text">
                No events recorded yet. Events will appear here when the proxy processes traffic.
              </div>
            </div>
          )}
        </div>
      </section>

      {/* ─── Footer ──────────────────────────────────────────────────── */}
      <footer className="footer">
        <div className="footer-info">
          <span className="footer-tag">📊 Metrics: {base}</span>
          <span className="footer-tag">🔌 MQTT: localhost:1884</span>
          <span className="footer-tag">📡 CoAP: localhost:5684</span>
        </div>
        <div className="footer-info">
          <span className="footer-tag">🔄 Auto-refresh: 5s</span>
        </div>
      </footer>
    </main>
  );
}
