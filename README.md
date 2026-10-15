# Samsung POWERbot-S for Home Assistant

[![HACS](https://img.shields.io/badge/HACS-Custom-41BDF5.svg?style=for-the-badge&logo=homeassistantcommunitystore&logoColor=white)](https://github.com/hacs/integration)
[![Validate](https://github.com/TSOrest/powerbot-s-ha/actions/workflows/validate.yml/badge.svg)](https://github.com/TSOrest/powerbot-s-ha/actions/workflows/validate.yml)
[![GitHub Release](https://img.shields.io/github/release/TSOrest/powerbot-s-ha.svg?style=for-the-badge&color=blue)](https://github.com/TSOrest/powerbot-s-ha/releases)
[![Built with Claude AI](https://img.shields.io/badge/Built_with-Claude_AI-FF6B35?style=for-the-badge)](https://anthropic.com)

[![Open your Home Assistant instance and open a repository inside the Home Assistant Community Store.](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=TSOrest&repository=powerbot-s-ha&category=integration)

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

---

## Українська

Інтеграція для Home Assistant для **Samsung VR7700 (POWERbot-S)** (робот-пилосос), що використовує реверс-інженерований хмарний API **mzrobo.com**.

### Можливості

| Сутність | Тип | Опис |
|----------|-----|------|
| Vacuum | `vacuum` | Старт, стоп, пауза, на базу, точкове прибирання, швидкість вентилятора |
| Status | `sensor` | Рядок стану з хмари (`cleaning`, `charging_finish`, …) |
| Battery | `sensor` | Рівень заряду (%) |
| Fan Speed | `sensor` | Поточний рівень всмоктування (тихий / нормальний / сильний) |
| Connection | `sensor` | онлайн / офлайн |
| Error | `binary_sensor` | `on` коли робот повідомляє про помилку |
| Cleaning | `binary_sensor` | `on` під час активного прибирання |
| Docked | `binary_sensor` | `on` коли на зарядній станції |
| Online | `binary_sensor` | `on` коли хмарний API доступний |

### Вимоги

- Home Assistant **2024.1** або новішийей
- �C౽іковий запис у додатку **POWERbot-S** для Android/iOS
- **Device ID** вашого робота (дивіться нижче)

### Встановлення через HACS

1. Відкрийте HACS → Інтеграції → **Користувацькі репозиторії**
2. Додайте `https://github.com/TSOrest/powerbot-s-ha` як тип **Integration**
3. Знайдіть **Samsung POWERbot-S** та натисніть **Завантажити**
4. Перезапустіть Home Assistant
5. Перейдіть до **Налаштування → Пристрої та служби → Додати інтеграцію → Samsung POWERbot-S**

### Ручне встановлення

1. Скопіюйте папку `custom_components/powerbot_s/` до `config/custom_components/` вашого HA
2. Перезапустіть Home Assistant
3. Додайте інтеграцію через інтерфейс

### Пошук Device ID

1. Відкрийте додаток **POWERbot-S**
2. Перейдіть до **Налаштувань → Інформація про пристрій**
3. Device ID — це довгий номер, наприклад `1870169732145270786`

Або увімкніть налагоджувальне логування та перевірте логи HA:

```yaml
logger:
  default: warning
  logs:
    custom_components.powerbot_s: debug
```

---

## License

MIT License — see [LICENSE](LICENSE)
