# $XBRDG Community Infrastructure Playbook
**xBridge MCP — pump.fun Fair Launch**
_Solo dev edition. No fluff. Everything is actionable._

---

## 1. X/Twitter Account Setup Checklist

### Account Creation
- [ ] Create account: `@xBridgeMCP` (first choice) or `@xBridgeToken` as fallback
- [ ] Username must match your Telegram channel handle exactly — credibility check
- [ ] Use the same email as your pump.fun account (for coherent identity)
- [ ] Enable 2FA immediately (authenticator app, not SMS)
- [ ] Verify phone number — required before you can post with any reach

### Profile Configuration
- [ ] **Profile photo**: Use `/home/supremeleader/mylab/GROK/site/assets/xbrdg-logo-400x400.png` — already 400x400, perfect spec
- [ ] **Header/Banner**: Recommended spec: **1500x500px**. Text to include: `$XBRDG | xBridge MCP | Claude Code → Grok API | pump.fun`. Use dark background with token logo centered.
- [ ] **Display name**: `xBridge MCP | $XBRDG`
- [ ] **Bio (160 chars max)**:
  ```
  Bridging Claude Code → xAI Grok API. $XBRDG on Solana. Fair launch. Built by a solo dev. MCP server. Real product. No team. No VC.
  ```
  _(132 chars — leaves room)_
- [ ] **Website field**: Your pump.fun token page URL (paste after deploy) or `https://github.com/your-repo` if open source
- [ ] **Location**: `Solana` (type literally — not an actual location, but visible and signals ecosystem)

### Pinned Tweet Plan
Draft this BEFORE launch. Pin immediately at T=0.

**Pinned Tweet Structure:**
```
🌉 $XBRDG is LIVE

xBridge MCP — the indie Python MCP server that bridges
Claude Code directly to the xAI Grok API.

Real product. Fair launch. No team allocation. No presale.

CA: [CONTRACT ADDRESS]
Buy: pump.fun/[CA]
Telegram: t.me/xBridgeMCP

Built by one dev. Ship or die. 🔥
```

**Thread replies to attach under pinned tweet:**
- Reply 1: How xBridge MCP works (1 paragraph + GitHub link if open)
- Reply 2: How to buy — step-by-step for non-crypto people (Phantom wallet → SOL → pump.fun)
- Reply 3: Telegram link + "Join the community"

### Pre-Launch Warm-Up Tweets (Schedule 24-48h before)
1. Tease tweet: `Something is bridging. 🌉 Soon.`
2. Product tweet: `xBridge MCP lets you call Grok from inside Claude Code. Real. Working. Ship. 👀`
3. Launch countdown: `T-24h. $XBRDG fair launch on pump.fun. Solo dev. Real product. No BS.`

---

## 2. Telegram Channel + Group Setup

### Names and Handles

| Asset | Handle | Type | Purpose |
|-------|--------|------|---------|
| Announcement Channel | `@xBridgeMCP` | Channel (broadcast only) | Official CA drops, price milestones, dev updates |
| Community Group | `@xBridgeCommunity` | Group (open chat) | Discussion, FUD management, memes |

If handles are taken, use: `@xBridgeMCPofficial` / `@xBRDGcommunity`

### Channel Setup (Broadcast)
- [ ] Create channel, set type: **Public**
- [ ] Description:
  ```
  Official $XBRDG announcements. xBridge MCP — Claude Code → Grok API bridge.
  Solana fair launch. No DMs from admins. DYOR.
  CA posted here first. Everything else is a scam.
  ```
- [ ] Link channel to group (Group Settings → Discussion → select your channel)
- [ ] Photo: same logo as X profile
- [ ] Sign messages as channel (not personal account)

### Group Setup (Discussion)
- [ ] Create group, set type: **Public**
- [ ] Description:
  ```
  $XBRDG community chat. xBridge MCP on Solana.
  Rules: No spam. No scam links. No DMs from "admins". DYOR.
  Official CA only from pinned message. Bot scammers get banned instantly.
  ```
- [ ] Set slowmode: **30 seconds** (prevents spam floods at launch)
- [ ] Restrict new members: read-only for first 5 minutes after joining (Rose bot handles this)

### Pinned Message Structure (Group)
Pin this immediately when group is created. Update CA field at T=0.

```
📌 $XBRDG — OFFICIAL INFO

🔑 Contract Address (CA):
[PASTE CA HERE — verify on Solscan before posting]

🛒 Buy on pump.fun:
pump.fun/[CA]

📢 Announcement channel: t.me/xBridgeMCP
🐦 Twitter: twitter.com/xBridgeMCP
💻 Product (xBridge MCP): [GitHub or docs link]

⚠️ SCAM WARNING:
• NO admin will EVER DM you first
• NO admin will EVER ask for SOL or wallet access
• The ONLY real CA is the one in this pinned message
• If someone sends you a "new CA" in DM — it's a scam

🔍 Verify on Solscan: [Solscan link to CA]
```

### Recommended Bots — Exact Bot Names

Add all three to the group and promote each to admin with: delete messages, ban users, restrict members, invite users via link.

| Bot | Telegram Handle | Primary Role | Priority |
|-----|----------------|-------------|----------|
| Rose | `@MissRose_bot` | Filters, blacklist, CAPTCHA, welcome | Install first |
| Combot | `@combot` | Anti-spam, analytics, triggers | Install second |
| Shieldy | `@shieldy_bot` | CAPTCHA specialist for new joiners | Install third |

#### Rose Bot Configuration
```
/captcha on
/setrules No spam. No scam links. No fake airdrops. No DMs from admins. DYOR. Violators banned.
/welcomemsg on
/welcome Welcome to $XBRDG! Read the pinned message for the official CA. No admin will DM you.
/blacklistmode del
```
Add blacklist phrases:
```
/bl free airdrop
/bl send sol
/bl dev wallet
/bl new ca
/bl 100x
/bl recovery phrase
```

#### Combot Configuration
After adding: visit https://combot.org/ → link your group → enable:
- Anti-spam: Strict mode
- CAPTCHA: Math puzzle
- Triggers: Add "moonshot", "guaranteed profit", "send ETH/SOL" → auto-mute
- Mute new members: 10 minutes read-only after join

#### Shieldy Configuration
```
/captcha
```
Select: Button click or math challenge. This catches the simplest bots that slip past Rose.

---

## 3. pump.fun Page Optimization

Beyond name, ticker, and logo — fill in every available field:

### Description Field
```
xBridge MCP is a real, working Python MCP server that bridges Claude Code
to the xAI Grok API. Built by a solo indie dev. Open source. Fair launch —
no team allocation, no presale, no VC. $XBRDG is the community token for
the xBridge ecosystem on Solana.
```

### Social Links (fill all available)
- Twitter/X: `https://twitter.com/xBridgeMCP`
- Telegram: `https://t.me/xBridgeMCP`
- Website/GitHub: your repo or docs link

### Logo
- Use `/home/supremeleader/mylab/GROK/site/assets/xbrdg-logo-400x400.png`
- pump.fun accepts PNG, recommended square, 400x400 is ideal

### What pump.fun does NOT show but you should screencap for community
After deploying:
1. Screenshot the pump.fun page showing your metadata
2. Screenshot Solscan showing: contract address, mint authority status, freeze authority status
3. Post both in Telegram pinned message as proof

### Tips
- Do NOT mark anything as "dev locked" unless you actually lock it — community checks
- The more complete your page, the higher it ranks in pump.fun's trending feed
- Adding a website link is a strong credibility signal — even a basic GitHub README counts

---

## 4. Launch Day Minute-by-Minute Sequence

### T-2h: Pre-Launch Prep
- [ ] Telegram group and channel are live with pinned messages (CA field left as `[PENDING]`)
- [ ] X/Twitter profile fully configured, banner uploaded, bio set
- [ ] Pre-launch tweets scheduled or drafted
- [ ] pump.fun metadata prepared (description, links, logo) — do NOT deploy yet
- [ ] Wallet loaded, pump.fun page open and ready to submit
- [ ] Post on X: `T-2h. $XBRDG fair launch incoming. Telegram live: t.me/xBridgeMCP`

### T-1h: Build Anticipation
- [ ] Post on X: `T-1h. Building the bridge. Solo dev, real product, fair launch. 🌉`
- [ ] Post in Telegram channel: `Launch in 1 hour. Pinned message will be updated with CA the moment we go live.`
- [ ] Check wallet balance, confirm pump.fun UI is responsive
- [ ] Have Solscan open and ready to paste the CA link immediately after deploy

### T-15min: Final Check
- [ ] Close all unnecessary browser tabs — you need speed at T=0
- [ ] Have your pinned message text in clipboard (the version with CA ready to paste)
- [ ] Have your X pinned tweet text in a notes file ready to copy
- [ ] Post on X: `15 minutes. $XBRDG. pump.fun. Let's go.`

### T=0: Deploy
1. Submit token on pump.fun (name, ticker, description, logo, links)
2. **Immediately copy the contract address (CA)**
3. Make your initial buy (recommended: 0.2-0.5 SOL to seed the bonding curve)
4. Open Solscan, verify the CA matches — screenshot it

### T=0 to T+2min: Blast
5. Update Telegram group pinned message — paste real CA, Solscan link
6. Post in Telegram channel:
   ```
   🚀 $XBRDG IS LIVE
   CA: [CA]
   Buy: pump.fun/[CA]
   Solscan: [link]
   ```
7. Post pinned tweet on X (pre-drafted text + CA + pump.fun link)
8. Reply to your pinned tweet with the "how to buy" thread

### T+5min: Confirmation Post
- Post on X: `$XBRDG live and trading. [CA] — verify on Solscan. No fake CA. No presale. Fair launch.`
- Post in Telegram: `CA confirmed live. Verify on Solscan before buying: [link]. Scammers already DMing fake CAs — do NOT trust DMs.`

### T+15min: Anti-Scam Blast
- This is when scammers spin up fake Telegrams and post fake CAs
- Post in group: `REMINDER: Only one real CA. It is in the pinned message. Anyone DMing you a different CA is a SCAMMER. Report and block.`
- Post on X: `PSA: Scammers are creating fake $XBRDG accounts. Verify CA: [CA] — only buy from pump.fun/[CA]. Official Telegram: t.me/xBridgeMCP`

### T+30min: Momentum Update
- Post holders count and bonding curve progress on X and Telegram
- Example: `$XBRDG — [X] holders, [Y]% bonded. Early. Real. 🌉`

### T+1h: Community Pulse
- Post on X: `1 hour in. $XBRDG holding. What are you bridging today? 👀`
- Ask the community in Telegram: `Who's using xBridge MCP for real? Drop your use case.`
- This generates organic content and engagement signals on X

### T+2h: State of the Bridge
- Compile a mini update: holders, bonding progress, any notable X mentions
- Post on X as a thread:
  - Tweet 1: Stats
  - Tweet 2: What xBridge MCP does (product reminder)
  - Tweet 3: Link to GitHub/docs for builders
- Post in Telegram channel: same update with a personal note from SupremeLeader

---

## 5. Anti-Scam / Anti-Bot Checklist (Execute Immediately After Deploy)

### Within the First 5 Minutes
- [ ] Post the official CA publicly on X and in Telegram simultaneously — this timestamps the real CA
- [ ] Update the Telegram pinned message with the real CA and lock it (pin + notify all members)
- [ ] Screenshot and post your Solscan token page showing mint authority status

### Within the First 30 Minutes
- [ ] Search X for `$XBRDG` — identify and report any fake accounts or fake CA posts immediately
- [ ] Search Telegram for `xBridge` — report fake channels/groups to Telegram support
- [ ] Post explicit scam warning on both X and Telegram (see T+15min above)
- [ ] Check that Rose bot and Combot are running — test by sending a blacklisted phrase from a test account

### Telegram Group Controls
- [ ] Enable slowmode (30 seconds) — do this BEFORE launch so it's active during the surge
- [ ] Have at least one trusted mod (can be your alt account) who can ban instantly
- [ ] Set new member join cooldown via Combot
- [ ] If scam bots flood the group: temporarily switch to approved-members-only mode while you clean up

### X/Twitter Controls
- [ ] Block and report every fake `@xBridgeMCP` variant account you find
- [ ] Add a tweet with explicit fake account names if they appear: `SCAM ALERT: @[fake account] is NOT us. Our only account is @xBridgeMCP.`
- [ ] Disable DMs or set to "followers only" — scammers impersonate you via DM

### On-Chain
- [ ] Verify mint authority is renounced (or note it clearly if not yet) — show Solscan proof
- [ ] Verify freeze authority status — post screenshot
- [ ] After pump.fun graduation to Raydium: lock LP tokens via Team Finance or Unicrypt, post TX proof

---

## 6. Week 1 Moderation Playbook

### General Rules to Pin and Enforce

```
$XBRDG Community Rules

1. No spam, no flooding
2. No scam links, no fake CAs, no "new contract" posts
3. No unsolicited DMs — admins NEVER DM first
4. No fake airdrop promotion
5. Price discussion OK. FUD OK. Threats/personal attacks = ban.
6. English in main chat. Other languages can start threads.
7. DYOR. Nothing here is financial advice.

Violations: warn → mute → ban. No appeals for scam violations.
```

### Handling FUD (Fear, Uncertainty, Doubt)

FUD is normal and healthy. Respond with facts, not emotion.

| FUD Type | Response Strategy |
|----------|-----------------|
| "Dev will rug" | Link Solscan showing mint authority status. "Verify on-chain. Not asking you to trust me." |
| "This is a scam" | "Here's the GitHub. Here's the MCP server. Real product, real code. DYOR." |
| "Liquidity is low" | "Fair launch means bonding curve. That's how pump.fun works. Read the docs." |
| "Nobody uses this" | Share xBridge MCP usage stats or GitHub stars if available |
| "Fake volume" | "pump.fun shows real on-chain transactions. Check Dexscreener." |
| "Dev dumped" | Link dev wallet on Solscan showing your holdings if you want to be transparent |

Key principle: Never delete legitimate FUD. Deleting FUD makes it look like you have something to hide. Only delete spam and scam links.

### Handling Fake Token Warnings

Someone will inevitably post "THE REAL $XBRDG IS AT [different CA]" — this is one of the most common attacks.

**Response protocol:**
1. Delete the message immediately
2. Ban the account (first offense for CA impersonation — zero tolerance)
3. Post in group: `Reminder: Fake CA just posted and deleted. Our CA is in the PINNED MESSAGE. Anyone posting a different CA is a scammer.`
4. Post on X: `Fake $XBRDG CA circulating. Real CA: [CA]. Verify on Solscan. One token, one CA.`

### Handling Impersonator Accounts

Someone creates `@xBridgeMCP2` or similar.

1. Screenshot the fake account
2. Report to X/Telegram
3. Post publicly: `SCAM ALERT: [fake handle] is impersonating us. Our ONLY account is @xBridgeMCP.`
4. Pin the scam alert tweet temporarily

### Daily Moderation Rhythm (Week 1)

**Every morning:**
- Check Telegram for overnight scam activity — run `/ban` on bots that slipped through
- Check X for fake account activity
- Post a short update: price, holders, bonding progress, or a product note

**Every evening:**
- Community engagement post on X (question, meme, poll)
- Milestone celebration if any (first 100 holders, 50% bonded, graduation, etc.)
- Brief Telegram message from SupremeLeader as dev — authentic voice builds loyalty

**Day 3: First AMA**
- Announce 24h in advance: `AMA tomorrow in t.me/xBridgeCommunity — ask me anything about $XBRDG and xBridge MCP`
- Collect questions via pinned message or just open format
- Answer 10-15 questions in a single session
- Post AMA recap on X as a thread

**Day 5: Meme Contest**
```
🎨 $XBRDG MEME CONTEST

Best meme wins 0.1 SOL from SupremeLeader's own bag.
Drop your entry below.
Voting: most reactions by [time] wins.
Rules: Must include $XBRDG branding. Keep it clean(ish).
```

**Day 7: Week 1 Recap**
Post on X and Telegram:
- Holders count
- Trading volume
- Bonding curve status or Raydium graduation status
- Next milestone target
- Genuine thank-you from SupremeLeader

### Tone Guide

You are a solo indie dev. That is your biggest credibility advantage over anonymous teams.

- Be direct and honest, not hype-maxing
- Admit what you don't know
- Share product updates even if small
- Occasional sarcasm is on-brand (SpectreHawk energy)
- If something goes wrong: acknowledge it, explain it, move forward

The community will stick with a genuine builder who communicates. They abandon ghost devs and hype merchants fast.

---

## Quick Reference Card

```
Official X:        @xBridgeMCP
Official Telegram: t.me/xBridgeMCP (channel) + t.me/xBridgeCommunity (group)
Real CA:           [UPDATE AT LAUNCH]
pump.fun:          pump.fun/[CA]
Solscan:           solscan.io/token/[CA]

Bots running:
  @MissRose_bot    → filters, blacklist, CAPTCHA
  @combot          → anti-spam, analytics
  @shieldy_bot     → CAPTCHA for new joiners

No admin DMs. No fake CAs. DYOR.
```

---

_Last updated: Launch day — update CA fields above before distributing._
