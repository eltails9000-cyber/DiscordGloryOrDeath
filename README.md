# Discord Bot

A professional, production-ready Discord bot built with Python 3.13 and Pycord.

## Features

| Module | Commands / Features |
|---|---|
| **Moderation** | `/ban`, `/unban`, `/kick`, `/timeout`, `/untimeout`, `/warn`, `/warnings`, `/clearwarnings`, `/purge`, `/slowmode`, `/lock`, `/unlock`, `/userinfo` |
| **Security** | Anti-spam, Anti-raid (auto-lockdown), Anti-scam links, Anti-invite, Anti-mass-mention, Anti-alt detection |
| **Verification** | Captcha button flow, account age requirement, auto role grant, alt detection |
| **Giveaways** | `/giveaway start/end/reroll/list`, persistent buttons, multiple winners, requirements |
| **Announcements** | `/announce`, `/scheduleannounce`, `/poll`, `/suggest`, `/reviewsuggestion` |
| **AI FAQ** | `/ask`, `/ai addknowledge/removeknowledge/listknowledge`, custom knowledge base |
| **Owner** | `/reload`, `/loadcog`, `/unloadcog`, `/botstatus`, `/shutdown`, `/botinfo`, `/servers`, `/dm` |
| **Config** | `/config show/setlogchannel/setmodlogchannel/setwelcomechannel/setleavechannel/setsuggestchannel/setsecuritychannel/setprefix` |
| **Logging** | Message delete/edit, member join/leave, bans, role changes, voice updates |

## Setup

### 1. Environment variables

Copy `.env.example` to `.env` and fill in the required values:

```bash
cp bot/.env.example bot/.env
```

At minimum you need:
- `DISCORD_TOKEN` — your bot token from the [Discord Developer Portal](https://discord.com/developers/applications)
- `OWNER_IDS` — your Discord user ID (right-click → Copy ID with Developer Mode enabled)

All channel and role IDs are **optional** — features that depend on them are silently skipped if not configured.

### 2. Install dependencies

```bash
pip install -r bot/requirements.txt
```

### 3. Run the bot

```bash
python bot/main.py
```

## Architecture

```
bot/
├── main.py              # Entry point — initialises DB, loads cogs, starts bot
├── config.py            # All configuration — reads from env, no hardcoded IDs
├── database.py          # Schema creation and connection factory (aiosqlite)
│
├── cogs/                # Discord command groups (one file per feature)
│   ├── moderation.py    # Slash commands: ban, kick, timeout, warn, purge…
│   ├── security.py      # Slash commands: lockdown, security status
│   ├── verification.py  # Slash commands: setupverification, status
│   ├── giveaways.py     # Slash commands: giveaway start/end/reroll/list
│   ├── announcements.py # Slash commands: announce, poll, suggest
│   ├── ai.py            # Slash commands: ask, ai knowledge management
│   ├── owner.py         # Slash commands: reload, status, shutdown…
│   ├── events.py        # Event listeners: on_message, on_member_join…
│   └── config_cog.py    # Slash commands: /config set*
│
├── services/            # Business logic (no Discord knowledge)
│   ├── database_service.py   # Generic DB helpers (fetchone, execute…)
│   ├── moderation_service.py # Warning/mute/ban CRUD
│   ├── security_service.py   # In-memory spam/raid trackers, domain checks
│   ├── verification_service.py # Captcha flow, role assignment
│   ├── giveaway_service.py   # Giveaway lifecycle, entry tracking
│   ├── announcement_service.py # Scheduled messages, polls, suggestions
│   └── ai_service.py         # OpenAI integration, knowledge base
│
├── utils/               # Shared utilities
│   ├── embeds.py        # Branded embed factory functions
│   ├── permissions.py   # Role/permission helper functions
│   ├── checks.py        # Slash command permission decorators
│   ├── cooldowns.py     # Custom cooldown manager
│   ├── helpers.py       # Duration parsing, URL extraction, etc.
│   ├── logger.py        # Structured rotating file + console logging
│   └── views.py         # Persistent Discord UI components
│
└── data/                # Runtime data (auto-created)
    ├── database.db      # SQLite database
    ├── logs/            # Rotating log files
    └── backups/         # Database backups
```

## Configuration

All settings live in `config.py` which reads from environment variables.  
**Never hardcode IDs** — use the `/config set*` slash commands to configure channels per-guild,
or set them globally via environment variables before starting.

### Security thresholds

| Setting | Default | Description |
|---|---|---|
| `SECURITY_SPAM_THRESHOLD` | 5 | Messages before timeout |
| `SECURITY_SPAM_INTERVAL` | 5s | Sliding window |
| `SECURITY_RAID_JOIN_THRESHOLD` | 10 | Joins before lockdown |
| `SECURITY_RAID_INTERVAL` | 10s | Join tracking window |
| `SECURITY_MIN_ACCOUNT_AGE` | 7 days | Alt detection threshold |
| `SECURITY_MASS_MENTION_THRESHOLD` | 5 | Mentions before action |

### Moderation escalation

Warnings automatically escalate:
- ≥ `MOD_WARN_THRESHOLD_MUTE` (3) → auto timeout
- ≥ `MOD_WARN_THRESHOLD_KICK` (5) → auto kick
- ≥ `MOD_WARN_THRESHOLD_BAN` (7) → auto ban

## Required Discord Permissions

- `Manage Roles` — for verification, mute role
- `Manage Channels` — for lockdown
- `Moderate Members` — for timeouts
- `Ban Members` — for bans
- `Kick Members` — for kicks
- `Manage Messages` — for purge, anti-spam delete
- `Send Messages`, `Embed Links`, `Read Message History` — general operation

**The bot's role must be above all roles it needs to assign/remove.**

## AI Feature

The `/ask` command uses OpenAI by default. Set `OPENAI_API_KEY` in your environment.  
You can also build a local knowledge base with `/ai addknowledge` — keyword matches are
checked first before hitting OpenAI, reducing API costs.

## Deployment on Replit

1. Add `DISCORD_TOKEN` (and other secrets) via the Secrets panel.
2. The bot workflow will run `python bot/main.py` automatically.
3. Use an [UptimeRobot](https://uptimerobot.com/) ping or Replit's **Always On** to keep it running.
