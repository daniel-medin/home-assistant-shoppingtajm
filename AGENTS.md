# Repository Guidance

This repository contains a Home Assistant custom integration for ShoppingTajm.

## Layout

- Integration code lives in `custom_components/shoppingtajm/`.
- Home Assistant translation strings live in `custom_components/shoppingtajm/translations/en.json`.
- Service UI descriptions live in `custom_components/shoppingtajm/services.yaml`.
- HACS metadata lives in `hacs.json`.
- CI workflows live in `.github/workflows/`.

## Development Notes

- Keep the integration installable through HACS using the `custom_components/shoppingtajm` layout.
- Use async Home Assistant APIs and `aiohttp`; do not add blocking network calls.
- Keep Personal Access Tokens out of logs, diagnostics, entity attributes, and unique IDs.
- Treat list names and item names as user data.
- Prefer `DataUpdateCoordinator` for polling and refresh behavior.
- Update `README.md` when changing setup, entities, services, or automation examples.

## Local Checks

```bash
ruff check .
ruff format --check .
mypy custom_components/shoppingtajm
```

For Home Assistant manifest validation, use the hassfest GitHub Action in this repository.
