# Testing rcloud

## Quick Start Testing

### 1. Setup rcloud Server

On the server that will run rcloud:

```bash
# Configure and build
make defconfig-rcloud
make

# Install and start service
make rcloud
sudo systemctl start rcloud
sudo systemctl status rcloud

# Verify API is running
curl http://localhost:8765/api/v1/health
curl http://localhost:8765/api/v1/status
```

### 2. Setup Test Environment with Base Images

Before you can create VMs, you need guestfs base images:

```bash
# On a separate kdevops instance or the same system:
make defconfig-rcloud-guest-test
make

# This will:
# - Setup guestfs infrastructure
# - Download and prepare Debian 13 base image
# - Configure libvirt and storage pools
```

The base image will be created at the configured `guestfs_base_image_dir`
(typically `/xfs1/libvirt/guestfs/base_images/`).

### 3. Verify Base Images

```bash
curl http://localhost:8765/api/v1/images
```

Should return JSON with available base images:
```json
{
  "images": [
    {"name": "debian-13-generic-amd64.raw"}
  ]
}
```

### 4. Test REST API

#### Create a VM

```bash
curl -X POST http://localhost:8765/api/v1/vms \
  -H "Content-Type: application/json" \
  -d '{
    "name": "test-vm-01",
    "vcpus": 2,
    "memory_mb": 4096,
    "base_image": "debian-13-generic-amd64.raw",
    "root_disk_gb": 50
  }'
```

Response:
```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "name": "test-vm-01",
  "state": "creating"
}
```

#### List VMs

```bash
curl http://localhost:8765/api/v1/vms
```

#### Get VM Details

```bash
curl http://localhost:8765/api/v1/vms/550e8400-e29b-41d4-a716-446655440000
```

#### Stop VM

```bash
curl -X POST http://localhost:8765/api/v1/vms/550e8400-e29b-41d4-a716-446655440000/stop
```

#### Start VM

```bash
curl -X POST http://localhost:8765/api/v1/vms/550e8400-e29b-41d4-a716-446655440000/start
```

#### Destroy VM

```bash
curl -X DELETE http://localhost:8765/api/v1/vms/550e8400-e29b-41d4-a716-446655440000
```

### 5. Test Terraform Provider

#### Install Provider

```bash
make rcloud-terraform-install
```

#### Create Test Configuration

```bash
mkdir -p ~/rcloud-test
cd ~/rcloud-test

cat > main.tf <<'EOF'
terraform {
  required_providers {
    rcloud = {
      source = "kdevops/rcloud"
    }
  }
}

provider "rcloud" {
  endpoint = "http://localhost:8765"
}

resource "rcloud_vm" "test" {
  name         = "terraform-test-01"
  vcpus        = 2
  memory_gb    = 4
  base_image   = "debian-13-generic-amd64.raw"
  root_disk_gb = 50
}

output "vm_id" {
  value = rcloud_vm.test.id
}

output "vm_state" {
  value = rcloud_vm.test.state
}
EOF
```

#### Run Terraform

```bash
terraform init
terraform plan
terraform apply

# Check the VM was created
curl http://localhost:8765/api/v1/vms

# Destroy
terraform destroy
```

## Testing Workflow

### Option 1: Server and Client on Same Host

```bash
# Terminal 1: Setup rcloud server
make defconfig-rcloud
make
make rcloud
sudo systemctl start rcloud

# Terminal 2: Setup guestfs base images
make defconfig-rcloud-guest-test
make

# Terminal 3: Test API
curl http://localhost:8765/api/v1/health
curl http://localhost:8765/api/v1/images
# ... create VMs via curl or Terraform
```

### Option 2: Separate Server and Client Machines

**On Server:**
```bash
# Setup rcloud
make defconfig-rcloud
make
make rcloud
sudo systemctl start rcloud

# If accessing from network, bind to all interfaces:
# Edit /etc/systemd/system/rcloud.service
# Add: Environment="RCLOUD_SERVER_BIND=0.0.0.0:8765"
# Then:
sudo systemctl daemon-reload
sudo systemctl restart rcloud

# Open firewall if needed:
sudo firewall-cmd --add-port=8765/tcp --permanent
sudo firewall-cmd --reload
```

**On Client:**
```bash
# Setup guestfs base images (if not already on server)
make defconfig-rcloud-guest-test
make

# Test from client
curl http://server-ip:8765/api/v1/health

# Or use SSH tunnel for security
ssh -L 8765:localhost:8765 user@server-ip
curl http://localhost:8765/api/v1/health
```

### Option 3: Using SSH Tunnel (Recommended for Security)

```bash
# On client: Create SSH tunnel
ssh -L 8765:localhost:8765 user@rcloud-server

# In another terminal on client: Access API
curl http://localhost:8765/api/v1/health

# Use Terraform with tunnel
cd ~/rcloud-test
terraform apply
```

## Monitoring

### Check rcloud Logs

```bash
sudo journalctl -u rcloud -f
```

### Check Prometheus Metrics

```bash
curl http://localhost:8765/metrics
```

Example metrics:
```
# HELP rcloud_http_requests_total Total number of HTTP requests
# TYPE rcloud_http_requests_total counter
rcloud_http_requests_total{method="POST",endpoint="/vms",status="201"} 5

# HELP rcloud_vm_count Current number of VMs
# TYPE rcloud_vm_count gauge
rcloud_vm_count 2

# HELP rcloud_vm_operations_total Total number of VM operations
# TYPE rcloud_vm_operations_total counter
rcloud_vm_operations_total{method="VM",endpoint="create",status="success"} 5
```

## Troubleshooting

### rcloud Service Won't Start

```bash
# Check logs
sudo journalctl -u rcloud -e

# Common issues:
# 1. libvirt not running
sudo systemctl status libvirtd
sudo systemctl start libvirtd

# 2. rcloud user not in libvirt group
sudo usermod -a -G libvirt rcloud

# 3. KDEVOPS_ROOT not set correctly
sudo systemctl edit rcloud
# Add/fix: Environment="KDEVOPS_ROOT=/path/to/kdevops"
```

### Cannot Connect to API

```bash
# Check if service is listening
sudo ss -tlnp | grep 8765

# Check firewall
sudo firewall-cmd --list-all

# Check rcloud is running
sudo systemctl status rcloud
```

### No Base Images Available

```bash
# Check guestfs base images directory
ls -la $(grep guestfs_base_image_dir extra_vars.yaml | cut -d: -f2 | tr -d ' "')

# Ensure guestfs setup ran
make bringup  # This creates base images
```

### VM Creation Fails

```bash
# Check libvirt connection
virsh -c qemu:///system list --all

# Check storage pool
virsh -c qemu:///system pool-list
virsh -c qemu:///system pool-info default

# Check base image exists and is readable
ls -la /xfs1/libvirt/guestfs/base_images/

# Check rcloud user can access libvirt
sudo -u rcloud virsh -c qemu:///system list --all
```

### Terraform Apply Fails

```bash
# Check provider is installed
ls -la ~/.terraform.d/plugins/registry.terraform.io/kdevops/rcloud/

# Check API is accessible
curl http://localhost:8765/api/v1/health

# Enable Terraform logging
export TF_LOG=DEBUG
terraform apply
```

## Integration Testing

### Automated Test Script

```bash
#!/bin/bash
# test-rcloud.sh

set -e

API="http://localhost:8765"

echo "1. Health check..."
curl -f $API/api/v1/health

echo "2. List images..."
IMAGES=$(curl -s $API/api/v1/images | jq -r '.images[0].name')
echo "Found image: $IMAGES"

echo "3. Create VM..."
VM_ID=$(curl -s -X POST $API/api/v1/vms \
  -H "Content-Type: application/json" \
  -d "{
    \"name\": \"test-$(date +%s)\",
    \"vcpus\": 2,
    \"memory_mb\": 2048,
    \"base_image\": \"$IMAGES\",
    \"root_disk_gb\": 20
  }" | jq -r '.id')
echo "Created VM: $VM_ID"

echo "4. Get VM details..."
curl -s $API/api/v1/vms/$VM_ID | jq

echo "5. List all VMs..."
curl -s $API/api/v1/vms | jq

echo "6. Stop VM..."
curl -s -X POST $API/api/v1/vms/$VM_ID/stop | jq

echo "7. Destroy VM..."
curl -s -X DELETE $API/api/v1/vms/$VM_ID | jq

echo "All tests passed!"
```

Run with:
```bash
chmod +x test-rcloud.sh
./test-rcloud.sh
```

## Performance Testing

### Create Multiple VMs

```bash
#!/bin/bash
for i in {1..10}; do
  curl -X POST http://localhost:8765/api/v1/vms \
    -H "Content-Type: application/json" \
    -d "{
      \"name\": \"perf-test-$i\",
      \"vcpus\": 2,
      \"memory_mb\": 2048,
      \"base_image\": \"debian-13-generic-amd64.raw\",
      \"root_disk_gb\": 20
    }" &
done
wait

# Check they were all created
curl http://localhost:8765/api/v1/vms | jq '.vms | length'
```

## Next Steps

Once basic testing is complete:

1. **Test with real workloads**: SSH into created VMs and run applications
2. **Test Terraform workflows**: Use complex Terraform configs with multiple VMs
3. **Test multi-user**: Have multiple users create VMs simultaneously
4. **Monitor metrics**: Setup Prometheus to scrape the metrics endpoint
5. **Test persistence**: Restart rcloud service and verify VMs are still manageable
