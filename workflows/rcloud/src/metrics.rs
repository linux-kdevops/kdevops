use prometheus_client::encoding::text::encode;
use prometheus_client::encoding::EncodeLabelSet;
use prometheus_client::metrics::counter::Counter;
use prometheus_client::metrics::family::Family;
use prometheus_client::metrics::gauge::Gauge;
use prometheus_client::registry::Registry;
use std::sync::{Arc, Mutex};

/// Metrics labels for API endpoints
#[derive(Clone, Debug, Hash, PartialEq, Eq, EncodeLabelSet)]
pub struct ApiLabels {
    pub method: String,
    pub endpoint: String,
    pub status: String,
}

/// Application metrics
#[allow(dead_code)]
pub struct Metrics {
    registry: Arc<Mutex<Registry>>,
    http_requests_total: Family<ApiLabels, Counter>,
    vm_count: Gauge,
    vm_operations_total: Family<ApiLabels, Counter>,
}

impl Metrics {
    pub fn new() -> Self {
        let mut registry = Registry::default();

        // HTTP request counter
        let http_requests_total = Family::<ApiLabels, Counter>::default();
        registry.register(
            "rcloud_http_requests_total",
            "Total number of HTTP requests",
            http_requests_total.clone(),
        );

        // VM count gauge
        let vm_count = Gauge::default();
        registry.register("rcloud_vm_count", "Current number of VMs", vm_count.clone());

        // VM operations counter
        let vm_operations_total = Family::<ApiLabels, Counter>::default();
        registry.register(
            "rcloud_vm_operations_total",
            "Total number of VM operations",
            vm_operations_total.clone(),
        );

        Self {
            registry: Arc::new(Mutex::new(registry)),
            http_requests_total,
            vm_count,
            vm_operations_total,
        }
    }

    /// Record an HTTP request
    #[allow(dead_code)]
    pub fn record_request(&self, method: &str, endpoint: &str, status: &str) {
        let labels = ApiLabels {
            method: method.to_string(),
            endpoint: endpoint.to_string(),
            status: status.to_string(),
        };
        self.http_requests_total.get_or_create(&labels).inc();
    }

    /// Update VM count
    #[allow(dead_code)]
    pub fn set_vm_count(&self, count: i64) {
        self.vm_count.set(count);
    }

    /// Record a VM operation
    #[allow(dead_code)]
    pub fn record_vm_operation(&self, operation: &str, status: &str) {
        let labels = ApiLabels {
            method: "VM".to_string(),
            endpoint: operation.to_string(),
            status: status.to_string(),
        };
        self.vm_operations_total.get_or_create(&labels).inc();
    }

    /// Encode metrics in Prometheus text format
    pub fn encode(&self) -> String {
        let mut buffer = String::new();
        if let Ok(registry) = self.registry.lock() {
            let _ = encode(&mut buffer, &registry);
        }
        buffer
    }
}

impl Default for Metrics {
    fn default() -> Self {
        Self::new()
    }
}
