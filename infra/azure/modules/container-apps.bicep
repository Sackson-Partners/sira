// SIRA Platform - Azure Container Apps Module
// Resource Group: sira-rg | Phase 2 MVP
// Uses Docker Hub (docker.io/sacksons) - no ACR dependency

@description('Azure region')
param location string

@description('Environment tag')
param environment string

@description('Docker Hub image registry')
param registry string = 'docker.io/sacksons'

@description('Database URL for API (defaults to SQLite for zero-config startup)')
param databaseUrl string = 'sqlite:///./sira.db'

@description('Secret key for JWT signing')
param secretKey string = 'sira-secret-key-change-in-production-min-32-chars-ok'

@description('Allowed CORS origins (comma-separated)')
param allowedOrigins string = '*'

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
      }
    }
    template: {
      containers: [{
        name: 'api-gateway'
        image: '${registry}/sira-api:latest'
        resources: {
          cpu: json('0.5')
          memory: '1Gi'
        }
        env: [
          { name: 'ENVIRONMENT',    value: environment }
          { name: 'DATABASE_URL',   value: databaseUrl }
          { name: 'SECRET_KEY',     value: secretKey }
          { name: 'ALLOWED_ORIGINS', value: allowedOrigins }
          { name: 'LOG_LEVEL',      value: 'INFO' }
          { name: 'PORT',           value: '8000' }
        ]
      }]
      scale: {
        minReplicas: 1
        maxReplicas: 5
      }
    }
  }
  tags: { project: 'SIRA', environment: environment }
}

// ---------------------------------------------------------------------------
// Telematics Worker
// ---------------------------------------------------------------------------
resource telematicsWorker 'Microsoft.App/containerApps@2023-05-01' = {
  name: 'sira-telematics-${environment}'
  location: location
  properties: {
    managedEnvironmentId: containerAppsEnv.id
    configuration: {
      activeRevisionsMode: 'Single'
    }
    template: {
      containers: [{
        name: 'telematics-worker'
        image: '${registry}/sira-telematics:latest'
        resources: {
          cpu: json('0.25')
          memory: '0.5Gi'
        }
        env: [
          { name: 'ENVIRONMENT', value: environment }
          { name: 'DATABASE_URL', value: databaseUrl }
          { name: 'SECRET_KEY',   value: secretKey }
        ]
      }]
      scale: {
        minReplicas: 1
        maxReplicas: 1
      }
    }
  }
  tags: { project: 'SIRA', environment: environment }
}

// ---------------------------------------------------------------------------
// Maritime Worker
// ---------------------------------------------------------------------------
resource maritimeWorker 'Microsoft.App/containerApps@2023-05-01' = {
  name: 'sira-maritime-${environment}'
  location: location
  properties: {
    managedEnvironmentId: containerAppsEnv.id
    configuration: {
      activeRevisionsMode: 'Single'
    }
    template: {
      containers: [{
        name: 'maritime-worker'
        image: '${registry}/sira-maritime:latest'
        resources: {
          cpu: json('0.25')
          memory: '0.5Gi'
        }
        env: [
          { name: 'ENVIRONMENT', value: environment }
          { name: 'DATABASE_URL', value: databaseUrl }
          { name: 'SECRET_KEY',   value: secretKey }
        ]
      }]
      scale: {
        minReplicas: 1
        maxReplicas: 3
      }
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
    }
    template: {
      containers: [{
        name: 'ai-worker'
        image: '${registry}/sira-ai:latest'
        resources: {
          cpu: json('0.5')
          memory: '1Gi'
        }
        env: [
          { name: 'ENVIRONMENT', value: environment }
          { name: 'DATABASE_URL', value: databaseUrl }
          { name: 'SECRET_KEY',   value: secretKey }
        ]
      }]
      scale: {
        minReplicas: 1
        maxReplicas: 5
      }
    }
  }
  tags: { project: 'SIRA', environment: environment }
}

// ---------------------------------------------------------------------------
// Outputs
// ---------------------------------------------------------------------------
output containerAppsEnvId string = containerAppsEnv.id
output acrLoginServer string = registry
output apiGatewayFqdn string = apiGateway.properties.configuration.ingress.fqdn
