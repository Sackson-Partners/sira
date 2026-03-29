// SIRA Platform - Azure Infrastructure Orchestrator
// Phase 2: Resource Group sira-rg
// Deploys: PostgreSQL + Key Vault + Managed Identity + Container Apps
//
// All secret params are @secure() — never hardcoded, never logged by ARM.
// Supply them via CI/CD pipeline secrets (GitHub Actions → azure-deploy.yml).

targetScope = 'resourceGroup'

@description('Azure region for all resources')
param location string = 'southafricanorth'

@description('Environment: dev, staging, prod')
param environment string = 'staging'

@description('Docker Hub image registry')
param registry string = 'docker.io/sacksons'

@description('JWT secret key. Generate: python3 -c "import secrets; print(secrets.token_hex(32))"')
@secure()
param secretKey string

@description('PostgreSQL admin password. Minimum 8 chars, must include upper, lower, digit, symbol.')
@secure()
param dbAdminPassword string

@description('Comma-separated allowed CORS origins. Example: https://sira.yourdomain.com')
param allowedOrigins string

// ---------------------------------------------------------------------------
// Module 1: PostgreSQL Flexible Server
// ---------------------------------------------------------------------------
module database 'modules/database.bicep' = {
  name: 'sira-database'
  params: {
    location: location
    environment: environment
    adminPassword: dbAdminPassword
  }
}

// ---------------------------------------------------------------------------
// Module 2: Container Apps + Key Vault + Managed Identity
// databaseUrl is constructed here from the database module outputs.
// The password never appears in an output — only in this @secure() interpolation.
// ---------------------------------------------------------------------------
module containerApps 'modules/container-apps.bicep' = {
  name: 'sira-container-apps'
  params: {
    location: location
    environment: environment
    registry: registry
    secretKey: secretKey
    databaseUrl: 'postgresql://${database.outputs.adminLogin}:${dbAdminPassword}@${database.outputs.fqdn}/${database.outputs.databaseName}?sslmode=require'
    allowedOrigins: allowedOrigins
  }
}

// ---------------------------------------------------------------------------
// Outputs
// ---------------------------------------------------------------------------
output containerAppsEnvId string = containerApps.outputs.containerAppsEnvId
output apiGatewayFqdn string = containerApps.outputs.apiGatewayFqdn
output keyVaultName string = containerApps.outputs.keyVaultName
output databaseFqdn string = database.outputs.fqdn
