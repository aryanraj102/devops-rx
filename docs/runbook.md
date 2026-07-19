# OpsSight Runbook — Known Issues & Approved Fixes

Reference document for the remediation agent. Each entry maps a detected issue pattern to the team-approved resolution.

---

## Memory (OOM)

**Pattern:** `Out of memory: Kill process` / `OOMKilled`

**Root cause:** Process exceeded available RAM; kernel invoked OOM killer.

**Fix:**
1. Identify peak heap: `jmap -heap <pid>` (Java) or review cgroup stats
2. Increase pod/container memory limit by 50% as immediate relief
3. Set JVM heap: `-Xmx2g -Xms512m` to bound Java heap
4. Add horizontal pod autoscaling if load-driven

---

## Disk Full

**Pattern:** `No space left on device` / `EXT4-fs error`

**Fix:**
```bash
df -h                        # locate full filesystem
du -sh /var/* | sort -rh     # find largest directories
journalctl --vacuum-size=500M # trim systemd journal
find /var/log -name "*.gz" -mtime +7 -delete
docker system prune -f       # clear unused Docker layers
```

---

## SSH Brute Force

**Pattern:** Repeated `Failed password for root` from single IP within 60s

**Fix:**
```bash
fail2ban-client status sshd   # check if fail2ban caught it
iptables -A INPUT -s <ip> -j DROP
# Long term: disable password auth, use keys only
sed -i 's/PasswordAuthentication yes/PasswordAuthentication no/' /etc/ssh/sshd_config
systemctl restart sshd
```

---

## Service Crash / Restart Loop

**Pattern:** `systemd: Failed with result 'signal'` + restart counter incrementing

**Fix:**
```bash
systemctl status <service>
journalctl -u <service> -n 100
systemctl restart <service>
# If persists: check ulimits, coredumps, and service config
```

---

## ImagePullBackOff (Kubernetes)

**Pattern:** `ImagePullBackOff` / `Unauthorized`

**Fix:**
```bash
kubectl describe pod <pod> -n <ns>    # get exact error
kubectl create secret docker-registry regcred \
  --docker-server=myrepo \
  --docker-username=<user> \
  --docker-password=<token>
# Patch deployment to use imagePullSecrets: [name: regcred]
```

---

## Node Memory Pressure (Kubernetes)

**Pattern:** `MemoryPressure=True` on node

**Fix:**
1. Identify memory consumers: `kubectl top pods -A --sort-by=memory`
2. Evict or reschedule low-priority pods
3. Add node to cluster or increase node VM size
4. Set resource requests/limits on all workloads
