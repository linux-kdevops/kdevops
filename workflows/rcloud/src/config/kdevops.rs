use anyhow::{Context, Result};
use serde::{Deserialize, Serialize};
use std::collections::HashMap;
use std::fs;
use std::path::Path;

/// kdevops configuration parsed from extra_vars.yaml
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct KdevopsConfig {
    pub libvirt_uri: String,
    pub storage_pool_path: String,
    pub base_images_dir: String,
    pub network_bridge: Option<String>,
    pub rcloud_server_bind: Option<String>,
    pub rcloud_workers: Option<usize>,
    pub ssh_user: Option<String>,
    pub ssh_pubkey_file: Option<String>,

    #[serde(flatten)]
    pub extra: HashMap<String, serde_yaml::Value>,
}

impl KdevopsConfig {
    /// Load configuration from kdevops directory
    pub fn load(kdevops_root: &Path) -> Result<Self> {
        let extra_vars_path = kdevops_root.join("extra_vars.yaml");

        let contents = fs::read_to_string(&extra_vars_path)
            .with_context(|| format!("Failed to read {}", extra_vars_path.display()))?;

        let yaml: serde_yaml::Value =
            serde_yaml::from_str(&contents).context("Failed to parse extra_vars.yaml")?;

        // Try environment variables first, then fall back to extra_vars.yaml
        let storage_pool_path = std::env::var("RCLOUD_STORAGE_POOL_PATH")
            .ok()
            .or_else(|| Self::get_string(&yaml, "kdevops_storage_pool_path"))
            .or_else(|| Self::get_string(&yaml, "libvirt_storage_pool_path"))
            .context("Missing storage pool path. Set RCLOUD_STORAGE_POOL_PATH env var or kdevops_storage_pool_path in extra_vars.yaml")?;

        let base_images_dir = std::env::var("RCLOUD_BASE_IMAGES_DIR")
            .ok()
            .or_else(|| Self::get_string(&yaml, "guestfs_base_image_dir"))
            .context("Missing base images directory. Set RCLOUD_BASE_IMAGES_DIR env var or guestfs_base_image_dir in extra_vars.yaml")?;

        // Extract configuration values
        let config = Self {
            libvirt_uri: std::env::var("RCLOUD_LIBVIRT_URI")
                .ok()
                .or_else(|| Self::get_string(&yaml, "libvirt_uri"))
                .unwrap_or_else(|| "qemu:///system".to_string()),

            storage_pool_path,
            base_images_dir,

            network_bridge: std::env::var("RCLOUD_NETWORK_BRIDGE")
                .ok()
                .or_else(|| Self::get_string(&yaml, "libvirt_bridge_name"))
                .or_else(|| Some("virbr0".to_string())),

            rcloud_server_bind: std::env::var("RCLOUD_SERVER_BIND")
                .ok()
                .or_else(|| Self::get_string(&yaml, "rcloud_server_bind")),

            rcloud_workers: std::env::var("RCLOUD_WORKERS")
                .ok()
                .and_then(|s| s.parse().ok())
                .or_else(|| Self::get_usize(&yaml, "rcloud_workers")),

            ssh_user: Self::get_string(&yaml, "kdevops_terraform_ssh_config_user"),
            ssh_pubkey_file: Self::get_string(&yaml, "kdevops_terraform_ssh_config_pubkey_file"),

            extra: serde_yaml::from_value(yaml).context("Failed to parse extra configuration")?,
        };

        Ok(config)
    }

    /// Helper to extract string value from YAML
    fn get_string(yaml: &serde_yaml::Value, key: &str) -> Option<String> {
        yaml.get(key)
            .and_then(|v| v.as_str())
            .map(|s| s.to_string())
    }

    /// Helper to extract usize value from YAML
    fn get_usize(yaml: &serde_yaml::Value, key: &str) -> Option<usize> {
        yaml.get(key).and_then(|v| v.as_u64()).map(|n| n as usize)
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use std::io::Write;
    use tempfile::TempDir;

    #[test]
    fn test_load_kdevops_config() {
        let temp_dir = TempDir::new().unwrap();
        let extra_vars_path = temp_dir.path().join("extra_vars.yaml");

        let yaml_content = r#"
libvirt_uri: "qemu:///system"
kdevops_storage_pool_path: "/xfs1/libvirt/kdevops"
guestfs_base_image_dir: "/xfs1/libvirt/guestfs/base_images"
libvirt_bridge_name: "virbr0"
"#;

        let mut file = fs::File::create(&extra_vars_path).unwrap();
        file.write_all(yaml_content.as_bytes()).unwrap();
        drop(file);

        let config = KdevopsConfig::load(temp_dir.path()).unwrap();

        assert_eq!(config.libvirt_uri, "qemu:///system");
        assert_eq!(config.storage_pool_path, "/xfs1/libvirt/kdevops");
        assert_eq!(config.base_images_dir, "/xfs1/libvirt/guestfs/base_images");
        assert_eq!(config.network_bridge, Some("virbr0".to_string()));
    }
}
