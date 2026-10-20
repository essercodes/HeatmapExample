// Container health check: exits 0 if the server on this container answers GET / with 2xx.
// Runs as a separate process inside the container (ECS healthCheck), so it can only observe the
// server through its port. PORT matches what react-router-serve listens on (default 3000).
const url = `http://localhost:${process.env.PORT ?? 3000}/`;

try {
  const res = await fetch(url, { signal: AbortSignal.timeout(3000) });
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
} catch (err) {
  console.error(`unhealthy: ${err.message}`);
  process.exit(1);
}
