import { execFileSync } from 'node:child_process';

export default function globalTeardown() {
  try {
    execFileSync('docker', ['rm', '-f', 'rfbalance-e2e-api'], { stdio: 'ignore' });
  } catch {
    // O contêiner já foi removido normalmente pelo `docker compose run --rm`.
  }
}
