# Combot Announcement Guide — xBridge MCP

> Telegram groups: @xBridgeMCP (broadcast) · @xBridgeCommunity (main group)
> Dashboard: combot.org → My Communities

---

## Prerequisites

1. Add @combot as admin in **@xBridgeCommunity**
   - Group Settings → Edit → Administrators → Search @combot
   - Grant: Post Messages, Delete Messages, Pin Messages
2. Log in at **combot.org** with your Telegram account
3. Select the group from "My Communities" sidebar

---

## 0. Hourly Rotating Announcements with Buy Buttons

> **Requires Combot Premium** for hourly scheduling + inline keyboard buttons.
> Basic `[text](url)` hyperlink buttons are free but look like links, not buttons.
> Premium inline keyboards render as proper clickable buttons below the message.

**Dashboard path:** Tools → Scheduled Messages → Create New

### Button formats

**Free (Markdown hyperlinks — look like links):**
```
[Buy $XBRDG](https://pump.fun/coin/6vUhppYep18WSncUDR6Brt9yZw31ycLDPDEHo13pump)
[Get xBridge MCP](https://github.com/hrco/xbridge-mcp)
```

**Premium (inline keyboard JSON — renders as real buttons):**
```json
{
  "inline_keyboard": [
    [
      {"text": "🟢 Buy $XBRDG", "url": "https://pump.fun/coin/6vUhppYep18WSncUDR6Brt9yZw31ycLDPDEHo13pump"},
      {"text": "🐳 Get xBridge MCP", "url": "https://github.com/hrco/xbridge-mcp"}
    ]
  ]
}
```

---

### 4 rotating variations — stagger start times 1h apart

Schedule each as **Recurring · Every 4 hours** offset by 1h so they rotate.
- Variation 1 → start 12:00 UTC
- Variation 2 → start 13:00 UTC
- Variation 3 → start 14:00 UTC
- Variation 4 → start 15:00 UTC

Result: a different message posts every hour, cycling through all 4 every 4h.

---

**Variation 1 — Install hook**
```
🐳 Claude Code + Grok in one Docker container.

docker pull hrco/xbridge-mcp:latest

Web search · X search · Sessions · Chains
Image gen · Video gen · xAI docs
16 tools. €3.69/mo. BYOK.

[Buy $XBRDG](https://pump.fun/coin/6vUhppYep18WSncUDR6Brt9yZw31ycLDPDEHo13pump) · [Get xBridge MCP](https://github.com/hrco/xbridge-mcp)
```

---

**Variation 2 — Feature spotlight**
```
🔍 Real-time web + X search inside Claude Code.
🎨 Generate images and video on demand.
🔗 Automated research, debug, and summarize chains.
💬 Persistent sessions — no context loss.

xBridge MCP · €3.69/mo · BYOK

[Buy $XBRDG](https://pump.fun/coin/6vUhppYep18WSncUDR6Brt9yZw31ycLDPDEHo13pump) · [Get xBridge MCP](https://github.com/hrco/xbridge-mcp)
```

---

**Variation 3 — $XBRDG token focus**
```
🌉 Built the bridge. Made a token.

$XBRDG — community memecoin for xBridge MCP
Solana · pump.fun fair launch · no utility promises

CA: 6vUhppYep18WSncUDR6Brt9yZw31ycLDPDEHo13pump

[Buy $XBRDG](https://pump.fun/coin/6vUhppYep18WSncUDR6Brt9yZw31ycLDPDEHo13pump) · [Get xBridge MCP](https://github.com/hrco/xbridge-mcp)
```

---

**Variation 4 — Pain point / CTA**
```
Claude Code can't search the web.
Can't generate images or video.
Can't persist context between sessions.

xBridge MCP fixes all of that.
€3.69/mo · Docker · BYOK

[Buy $XBRDG](https://pump.fun/coin/6vUhppYep18WSncUDR6Brt9yZw31ycLDPDEHo13pump) · [Get xBridge MCP](https://github.com/hrco/xbridge-mcp)
```

---

### Setup steps (hourly rotation)

1. Log in → combot.org → select **@xBridgeCommunity**
2. Tools → Scheduled Messages → **Create New**
3. Paste Variation 1 text into the message editor
4. If premium: click **Add Inline Keyboard** → paste the JSON above
5. Schedule Type: **Recurring** · Frequency: **Every 4 hours** · Start: **12:00 UTC**
6. Enable **Delete After: 55 minutes** (keeps chat clean, old post gone before new one arrives)
7. Save → repeat for Variations 2, 3, 4 with start times 13:00 / 14:00 / 15:00 UTC
8. Test: hit **Test Send** on each to verify buttons render in the group

---

## 1. Scheduled / Recurring Announcements

**Dashboard path:** Tools → Scheduled Messages → Create New

### Weekly "How to Get Started" post
Post to: **@xBridgeCommunity**
Schedule: Every Monday, 10:00 UTC

```
🚀 Weekly tip: Get xBridge MCP running in 2 steps

docker pull hrco/xbridge-mcp:latest
docker run -e XAI_API_KEY=your_key hrco/xbridge-mcp:latest

16 Grok tools inside Claude Code. €3.69/mo.
GitHub: https://github.com/hrco/xbridge-mcp
```

Settings:
- Schedule Type: **Recurring**
- Frequency: Every week, Monday
- Pin Message: optional

---

### Periodic $XBRDG token update
Post to: **@xBridgeMCP** (broadcast channel)
Schedule: Every 3 days

```
$XBRDG — xBridge MCP community token

🌉 Solana · pump.fun fair launch
CA: 6vUhppYep18WSncUDR6Brt9yZw31ycLDPDEHo13pump

pump.fun: https://pump.fun/coin/6vUhppYep18WSncUDR6Brt9yZw31ycLDPDEHo13pump
Site: https://xbrdg.com
```

Settings:
- Schedule Type: **Recurring**
- Frequency: Every 3 days
- Pin Message: No

---

## 2. Trigger-Based Auto-Replies

**Dashboard path:** Moderation → Auto Responses → Add New Response
Apply to: **@xBridgeCommunity only**

---

### Trigger: "price" or "token"

| Field | Value |
|-------|-------|
| Trigger Type | Contains |
| Trigger Phrase | `price` |
| Reply to Message | Yes |
| Delete After | — |

**Response:**
```
$XBRDG on pump.fun 🌉
CA: 6vUhppYep18WSncUDR6Brt9yZw31ycLDPDEHo13pump
https://pump.fun/coin/6vUhppYep18WSncUDR6Brt9yZw31ycLDPDEHo13pump
Chart: https://dexscreener.com/solana/6vUhppYep18WSncUDR6Brt9yZw31ycLDPDEHo13pump
```

Repeat for trigger phrase: `token`, `ca`, `contract`

---

### Trigger: "install" or "setup" or "docker"

| Field | Value |
|-------|-------|
| Trigger Type | Contains |
| Trigger Phrase | `install` |
| Reply to Message | Yes |

**Response:**
```
Install xBridge MCP via Docker:

docker pull hrco/xbridge-mcp:latest
docker run -e XAI_API_KEY=your_key hrco/xbridge-mcp:latest

Full guide + Claude Code config:
https://github.com/hrco/xbridge-mcp
```

Repeat for trigger phrases: `setup`, `docker`, `how to start`

---

### Trigger: "price" alternative — MCP tool price

| Trigger Phrase | `€3.69` or `cost` or `paid` |
|-------|-------|
| Response | `xBridge MCP is €3.69/mo — paid Docker image, BYOK (your own XAI_API_KEY). GitHub: https://github.com/hrco/xbridge-mcp` |

---

## 3. Welcome Message for New Members

**Dashboard path:** Moderation → Greetings → Enable
Apply to: **@xBridgeCommunity only**

Settings:
- Message Type: Text Message
- Send as Reply: Yes (to join notification)
- Delete After: 48 hours
- Target: New Members Only

**Welcome text:**
```
👋 Welcome to xBridge MCP Community!

xBridge MCP bridges Claude Code → xAI Grok API.
16 tools: chat, web/X search, sessions, chains, image gen, video gen, docs.

🐳 Install:
docker pull hrco/xbridge-mcp:latest

🔑 You need your own XAI_API_KEY (free at x.ai/api)

💰 €3.69/mo · BYOK · Paid Docker image
📦 GitHub: https://github.com/hrco/xbridge-mcp
🌐 Site: https://xbridgemcp.com

Community token: $XBRDG on Solana
CA: 6vUhppYep18WSncUDR6Brt9yZw31ycLDPDEHo13pump

Ask anything here 👇
```

---

## Quick Reference — All Triggers to Set Up

| Trigger phrase | Auto-reply topic |
|----------------|-----------------|
| `price` | $XBRDG pump.fun link + CA |
| `token` | $XBRDG pump.fun link + CA |
| `ca` | $XBRDG CA only |
| `contract` | $XBRDG CA only |
| `install` | Docker install command + GitHub |
| `setup` | Docker install command + GitHub |
| `docker` | Docker install command + GitHub |
| `how to start` | Docker install command + GitHub |
| `cost` | €3.69/mo pricing info |
| `paid` | €3.69/mo pricing info |
| `xai` | Brief: "xBridge uses xAI Grok API. BYOK via XAI_API_KEY from x.ai/api" |

---

## Notes

- Broadcast channel @xBridgeMCP: use Scheduled Messages only (no member joins = no welcome/triggers)
- Free Combot tier: up to 5 scheduled messages, ~10 triggers
- Upgrade to Combot Pro for unlimited triggers + inline buttons in welcome
- Test triggers by posting the keyword yourself in the group
