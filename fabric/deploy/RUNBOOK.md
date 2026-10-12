# Runbook: stand up the DAPA dashboards in Azure

One command creates a Fabric capacity in your Azure resource group, creates a Fabric workspace on it, creates the empty data tables and publishes both Power BI dashboard skeletons. No data is loaded. It signs in as you through the Azure CLI, so there are no keys or passwords to handle.

Works on macOS, Windows and Linux. Expect about 15 minutes end to end, most of it waiting on Azure and Spark.

## What gets created

| Where | What | Billed? |
|---|---|---|
| Your Azure resource group | One Fabric capacity (size F2 by default) | Yes, hourly while running. Pause it when idle. |
| Microsoft Fabric | One workspace on that capacity | No separate charge |
| That workspace | Lakehouse, notebook, two semantic models, two reports | Covered by the capacity |

Nothing outside these is created or changed. Re-running the command updates the same items in place and never deletes anything.

## Before you start

You need:

- **Azure CLI**, from https://aka.ms/installazurecli
- **Python 3.10 or newer**, from https://www.python.org/downloads (no extra packages needed)
- **Git**, to get this repository
- **A work or school Microsoft account** in the same Microsoft Entra tenant as the Azure subscription. Personal Microsoft accounts cannot use Fabric.
- **Contributor or Owner** on the target resource group
- **Fabric enabled for your organization.** A Fabric or Power BI administrator controls this in the Fabric admin portal, under tenant settings, with the setting "Users can create Fabric items". If you are unsure, step 6 will tell you.

To show the maps, a Fabric administrator also needs to turn on "Use Azure Maps visual" in the same tenant settings. Everything else works without it.

## Steps

1. **Get the code.**

   ```bash
   git clone https://github.com/bryan3342/lead-microsoft-project.git
   cd lead-microsoft-project
   ```

2. **Sign in to Azure.** A browser window opens. Use your work account.

   ```bash
   az login
   ```

   If your account can see more than one tenant, add `--tenant <tenant-id>` so you sign in to the one that holds the subscription.

3. **Find your subscription ID and resource group.**

   ```bash
   az account list --query "[].{name:name, id:id}" -o table
   az group list --subscription <subscription-id> --query "[].{name:name, location:location}" -o table
   ```

4. **Create your settings file.** Copy the example, then fill in the values. Git ignores your copy.

   ```bash
   cp fabric/deploy/config.env.example fabric/deploy/config.env
   ```

   On Windows Command Prompt, use `copy fabric\deploy\config.env.example fabric\deploy\config.env`.

   | Setting | What to put |
   |---|---|
   | `SUBSCRIPTION_ID` | From step 3 |
   | `RESOURCE_GROUP` | An existing resource group from step 3 |
   | `LOCATION` | The region for the capacity, for example `eastus`. Keep it close to the resource group. |
   | `CAPACITY_NAME` | Lowercase letters and digits only, unique in the subscription |
   | `CAPACITY_SKU` | `F2` unless you need more power |
   | `CAPACITY_ADMINS` | Your sign-in email, plus anyone else who should manage the capacity |
   | `WORKSPACE_NAME` | Any name, for example `DAPA Dev` |
   | `WORKSPACE_ADMINS` | Optional teammates' sign-in emails, comma-separated |
   | `SAMPLE` | Optional metro to load, a folder under `data/processed` such as `houston`. Empty deploys the skeleton with no data. Change it and re-run `up` to switch metro. |

   If the team already has a Fabric capacity, put its name in `CAPACITY_NAME` and the script reuses it.

5. **Check the plan.** This sends nothing to Azure.

   ```bash
   python3 fabric/deploy/deploy.py up --dry-run
   ```

   On Windows, use `python` instead of `python3` in this and later commands.

6. **Deploy.**

   ```bash
   python3 fabric/deploy/deploy.py up
   ```

   It prints each stage as it goes. The notebook run takes the longest because Spark has to start. At the end it prints a link to each dashboard.

7. **Open the links** and sign in with the same account. The Bank Dashboard has six pages: Overview, Opportunity Map, Community Evidence, Branch Opportunities, Pilot Results and Scenario. The Mastercard Playbook has one page. Every chart is an empty, labeled placeholder until data pipelines fill the tables.

   To see the layout without deploying anything, run `python3 fabric/tools/preview.py` from the repository root.

## Day to day

| Task | Command |
|---|---|
| Stop billing, keep everything | `python3 fabric/deploy/deploy.py pause` |
| Start again | `python3 fabric/deploy/deploy.py resume` |
| See what exists | `python3 fabric/deploy/deploy.py status` |
| Publish changes after editing files in `fabric/workspace` | `python3 fabric/deploy/deploy.py up` |

While paused, the dashboards don't load, but nothing is lost.

## Removing everything

The script never deletes anything. Do these by hand, and only when the team agrees, because they cannot be undone.

1. In Fabric, open the workspace settings and delete the workspace. This removes the data and dashboards.
2. Delete the capacity:

   ```bash
   az resource delete --ids /subscriptions/<subscription-id>/resourceGroups/<resource-group>/providers/Microsoft.Fabric/capacities/<capacity-name>
   ```

## Troubleshooting

| Symptom | Fix |
|---|---|
| `Azure CLI not found` | Install it, open a new terminal, run `az login` |
| `AuthorizationFailed` creating the capacity | You need Contributor on the resource group |
| `Capacity is active in Azure but not visible in Fabric` | Add your email to `CAPACITY_ADMINS`, then re-run `up` |
| `FeatureNotAvailable` or `Unauthorized` creating the workspace | Fabric is turned off for your organization. Ask a Fabric administrator. |
| `Notebook run Failed` | Open the workspace, open Create Tables, and look at the failed cell. Re-run `up` once it's fixed. |
| A model refresh keeps failing | Wait two minutes and re-run `up`. Sometimes the lakehouse takes a moment to show new tables. |
| Reports open but visuals show errors | Open the semantic model's settings and confirm the data source sign-in uses single sign-on with your account. Then refresh the model. |
| Maps are blank | Turn on the Azure Maps visual in tenant settings. If they are still blank, drag `latitude` and `longitude` back into the map's field wells and save. |
| `HTTP 429` messages | Fabric is throttling. The script waits and retries on its own. |

## Security notes

- **No stored credentials.** The script borrows short-lived tokens from your Azure CLI sign-in. `config.env` holds only names and IDs, and git ignores it.
- **Least privilege.** Only the people you list get capacity admin or workspace admin. Add others in Fabric with the lowest role they need, such as Viewer.
- **Data stays in your tenant.** The lakehouse, models and reports live in your organization's Fabric tenant. The script never turns on sharing outside the organization, public links or "publish to web".
- **No data yet.** The tables start empty. Before any real bank data arrives, move the Mastercard Playbook model and report into a separate workspace that receives only the aggregated table, and apply sensitivity labels.
