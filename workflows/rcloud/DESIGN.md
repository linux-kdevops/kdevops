# rcloud Design Document

## Vision

rcloud is a **private cloud infrastructure** built in Rust, designed to turn bare metal servers into a cloud platform comparable to Ubicloud/AWS/GCE. It provides a REST API and Terraform provider for declarative VM management.

## Goals

1. **Ubicloud Alternative**: Provide a self-hosted cloud platform for Linux kernel development and testing
2. **Terraform Integration**: First-class Terraform provider for Infrastructure as Code
3. **Multi-Host Scaling**: Start single-host, scale to multiple physical servers
4. **Leverage kdevops**: Integrate with existing guestfs infrastructure and workflows
5. **Developer-Friendly**: Simple API, clear documentation, easy to extend

## Architecture

### Single-Host MVP (Phase 1)

```
┌─────────────────────────────────────────────┐
│ Clients                                      │
│                                              │
│  Terraform          curl/httpie       CLI   │
│  (terraform apply)  (REST API)        (dev) │
└──────────────┬──────────────┬───────────────┘
               │              │
               ▼              ▼
┌──────────────────────────────────────────────┐
│ rcloud API Server (Rust/actix-web)           │
│                                               │
│  ┌─────────────┐  ┌─────────────┐           │
│  │ Terraform   │  │ REST API    │           │
│  │ Endpoints   │  │ /api/v1/... │           │
│  └─────────────┘  └─────────────┘           │
│                                               │
│  ┌─────────────────────────────────┐         │
│  │ VM Manager                       │         │
│  │ - Create/destroy VMs             │         │
│  │ - Start/stop operations          │         │
│  │ - State tracking                 │         │
│  └─────────────────────────────────┘         │
│                                               │
│  ┌─────────────────────────────────┐         │
│  │ guestfs Integration              │         │
│  │ - Use kdevops base images        │         │
│  │ - Reuse XML templates            │         │
│  │ - Leverage storage pools         │         │
│  └─────────────────────────────────┘         │
└───────────────────┬───────────────────────────┘
                    │
                    ▼
┌────────────────────────────────────────────────┐
│ Host Infrastructure (kdevops-managed)          │
│                                                 │
│  ┌─────────────┐  ┌──────────────┐            │
│  │ libvirt     │  │ guestfs      │            │
│  │ (VMs)       │  │ (base images)│            │
│  └─────────────┘  └──────────────┘            │
│                                                 │
│  Storage: /xfs1/libvirt/                       │
│    - base_images/ (shared, read-only)          │
│    - vms/ (per-VM storage)                     │
└────────────────────────────────────────────────┘
```

## API Design

### REST API Endpoints

#### VM Management
```
POST   /api/v1/vms              Create VM
GET    /api/v1/vms              List all VMs
GET    /api/v1/vms/:id          Get VM details
DELETE /api/v1/vms/:id          Destroy VM
POST   /api/v1/vms/:id/start    Start VM
POST   /api/v1/vms/:id/stop     Stop VM
GET    /api/v1/vms/:id/console  Get console access info
```

#### Base Images
```
GET    /api/v1/images           List available base images
GET    /api/v1/images/:id       Get image details
```

#### System Info
```
GET    /api/v1/status           System status & capacity
GET    /api/v1/health           Health check
```

### VM Resource Schema

```json
{
  "id": "vm-abc123",
  "name": "web-server-01",
  "state": "running",
  "vcpus": 4,
  "memory_mb": 8192,
  "disks": [
    {
      "type": "root",
      "size_gb": 100,
      "driver": "virtio"
    },
    {
      "type": "data",
      "size_gb": 500,
      "driver": "virtio"
    }
  ],
  "network": {
    "bridge": "virbr0",
    "ip_address": "192.168.122.45",
    "mac_address": "52:54:00:12:34:56"
  },
  "image": "debian13",
  "created_at": "2025-10-10T12:00:00Z",
  "updated_at": "2025-10-10T12:05:00Z"
}
```

## Terraform Provider

### Provider Configuration

```hcl
terraform {
  required_providers {
    rcloud = {
      source  = "kdevops/rcloud"
      version = "~> 0.1.0"
    }
  }
}

provider "rcloud" {
  endpoint = "http://localhost:8765"
  token    = var.rcloud_token  # Optional for MVP
}
```

### Resource: rcloud_vm

```hcl
resource "rcloud_vm" "web_server" {
  name      = "web-01"
  vcpus     = 4
  memory_gb = 8
  image     = "debian13"

  root_disk_gb = 100

  extra_disks = [
    {
      size_gb = 500
      type    = "virtio"
    }
  ]

  network = {
    bridge = "virbr0"
  }
}

output "vm_ip" {
  value = rcloud_vm.web_server.ip_address
}
```

## Integration with kdevops

### Use Existing Infrastructure

1. **Base Images**: Read from `guestfs_base_image_dir`
   - `/xfs1/libvirt/guestfs/base_images/debian-13-generic-amd64.raw`
   - `/xfs1/libvirt/guestfs/base_images/ubuntu-24.04.raw`

2. **Storage Pools**: Use `kdevops_storage_pool_path`
   - `/xfs1/libvirt/kdevops/`

3. **XML Templates**: Reuse `playbooks/roles/gen_nodes/templates/guestfs_q35.j2.xml`
   - Parse and render with Rust templating (tera/handlebars)

4. **Configuration**: Read from `extra_vars.yaml`
   ```rust
   let config = Config::from_kdevops("/path/to/kdevops")?;
   let base_images = config.guestfs_base_image_dir;
   let storage_pool = config.kdevops_storage_pool_path;
   ```

### Deployment Model

```bash
# Admin sets up kdevops infrastructure
make defconfig-rcloud
make bringup  # Sets up libvirt, guestfs, base images

# Deploy rcloud service
make rcloud-deploy  # Starts API server as systemd service

# Users consume via Terraform
terraform apply
```

## Implementation Plan

### Phase 1: Core REST API (Week 1-2)

**Milestone 1.1: Basic API Server**
- [ ] Set up actix-web server
- [ ] Health check endpoint (`/api/v1/health`)
- [ ] Status endpoint (`/api/v1/status`)
- [ ] Read kdevops config from `extra_vars.yaml`

**Milestone 1.2: VM Lifecycle**
- [ ] Create VM endpoint (`POST /api/v1/vms`)
  - Generate libvirt XML from template
  - Create disk images
  - Define and start VM
- [ ] List VMs endpoint (`GET /api/v1/vms`)
- [ ] Get VM details endpoint (`GET /api/v1/vms/:id`)
- [ ] Start/stop endpoints
- [ ] Destroy VM endpoint

**Milestone 1.3: guestfs Integration**
- [ ] Read base images from guestfs
- [ ] Use guestfs XML templates (Tera templating)
- [ ] COW (copy-on-write) from base images
- [ ] Proper storage pool paths

### Phase 2: Terraform Provider (Week 3-4)

**Milestone 2.1: Provider Skeleton**
- [ ] Terraform plugin framework setup
- [ ] Provider configuration schema
- [ ] Connection to rcloud API

**Milestone 2.2: VM Resource**
- [ ] `rcloud_vm` resource CRUD
- [ ] State management
- [ ] Import existing VMs
- [ ] Computed attributes (IP, state)

**Milestone 2.3: Integration & Testing**
- [ ] Example Terraform configs
- [ ] Integration tests
- [ ] Documentation

### Phase 3: Production Readiness (Week 5-6)

**Milestone 3.1: Robustness**
- [ ] Error handling & recovery
- [ ] Logging (tracing/slog)
- [ ] Metrics (Prometheus)
- [ ] Graceful shutdown

**Milestone 3.2: Deployment**
- [ ] Systemd service file
- [ ] Ansible playbook for deployment
- [ ] Configuration management
- [ ] Monitoring setup

**Milestone 3.3: Documentation**
- [ ] API documentation (OpenAPI/Swagger)
- [ ] Terraform provider docs
- [ ] Deployment guide
- [ ] Architecture diagrams

## Technology Stack

### Core Components

- **Language**: Rust (stable)
- **Web Framework**: actix-web 4.x
- **Libvirt**: virt-rs crate
- **Config**: serde-yaml, config-rs
- **Templating**: tera (Jinja2-like for Rust)
- **Database**: None for MVP (in-memory state, libvirt is source of truth)
- **Logging**: tracing + tracing-subscriber
- **Metrics**: prometheus-client

### Terraform Provider

- **Framework**: terraform-plugin-framework (Go)
- **API Client**: reqwest (Rust) or generated OpenAPI client

### Testing

- **Unit Tests**: Rust built-in testing
- **Integration Tests**: testcontainers-rs (for libvirt?)
- **E2E Tests**: Terraform configs + real libvirt

## File Structure

```
workflows/rcloud/
├── DESIGN.md                    # This file
├── README.md                    # User documentation
├── Cargo.toml                   # Rust dependencies
├── src/
│   ├── main.rs                  # Entry point (API server)
│   ├── api/
│   │   ├── mod.rs              # API module
│   │   ├── server.rs           # actix-web setup
│   │   ├── routes.rs           # Route definitions
│   │   ├── handlers/
│   │   │   ├── vms.rs          # VM endpoints
│   │   │   ├── images.rs       # Image endpoints
│   │   │   └── health.rs       # Health/status endpoints
│   │   └── models.rs           # API request/response types
│   ├── vm/
│   │   ├── mod.rs              # VM module
│   │   ├── manager.rs          # VM lifecycle operations
│   │   ├── libvirt.rs          # libvirt wrapper
│   │   └── xml.rs              # XML generation (templates)
│   ├── config/
│   │   ├── mod.rs              # Config module
│   │   ├── kdevops.rs          # Parse kdevops config
│   │   └── rcloud.rs           # rcloud-specific config
│   └── lib.rs                  # Library exports
├── templates/
│   └── vm-q35.xml.tera         # libvirt XML template (from guestfs)
├── config/
│   └── rcloud.yaml             # Default configuration
└── tests/
    ├── api_tests.rs            # API integration tests
    └── vm_tests.rs             # VM operation tests

terraform-provider-rcloud/       # Separate repo/directory
├── main.go                      # Provider entry point
├── provider/
│   ├── provider.go             # Provider configuration
│   ├── resource_vm.go          # rcloud_vm resource
│   └── data_source_vm.go       # rcloud_vm data source
└── examples/
    └── main.tf                 # Example configuration
```

## Configuration

### rcloud.yaml

```yaml
# Server configuration
server:
  bind_address: "0.0.0.0:8765"
  workers: 4

# kdevops integration
kdevops:
  config_path: "/path/to/kdevops"
  extra_vars_file: "extra_vars.yaml"

# libvirt
libvirt:
  uri: "qemu:///system"
  storage_pool_path: "/xfs1/libvirt/kdevops"

# VM defaults
vm_defaults:
  network_bridge: "virbr0"
  disk_format: "raw"
  disk_driver: "virtio"

# Logging
logging:
  level: "info"
  format: "json"  # or "text"
```

## Security Considerations (Future)

For production multi-user deployment:

1. **Authentication**: API tokens, OAuth2
2. **Authorization**: Role-based access control (RBAC)
3. **Network**: TLS/HTTPS for API
4. **Resource Isolation**: User namespacing
5. **Quotas**: Per-user resource limits

## Monitoring & Observability

1. **Metrics**: Prometheus-compatible `/metrics` endpoint
   - VM count, CPU usage, memory usage
   - API request rates, latencies
   - Error rates

2. **Logging**: Structured JSON logging
   - Request/response logs
   - VM operation logs
   - Error traces

3. **Tracing**: OpenTelemetry (future)

## Open Questions

1. **State Management**: Where to store VM metadata?
   - Option A: In-memory (ephemeral, simple)
   - Option B: sqlite (persistent, queryable)
   - Option C: libvirt is source of truth (read from libvirt API)
   - **Decision**: Start with Option C (libvirt as SSOT), add DB later if needed

2. **Image Management**: How to handle base images?
   - Option A: Read-only from guestfs location
   - Option B: Import/copy to rcloud-managed location
   - **Decision**: Option A for MVP

3. **Networking**: Static IPs vs DHCP?
   - MVP: Use libvirt's default network (DHCP)
   - Future: Support static IPs, custom networks

4. **Multi-tenancy**: User isolation?
   - MVP: Single-user (no auth)
   - Phase 2: API tokens
   - Phase 3: Full multi-tenancy

## Success Criteria

### MVP (Phase 1 + 2 Complete)

- [ ] REST API server running as systemd service
- [ ] Can create/destroy VMs via API
- [ ] Terraform provider can provision VMs
- [ ] Uses kdevops guestfs base images
- [ ] VMs boot and are accessible via SSH
- [ ] Basic monitoring (Prometheus metrics)

### Production Ready (Phase 3 Complete)

- [ ] Comprehensive error handling
- [ ] Full API documentation
- [ ] Deployment automation (Ansible)
- [ ] Integration tests passing
- [ ] Performance tested (50+ concurrent VMs)

## References

- Ubicloud: https://www.ubicloud.com/
- Terraform Provider Framework: https://developer.hashicorp.com/terraform/plugin/framework
- libvirt Rust bindings: https://crates.io/crates/virt
- actix-web: https://actix.rs/
