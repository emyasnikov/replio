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

Add an agent by copying a service block and changing the name, port, and volume. Bring the fleet up with `docker compose up -d`.

## systemd

The template unit is `deploy/replio@.service`. It is a template, so the service name supplies the instance. Copy it into place and enable one instance per agent:

```bash
sudo cp deploy/replio@.service /etc/systemd/system/
sudo systemctl enable replio@docs --now
```

The instance name `docs` is used in three places. It is the working directory, `WorkingDirectory=/srv/replio/%i`, the project path passed to `replio serve`, and the user the service runs as, `User=%i`. Create the directory with the agent config and a matching user:

```bash
sudo mkdir -p /srv/replio/docs
sudo useradd -r -d /srv/replio/docs docs
# place .replio/config.json under /srv/replio/docs
```

The API key is read from `/etc/replio/<name>.env` through `EnvironmentFile`. Create one per agent:

```bash
# /etc/replio/docs.env
REPLIO_API_KEY=...
```

`Restart=on-failure` restarts the agent if it exits abnormally. Logs go to the journal:

```bash
journalctl -u replio@docs -f
```

### Ports

The template binds `127.0.0.1:8787` for every instance. Give each agent its own port in its environment file and override the `ExecStart` command by redefining it in a drop-in:

```bash
sudo mkdir -p /etc/systemd/system/replio@docs.service.d
# /etc/systemd/system/replio@docs.service.d/port.conf
[Service]
ExecStart=
ExecStart=/usr/local/bin/replio serve --host 127.0.0.1 --port 8781 --path /srv/replio/docs
```

The empty `ExecStart=` clears the unit default before the new line takes effect.

## launchd (macOS)

The template is `deploy/com.replio.agent.plist.example`. On macOS you run one LaunchAgent per agent in your own user session. Copy the plist to `~/Library/LaunchAgents/`, replace the `<NAME>` and `<USER>` placeholders, and adjust the path:

```xml
<key>ProgramArguments</key>
<array>
    <string>/usr/local/bin/replio</string>
    <string>serve</string>
    <string>--host</string>
    <string>127.0.0.1</string>
    <string>--port</string>
    <string>8781</string>
    <string>--path</string>
    <string>/Users/you/agents/docs</string>
</array>
```

Give each agent a distinct port and project path. Load it:

```bash
cp ~/Library/LaunchAgents/com.replio.docs.plist
launchctl load ~/Library/LaunchAgents/com.replio.docs.plist
```

`RunAtLoad` starts the agent when you log in and `KeepAlive` restarts it if it exits. Standard output and error go to `/tmp/replio-<name>.log` and `/tmp/replio-<name>.err.log`, or you can point those keys at files under `~/Library/Logs/`.

The API key comes from the agent's own `~/.config/replio/config.json` or `.replio/config.json`, just like a normal local install.

## Health checks

Every deployed agent exposes `GET /health`, which returns `{"status": "ok"}`. Docker Compose and systemd pick up a dead agent through their restart policy. For an external monitor, poll the health endpoint on each agent's port:

```bash
curl -fsS localhost:8781/health
```