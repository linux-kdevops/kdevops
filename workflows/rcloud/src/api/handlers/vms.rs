use actix_web::{web, HttpResponse, Result};
use tracing::{error, info};

use crate::api::models::{CreateVmRequest, CreateVmResponse, ListVmsResponse, VmResponse};
use crate::config::AppConfig;
use crate::vm::{VmManager, VmSpec};

/// Create a new VM
pub async fn create_vm(
    config: web::Data<AppConfig>,
    req: web::Json<CreateVmRequest>,
) -> Result<HttpResponse> {
    info!("Received request to create VM: {}", req.name);

    let vm_spec = VmSpec {
        name: req.name.clone(),
        vcpus: req.vcpus,
        memory_mb: req.memory_mb,
        base_image: req.base_image.clone(),
        root_disk_gb: req.root_disk_gb,
        ssh_user: req.ssh_user.clone(),
        ssh_public_key: req.ssh_public_key.clone(),
    };

    let manager = VmManager::new(config.as_ref().clone());

    match manager.create_vm(&vm_spec) {
        Ok(vm_id) => {
            info!("Successfully created VM {} with ID {}", req.name, vm_id);
            let response = CreateVmResponse {
                id: vm_id,
                name: req.name.clone(),
                state: "creating".to_string(),
            };
            Ok(HttpResponse::Created().json(response))
        }
        Err(e) => {
            error!("Failed to create VM {}: {}", req.name, e);
            Ok(HttpResponse::InternalServerError().json(serde_json::json!({
                "error": format!("Failed to create VM: {}", e)
            })))
        }
    }
}

/// List all VMs
pub async fn list_vms(config: web::Data<AppConfig>) -> Result<HttpResponse> {
    info!("Received request to list VMs");

    let manager = VmManager::new(config.as_ref().clone());

    match manager.list_vms() {
        Ok(vms) => {
            let response = ListVmsResponse {
                vms: vms
                    .iter()
                    .map(|vm| VmResponse {
                        id: vm.id.clone(),
                        name: vm.name.clone(),
                        state: vm.state.clone(),
                        vcpus: vm.vcpus,
                        memory_mb: vm.memory_mb,
                        ip_address: vm.ip_address.clone(),
                    })
                    .collect(),
            };
            Ok(HttpResponse::Ok().json(response))
        }
        Err(e) => {
            error!("Failed to list VMs: {}", e);
            Ok(HttpResponse::InternalServerError().json(serde_json::json!({
                "error": format!("Failed to list VMs: {}", e)
            })))
        }
    }
}

/// Get VM details
pub async fn get_vm(
    config: web::Data<AppConfig>,
    vm_id: web::Path<String>,
) -> Result<HttpResponse> {
    info!("Received request to get VM: {}", vm_id);

    let manager = VmManager::new(config.as_ref().clone());

    match manager.get_vm(&vm_id) {
        Ok(vm) => {
            let response = VmResponse {
                id: vm.id,
                name: vm.name,
                state: vm.state,
                vcpus: vm.vcpus,
                memory_mb: vm.memory_mb,
                ip_address: vm.ip_address,
            };
            Ok(HttpResponse::Ok().json(response))
        }
        Err(e) => {
            error!("Failed to get VM {}: {}", vm_id, e);
            Ok(HttpResponse::NotFound().json(serde_json::json!({
                "error": format!("VM not found: {}", e)
            })))
        }
    }
}

/// Start a VM
pub async fn start_vm(
    config: web::Data<AppConfig>,
    vm_id: web::Path<String>,
) -> Result<HttpResponse> {
    info!("Received request to start VM: {}", vm_id);

    let manager = VmManager::new(config.as_ref().clone());

    match manager.start_vm(&vm_id) {
        Ok(_) => Ok(HttpResponse::Ok().json(serde_json::json!({
            "status": "started"
        }))),
        Err(e) => {
            error!("Failed to start VM {}: {}", vm_id, e);
            Ok(HttpResponse::InternalServerError().json(serde_json::json!({
                "error": format!("Failed to start VM: {}", e)
            })))
        }
    }
}

/// Stop a VM
pub async fn stop_vm(
    config: web::Data<AppConfig>,
    vm_id: web::Path<String>,
) -> Result<HttpResponse> {
    info!("Received request to stop VM: {}", vm_id);

    let manager = VmManager::new(config.as_ref().clone());

    match manager.stop_vm(&vm_id) {
        Ok(_) => Ok(HttpResponse::Ok().json(serde_json::json!({
            "status": "stopped"
        }))),
        Err(e) => {
            error!("Failed to stop VM {}: {}", vm_id, e);
            Ok(HttpResponse::InternalServerError().json(serde_json::json!({
                "error": format!("Failed to stop VM: {}", e)
            })))
        }
    }
}

/// Destroy a VM
pub async fn destroy_vm(
    config: web::Data<AppConfig>,
    vm_id: web::Path<String>,
) -> Result<HttpResponse> {
    info!("Received request to destroy VM: {}", vm_id);

    let manager = VmManager::new(config.as_ref().clone());

    match manager.destroy_vm(&vm_id) {
        Ok(_) => Ok(HttpResponse::Ok().json(serde_json::json!({
            "status": "destroyed"
        }))),
        Err(e) => {
            error!("Failed to destroy VM {}: {}", vm_id, e);
            Ok(HttpResponse::InternalServerError().json(serde_json::json!({
                "error": format!("Failed to destroy VM: {}", e)
            })))
        }
    }
}
