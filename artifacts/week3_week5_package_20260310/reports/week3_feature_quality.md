# Week 3 Step 4 Feature Quality Validation

## Dataset Coverage

- Rows: **11209**
- Distinct runs: **21**
- Protocol counts: `{'coap': 4540, 'mqtt': 6669}`
- Label counts: `{'benign': 3321, 'coap_protocol_abuse': 1500, 'coap_request_flood': 1500, 'mqtt_protocol_abuse': 1765, 'mqtt_publish_flood': 1518, 'mqtt_wildcard_abuse': 1605}`

## Feature Sanity Checks

- Protocol one-hot violations (`f15`,`f16`): **0**
- Normalized feature out-of-range counts (`f00..f14`):
  - `f00`: 0
  - `f01`: 0
  - `f02`: 0
  - `f03`: 0
  - `f04`: 0
  - `f05`: 0
  - `f06`: 0
  - `f07`: 0
  - `f08`: 0
  - `f09`: 0
  - `f10`: 0
  - `f11`: 0
  - `f12`: 0
  - `f13`: 0
  - `f14`: 0

## Cross-Protocol Alignment (KL)

Mean symmetric KL divergence per canonical class:
- `benign`: 13.577499
- `flood`: 15.870026
- `protocol_abuse`: 15.416607

## Artifacts

- `feature_summary_overall.csv`
- `feature_summary_by_protocol.csv`
- `kl_alignment_by_class.csv`
