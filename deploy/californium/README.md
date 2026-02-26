# Californium Backend Service

This folder contains a minimal Java CoAP backend based on Eclipse Californium.

Exposed resources:
- `coap://<host>:5683/health`
- `coap://<host>:5683/sensors/temp`
- `coap://<host>:5683/actuators/valve`

Build/run is wired through `deploy/docker-compose.yml` as service `californium-backend`.
