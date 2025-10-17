# Terraform Provider for rcloud

Terraform provider for managing VMs through the rcloud REST API.

## Requirements

- [Terraform](https://www.terraform.io/downloads.html) >= 1.0
- [Go](https://golang.org/doc/install) >= 1.21
- Running rcloud API server

## Building the Provider

```bash
cd terraform-provider-rcloud
go mod download
go build -o terraform-provider-rcloud
```

## Installing the Provider for Local Development

### Linux/macOS

```bash
mkdir -p ~/.terraform.d/plugins/registry.terraform.io/kdevops/rcloud/0.1.0/linux_amd64
cp terraform-provider-rcloud ~/.terraform.d/plugins/registry.terraform.io/kdevops/rcloud/0.1.0/linux_amd64/
```

## Using the Provider

```hcl
terraform {
  required_providers {
    rcloud = {
      source = "kdevops/rcloud"
      version = "~> 0.1.0"
    }
  }
}

provider "rcloud" {
  endpoint = "http://localhost:8765"
}

resource "rcloud_vm" "example" {
  name         = "my-vm"
  vcpus        = 4
  memory_gb    = 8
  base_image   = "debian-13-generic-amd64.raw"
  root_disk_gb = 100
}

output "vm_id" {
  value = rcloud_vm.example.id
}
```

## Configuration

### Provider Configuration

- `endpoint` - (Optional) rcloud API endpoint URL. Defaults to `http://localhost:8765`. Can also be set via `RCLOUD_ENDPOINT` environment variable.
- `token` - (Optional) API authentication token. Can be set via `RCLOUD_TOKEN` environment variable.

### Resource: rcloud_vm

Creates and manages a virtual machine.

#### Arguments

- `name` - (Required) VM name. Changing this forces a new resource.
- `vcpus` - (Required) Number of virtual CPUs. Changing this forces a new resource.
- `memory_gb` - (Required) Memory in GB. Changing this forces a new resource.
- `base_image` - (Required) Base image filename from guestfs base images directory. Changing this forces a new resource.
- `root_disk_gb` - (Required) Root disk size in GB. Changing this forces a new resource.

#### Attributes

- `id` - VM UUID assigned by libvirt.
- `state` - Current VM state (e.g., "running", "stopped").

## Development

### Building

```bash
go build -o terraform-provider-rcloud
```

### Testing

```bash
# Run unit tests
go test ./...

# Run acceptance tests (requires running rcloud server)
TF_ACC=1 go test ./... -v
```

## License

copyleft-next-0.3.1
