import { describe, it, expect, vi, afterEach } from 'vitest';
import { wsBase } from './wsBase';

afterEach(() => { vi.unstubAllEnvs(); vi.unstubAllGlobals(); });

describe('wsBase', () => {
  it('uses VITE_WS_URL when set (bundled app)', () => {
    vi.stubEnv('VITE_WS_URL', 'wss://mentoring.smallpeice.online');
    expect(wsBase()).toBe('wss://mentoring.smallpeice.online');
  });

  it('falls back to the page origin on https (website)', () => {
    vi.stubEnv('VITE_WS_URL', '');
    vi.stubGlobal('location', { protocol: 'https:', host: 'mentoring.smallpeice.online' });
    expect(wsBase()).toBe('wss://mentoring.smallpeice.online');
  });

  it('falls back to ws:// on http (local dev)', () => {
    vi.stubEnv('VITE_WS_URL', '');
    vi.stubGlobal('location', { protocol: 'http:', host: 'localhost:3000' });
    expect(wsBase()).toBe('ws://localhost:3000');
  });
});
