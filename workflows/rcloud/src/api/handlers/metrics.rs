use actix_web::{web, HttpResponse, Result};
use tracing::info;

use crate::metrics::Metrics;

/// Prometheus metrics endpoint
pub async fn metrics_handler(metrics: web::Data<Metrics>) -> Result<HttpResponse> {
    info!("Metrics endpoint accessed");

    let metrics_text = metrics.encode();

    Ok(HttpResponse::Ok()
        .content_type("text/plain; version=0.0.4")
        .body(metrics_text))
}
