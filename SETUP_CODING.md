# SentriX Coding Setup & Deployment Guide

**Last Updated:** April 7, 2026  
**Target:** Complete setup from scratch to fully running system  
**Estimated Time:** 20–30 minutes (depending on internet speed)

---

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [Repository Layout](#repository-layout)
3. [Step 1: Initial Setup](#step-1-initial-setup)
4. [Step 2: Build C++ Proxy Core](#step-2-build-c-proxy-core)
5. [Step 3: Configure Python Environment](#step-3-configure-python-environment)
6. [Step 4: Configure Node.js Dashboard](#step-4-configure-nodejs-dashboard)
7. [Step 5: Start Infrastructure (Docker)](#step-5-start-infrastructure-docker)
8. [Step 6: Run the Full Stack](#step-6-run-the-full-stack)
9. [Step 7: Verify Everything Works](#step-7-verify-everything-works)
10. [Step 8: Generate Test Traffic](#step-8-generate-test-traffic)
11. [Quick Reference Commands](#quick-reference-commands)
12. [Troubleshooting](#troubleshooting)
13. [Cleanup](#cleanup)

---

## Prerequisites

### System Requirements

- **OS:** Linux (Ubuntu 20.04+, Debian 11+, Arch Linux) or macOS 12+
- **RAM:** 8 GB minimum (4 GB for Docker containers, 4 GB for services)
- **Disk:** 10 GB free space (3 GB for Docker images, 2 GB for Python venv, 5 GB for data/models)
- **Network Ports:** 1883, 1884, 5683, 5684, 3000, 8080 must be available

### Required Software

Check your system:

```bash
# Check system info
uname -a
lsb_release -a  # On Linux

# Verify critical tools
which python3 && python3 --version      # Need Python 3.10+
which node && node --version            # Need Node.js 18+
which npm && npm --version              # Need npm 9+
which docker && docker --version        # Need Docker 20.10+
docker compose version                  # Need Docker Compose 2.0+
which gcc && gcc --version              # Need GCC 9+ (or Clang 10+)
which cmake && cmake --version          # Need CMake 3.16+
which git && git --version              # Need Git 2.25+
```

### Installation Instructions (Ubuntu/Debian)

If any prerequisites are missing, install them:

```bash
# Update package manager
sudo apt update
sudo apt upgrade -y

# Install build tools
sudo apt install -y build-essential cmake git curl wget

# Install Python 3.10+ (if not present)
sudo apt install -y python3.10 python3.10-venv python3.10-dev python3-pip
sudo update-alternatives --install /usr/bin/python3 python3 /usr/bin/python3.10 1

# Verify Python
python3 --version  # Should be 3.10+

# Install Node.js 18+ (using NodeSource)
curl -fsSL https://deb.nodesource.com/setup_18.x | sudo -E bash -
sudo apt install -y nodejs

# Verify Node.js
node --version    # Should be 18.0.0+
npm --version     # Should be 9.0.0+

# Install Docker (if not present)
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh

# Add current user to docker group (so you don't need sudo)
sudo usermod -aG docker $USER
newgrp docker  # Activate group without logout

# Verify Docker
docker --version
docker compose version

# Install OpenSSL dev (needed for C++ builds)
sudo apt install -y libssl-dev
```

### Installation Instructions (macOS with Homebrew)

```bash
# Update Homebrew
brew update

# Install build tools
brew install cmake gcc@12 git

# Install Python 3.10+
brew install python@3.10
python3.10 --version

# Install Node.js 18+
brew install node
node --version

# Install Docker (via Docker Desktop GUI or Homebrew)
brew install --cask docker
# or
brew install colima  # Lightweight Docker alternative

# Verify installations
python3 --version
node --version
docker --version
```

### Installation Instructions (Arch Linux)

```bash
# Update package manager and system
sudo pacman -Syu

# Install build tools and development packages
sudo pacman -S base-devel git cmake gcc

# Install Python 3.10+
sudo pacman -S python

# Verify Python version
python --version  # Should be 3.11+ on current Arch

# Install Node.js 18+ and npm
sudo pacman -S nodejs npm

# Verify Node.js
node --version    # Should be 18.0.0+
npm --version     # Should be 9.0.0+

# Install Docker
sudo pacman -S docker

# Add current user to docker group (so you don't need sudo)
sudo usermod -aG docker $USER
newgrp docker  # Activate group without logout

# Verify Docker
docker --version
docker compose version  # Docker Compose might need separate installation

# If Docker Compose not found, install via AUR or manually
# Via AUR with yay:
yay -S docker-compose
# Or manually:
# sudo curl -L "https://github.com/docker/compose/releases/download/v2.20.0/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
# sudo chmod +x /usr/local/bin/docker-compose

# Install OpenSSL dev (needed for C++ builds)
sudo pacman -S openssl

# Install additional utilities (optional but recommended)
sudo pacman -S gcc g++ clang

# Enable and start Docker daemon
sudo systemctl enable docker
sudo systemctl start docker

# Verify all installations
python --version
node --version
npm --version
docker --version
docker compose version
gcc --version
cmake --version
```

---

## Repository Layout

- `proxy-core/` — C++ shared proxy framework + protocol modules
- `simulators/` — Python benign/attack traffic generators
- `ml-pipeline/` — ML training pipeline (models, training scripts, evaluation)
- `dashboard/` — Next.js real-time monitoring UI
- `deploy/` — Docker Compose stack + broker configurations
- `data/` — Dataset workspace (raw, features, processed)
- `config/` — Configuration files (feature schemas, thresholds)

---

## Step 1: Initial Setup

### 1.1) Clone or Navigate to Repository

If you haven't already, navigate to the SentriX repository:

```bash
# Navigate to your SentriX directory
cd /home/billy/X/SentriX

# Verify you're in the right place
ls -la | grep -E "(proxy-core|dashboard|ml-pipeline|deploy)"

# Expected output: directories proxy-core, dashboard, ml-pipeline, deploy, etc.
```

### 1.2) Create Data Directories

```bash
# Create necessary directories for data storage
mkdir -p data/raw
mkdir -p data/features
mkdir -p data/processed
mkdir -p ml-pipeline/reports
mkdir -p ml-pipeline/figures
mkdir -p ml-pipeline/models

# Create temporary directories for metrics/events
mkdir -p /tmp/sentrix-dev
mkdir -p /tmp/sentrix-demo

# Verify directories exist
ls -ld data/* ml-pipeline/*

# Expected: All directories created successfully
```

### 1.3) Initialize Git (if needed)

```bash
# Check if git is initialized
git status

# If not initialized, initialize
git init
git add .
git commit -m "Initial SentriX setup"
```

---

## Step 2: Build C++ Proxy Core

### 2.1) Check C++ Compiler & CMake

```bash
# Verify compiler
gcc --version        # Should be 9+
g++ --version        # Should be 9+

# Alternative: Use Clang
clang --version      # Should be 10+

# Verify CMake
cmake --version      # Should be 3.16+
```

### 2.2) Build Proxy Core (Debug Mode - Recommended for Development)

```bash
cd /home/billy/X/SentriX/proxy-core

# Clean any previous builds
rm -rf build build-onnx CMakeCache.txt

# Create build directory
mkdir -p build

# Configure CMake (debug build with symbols)
cmake -S . -B build \
  -DCMAKE_BUILD_TYPE=Debug \
  -DCMAKE_CXX_COMPILER=g++ \
  -DCMAKE_CXX_FLAGS="-Wall -Wextra -Wpedantic"

# Build
cmake --build build -j$(nproc)

# Verify executable was created
ls -lh build/sentrix_proxy
file build/sentrix_proxy

# Expected: ELF 64-bit executable, not stripped
```

### 2.3) Build Proxy Core (Release Mode - for Production)

```bash
cd /home/billy/X/SentriX/proxy-core

# Create release build directory
mkdir -p build-release

# Configure for release (with ONNX Runtime support)
cmake -S . -B build-release \
  -DCMAKE_BUILD_TYPE=Release \
  -DSENTRIX_ENABLE_ONNX_RUNTIME=ON

# Build with optimization
cmake --build build-release -j$(nproc) --config Release

# Verify and check size
ls -lh build-release/sentrix_proxy
strip build-release/sentrix_proxy  # Optional: reduce size

# Expected: ~2-5 MB executable after strip
```

### 2.4) Test Proxy Binary Locally (Without Docker)

```bash
# First, ensure backends are running in Docker
cd /home/billy/X/SentriX/deploy
docker compose up -d mosquitto californium-backend

# Wait for services to start
sleep 3
docker compose ps

# Expected: sentrix-mosquitto and sentrix-coap-backend both "Up"

# Now run proxy with host environment variables
cd /home/billy/X/SentriX/proxy-core
SENTRIX_MQTT_BROKER_HOST=127.0.0.1 \
SENTRIX_MQTT_BROKER_PORT=1883 \
SENTRIX_COAP_BACKEND_HOST=127.0.0.1 \
SENTRIX_COAP_BACKEND_PORT=5683 \
SENTRIX_MQTT_PROXY_PORT=1884 \
SENTRIX_COAP_PROXY_PORT=5684 \
SENTRIX_METRICS_PATH=/tmp/sentrix-dev/metrics.json \
SENTRIX_EVENTS_PATH=/tmp/sentrix-dev/events.jsonl \
SENTRIX_FEATURE_DEBUG_PATH=/tmp/sentrix-dev/features.jsonl \
./build/sentrix_proxy

# Expected output:
# [PROXY] MQTT module listening on 0.0.0.0:1884
# [PROXY] CoAP module listening on 0.0.0.0:5684
# [DETECTION] Detection pipeline initialized
```

If the proxy runs successfully, press `Ctrl+C` to stop it. We'll run it again in the full stack.

---

## Step 3: Configure Python Environment

### 3.1) Create Python Virtual Environment

```bash
cd /home/billy/X/SentriX

# Create venv
python3 -m venv .venv

# Verify venv was created
ls -ld .venv

# Expected: .venv directory exists
```

### 3.2) Activate Virtual Environment

```bash
# Activate the venv
source .venv/bin/activate

# Verify activation (prompt should show (.venv) prefix)
echo $VIRTUAL_ENV
# Expected: /home/billy/X/SentriX/.venv

# Check Python version
python --version  # Should be 3.10+
```

### 3.3) Install Python Dependencies

```bash
# Ensure pip is up to date
pip install --upgrade pip setuptools wheel

# Install core ML/data science dependencies
pip install \
  numpy==1.24.0 \
  pandas==2.0.0 \
  scikit-learn==1.2.0 \
  lightgbm==4.0.0 \
  matplotlib==3.7.0 \
  seaborn==0.12.0 \
  scipy==1.10.0

# Install ONNX support for ML model export
pip install \
  onnx==1.14.0 \
  onnxmltools==1.12.0 \
  onnxruntime==1.15.0

# Install testing & utilities
pip install pytest pytest-cov ipython jupyter

# Install MQTT client for simulators
pip install paho-mqtt==1.7.1

# Install CoAP client for simulators
pip install aiocoap==0.4.4

# Verify installations
pip list | grep -E "(numpy|pandas|lightgbm|scikit-learn|onnx)"

# Expected: All packages listed with versions
```

### 3.4) Create requirements.txt for Reproducibility

```bash
cd /home/billy/X/SentriX

# Generate requirements file from current venv
pip freeze > requirements.txt

# Verify it contains key packages
grep -E "(numpy|pandas|lightgbm|onnx)" requirements.txt

# Expected: All key packages present with pinned versions
```

---

## Step 4: Configure Node.js Dashboard

### 4.1) Install Node Dependencies

```bash
cd /home/billy/X/SentriX/dashboard

# Install npm packages
npm install

# This installs Next.js, React, Recharts, TypeScript, etc.
# Verify node_modules exists
ls -ld node_modules

# Expected: node_modules directory created with all dependencies

# Check specific packages
npm list next react recharts

# Expected: All three packages listed
```

### 4.2) Create Environment Files

```bash
cd /home/billy/X/SentriX/dashboard

# Create .env.local from template (if template exists)
if [ -f .env.example ]; then
  cp .env.example .env.local
else
  # If no template, create it manually
  cat > .env.local <<EOF
NEXT_PUBLIC_METRICS_BASE_URL=http://localhost:8080
NEXT_PUBLIC_REFRESH_INTERVAL=5000
EOF
fi

# Verify .env.local created
cat .env.local

# Expected:
# NEXT_PUBLIC_METRICS_BASE_URL=http://localhost:8080
# NEXT_PUBLIC_REFRESH_INTERVAL=5000
```

### 4.3) Build Dashboard (Optional, for production)

```bash
cd /home/billy/X/SentriX/dashboard

# Build optimized production version (takes 1-2 minutes)
npm run build

# Verify build succeeded
ls -ld .next

# Expected: .next directory created with optimized build

# Check build size
du -sh .next

# Expected: ~200-500 MB (normal for Next.js)
```

---

## Step 5: Start Infrastructure (Docker)

### 5.1) Verify Docker Daemon is Running

```bash
# Check Docker daemon
docker ps

# Expected: Shows running containers or "Container ID ... IMAGE ..." header

# If Docker not running:
# - Linux: sudo systemctl start docker
# - macOS: Open Docker Desktop app
```

### 5.2) Build & Start All Containers

```bash
cd /home/billy/X/SentriX/deploy

# First, build Californium backend (one-time)
docker compose build californium-backend

# This builds a custom Java CoAP server
# Expected output: "Successfully tagged sentrix-coap-backend:latest"

# Now build all services
docker compose build

# Expected: All services built successfully

# Verify images were created
docker images | grep sentrix

# Expected: sentrix:proxy-core, sentrix:californium-backend, etc.
```

### 5.3) Start Services

```bash
cd /home/billy/X/SentriX/deploy

# Start all services
docker compose up -d

# Verify services are up
docker compose ps

# Expected output:
# NAME                    STATUS    PORTS
# sentrix-mosquitto       Up        0.0.0.0:1883->1883/tcp
# sentrix-coap-backend    Up        0.0.0.0:5683->5683/udp
# sentrix-proxy-core      Up        0.0.0.0:1884->1884/tcp, 0.0.0.0:5684->5684/udp
# sentrix-metrics-api     Up        0.0.0.0:8080->8080/tcp

# Check logs to ensure services started cleanly
docker compose logs --tail=20 proxy-core
docker compose logs --tail=20 metrics-api-stub

# Expected: No error messages, services initialized
```

---

## Step 6: Run the Full Stack

### 6.1) Terminal A: Docker Services (Already Running)

Services are already running from Step 5. Keep docker compose running:

```bash
cd /home/billy/X/SentriX/deploy

# Watch logs in real-time
docker compose logs -f

# or monitor specific services
docker compose logs -f proxy-core
```

### 6.2) Terminal B: Metrics API Server

```bash
cd /home/billy/X/SentriX

# Start Node.js metrics API server
node deploy/scripts/metrics_server.js

# Expected output:
# Server running on http://localhost:8080
# Monitoring /tmp/sentrix-demo/metrics.json

# Keep this terminal open
```

### 6.3) Terminal C: Dashboard Frontend

```bash
cd /home/billy/X/SentriX/dashboard

# Activate Python venv first (needed for any Python simulators later)
source ../.venv/bin/activate

# Start Next.js dev server
npm run dev

# Expected output:
# ▲ Next.js 14.2.32
# - Local:        http://localhost:3000
# - Environments: .env.local

# Keep this terminal open

# Dashboard is now accessible at http://localhost:3000
```

### 6.4) Verify All Services Running

```bash
# In a new Terminal D, check all services are responding

# Check Mosquitto MQTT broker
mosquitto_sub -h 127.0.0.1 -p 1883 -t '#' -C 1 &
sleep 1
# (No output expected - broker is just listening)

# Check proxy metrics API
curl http://localhost:8080/health
# Expected: {"status":"ok",...}

# Check metrics
curl http://localhost:8080/metrics | python -m json.tool
# Expected: {"mqtt_msgs":0,"coap_msgs":0,...}

# Check dashboard health
curl http://localhost:3000 -I
# Expected: HTTP/1.1 200 OK

# Expected all checks pass ✅
```

---

## Step 7: Verify Everything Works

### 7.1) Verify MQTT Pass-Through

```bash
# In Terminal D (or new terminal)

# Publish test MQTT messages to proxy ingress (1884)
python3 - <<'MQTT_TEST'
import paho.mqtt.client as mqtt
import time

client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)

def on_connect(client, userdata, flags, rc, properties=None):
    if rc == 0:
        print("Connected to MQTT proxy. Publishing 5 test messages...")
        for i in range(5):
            topic = f"sensors/temp/room{i}"
            message = f"temperature_{i}_{time.time()}"
            client.publish(topic, payload=message, qos=1)
            print(f"  Published to {topic}: {message}")
        time.sleep(1)
    client.disconnect()

client.on_connect = on_connect
client.connect("127.0.0.1", 1884, keepalive=30)
client.loop_start()
time.sleep(3)
print("Done. Check metrics API for mqtt_msgs increase.")
MQTT_TEST

# Check if MQTT messages were recorded
curl http://localhost:8080/metrics | python -m json.tool | grep mqtt_msgs
# Expected: "mqtt_msgs" > 0
```

### 7.2) Verify CoAP Pass-Through (Optional)

```bash
# If simulators are available, test CoAP
cd /home/billy/X/SentriX

source .venv/bin/activate

# Try running CoAP benign simulator (if available)
python -m simulators.coap.coap_live_benign --host 127.0.0.1 --port 5684 --count 10 2>/dev/null || \
  echo "CoAP simulators not available (optional)"

# Check if CoAP messages were recorded
curl http://localhost:8080/metrics | python -m json.tool | grep coap_msgs
# Expected: "coap_msgs" > 0 (if simulator ran)
```

### 7.3) Check Dashboard Displays Metrics

Open browser and navigate to:
```
http://localhost:3000
```

**Expected to see:**
- ✅ Four KPI cards at top (MQTT count, CoAP count, Detections, Latency P95)
- ✅ Protocol distribution pie chart
- ✅ Feature statistics (total vectors, per-protocol counts)
- ✅ Anomaly score distribution
- ✅ Auto-refreshing every 5 seconds

If dashboard shows "Error fetching metrics", check:
1. Metrics API running on port 8080
2. Metrics file exists: `ls -la /tmp/sentrix-demo/metrics.json`
3. API responding: `curl http://localhost:8080/metrics`

### 7.4) View Feature Vectors & Events

```bash
# Check events log
curl http://localhost:8080/events | python -m json.tool | head -30

# Check feature vectors (if exported)
ls -la /tmp/sentrix-dev/features.jsonl 2>/dev/null || \
  echo "Feature debug file not created yet (will be created when proxy runs)"

# View first feature vector (if available)
head -1 /tmp/sentrix-dev/features.jsonl 2>/dev/null | python -m json.tool
```

---

## Step 8: Generate Test Traffic

### 8.1) Generate MQTT Traffic

```bash
cd /home/billy/X/SentriX

source .venv/bin/activate

# Run benign MQTT scenario (generates normal traffic)
python proxy-core/scripts/week8_benign_scenario.py

# Expected output:
# MQTT traffic generated: X messages published
# Check metrics at http://localhost:8080/metrics
```

### 8.2) Generate CoAP Traffic (If Simulators Available)

```bash
cd /home/billy/X/SentriX

source .venv/bin/activate

# Benign CoAP traffic
python -m simulators.coap.coap_live_benign \
  --host 127.0.0.1 \
  --port 5684 \
  --count 20 \
  2>/dev/null || echo "CoAP simulator not available"

# Attack-like CoAP traffic (if available)
python -m simulators.coap.coap_live_attacks \
  --host 127.0.0.1 \
  --port 5684 \
  --attack request_flood \
  --count 40 \
  2>/dev/null || echo "CoAP simulator not available"
```

### 8.3) Monitor Metrics in Real-Time

```bash
# In another terminal, watch metrics update every 2 seconds
watch -n 2 'curl -s http://localhost:8080/metrics | python -m json.tool'

# Or check feature stats
watch -n 2 'curl -s http://localhost:8080/features/stats | python -m json.tool'
```

---

## Quick Reference Commands

### Start Everything (Fastest)

```bash
# Terminal 1: Docker services
cd /home/billy/X/SentriX/deploy
docker compose up -d && docker compose logs -f

# Terminal 2: Metrics API
cd /home/billy/X/SentriX
node deploy/scripts/metrics_server.js

# Terminal 3: Dashboard
cd /home/billy/X/SentriX/dashboard
npm run dev

# Terminal 4: Run traffic (after all services up)
cd /home/billy/X/SentriX
source .venv/bin/activate
python proxy-core/scripts/week8_benign_scenario.py
```

### Build Proxy Only

```bash
cd /home/billy/X/SentriX/proxy-core
rm -rf build
cmake -S . -B build -DCMAKE_BUILD_TYPE=Debug
cmake --build build -j
./build/sentrix_proxy  # with env vars set
```

### Run ML Training

```bash
cd /home/billy/X/SentriX

source .venv/bin/activate

# Train all baseline models (5-fold CV)
python ml-pipeline/src/train_baselines.py

# Expected runtime: ~5 minutes
# Output: ml-pipeline/reports/week5_baseline_metrics.csv

# Train champion model only
python ml-pipeline/src/week6_train_champion.py
# Output: ml-pipeline/models/lightgbm_full.pkl

# Validate feature quality
python ml-pipeline/src/validate_feature_quality.py
# Output: ml-pipeline/reports/{feature_summary,kl_alignment}*.csv
```

### Generate Paper Figures

```bash
cd /home/billy/X/SentriX

source .venv/bin/activate

# Generate all 7 paper figures
python ml-pipeline/src/week11_generate_figures.py

# Output: ml-pipeline/figures/fig[1-7]_*.png
# Expected runtime: ~2 minutes

# View figures
ls -lh ml-pipeline/figures/
```

### Run Statistical Analysis

```bash
cd /home/billy/X/SentriX

source .venv/bin/activate

# Perform bootstrap CIs and pairwise tests
python ml-pipeline/src/week11_statistical_analysis.py

# Output: ml-pipeline/reports/week11_statistical_analysis.json
# Expected runtime: ~1 minute
```

---

## Troubleshooting

### Issue: Docker Services Not Starting

**Symptoms:** `docker compose ps` shows "Exited" or "Created"

**Solution:**
```bash
# Check logs
docker compose logs proxy-core
docker compose logs mosquitto

# Restart with verbose output
docker compose down
docker compose up --build

# Check port conflicts
lsof -i :1883  # MQTT
lsof -i :1884  # MQTT Proxy
lsof -i :5683  # CoAP
lsof -i :5684  # CoAP Proxy
lsof -i :8080  # Metrics API
lsof -i :3000  # Dashboard

# Kill conflicting processes if found
pkill -f sentrix
```

### Issue: Proxy Binary Build Fails

**Symptoms:** `cmake --build build` shows compiler errors

**Solution:**
```bash
# Check compiler version
g++ --version  # Need 9+
cmake --version  # Need 3.16+

# Clean and rebuild
cd proxy-core
rm -rf build CMakeCache.txt

# Try with explicit compiler
cmake -S . -B build \
  -DCMAKE_CXX_COMPILER=/usr/bin/g++-11 \
  -DCMAKE_C_COMPILER=/usr/bin/gcc-11

cmake --build build -j4 -v  # -v for verbose
```

### Issue: Python Venv Problems

**Symptoms:** `python --version` shows wrong version or module not found

**Solution:**
```bash
# Verify venv is activated
echo $VIRTUAL_ENV  # Should show path to .venv

# If not activated or wrong Python:
cd /home/billy/X/SentriX
python3 -m venv .venv --clear  # Recreate
source .venv/bin/activate
python --version  # Should be 3.10+

# Reinstall dependencies
pip install --upgrade pip
pip install -r requirements.txt
```

### Issue: Dashboard Won't Start

**Symptoms:** `npm run dev` fails or shows blank page

**Solution:**
```bash
cd /home/billy/X/SentriX/dashboard

# Clean and rebuild
rm -rf node_modules .next
npm install
npm run build  # Optional: test build

# Check env file
cat .env.local
# Should have: NEXT_PUBLIC_METRICS_BASE_URL=http://localhost:8080

# Start dev server with verbose output
npm run dev -- --debug
```

### Issue: Metrics API Not Responding

**Symptoms:** `curl http://localhost:8080/metrics` times out or refuses connection

**Solution:**
```bash
# Check if metrics API is running
ps aux | grep metrics_server

# Check if port is in use
lsof -i :8080

# Check metrics file exists
ls -la /tmp/sentrix-dev/metrics.json

# Manually start metrics server with verbose output
cd /home/billy/X/SentriX
node deploy/scripts/metrics_server.js

# If file path error, check SENTRIX_METRICS_PATH env var in proxy
```

### Issue: MQTT Messages Not Reaching Dashboard

**Symptoms:** Dashboard shows mqtt_msgs = 0 after sending messages

**Solution:**
```bash
# Check if proxy is receiving messages
# 1. Verify proxy is running
docker compose ps proxy-core

# 2. Publish and check event log
curl http://localhost:8080/events | python -m json.tool | grep -c "mqtt"

# 3. Check metrics file directly
cat /tmp/sentrix-dev/metrics.json | python -m json.tool

# 4. Monitor proxy logs
docker compose logs -f proxy-core | grep -E "(MQTT|traffic|msg)"

# If no messages: proxy may not be connected to broker
# Check broker logs
docker compose logs mosquitto
```

### Issue: ML Training Very Slow

**Symptoms:** `train_baselines.py` running for >15 minutes

**Solution:**
```bash
# Check if it's CPU-bound (expected for tree models)
# Run with reduced folds for testing
python ml-pipeline/src/train_baselines.py --folds 2 --models lightgbm

# Check available CPUs
nproc  # Should be 4+

# Monitor during training
watch -n 2 'ps aux | grep train'
top  # Check CPU usage
```

### Issue: Out of Disk Space

**Symptoms:** Docker pull fails or ML training fails with "No space left on device"

**Solution:**
```bash
# Check disk usage
df -h

# Clean Docker
docker system prune -a --volumes

# Clean pip cache
pip cache purge

# Clean ML cache
rm -rf .cache ml-pipeline/reports/* ml-pipeline/figures/*

# Remove old Docker images
docker image prune -a
```

---

## Cleanup

### Stop Services (Keep Data)

```bash
# Stop Docker services
cd /home/billy/X/SentriX/deploy
docker compose down

# Expected: All containers stopped and removed

# Verify
docker compose ps
# Expected: empty or "no containers"

# Data persists in:
# - /tmp/sentrix-dev/  (metrics, events, features)
# - data/  (datasets)
# - ml-pipeline/reports/  (results)
```

### Full Cleanup (Remove Everything)

```bash
# Remove Docker containers, images, volumes
cd /home/billy/X/SentriX/deploy
docker compose down -v --remove-orphans

# Remove built artifacts
rm -rf proxy-core/build proxy-core/build-release
rm -rf dashboard/node_modules dashboard/.next
rm -rf .venv

# Remove Python cache
find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null
find . -type d -name .pytest_cache -exec rm -rf {} + 2>/dev/null

# Remove temp files
rm -rf /tmp/sentrix-dev /tmp/sentrix-demo

# Verify cleanup
docker ps
docker images | grep sentrix
ls proxy-core/build* 2>/dev/null || echo "Build artifacts cleaned"
```

### Selective Cleanup

```bash
# Remove only Python venv (keep Docker services)
rm -rf .venv

# Remove only Docker (keep Python/node)
docker compose down -v

# Remove only dashboard node_modules
rm -rf dashboard/node_modules

# Remove only ML results
rm -rf ml-pipeline/reports/* ml-pipeline/figures/*
```

---

## Next Steps

Once everything is running:

1. **Explore the Dashboard** at `http://localhost:3000`
2. **Send Test Traffic** using scripts in `proxy-core/scripts/`
3. **Review Metrics API** at `http://localhost:8080/metrics`
4. **Train ML Models** with `python ml-pipeline/src/train_baselines.py`
5. **Read Full Docs** in `CODEBASE_OVERVIEW_ONBOARDING.md`
6. **Run Demo** using `DEMO_CHEATSHEET_5MIN.md`

---

## Support & Issues

For detailed help:
- See `CODEBASE_OVERVIEW_ONBOARDING.md` for architecture details
- Check `Research_plan.md` for research objectives
- Review weekly reports in `ml-pipeline/reports/`
- Check C++ header files in `proxy-core/include/sentrix/` for code comments

**Happy hacking! 🚀**
