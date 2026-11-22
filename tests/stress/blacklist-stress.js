// k6 stress test for the Blacklist microservice (Entrega 4 - New Relic analysis)
//
// Usage (token and URL are passed as environment variables, never hardcoded):
//   k6 run -e BASE_URL=http://<load-balancer-dns> -e TOKEN=<jwt> blacklist-stress.js
//
// Or with Docker, without installing k6:
//   docker run --rm -i -e BASE_URL=http://<load-balancer-dns> -e TOKEN=<jwt> grafana/k6 run - < blacklist-stress.js

import http from 'k6/http';
import { check, sleep } from 'k6';

// Base URL of the service and JWT used for the protected endpoints
const BASE_URL = __ENV.BASE_URL || 'http://localhost:5000';
const TOKEN = __ENV.TOKEN || '';

// Fixed application identifier sent in every POST
const APP_UUID = '2f6c1c2e-6d3b-4b7a-9c1e-1a2b3c4d5e6f';

// Load profile: warm-up, normal load, ramp to stress, sustained stress, ramp-down
export const options = {
  stages: [
    { duration: '1m', target: 10 },
    { duration: '3m', target: 10 },
    { duration: '2m', target: 50 },
    { duration: '3m', target: 50 },
    { duration: '1m', target: 0 },
  ],
  thresholds: {
    // 95% of requests should answer in under 800 ms
    http_req_duration: ['p(95)<800'],
    // At least 95% of the checks should pass
    checks: ['rate>0.95'],
  },
};

// Expected 4xx responses (validation, auth, duplicates) are not counted as failed requests
http.setResponseCallback(http.expectedStatuses(200, 201, 400, 401, 409));

// Headers for authenticated and unauthenticated requests
const authHeaders = { headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${TOKEN}` } };
const noAuthHeaders = { headers: { 'Content-Type': 'application/json' } };

export default function () {
  // Unique email per virtual user and iteration, so every POST creates a new record
  const email = `stress.${__VU}.${__ITER}.${Date.now()}@example.com`;
  const body = JSON.stringify({ email: email, app_uuid: APP_UUID, blocked_reason: 'k6 stress test' });

  // Health check, used as a cheap baseline transaction
  const health = http.get(`${BASE_URL}/health`, { tags: { name: 'GET /health' } });
  check(health, { 'health 200': (r) => r.status === 200 });

  // Create a new blacklist entry (database write)
  const created = http.post(`${BASE_URL}/blacklists`, body, { ...authHeaders, tags: { name: 'POST /blacklists' } });
  check(created, { 'create 201': (r) => r.status === 201 });

  // Query the email that was just created (database read)
  const found = http.get(`${BASE_URL}/blacklists/${email}`, { ...authHeaders, tags: { name: 'GET /blacklists/{email}' } });
  check(found, { 'query 200': (r) => r.status === 200 });

  // Query an email that is not in the blacklist
  const missing = http.get(`${BASE_URL}/blacklists/missing.${__VU}.${__ITER}@example.com`, { ...authHeaders, tags: { name: 'GET /blacklists/{email}' } });
  check(missing, { 'query missing 200': (r) => r.status === 200 });

  // Repeat the same POST to produce a duplicate (409)
  const duplicate = http.post(`${BASE_URL}/blacklists`, body, { ...authHeaders, tags: { name: 'POST /blacklists' } });
  check(duplicate, { 'duplicate 409': (r) => r.status === 409 });

  // In 10% of the iterations, send an invalid body to produce a validation error (400)
  if (Math.random() < 0.1) {
    const invalid = http.post(`${BASE_URL}/blacklists`, JSON.stringify({ email: 'not-an-email' }), { ...authHeaders, tags: { name: 'POST /blacklists' } });
    check(invalid, { 'invalid 400': (r) => r.status === 400 });
  }

  // In another 10% of the iterations, call without a token to produce an auth error (401)
  if (Math.random() < 0.1) {
    const unauthorized = http.get(`${BASE_URL}/blacklists/${email}`, { ...noAuthHeaders, tags: { name: 'GET /blacklists/{email}' } });
    check(unauthorized, { 'no token 401': (r) => r.status === 401 });
  }

  // Think time between iterations
  sleep(1);
}