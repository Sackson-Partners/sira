// SIRA Platform - Azure Infrastructure
// Phase 2: Resource Group sira-rg, Container Apps
// Subscription: e919967a-c8ff-4896-977b-360167fa1a84
// Deploys into existing resource group sira-rg (resource group scope)

targetScope = 'resourceGroup'

@description('Azure region for all resources')
param location string = 'southafricanorth'

@description('Environment: dev, staging, prod')
param environment string = 'staging'

// ---------------------------------------------------------------------------
// Deploy resources into sira-rg
// ---------------------------------------------------------------------------
module siraResources 'modules/container-apps.bicep' = {
  name: 'sira-resources'
  params: {
    location: location
    environment: environment
    acrName: 'siracr${uniqueString(resourceGroup().id)}'
  }
}

output containerAppsEnvId string = siraResources.outputs.containerAppsEnvId
output acrLoginServer string = siraResources.outputs.acrLoginServer
