# SynaptiQ — Azure Deployment

## Prerequisites

- Azure CLI (`az login`)
- Resource group: `synaptiq-rg`
- Container images pushed to Azure Container Registry

## Deploy infrastructure

```bash
az group create -n synaptiq-rg -l eastus

az deployment group create \
  -g synaptiq-rg \
  -f deployment/azure/main.bicep \
  -p postgresPassword='<secure>' \
     openRouterApiKey='sk-or-...' \
     apiImage='myregistry.azurecr.io/synaptiq-api:latest' \
     frontendImage='myregistry.azurecr.io/synaptiq-frontend:latest'
```

## Phase 4 observability

- OpenTelemetry traces export to OTLP (`OTEL_EXPORTER_OTLP_ENDPOINT`)
- Log Analytics workspace created by Bicep
- Prometheus metrics at `/observability/metrics`
- Benchmark KPIs at `/benchmark/metrics`
