---
status: complete
---

# Phone Terminal Access — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Access a tmux session inside a VSCode devcontainer from an Android phone over the internet, using Tailscale for networking and SSH for the terminal hop.

**Architecture:** Tailscale creates a private WireGuard tunnel between the Android phone and the Linux dev machine. SSH from Termux on the phone connects to the host via Tailscale; a `RemoteCommand` in the Termux SSH config runs `docker exec` to drop the session directly into the devcontainer's tmux. No server-side sshd config is changed, so existing SSH access from laptop/desktop is unaffected.

**Tech Stack:** Tailscale, OpenSSH (host + Termux), tmux (inside devcontainer), Docker, Android/Termux

---

### Task 1: Install Tailscale on the Linux dev machine (host)

**Files:** none (system-level install)

- [ ] **Step 1: Install Tailscale**

Run on the host machine (not inside the devcontainer — open a host terminal or VSCode integrated terminal then exit to the host):

```bash
curl -fsSL https://tailscale.com/install.sh | sh
```

- [ ] **Step 2: Authenticate and bring up Tailscale**

```bash
sudo tailscale up
```

A URL is printed. Open it in a browser, sign in with your Tailscale account (create one free at tailscale.com if you don't have one), and authorise the machine.

- [ ] **Step 3: Note your machine's Tailscale hostname**

```bash
tailscale status
```

Expected output includes a line like:

```
100.x.y.z   dev-machine   yourname@   linux   -
```

Also run:

```bash
tailscale status --json | python3 -c "import sys,json; d=json.load(sys.stdin); print(d['Self']['DNSName'])"
```

This prints the stable MagicDNS hostname (e.g. `dev-machine.tail12345.ts.net`). **Record this — you'll use it in Task 4.**

- [ ] **Step 4: Verify Tailscale service is enabled at boot**

```bash
sudo systemctl is-enabled tailscaled
```

Expected: `enabled`. If it says `disabled`, run:

```bash
sudo systemctl enable tailscaled
```

---

### Task 2: Install Tailscale on Android and join the tailnet

**Files:** none (phone setup)

- [ ] **Step 1: Install the Tailscale app**

On your Android phone, install **Tailscale** from the Google Play Store.

- [ ] **Step 2: Sign in with the same account**

Open the app, sign in with the same account you used in Task 1. Tap **Connect**.

- [ ] **Step 3: Verify both devices appear in the tailnet**

In the Tailscale app on the phone, tap the device list. You should see your dev machine listed as online with its hostname. If the machine shows as "offline", go back to the host and run `sudo tailscale up` again.

---

### Task 3: Verify SSH access to the host is possible

**Files:** none (SSH key setup)

SSH must be running on the host and the phone's public key must be in `authorized_keys`.

- [ ] **Step 1: Install Termux on Android**

Install **Termux** from F-Droid (preferred) or Google Play. Open Termux.

- [ ] **Step 2: Install OpenSSH in Termux**

```bash
pkg update && pkg install openssh
```

- [ ] **Step 3: Generate an SSH key pair in Termux (if you don't already have one)**

```bash
ssh-keygen -t ed25519 -C "android-phone" -f ~/.ssh/id_ed25519
```

Press Enter twice to accept defaults (no passphrase, or add one for security).

- [ ] **Step 4: Display the public key**

```bash
cat ~/.ssh/id_ed25519.pub
```

Copy the entire output (starts with `ssh-ed25519 ...`).

- [ ] **Step 5: Add the public key to the host**

On the host (use the VSCode terminal or any existing shell), append the key:

```bash
echo 'PASTE_PUBLIC_KEY_HERE' >> ~/.ssh/authorized_keys
chmod 600 ~/.ssh/authorized_keys
```

Replace `PASTE_PUBLIC_KEY_HERE` with the key you copied.

- [ ] **Step 6: Verify SSH is running on the host**

On the host:

```bash
sudo systemctl is-active ssh || sudo systemctl is-active sshd
```

Expected: `active`. If inactive:

```bash
sudo systemctl start ssh   # Debian/Ubuntu
# or
sudo systemctl start sshd  # Fedora/Arch
```

- [ ] **Step 7: Test plain SSH from Termux**

In Termux (replace `youruser` and the hostname with your values from Task 1 Step 3):

```bash
ssh youruser@dev-machine.tail12345.ts.net
```

Expected: you get a shell prompt on the host. Type `exit` when done.

If it times out, check `tailscale status` on the host. If it asks for a password, the public key wasn't added correctly — repeat Step 5.

---

### Task 4: Verify tmux is installed inside the devcontainer

**Files:** possibly `devcontainer.json` if tmux is missing

- [ ] **Step 1: Find your devcontainer name**

On the host:

```bash
docker ps --format 'table {{.Names}}\t{{.Image}}\t{{.Status}}'
```

Look for the container that corresponds to this workspace (likely something like `ocr-container_devcontainer` or a hash-based name). **Record the exact name.**

- [ ] **Step 2: Check if tmux is installed inside the container**

```bash
docker exec -it <container-name> which tmux
```

Expected: `/usr/bin/tmux` or similar. If the command exits with nothing, tmux is not installed.

- [ ] **Step 3 (only if tmux is missing): Install tmux inside the container**

```bash
docker exec -it <container-name> bash -c "apt-get update && apt-get install -y tmux"
```

This installs it for the current container run. To make it persist across rebuilds, add to `.devcontainer/devcontainer.json`:

```json
"postCreateCommand": "sudo apt-get install -y tmux"
```

Or add it to the Dockerfile used by the devcontainer.

- [ ] **Step 4: Verify docker exec + tmux works end-to-end from the host**

```bash
docker exec -it <container-name> tmux new-session -As main
```

Expected: a tmux session opens inside the container. Press `Ctrl-b d` to detach. Running this a second time should re-attach to the same session.

---

### Task 5: Configure Termux SSH aliases

**Files:** `~/.ssh/config` in Termux (on the phone)

- [ ] **Step 1: Create the SSH config in Termux**

In Termux on the phone (replace all placeholders with your actual values):

```bash
mkdir -p ~/.ssh
cat > ~/.ssh/config << 'EOF'
# Normal interactive shell on the host
Host devhost
  HostName dev-machine.tail12345.ts.net
  User yourlinuxusername
  IdentityFile ~/.ssh/id_ed25519

# Direct drop into devcontainer tmux session
Host devbox
  HostName dev-machine.tail12345.ts.net
  User yourlinuxusername
  IdentityFile ~/.ssh/id_ed25519
  RequestTTY force
  RemoteCommand docker exec -it ocr-container_devcontainer tmux new-session -As main
EOF
chmod 600 ~/.ssh/config
```

Replace:
- `dev-machine.tail12345.ts.net` → your Tailscale hostname from Task 1 Step 3
- `yourlinuxusername` → your Linux username on the host
- `ocr-container_devcontainer` → the container name from Task 4 Step 1

---

### Task 6: End-to-end verification

- [ ] **Step 1: Test host alias**

In Termux:

```bash
ssh devhost
```

Expected: host shell prompt (e.g. `youruser@dev-machine:~$`). Type `exit`.

- [ ] **Step 2: Test devcontainer alias**

In Termux:

```bash
ssh devbox
```

Expected: you land inside the devcontainer in a tmux session named `main`. Your prompt will reflect the container's shell (e.g. `vscode@...:/workspaces/ocr-container$`).

- [ ] **Step 3: Verify session persistence**

While connected via `ssh devbox`, open a second pane with `Ctrl-b %`. Type something in it. Then disconnect by closing Termux entirely.

Reconnect with `ssh devbox`. Expected: you re-attach to the same tmux session with both panes still intact.

- [ ] **Step 4: Verify laptop SSH still works**

From your laptop (not the phone), SSH to the host as normal. Expected: unaffected — the host sshd config was never changed.

---

### Task 7: Optional — add a Termux home-screen shortcut

- [ ] **Step 1: Create a Termux widget script**

Install the **Termux:Widget** add-on from F-Droid. Then in Termux:

```bash
mkdir -p ~/.shortcuts
cat > ~/.shortcuts/devbox.sh << 'EOF'
#!/data/data/com.termux/files/usr/bin/bash
ssh devbox
EOF
chmod +x ~/.shortcuts/devbox.sh
```

- [ ] **Step 2: Add the widget to your home screen**

Long-press the Android home screen → Widgets → Termux:Widget → select `devbox`. Tapping it launches Termux and immediately connects to your devcontainer tmux session.
