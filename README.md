<p align="center">
  <img src="https://raw.githubusercontent.com/daniel-medin/home-assistant-shoppingtajm/main/custom_components/shoppingtajm/brand/logo.png" alt="Shoppingtajm" width="640">
</p>

# Shoppingtajm for Home Assistant

Custom Home Assistant integration for [Shoppingtajm](https://shoppingtajm.se), a Swedish shopping list app.

The integration is built for HACS and uses the Shoppingtajm REST API with Personal Access Token authentication.

## Features

- UI config flow for server URL and Personal Access Token
- 60 second polling through `DataUpdateCoordinator`
- Sensors for total lists, active list, remaining items, completed items, and last update time
- Button entity to refresh Shoppingtajm data immediately
- Home Assistant services for adding, completing, deleting, and creating lists
- Custom Lovelace card for switching lists and managing items
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

The config flow validates the token against `GET /api/ha/status`. For older Shoppingtajm servers without that endpoint, the integration falls back to the documented list API after attempting the status endpoint.

## Entities

Sensors:

- `sensor.shoppingtajm_total_lists`
- `sensor.shoppingtajm_active_list_name`
- `sensor.shoppingtajm_remaining_items`
- `sensor.shoppingtajm_completed_items`
- `sensor.shoppingtajm_last_updated`

Button:

- `button.shoppingtajm_refresh_shopping_data`

The active list sensor also exposes `lists` and `items` attributes for the custom dashboard card.

## Dashboard Card

This repository includes an optional custom Lovelace card under the repository `www/` folder. The card module is `www/shoppingtajm-card.js`, with image assets in `www/shoppingtajm-icon.png`, `www/shoppingtajm-logo.png`, and `www/shoppingtajm-logo-inverted.png`.

HACS installs the integration files under `custom_components/shoppingtajm/`. The dashboard card assets currently need to be copied manually from this repository's `www/` folder into your Home Assistant `config/www/` folder:

```text
config/www/shoppingtajm-card.js
config/www/shoppingtajm-icon.png
config/www/shoppingtajm-logo.png
config/www/shoppingtajm-logo-inverted.png
```

Register the card resource:

```text
/local/shoppingtajm-card.js
```

Use resource type:

```text
JavaScript Module
```

After changing copied card files, reload the browser. If Home Assistant keeps an old cached card, update the resource URL with a cache-busting query string, for example `/local/shoppingtajm-card.js?v=20260606`.

Then add a manual dashboard card:

```yaml
type: custom:shoppingtajm-card
entity: sensor.shoppingtajm_active_list_name
```

Home Assistant can also discover the card from the dashboard card picker as **Shoppingtajm Card** after the JavaScript module resource has loaded.

The card can switch lists, add items with suggestions, rename items, edit item quantities, complete items, delete items, read single rows aloud, and refresh the active list sensor.
The visual editor supports preferred language (automatic from the Home Assistant user language, Swedish, or English), background color, automatic/light/dark theme mode, opening the cart by default, icon visibility, sound on/off, stretch fullscreen, and a default list. Active items can be reordered by dragging the handle on each row; the card updates the row order locally first and shows a sync icon while Home Assistant saves the new order. On Home Assistant 2026.6 and newer, the card is suggested automatically for Shoppingtajm active-list sensor entities.

When updating the card during development, copy the changed files from `www/` to `config/www/` and reload the browser. If Home Assistant keeps an old cached card, add or change a cache-busting query string on the resource, for example:

```text
/local/shoppingtajm-card.js?v=20260605
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

If you configure multiple Shoppingtajm accounts, include `entry_id` in service calls.

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
