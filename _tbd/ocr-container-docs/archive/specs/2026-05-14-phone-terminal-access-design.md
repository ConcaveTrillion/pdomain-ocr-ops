# Phone Terminal Access to VSCode Devcontainer

**Date:** 2026-05-14  
**Status:** Approved

## Problem

Need to reach a tmux session running inside a VSCode devcontainer on a Linux dev machine from an Android phone over the internet.

## Architecture

```
Termux (Android) → SSH (Tailscale WireGuard) → Linux host → docker exec → devcontainer → tmux
```

The phone connects via SSH to the dev machine over a Tailscale private tunnel. The host immediately runs `docker exec` into the devcontainer and attaches (or creates) a named tmux session. From the phone's perspective it is a single SSH connection that drops directly into the devcontainer shell.

Regular SSH access to the host (from laptop or elsewhere) is completely unaffected — no server-side config is changed.

## Components

### 1. Tailscale (network layer)

- Install Tailscale on the Linux dev machine (the Docker host): `curl -fsSL https://tailscale.com/install.sh | sh && sudo tailscale up`
- Install the Tailscale Android app and sign in with the same account
- Both devices join the same tailnet; the dev machine gets a stable hostname like `dev-machine.tail12345.ts.net`
- Tailscale runs as a system service on the host — stays up without VSCode open

### 2. SSH server on host

The host must have `sshd` running and the phone's SSH public key in `~/.ssh/authorized_keys`. No changes to `sshd_config` are needed.

Generate a key pair in Termux if you don't have one:
```bash
ssh-keygen -t ed25519 -C "android-phone"
```

Copy the public key to the host's `~/.ssh/authorized_keys` (do this once, e.g. paste it in from the VSCode terminal).

### 3. tmux inside the devcontainer

tmux must be installed inside the devcontainer, not just on the host.

Verify: `docker exec -it <container> which tmux`

If missing, add it to your `devcontainer.json` `postCreateCommand` or Dockerfile so it persists across rebuilds.

### 4. Termux SSH config (Android)

In Termux, create `~/.ssh/config`:

```
# Normal host shell
Host devhost
  HostName dev-machine.tail12345.ts.net
  User <your-linux-username>
  IdentityFile ~/.ssh/id_ed25519

# One-shot into devcontainer tmux
Host devbox
  HostName dev-machine.tail12345.ts.net
  User <your-linux-username>
  IdentityFile ~/.ssh/id_ed25519
  RequestTTY force
  RemoteCommand docker exec -it <container-name> tmux new-session -As main
```

- `ssh devhost` → normal interactive shell on the Linux host
- `ssh devbox` → lands directly in the devcontainer tmux session (creates one named `main` if none exists, attaches otherwise)

Find the container name with `docker ps` on the host — for this workspace it is likely `ocr-container_devcontainer` or similar.

## Data Flow

1. Phone connects to Tailscale (automatic, always-on)
2. `ssh devbox` from Termux → Tailscale routes to host's port 22
3. Host authenticates via ed25519 key, runs `RemoteCommand`
4. `docker exec` attaches to the running devcontainer
5. tmux creates or re-attaches the `main` session
6. Phone is now in the devcontainer shell with full tmux session persistence

## Error Handling / Edge Cases

| Situation | Behaviour |
|-----------|-----------|
| Devcontainer not running | `docker exec` fails with "no such container"; start the container first via VSCode on the host |
| tmux not in devcontainer | `docker exec` exits immediately; install tmux and rebuild |
| Tailscale not running on host | SSH times out; `sudo systemctl start tailscaled` on host |
| SSH key not in authorized_keys | SSH asks for password (or rejects); add the key once |
| Session already open elsewhere | tmux attaches to existing session — correct behaviour for phones |

## Testing / Verification

1. From the host, confirm Tailscale is up: `tailscale status`
2. From Termux: `ssh devhost` → should get a host shell
3. From Termux: `ssh devbox` → should land in devcontainer tmux
4. Disconnect and reconnect: session should survive and re-attach
5. Verify normal laptop SSH still works (nothing changed server-side)

## What Is Not Covered

- Tailscale exit-node / VPN-for-all-traffic (not needed here)
- Exposing the devcontainer's sshd directly (more complex, not required)
- iOS (different SSH client apps, same Tailscale approach applies)
