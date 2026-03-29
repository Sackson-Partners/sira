// SIRA Platform - Azure Container Apps + Key Vault + Managed Identity
// Resource Group: sira-rg | Phase 2 MVP
//
// SECRET HANDLING: secretKey and databaseUrl are @secure() params.
// Their values are written into Key Vault at deploy time.
// Container Apps reference secrets via keyVaultUrl + managed identity —
// no secret value ever appears in plaintext environment variables.

@description('Azure region')
param location string

@description('Environment tag')
param environment string

@description('Docker Hub image registry')
param registry string = 'docker.io/sacksons'

@description('Database URL. Required — no default. Stored in Key Vault.')
@secure()
param databaseUrl string

@description('JWT secret key. Required — no default. Stored in Key Vault.')
@secure()
param secretKey string

@description('Comma-separated allowed CORS origins. Must be explicit — no wildcards.')
param allowedOrigins string

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
// User-Assigned Managed Identity
// Container Apps use this identity to read secrets from Key Vault.
// ---------------------------------------------------------------------------
resource siraIdentity 'Microsoft.ManagedIdentity/userAssignedIdentities@2023-01-31' = {
  name: 'sira-identity-${environment}'
  location: location
  tags: { project: 'SIRA', environment: environment }
}

// ---------------------------------------------------------------------------
// Azure Key Vault
// Holds all application secrets. RBAC-authorised (not vault access policies).
// Name uses a short hash suffix to stay globally unique and within 24 chars.
// ---------------------------------------------------------------------------
resource keyVault 'Microsoft.KeyVault/vaults@2023-07-01' = {
  name: 'sira-kv-${take(uniqueString(resourceGroup().id), 8)}'
  location: location
  properties: {
    sku: { family: 'A', name: 'standard' }
    tenantId: subscription().tenantId
    enableRbacAuthorization: true   // use role assignments, not access policies
    enableSoftDelete: true
    softDeleteRetentionInDays: 7
    publicNetworkAccess: 'Enabled'
    networkAcls: {
      defaultAction: 'Allow'
      bypass: 'AzureServices'
    }
  }
  tags: { project: 'SIRA', environment: environment }
}

// Grant the managed identity the "Key Vault Secrets User" role on the vault.
// Role ID 4633458b-17de-408a-b874-0445c86b69e6 = Key Vault Secrets User (read-only).
resource kvSecretsUserRole 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(keyVault.id, siraIdentity.id, 'kv-secrets-user')
  scope: keyVault
  properties: {
    roleDefinitionId: subscriptionResourceId(
      'Microsoft.Authorization/roleDefinitions',
      '4633458b-17de-408a-b874-0445c86b69e6'
    )
    principalId: siraIdentity.properties.principalId
    principalType: 'ServicePrincipal'
  }
}

// Populate Key Vault secrets — values come from @secure() params, never committed.
resource kvSecretKey 'Microsoft.KeyVault/vaults/secrets@2023-07-01' = {
  parent: keyVault
  name: 'secret-key'
  properties: { value: secretKey, attributes: { enabled: true } }
}

resource kvDatabaseUrl 'Microsoft.KeyVault/vaults/secrets@2023-07-01' = {
  parent: keyVault
  name: 'database-url'
  properties: { value: databaseUrl, attributes: { enabled: true } }
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
  dependsOn: [kvSecretsUserRole, kvSecretKey, kvDatabaseUrl]
  identity: {
    type: 'UserAssigned'
    userAssignedIdentities: { '${siraIdentity.id}': {} }
  }
  properties: {
    managedEnvironmentId: containerAppsEnv.id
    configuration: {
      activeRevisionsMode: 'Single'
      ingress: {
        external: true
        targetPort: 8000
        transport: 'http'
      }
      secrets: [
        {
          name: 'secret-key'
          keyVaultUrl: kvSecretKey.properties.secretUri
          identity: siraIdentity.id
        }
        {
          name: 'database-url'
          keyVaultUrl: kvDatabaseUrl.properties.secretUri
          identity: siraIdentity.id
        }
      ]
    }
    template: {
      containers: [{
        name: 'api-gateway'
        image: '${registry}/sira-api:latest'
        resources: { cpu: json('0.5'), memory: '1Gi' }
        env: [
          { name: 'ENVIRONMENT',     value: environment }
          { name: 'DATABASE_URL',    secretRef: 'database-url' }
          { name: 'SECRET_KEY',      secretRef: 'secret-key' }
          { name: 'ALLOWED_ORIGINS', value: allowedOrigins }
          { name: 'LOG_LEVEL',       value: 'INFO' }
          { name: 'PORT',            value: '8000' }
        ]
      }]
      scale: { minReplicas: 1, maxReplicas: 5 }
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
  dependsOn: [kvSecretsUserRole, kvSecretKey, kvDatabaseUrl]
  identity: {
    type: 'UserAssigned'
    userAssignedIdentities: { '${siraIdentity.id}': {} }
  }
  properties: {
    managedEnvironmentId: containerAppsEnv.id
    configuration: {
      activeRevisionsMode: 'Single'
      secrets: [
        { name: 'secret-key',   keyVaultUrl: kvSecretKey.properties.secretUri,   identity: siraIdentity.id }
        { name: 'database-url', keyVaultUrl: kvDatabaseUrl.properties.secretUri, identity: siraIdentity.id }
      ]
    }
    template: {
      containers: [{
        name: 'telematics-worker'
        image: '${registry}/sira-telematics:latest'
        resources: { cpu: json('0.25'), memory: '0.5Gi' }
        env: [
          { name: 'ENVIRONMENT',  value: environment }
          { name: 'DATABASE_URL', secretRef: 'database-url' }
          { name: 'SECRET_KEY',   secretRef: 'secret-key' }
        ]
      }]
      scale: { minReplicas: 1, maxReplicas: 1 }
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
  dependsOn: [kvSecretsUserRole, kvSecretKey, kvDatabaseUrl]
  identity: {
    type: 'UserAssigned'
    userAssignedIdentities: { '${siraIdentity.id}': {} }
  }
  properties: {
    managedEnvironmentId: containerAppsEnv.id
    configuration: {
      activeRevisionsMode: 'Single'
      secrets: [
        { name: 'secret-key',   keyVaultUrl: kvSecretKey.properties.secretUri,   identity: siraIdentity.id }
        { name: 'database-url', keyVaultUrl: kvDatabaseUrl.properties.secretUri, identity: siraIdentity.id }
      ]
    }
    template: {
      containers: [{
        name: 'maritime-worker'
        image: '${registry}/sira-maritime:latest'
        resources: { cpu: json('0.25'), memory: '0.5Gi' }
        env: [
          { name: 'ENVIRONMENT',  value: environment }
          { name: 'DATABASE_URL', secretRef: 'database-url' }
          { name: 'SECRET_KEY',   secretRef: 'secret-key' }
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
  dependsOn: [kvSecretsUserRole, kvSecretKey, kvDatabaseUrl]
  identity: {
    type: 'UserAssigned'
    userAssignedIdentities: { '${siraIdentity.id}': {} }
  }
  properties: {
    managedEnvironmentId: containerAppsEnv.id
    configuration: {
      activeRevisionsMode: 'Single'
      secrets: [
        { name: 'secret-key',   keyVaultUrl: kvSecretKey.properties.secretUri,   identity: siraIdentity.id }
        { name: 'database-url', keyVaultUrl: kvDatabaseUrl.properties.secretUri, identity: siraIdentity.id }
      ]
    }
    template: {
      containers: [{
        name: 'ai-worker'
        image: '${registry}/sira-ai:latest'
        resources: { cpu: json('0.5'), memory: '1Gi' }
        env: [
          { name: 'ENVIRONMENT',  value: environment }
          { name: 'DATABASE_URL', secretRef: 'database-url' }
          { name: 'SECRET_KEY',   secretRef: 'secret-key' }
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
output acrLoginServer string = registry
output apiGatewayFqdn string = apiGateway.properties.configuration.ingress.fqdn
output keyVaultName string = keyVault.name
output managedIdentityId string = siraIdentity.id
