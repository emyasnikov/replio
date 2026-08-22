# Deployment

You can run `replio serve` directly, but for a fleet of agents you usually want each one supervised and restarted on failure. Three options are covered here: Docker, systemd on Linux, and launchd on macOS.

The three options are alternatives. Pick the one that matches your host: systemd on bare-metal Linux, launchd on macOS, and Docker on containerized or mixed hosts. You need only one of them, and each supervises the process and restarts it on failure.

Generic templates live in [`deploy/`](../deploy/). They are held in the repo and work as-is. The per-agent values, like the project path, the port, and the API key, are configured on your machine, never in the templates.

A deployed agent is always just `replio serve` pointed at a folder. The folder holds `.replio/config.json` with the provider, model, system prompt, tool permissions, and plugins. Sessions are written under `.replio/sessions/` in the same folder. Mount that folder into the container or point a service unit at it and the agent keeps its state across restarts.

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
docker run -d --name docs-agent -p 8781:8781 \
  -e REPLIO_PORT=8781 \
  -e REPLIO_PATH=/srv/docs \
  -v "$PWD/agents/docs:/srv/docs" \
  replio
```

The mounted `/srv/docs` directory holds the agent's `.replio/config.json` and its sessions. Put the API key in that config, or pass it with `-e REPLIO_API_KEY=...` and set it in the config later.

### Fleet with Docker Compose

The file `docker-compose.yml.example` defines one service per agent. Copy it to `docker-compose.yml` and adjust the services.
```

```yaml
services:
  docs-agent:
    build:
      context: ..
      dockerfile: deploy/Dockerfile
    environment:
      REPLIO_PORT: 8781
      REPLIO_PATH: /srv/docs
    volumes:
      - ./agents/docs:/srv/docs
    ports:
      - "8781:8781"
    restart: unless-stopped
```


## Health checks

Every deployed agent exposes `GET /health`, which returns `{"status": "ok"}`. For an external monitor, poll the health endpoint on each agent's port:

```bash
curl -fsS localhost:8781/health
```