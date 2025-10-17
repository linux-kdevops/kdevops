use anyhow::{Context, Result};
use tracing::{info, warn};
use uuid::Uuid;
use virt::connect::Connect;
use virt::domain::Domain;

use super::disk;
use super::xml;
use crate::config::AppConfig;

/// VM specification for creation
#[derive(Debug, Clone)]
pub struct VmSpec {
    pub name: String,
    pub vcpus: u32,
    pub memory_mb: u64,
    pub base_image: String,
    pub root_disk_gb: u64,
    /// Optional SSH username (falls back to config if not provided)
    pub ssh_user: Option<String>,
    /// Optional SSH public key content (falls back to config if not provided)
    pub ssh_public_key: Option<String>,
}

/// VM Manager handles VM lifecycle operations via libvirt
pub struct VmManager {
    config: AppConfig,
}

impl VmManager {
    pub fn new(config: AppConfig) -> Self {
        Self { config }
    }

    /// Connect to libvirt
    fn connect(&self) -> Result<Connect> {
        info!("Connecting to libvirt at {}", self.config.libvirt_uri);
        Connect::open(Some(&self.config.libvirt_uri)).with_context(|| {
            format!(
                "Failed to connect to libvirt at {}",
                self.config.libvirt_uri
            )
        })
    }

    /// Create a new VM
    pub fn create_vm(&self, spec: &VmSpec) -> Result<String> {
        let vm_id = Uuid::new_v4().to_string();
        info!("Creating VM {} with ID {}", spec.name, vm_id);

        // Validate base image exists
        let base_image_path = self.config.base_images_dir.join(&spec.base_image);
        if !base_image_path.exists() {
            anyhow::bail!(
                "Base image not found: {}. Available images in {}",
                spec.base_image,
                self.config.base_images_dir.display()
            );
        }

        // Create VM disk directory and path
        let disk_path = disk::get_root_disk_path(&self.config.storage_pool_path, &spec.name);
        let vm_dir = disk::get_vm_disk_dir(&self.config.storage_pool_path, &spec.name);

        info!("VM disk will be created at: {}", disk_path.display());
        info!("Using base image: {}", base_image_path.display());

        // Create COW disk from base image
        if let Err(e) = disk::create_cow_disk(&base_image_path, &disk_path, spec.root_disk_gb) {
            // Disk creation failed - no cleanup needed
            return Err(e).context("Failed to create VM disk");
        }

        // Customize COW disk with target user and SSH keys
        if let Err(e) = self.customize_vm_disk(
            &disk_path,
            spec.ssh_user.as_deref(),
            spec.ssh_public_key.as_deref(),
        ) {
            // Customization failed - clean up disk
            warn!("Failed to customize VM disk, cleaning up");
            if let Err(cleanup_err) = disk::delete_disk(&disk_path) {
                warn!("Failed to delete disk during cleanup: {}", cleanup_err);
            }
            if vm_dir.exists() {
                if let Err(cleanup_err) = std::fs::remove_dir(&vm_dir) {
                    warn!(
                        "Failed to remove VM directory during cleanup: {}",
                        cleanup_err
                    );
                }
            }
            return Err(e).context("Failed to customize VM disk");
        }

        // Determine if UEFI is required based on image name
        // Debian nocloud images and other cloud images typically require UEFI
        let requires_uefi = spec.base_image.contains("nocloud")
            || spec.base_image.contains("uefi")
            || spec.base_image.contains("cloud");

        // Generate libvirt XML
        let vm_xml = xml::generate_simple_vm_xml(
            &spec.name,
            spec.vcpus,
            spec.memory_mb,
            &disk_path,
            &self.config.network_bridge,
            requires_uefi,
        );

        // Define VM in libvirt
        let conn = self.connect()?;
        let domain = match Domain::define_xml(&conn, &vm_xml) {
            Ok(domain) => domain,
            Err(e) => {
                // Libvirt define failed - clean up disk
                warn!("Failed to define VM in libvirt, cleaning up disk");
                if let Err(cleanup_err) = disk::delete_disk(&disk_path) {
                    warn!("Failed to delete disk during cleanup: {}", cleanup_err);
                }
                if vm_dir.exists() {
                    if let Err(cleanup_err) = std::fs::remove_dir(&vm_dir) {
                        warn!(
                            "Failed to remove VM directory during cleanup: {}",
                            cleanup_err
                        );
                    }
                }
                return Err(e).context("Failed to define VM in libvirt");
            }
        };

        // Start the VM
        if let Err(e) = domain.create() {
            // VM start failed - clean up libvirt domain and disk
            warn!("Failed to start VM, cleaning up domain and disk");
            // Use undefine_flags(4) to clean up NVRAM for UEFI VMs
            if let Err(cleanup_err) = domain.undefine_flags(4) {
                warn!("Failed to undefine domain during cleanup: {}", cleanup_err);
            }
            if let Err(cleanup_err) = disk::delete_disk(&disk_path) {
                warn!("Failed to delete disk during cleanup: {}", cleanup_err);
            }
            if vm_dir.exists() {
                if let Err(cleanup_err) = std::fs::remove_dir(&vm_dir) {
                    warn!(
                        "Failed to remove VM directory during cleanup: {}",
                        cleanup_err
                    );
                }
            }
            return Err(e).context("Failed to start VM");
        }

        let uuid = domain.get_uuid_string().context("Failed to get VM UUID")?;

        info!(
            "Successfully created and started VM {} with UUID {}",
            spec.name, uuid
        );
        Ok(uuid)
    }

    /// List all VMs
    pub fn list_vms(&self) -> Result<Vec<VmInfo>> {
        let conn = self.connect()?;

        let domains = conn.list_all_domains(0).context("Failed to list domains")?;

        let mut vms = Vec::new();
        for domain in domains {
            if let Ok(info) = self.get_vm_info_from_domain(&domain) {
                vms.push(info);
            }
        }

        Ok(vms)
    }

    /// Get VM information
    pub fn get_vm(&self, id: &str) -> Result<VmInfo> {
        let conn = self.connect()?;

        // Try to find domain by UUID or name
        let domain = Domain::lookup_by_uuid_string(&conn, id)
            .or_else(|_| Domain::lookup_by_name(&conn, id))
            .context("VM not found")?;

        self.get_vm_info_from_domain(&domain)
    }

    /// Start a VM
    pub fn start_vm(&self, id: &str) -> Result<()> {
        info!("Starting VM {}", id);
        let conn = self.connect()?;
        let domain = Domain::lookup_by_uuid_string(&conn, id)
            .or_else(|_| Domain::lookup_by_name(&conn, id))
            .context("VM not found")?;

        domain.create().context("Failed to start VM")?;
        info!("VM {} started successfully", id);
        Ok(())
    }

    /// Stop a VM
    pub fn stop_vm(&self, id: &str) -> Result<()> {
        info!("Stopping VM {}", id);
        let conn = self.connect()?;
        let domain = Domain::lookup_by_uuid_string(&conn, id)
            .or_else(|_| Domain::lookup_by_name(&conn, id))
            .context("VM not found")?;

        domain.shutdown().context("Failed to stop VM")?;
        info!("VM {} stopped successfully", id);
        Ok(())
    }

    /// Destroy a VM
    pub fn destroy_vm(&self, id: &str) -> Result<()> {
        info!("Destroying VM {}", id);
        let conn = self.connect()?;
        let domain = Domain::lookup_by_uuid_string(&conn, id)
            .or_else(|_| Domain::lookup_by_name(&conn, id))
            .context("VM not found")?;

        // Get VM name for disk cleanup
        let vm_name = domain.get_name().context("Failed to get VM name")?;

        // Stop if running
        if domain.is_active().unwrap_or(false) {
            domain.destroy().context("Failed to forcefully stop VM")?;
        }

        // Undefine domain with NVRAM cleanup for UEFI VMs
        // VIR_DOMAIN_UNDEFINE_NVRAM = 4
        // This flag removes NVRAM files for UEFI VMs and is safe for non-UEFI VMs
        domain.undefine_flags(4).context("Failed to undefine VM")?;

        // Delete disk files
        let disk_path = disk::get_root_disk_path(&self.config.storage_pool_path, &vm_name);
        if let Err(e) = disk::delete_disk(&disk_path) {
            warn!("Failed to delete disk {}: {}", disk_path.display(), e);
        }

        // Try to remove VM directory
        let vm_dir = disk::get_vm_disk_dir(&self.config.storage_pool_path, &vm_name);
        if vm_dir.exists() {
            if let Err(e) = std::fs::remove_dir(&vm_dir) {
                warn!("Failed to remove VM directory {}: {}", vm_dir.display(), e);
            }
        }

        info!("VM {} destroyed successfully", id);
        Ok(())
    }

    /// Customize VM disk with target user and SSH configuration
    fn customize_vm_disk(
        &self,
        disk_path: &std::path::Path,
        ssh_user_override: Option<&str>,
        ssh_public_key_content: Option<&str>,
    ) -> Result<()> {
        use std::fs::File;
        use std::io::Write;
        use std::process::Command;

        // Determine SSH user: API parameter takes precedence, then fall back to config
        let ssh_user = if let Some(user) = ssh_user_override {
            user
        } else if let Some(user) = &self.config.ssh_user {
            user.as_str()
        } else {
            info!("No ssh_user provided via API or configured, skipping disk customization");
            return Ok(());
        };

        // Handle SSH public key: either from API content or from config file path
        let temp_key_file;
        let ssh_key_path = if let Some(key_content) = ssh_public_key_content {
            // SSH key content provided via API - write to temporary file
            info!("Using SSH public key content from API request");
            temp_key_file =
                std::env::temp_dir().join(format!("rcloud_ssh_key_{}.pub", uuid::Uuid::new_v4()));

            let mut file = File::create(&temp_key_file).with_context(|| {
                format!(
                    "Failed to create temporary SSH key file: {}",
                    temp_key_file.display()
                )
            })?;

            file.write_all(key_content.as_bytes()).with_context(|| {
                format!(
                    "Failed to write SSH key to temporary file: {}",
                    temp_key_file.display()
                )
            })?;

            file.write_all(b"\n")
                .context("Failed to write newline to temporary SSH key file")?;

            info!(
                "Wrote SSH public key to temporary file: {}",
                temp_key_file.display()
            );
            temp_key_file.as_path()
        } else if let Some(file) = &self.config.ssh_pubkey_file {
            // Fall back to configured file path
            info!("Using SSH public key from configured file: {}", file);
            std::path::Path::new(file)
        } else {
            info!("No ssh_public_key provided via API or configured, skipping disk customization");
            return Ok(());
        };

        info!(
            "Customizing VM disk to add user {} with SSH key from {}",
            ssh_user,
            ssh_key_path.display()
        );

        // Build virt-customize command to add user and SSH configuration
        let mut cmd = Command::new("virt-customize");
        cmd.arg("-a").arg(disk_path);

        // Create user with home directory
        cmd.arg("--run-command")
            .arg(format!("useradd -m -s /bin/bash {}", ssh_user));

        // Add user to sudoers with NOPASSWD
        cmd.arg("--run-command").arg(format!(
            "echo '{} ALL=(ALL) NOPASSWD:ALL' > /etc/sudoers.d/{}",
            ssh_user, ssh_user
        ));

        // Set proper permissions on sudoers file
        cmd.arg("--run-command")
            .arg(format!("chmod 0440 /etc/sudoers.d/{}", ssh_user));

        // Create .ssh directory for user
        cmd.arg("--run-command")
            .arg(format!("mkdir -p /home/{}/.ssh", ssh_user));

        // Set proper permissions on .ssh directory
        cmd.arg("--run-command")
            .arg(format!("chmod 0700 /home/{}/.ssh", ssh_user));

        // Inject SSH public key
        cmd.arg("--ssh-inject")
            .arg(format!("{}:file:{}", ssh_user, ssh_key_path.display()));

        // Set proper ownership on home directory
        cmd.arg("--run-command").arg(format!(
            "chown -R {}:{} /home/{}",
            ssh_user, ssh_user, ssh_user
        ));

        info!("Running virt-customize to configure user and SSH access");
        let output = cmd.output().context("Failed to execute virt-customize")?;

        // Clean up temporary key file if we created one
        if ssh_public_key_content.is_some() {
            if let Err(e) = std::fs::remove_file(ssh_key_path) {
                warn!(
                    "Failed to remove temporary SSH key file {}: {}",
                    ssh_key_path.display(),
                    e
                );
            } else {
                info!(
                    "Cleaned up temporary SSH key file: {}",
                    ssh_key_path.display()
                );
            }
        }

        if !output.status.success() {
            let stderr = String::from_utf8_lossy(&output.stderr);
            let stdout = String::from_utf8_lossy(&output.stdout);
            warn!("virt-customize failed: exit_code={}", output.status);
            warn!("virt-customize stdout: {}", stdout);
            warn!("virt-customize stderr: {}", stderr);
            anyhow::bail!(
                "virt-customize failed: exit_code={}, stdout={}, stderr={}",
                output.status,
                stdout,
                stderr
            );
        }

        info!(
            "Successfully customized VM disk with user {} and SSH configuration",
            ssh_user
        );
        Ok(())
    }

    /// Extract VM info from libvirt Domain
    fn get_vm_info_from_domain(&self, domain: &Domain) -> Result<VmInfo> {
        let uuid = domain
            .get_uuid_string()
            .context("Failed to get domain UUID")?;
        let name = domain.get_name().context("Failed to get domain name")?;

        let is_active = domain.is_active().unwrap_or(false);
        let state = if is_active { "running" } else { "stopped" };

        let info = domain.get_info().context("Failed to get domain info")?;

        // Query IP address from libvirt (only works if VM is running)
        let ip_address = if is_active {
            match self.get_domain_ip_address(domain) {
                Ok(ip) => Some(ip),
                Err(e) => {
                    warn!("Failed to get IP address for domain {}: {}", name, e);
                    None
                }
            }
        } else {
            None
        };

        Ok(VmInfo {
            id: uuid,
            name,
            state: state.to_string(),
            vcpus: info.nr_virt_cpu,
            memory_mb: info.memory / 1024, // Convert from KiB to MiB
            ip_address,
        })
    }

    /// Get IP address from domain using virsh domifaddr command
    fn get_domain_ip_address(&self, domain: &Domain) -> Result<String> {
        use std::process::Command;

        let vm_name = domain.get_name().context("Failed to get VM name")?;

        // Use virsh domifaddr to get IP directly from domain
        // This works without needing a defined libvirt network
        // Note: virsh requires elevated permissions to access qemu:///system
        let output = Command::new("sudo")
            .arg("virsh")
            .arg("domifaddr")
            .arg(&vm_name)
            .output()
            .context("Failed to execute virsh domifaddr")?;

        if !output.status.success() {
            let stderr = String::from_utf8_lossy(&output.stderr);
            let stdout = String::from_utf8_lossy(&output.stdout);
            anyhow::bail!(
                "Failed to query domain interfaces: stdout={}, stderr={}",
                stdout,
                stderr
            );
        }

        self.parse_domifaddr_output(&String::from_utf8_lossy(&output.stdout))
    }

    /// Parse virsh domifaddr output to extract IP address
    fn parse_domifaddr_output(&self, output: &str) -> Result<String> {
        // Format:
        // Name       MAC address          Protocol     Address
        // -------------------------------------------------------------------------------
        // vnet0      52:54:00:xx:xx:xx    ipv4         192.168.122.100/24

        for line in output.lines().skip(2) {
            // Skip header lines
            let fields: Vec<&str> = line.split_whitespace().collect();
            if fields.len() >= 4 && fields[2] == "ipv4" {
                let ip_with_prefix = fields[3];
                // Remove /24 or other CIDR suffix
                if let Some(ip) = ip_with_prefix.split('/').next() {
                    return Ok(ip.to_string());
                }
            }
        }

        anyhow::bail!("No IP address found for domain")
    }

    /// List available base images
    pub fn list_base_images(&self) -> Result<Vec<String>> {
        let mut images = Vec::new();

        let entries = std::fs::read_dir(&self.config.base_images_dir).with_context(|| {
            format!(
                "Failed to read base images directory: {}",
                self.config.base_images_dir.display()
            )
        })?;

        for entry in entries.flatten() {
            let path = entry.path();
            if path.is_file() {
                if let Some(filename) = path.file_name() {
                    images.push(filename.to_string_lossy().to_string());
                }
            }
        }

        images.sort();
        Ok(images)
    }
}

/// VM information for API responses
#[derive(Debug, Clone)]
pub struct VmInfo {
    pub id: String,
    pub name: String,
    pub state: String,
    pub vcpus: u32,
    pub memory_mb: u64,
    pub ip_address: Option<String>,
}
