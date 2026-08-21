# Kova

> **Kova** — Terminal-native AI programming assistant with persistent memory, team collaboration, and sandboxed execution.

<p align="center">
  <img src="https://img.shields.io/badge/python-3.11+-blue?style=flat&logo=python&logoColor=white" alt="Python version">
  <img src="https://img.shields.io/badge/license-MIT-green?style=flat" alt="License">
  <img src="https://img.shields.io/badge/status-beta-orange?style=flat" alt="Status">
  <img src="https://img.shields.io/badge/terminal-TUI-875FFF?style=flat&logo=terminal&logoColor=white" alt="Terminal UI">
</p>

<div align="center">

[✨ Features](#-features) · [🚀 Installation](#-installation) · [⚡ Quick Start](#-quick-start) · [🧠 Architecture](#-architecture) · [🔧 Configuration](#-configuration) · [📖 Commands](#-commands)

</div>

---

## ✨ Features

- **🧠 Persistent Memory** — Type‑tagged memories (user/project/reference) survive across sessions with automatic consolidation.
- **🤖 Sub‑Agents** — Delegate work to specialized agents (Explore, Plan, General‑Purpose, Verification) with isolated toolsets.
- **👥 Team & Swarm Mode** — Create teams of agents that communicate via mailbox, run in worktrees, and coordinate in real time.
- **🔒 Fine‑grained Permissions** — 4 permission modes (Default / AcceptEdits / Plan / Bypass), rule‑based allow/deny, and OS‑level sandboxing (macOS Seatbelt / Linux Bubblewrap).
- **📎 Worktree Isolation** — Each agent can work in a disposable Git worktree; changes can be kept or discarded.
- **📦 Skill System** — Loadable skill packages (fork/inline) that expand Kova’s capabilities on demand.
- **🔌 MCP Server Integration** — Connect to Model Context Protocol servers for extended tools and resources.
- **🪝 Hook Engine** — Define shell commands that fire on lifecycle events (pre‑tool, post‑tool, session start/end, etc.).
- **🔄 Context Management** — Automatic compaction and tool‑result spilling to disk keeps large sessions under context limits.
- **🌐 Remote UI** — Optional WebSocket‑based web interface for browser access.

---

## 🚀 Installation

```bash
# Clone the repository
git clone https://github.com/your-org/kova.git
cd kova

# Create a virtual environment
python -m venv .venv
source .venv/bin/activate   # or `.venv\Scripts\activate` on Windows

# Install Kova
pip install -e .
```

### Requirements

- Python 3.11 or later
- macOS (Seatbelt) or Linux (Bubblewrap) for OS‑level sandboxing
- `git` (for worktree support)
- Optional: `tmux` or iTerm2 for team pane backend

---

## ⚡ Quick Start

```bash
# Run Kova in your project directory
kova

# With a specific permission mode
kova --mode bypassPermissions

# Non‑interactive mode (headless)
kova -p "Explain the project structure" --output-format stream-json

# Remote web UI mode
kova --remote
```

Once inside the terminal UI:

- Type your request and press `Enter` to send.
- Use `/` for commands — e.g., `/help`, `/plan`, `/memory`, `/permission mode bypassPermissions`.
- Press `Shift+Tab` to cycle permission modes.
- `Ctrl+O` to toggle tool output blocks.

---

## 🧠 Architecture

Kova is built as a modular event‑driven system:

| Component        | Description                                                                 |
|------------------|-----------------------------------------------------------------------------|
| **Agent**        | Main loop with streaming, tool execution, and permission orchestration.     |
| **Tool Registry**| Pluggable tools (Bash, ReadFile, EditFile, WriteFile, Grep, Glob, MCP…).   |
| **Permission**   | Multi‑layer decision engine (dangerous‑commands, sandbox, rules, modes).    |
| **Sub‑Agent**    | Forked or definition‑based child agents with isolated tools/traces.         |
| **Teams**        | Collaborative agent teams with mailboxes, shared tasks, and backends.       |
| **Worktree**     | Isolated Git worktrees per agent, with automatic cleanup.                   |
| **Memory**       | Persistent memory files + auto‑extraction + consolidation (dream).          |
| **Skills**       | Reusable skill packages (SOPs) that can be loaded via `/skill`.             |
| **MCP**          | Client for Model Context Protocol servers (stdio/HTTP).                     |
| **Hooks**        | Shell/HTTP/Agent callbacks triggered by lifecycle events.                   |
| **Session**      | JSONL‑based conversation history with compaction and resume.                |
| **TUI**          | Textual‑based terminal interface with inline widgets for permissions/plan.  |
| **Remote**       | WebSocket server that provides a browser UI (optional).                     |

---

## 🔧 Configuration

Koa looks for `config.yaml` in these locations (higher priority last):

1. `~/.kova/config.yaml` — global user config
2. `<project>/.kova/config.yaml` — project‑level config
3. `<project>/.kova/config.local.yaml` — local overrides (git‑ignored)

### Minimal example

```yaml
providers:
  - name: anthropic
    protocol: anthropic
    base_url: https://api.anthropic.com/v1
    model: claude-sonnet-4-6
    api_key: ${ANTHROPIC_API_KEY}
    context_window: 200000
    thinking: true

permission_mode: default
enable_fork: true
enable_verification_agent: true

mcp_servers:
  - name: github
    command: npx
    args: ["-y", "@modelcontextprotocol/server-github"]
    env:
      GITHUB_TOKEN: ${GITHUB_TOKEN}

hooks:
  - id: auto-format
    event: post_tool_use
    if: 'tool == "WriteFile"'
    action:
      type: command
      command: "prettier --write $TOOL_ARGS.file_path"

sandbox:
  enabled: true
  auto_allow: true
  network_enabled: false

worktree:
  symlink_directories: ["node_modules", ".venv"]
  stale_cleanup_interval: 3600
  stale_cutoff_hours: 24
```

### Permission Modes

| Mode               | Read | Write | Command |
|--------------------|------|-------|---------|
| `default`          | ✅   | ❓ Ask | ❓ Ask  |
| `acceptEdits`      | ✅   | ✅    | ❓ Ask  |
| `plan`             | ✅   | ❓ Ask | ❓ Ask  |
| `bypassPermissions`| ✅   | ✅    | ✅      |

---

## 📖 Built‑in Commands

| Command           | Aliases | Description                               |
|-------------------|---------|-------------------------------------------|
| `/help`           | h, ?    | Show command help                         |
| `/status`         | s       | Display session & token usage             |
| `/clear`          |         | Reset conversation and session            |
| `/compact`        | c       | Manually compress context                 |
| `/plan`           | p       | Enter Plan mode                           |
| `/session`        |         | Manage sessions (`list`, `resume`, `new`) |
| `/memory`         |         | View/edit persistent memories             |
| `/permission`     |         | Manage permission modes/rules             |
| `/sandbox`        |         | Toggle OS sandbox (`on-auto`, `on`, `off`)|
| `/rewind`         |         | Restore previous checkpoint               |
| `/skill`          | skills  | List/load/reload skills                   |
| `/tasks`          | task    | View background sub‑agent tasks           |
| `/trace`          | tree    | Show agent call tree                      |
| `/worktree`       | wt      | Manage Git worktrees                      |
| `/mcp`            |         | Show MCP server status                    |

---

## 🧪 Development

### Run tests

```bash
pytest tests/ -v
```

### Project Structure

```
kova/
├── agents/          # Sub‑agent definitions & loader
├── commands/        # Slash command registry & handlers
├── context/         # Context management (compaction, spilling)
├── filehistory/     # File snapshots for /rewind
├── hooks/           # Hook engine & executors
├── mcp/             # MCP client & tool wrapper
├── memory/          # Persistent memory, consolidation, recall
├── permissions/     # Multi‑layer permission checker
├── sandbox/         # OS sandbox implementations
├── skills/          # Skill parser, loader, executor
├── teams/           # Team coordination (mailbox, tasks, backends)
├── tools/           # Tool implementations (Bash, file ops, etc.)
├── worktree/        # Git worktree manager
├── agent.py         # Main Agent loop
├── app.py           # TUI application
├── client.py        # LLM clients (Anthropic, OpenAI, compatible)
├── config.py        # Config loading & validation
├── conversation.py  # Conversation manager
├── prompts.py       # System prompt builder
├── remote.py        # WebSocket remote server
└── serialization.py # Provider‑specific message formatting
```

---

## 📄 License

[MIT](LICENSE)

---

## 🌟 Acknowledgements

Built with ❤️ using [Textual](https://github.com/Textualize/textual), inspired by tools like Claude Code and Cline.
