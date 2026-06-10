<h1 align="center">Shoppingtajm for Home Assistant</h1>

<p align="center">
  <a href="https://github.com/daniel-medin/home-assistant-shoppingtajm/releases">
    <img src="https://img.shields.io/github/v/release/daniel-medin/home-assistant-shoppingtajm?style=for-the-badge" alt="Release">
  </a>
  <a href="https://github.com/daniel-medin/home-assistant-shoppingtajm/actions/workflows/hacs.yml">
    <img src="https://img.shields.io/github/actions/workflow/status/daniel-medin/home-assistant-shoppingtajm/hacs.yml?branch=main&label=HACS&style=for-the-badge" alt="HACS Validation">
  </a>
  <a href="https://github.com/daniel-medin/home-assistant-shoppingtajm/actions/workflows/hassfest.yml">
    <img src="https://img.shields.io/github/actions/workflow/status/daniel-medin/home-assistant-shoppingtajm/hassfest.yml?branch=main&label=hassfest&style=for-the-badge" alt="Home Assistant Validation">
  </a>
  <a href="https://github.com/hacs/integration">
    <img src="https://img.shields.io/badge/HACS-Custom-orange.svg?style=for-the-badge" alt="HACS Custom">
  </a>
</p>

<!-- <p align="center">
  <img src="https://raw.githubusercontent.com/daniel-medin/home-assistant-shoppingtajm/main/custom_components/shoppingtajm/brand/logo.png" alt="Shoppingtajm logo" width="720">
</p> -->

<p align="center">
  <picture>
    <source media="(prefers-color-scheme: dark)" srcset="https://raw.githubusercontent.com/daniel-medin/home-assistant-shoppingtajm/main/custom_components/shoppingtajm/brand/logo_inverted.png">
    <source media="(prefers-color-scheme: light)" srcset="https://raw.githubusercontent.com/daniel-medin/home-assistant-shoppingtajm/main/custom_components/shoppingtajm/brand/logo.png">
    <img src="https://raw.githubusercontent.com/daniel-medin/home-assistant-shoppingtajm/main/custom_components/shoppingtajm/brand/logo.png" alt="Shoppingtajm logo" width="720">
  </picture>
</p>

Custom Home Assistant integration for [Shoppingtajm](https://shoppingtajm.se), a Swedish shopping list app.

The integration is built for HACS and uses the Shoppingtajm REST API with Personal Access Token authentication.

## Features

- UI config flow for server URL and Personal Access Token
- Push refresh from the Shoppingtajm SSE endpoint, with 60 second polling fallback through `DataUpdateCoordinator`
- Sensors for total lists, active list, remaining items, completed items, and last update time
- Event `shoppingtajm_item_added` for simple automations when an item is added to the active list
- Home Assistant services for adding, completing, deleting, and creating lists
- Custom Lovelace card for switching lists and managing items
- Cost lists are ignored; the integration only exposes grocery lists
- Diagnostics with token redaction
- Config entry migration hook
- HACS, Ruff, MyPy, HACS validation, and hassfest workflow files

## Installation Through HACS Custom Repository

1. Open HACS in Home Assistant.
2. Go to **Integrations**.
3. Choose **Custom repositories** from the menu.
4. Add:

   ```text
   https://github.com/daniel-medin/home-assistant-shoppingtajm
   ```

5. Select category **Integration**.
6. Install **Shoppingtajm**.
7. Restart Home Assistant.
8. In Home Assistant, add the **Shoppingtajm** integration from **Settings -> Devices & services -> Add integration**.

## Add Shoppingtajm

1. In Shoppingtajm, create a Personal Access Token:

   ```text
   Installningar -> Avancerade installningar -> API-nycklar
   ```

2. In Home Assistant, go to **Settings -> Devices & services -> Add integration**.
3. Search for **Shoppingtajm**.
4. Enter:

   - Server URL, for example `https://shoppingtajm.se`
   - Personal Access Token, for example `stj_...`

The config flow validates the token against `GET /api/ha/status`. After setup, the integration listens to `GET /api/ha/events` for push refresh signals and refreshes `/api/ha/status` when Shoppingtajm changes. If the SSE endpoint is unavailable or disconnected, normal 60 second polling continues as a fallback. For older Shoppingtajm servers without the status endpoint, the integration falls back to the documented list API after attempting the status endpoint.

## Entities

Sensors:

- `sensor.shoppingtajm_total_lists`
- `sensor.shoppingtajm_active_list_name`
- `sensor.shoppingtajm_remaining_items`
- `sensor.shoppingtajm_completed_items`
- `sensor.shoppingtajm_last_updated`

Button:

- `button.shoppingtajm_refresh_shopping_data`

The active list sensor also exposes `lists` and `items` attributes for the custom dashboard card. `lists` only contains grocery lists. If the active Shoppingtajm list is a cost list, the integration falls back to the first available grocery list for item reads and card actions.

The integration fires `shoppingtajm_item_added` when a new item appears in the current active list. The event data includes `list_id`, `list_name`, `item_id`, `item_name`, and `status`.

## Dashboard Card

This repository includes brand assets under `brand/` for HACS and an optional custom Lovelace card under the repository `www/` folder. HACS installs an integration-served copy of the card under `custom_components/shoppingtajm/www/`.

Register the card resource:

```text
/shoppingtajm_static/shoppingtajm-card.js?v=0.1.13
```

Use resource type:

```text
JavaScript Module
```

If you previously used `/local/shoppingtajm-card.js`, replace that dashboard resource with the `/shoppingtajm_static/...` resource above. HACS updates the integration-served card, but it does not update old manually copied files in `config/www/`.

Then add a manual dashboard card:

```yaml
type: custom:shoppingtajm-card
entity: sensor.shoppingtajm_active_list_name
```

Home Assistant can also discover the card from the dashboard card picker as **Shoppingtajm Card** after the JavaScript module resource has loaded.

The card can switch lists, add items with suggestions, rename items, edit item quantities, complete items, delete items, and read single rows aloud.
If the Shoppingtajm integration has not been added in Home Assistant yet, the card shows setup instructions instead of inactive controls.
The visual editor supports preferred language (automatic from the Home Assistant user language, Swedish, or English), background color, automatic/light/dark theme mode, opening the cart by default, icon visibility, sound on/off, stretch fullscreen, and a default list. Active items can be reordered by dragging the handle on each row; the card updates the row order locally first and shows a sync icon while Home Assistant saves the new order. On Home Assistant 2026.6 and newer, the card is suggested automatically for Shoppingtajm active-list sensor entities.

When updating the card during development, copy the changed files from `www/` to `custom_components/shoppingtajm/www/` and reload the browser. If Home Assistant keeps an old cached card, add or change a cache-busting query string on the resource, for example:

```text
/shoppingtajm_static/shoppingtajm-card.js?v=dev
```

## Services

### Add an item

```yaml
action: shoppingtajm.add_item
data:
  list_id: 123
  item_name: "Mjolk"
```

### Complete an item

```yaml
action: shoppingtajm.complete_item
data:
  list_id: 123
  item_id: 456
```

### Rename an item

```yaml
action: shoppingtajm.update_item
data:
  list_id: 123
  item_id: 456
  item_name: "Mjolk"
```

### Set item quantity

```yaml
action: shoppingtajm.set_item_quantity
data:
  list_id: 123
  item_id: 456
  quantity: 2
```

### Delete an item

```yaml
action: shoppingtajm.delete_item
data:
  list_id: 123
  item_id: 456
```

### Create a list

```yaml
action: shoppingtajm.create_list
data:
  name: "Veckohandling"
```

### Activate a list

```yaml
action: shoppingtajm.activate_list
data:
  list_id: 123
```

### Reorder items

```yaml
action: shoppingtajm.reorder_items
data:
  list_id: 123
  status: active
  item_ids:
    - 456
    - 789
```

If you configure multiple Shoppingtajm accounts, include `entry_id` in service calls. `list_id` is optional for `complete_item` and `delete_item`; when omitted, the integration uses its active grocery list.

## Automation Examples

Add coffee when the remaining item count drops to zero:

```yaml
alias: Add coffee when list is empty
triggers:
  - trigger: numeric_state
    entity_id: sensor.shoppingtajm_remaining_items
    below: 1
actions:
  - action: shoppingtajm.add_item
    data:
      list_id: 123
      item_name: "Kaffe"
```

Refresh Shoppingtajm every morning:

```yaml
alias: Refresh Shoppingtajm in the morning
triggers:
  - trigger: time
    at: "07:00:00"
actions:
  - action: button.press
    target:
      entity_id: button.shoppingtajm_refresh_shopping_data
```

Create a Friday shopping list:

```yaml
alias: Create Friday shopping list
triggers:
  - trigger: time
    at: "16:00:00"
actions:
  - action: shoppingtajm.create_list
    data:
      name: "Fredagshandling"
```

Notify once when items are added to the current active list:

```yaml
alias: Notify when Shoppingtajm groceries are added
description: ""
triggers:
  - trigger: event
    event_type: shoppingtajm_item_added
conditions: []
actions:
  - delay: "00:02:00"
  - action: notify.mobile_app_your_phone
    data:
      message: "Lista {{ trigger.event.data.list_name }} in Shoppingtajm is updated!"
mode: restart
```

Replace `notify.mobile_app_your_phone` with the notify action for your Home Assistant mobile app device. The `mode: restart` line debounces repeated additions: if more items are added during the 2 minute delay, the timer starts over and only the final notification is sent.

To test the automation, go to **Developer Tools** > **Events** and fire this event type:

```text
shoppingtajm_item_added
```

With this YAML event data:

```yaml
list_name: Groceries
item_name: Milk
item_id: test-item
list_id: test-list
status: pending
```

The `trigger.event.data.list_name` template is filled from the event data and only exists when the automation is triggered by `shoppingtajm_item_added`. If you test only the notify action manually in **Developer Tools** > **Actions**, use a fixed message instead, for example `Lista Groceries in Shoppingtajm is updated!`.

## Development

Install development dependencies:

```bash
python -m pip install -r requirements-dev.txt
```

Run local checks:

```bash
ruff check .
ruff format --check .
mypy custom_components/shoppingtajm
```

Home Assistant and HACS validation run in GitHub Actions using hassfest and `hacs/action`.
