'use client';

import { useEffect, useState } from 'react';
import { PieChart, Pie, Cell, BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer, LineChart, Line } from 'recharts';

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

export default function Dashboard() {
  const [metrics, setMetrics] = useState<Metrics | null>(null);
  const [featureStats, setFeatureStats] = useState<FeatureStats | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [lastUpdate, setLastUpdate] = useState<string>('');

  const metricsBase = process.env.NEXT_PUBLIC_METRICS_BASE_URL ?? 'http://localhost:8080';

  useEffect(() => {
    const fetchData = async () => {
      try {
        setLoading(true);
        setError(null);

        // Fetch metrics
        const metricsRes = await fetch(`${metricsBase}/metrics`);
        if (metricsRes.ok) {
          setMetrics((await metricsRes.json()) as Metrics);
        }

        // Fetch feature stats
        const statsRes = await fetch(`${metricsBase}/features/stats`);
        if (statsRes.ok) {
          setFeatureStats((await statsRes.json()) as FeatureStats);
        }

        setLastUpdate(new Date().toLocaleTimeString());
      } catch (err) {
        setError((err as Error).message);
      } finally {
        setLoading(false);
      }
    };

    fetchData();
    const interval = setInterval(fetchData, 5000); // Refresh every 5s

    return () => clearInterval(interval);
  }, [metricsBase]);

  if (loading && !metrics) {
    return (
      <main style={{ padding: '2rem' }}>
        <div style={{ color: '#999' }}>Loading metrics...</div>
      </main>
    );
  }

  if (error && !metrics) {
    return (
      <main style={{ padding: '2rem' }}>
        <div style={{ color: '#d32f2f' }}>Connection error: {error}</div>
        <p style={{ marginTop: '0.5rem', fontSize: '0.9rem' }}>
          Make sure the metrics server is running: <code>node deploy/scripts/metrics_server.js</code>
        </p>
      </main>
    );
  }

  if (!metrics) {
    return (
      <main style={{ padding: '2rem' }}>
        <div style={{ color: '#666' }}>No metrics data available</div>
      </main>
    );
  }

  // Prepare protocol distribution data
  const protocolData = [
    { name: 'MQTT', value: metrics.mqtt_msgs, fill: '#0ea5e9' },
    { name: 'CoAP', value: metrics.coap_msgs, fill: '#f97316' },
  ];

  // Prepare anomaly distribution data
  const anomalyData = featureStats
    ? [
        { name: 'Min', value: featureStats.anomaly_stats.min },
        { name: 'Mean', value: featureStats.anomaly_stats.mean },
        { name: 'P95', value: featureStats.anomaly_stats.p95 },
        { name: 'Max', value: featureStats.anomaly_stats.max },
      ]
    : [];

  return (
    <main style={{ padding: '2rem', fontFamily: 'system-ui, -apple-system, sans-serif' }}>
      <div style={{ marginBottom: '2rem' }}>
        <h1 style={{ margin: '0 0 0.5rem 0' }}>SentriX Week 9 Dashboard</h1>
        <p style={{ margin: '0', color: '#999', fontSize: '0.9rem' }}>
          Real-time proxy metrics and feature statistics
          {lastUpdate && ` • Last update: ${lastUpdate}`}
        </p>
      </div>

      {/* Key Metrics Grid */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: '1rem', marginBottom: '2rem' }}>
        <div style={{ padding: '1.5rem', border: '1px solid #e5e7eb', borderRadius: '0.5rem', backgroundColor: '#f9fafb' }}>
          <div style={{ fontSize: '0.875rem', color: '#666', marginBottom: '0.5rem' }}>MQTT Messages</div>
          <div style={{ fontSize: '2rem', fontWeight: 'bold', color: '#0ea5e9' }}>{metrics.mqtt_msgs}</div>
        </div>
        <div style={{ padding: '1.5rem', border: '1px solid #e5e7eb', borderRadius: '0.5rem', backgroundColor: '#f9fafb' }}>
          <div style={{ fontSize: '0.875rem', color: '#666', marginBottom: '0.5rem' }}>CoAP Messages</div>
          <div style={{ fontSize: '2rem', fontWeight: 'bold', color: '#f97316' }}>{metrics.coap_msgs}</div>
        </div>
        <div style={{ padding: '1.5rem', border: '1px solid #e5e7eb', borderRadius: '0.5rem', backgroundColor: '#f9fafb' }}>
          <div style={{ fontSize: '0.875rem', color: '#666', marginBottom: '0.5rem' }}>Detection Events</div>
          <div style={{ fontSize: '2rem', fontWeight: 'bold', color: '#10b981' }}>{metrics.detections}</div>
        </div>
        <div style={{ padding: '1.5rem', border: '1px solid #e5e7eb', borderRadius: '0.5rem', backgroundColor: '#f9fafb' }}>
          <div style={{ fontSize: '0.875rem', color: '#666', marginBottom: '0.5rem' }}>Latency P95</div>
          <div style={{ fontSize: '2rem', fontWeight: 'bold', color: '#8b5cf6' }}>{metrics.latency_ms_p95.toFixed(1)} ms</div>
        </div>
      </div>

      {/* Charts */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(350px, 1fr))', gap: '2rem' }}>
        {/* Protocol Distribution */}
        <div style={{ padding: '1.5rem', border: '1px solid #e5e7eb', borderRadius: '0.5rem', backgroundColor: '#fafafa' }}>
          <h2 style={{ margin: '0 0 1rem 0', fontSize: '1.1rem' }}>Message Distribution</h2>
          <ResponsiveContainer width="100%" height={250}>
            <PieChart>
              <Pie data={protocolData} cx="50%" cy="50%" labelLine={false} label={({ name, value }) => `${name}: ${value}`} outerRadius={80} fill="#8884d8" dataKey="value">
                {protocolData.map((entry, index) => (
                  <Cell key={`cell-${index}`} fill={entry.fill} />
                ))}
              </Pie>
              <Tooltip />
            </PieChart>
          </ResponsiveContainer>
        </div>

        {/* Feature Statistics */}
        {featureStats && (
          <div style={{ padding: '1.5rem', border: '1px solid #e5e7eb', borderRadius: '0.5rem', backgroundColor: '#fafafa' }}>
            <h2 style={{ margin: '0 0 1rem 0', fontSize: '1.1rem' }}>Feature Vectors</h2>
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1rem', marginBottom: '1rem' }}>
              <div>
                <div style={{ fontSize: '0.875rem', color: '#666' }}>Total Vectors</div>
                <div style={{ fontSize: '1.5rem', fontWeight: 'bold' }}>{featureStats.total_vectors}</div>
              </div>
              <div>
                <div style={{ fontSize: '0.875rem', color: '#666' }}>MQTT Vectors</div>
                <div style={{ fontSize: '1.5rem', fontWeight: 'bold', color: '#0ea5e9' }}>{featureStats.by_protocol.mqtt}</div>
              </div>
              <div>
                <div style={{ fontSize: '0.875rem', color: '#666' }}>CoAP Vectors</div>
                <div style={{ fontSize: '1.5rem', fontWeight: 'bold', color: '#f97316' }}>{featureStats.by_protocol.coap}</div>
              </div>
              <div>
                <div style={{ fontSize: '0.875rem', color: '#666' }}>Unknown Protocol</div>
                <div style={{ fontSize: '1.5rem', fontWeight: 'bold' }}>{featureStats.by_protocol.unknown}</div>
              </div>
            </div>
          </div>
        )}
      </div>

      {/* Anomaly Score Distribution */}
      {featureStats && anomalyData.length > 0 && (
        <div style={{ padding: '1.5rem', border: '1px solid #e5e7eb', borderRadius: '0.5rem', backgroundColor: '#fafafa', marginTop: '2rem' }}>
          <h2 style={{ margin: '0 0 1rem 0', fontSize: '1.1rem' }}>Anomaly Score Distribution</h2>
          <ResponsiveContainer width="100%" height={300}>
            <BarChart data={anomalyData}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="name" />
              <YAxis domain={[0, 1]} />
              <Tooltip formatter={(value) => (typeof value === 'number' ? value.toFixed(4) : value)} />
              <Bar dataKey="value" fill="#8b5cf6" />
            </BarChart>
          </ResponsiveContainer>
        </div>
      )}

      <div style={{ marginTop: '3rem', paddingTop: '1rem', borderTop: '1px solid #e5e7eb', fontSize: '0.875rem', color: '#666' }}>
        <p style={{ margin: '0' }}>
          📊 Metrics server: <code style={{ color: '#d946ef' }}>http://localhost:8080</code> • Proxy: <code style={{ color: '#d946ef' }}>localhost:1884/5684</code> • Auto-refresh: 5s
        </p>
      </div>
    </main>
  );
}
