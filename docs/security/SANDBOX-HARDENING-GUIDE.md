# Sandbox Hardening Guide
Author: Bogdan Ticu

## Overview

Skills run in Docker containers with strict isolation. This document explains the security setup.

## Container Isolation

Each skill runs in its own container:

```bash
docker run \
  --rm \
  --read-only \
  --memory 512m \
  --cpus 1 \
  --cap-drop=ALL \
  --cap-add=NET_BIND_SERVICE \
  --security-opt no-new-privileges \
  -v <declared-paths>:ro \
  <skill-image>
```

What this does:
- read-only root filesystem (can't modify system)
- Memory capped at 512MB
- CPU limited to 1 core
- Drop all capabilities (can't escalate)
- No new privileges allowed
- Only declared files mounted

## File Access Control

Skill manifest declares paths:

```yaml
capabilities:
  file_read:
    paths:
      - /tmp/uploads/*
      - /home/user/documents/*
  file_write:
    paths:
      - /tmp/outputs/*
```

What is enforced:
- Read allowed only from declared paths
- Write allowed only from declared paths
- No access to /etc, /root, /sys, /proc
- No .. path traversal
- No symlinks to restricted areas
- Violations kill process

Example attack prevented:
```python
# Skill tries to read /etc/passwd
with open("/etc/passwd") as f:
    data = f.read()
```
Result: Permission denied. Process exits.

## Network Isolation

Skill manifest declares network access:

```yaml
capabilities:
  network:
    - domain: api.example.com
      protocol: [https]
      ports: [443]
```

What is enforced:
- DNS requests for other domains blocked
- Connections to other IPs rejected
- Only declared protocol allowed
- Only declared port allowed
- All requests logged

Example attack prevented:
```python
import socket
# Skill tries to connect to malicious server
socket.connect(("evil.com", 22))
```
Result: Connection refused. Logged.

## Subprocess Execution

Skill manifest declares commands:

```yaml
capabilities:
  subprocess:
    allowed_commands:
      - python
      - node
```

What is enforced:
- Only declared commands allowed
- Shell access blocked
- No command injection possible
- All commands logged

Example attack prevented:
```python
import subprocess
# Skill tries to run arbitrary command
subprocess.run("rm -rf /")
```
Result: Command not in whitelist. Rejected.

## Environment Variables

Secrets passed via environment:

```yaml
capabilities:
  system:
    env_vars:
      - API_KEY
      - SECRET_TOKEN
```

What is enforced:
- Only declared vars accessible
- No access to system env
- Values passed securely
- Not logged or stored

## Resource Limits

Prevent resource exhaustion:

- Memory: 512MB default (configurable)
- CPU: 1 core default (configurable)
- Time: 5 minute timeout (configurable)
- File size: 10GB default

Manifest can request more:

```yaml
resources:
  memory: 2GB
  cpu: 4
  timeout_seconds: 1800
```

Registry validates requests reasonable.

## Syscall Filtering

seccomp profile blocks dangerous calls:

Blocked:
- ptrace (debug other processes)
- socket + AF_PACKET (raw sockets)
- mount/unmount
- insmod/rmmod (kernel modules)
- kexec (kernel replacement)

Allowed:
- open, read, write, close
- fork, exec
- bind, listen, connect (declared networks only)
- mmap, munmap
- signal handling

## Logging and Audit Trail

Every access logged:

```
[2026-03-27 10:15:34] skill:csv-processor
  action: file_read
  path: /tmp/uploads/data.csv
  result: success

[2026-03-27 10:15:35] skill:csv-processor
  action: network_connect
  domain: api.example.com
  port: 443
  result: success

[2026-03-27 10:15:36] skill:csv-processor
  action: file_read
  path: /etc/passwd
  result: DENIED (not in manifest)
```

Logs kept for audit and debugging.

## Testing the Sandbox

Test that isolation works:

```bash
# Run security tests
skillpm validate --strict <skill-dir>

# Tests verify:
# - Code matches manifest
# - No hardcoded secrets
# - No suspicious patterns
# - Sandbox doesn't leak

# Run in sandbox locally
skillpm run <skill-name>

# Verify logs show correct isolation
cat ~/.skillpm/logs/<skill-name>.log
```

## Violations and Responses

If skill violates isolation:

1. Immediate process termination
2. Logged with full context
3. Alert to user
4. Option to report to registry
5. Skill marked for review

Process death means:
- User sees clear error
- No data corruption
- Attempts to escalate fail

## Updates and Patches

If vulnerability found in Docker/seccomp:

1. SkillPM issues advisory
2. Users update via skillpm update
3. Rerun affected skills
4. Logs checked for exploitation

## Assumptions and Limits

This sandbox is NOT:
- Waterproof against kernel exploits
- Protection against CPU timing attacks
- Defense against side-channel attacks

This sandbox IS:
- Good enough for Phase 1
- Protects against normal attacks
- Blocks category of risks
- Can be hardened further later

## Future Improvements

Phase 2+:
- AppArmor/SELinux profiles
- Network namespace isolation
- Separate process isolation
- Hardened libc wrapper
