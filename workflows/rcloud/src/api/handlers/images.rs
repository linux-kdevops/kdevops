use actix_web::{web, HttpResponse, Result};
use tracing::{error, info};

use crate::api::models::{ImageInfo, ListImagesResponse};
use crate::config::AppConfig;
use crate::vm::VmManager;

/// List available base images
pub async fn list_images(config: web::Data<AppConfig>) -> Result<HttpResponse> {
    info!("Received request to list base images");

    let manager = VmManager::new(config.as_ref().clone());

    match manager.list_base_images() {
        Ok(images) => {
            let response = ListImagesResponse {
                images: images
                    .iter()
                    .map(|name| ImageInfo { name: name.clone() })
                    .collect(),
            };
            Ok(HttpResponse::Ok().json(response))
        }
        Err(e) => {
            error!("Failed to list base images: {}", e);
            Ok(HttpResponse::InternalServerError().json(serde_json::json!({
                "error": format!("Failed to list images: {}", e)
            })))
        }
    }
}
