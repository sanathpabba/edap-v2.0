# Important Links

Quick reference for URLs used in this project. Add new links under the matching section.
Contains URLs only, no secrets.

## Azure

| Resource | Link |
|---|---|
| Azure Portal | https://portal.azure.com |
| Subscription (Azure subscription 1) | https://portal.azure.com/#@/resource/subscriptions/1bd38212-4f79-42c0-b758-37a56d9ebc7e/overview |
| Resource group `edap-rg` | https://portal.azure.com/#@/resource/subscriptions/1bd38212-4f79-42c0-b758-37a56d9ebc7e/resourceGroups/edap-rg/overview |

Region: `centralus`

## Databricks Workspaces

| Workspace | Compute mode | SKU | Workspace URL | Azure Portal |
|---|---|---|---|---|
| `edap-databricks-workspace` | Serverless | - | https://adb-7405612919129990.10.azuredatabricks.net | [Open](https://portal.azure.com/#@/resource/subscriptions/1bd38212-4f79-42c0-b758-37a56d9ebc7e/resourceGroups/edap-rg/providers/Microsoft.Databricks/workspaces/edap-databricks-workspace/overview) |
| `edap-databricks-workspace-v2-0` | Hybrid (serverless + classic) | Premium | https://adb-7405618235802101.1.azuredatabricks.net | [Open](https://portal.azure.com/#@/resource/subscriptions/1bd38212-4f79-42c0-b758-37a56d9ebc7e/resourceGroups/edap-rg/providers/Microsoft.Databricks/workspaces/edap-databricks-workspace-v2-0/overview) |

- Workspace IDs: `7405612919129990` (v1), `7405618235802101` (v2-0)
- v2-0 managed resource group: `edap-databricks-v2-0-managed-rg`
- Azure doesn't allow `.` in workspace names, hence `v2-0`.
