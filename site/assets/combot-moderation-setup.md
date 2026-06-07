# Combot Moderation Setup — $XBRDG Community
> Based on researched Combot features (combot.org). Last verified: March 2026.
> Official source: https://t.me/combotnews · https://combot.org/commands

---

## Bots to Add (3 total — all free)

| Bot | Handle | Role |
|-----|--------|------|
| Combot | `@combot` | Anti-spam, triggers, analytics, moderation |
| Service Message Cleaner | `@servmsgcleanerbot` | Auto-deletes join/leave notifications |
| Sticker Cleaner | `@stickerscleanerbot` | Auto-deletes sticker spam (optional) |

### Admin permissions required for each
- Delete Messages
- Ban Users
- Restrict Members
- Invite Users via Link

---

## Step 1 — Service Message Cleanup (Free, Zero Config)

**Add `@servmsgcleanerbot` as admin** — it immediately and automatically deletes:
- "X joined the group" notifications
- "X left the group" notifications
- No dashboard configuration needed

> This is NOT a Combot feature. It's a separate free bot.

---

## Step 2 — Activate Combot Moderation Module

1. Go to **combot.org** → log in with Telegram
2. Select your group from "My chats"
3. If Moderation shows a 24-hour trial prompt → activate it
4. Your group is small (~4–50 members) — Moderation module is **free** at this size

---

## Step 3 — CAS Anti-Spam (On by Default)

**Combot Anti-Spam (CAS)** pre-bans known spammers before their first message.
It is enabled by default. **Leave it on.**

Dashboard path: `Moderation → CAS`

No changes needed. Verify it shows "Enabled".

---

## Step 4 — Link Filter (Most Critical for Crypto Group)

**Dashboard path:** `Moderation → Links`

| Setting | Value |
|---------|-------|
| Mode | **Whitelist** (allow only your links, block everything else) |
| Whitelist entries | `pump.fun` |
| | `dexscreener.com` |
| | `solscan.io` |
| | `github.com` |
| | `xbridgemcp.com` |
| | `xbrdg.com` |
| | `t.me/xBridgeMCP` (your channel) |
| | `t.me/xBridgeCommunity` (your group) |
| Action on violation | **Delete + Warn** |
| First message with link | **Ban + Delete** (new user scam = zero tolerance) |

> This kills fake CA links and scam Telegrams automatically.

---

## Step 5 — Flood Control

**Dashboard path:** `Moderation → Flood Control`

| Setting | Value |
|---------|-------|
| Max messages in interval | 4 messages |
| Interval | 10 seconds |
| Action | Mute (temporary) |
| Mute duration | 60 minutes |
| Delete duplicate messages | ✅ Yes (last 120 seconds window) |

---

## Step 6 — Forward Filtering

**Dashboard path:** `Moderation → Forward Filtering`

| Setting | Value |
|---------|-------|
| Delete forwards from bots | ✅ Yes |
| Delete forwards from channels | ✅ Yes |
| Delete other forwards | Off (allow user-to-user forwards) |
| Whitelist | Add your own channel `@xBridgeMCP` |

---

## Step 7 — New Member Protection

**Dashboard path:** `Moderation → Captcha`

| Setting | Value |
|---------|-------|
| Captcha | ✅ Enable (button click or math) |
| Delete welcome message after captcha | ✅ Yes |
| Mute new members until captcha passed | ✅ Yes |
| Kick if no captcha response after | 5 minutes |

---

## Step 8 — Report System

**Dashboard path:** `Moderation → Reports`

| Setting | Value |
|---------|-------|
| Auto-delete reported message after X reports | 3 |
| Auto-warn user after X reports | 3 |
| Show reporter name | Off (protect reporters) |

---

## Step 9 — Triggers (Keyword Auto-Replies)

**Dashboard path:** `Triggers → Add New`

Free tier: ~10 triggers. Priority triggers to set up first:

| Trigger phrase | Response |
|----------------|----------|
| `ca` or `contract` | `CA: 6vUhppYep18WSncUDR6Brt9yZw31ycLDPDEHo13pump` |
| `price` or `chart` | `$XBRDG chart: https://dexscreener.com/solana/6vUhppYep18WSncUDR6Brt9yZw31ycLDPDEHo13pump` |
| `buy` or `pump` | `Buy $XBRDG: https://pump.fun/coin/6vUhppYep18WSncUDR6Brt9yZw31ycLDPDEHo13pump` |
| `install` or `docker` or `setup` | `docker pull hrco/xbridge-mcp:latest` + GitHub link |
| `new ca` or `new contract` | **Delete + Warn** (no response — scam phrase) |
| `recovery phrase` or `private key` | **Delete + Ban** (no response — scam phrase) |
| `send sol` or `send eth` | **Delete + Ban** |
| `100x` or `guaranteed` | **Delete + Warn** |
| `airdrop` | **Delete + Warn** (unless you're running one) |
| `xbridgemcp.com` | Whitelist — allow (your own site) |

**Trigger action options:** text reply · delete message · warn user · mute · ban

---

## Timed Deletion — Manual Commands

Combot can delete specific messages on a timer using in-chat commands:

| Command | Effect |
|---------|--------|
| Reply to a message + `!d 1h` | Delete that message after 1 hour |
| Reply to a message + `!d 24h` | Delete after 24 hours |
| Reply to a message + `!sd` | Delete silently now |
| `!purge` | Bulk-delete up to 500 messages above it |
| `!d` max timer | **9 hours** (Telegram's 48h bot limit is the ceiling) |

> Use `!d` for scheduled posts you want to auto-expire.
> Use `!purge` during scam floods to clean fast.

---

## Scheduled Messages (Verify in Dashboard)

> ⚠️ Sources conflict on whether recurring scheduled messages are free or Pro-only.
> Check your dashboard — if "Recurring" is locked, it requires Combot Pro ($19.99/mo).

**If free:** Configure the 4 rotating announcement variations as documented in `combot-announcements.md`.

**If locked/Pro-only alternatives (free workarounds):**
- Use `@ControllerBot` (free Telegram bot for scheduled posts)
- Use `@MessageSchedulerBot`
- Post manually on the schedule — at Day 2 with 4 holders, manual is fine

---

## Combot Dashboard Quick Reference

| Path | What's There |
|------|-------------|
| `combot.org → My chats → [group]` | Entry point |
| `Moderation` | All anti-spam, flood, links, forwards, captcha |
| `Triggers` | Keyword auto-replies |
| `Welcome Messages` | New member greeting |
| `Scheduled Messages` | Recurring posts (verify free/Pro) |
| `Analytics` | Member activity, message stats (always free) |
| `Journal` | Last 50 deleted messages, `!log` in chat |

---

## Priority Order (Execute Now)

1. `@servmsgcleanerbot` → add as admin (2 min, zero config)
2. Link filter → whitelist mode + add your domains (10 min)
3. Captcha → enable for new members (5 min)
4. Forward filtering → bots + channels (5 min)
5. Triggers → CA, price, buy, scam phrases (15 min)
6. Flood control → set thresholds (5 min)
7. Scheduled messages → verify if free in your dashboard

---

## Notes

- Combot Pro pricing (2025): $19.99/mo personal, $79.99/mo commercial
- At 4–50 members, all moderation features should be available free
- The `@combotnews` Telegram channel is the most reliable source for feature changes
- Always test triggers by posting the keyword yourself from a test account
