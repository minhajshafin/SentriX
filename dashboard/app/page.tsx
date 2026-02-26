type Metrics = {
  mqtt_msgs: number;
  coap_msgs: number;
  detections: number;
  latency_ms_p95: number;
};

type SecurityEvent = {
  ts: string;
  protocol: string;
  direction: string;
  event: string;
  bytes: number;
  detail: string;
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

async function getEvents(): Promise<SecurityEvent[]> {
  const base = process.env.NEXT_PUBLIC_METRICS_BASE_URL ?? 'http://localhost:8080';

  try {
    const response = await fetch(`${base}/events`, {
      cache: 'no-store',
    });

    if (!response.ok) {
      return [];
    }

    const body = (await response.json()) as { events?: SecurityEvent[] };
    const events = body.events ?? [];
    return events.slice(-30).reverse();
  } catch {
    return [];
  }
}

export default async function HomePage() {
  const metrics = await getMetrics();
  const events = await getEvents();

  return (
    <main className="container">
      <h1>SentriX Dashboard</h1>
      <p className="sub">Minimal Week 2 dashboard scaffold</p>

      {!metrics ? (
        <div className="card error">
          <h2>Metrics API unavailable</h2>
          <p>Check http://localhost:8080/health and ensure docker compose up is running.</p>
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

      <div className="card" style={{ marginTop: '1rem' }}>
        <h2>Endpoints</h2>
        <p>MQTT proxy ingress: localhost:1884</p>
        <p>Metrics API: http://localhost:8080/metrics</p>
      </div>

      <div className="card" style={{ marginTop: '1rem' }}>
        <h2>Security Event Tracker</h2>
        {events.length === 0 ? (
          <p className="sub">No events yet. Send MQTT traffic to localhost:1884.</p>
        ) : (
          <div className="event-list">
            {events.map((event, index) => (
              <div className="event-item" key={`${event.ts}-${event.protocol}-${index}`}>
                <p className="event-time">{event.ts}</p>
                <p className="event-main">
                  <span className="event-pill">{event.protocol.toUpperCase()}</span>
                  {' '}
                  {event.direction}
                  {' '}
                  {event.event}
                  {' '}
                  ({event.bytes} bytes)
                </p>
                {event.detail ? <p className="event-detail">{event.detail}</p> : null}
              </div>
            ))}
          </div>
        )}
      </div>
    </main>
  );
}
