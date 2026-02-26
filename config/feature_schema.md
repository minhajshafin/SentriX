# Unified Feature Schema v1 (33 dimensions)

Vector shape:
- 15 normalized behavioral features
- 2 protocol one-hot features (`[1,0]=mqtt`, `[0,1]=coap`)
- 8 MQTT auxiliary features
- 8 CoAP auxiliary features

Tabular output columns:
- `timestamp, protocol, source_id, attack_label, attack_family, f00..f32`

Producer module:
- `simulators/common/feature_schema.py`
