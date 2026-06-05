# Shoppingtajm for Home Assistant

Custom Home Assistant integration for [Shoppingtajm](https://shoppingtajm.se), a Swedish shopping list app.

The integration is built for HACS and uses the Shoppingtajm REST API with Personal Access Token authentication.

## Features

- UI config flow for server URL and Personal Access Token
- 60 second polling through `DataUpdateCoordinator`
- Sensors for total lists, active list, remaining items, completed items, and last update time
- Button entity to refresh Shoppingtajm data immediately
- Home Assistant services for adding, completing, deleting, and creating lists
- Diagnostics with token redaction
- Config entry migration hook
- HACS, Ruff, MyPy, HACS validation, and hassfest workflow files

## Installation Through HACS

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
alias: Refresh ShoppingTajm in the morning
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
