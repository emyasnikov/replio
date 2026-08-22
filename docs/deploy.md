# Deployment

You can run `replio serve` directly, but a fleet of agents is best supervised by Docker: one container per agent, restarted on failure, with the agent's config and sessions kept on a mounted folder. Replio has two install paths:

- **Single interactive agent** - install with pipx and run the REPL, `replio run`, or `replio serve` by hand. See the [README](../README.md).
- **Supervised fleet or always-on server** - this page. Build the image from the repo's `Dockerfile` and run one container per agent with `docker-compose.yml.example`.

The Docker templates live at the repo root (`Dockerfile`, `replio-entrypoint.sh`, `docker-compose.yml.example`) and work as-is. Per-agent values - the project path, the port, and the API key - are configured on your machine, never in the templates.

A deployed agent is always just `replio serve` pointed at a folder inside the container. The folder holds `.replio/config.json` with the provider, model, system prompt, tool permissions, and plugins. Sessions are written under `.replio/sessions/` in the same folder. Mount that folder into the container and the agent keeps its state across restarts.

## Docker

The image runs `replio serve` and takes three environment variables:

| Variable | Default | Purpose |
|----------|---------|---------|
| `REPLIO_HOST` | `0.0.0.0` | Bind address |
| `REPLIO_PORT` | `8787` | Bind port |
| `REPLIO_PATH` | (unset) | Project path the agent is scoped to. When set, the server uses `--path` and reads `.replio/config.json` from that directory |

Build the image from the repo root:

```bash
docker build -t replio .
```

### Single agent

```bash
docker run -d --name docs-agent -p 127.0.0.1:8781:8781 \
  -e REPLIO_PORT=8781 \
  -e REPLIO_PATH=/srv/docs \
  -v "$PWD/agents/docs:/srv/docs" \
  replio
```

The mounted `agents/docs` directory holds the agent's `.replio/config.json` (with the API key, model, and permissions) and its sessions. The container runs as root, so agent-written session files are root-owned on the host, add `--user "$(id -u):$(id -g)"` if you want them owned by your uid.

### Fleet with Docker Compose

The file `docker-compose.yml.example` at the repo root defines one service per agent. Copy it to `docker-compose.yml`, adjust the services (name, `REPLIO_PATH`, port, volume - the API key and model come from the mounted `.replio/config.json`):

```yaml
services:
  docs-agent:
    build:
      context: .
    environment:
      REPLIO_PORT: 8781
      REPLIO_PATH: /srv/docs
    volumes:
      - ./agents/docs:/srv/docs
    ports:
      - "127.0.0.1:8781:8781"
    restart: unless-stopped
```

Ports publish on `127.0.0.1` so the JSON API stays host-local behind your reverse proxy. Containers run as root, add `user: "1000:1000"` (your uid) to a service if you want agent-written files in the mounted folders owned by you.

Add an agent by copying a service block and changing the name, port, and volume. Bring the fleet up:

```bash
docker compose up -d
```

Compose's `restart: unless-stopped` restarts a dead agent. See [docs/usage/programming.md](usage/programming.md) for a full role-based programming fleet built on this template.

## Health checks

Every deployed agent exposes `GET /health`, which returns `{"status": "ok"}`. For an external monitor, poll the health endpoint on each agent's port:

```bash
curl -fsS localhost:8781/health
```
