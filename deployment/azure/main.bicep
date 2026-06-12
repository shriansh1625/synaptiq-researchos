// SynaptiQ ResearchOS — Azure production baseline
// Deploy: az deployment group create -g synaptiq-rg -f deployment/azure/main.bicep

@description('Azure region')
param location string = resourceGroup().location

@description('Environment name')
param environmentName string = 'synaptiq-prod'

@description('Container image for API')
param apiImage string = 'synaptiq-api:latest'

@description('Container image for frontend')
param frontendImage string = 'synaptiq-frontend:latest'

@secure()
param postgresPassword string

@secure()
param openRouterApiKey string

var storageAccountName = toLower('${environmentName}store')
var keyVaultName = '${environmentName}-kv'

resource logAnalytics 'Microsoft.OperationalInsights/workspaces@2022-10-01' = {
  name: '${environmentName}-logs'
  location: location
  properties: {
    sku: { name: 'PerGB2018' }
    retentionInDays: 30
  }
}

resource storage 'Microsoft.Storage/storageAccounts@2023-01-01' = {
  name: storageAccountName
  location: location
  sku: { name: 'Standard_LRS' }
  kind: 'StorageV2'
  properties: {
    supportsHttpsTrafficOnly: true
    minimumTlsVersion: 'TLS1_2'
  }
}

resource blobContainer 'Microsoft.Storage/storageAccounts/blobServices/containers@2023-01-01' = {
  name: '${storage.name}/default/synaptiq-artifacts'
  properties: { publicAccess: 'None' }
}

resource postgres 'Microsoft.DBforPostgreSQL/flexibleServers@2023-06-01-preview' = {
  name: '${environmentName}-pg'
  location: location
  sku: { name: 'Standard_B1ms', tier: 'Burstable' }
  properties: {
    version: '16'
    administratorLogin: 'synaptiq'
    administratorLoginPassword: postgresPassword
    storage: { storageSizeGB: 32 }
    backup: { backupRetentionDays: 7, geoRedundantBackup: 'Disabled' }
    highAvailability: { mode: 'Disabled' }
  }
}

resource redis 'Microsoft.Cache/redis@2023-08-01' = {
  name: '${environmentName}-redis'
  location: location
  properties: {
    sku: { name: 'Basic', family: 'C', capacity: 0 }
    enableNonSslPort: false
    minimumTlsVersion: '1.2'
  }
}

resource containerEnv 'Microsoft.App/managedEnvironments@2024-03-01' = {
  name: '${environmentName}-cae'
  location: location
  properties: {
    appLogsConfiguration: {
      destination: 'log-analytics'
      logAnalyticsConfiguration: {
        customerId: logAnalytics.properties.customerId
        sharedKey: logAnalytics.listKeys().primarySharedKey
      }
    }
  }
}

resource apiApp 'Microsoft.App/containerApps@2024-03-01' = {
  name: '${environmentName}-api'
  location: location
  properties: {
    managedEnvironmentId: containerEnv.id
    configuration: {
      ingress: {
        external: true
        targetPort: 8000
        transport: 'auto'
      }
      secrets: [
        { name: 'openrouter-key', value: openRouterApiKey }
        { name: 'pg-password', value: postgresPassword }
      ]
    }
    template: {
      containers: [
        {
          name: 'api'
          image: apiImage
          env: [
            { name: 'ENVIRONMENT', value: 'production' }
            { name: 'LLM_PROVIDER', value: 'openrouter' }
            { name: 'OPENROUTER_API_KEY', secretRef: 'openrouter-key' }
            { name: 'OTEL_EXPORTER_OTLP_ENDPOINT', value: 'http://otel-collector:4317' }
            {
              name: 'AZURE_STORAGE_CONNECTION_STRING'
              value: 'DefaultEndpointsProtocol=https;AccountName=${storage.name};AccountKey=${storage.listKeys().keys[0].value};EndpointSuffix=core.windows.net'
            }
          ]
          resources: { cpu: json('1.0'), memory: '2Gi' }
        }
      ]
      scale: { minReplicas: 1, maxReplicas: 3 }
    }
  }
}

resource frontendApp 'Microsoft.App/containerApps@2024-03-01' = {
  name: '${environmentName}-ui'
  location: location
  properties: {
    managedEnvironmentId: containerEnv.id
    configuration: {
      ingress: {
        external: true
        targetPort: 3000
        transport: 'auto'
      }
    }
    template: {
      containers: [
        {
          name: 'frontend'
          image: frontendImage
          env: [
            {
              name: 'NEXT_PUBLIC_API_URL'
              value: 'https://${apiApp.properties.configuration.ingress.fqdn}'
            }
          ]
          resources: { cpu: json('0.5'), memory: '1Gi' }
        }
      ]
      scale: { minReplicas: 1, maxReplicas: 2 }
    }
  }
}

output apiUrl string = 'https://${apiApp.properties.configuration.ingress.fqdn}'
output frontendUrl string = 'https://${frontendApp.properties.configuration.ingress.fqdn}'
output storageAccount string = storage.name
output logAnalyticsWorkspace string = logAnalytics.name
