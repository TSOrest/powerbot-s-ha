# Samsung POWERbot-S for Home Assistant

[![hacs_badge](https://img.shields.io/badge/HACS-Custom-orange.svg)](https://github.com/hacs/integration)
[![GitHub release](https://img.shields.io/github/release/TSOrest/powerbot-s-ha.svg)](https://github.com/TSOrest/powerbot-s-ha/releases)

> **[Українська версія нижче](#українська)**

---

## English

Custom Home Assistant integration for the **Samsung VR7700 (POWERbot-S)** robot vacuum cleaner, using the reverse-engineered **mzrobo.com** cloud API.

### Features

| Entity | Type | Description |
|--------|------|-------------|
| Vacuum | `vacuum` | Start, stop, pause, return to dock, spot clean, fan speed |
| Status | `sensor` | Raw state string from cloud (`cleaning`, `charging_finish`, …) |
| Battery | `sensor` | Battery level (%) |
| Fan Speed | `sensor` | Current suction level (quiet / normal / strong) |
| Connection | `sensor` | online / offline |
| Error | `binary_sensor` | `on` when robot reports an error |
| Cleaning | `binary_sensor` | `on` when actively cleaning |
| Docked | `binary_sensor` | `on` when in charging dock |
| Online | `binary_sensor` | `on` when cloud API is reachable |

### Requirements

- Home Assistant **2024.1** or newer
- An account in the **POWERbot-S** Android/iOS app
- Your robot's **Device ID** (see below)

### Installation via HACS

1. Open HACS → Integrations → **Custom repositories**
2. Add `https://github.com/TSOrest/powerbot-s-ha` as type **Integration**
3. Find **Samsung POWERbot-S** and click **Download**
4. Restart Home Assistant
5. Go to **Settings → Devices & Services → Add Integration → Samsung POWERbot-S**

### Manual Installation

1. Copy the `custom_components/powerbot_s/` folder to your HA `config/custom_components/` directory
2. Restart Home Assistant
3. Add the integration via the UI

### Finding Your Device ID

1. Open the **POWERbot-S** app
2. Go to the robot's **Settings → Device Info**
3. The Device ID is a long number like `1870169732145270786`

Alternatively, enable debug logging and look in the HA logs:
```yaml
logger:
  default: warning
  logs:
    custom_components.powerbot_s: debug
```

### Important Notes

- **Map display is not supported.** The mzrobo.com REST API does not expose any map or cleaning-history endpoints. This is a cloud API limitation, not a bug in this integration.
- **Hex commands** are reverse-engineered from APK v1.2.1. If commands don't work on your firmware, capture traffic with [mitmproxy](https://mitmproxy.org/) and open an issue.
- The robot is controlled via the **cloud** (no local network control available).

### Automation Example

```yaml
automation:
  - alias: "Start cleaning at 9 AM on weekdays"
    trigger:
      - platform: time
        at: "09:00:00"
    condition:
      - condition: time
        weekday: [mon, tue, wed, thu, fri]
    action:
      - service: vacuum.start
        target:
          entity_id: vacuum.samsung_powerbot_s
```

---

## Українська

Інтеграція Home Assistant для **Samsung VR7700 (POWERbot-S)**, яка використовує хмарне API **mzrobo.com** (реверс-інженерія з APK).

### Що вміє інтеграція

| Сутність | Тип | Опис |
|----------|-----|------|
| Пилосос | `vacuum` | Старт, стоп, пауза, повернення на базу, точкове прибирання, потужність всмоктування |
| Статус | `sensor` | Сирий стан з хмари (`cleaning`, `charging_finish`, …) |
| Батарея | `sensor` | Заряд батареї (%) |
| Швидкість вентилятора | `sensor` | Поточна потужність (тихо / нормально / потужно) |
| З'єднання | `sensor` | online / offline |
| Помилка | `binary_sensor` | `on` коли робот повідомляє про помилку |
| Прибирання | `binary_sensor` | `on` коли активно прибирає |
| На базі | `binary_sensor` | `on` коли стоїть на зарядці |
| Онлайн | `binary_sensor` | `on` коли хмарне API доступне |

### Встановлення через HACS

1. HACS → Інтеграції → **Користувацькі репозиторії**
2. Додати `https://github.com/TSOrest/powerbot-s-ha` з типом **Інтеграція**
3. Знайти **Samsung POWERbot-S** → **Завантажити**
4. Перезавантажити Home Assistant
5. **Налаштування → Пристрої та служби → Додати інтеграцію → Samsung POWERbot-S**

### Де знайти Device ID

1. Відкрийте додаток **POWERbot-S**
2. Налаштування пристрою → **Інформація про пристрій**
3. Device ID — це довгий номер, наприклад: `1870169732145270786`

### Важливо

- **Карта прибирання не підтримується** — API mzrobo.com не надає доступу до карт чи історії прибирання.
- Керування роботом відбувається **через хмару**, локального API немає.

---

## License

MIT © 2024 [TSOrest](https://github.com/TSOrest)
