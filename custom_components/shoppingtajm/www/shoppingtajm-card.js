const DEFAULT_BACKGROUND = "#f7f6f1";
const CARD_VERSION = "0.1.12";
const CARD_RESOURCE_URL = `/shoppingtajm_static/shoppingtajm-card.js?v=${CARD_VERSION}`;
const ICON_SRC = `/shoppingtajm_static/shoppingtajm-icon.png?v=${CARD_VERSION}-icon`;
const THEME_MODES = ["auto", "light", "dark"];
const LANGUAGE_MODES = ["auto", "sv", "en"];
const DEFAULT_LANGUAGE = "en";
const CARD_TRANSLATIONS = {
  en: {
    addItem: "Add item",
    background: "Background",
    cart: "Cart",
    chooseList: "Choose list",
    currentActiveList: "Current active list",
    defaultList: "Default list",
    deleteItem: "Delete item",
    done: "Done",
    doubleClickToEdit: "Double-click to edit",
    dragToReorder: "Drag to reorder",
    emptyActiveItems: "No active items.",
    entity: "Entity",
    language: "Language",
    languageAuto: "Automatic",
    languageEnglish: "English",
    languageSwedish: "Swedish",
    markAsDone: "Mark as done",
    milk: "Milk",
    readItem: "Read item",
    readList: "Read list",
    requiresEntity: "Shoppingtajm card requires an entity",
    setupMessage: `No Shoppingtajm active-list sensor was found. Make sure the integration is loaded. If you previously used /local/shoppingtajm-card.js, replace that dashboard resource with ${CARD_RESOURCE_URL}.`,
    setupTitle: "Shoppingtajm is not configured yet",
    showCompletedOpen: "Show completed open",
    showLogo: "Show icon",
    soundEnabled: "Sound",
    stopReading: "Stop reading",
    stretchFullscreen: "Stretch fullscreen",
    syncOrder: "Syncing order",
    theme: "Theme",
    themeAuto: "Automatic",
    themeDark: "Dark",
    themeLight: "Light",
    editQuantity: "Edit quantity",
  },
  sv: {
    addItem: "Lägg till vara",
    background: "Bakgrund",
    cart: "Kundvagn",
    chooseList: "Välj lista",
    currentActiveList: "Nuvarande aktiv lista",
    defaultList: "Standardlista",
    deleteItem: "Ta bort vara",
    done: "Klar",
    doubleClickToEdit: "Dubbelklicka för att redigera",
    dragToReorder: "Dra för att ändra ordning",
    emptyActiveItems: "Inga aktiva varor.",
    entity: "Entitet",
    language: "Språk",
    languageAuto: "Automatiskt",
    languageEnglish: "English",
    languageSwedish: "Svenska",
    markAsDone: "Markera som klar",
    milk: "Mjölk",
    readItem: "Läs vara",
    readList: "Läs listan",
    requiresEntity: "Shoppingtajm-kortet kräver en entitet",
    setupMessage: `Ingen Shoppingtajm-sensor för aktiv lista hittades. Kontrollera att integrationen är laddad. Om du tidigare använde /local/shoppingtajm-card.js, byt dashboard-resursen till ${CARD_RESOURCE_URL}.`,
    setupTitle: "Shoppingtajm är inte konfigurerat än",
    showCompletedOpen: "Visa kundvagnen öppen",
    showLogo: "Visa ikon",
    soundEnabled: "Ljud",
    stopReading: "Stoppa uppläsning",
    stretchFullscreen: "Fyll skärmen",
    syncOrder: "Synkar ordning",
    theme: "Tema",
    themeAuto: "Automatiskt",
    themeDark: "Mörkt",
    themeLight: "Ljust",
    editQuantity: "Redigera antal",
  },
};

function normalizeLanguageMode(languageMode) {
  return LANGUAGE_MODES.includes(languageMode) ? languageMode : "auto";
}

function languageFromHass(hass, preferredLanguage) {
  const languageMode = normalizeLanguageMode(preferredLanguage);
  if (languageMode !== "auto") {
    return languageMode;
  }
  const hassLanguage = String(hass?.locale?.language ?? hass?.language ?? "").toLowerCase();
  if (hassLanguage.startsWith("sv")) {
    return "sv";
  }
  if (hassLanguage.startsWith("en")) {
    return "en";
  }
  return DEFAULT_LANGUAGE;
}

function localize(language, key) {
  return CARD_TRANSLATIONS[language]?.[key] ?? CARD_TRANSLATIONS[DEFAULT_LANGUAGE][key] ?? key;
}

function isShoppingtajmCardEntity(hass, entityId) {
  const state = hass?.states?.[entityId];
  return (
    entityId?.startsWith("sensor.") &&
    entityId.includes("shoppingtajm") &&
    (entityId.includes("active_list_name") || state?.attributes?.items || state?.attributes?.lists)
  );
}

function findShoppingtajmCardEntity(hass, preferredEntityId) {
  if (isShoppingtajmCardEntity(hass, preferredEntityId)) {
    return preferredEntityId;
  }
  return (
    Object.keys(hass?.states ?? {}).find(
      (entityId) =>
        entityId.startsWith("sensor.") &&
        entityId.includes("shoppingtajm") &&
        entityId.includes("active_list_name"),
    ) ??
    Object.keys(hass?.states ?? {}).find((entityId) => isShoppingtajmCardEntity(hass, entityId))
  );
}

class ShoppingtajmCard extends HTMLElement {
  static getConfigElement() {
    return document.createElement("shoppingtajm-card-editor");
  }

  static getStubConfig(hass) {
    const entity = findShoppingtajmCardEntity(hass) ?? "sensor.shoppingtajm_active_list_name";
    return {
      entity,
      background_color: DEFAULT_BACKGROUND,
      preferred_language: "auto",
      theme_mode: "auto",
      show_completed: true,
      show_logo: true,
      sound_enabled: true,
      stretch_fullscreen: false,
    };
  }

  setConfig(config) {
    const normalizedConfig = {
      ...config,
      entity: config.entity || "sensor.shoppingtajm_active_list_name",
      preferred_language: normalizeLanguageMode(config.preferred_language),
      theme_mode: this._normalizeThemeMode(config.theme_mode, config.dark_mode),
    };
    delete normalizedConfig.dark_mode;
    this._config = {
      background_color: DEFAULT_BACKGROUND,
      preferred_language: "auto",
      theme_mode: "auto",
      show_completed: true,
      show_logo: true,
      sound_enabled: true,
      stretch_fullscreen: false,
      ...normalizedConfig,
    };
    this._busy = false;
    this._expandedCompleted = Boolean(this._config.show_completed);
    this._lastSignature = "";
    this._suggestions = [];
    this._suggestionTimer = undefined;
    this._draggedItemId = undefined;
    this._localActiveOrderIds = undefined;
    this._pendingReorderIds = undefined;
    this._reorderRequestId = 0;
    this._reorderSyncTimer = undefined;
    this._reorderSyncing = false;
    this._defaultListApplied = false;
    this._lastListId = undefined;
    this._playing = false;
    this._audio = undefined;
    this._audioResolve = undefined;
    this._editingNameItemId = undefined;
    this._editingQuantityItemId = undefined;
    this._pendingEditorFocus = undefined;
    if (!this.shadowRoot) {
      this.attachShadow({ mode: "open" });
    }
  }

  set hass(hass) {
    this._hass = hass;
    this._applyDefaultList();
    this._reconcileOptimisticOrder();
    const signature = this._stateSignature();
    if (signature !== this._lastSignature) {
      this._lastSignature = signature;
      this._render();
    }
  }

  getCardSize() {
    return 6;
  }

  _state() {
    const entityId = this._entityId();
    return entityId ? this._hass?.states?.[entityId] : undefined;
  }

  _entityId() {
    return findShoppingtajmCardEntity(this._hass, this._config.entity);
  }

  _attributes() {
    return this._state()?.attributes ?? {};
  }

  _items(status) {
    const items = (this._attributes().items ?? []).filter((item) => item.status === status);
    if (status !== "active" || !this._localActiveOrderIds?.length) {
      return items;
    }

    return this._sortItemsByOrder(items, this._localActiveOrderIds);
  }

  async _call(service, data) {
    this._busy = true;
    try {
      await this._hass.callService("shoppingtajm", service, data);
    } finally {
      this._busy = false;
    }
  }

  async _applyDefaultList() {
    const defaultListId = Number(this._config.default_list_id);
    const activeListId = Number(this._attributes().list_id);
    if (
      this._defaultListApplied ||
      !this._hass ||
      !defaultListId ||
      !activeListId ||
      defaultListId === activeListId
    ) {
      return;
    }
    this._defaultListApplied = true;
    await this._call("activate_list", { list_id: defaultListId });
  }

  async _addItem() {
    const input = this.shadowRoot.querySelector(".new-item");
    const name = input.value.trim();
    const listId = Number(this._attributes().list_id);
    if (!name || !listId) {
      return;
    }
    input.value = "";
    await this._call("add_item", { list_id: listId, item_name: name });
  }

  async _reorderItems(itemIds) {
    const listId = Number(this._attributes().list_id);
    if (!listId || itemIds.length < 2) {
      return;
    }

    const requestId = ++this._reorderRequestId;
    this._localActiveOrderIds = itemIds;
    this._pendingReorderIds = itemIds;
    this._reorderSyncing = true;
    this._setReorderTimeout(requestId);
    this._render();

    try {
      await this._hass.callService("shoppingtajm", "reorder_items", {
        list_id: listId,
        status: "active",
        item_ids: itemIds,
      });
    } catch (_err) {
      if (requestId === this._reorderRequestId) {
        this._clearOptimisticOrder();
        this._render();
      }
    }
  }

  _reconcileOptimisticOrder() {
    const activeListId = Number(this._attributes().list_id) || undefined;
    if (this._lastListId !== activeListId) {
      this._lastListId = activeListId;
      this._clearOptimisticOrder();
      return;
    }

    if (!this._pendingReorderIds?.length) {
      return;
    }

    const remoteOrderIds = this._remoteActiveOrderIds();
    if (this._sameOrder(remoteOrderIds, this._pendingReorderIds)) {
      this._clearOptimisticOrder();
      return;
    }

    this._localActiveOrderIds = this._mergeOrder(this._pendingReorderIds, remoteOrderIds);
  }

  _remoteActiveOrderIds() {
    return (this._attributes().items ?? [])
      .filter((item) => item.status === "active")
      .map((item) => Number(item.id));
  }

  _sortItemsByOrder(items, orderIds) {
    const byId = new Map(items.map((item) => [Number(item.id), item]));
    const sorted = [];
    for (const itemId of orderIds) {
      const item = byId.get(Number(itemId));
      if (item) {
        sorted.push(item);
        byId.delete(Number(itemId));
      }
    }
    sorted.push(...byId.values());
    return sorted;
  }

  _mergeOrder(preferredOrderIds, availableOrderIds) {
    const available = new Set(availableOrderIds.map((itemId) => Number(itemId)));
    const merged = preferredOrderIds
      .map((itemId) => Number(itemId))
      .filter((itemId) => available.has(itemId));

    for (const itemId of availableOrderIds) {
      const numericId = Number(itemId);
      if (!merged.includes(numericId)) {
        merged.push(numericId);
      }
    }

    return merged;
  }

  _sameOrder(first, second) {
    if (first.length !== second.length) {
      return false;
    }
    return first.every((itemId, index) => Number(itemId) === Number(second[index]));
  }

  _setReorderTimeout(requestId) {
    window.clearTimeout(this._reorderSyncTimer);
    this._reorderSyncTimer = window.setTimeout(() => {
      if (requestId === this._reorderRequestId && this._pendingReorderIds?.length) {
        this._clearOptimisticOrder();
        this._render();
      }
    }, 12000);
  }

  _clearOptimisticOrder() {
    window.clearTimeout(this._reorderSyncTimer);
    this._localActiveOrderIds = undefined;
    this._pendingReorderIds = undefined;
    this._reorderSyncing = false;
  }

  _startNameEdit(item) {
    this._editingNameItemId = Number(item.id);
    this._editingQuantityItemId = undefined;
    this._pendingEditorFocus = ".name-edit";
    this._render();
  }

  async _commitNameEdit(itemId, value) {
    if (this._editingNameItemId !== itemId) {
      return;
    }
    const listId = Number(this._attributes().list_id);
    const item = this._itemById(itemId);
    const itemName = value.trim();
    this._editingNameItemId = undefined;
    if (!listId || !item || !itemName || itemName === item.name) {
      this._render();
      return;
    }
    await this._call("update_item", { list_id: listId, item_id: itemId, item_name: itemName });
  }

  _startQuantityEdit(item) {
    this._editingQuantityItemId = Number(item.id);
    this._editingNameItemId = undefined;
    this._pendingEditorFocus = ".quantity-edit";
    this._render();
  }

  async _commitQuantityEdit(itemId, value) {
    if (this._editingQuantityItemId !== itemId) {
      return;
    }
    const listId = Number(this._attributes().list_id);
    const item = this._itemById(itemId);
    const quantity = Math.max(1, Math.min(1000, Number.parseInt(value, 10) || 1));
    const currentQuantity = Number(item?.extra_count ?? 0) + 1;
    this._editingQuantityItemId = undefined;
    if (!listId || !item || quantity === currentQuantity) {
      this._render();
      return;
    }
    await this._call("set_item_quantity", { list_id: listId, item_id: itemId, quantity });
  }

  _cancelInlineEdit() {
    this._editingNameItemId = undefined;
    this._editingQuantityItemId = undefined;
    this._render();
  }

  _itemById(itemId) {
    return (this._attributes().items ?? []).find((item) => Number(item.id) === Number(itemId));
  }

  async _readList() {
    const listId = Number(this._attributes().list_id);
    const items = this._items("active");
    if (!this._config.sound_enabled || !this._hass || !listId || !items.length || this._playing) {
      return;
    }

    this._playing = true;
    this._render();
    try {
      for (const item of items) {
        if (!this._playing) {
          break;
        }
        await this._playItemAudio(listId, Number(item.id));
      }
    } finally {
      this._playing = false;
      this._render();
    }
  }

  async _readItem(itemId) {
    const listId = Number(this._attributes().list_id);
    if (!this._config.sound_enabled || !this._hass || !listId || !itemId || this._playing) {
      return;
    }

    this._playing = true;
    this._render();
    try {
      await this._playItemAudio(listId, itemId);
    } finally {
      this._playing = false;
      this._render();
    }
  }

  _stopReading() {
    this._playing = false;
    if (this._audio) {
      this._audio.pause();
      this._audio.currentTime = 0;
    }
    if (this._audioResolve) {
      this._audioResolve();
      this._audioResolve = undefined;
    }
  }

  async _playItemAudio(listId, itemId) {
    try {
      const audio = await this._hass.callWS({
        type: "shoppingtajm/item_audio",
        list_id: listId,
        item_id: itemId,
      });
      await this._playDataAudio(audio.content_type, audio.data);
    } catch (_err) {
      // Missing item audio should not stop the whole list from being read.
    }
  }

  _playDataAudio(contentType, data) {
    return new Promise((resolve) => {
      const audio = new Audio(`data:${contentType || "audio/mpeg"};base64,${data}`);
      this._audio = audio;
      this._audioResolve = resolve;
      const cleanup = () => {
        this._audioResolve = undefined;
        resolve();
      };
      audio.addEventListener("ended", cleanup, { once: true });
      audio.addEventListener("error", cleanup, { once: true });
      audio.play().catch(cleanup);
    });
  }

  _stateSignature() {
    const attrs = this._attributes();
    return JSON.stringify({
      state: this._state()?.state,
      entity: this._entityId(),
      listId: attrs.list_id,
      lists: attrs.lists ?? [],
      items: attrs.items ?? [],
      config: {
        background_color: this._config.background_color,
        preferred_language: this._config.preferred_language,
        language: this._language(),
        theme_mode: this._config.theme_mode,
        dark_mode: this._isDarkMode(),
        show_completed: this._config.show_completed,
        show_logo: this._config.show_logo,
        sound_enabled: this._config.sound_enabled,
        stretch_fullscreen: this._config.stretch_fullscreen,
        localActiveOrderIds: this._localActiveOrderIds ?? [],
        reorderSyncing: this._reorderSyncing,
        playing: this._playing,
      },
    });
  }

  _scheduleSuggestions() {
    window.clearTimeout(this._suggestionTimer);
    const input = this.shadowRoot.querySelector(".new-item");
    const query = input.value.trim();
    this._suggestionTimer = window.setTimeout(() => {
      this._fetchSuggestions(query);
    }, 180);
  }

  async _fetchSuggestions(query) {
    const listId = Number(this._attributes().list_id);
    if (!this._hass || !listId) {
      return;
    }
    try {
      const response = await this._hass.callWS({
        type: "shoppingtajm/item_suggestions",
        query,
        list_id: listId,
      });
      this._suggestions = response.suggestions ?? [];
      this._updateSuggestions();
    } catch (_err) {
      this._suggestions = [];
      this._updateSuggestions();
    }
  }

  _updateSuggestions() {
    const list = this.shadowRoot.querySelector("#shoppingtajm-suggestions");
    if (!list) {
      return;
    }
    list.innerHTML = this._suggestions
      .map((item) => `<option value="${this._escape(item.name ?? item.Name ?? "")}"></option>`)
      .join("");
  }

  _normalizeThemeMode(themeMode, darkMode) {
    if (THEME_MODES.includes(themeMode)) {
      return themeMode;
    }
    return darkMode === true ? "dark" : "auto";
  }

  _isDarkMode() {
    const themeMode = this._normalizeThemeMode(this._config.theme_mode, this._config.dark_mode);
    if (themeMode === "dark") {
      return true;
    }
    if (themeMode === "light") {
      return false;
    }
    if (typeof this._hass?.themes?.darkMode === "boolean") {
      return this._hass.themes.darkMode;
    }
    return Boolean(this._hass?.selectedTheme?.dark);
  }

  _language() {
    return languageFromHass(this._hass, this._config.preferred_language);
  }

  _t(key) {
    return localize(this._language(), key);
  }

  _render() {
    if (!this.shadowRoot || !this._hass) {
      return;
    }

    const attrs = this._attributes();
    const hasState = Boolean(this._state());
    const lists = attrs.lists ?? [];
    const active = this._items("active");
    const completed = this._items("cart");
    const activeListId = Number(attrs.list_id);
    const activeList = lists.find((list) => Number(list.id) === activeListId);
    const stateName = this._state()?.state;
    const activeListName =
      attrs.list_name ||
      activeList?.name ||
      (stateName && !["unknown", "unavailable"].includes(stateName) ? stateName : "Shoppingtajm");
    const disabled = this._busy ? "disabled" : "";
    const darkMode = this._isDarkMode();
    const dark = darkMode ? "dark" : "";
    const stretch = this._config.stretch_fullscreen ? "stretch" : "";
    const background = this._escapeCssColor(this._config.background_color || DEFAULT_BACKGROUND);
    const t = (key) => this._t(key);

    this.shadowRoot.innerHTML = `
      <ha-card class="${dark} ${stretch}" style="--shoppingtajm-card-bg: ${background}">
        <div class="card">
          <div class="header">
            <div class="brand">
              ${
                this._config.show_logo
                  ? `<img class="app-icon" src="${ICON_SRC}" alt="Shoppingtajm">`
                  : ""
              }
              <div class="brand-copy">
                <div class="brand-kicker">Shoppingtajm</div>
                <div class="title" title="${this._escape(activeListName)}">${this._escape(activeListName)}</div>
              </div>
            </div>
            <div class="header-actions">
              ${
                hasState && this._reorderSyncing
                  ? `<span class="sync-status" title="${this._escape(t("syncOrder"))}">
                      <ha-icon icon="mdi:sync"></ha-icon>
                    </span>`
                  : ""
              }
            </div>
          </div>

          ${
            hasState
              ? `
                <div class="add-row">
                  <input class="new-item" type="text" placeholder="${this._escape(t("addItem"))}" list="shoppingtajm-suggestions" autocomplete="off" ${disabled}>
                  <datalist id="shoppingtajm-suggestions">
                    ${this._suggestions
                      .map((item) => `<option value="${this._escape(item.name ?? item.Name ?? "")}"></option>`)
                      .join("")}
                  </datalist>
                  <select class="list-picker" title="${this._escape(t("chooseList"))}" ${disabled}>
                    ${lists
                      .map(
                        (list) => `
                          <option value="${list.id}" ${Number(list.id) === activeListId ? "selected" : ""}>
                            ${this._escape(list.name)}
                          </option>
                        `,
                      )
                      .join("")}
                  </select>
                  <button class="add" title="${this._escape(t("addItem"))}" ${disabled}>
                    <ha-icon icon="mdi:plus"></ha-icon>
                  </button>
                </div>

                <div class="items active-items">
                  ${active.length ? active.map((item) => this._itemTemplate(item, false, disabled)).join("") : this._emptyActiveItems()}
                </div>

                <button class="completed-toggle" ${disabled}>
                  <ha-icon icon="${this._expandedCompleted ? "mdi:chevron-up" : "mdi:chevron-down"}"></ha-icon>
                  ${this._escape(t("cart"))}
                </button>

                <div class="items completed ${this._expandedCompleted ? "open" : ""}">
                  ${completed.map((item) => this._itemTemplate(item, true, disabled)).join("")}
                </div>
              `
              : this._setupNotice()
          }
        </div>
      </ha-card>
      <style>
        :host {
          display: block;
        }
        ha-card {
          --shoppingtajm-fullscreen-height: calc(100dvh - 96px);
          --shoppingtajm-surface: var(--shoppingtajm-card-bg);
          --shoppingtajm-text: #302c26;
          --shoppingtajm-muted: #766f64;
          --shoppingtajm-line: rgba(48, 44, 38, 0.14);
          --shoppingtajm-input: rgba(255, 255, 255, 0.72);
          --shoppingtajm-input-focus: #ffffff;
          --shoppingtajm-hover: rgba(48, 44, 38, 0.08);
          --shoppingtajm-pill: rgba(48, 44, 38, 0.08);
          --shoppingtajm-button-hover: rgba(48, 44, 38, 0.1);
          --shoppingtajm-scrollbar: rgba(48, 44, 38, 0.28);
          background: var(--shoppingtajm-surface);
          color: var(--shoppingtajm-text);
        }
        ha-card.dark {
          --shoppingtajm-surface: #171a1f;
          --shoppingtajm-text: #f6f7f2;
          --shoppingtajm-muted: #aeb6bf;
          --shoppingtajm-line: rgba(246, 247, 242, 0.14);
          --shoppingtajm-input: #232831;
          --shoppingtajm-input-focus: #2b313b;
          --shoppingtajm-hover: rgba(246, 247, 242, 0.08);
          --shoppingtajm-pill: #252b34;
          --shoppingtajm-button-hover: rgba(246, 247, 242, 0.12);
          --shoppingtajm-scrollbar: rgba(246, 247, 242, 0.28);
          box-shadow: inset 0 0 0 1px rgba(246, 247, 242, 0.08);
        }
        .card {
          padding: 16px;
        }
        ha-card.stretch {
          height: max(480px, var(--shoppingtajm-fullscreen-height));
        }
        ha-card.stretch .card {
          box-sizing: border-box;
          display: flex;
          flex-direction: column;
          height: 100%;
          min-height: 0;
        }
        ha-card.stretch .active-items {
          flex: 1 1 auto;
          min-height: 0;
          overflow-y: auto;
        }
        ha-card.stretch .completed.open {
          flex: 0 1 38%;
          min-height: 0;
          overflow-y: auto;
        }
        .header,
        .header-actions,
        .add-row,
        .item,
        .completed-toggle {
          align-items: center;
          display: flex;
          gap: 8px;
        }
        .header {
          justify-content: space-between;
          margin: -16px -16px 14px;
          padding: 16px 16px 14px;
          border-bottom: 1px solid var(--shoppingtajm-line);
        }
        .header-actions {
          flex-shrink: 0;
        }
        .brand {
          align-items: center;
          display: flex;
          gap: 12px;
          min-width: 0;
        }
        .brand-copy {
          min-width: 0;
        }
        .brand-kicker {
          color: #1c7c59;
          font-size: 13px;
          font-weight: 800;
          line-height: 1.1;
          text-transform: uppercase;
        }
        .title {
          color: #171717;
          font-size: 25px;
          font-weight: 800;
          line-height: 1.08;
          overflow: hidden;
          text-overflow: ellipsis;
          white-space: nowrap;
        }
        ha-card.dark .title {
          color: var(--shoppingtajm-text);
        }
        .app-icon {
          border-radius: 16px;
          display: block;
          flex: 0 0 auto;
          height: 58px;
          width: 58px;
        }
        .list-picker,
        .new-item {
          background: var(--shoppingtajm-input);
          border: 1px solid var(--shoppingtajm-line);
          border-radius: 6px;
          color: var(--shoppingtajm-text);
          font: inherit;
          min-height: 38px;
          min-width: 0;
          padding: 0 10px;
        }
        .list-picker:focus,
        .new-item:focus,
        .name-edit:focus,
        .quantity-edit:focus {
          background: var(--shoppingtajm-input-focus);
          border-color: var(--primary-color);
          outline: none;
        }
        .list-picker {
          flex: 0 1 170px;
        }
        .list-picker option {
          background: var(--shoppingtajm-input);
          color: var(--shoppingtajm-text);
        }
        .add-row {
          flex-wrap: wrap;
          margin-bottom: 12px;
        }
        .new-item {
          flex: 1 1 180px;
        }
        button {
          background: none;
          border: 0;
          color: var(--shoppingtajm-text);
          cursor: pointer;
          font: inherit;
        }
        button:disabled,
        input:disabled,
        select:disabled {
          cursor: progress;
          opacity: 0.58;
        }
        ha-card.dark button:disabled,
        ha-card.dark input:disabled,
        ha-card.dark select:disabled {
          opacity: 0.48;
        }
        .icon-button,
        .add,
        .delete,
        .done,
        .read-item,
        .drag-handle,
        .sync-status {
          align-items: center;
          border-radius: 50%;
          display: inline-flex;
          height: 34px;
          justify-content: center;
          width: 34px;
        }
        .sync-status {
          color: var(--primary-color);
        }
        .sync-status ha-icon {
          animation: shoppingtajm-spin 1s linear infinite;
        }
        .icon-button:hover,
        .add:hover,
        .delete:hover,
        .done:hover,
        .read-item:hover,
        .drag-handle:hover {
          background: var(--shoppingtajm-button-hover);
        }
        .item {
          border-top: 1px solid var(--shoppingtajm-line);
          min-height: 46px;
          padding: 5px 0;
        }
        .item.drag-over {
          box-shadow: inset 0 2px 0 var(--primary-color);
        }
        .drag-handle {
          color: var(--shoppingtajm-muted);
          cursor: grab;
          flex-shrink: 0;
        }
        .drag-handle:active {
          cursor: grabbing;
        }
        .name {
          flex: 1;
          min-width: 0;
          overflow-wrap: anywhere;
        }
        .name-edit {
          flex: 1;
          min-width: 0;
        }
        .name-edit,
        .quantity-edit {
          background: var(--shoppingtajm-input);
          border: 1px solid var(--shoppingtajm-line);
          border-radius: 6px;
          color: var(--shoppingtajm-text);
          font: inherit;
          min-height: 34px;
          padding: 0 8px;
        }
        .quantity-pill {
          background: var(--shoppingtajm-pill);
          border: 1px solid var(--shoppingtajm-line);
          border-radius: 999px;
          color: var(--shoppingtajm-muted);
          flex-shrink: 0;
          font-size: 12px;
          line-height: 1;
          min-width: 34px;
          padding: 5px 8px;
        }
        .quantity-edit {
          flex-shrink: 0;
          text-align: center;
          width: 64px;
        }
        .actions {
          align-items: center;
          display: flex;
          flex-shrink: 0;
          gap: 4px;
          margin-left: auto;
        }
        .completed .name {
          color: var(--shoppingtajm-muted);
          text-decoration: line-through;
        }
        .completed-toggle {
          color: var(--shoppingtajm-muted);
          justify-content: center;
          margin-top: 8px;
          min-height: 36px;
          width: 100%;
        }
        .completed {
          display: none;
        }
        .completed.open {
          display: block;
        }
        .items {
          scrollbar-color: var(--shoppingtajm-scrollbar) transparent;
        }
        .empty {
          border-top: 1px solid var(--shoppingtajm-line);
          color: var(--shoppingtajm-muted);
          padding: 14px 0;
          text-align: center;
        }
        .setup-notice {
          align-items: flex-start;
          background: var(--shoppingtajm-input);
          border: 1px solid var(--shoppingtajm-line);
          border-radius: 8px;
          display: flex;
          gap: 12px;
          padding: 14px;
        }
        .setup-notice ha-icon {
          color: #d97706;
          flex: 0 0 auto;
          margin-top: 2px;
        }
        .setup-copy {
          display: grid;
          gap: 6px;
        }
        .setup-title {
          font-weight: 800;
        }
        .setup-message {
          color: var(--shoppingtajm-muted);
          font-size: 14px;
          line-height: 1.45;
        }
        .setup-debug {
          color: var(--shoppingtajm-muted);
          font-size: 12px;
          line-height: 1.4;
          opacity: 0.82;
        }
        @keyframes shoppingtajm-spin {
          from {
            transform: rotate(0deg);
          }
          to {
            transform: rotate(360deg);
          }
        }
      </style>
    `;

    this._bindEvents();
  }

  _bindEvents() {
    this.shadowRoot.querySelector(".list-picker")?.addEventListener("change", (event) => {
      this._defaultListApplied = true;
      this._call("activate_list", { list_id: Number(event.target.value) });
    });
    this.shadowRoot.querySelector(".add")?.addEventListener("click", () => this._addItem());
    this.shadowRoot.querySelector(".new-item")?.addEventListener("keydown", (event) => {
      if (event.key === "Enter") {
        this._addItem();
      }
    });
    this.shadowRoot.querySelector(".new-item")?.addEventListener("input", () => {
      this._scheduleSuggestions();
    });
    this.shadowRoot.querySelector(".completed-toggle")?.addEventListener("click", () => {
      this._expandedCompleted = !this._expandedCompleted;
      this._render();
    });
    this.shadowRoot.querySelectorAll("[data-complete]").forEach((button) => {
      button.addEventListener("click", () => {
        const listId = Number(this._attributes().list_id);
        const payload = { item_id: Number(button.dataset.complete) };
        if (listId) {
          payload.list_id = listId;
        }
        this._call("complete_item", payload);
      });
    });
    this.shadowRoot.querySelectorAll("[data-delete]").forEach((button) => {
      button.addEventListener("click", () => {
        const listId = Number(this._attributes().list_id);
        const payload = { item_id: Number(button.dataset.delete) };
        if (listId) {
          payload.list_id = listId;
        }
        this._call("delete_item", payload);
      });
    });
    this.shadowRoot.querySelectorAll("[data-read-item]").forEach((button) => {
      button.addEventListener("click", () => {
        this._readItem(Number(button.dataset.readItem));
      });
    });
    this.shadowRoot.querySelectorAll("[data-edit-name]").forEach((name) => {
      name.addEventListener("dblclick", () => {
        const item = this._itemById(Number(name.dataset.editName));
        if (item) {
          this._startNameEdit(item);
        }
      });
    });
    this.shadowRoot.querySelectorAll(".name-edit").forEach((input) => {
      input.addEventListener("keydown", (event) => {
        if (event.key === "Enter") {
          event.preventDefault();
          input.blur();
        }
        if (event.key === "Escape") {
          event.preventDefault();
          this._cancelInlineEdit();
        }
      });
      input.addEventListener("blur", () => {
        this._commitNameEdit(Number(input.dataset.itemId), input.value);
      });
    });
    this.shadowRoot.querySelectorAll("[data-edit-quantity]").forEach((button) => {
      button.addEventListener("click", () => {
        const item = this._itemById(Number(button.dataset.editQuantity));
        if (item) {
          this._startQuantityEdit(item);
        }
      });
    });
    this.shadowRoot.querySelectorAll(".quantity-edit").forEach((input) => {
      input.addEventListener("keydown", (event) => {
        if (event.key === "Enter") {
          event.preventDefault();
          input.blur();
        }
        if (event.key === "Escape") {
          event.preventDefault();
          this._cancelInlineEdit();
        }
      });
      input.addEventListener("blur", () => {
        this._commitQuantityEdit(Number(input.dataset.itemId), input.value);
      });
    });
    this.shadowRoot.querySelectorAll(".active-items .item").forEach((row) => {
      row.addEventListener("dragstart", (event) => {
        this._draggedItemId = Number(row.dataset.itemId);
        event.dataTransfer.effectAllowed = "move";
        event.dataTransfer.setData("text/plain", String(this._draggedItemId));
      });
      row.addEventListener("dragover", (event) => {
        event.preventDefault();
        row.classList.add("drag-over");
      });
      row.addEventListener("dragleave", () => row.classList.remove("drag-over"));
      row.addEventListener("drop", (event) => {
        event.preventDefault();
        row.classList.remove("drag-over");
        this._handleDrop(Number(row.dataset.itemId));
      });
      row.addEventListener("dragend", () => {
        this.shadowRoot.querySelectorAll(".drag-over").forEach((item) => item.classList.remove("drag-over"));
      });
    });
    this._focusPendingEditor();
  }

  _handleDrop(targetItemId) {
    const sourceItemId = Number(this._draggedItemId);
    if (!sourceItemId || !targetItemId || sourceItemId === targetItemId) {
      return;
    }
    const itemIds = this._items("active").map((item) => Number(item.id));
    const sourceIndex = itemIds.indexOf(sourceItemId);
    const targetIndex = itemIds.indexOf(targetItemId);
    if (sourceIndex < 0 || targetIndex < 0) {
      return;
    }
    itemIds.splice(sourceIndex, 1);
    itemIds.splice(targetIndex, 0, sourceItemId);
    this._reorderItems(itemIds);
  }

  _itemTemplate(item, completed, disabled) {
    const quantity = Number(item.extra_count ?? 0) + 1;
    const itemId = Number(item.id);
    const editingName = this._editingNameItemId === itemId;
    const editingQuantity = this._editingQuantityItemId === itemId;
    const draggable = completed || editingName || editingQuantity ? "" : "draggable=\"true\"";
    const t = (key) => this._t(key);
    const name = editingName
      ? `<input class="name-edit" data-item-id="${item.id}" value="${this._escape(item.name)}" ${disabled}>`
      : `<div class="name" data-edit-name="${item.id}" title="${this._escape(t("doubleClickToEdit"))}">${this._escape(item.name)}</div>`;
    const quantityControl = editingQuantity
      ? `<input class="quantity-edit" data-item-id="${item.id}" type="number" min="1" max="1000" value="${quantity}" ${disabled}>`
      : `<button class="quantity-pill" data-edit-quantity="${item.id}" title="${this._escape(t("editQuantity"))}" ${disabled}>${quantity}</button>`;
    const readControl = this._config.sound_enabled
      ? `<button class="read-item" data-read-item="${item.id}" title="${this._escape(t("readItem"))}" ${disabled || (this._playing ? "disabled" : "")}>
          <ha-icon icon="mdi:bullhorn"></ha-icon>
        </button>`
      : "";
    return `
      <div class="item" data-item-id="${item.id}" ${draggable}>
        ${
          completed
            ? `<span class="drag-handle" title="${this._escape(t("done"))}"><ha-icon icon="mdi:check"></ha-icon></span>`
            : `<button class="drag-handle" title="${this._escape(t("dragToReorder"))}" ${disabled}>
                <ha-icon icon="mdi:drag"></ha-icon>
              </button>`
        }
        ${name}
        <div class="actions">
          ${quantityControl}
          ${readControl}
          ${
            completed
              ? ""
              : `<button class="done" data-complete="${item.id}" title="${this._escape(t("markAsDone"))}" ${disabled}>
                  <ha-icon icon="mdi:check"></ha-icon>
                </button>`
          }
          <button class="delete" data-delete="${item.id}" title="${this._escape(t("deleteItem"))}" ${disabled}>
            <ha-icon icon="mdi:delete-outline"></ha-icon>
          </button>
        </div>
      </div>
    `;
  }

  _focusPendingEditor() {
    if (!this._pendingEditorFocus) {
      return;
    }
    const selector = this._pendingEditorFocus;
    this._pendingEditorFocus = undefined;
    window.requestAnimationFrame(() => {
      const input = this.shadowRoot?.querySelector(selector);
      input?.focus();
      input?.select();
    });
  }

  _emptyActiveItems() {
    const t = (key) => this._t(key);
    return `<div class="empty">${this._escape(t("emptyActiveItems"))}</div>`;
  }

  _setupNotice() {
    const t = (key) => this._t(key);
    const entityId = this._entityId() ?? this._config.entity ?? "auto";
    return `
      <div class="setup-notice">
        <ha-icon icon="mdi:alert-circle-outline"></ha-icon>
        <div class="setup-copy">
          <div class="setup-title">${this._escape(t("setupTitle"))}</div>
          <div class="setup-message">${this._escape(t("setupMessage"))}</div>
          <div class="setup-debug">Card ${this._escape(CARD_VERSION)} · ${this._escape(entityId)}</div>
        </div>
      </div>
    `;
  }

  _escape(value) {
    return String(value ?? "")
      .replaceAll("&", "&amp;")
      .replaceAll("<", "&lt;")
      .replaceAll(">", "&gt;")
      .replaceAll('"', "&quot;")
      .replaceAll("'", "&#039;");
  }

  _escapeCssColor(value) {
    const color = String(value ?? "").trim();
    return /^#[0-9a-f]{3}([0-9a-f]{3})?$/i.test(color) ? color : DEFAULT_BACKGROUND;
  }
}

class ShoppingtajmCardEditor extends HTMLElement {
  setConfig(config) {
    const normalizedConfig = {
      ...config,
      preferred_language: normalizeLanguageMode(config.preferred_language),
      theme_mode: this._normalizeThemeMode(config.theme_mode, config.dark_mode),
    };
    delete normalizedConfig.dark_mode;
    this._config = {
      background_color: DEFAULT_BACKGROUND,
      preferred_language: "auto",
      theme_mode: "auto",
      show_completed: true,
      show_logo: true,
      sound_enabled: true,
      stretch_fullscreen: false,
      ...normalizedConfig,
    };
    if (!this.shadowRoot) {
      this.attachShadow({ mode: "open" });
    }
    this._render();
  }

  set hass(hass) {
    this._hass = hass;
    this._render();
  }

  _state() {
    const entityId = findShoppingtajmCardEntity(this._hass, this._config?.entity);
    return entityId ? this._hass?.states?.[entityId] : undefined;
  }

  _lists() {
    return this._state()?.attributes?.lists ?? [];
  }

  _updateConfig(patch) {
    this._config = { ...this._config, ...patch };
    this.dispatchEvent(
      new CustomEvent("config-changed", {
        detail: { config: this._config },
        bubbles: true,
        composed: true,
      }),
    );
    this._render();
  }

  _normalizeThemeMode(themeMode, darkMode) {
    if (THEME_MODES.includes(themeMode)) {
      return themeMode;
    }
    return darkMode === true ? "dark" : "auto";
  }

  _language() {
    return languageFromHass(this._hass, this._config.preferred_language);
  }

  _t(key) {
    return localize(this._language(), key);
  }

  _render() {
    if (!this.shadowRoot || !this._config) {
      return;
    }
    const lists = this._lists();
    const themeMode = this._normalizeThemeMode(this._config.theme_mode, this._config.dark_mode);
    const languageMode = normalizeLanguageMode(this._config.preferred_language);
    const t = (key) => this._t(key);
    this.shadowRoot.innerHTML = `
      <div class="editor">
        <label>
          <span>${this._escape(t("entity"))}</span>
          <input class="entity" value="${this._escape(this._config.entity ?? "")}">
        </label>
        <label>
          <span>${this._escape(t("defaultList"))}</span>
          <select class="default-list">
            <option value="">${this._escape(t("currentActiveList"))}</option>
            ${lists
              .map(
                (list) => `
                  <option value="${list.id}" ${String(this._config.default_list_id ?? "") === String(list.id) ? "selected" : ""}>
                    ${this._escape(list.name)}
                  </option>
                `,
              )
              .join("")}
          </select>
        </label>
        <label>
          <span>${this._escape(t("background"))}</span>
          <input class="background" type="color" value="${this._escape(this._config.background_color ?? DEFAULT_BACKGROUND)}">
        </label>
        <label>
          <span>${this._escape(t("language"))}</span>
          <select class="preferred-language">
            <option value="auto" ${languageMode === "auto" ? "selected" : ""}>${this._escape(t("languageAuto"))}</option>
            <option value="sv" ${languageMode === "sv" ? "selected" : ""}>${this._escape(t("languageSwedish"))}</option>
            <option value="en" ${languageMode === "en" ? "selected" : ""}>${this._escape(t("languageEnglish"))}</option>
          </select>
        </label>
        <fieldset class="theme-options">
          <legend>${this._escape(t("theme"))}</legend>
          <label class="radio">
            <input class="theme-mode" type="radio" name="theme-mode" value="auto" ${themeMode === "auto" ? "checked" : ""}>
            <span>${this._escape(t("themeAuto"))}</span>
          </label>
          <label class="radio">
            <input class="theme-mode" type="radio" name="theme-mode" value="light" ${themeMode === "light" ? "checked" : ""}>
            <span>${this._escape(t("themeLight"))}</span>
          </label>
          <label class="radio">
            <input class="theme-mode" type="radio" name="theme-mode" value="dark" ${themeMode === "dark" ? "checked" : ""}>
            <span>${this._escape(t("themeDark"))}</span>
          </label>
        </fieldset>
        <label class="toggle">
          <span>${this._escape(t("showCompletedOpen"))}</span>
          <input class="show-completed" type="checkbox" ${this._config.show_completed ? "checked" : ""}>
        </label>
        <label class="toggle">
          <span>${this._escape(t("showLogo"))}</span>
          <input class="show-logo" type="checkbox" ${this._config.show_logo ? "checked" : ""}>
        </label>
        <label class="toggle">
          <span>${this._escape(t("soundEnabled"))}</span>
          <input class="sound-enabled" type="checkbox" ${this._config.sound_enabled ? "checked" : ""}>
        </label>
        <label class="toggle">
          <span>${this._escape(t("stretchFullscreen"))}</span>
          <input class="stretch-fullscreen" type="checkbox" ${this._config.stretch_fullscreen ? "checked" : ""}>
        </label>
      </div>
      <style>
        .editor {
          display: grid;
          gap: 14px;
          padding: 12px;
        }
        label {
          display: grid;
          gap: 6px;
        }
        .toggle {
          align-items: center;
          display: flex;
          justify-content: space-between;
        }
        .theme-options {
          border: 0;
          display: grid;
          gap: 8px;
          margin: 0;
          padding: 0;
        }
        legend {
          color: var(--secondary-text-color);
          font-size: 12px;
          padding: 0;
        }
        .radio {
          align-items: center;
          display: flex;
          gap: 8px;
        }
        .radio input {
          min-height: auto;
          padding: 0;
        }
        span {
          color: var(--secondary-text-color);
          font-size: 12px;
        }
        input,
        select {
          background: var(--card-background-color);
          border: 1px solid var(--divider-color);
          border-radius: 6px;
          color: var(--primary-text-color);
          font: inherit;
          min-height: 36px;
          padding: 0 8px;
        }
        input[type="color"] {
          padding: 2px;
        }
      </style>
    `;

    this.shadowRoot.querySelector(".entity")?.addEventListener("change", (event) => {
      this._updateConfig({ entity: event.target.value.trim() });
    });
    this.shadowRoot.querySelector(".default-list")?.addEventListener("change", (event) => {
      const value = event.target.value;
      this._updateConfig({ default_list_id: value ? Number(value) : undefined });
    });
    this.shadowRoot.querySelector(".background")?.addEventListener("input", (event) => {
      this._updateConfig({ background_color: event.target.value });
    });
    this.shadowRoot.querySelector(".preferred-language")?.addEventListener("change", (event) => {
      this._updateConfig({ preferred_language: normalizeLanguageMode(event.target.value) });
    });
    this.shadowRoot.querySelectorAll(".theme-mode").forEach((input) => {
      input.addEventListener("change", (event) => {
        if (event.target.checked) {
          this._updateConfig({ theme_mode: event.target.value });
        }
      });
    });
    this.shadowRoot.querySelector(".show-completed")?.addEventListener("change", (event) => {
      this._updateConfig({ show_completed: event.target.checked });
    });
    this.shadowRoot.querySelector(".show-logo")?.addEventListener("change", (event) => {
      this._updateConfig({ show_logo: event.target.checked });
    });
    this.shadowRoot.querySelector(".sound-enabled")?.addEventListener("change", (event) => {
      this._updateConfig({ sound_enabled: event.target.checked });
    });
    this.shadowRoot.querySelector(".stretch-fullscreen")?.addEventListener("change", (event) => {
      this._updateConfig({ stretch_fullscreen: event.target.checked });
    });
  }

  _escape(value) {
    return String(value ?? "")
      .replaceAll("&", "&amp;")
      .replaceAll("<", "&lt;")
      .replaceAll(">", "&gt;")
      .replaceAll('"', "&quot;")
      .replaceAll("'", "&#039;");
  }
}

customElements.define("shoppingtajm-card", ShoppingtajmCard);
customElements.define("shoppingtajm-card-editor", ShoppingtajmCardEditor);

window.customCards = window.customCards || [];
window.customCards.push({
  type: "shoppingtajm-card",
  name: "Shoppingtajm Card",
  description: "Manage Shoppingtajm lists and items.",
  documentationURL: "https://github.com/daniel-medin/home-assistant-shoppingtajm",
  image: ICON_SRC,
  logo: ICON_SRC,
  preview: true,
  getEntitySuggestion: (hass, entityId) => {
    if (!isShoppingtajmCardEntity(hass, entityId)) {
      return null;
    }
    return {
      config: {
        type: "custom:shoppingtajm-card",
        entity: entityId,
        preferred_language: "auto",
        theme_mode: "auto",
      },
    };
  },
});
