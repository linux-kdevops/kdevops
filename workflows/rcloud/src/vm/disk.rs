use anyhow::{Context, Result};
use std::path::{Path, PathBuf};
use std::process::Command;
use tracing::info;

/// Create a COW (copy-on-write) disk from a base image
pub fn create_cow_disk(base_image: &Path, target_disk: &Path, size_gb: u64) -> Result<()> {
    info!(
        "Creating COW disk: {} (size: {}G, base: {})",
        target_disk.display(),
        size_gb,
        base_image.display()
    );

    // Ensure parent directory exists
    if let Some(parent) = target_disk.parent() {
        std::fs::create_dir_all(parent)
            .with_context(|| format!("Failed to create directory {}", parent.display()))?;
    }

    // Use qemu-img to create COW disk
    // qemu-img create -f qcow2 -b base_image.raw -F raw target.qcow2 size
    let size_str = format!("{}G", size_gb);

    let output = Command::new("qemu-img")
        .arg("create")
        .arg("-f")
        .arg("qcow2")
        .arg("-b")
        .arg(base_image)
        .arg("-F")
        .arg("raw")
        .arg(target_disk)
        .arg(&size_str)
        .output()
        .context("Failed to execute qemu-img")?;

    if !output.status.success() {
        let stderr = String::from_utf8_lossy(&output.stderr);
        anyhow::bail!("qemu-img failed: {}", stderr);
    }

    info!("Successfully created COW disk at {}", target_disk.display());
    Ok(())
}

/// Delete a disk file
pub fn delete_disk(disk_path: &Path) -> Result<()> {
    if disk_path.exists() {
        info!("Deleting disk: {}", disk_path.display());
        std::fs::remove_file(disk_path)
            .with_context(|| format!("Failed to delete disk {}", disk_path.display()))?;
        info!("Successfully deleted disk");
    }
    Ok(())
}

/// Get the VM disk directory path
pub fn get_vm_disk_dir(storage_pool: &Path, vm_name: &str) -> PathBuf {
    storage_pool.join(vm_name)
}

/// Get the root disk path for a VM
pub fn get_root_disk_path(storage_pool: &Path, vm_name: &str) -> PathBuf {
    get_vm_disk_dir(storage_pool, vm_name).join("root.qcow2")
}
