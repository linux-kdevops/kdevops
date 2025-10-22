pub mod kdevops;

use anyhow::{Context, Result};
use serde::{Deserialize, Serialize};
use std::path::PathBuf;

/// Main application configuration
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct AppConfig {
    /// Server configuration
    pub server: ServerConfig,

    /// kdevops root directory
    pub kdevops_root: PathBuf,

    /// Libvirt connection URI
    pub libvirt_uri: String,

    /// Storage pool path for VMs
    pub storage_pool_path: PathBuf,

    /// Base images directory (from guestfs)
    pub base_images_dir: PathBuf,

    /// Network bridge name
    pub network_bridge: String,

    /// SSH user for VM access
    pub ssh_user: Option<String>,

    /// SSH public key file for VM access
    pub ssh_pubkey_file: Option<String>,

    /// VM defaults
    pub vm_defaults: VmDefaults,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ServerConfig {
    pub bind_address: String,
    pub workers: usize,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct VmDefaults {
    pub disk_format: String,
    pub disk_driver: String,
}

impl Default for ServerConfig {
    fn default() -> Self {
        Self {
            bind_address: "127.0.0.1:8765".to_string(),
            workers: 4,
        }
    }
}

impl Default for VmDefaults {
    fn default() -> Self {
        Self {
            disk_format: "raw".to_string(),
            disk_driver: "virtio".to_string(),
        }
    }
}

impl AppConfig {
    /// Load configuration from environment and kdevops
    pub fn load() -> Result<Self> {
        // Determine kdevops root
        let kdevops_root = std::env::var("KDEVOPS_ROOT")
            .map(PathBuf::from)
            .or_else(|_| std::env::current_dir())
            .context("Failed to determine kdevops root directory")?;

        // Load kdevops configuration
        let kdevops_config = kdevops::KdevopsConfig::load(&kdevops_root)
            .context("Failed to load kdevops configuration")?;

        // Build server config from kdevops config or defaults
        let server = ServerConfig {
            bind_address: kdevops_config
                .rcloud_server_bind
                .clone()
                .unwrap_or_else(|| ServerConfig::default().bind_address),
            workers: kdevops_config
                .rcloud_workers
                .unwrap_or_else(|| ServerConfig::default().workers),
        };

        // Build application config from kdevops config
        let config = Self {
            server,
            kdevops_root: kdevops_root.clone(),
            libvirt_uri: kdevops_config.libvirt_uri.clone(),
            storage_pool_path: PathBuf::from(&kdevops_config.storage_pool_path),
            base_images_dir: PathBuf::from(&kdevops_config.base_images_dir),
            network_bridge: kdevops_config
                .network_bridge
                .clone()
                .unwrap_or_else(|| "default".to_string()),
            ssh_user: kdevops_config.ssh_user.clone(),
            ssh_pubkey_file: kdevops_config.ssh_pubkey_file.clone(),
            vm_defaults: VmDefaults::default(),
        };

        Ok(config)
    }

    /// Get path to libvirt XML template
    #[allow(dead_code)]
    pub fn xml_template_path(&self) -> PathBuf {
        self.kdevops_root
            .join("playbooks/roles/gen_nodes/templates/guestfs_q35.j2.xml")
    }
}
