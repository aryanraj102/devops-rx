# Severity Policy

Defines what each severity level means for this incident analysis suite.

## Critical
Immediate impact on production availability or data integrity. Requires paging on-call.

- OOM kill of production process
- Disk full on production filesystem
- Database crash or data corruption
- Complete service outage (all requests failing)
- Security breach (unauthorized access confirmed)

## High
Significant degradation; not yet a full outage but deteriorating fast.

- Repeated service restarts (crash loop)
- SSH brute force in progress
- Pod OOMKilled with restart count > 1
- Error rate > 10% on key endpoints
- Node memory/disk pressure

## Medium
Noticeable but not immediately production-breaking.

- CPU load average sustained > 10x core count
- Failed cron jobs (non-critical)
- Liveness probe failures (pod recovering)
- Slow requests (p99 > 5s)
- ImagePullBackOff (pod not serving traffic yet)

## Low
Informational; should be tracked but no immediate action required.

- NTP clock drift
- Swap usage > 70%
- Log rotation failures on non-critical services
- 404 spikes from known scanners
- Single failed login attempt
