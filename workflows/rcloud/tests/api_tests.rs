use actix_web::{test, web, App};
use rcloud::api::handlers::health;

#[actix_rt::test]
async fn test_health_check() {
    let app =
        test::init_service(App::new().route("/api/v1/health", web::get().to(health::health_check)))
            .await;

    let req = test::TestRequest::get().uri("/api/v1/health").to_request();

    let resp = test::call_service(&app, req).await;
    assert!(resp.status().is_success());

    let body: serde_json::Value = test::read_body_json(resp).await;
    assert_eq!(body["status"], "healthy");
    assert!(body["version"].is_string());
}
