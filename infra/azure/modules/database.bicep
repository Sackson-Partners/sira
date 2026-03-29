// SIRA Platform - Azure Database for PostgreSQL Flexible Server
// Provisions a Burstable B1ms instance in the sira-rg resource group.
//
// SECURITY: adminPassword is @secure() and never stored in Bicep outputs.
// The caller (main.bicep) constructs the DATABASE_URL and passes it directly
// to the Key Vault via the container-apps module.

@description('Azure region')
param location string

@description('Environment tag')
param environment string

@description('PostgreSQL admin password. Required — no default.')
@secure()
param adminPassword string

var serverName = 'sira-db-${environment}'
var adminLogin = 'sira_admin'
var databaseName = 'sira'

// ---------------------------------------------------------------------------
// PostgreSQL Flexible Server
// ---------------------------------------------------------------------------
resource postgresServer 'Microsoft.DBforPostgreSQL/flexibleServers@2022-12-01' = {
  name: serverName
  location: location
  sku: {
    name: 'Standard_B1ms'
    tier: 'Burstable'
  }
  properties: {
    version: '16'  // NOTE: southafricanorth only supports v18 for new servers; existing server stays at v16
    administratorLogin: adminLogin
    administratorLoginPassword: adminPassword
    storage: {
      storageSizeGB: 32
      autoGrow: 'Enabled'
    }
    backup: {
      backupRetentionDays: 7
      geoRedundantBackup: 'Disabled'
    }
    highAvailability: {
      mode: 'Disabled'
    }
    authConfig: {
      activeDirectoryAuth: 'Disabled'
      passwordAuth: 'Enabled'
    }
    // Enforce TLS — clients must use sslmode=require
    maintenanceWindow: {
      customWindow: 'Disabled'
    }
  }
  tags: { project: 'SIRA', environment: environment }
}

// ---------------------------------------------------------------------------
// Application Database
// ---------------------------------------------------------------------------
resource postgresDatabase 'Microsoft.DBforPostgreSQL/flexibleServers/databases@2022-12-01' = {
  parent: postgresServer
  name: databaseName
  properties: {
    charset: 'UTF8'
    collation: 'en_US.utf8'
  }
}

// Allow Azure services to connect (IP 0.0.0.0 → 0.0.0.0 is the Azure-services rule)
resource postgresFirewall 'Microsoft.DBforPostgreSQL/flexibleServers/firewallRules@2022-12-01' = {
  parent: postgresServer
  name: 'AllowAzureServices'
  properties: {
    startIpAddress: '0.0.0.0'
    endIpAddress: '0.0.0.0'
  }
}

// ---------------------------------------------------------------------------
// Outputs (no password — caller already holds it as a @secure() param)
// ---------------------------------------------------------------------------
output serverName string = postgresServer.name
output fqdn string = postgresServer.properties.fullyQualifiedDomainName
output adminLogin string = adminLogin
output databaseName string = databaseName
