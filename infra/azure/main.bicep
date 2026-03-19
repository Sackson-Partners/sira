// SIRA Platform - Azure Infrastructure
// Phase 2: Resource Group sira-rg, Container Apps, PostgreSQL, Key Vault
// Subscription: e919967a-c8ff-4896-977b-360167fa1a84

targetScope = 'subscription'

@description('Azure region for all resources')
param location string = 'westeurope'

@description('Environment: dev, staging, prod')
param environment string = 'prod'

@description('Container Registry name')
param acrName string = 'siracr${uniqueString(subscription().subscriptionId)}'

// ---------------------------------------------------------------------------
// Resource Group: sira-rg
// ---------------------------------------------------------------------------
resource sirarRg 'Microsoft.Resources/resourceGroups@2023-07-01' = {
  name: 'sira-rg'
    location: location
      tags: {
          project: 'SIRA'
              sponsor: 'Energie-Partners'
                  phase: 'MVP-Phase-2'
                      environment: environment
                        }
                        }

                        // ---------------------------------------------------------------------------
                        // Deploy resources into sira-rg
                        // ---------------------------------------------------------------------------
                        module siraResources 'modules/container-apps.bicep' = {
                          name: 'sira-resources'
                            scope: sirarRg
                              params: {
                                  location: location
                                      environment: environment
                                          acrName: acrName
                                            }
                                            }

                                            output resourceGroupName string = sirarRg.name
                                            output containerAppsEnvId string = siraResources.outputs.containerAppsEnvId
                                            output acrLoginServer string = siraResources.outputs.acrLoginServer
                                            
