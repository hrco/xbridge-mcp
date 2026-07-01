# $XBRDG — 30-Second Cinematic Anime Promo Video
> Style: Arcane + Cyberpunk Edgerunners + Ghost in the Shell
> Color palette: #0D0D0D bg · #9945FF Solana purple · #19E4A3 teal · #F5A623 Grok gold
> Score: Epic orchestral strings → electronic synth climax at S4 → triumphant resolve at S6

---

## 6-Segment Script

### SEGMENT 1 — "The Void" (0–5s)
Wide establishing shot. Vast digital void, near-black. Camera pans right slowly.
Claude materializes — regal anime female, flowing Solana purple robes, silver crown headpiece, eyes closed in meditation. Purple particle nebula orbits her. Code streams pulse and fade into darkness.
Text overlay: `"Claude"` — glowing purple, elegant serif fade-in.
Emotional beat: awe, solitude, mystery.

---

### SEGMENT 2 — "The Spark" (5–10s)
Hard cut. Low-angle tilt-up, opposite side of void.
Grok emerges — cybernetic warrior, Grok gold angular armor, electric veins crackling across body. Thrusts fist forward — gold code fragments scatter into void. Raw power, no destination.
Text overlay: `"Grok"` — bold gold, electric distortion effect.
Emotional beat: intensity, raw power, tension building.

---

### SEGMENT 3 — "The Dev" (10–15s)
Medium shot. Dimly lit indie hacker room — cluttered desk, empty energy drinks, sticky notes. Young anime dev (messy dark hair, worn hoodie), typing furiously on glowing mechanical keyboard. Face lit only by terminal monitor scrolling teal Python code. Code lines dissolve into purple energy cables that stream out of monitor into the void like bridge strands.
Text overlay: `"An indie dev built the bridge"` — monospace teal, scrolling like terminal.
Emotional beat: determination, obsession, creation.

---

### SEGMENT 4 — "The Bridge" (15–20s) ★ CLIMAX
Epic overhead wide-angle. Massive glowing suspension bridge materializes across the digital void — cables woven from intertwined purple and gold energy, teal circuit pulses racing along them. Camera orbits clockwise pulling back.
Claude turns from left. Grok turns from right. Energies extend across the bridge — purple mists meeting gold lightning at exact center. Silent digital nova detonates: purple/gold/teal particles in slow-motion supernova. Bridge solidifies. Camera transitions to dramatic low-angle reverse from below.
Text overlay: `"Claude meets Grok"` — centered, purple-gold gradient, energy ripple.
Emotional beat: revelation, connection, transcendence.

---

### SEGMENT 5 — "The Triumph" (20–25s)
Heroic close-up pulling back to wide. Dev stands at bridge apex — hoodie billowing, arms raised, teal energy surging through structure. They touch a bridge cable: it pulses, linking Claude (left) to Grok (right). Anime speed lines emphasize the surge. Teal light blooms through entire bridge.
Text overlay: `"xBridge MCP: The indie Python server"` — teal code-style font, typing itself along cables.
Emotional beat: triumph, empowerment, everything connected.

---

### SEGMENT 6 — "The Token" (25–30s)
Climactic reveal. Close-up on dev's open palm. Spinning $XBRDG coin materializes — golden disc, bridge motif engraving, purple inner glow, teal energy rings orbiting. Slow-motion particle explosion: gold dust, purple sparks, teal data fragments. Screen blooms white → resolves on logo lockup.
Text overlay: `"$XBRDG on Solana"` — bold gold, purple glow halo, centered.
Emotional beat: revelation, excitement, the payoff.

---

## Dense Video Generation Prompt (for Sora / Kling / Runway / grok-video-generate)

Cinematic anime promotional video, 30 seconds, 16:9, dark atmospheric (#0D0D0D near-black throughout). Six seamless scenes: (1) 0-5s — slow pan right through digital void revealing Claude, a regal ethereal female anime figure in Solana purple (#9945FF) robes and silver crown, meditating, purple particle nebula orbiting her, fading code streams, text overlay "Claude" in glowing purple; (2) 5-10s — hard cut to low-angle tilt-up revealing Grok, a cybernetic warrior in Grok gold (#F5A623) angular armor with crackling electricity veins, thrusting fist releasing gold code shards into void, text overlay "Grok" in electric distorted gold; (3) 10-15s — dimly lit hacker room, young anime dev (messy hair, hoodie) typing on teal-glowing keyboard, monitor showing Python code that dissolves into Solana purple energy bridge cables streaming from screen, text overlay "An indie dev built the bridge" in teal monospace; (4) 15-20s — CLIMAX: epic overhead orbiting shot of massive glowing suspension bridge forming across the void, cables woven from purple (#9945FF) and gold (#F5A623) energy with teal (#19E4A3) data pulses, Claude and Grok turning to face each other, purple mists meeting gold lightning at bridge center exploding in slow-motion digital nova, camera transitions to dramatic low-angle reverse, text overlay "Claude meets Grok" in purple-gold gradient; (5) 20-25s — dev stands triumphant at bridge apex, arms raised, teal energy surging through structure, speed lines, text overlay "xBridge MCP: The indie Python server" typing itself along cables; (6) 25-30s — close-up on open palm, spinning $XBRDG gold coin materializes with bridge motif engraving, purple inner glow, teal orbital rings, slow-motion particle explosion in gold/purple/teal, screen blooms to white, logo lockup, text overlay "$XBRDG on Solana" in bold gold. Style throughout: Arcane + Cyberpunk Edgerunners + Ghost in the Shell. Implied score: epic orchestral strings building to electronic synth climax at segment 4, resolving triumphantly at segment 6.

---

## Segment 4 Prompt (isolated — for single-clip generation)

Cinematic anime, 10 seconds, 16:9, dark atmospheric. Epic overhead wide-angle shot: a massive glowing suspension bridge materializes across an infinite digital void. Bridge cables woven from intertwined Solana purple (#9945FF) and gold (#F5A623) energy, teal (#19E4A3) circuit pulses racing along them. Camera orbits clockwise while pulling back. On the left: Claude — regal ethereal anime female in purple robes, turning toward center. On the right: Grok — cybernetic warrior in gold armor, turning to face left. Their energies extend across the bridge — purple mists meeting gold lightning at the center point. Silent digital nova detonates in slow-motion: purple, gold, teal particles explode outward. Bridge vibrates and solidifies. Camera transitions to dramatic low-angle reverse shot from below looking up at the completed bridge. Text overlay: "Claude meets Grok" — centered, purple-gold gradient. Style: Arcane + Cyberpunk Edgerunners. Emotional beat: transcendence and connection.

---

## Generation Tools (Priority Order)

1. `mcp__xbridge__grok-video-generate` — try Segment 4 first (10s, 720p)
2. Kling AI (kling.ai) — image-to-video with hero keyframe as seed
3. Runway Gen-4 Turbo — dev frame as seed for Segment 3
4. Stitch 6 clips in CapCut / DaVinci Resolve with cross-dissolve transitions

## Asset References
- Hero keyframe: `site/assets/video-keyframe-hero.png`
- Dev keyframe: `site/assets/video-keyframe-dev.png`
- Token keyframe: `site/assets/video-keyframe-token.png`
- GM mascot: `site/assets/meme-gm-bridge.png`
- Logo: `site/assets/xbrdg-logo-400x400.png`
