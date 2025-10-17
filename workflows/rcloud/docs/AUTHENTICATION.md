# rcloud Authentication (Future TODO)

## Current State

The MVP implementation has **no authentication** - any client with network access to the rcloud API server can create, modify, and destroy VMs. This is acceptable for:

- Single-user private development environments
- Environments where network access to the rcloud server is already restricted (firewall, VPN, SSH tunnel)
- Trusted multi-user environments where users already have SSH access to the host

## Future Authentication Options

### Option 1: Simple API Token File (Recommended)

File-based token authentication similar to SSH authorized_keys pattern.

#### Design

**Token Storage**: `~/.rcloud/tokens` or `/etc/rcloud/tokens`

Format:
```
# username:token_hex:created_timestamp:description
mcgrof:a1b2c3d4e5f6789...:1696896000:laptop
jenkins:9f8e7d6c5b4a321...:1696896100:ci-system
```

**Client Authentication**:
```bash
# Store token in client config
echo "a1b2c3d4e5f6789..." > ~/.rcloud/token

# Or use environment variable
export RCLOUD_TOKEN=a1b2c3d4e5f6789...

# Use with curl
curl -H "Authorization: Bearer a1b2c3d4e5f6789..." \
  http://localhost:8765/api/v1/vms

# Terraform provider already supports this
provider "rcloud" {
  endpoint = "http://localhost:8765"
  token    = var.rcloud_token
}
```

**Token Management CLI**:
```bash
# Generate new token
rcloud token create --user mcgrof --description "my laptop"
# Output: Token: a1b2c3d4e5f6789abcdef... (save this, it won't be shown again)

# List active tokens
rcloud token list
# mcgrof    a1b2...  2024-10-10  laptop
# jenkins   9f8e...  2024-10-10  ci-system

# Revoke token
rcloud token revoke a1b2c3d4e5f6789...
```

**Implementation**:
- Simple actix-web middleware to check `Authorization: Bearer` header
- Load tokens from file at startup (or watch for changes)
- Log authentication attempts for audit trail
- Token generation: `openssl rand -hex 32` or similar

**Advantages**:
- Very simple to implement and understand
- No external dependencies (no database, no auth server)
- Easy to audit (just a text file)
- Works well with CI/CD (inject token as environment variable)
- Already designed into Terraform provider
- Familiar pattern for sysadmins (like SSH keys)

**Trade-offs**:
- Tokens are long-lived (manual revocation required)
- No automatic expiration (could add timestamp checks)
- Token transmitted in HTTP headers (use HTTPS in production)

### Option 2: Mutual TLS (mTLS) with Client Certificates

Certificate-based authentication similar to kubectl/Kubernetes.

#### Design

**Certificate Authority**:
- rcloud acts as CA or uses existing CA
- Generate client certificates signed by CA
- Client presents certificate with every HTTPS request

**Setup**:
```bash
# Server: Generate CA and server cert
rcloud cert init-ca
rcloud cert generate-server

# Admin: Generate client certificate for user
rcloud cert generate-client --user mcgrof --days 365

# Client: Use certificate
curl --cert ~/.rcloud/client.crt \
     --key ~/.rcloud/client.key \
     --cacert ~/.rcloud/ca.crt \
     https://localhost:8443/api/v1/vms
```

**Implementation**:
- Configure actix-web for HTTPS with client certificate validation
- Extract username from certificate CN or Subject Alternative Name
- Map certificate to permissions/roles

**Advantages**:
- Very secure (mutual authentication)
- Standard TLS infrastructure
- Automatic certificate expiration
- No bearer tokens to leak
- Works well with existing PKI infrastructure

**Trade-offs**:
- More complex setup (certificate management)
- Requires HTTPS (TLS overhead)
- Certificate distribution and renewal
- May be overkill for simple use cases

## Recommendation

For the **first authentication implementation**, use **Option 1 (Simple API Token File)**:

1. Simpler to implement and use
2. Matches kdevops's file-based configuration philosophy
3. Adequate security for private cloud environments
4. Easy to evolve to more sophisticated schemes later
5. Terraform provider already has token support built-in

**Option 2 (mTLS)** is better suited for:
- Multi-tenant production environments
- Environments requiring strong cryptographic authentication
- Integration with existing PKI infrastructure
- Compliance requirements (audit trails, certificate rotation)

## Implementation Priority

**Phase 3 - Production Readiness** (from DESIGN.md):
- [ ] Implement Option 1: Simple API token authentication
  - [ ] Token file format and storage
  - [ ] actix-web middleware for token validation
  - [ ] Token management CLI commands
  - [ ] Logging and audit trail
  - [ ] Documentation and examples

**Future Enhancement**:
- [ ] Add token expiration timestamps
- [ ] Support HTTPS with TLS
- [ ] Consider mTLS for high-security deployments

## MVP Deployment Model

For now, rcloud security relies on **network-level access control**:

1. **Localhost only**: Bind to `127.0.0.1:8765` (default)
2. **SSH tunneling**: Users connect via `ssh -L 8080:localhost:8765 server`
3. **Firewall rules**: Block port 8080 from external networks
4. **VPN access**: Require VPN to access rcloud network

This matches how many development tools work (Jupyter, development databases, etc.) and is adequate for single-server, trusted-user environments.
