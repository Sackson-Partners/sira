#!/usr/bin/env bash
# scripts/setup-azure-sp.sh
#
# Creates (or resets) a service principal scoped only to the sira-rg resource group.
# The output JSON is what you paste into the AZURE_CREDENTIALS GitHub Actions secret.
#
# Prerequisites:
#   - Azure CLI installed and logged in: az login
#   - Sufficient permissions (User Access Administrator or Owner on sira-rg)
#
# Usage:
#   chmod +x scripts/setup-azure-sp.sh
#   ./scripts/setup-azure-sp.sh
#
# After running:
#   1. Copy the JSON output.
#   2. GitHub repo → Settings → Secrets and variables → Actions → New secret.
#   3. Name: AZURE_CREDENTIALS   Value: <paste JSON>

set -euo pipefail

SUBSCRIPTION_ID="e919967a-c8ff-4896-977b-360167fa1a84"
RESOURCE_GROUP="sira-rg"
SP_NAME="sira-github-actions"
SCOPE="/subscriptions/${SUBSCRIPTION_ID}/resourceGroups/${RESOURCE_GROUP}"

echo "Creating service principal '${SP_NAME}' scoped to ${SCOPE} ..."

az ad sp create-for-rbac \
  --name "${SP_NAME}" \
  --role contributor \
  --scopes "${SCOPE}" \
  --sdk-auth

echo ""
echo "✓ Done. Copy the JSON above and store it as the AZURE_CREDENTIALS secret in GitHub."
echo ""
echo "To verify the scoping, run:"
echo "  az role assignment list --assignee \$(az ad sp list --display-name ${SP_NAME} --query '[0].appId' -o tsv) --scope ${SCOPE} -o table"
