# Samsung POWERbot-S for Home Assistant

[![HACS](https://img.shields.io/badge/HACS-Custom-41BDF5.svg?logo=homeassistantcommunitystore&logoColor=white)](https://github.com/hacs/integration)
[![Validate](https://github.com/TSOrest/powerbot-s-ha/actions/workflows/validate.yml/badge.svg)](https://github.com/TSOrest/powerbot-s-ha/actions/workflows/validate.yml)
[![GitHub Release](https://img.shields.io/github/v/release/TSOrest/powerbot-s-ha?color=blue)](https://github.com/TSOrest/powerbot-s-ha/releases)
[![Built with Claude AI](https://img.shields.io/badge/Built_with-Claude_AI-FF6B35)](https://anthropic.com)

[![Open your Home Assistant instance and open a repository inside the Home Assistant Community Store.](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=TSOrest&repository=powerbot-s-ha&category=integration)

> **[Українська версія нижче](#українська)**

---

## English

Custom Home Assistant integration for the **Samsung VR7700 (POWERbot-S)** robot vacuum, using the **mzrobo.com** cloud that the POWERbot-S mobile app talks to.

### Features

| Entity | Type | Description |
|--------|------|-------------|
| Vacuum | `vacuum` | Start, stop, pause, return to dock, spot clean, fan speed |
| Status | `sensor` | Raw state string from the cloud (`cleaning`, `charging_finish`, …) |
| Battery | `sensor` | Battery level (%) |
| Fan speed | `sensor` | Current suction level (quiet / normal / strong) |
| Connection | `sensor` | online / offline (diagnostic) |
| Problem | `binary_sensor` | `on` when the robot reports an error |
| Cleaning | `binary_sensor` | `on` while cleaning |
| Docked | `binary_sensor` | `on` while in the charging dock |
| Connectivity | `binary_sensor` | `on` when the cloud is reachable (diagnostic) |

### Requirements

- Home Assistant **2025.2** or newer (2026.3+ shows the integration icon)
- An account in the **POWERbot-S** Android/iOS app with your robot added to it

### Installation via HACS

1. Click the **Open your Home Assistant instance** button above, or in HACS open **⋮ → Custom repositories** and add `https://github.com/TSOrest/powerbot-s-ha` as type **Integration**
2. Find **Samsung POWERbot-S** and click **Download**
3. Restart Home Assistant

### Manual installation

1. Copy `custom_components/powerbot_s/` to your HA `config/custom_components/` folder
2. Restart Home Assistant

### Setup

1. Go to **Settings → Devices & services → Add integration → Samsung POWERbot-S**
2. Sign in with the email and password from the POWERbot-S app

The robot on your account is added automatically. If the account has several robots, you pick one from a list (add the integration again for each robot). If the stored login ever stops working, Home Assistant asks you to sign in again.

### Troubleshooting

Enable debug logging and check the HA log:

```yaml
logger:
  default: warning
  logs:
    custom_components.powerbot_s: debug
```

---

## Українська

Інтеграція Home Assistant для робота-пилососа **Samsung VR7700 (POWERbot-S)**. Працює через хмару **mzrobo.com**, яку використовує мобільний додаток POWERbot-S.

### Можливості

| Сутність | Тип | Опис |
|----------|-----|------|
| Пилосос | `vacuum` | Старт, стоп, пауза, на базу, точкове прибирання, швидкість вентилятора |
| Стан | `sensor` | Рядок стану з хмари (`cleaning`, `charging_finish`, …) |
| Батарея | `sensor` | Рівень заряду (%) |
| Швидкість вентилятора | `sensor` | Поточний рівень всмоктування (тихо / нормально / сильно) |
| З'єднання | `sensor` | онлайн / офлайн (діагностика) |
| Проблема | `binary_sensor` | `on`, коли робот повідомляє про помилку |
| Прибирання | `binary_sensor` | `on` під час прибирання |
| На базі | `binary_sensor` | `on`, коли робот на зарядній станції |
| Підключення | `binary_sensor` | `on`, коли хмара доступна (діагностика) |

### Вимоги

- Home Assistant **2025.2** або новіший (іконка інтеграції показується з 2026.3)
- Акаунт у додатку **POWERbot-S** для Android/iOS, до якого додано робота

### Встановлення через HACS

1. Натисніть кнопку **Open your Home Assistant instance** вище, або в HACS відкрийте **⋮ → Користувацькі репозиторії** і додайте `https://github.com/TSOrest/powerbot-s-ha` як тип **Integration**
2. Знайдіть **Samsung POWERbot-S** і натисніть **Завантажити**
3. Перезапустіть Home Assistant

### Ручне встановлення

1. Скопіюйте `custom_components/powerbot_s/` до папки `config/custom_components/` вашого HA
2. Перезапустіть Home Assistant

### Налаштування

1. Відкрийте **Налаштування → Пристрої та служби → Додати інтеграцію → Samsung POWERbot-S**
2. Увійдіть з email і паролем від додатку POWERbot-S

Робот з вашого акаунта додається автоматично. Якщо на акаунті кілька роботів, ви обираєте одного зі списку (для кожного робота інтеграцію додають окремо). Якщо збережений вхід перестане працювати, Home Assistant попросить увійти знову.

### Діагностика

Увімкніть налагоджувальне логування і перегляньте журнал HA:

```yaml
logger:
  default: warning
  logs:
    custom_components.powerbot_s: debug
```

---

## License

MIT License — see [LICENSE](LICENSE)
