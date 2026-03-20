// SIRA Platform - Azure Container Apps Module
// Resource Group: sira-rg | Phase 2 MVP
// Deploys: ACR, Container Apps Environment, API Gateway, Telematics Worker,
//          Maritime Worker, AI Worker, Scheduler, Key Vault, Log Analytics

@description('Azure region')
  param location string

@description('Environment tag')
param environment string

@description('Azure Container Registry name')
param acrName string

// ---------------------------------------------------------------------------
// Log Analytics Workspace
// ---------------------------------------------------------------------------
resource logAnalytics 'Microsoft.OperationalInsights/workspaces@2022-10-01' = {
    name: 'sira-logs-${environment}'
    location: location
  properties: {
    sku: { name: 'PerGB2018' }
    retentionInDays: 30
      }
  tags: { project: 'SIRA', environment: environment }
}

// ---------------------------------------------------------------------------
// Azure Container Registry
// ---------------------------------------------------------------------------
resource acr 'Microsoft.ContainerRegistry/registries@2023-07-01' = {
  name: acrName
      location: location
      sku: { name: 'Basic' }
  properties: { adminUserEnabled: true }
  tags: { project: 'SIRA', environment: environment }
}

// ---------------------------------------------------------------------------
// Key Vault
// ---------------------------------------------------------------------------
resource keyVault 'Microsoft.KeyVault/vaults@2023-07-01' = {
  name: 'sira-kv-${uniqueString(resourceGroup().id)}'
      location: location
  properties: {
    sku: { family: 'A', name: 'standard' }
    tenantId: subscription().tenantId
          enableRbacAuthorization: true
          enableSoftDelete: true
          softDeleteRetentionInDays: 7
      }
  tags: { project: 'SIRA', environment: environment }
}

// ---------------------------------------------------------------------------
// Container Apps Environment
// ---------------------------------------------------------------------------
resource containerAppsEnv 'Microsoft.App/managedEnvironments@2023-05-01' = {
  name: 'sira-cae-${environment}'
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
  tags: { project: 'SIRA', environment: environment }
}

// ---------------------------------------------------------------------------
// API Gateway Container App
// ---------------------------------------------------------------------------
resource apiGateway 'Microsoft.App/containerApps@2023-05-01' = {
  name: 'sira-api-${environment}'
      location: location
  properties: {
    managedEnvironmentId: containerAppsEnv.id
          configuration: {
        activeRevisionsMode: 'Single'
                ingress: {
        external: true
                  targetPort: 8000
                  transport: 'http'
                  corsPolicy: {
          allowedOrigins: ['https://sira-teal.vercel.app', 'https://*.vercel.app']
                      allowedMethods: ['GET', 'POST', 'PUT', 'PATCH', 'DELETE', 'OPTIONS']
                      allowedHeaders: ['*']
                      allowCredentials: true
            }
        }
      registries: [{ server: acr.properties.loginServer, username: acr.name, passwordSecretRef: 'acr-password' }]
      secrets: [{ name: 'acr-password', value: acr.listCredentials().passwords[0].value }]
        }
    template: {
      containers: [{
        name: 'api-gateway'
                  image: '${acr.properties.loginServer}/sira-api:latest'
                  resources: { cpu: json('0.5'), memory: '1Gi' }
        env: [
{ name: 'ENVIRONMENT', value: environment }
          { name: 'DATABASE_URL', secretRef: 'database-url' }
{ name: 'SUPABASE_URL', secretRef: 'supabase-url' }
{ name: 'SUPABASE_JWT_SECRET', secretRef: 'supabase-jwt-secret' }
{ name: 'CLAUDE_API_KEY', secretRef: 'claude-api-key' }
{ name: 'MAPBOX_SECRET_TOKEN', secretRef: 'mapbox-secret-token' }
        ]
      }]
      scale: {
        minReplicas: 2
                  maxReplicas: 10
                  rules: [{ name: 'cpu-scale', custom: { type: 'cpu', metadata: { type: 'Utilization', value: '70' } } }]
          }
    }
  }
  tags: { project: 'SIRA', environment: environment }
}

// ---------------------------------------------------------------------------
// Telematics Worker (always-on MQTT ingestion)
// ---------------------------------------------------------------------------
resource telematicsWorker 'Microsoft.App/containerApps@2023-05-01' = {
  name: 'sira-telematics-${environment}'
      location: location
  properties: {
    managedEnvironmentId: containerAppsEnv.id
          configuration: {
      activeRevisionsMode: 'Single'
              registries: [{ server: acr.properties.loginServer, username: acr.name, passwordSecretRef: 'acr-password' }]
      secrets: [{ name: 'acr-password', value: acr.listCredentials().passwords[0].value }]
        }
    template: {
      containers: [{
        name: 'telematics-worker'
                  image: '${acr.properties.loginServer}/sira-telematics:latest'
                  resources: { cpu: json('0.25'), memory: '0.5Gi' }
        env: [
{ name: 'FLESPI_TOKEN', secretRef: 'flespi-token' }
          { name: 'DATABASE_URL', secretRef: 'database-url' }
        ]
      }]
      scale: { minReplicas: 1, maxReplicas: 1 }
    }
  }
  tags: { project: 'SIRA', environment: environment }
}

// ---------------------------------------------------------------------------
// Maritime Worker (MarineTraffic polling)
// ---------------------------------------------------------------------------
resource maritimeWorker 'Microsoft.App/containerApps@2023-05-01' = {
  name: 'sira-maritime-${environment}'
      location: location
  properties: {
    managedEnvironmentId: containerAppsEnv.id
          configuration: {
      activeRevisionsMode: 'Single'
              registries: [{ server: acr.properties.loginServer, username: acr.name, passwordSecretRef: 'acr-password' }]
      secrets: [{ name: 'acr-password', value: acr.listCredentials().passwords[0].value }]
        }
    template: {
      containers: [{
        name: 'maritime-worker'
                  image: '${acr.properties.loginServer}/sira-maritime:latest'
                  resources: { cpu: json('0.25'), memory: '0.5Gi' }
        env: [
{ name: 'MARINE_TRAFFIC_API_KEY', secretRef: 'marine-traffic-api-key' }
          { name: 'DATABASE_URL', secretRef: 'database-url' }
        ]
      }]
      scale: { minReplicas: 1, maxReplicas: 3 }
    }
  }
  tags: { project: 'SIRA', environment: environment }
}

// ---------------------------------------------------------------------------
// AI Worker
// ---------------------------------------------------------------------------
resource aiWorker 'Microsoft.App/containerApps@2023-05-01' = {
  name: 'sira-ai-worker-${environment}'
      location: location
  properties: {
    managedEnvironmentId: containerAppsEnv.id
          configuration: {
      activeRevisionsMode: 'Single'
              registries: [{ server: acr.properties.loginServer, username: acr.name, passwordSecretRef: 'acr-password' }]
      secrets: [{ name: 'acr-password', value: acr.listCredentials().passwords[0].value }]
        }
    template: {
      containers: [{
        name: 'ai-worker'
                  image: '${acr.properties.loginServer}/sira-ai:latest'
                  resources: { cpu: json('0.5'), memory: '1Gi' }
        env: [
{ name: 'CLAUDE_API_KEY', secretRef: 'claude-api-key' }
          { name: 'OPENAI_API_KEY', secretRef: 'openai-api-key' }
{ name: 'DATABASE_URL', secretRef: 'database-url' }
        ]
      }]
      scale: { minReplicas: 1, maxReplicas: 5 }
    }
  }
  tags: { project: 'SIRA', environment: environment }
}

// ---------------------------------------------------------------------------
// Outputs
// ---------------------------------------------------------------------------
output containerAppsEnvId string = containerAppsEnv.id
  output acrLoginServer string = acr.properties.loginServer
  output keyVaultUri string = keyVault.properties.vaultUri
  output apiGatewayFqdn string = apiGateway.properties.configuration.ingress.fqdn
