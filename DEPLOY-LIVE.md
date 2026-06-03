# Taking THE COUNCIL live in public (laptop tunnel)

The live, multi-agent council runs a small Python server (`council_server`) that holds your
Anthropic API key and streams the deliberation to the browser. GitHub Pages can't run it
(it's static, and the key must never be public). The simplest way to get a **public, fully
interactive link** — ideal for a talk — is to run the server on your laptop and expose it
through a one-command tunnel. Your key never leaves your machine, there's no hosting account,
and the link is live only while your laptop + tunnel are running.

```
  audience browser  ──►  https://<name>.trycloudflare.com  ──►  cloudflared  ──►  127.0.0.1:8099
                          (public, ephemeral)                    (on your laptop)   (council_server, your key)
```

## One-time setup
```bash
brew install cloudflared          # tunnel client (no account needed for quick tunnels)
# Your real key lives in branchscape/.env  (ANTHROPIC_API_KEY=sk-ant-…) — gitignored.
```

## Each time you go live (two terminals)

**Terminal 1 — the server (with a presenter passcode so randoms can't spend your budget):**
```bash
cd branchscape
COUNCIL_PASSCODE="pick-a-secret" python3 -m council_server 8099
# (optional) COUNCIL_MAX_CONCURRENT=2  caps simultaneous deliberations. Default 2.
```

**Terminal 2 — the public tunnel:**
```bash
cloudflared tunnel --url http://127.0.0.1:8099
# prints something like:  https://brave-otter-1234.trycloudflare.com
```

## The two URLs
- **Presenter (you, can convene):**
  `https://<name>.trycloudflare.com/council.html?key=pick-a-secret`
- **Spectator (audience — watches, can't trigger spend):**
  `https://<name>.trycloudflare.com/council.html`
  Without the passcode, "Convene" returns a friendly 🔒 message. But the deliberation is
  broadcast to **every** connected viewer over SSE — so when you convene, the whole room
  watches the same live debate in real time.

## Good to know
- **Cost:** every "Convene" makes real Anthropic API calls on your key (~a handful of calls
  per run). The passcode gate + concurrency cap exist to bound that on a public link.
- **Ephemeral URL:** a `trycloudflare.com` quick-tunnel URL changes each time you start
  `cloudflared`. Start it once before the talk and keep both terminals open. (For a stable
  URL, a free Cloudflare named tunnel or `ngrok` with an account both work too.)
- **No `?live` needed:** the bare `/council.html` now auto-detects the live server and runs
  the real agents; add `?demo` to force the offline scripted demo, or `?offline` for the
  zero-network void basemap.
- **ngrok alternative:** `ngrok http 127.0.0.1:8099` (needs a free ngrok account/authtoken;
  the free tier shows a one-time interstitial page to first-time visitors).
- **Reliability:** if the venue Wi-Fi dies, `…/council.html?demo` is the fully-local,
  deterministic fallback that needs no network or key.
