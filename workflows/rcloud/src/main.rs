use actix_web::{middleware, web, App, HttpServer};
use tracing::{info, Level};
use tracing_subscriber::FmtSubscriber;

mod api;
mod config;
mod metrics;
mod vm;

use crate::api::routes::configure_routes;
use crate::config::AppConfig;
use crate::metrics::Metrics;

#[actix_web::main]
async fn main() -> std::io::Result<()> {
    // Initialize tracing
    let subscriber = FmtSubscriber::builder()
        .with_max_level(Level::INFO)
        .with_target(false)
        .with_thread_ids(true)
        .with_file(true)
        .with_line_number(true)
        .json()
        .finish();

    tracing::subscriber::set_global_default(subscriber).expect("Failed to set tracing subscriber");

    info!("Starting rcloud API server");

    // Load configuration
    let config = AppConfig::load().expect("Failed to load configuration");
    info!("Loaded configuration from: {:?}", config.kdevops_root);
    info!("Libvirt URI: {}", config.libvirt_uri);
    info!("Storage pool: {}", config.storage_pool_path.display());

    let bind_addr = config.server.bind_address.clone();
    let workers = config.server.workers;

    info!("Starting HTTP server on {}", bind_addr);

    // Create shared application state
    let app_state = web::Data::new(config);

    // Create metrics
    let metrics = web::Data::new(Metrics::new());
    info!("Initialized Prometheus metrics");

    // Start HTTP server
    HttpServer::new(move || {
        App::new()
            .app_data(app_state.clone())
            .app_data(metrics.clone())
            // Middleware
            .wrap(middleware::Logger::default())
            .wrap(middleware::Compress::default())
            .wrap(tracing_actix_web::TracingLogger::default())
            // Configure routes
            .configure(configure_routes)
    })
    .workers(workers)
    .bind(&bind_addr)?
    .run()
    .await
}
