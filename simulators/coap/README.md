# CoAP Live Traffic Scripts

These scripts generate real CoAP traffic against the SentriX CoAP proxy ingress (`5684/udp`).

## Benign

```bash
python -m simulators.coap.coap_live_benign --host 127.0.0.1 --port 5684 --count 50
```

## Attack-like

```bash
python -m simulators.coap.coap_live_attacks --host 127.0.0.1 --port 5684 --attack request_flood --count 100
python -m simulators.coap.coap_live_attacks --host 127.0.0.1 --port 5684 --attack malformed_burst --count 40
```
