# Week 5 Baseline Training Results

## Grouped CV (run_id-safe)

| feature_set | model | split | accuracy | f1_macro | f1_weighted |
| --- | --- | --- | ---: | ---: | ---: |
| normalized | random_forest | grouped_cv | 0.7792 | 0.5969 | 0.8118 |
| normalized_plus_pid | random_forest | grouped_cv | 0.7792 | 0.5969 | 0.8118 |
| full | random_forest | grouped_cv | 0.7792 | 0.5969 | 0.8118 |
| normalized | hist_gb | grouped_cv | 0.7372 | 0.5721 | 0.7781 |
| normalized_plus_pid | hist_gb | grouped_cv | 0.7372 | 0.5721 | 0.7781 |
| full | hist_gb | grouped_cv | 0.7372 | 0.5721 | 0.7781 |
| normalized_plus_pid | logreg | grouped_cv | 0.5388 | 0.3894 | 0.5456 |
| normalized | logreg | grouped_cv | 0.5388 | 0.3894 | 0.5455 |
| full | logreg | grouped_cv | 0.5370 | 0.3877 | 0.5432 |

## Cross-Protocol Generalization

| feature_set | model | split | accuracy | f1_macro | f1_weighted |
| --- | --- | --- | ---: | ---: | ---: |
| normalized_plus_pid | random_forest | cross_coap_to_mqtt | 0.2671 | 0.0899 | 0.1201 |
| full | random_forest | cross_coap_to_mqtt | 0.2671 | 0.0899 | 0.1201 |
| normalized | random_forest | cross_coap_to_mqtt | 0.2666 | 0.0898 | 0.1200 |
| normalized | hist_gb | cross_coap_to_mqtt | 0.2650 | 0.0784 | 0.1256 |
| normalized_plus_pid | hist_gb | cross_coap_to_mqtt | 0.2650 | 0.0784 | 0.1256 |
| full | hist_gb | cross_coap_to_mqtt | 0.2650 | 0.0784 | 0.1256 |
| normalized | logreg | cross_coap_to_mqtt | 0.0408 | 0.0172 | 0.0275 |
| normalized_plus_pid | logreg | cross_coap_to_mqtt | 0.0408 | 0.0172 | 0.0275 |
| full | logreg | cross_coap_to_mqtt | 0.0408 | 0.0172 | 0.0275 |
| normalized | logreg | cross_mqtt_to_coap | 0.2526 | 0.0929 | 0.1576 |
| normalized_plus_pid | logreg | cross_mqtt_to_coap | 0.2526 | 0.0929 | 0.1576 |
| full | logreg | cross_mqtt_to_coap | 0.2526 | 0.0929 | 0.1576 |
| normalized | random_forest | cross_mqtt_to_coap | 0.0416 | 0.0254 | 0.0517 |
| normalized | hist_gb | cross_mqtt_to_coap | 0.0416 | 0.0254 | 0.0517 |
| normalized_plus_pid | random_forest | cross_mqtt_to_coap | 0.0416 | 0.0254 | 0.0517 |
| normalized_plus_pid | hist_gb | cross_mqtt_to_coap | 0.0416 | 0.0254 | 0.0517 |
| full | random_forest | cross_mqtt_to_coap | 0.0416 | 0.0254 | 0.0517 |
| full | hist_gb | cross_mqtt_to_coap | 0.0416 | 0.0254 | 0.0517 |

Artifacts:
- `week5_baseline_metrics.csv`
- `week5_baseline_summary.json`
