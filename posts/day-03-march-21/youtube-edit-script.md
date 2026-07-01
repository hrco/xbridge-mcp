# xBridge MCP — YouTube Video Edit Script
> Total target: ~90 seconds (1:30)
> Editor: CapCut / DaVinci Resolve / any NLE
> All clips: 720p 16:9 (except screencast — crop/scale to match)

---

## Timeline

### ACT 1: THE HOOK (0:00 — 0:25)

**[0:00 — 0:10] INTRO — "xBridge MCP" title reveal**
- File: `site/assets/video-intro-xbridge.mp4` (10s)
- Full clip, no trimming
- Add subtle bass hit at 0:08 when text assembles
- Text overlay at 0:09: `"Claude + Grok. One bridge."` (fade in, bottom center, white mono font)

**[0:10 — 0:25] THE BRIDGE — two AIs meet**
- File: `posts/day-03-march-21/video-claude-meets-grok.mp4` (15s)
- Use full clip
- Cross-dissolve transition from intro (0.5s)
- Text overlays (timed to action):
  - 0:12: `"Two AIs"` (center, fade)
  - 0:17: `"One Protocol"` (center, fade)
  - 0:22: `"19 Tools"` (center, hold)

### ACT 2: THE PROOF (0:25 — 0:55)

**[0:25 — 0:30] BRIDGE CLIMAX — anime style**
- File: `site/assets/video-segment4-bridge-climax.mp4` (10s)
- Trim to best 5s (the nova explosion moment)
- Hard cut from Act 1 — no dissolve, impact cut
- Text overlay: `"Built with AI, for AI"` (bottom left, teal mono)

**[0:30 — 0:55] LIVE DEMO — real terminal footage**
- File: `site/assets/demo-screencast.webm` (2m14s total)
- Crop/scale from 1500x1246 to 1280x720 (center crop or add black bars)
- Trim to the best 25s showing:
  - The grok-video-generate command being called
  - The "polling... generating..." waiting
  - The result URL appearing
- Speed up slow parts to 2x if needed
- Text overlays:
  - 0:32: `"Live demo — no edits"` (top right, small, subtle)
  - 0:45: `"Claude calls Grok via MCP"` (bottom center)

### ACT 3: THE CLOSE (0:55 — 1:30)

**[0:55 — 1:10] POWER UP — energy sequence**
- File: `site/assets/video-over9000-power-up.mp4` (15s)
- Use full clip or trim to best 15s
- Cross-dissolve from demo
- Text overlays:
  - 0:57: `"Free: 50 calls/day"` (left)
  - 1:02: `"Pro: unlimited"` (right)
  - 1:07: `"BYOK — your keys, your control"` (center)

**[1:10 — 1:20] TOKEN REVEAL**
- File: `site/assets/video-segment6-token-reveal.mp4` (5s)
- Full clip + slow to 2x duration (10s)
- Text overlays:
  - 1:12: `"$XBRDG holders get loyalty perks"` (center)
  - 1:17: `"Not an investment. Just vibes."` (bottom, smaller)

**[1:20 — 1:30] END CARD**
- Black screen, fade in
- Center: `xBridge MCP` (large, white)
- Below: `github.com/hrco/xbridge-mcp` (teal, mono)
- Below that: `xbridgemcp.com | xbrdg.com` (muted gray)
- Bottom: `Open Source · MIT License · Made with Claude + Grok`
- Hold 10s for YouTube end screen overlay area

---

## Audio Track

Option A: Use the audio from the Grok-generated clips (they have ambient AI music baked in)
Option B: Royalty-free cinematic track from:
- Pixabay (free, no attribution needed)
- Search: "cinematic technology" or "dark electronic ambient"
- Layer under all clips, duck during demo screencast

---

## Export Settings

- Resolution: 1280x720 (720p) — matches all source clips
- Codec: H.264
- Bitrate: 8-10 Mbps
- Audio: AAC 192kbps
- Format: MP4

---

## Files Checklist

| Clip | File | Duration | Use |
|------|------|----------|-----|
| Intro | `site/assets/video-intro-xbridge.mp4` | 10s | Full |
| Bridge meet | `posts/day-03-march-21/video-claude-meets-grok.mp4` | 15s | Full |
| Anime climax | `site/assets/video-segment4-bridge-climax.mp4` | 10s | Trim to 5s |
| Screencast | `site/assets/demo-screencast.webm` | 2m14s | Trim to 25s |
| Power up | `site/assets/video-over9000-power-up.mp4` | 15s | Full |
| Token reveal | `site/assets/video-segment6-token-reveal.mp4` | 5s | Slow to 10s |
| End card | Create in editor | 10s | Black + text |
