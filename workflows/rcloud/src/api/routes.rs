use actix_web::web;

use super::handlers::{health, images, metrics, vms};

/// Configure all API routes
pub fn configure_routes(cfg: &mut web::ServiceConfig) {
    cfg.service(
        web::scope("/api/v1")
            // Health endpoints
            .route("/health", web::get().to(health::health_check))
            .route("/status", web::get().to(health::system_status))
            // VM endpoints
            .route("/vms", web::post().to(vms::create_vm))
            .route("/vms", web::get().to(vms::list_vms))
            .route("/vms/{id}", web::get().to(vms::get_vm))
            .route("/vms/{id}", web::delete().to(vms::destroy_vm))
            .route("/vms/{id}/start", web::post().to(vms::start_vm))
            .route("/vms/{id}/stop", web::post().to(vms::stop_vm))
            // Image endpoints
            .route("/images", web::get().to(images::list_images)),
    )
    // Metrics endpoint (outside /api/v1 scope, standard Prometheus path)
    .route("/metrics", web::get().to(metrics::metrics_handler));
}
