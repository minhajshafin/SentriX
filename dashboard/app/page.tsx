type Metrics = {
  mqtt_msgs: number;
  coap_msgs: number;
  detections: number;
  latency_ms_p95: number;
};

async function getMetrics(): Promise<Metrics | null> {
  const base = process.env.NEXT_PUBLIC_METRICS_BASE_URL ?? 'http://localhost:8080';

  try {
    const response = await fetch(`${base}/metrics`, {
      cache: 'no-store',
    });

    if (!response.ok) {
      return null;
    }

    return (await response.json()) as Metrics;
  } catch {
    return null;
  }
}

export default async function HomePage() {
  const metrics = await getMetrics();

  return (
    <main className="container">
      <h1>SentriX Dashboard</h1>
      <p className="sub">Minimal Week 2 dashboard scaffold</p>

      {!metrics ? (
        <div className="card error">
          <h2>Metrics API unavailable</h2>
          <p>Check `http://localhost:8080/health` and ensure `docker compose up` is running.</p>
        </div>
      ) : (
        <div className="grid">
          <article className="card">
            <h2>MQTT Messages</h2>
            <p className="metric">{metrics.mqtt_msgs}</p>
          </article>
          <article className="card">
            <h2>CoAP Messages</h2>
            <p className="metric">{metrics.coap_msgs}</p>
          </article>
          <article className="card">
            <h2>Detections</h2>
            <p className="metric">{metrics.detections}</p>
          </article>
          <article className="card">
            <h2>Latency p95 (ms)</h2>
            <p className="metric">{metrics.latency_ms_p95}</p>
          </article>
        </div>
      )}
    </main>
  );
}
