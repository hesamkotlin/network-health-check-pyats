# Network Health Check Automation System (`Python` + `Cisco pyATS` + `FastAPI`)

![Python](https://img.shields.io/badge/Python-3.9%2B%20%7C%203.11%2B-3776AB?logo=python&logoColor=white)
![Cisco pyATS](https://img.shields.io/badge/Cisco-pyATS%20%26%20Genie%2025.10-049FD9?logo=cisco&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-REST%20API-009688?logo=fastapi&logoColor=white)
![SQLite](https://img.shields.io/badge/SQLite-Execution%20History-003B57?logo=sqlite&logoColor=white)
![Docker](https://img.shields.io/badge/Docker-Compose-2496ED?logo=docker&logoColor=white)
![Tests](https://img.shields.io/badge/pytest-10%20passed-4ade80?logo=pytest&logoColor=white)

A clean, production-structured **Network Test Automation & Health Check System** built with **Python**, **Cisco pyATS (`AEtest`)**, **Cisco Genie**, **Unicon**, **FastAPI**, and **SQLite**.

Designed with **Clean Architecture** and **Modular Monolith** principles, this project validates network device availability, interface operational/administrative status, IPv4 CIDR configuration, and routing table compliance (`Expected State` vs `Actual State`) across both **deterministic offline simulations** and **real Cisco IOS-XE routers** (Cisco DevNet Sandbox).

---

## 1. Key Engineering Highlights

- **Clean Domain Layer (`src/network_health/core/`):**
  - Immutable domain value objects (`@dataclass(frozen=True)`, `Enum`, strict `Type Hints`) and a structured domain exception hierarchy.
  - Pure, 100% deterministic validation functions comparing YAML-defined `ExpectedDeviceHealthPolicy` rules against a point-in-time `DeviceSnapshot`.
- **Strict Separation of Offline Simulation & Real Hardware (`src/network_health/devices/` & `simulation/`):**
  - Abstract `NetworkDeviceConnector(ABC)` contract implementing Dependency Inversion.
  - `SimulatedIosXeDevice` (`is_simulated=True`): Repeatable offline testing for `healthy`, `unhealthy`, and `unreachable` scenarios without requiring physical routers or VPN access.
  - `PyAtsRealDeviceConnector` (`is_simulated=False`): Live SSH connectivity via **Cisco Unicon** using environment-injected secrets (`%ENV{...}`) with zero hardcoded credentials.
- **Official Cisco Genie CLI Parsing (`src/network_health/simulation/genie_parser.py`):**
  - Parses raw Cisco IOS-XE CLI outputs (`show interfaces`, `show ip route`) using official **Cisco Genie** parsers and maps nested schemas into typed domain models.
- **Cisco pyATS `AEtest` Lifecycle & Automated Reporting (`src/network_health/tests/aetest_health_check.py`):**
  - Full `CommonSetup` → `DeviceAvailabilityTestcase` → `InterfaceHealthTestcase` → `RoutingTableTestcase` → `CommonCleanup` execution generating structured JSON and Markdown reports.
- **Multi-Device Concurrency Engine (`src/network_health/core/concurrency.py`):**
  - Demonstrates and benchmarks `ThreadPoolExecutor` (I/O-bound GIL release), `ProcessPoolExecutor` (CPU-bound multi-core parallelism), and `asyncio.gather` + `asyncio.to_thread` (non-blocking event loop offloading) with per-device timeout and error isolation.
- **REST API & SQLite Persistence (`src/network_health/api/` & `database/`):**
  - **FastAPI** + **Pydantic** endpoints backed by a parameterized **SQLite** repository storing test execution history.

---

## 2. Project Architecture

```text
network-health-check/
├── src/
│   └── network_health/
│       ├── core/
│       │   ├── models.py          # Immutable @dataclass domain models & Enums
│       │   ├── exceptions.py      # Domain exception hierarchy
│       │   ├── config.py          # YAML expected health policy loader
│       │   ├── validators.py      # Pure validation functions (Expected vs Actual)
│       │   └── concurrency.py     # Threading, Multiprocessing & Asyncio engine
│       ├── devices/
│       │   ├── base.py            # Abstract NetworkDeviceConnector (ABC)
│       │   └── real_device.py     # Real Cisco IOS-XE connector via Unicon SSH
│       ├── simulation/
│       │   ├── simulated_device.py# Deterministic offline router simulator
│       │   └── genie_parser.py    # Cisco Genie CLI parser & domain mapper
│       ├── database/
│       │   └── repository.py      # Parameterized SQLite execution history repository
│       ├── api/
│       │   └── app.py             # FastAPI REST endpoints & application service
│       ├── reporting/
│       │   └── reporter.py        # JSON & Markdown report generators
│       └── tests/
│           ├── aetest_health_check.py       # Official pyATS AEtest TestScript
│           ├── health_check_job.py          # pyATS Easypy Job runner file
│           ├── test_offline_health_check.py # Core & offline simulation pytest suite
│           └── test_advanced_phases.py      # Real device config, SQLite & concurrency tests
├── testbed/
│   └── devices.yaml.example       # pyATS Testbed topology template (%ENV{} secrets)
├── test_data/
│   ├── expected_health_policy.yaml# Expected interfaces, IPv4 CIDRs & routes
│   ├── iosxe_healthy_outputs.json # Representative healthy Cisco IOS-XE CLI outputs
│   └── iosxe_unhealthy_outputs.json # Representative unhealthy Cisco IOS-XE CLI outputs
├── docker/
│   ├── Dockerfile                 # Container image definition (Python + pyATS + FastAPI)
│   └── docker-compose.yml         # API Service + Test Execution Worker orchestration
├── learning/                      # 12 Persian (RTL) engineering & interview guides
├── reports/                       # Generated JSON & Markdown health reports
├── scripts/
│   └── run_offline_checks.py      # Standalone CLI runner
├── .env.example
├── pyproject.toml
└── requirements.txt
```

---

## 3. Quick Start & Installation (macOS / Linux)

```bash
# 1. Clone the repository and enter the project directory
git clone https://github.com/hesamkotlin/network-health-check-pyats.git
cd network-health-check-pyats

# 2. Create and activate an isolated virtual environment
python3 -m venv .venv
source .venv/bin/activate

# 3. Upgrade packaging tools and install dependencies
python -m pip install --upgrade pip setuptools wheel
python -m pip install --prefer-binary -r requirements.txt
python -m pip install --no-build-isolation --no-deps -e .

# 4. Verify Cisco pyATS & Genie installation
pyats version check --no-check
```

---

## 4. Running Tests & Generating Reports

### A. Run the Full `pytest` Unit & Integration Suite
Executes all 10 unit and integration tests covering YAML policy parsing, Genie CLI parsing, healthy/unhealthy/unreachable evaluations, real-device credential guards, SQLite history persistence, and multi-device concurrency (`Threading`, `Multiprocessing`, `Asyncio`):

```bash
.venv/bin/pytest
```

### B. Run Cisco pyATS `AEtest` Scripts (Offline Simulation)

```bash
# 1. Healthy Router Scenario (100% PASS)
.venv/bin/python src/network_health/tests/aetest_health_check.py --scenario healthy

# 2. Unhealthy Router Scenario (Detects IP drift, administratively down interface & missing routes)
.venv/bin/python src/network_health/tests/aetest_health_check.py --scenario unhealthy
```

### C. Run the Standalone CLI Health Check Runner

```bash
.venv/bin/python scripts/run_offline_checks.py --scenario healthy
.venv/bin/python scripts/run_offline_checks.py --scenario unhealthy
```

---

## 5. Sample Generated Report (`reports/health_report_unhealthy.md`)

| Check Name | Category | Outcome | Expected | Actual | Message |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `device_availability` | `availability` | **PASS** | `reachable=True, hostname=sim-rtr-core-01` | `reachable=True, hostname=sim-rtr-core-01` | Device 'sim-rtr-core-01' is reachable and identified. |
| `interface_status[GigabitEthernet1]` | `interface_status` | **PASS** | `admin=up, oper=up` | `admin=up, oper=up` | Interface 'GigabitEthernet1' is admin=up, oper=up. |
| `interface_ip[GigabitEthernet1]` | `interface_ip` | **FAIL** | `10.10.20.1/24` | `10.10.99.1/24` | Interface 'GigabitEthernet1' IP mismatch: expected '10.10.20.1/24', got '10.10.99.1/24'. |
| `interface_status[GigabitEthernet2]` | `interface_status` | **FAIL** | `admin=up, oper=up` | `admin=down, oper=down` | Interface 'GigabitEthernet2' status mismatch: expected (admin=up, oper=up), got (admin=down, oper=down). |
| `interface_ip[GigabitEthernet2]` | `interface_ip` | **PASS** | `172.16.10.1/24` | `172.16.10.1/24` | Interface 'GigabitEthernet2' has expected IP '172.16.10.1/24'. |
| `interface_status[Loopback0]` | `interface_status` | **PASS** | `admin=up, oper=up` | `admin=up, oper=up` | Interface 'Loopback0' is admin=up, oper=up. |
| `interface_ip[Loopback0]` | `interface_ip` | **PASS** | `192.168.255.1/32` | `192.168.255.1/32` | Interface 'Loopback0' has expected IP '192.168.255.1/32'. |
| `route[0.0.0.0/0]` | `routing` | **FAIL** | `prefix=0.0.0.0/0, active=True, protocol=static, next_hop=10.10.20.254` | `route_missing` | Route '0.0.0.0/0' is missing from the routing table. |
| `route[10.10.20.0/24]` | `routing` | **FAIL** | `prefix=10.10.20.0/24, active=True, protocol=connected, interface=GigabitEthernet1` | `route_missing` | Route '10.10.20.0/24' is missing from the routing table. |
| `route[172.16.10.0/24]` | `routing` | **FAIL** | `prefix=172.16.10.0/24, active=True, protocol=connected, interface=GigabitEthernet2` | `route_missing` | Route '10.10.20.0/24' is missing from the routing table. |

---

## 6. REST API Endpoints (`FastAPI` + `SQLite`)

To run the REST API locally (install `fastapi` and `uvicorn` inside `.venv` if not using Docker):

```bash
.venv/bin/pip install fastapi uvicorn
.venv/bin/uvicorn network_health.api.app:create_fastapi_app --factory --host 127.0.0.1 --port 8000
```

| Method | Endpoint | Description |
| :--- | :--- | :--- |
| `POST` | `/api/v1/runs` | Trigger a health check run (`{"hostname": "sim-rtr-core-01", "scenario": "healthy"}`) and store results in SQLite. |
| `GET` | `/api/v1/runs/{run_id}/status` | Retrieve lightweight execution status and pass/fail counts. |
| `GET` | `/api/v1/runs/{run_id}` | Retrieve full assertion breakdown for a specific test run. |
| `GET` | `/api/v1/runs` | List recent test execution history from SQLite. |
| `GET` | `/docs` | Interactive OpenAPI / Swagger UI documentation. |

---

## 7. Engineering & Interview Learning Guides (`learning/`)

The `learning/` directory contains 12 comprehensive Persian (RTL) engineering guides comparing Python & Network Automation concepts with Kotlin/Android:

- [`00-environment.md`](learning/00-environment.md) — Environment Inspection & Virtual Environments (`.venv`)
- [`01-python-fundamentals.md`](learning/01-python-fundamentals.md) — Python Fundamentals & `@dataclass` for Kotlin Developers
- [`02-pyats-fundamentals.md`](learning/02-pyats-fundamentals.md) — Cisco pyATS Ecosystem (`AEtest`, `Genie`, `Unicon`)
- [`03-aetest.md`](learning/03-aetest.md) — Deep Dive into `pyats.aetest` Lifecycle & Parameter Injection
- [`04-testbed-and-devices.md`](learning/04-testbed-and-devices.md) — pyATS Testbed Topology YAML & `%ENV{}` Secrets
- [`05-network-simulation.md`](learning/05-network-simulation.md) — Deterministic Offline Network Simulation
- [`06-genie.md`](learning/06-genie.md) — Parsing Cisco IOS-XE CLI Outputs with Cisco Genie
- [`07-real-device-connection.md`](learning/07-real-device-connection.md) — Real Device Integration via Unicon SSH & DevNet Sandbox
- [`08-api-and-database.md`](learning/08-api-and-database.md) — FastAPI REST Service, Pydantic Validation & SQLite Persistence
- [`09-concurrency.md`](learning/09-concurrency.md) — Python Concurrency (`GIL`, `Threading`, `Multiprocessing`, `Asyncio`)
- [`10-microservices-and-docker.md`](learning/10-microservices-and-docker.md) — Modular Monolith vs Microservices & Docker Compose
- [`11-interview-cheat-sheet.md`](learning/11-interview-cheat-sheet.md) & [`interview-cheat-sheet.html`](learning/interview-cheat-sheet.html) — Technical Interview Cheat Sheet
