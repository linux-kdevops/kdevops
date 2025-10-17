use actix_web::{web, HttpResponse, Result};
use serde::{Deserialize, Serialize};
use tracing::info;

use crate::config::AppConfig;

#[derive(Debug, Serialize, Deserialize)]
pub struct HealthResponse {
    pub status: String,
    pub version: String,
}

#[derive(Debug, Serialize, Deserialize)]
pub struct SystemStatusResponse {
    pub status: String,
    pub version: String,
    pub kdevops_root: String,
    pub libvirt_uri: String,
    pub storage_pool_path: String,
    pub base_images_dir: String,
    pub network_bridge: String,
}

/// Health check endpoint
pub async fn health_check() -> Result<HttpResponse> {
    info!("Health check requested");

    let response = HealthResponse {
        status: "healthy".to_string(),
        version: env!("CARGO_PKG_VERSION").to_string(),
    };

    Ok(HttpResponse::Ok().json(response))
}

/// System status endpoint with configuration details
pub async fn system_status(config: web::Data<AppConfig>) -> Result<HttpResponse> {
    info!("System status requested");

    let response = SystemStatusResponse {
        status: "operational".to_string(),
        version: env!("CARGO_PKG_VERSION").to_string(),
        kdevops_root: config.kdevops_root.display().to_string(),
        libvirt_uri: config.libvirt_uri.clone(),
        storage_pool_path: config.storage_pool_path.display().to_string(),
        base_images_dir: config.base_images_dir.display().to_string(),
        network_bridge: config.network_bridge.clone(),
    };

    Ok(HttpResponse::Ok().json(response))
}
