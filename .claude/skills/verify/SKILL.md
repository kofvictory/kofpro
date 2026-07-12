---
name: verify
description: Build, run, and visually verify kofpro (Next.js + floating desktop agent コフ) changes end-to-end.
---

# Verify kofpro changes

## Build & launch

```bash
npm install
cp .env.local.example .env.local   # dummy values are fine for UI work
npm run dev                        # http://localhost:3000 (root 307-redirects; just load /)
```

Supabase/Ollama/Anthropic are not reachable in CI-like environments — the UI still
renders; `/api/agent` falls through to an Anthropic 401 error reply, which is enough
to drive the agent's talking state.

## Driving the コフ avatar (DesktopAgent)

Use playwright-core with the preinstalled browser
(`executablePath: '/opt/pw-browsers/chromium_headless_shell-*/chrome-linux/headless_shell'`).

- Avatar button: `button[aria-label="AIアシスタントを開く"]` — the idle `avatarFloat`
  animation makes it permanently "unstable" for actionability checks; click with
  `{ force: true }`.
- Toggle smart mode (warm/anthropic skin): `getByRole('button', { name: '🧠 賢い' })`.
- `thinking` state is too short to catch (the 401 comes back in <150ms). To capture it,
  delay the API: `page.route('**/api/agent', r => setTimeout(() => r.continue(), 4000))`.
- `talking` lasts 2.5s after the reply arrives (hands visible during it); wait for
  `.bg-gray-100.text-gray-800` (assistant bubble), screenshot within the window.
- High-res closeups: `deviceScaleFactor: 3` + clip around bottom-right
  (`{ x: w-120, y: h-140, width: 110, height: 130 }` on a 480×720 viewport).

## Gotchas

- `npx tsc --noEmit` has pre-existing errors in supabase-typed files
  (QuickCapture/TriageCard/agent-tools) — not a regression signal.
- Remove `.env.local` before committing if you created it from the example.
