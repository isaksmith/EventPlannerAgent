// ============================================================================
// INTEGRATION WIRING  —  THE ONE PLACE YOU SWAP MOCKS FOR REAL SERVICES.
// ----------------------------------------------------------------------------
// Today this returns the mock implementations. To go live, implement the
// interfaces in ./contracts.ts and return your real services here instead, e.g.
//
//   export function getIntegrations(): Integrations {
//     return {
//       sai: new RealSai(),
//       memory: new RedisStore(env.REDIS_URL),
//       brand: new MidjourneyService(env.MJ_KEY),
//       deploy: new ClaudeCodeDeployer(env.VERCEL_TOKEN),
//       browserbase: new Browserbase(env.BB_KEY),
//       outreach: new OutreachDrafter(),
//       tracer: new ArizeTracer(env.ARIZE_KEY),
//     }
//   }
//
// The UI never changes — it only depends on the Integrations interface.
// ============================================================================
import type { Integrations } from './contracts'
import { createMockIntegrations } from './mocks'

export function getIntegrations(): Integrations {
  return createMockIntegrations()
}

export type { Integrations } from './contracts'
