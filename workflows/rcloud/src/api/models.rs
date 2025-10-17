use serde::{Deserialize, Serialize};

/// Request to create a new VM
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct CreateVmRequest {
    pub name: String,
    pub vcpus: u32,
    pub memory_mb: u64,
    pub base_image: String,
    pub root_disk_gb: u64,
    /// Optional SSH username to create (defaults to config if not provided)
    #[serde(skip_serializing_if = "Option::is_none")]
    pub ssh_user: Option<String>,
    /// Optional SSH public key content to inject (defaults to config if not provided)
    #[serde(skip_serializing_if = "Option::is_none")]
    pub ssh_public_key: Option<String>,
}

/// Response after creating a VM
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct CreateVmResponse {
    pub id: String,
    pub name: String,
    pub state: String,
}

/// VM details response
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct VmResponse {
    pub id: String,
    pub name: String,
    pub state: String,
    pub vcpus: u32,
    pub memory_mb: u64,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub ip_address: Option<String>,
}

/// List of VMs response
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ListVmsResponse {
    pub vms: Vec<VmResponse>,
}

/// Base image information
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ImageInfo {
    pub name: String,
}

/// List of base images
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ListImagesResponse {
    pub images: Vec<ImageInfo>,
}
