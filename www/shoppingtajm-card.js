class ShoppingTajmCard extends HTMLElement {
  static getStubConfig() {
    return { entity: "sensor.shoppingtajm_active_list_name" };
  }

  setConfig(config) {
    if (!config.entity) {
      throw new Error("ShoppingTajm card requires an entity");
    }
    this._config = config;
    this._busy = false;
    this._expandedCompleted = false;
    this.attachShadow({ mode: "open" });
  }

  set hass(hass) {
    this._hass = hass;
    this._render();
  }

  getCardSize() {
    return 5;
  }

  _state() {
    return this._hass?.states?.[this._config.entity];
  }

  _attributes() {
    return this._state()?.attributes ?? {};
  }

  _items(status) {
    return (this._attributes().items ?? []).filter((item) => item.status === status);
  }

  async _call(service, data) {
    this._busy = true;
    this._render();
    try {
      await this._hass.callService("shoppingtajm", service, data);
    } finally {
      this._busy = false;
      this._render();
    }
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

  _render() {
    if (!this.shadowRoot || !this._hass) {
      return;
    }

    const state = this._state();
    const attrs = this._attributes();
    const lists = attrs.lists ?? [];
    const active = this._items("active");
    const completed = this._items("cart");
    const activeListId = Number(attrs.list_id);
    const disabled = this._busy ? "disabled" : "";

    this.shadowRoot.innerHTML = `
      <ha-card>
        <div class="card">
          <div class="header">
            <div>
              <div class="title">ShoppingTajm</div>
              <div class="subtitle">${this._escape(state?.state ?? "Unavailable")}</div>
            </div>
            <button class="icon-button refresh" title="Refresh" ${disabled}>
              <ha-icon icon="mdi:refresh"></ha-icon>
            </button>
          </div>

          <div class="controls">
            <select class="list-picker" ${disabled}>
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
            <div class="counts">
              <span>${active.length} kvar</span>
              <span>${completed.length} klara</span>
            </div>
          </div>

          <div class="add-row">
            <input class="new-item" type="text" placeholder="Lagg till vara" ${disabled}>
            <button class="add" title="Add item" ${disabled}>
              <ha-icon icon="mdi:plus"></ha-icon>
            </button>
          </div>

          <div class="items">
            ${
              active.length
                ? active.map((item) => this._itemTemplate(item, false, disabled)).join("")
                : `<div class="empty">Inga aktiva varor.</div>`
            }
          </div>

          <button class="completed-toggle" ${disabled}>
            <ha-icon icon="${this._expandedCompleted ? "mdi:chevron-up" : "mdi:chevron-down"}"></ha-icon>
            Klara varor
          </button>

          <div class="items completed ${this._expandedCompleted ? "open" : ""}">
            ${completed.map((item) => this._itemTemplate(item, true, disabled)).join("")}
          </div>
        </div>
      </ha-card>
      <style>
        :host {
          display: block;
        }
        .card {
          padding: 16px;
        }
        .header,
        .controls,
        .add-row,
        .item,
        .completed-toggle {
          align-items: center;
          display: flex;
          gap: 8px;
        }
        .header {
          justify-content: space-between;
          margin-bottom: 14px;
        }
        .title {
          color: var(--primary-text-color);
          font-size: 20px;
          font-weight: 600;
          line-height: 1.2;
        }
        .subtitle {
          color: var(--secondary-text-color);
          font-size: 13px;
          margin-top: 2px;
        }
        .controls {
          justify-content: space-between;
          margin-bottom: 10px;
        }
        .list-picker,
        .new-item {
          background: var(--card-background-color);
          border: 1px solid var(--divider-color);
          border-radius: 6px;
          color: var(--primary-text-color);
          font: inherit;
          min-height: 38px;
          min-width: 0;
          padding: 0 10px;
        }
        .list-picker {
          flex: 1;
        }
        .counts {
          color: var(--secondary-text-color);
          display: flex;
          flex-shrink: 0;
          font-size: 12px;
          gap: 8px;
        }
        .add-row {
          margin-bottom: 12px;
        }
        .new-item {
          flex: 1;
        }
        button {
          background: none;
          border: 0;
          color: var(--primary-text-color);
          cursor: pointer;
          font: inherit;
        }
        button:disabled,
        input:disabled,
        select:disabled {
          cursor: progress;
          opacity: 0.6;
        }
        .icon-button,
        .add,
        .delete {
          align-items: center;
          border-radius: 50%;
          display: inline-flex;
          height: 36px;
          justify-content: center;
          width: 36px;
        }
        .icon-button:hover,
        .add:hover,
        .delete:hover,
        .checkbox:hover {
          background: var(--secondary-background-color);
        }
        .item {
          border-top: 1px solid var(--divider-color);
          min-height: 42px;
          padding: 4px 0;
        }
        .checkbox {
          align-items: center;
          border: 1px solid var(--divider-color);
          border-radius: 50%;
          display: inline-flex;
          flex-shrink: 0;
          height: 28px;
          justify-content: center;
          width: 28px;
        }
        .name {
          flex: 1;
          min-width: 0;
          overflow-wrap: anywhere;
        }
        .extra {
          color: var(--secondary-text-color);
          font-size: 12px;
          margin-left: 6px;
        }
        .completed .name {
          color: var(--secondary-text-color);
          text-decoration: line-through;
        }
        .completed-toggle {
          color: var(--secondary-text-color);
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
        .empty {
          border-top: 1px solid var(--divider-color);
          color: var(--secondary-text-color);
          padding: 14px 0;
          text-align: center;
        }
      </style>
    `;

    this.shadowRoot.querySelector(".refresh")?.addEventListener("click", () => {
      this._hass.callService("homeassistant", "update_entity", {
        entity_id: this._config.entity,
      });
    });
    this.shadowRoot.querySelector(".list-picker")?.addEventListener("change", (event) => {
      this._call("activate_list", { list_id: Number(event.target.value) });
    });
    this.shadowRoot.querySelector(".add")?.addEventListener("click", () => this._addItem());
    this.shadowRoot.querySelector(".new-item")?.addEventListener("keydown", (event) => {
      if (event.key === "Enter") {
        this._addItem();
      }
    });
    this.shadowRoot.querySelector(".completed-toggle")?.addEventListener("click", () => {
      this._expandedCompleted = !this._expandedCompleted;
      this._render();
    });
    this.shadowRoot.querySelectorAll("[data-complete]").forEach((button) => {
      button.addEventListener("click", () => {
        this._call("complete_item", { item_id: Number(button.dataset.complete) });
      });
    });
    this.shadowRoot.querySelectorAll("[data-delete]").forEach((button) => {
      button.addEventListener("click", () => {
        this._call("delete_item", { item_id: Number(button.dataset.delete) });
      });
    });
  }

  _itemTemplate(item, completed, disabled) {
    const icon = completed ? "mdi:check" : "mdi:cart-check";
    const extra = item.extra_count ? `<span class="extra">x${item.extra_count + 1}</span>` : "";
    return `
      <div class="item">
        <button class="checkbox" data-complete="${item.id}" title="Complete item" ${disabled}>
          <ha-icon icon="${icon}"></ha-icon>
        </button>
        <div class="name">${this._escape(item.name)}${extra}</div>
        <button class="delete" data-delete="${item.id}" title="Delete item" ${disabled}>
          <ha-icon icon="mdi:delete-outline"></ha-icon>
        </button>
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
}

customElements.define("shoppingtajm-card", ShoppingTajmCard);

window.customCards = window.customCards || [];
window.customCards.push({
  type: "shoppingtajm-card",
  name: "ShoppingTajm Card",
  description: "Manage ShoppingTajm lists and items.",
});
