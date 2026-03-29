// SIRA Platform - Azure Database for PostgreSQL Flexible Server
// References the existing server (already provisioned in sira-rg) and ensures
// the application database and firewall rules are present.
//
// Uses 'existing' for the server to avoid ARM conflicts with immutable
// properties (version, disk size, tier) that were set at original provision time.
//
// SECURITY: adminLogin and adminPassword are never stored in Bicep outputs.
// The caller (main.bicep) constructs the DATABASE_URL from the FQDN output.

@description('Environment tag')
param environment string

var serverName = 'sira-db-${environment}'
var adminLogin = 'sira_admin'
var databaseName = 'sira'

// ---------------------------------------------------------------------------
// Reference the existing PostgreSQL Flexible Server (do not re-provision)
// The server was created manually/previously and its immutable properties
// (version, disk size, SKU tier) cannot be changed via ARM update.
// ---------------------------------------------------------------------------
resource postgresServer 'Microsoft.DBforPostgreSQL/flexibleServers@2022-12-01' existing = {
  name: serverName
}

// ---------------------------------------------------------------------------
// Application Database — idempotent: no-op if already exists
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
// Idempotent: no-op if already exists
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
