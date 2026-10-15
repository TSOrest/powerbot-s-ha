# Samsung POWERbot-S for Home Assistant

[![HACS](https://img.shields.io/badge/HACS-Custom-41BDF5.svg?logo=homeassistantcommunitystore&logoColor=white)](https://github.com/hacs/integration)
[![Validate](https://img.shields.io/github/actions/workflow/status/TSOrest/powerbot-s-ha/validate.yml?branch=main&label=Validate&logo=github)](https://github.com/TSOrest/powerbot-s-ha/actions/workflows/validate.yml)
[![GitHub Release](https://img.shields.io/github/v/release/TSOrest/powerbot-s-ha?label=Release&color=blue)](https://github.com/TSOrest/powerbot-s-ha/releases)
[![Built with Claude AI](https://img.shields.io/badge/Built_with-Claude_AI-FF6B35)](https://anthropic.com)

[![Open your Home Assistant instance and open a repository inside the Home Assistant Community Store.](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=TSOrest&repository=powerbot-s-ha&category=integration)

> **[Українська версія нижче](#українська)**

---

## English

Custom Home Assistant integration for the **Samsung VR7700 (POWERbot-S)** robot vacuum, using the **mzrobo.com** cloud that the POWERbot-S mobile app talks to.

### Features

| Entity | Type | Description |
|--------|------|-------------|
| Vacuum | `vacuum` | Start, stop, pause/resume, return to dock, locate (beep), suction (off / quiet / low / normal / turbo / max) |
| Status | `sensor` | Raw state string from the cloud (`cleaning`, `charging_finish`, …) |
| Battery | `sensor` | Battery level (%) |
| Fan speed | `sensor` | Current suction level |
| Connection | `sensor` | online / offline (diagnostic) |
| Problem | `binary_sensor` | `on` when the robot reports an error |
| Cleaning | `binary_sensor` | `on` while cleaning |
| Docked | `binary_sensor` | `on` while in the charging dock |
| Connectivity | `binary_sensor` | `on` when the cloud is reachable (diagnostic) |
| Water level | `select` | Mop water level (off / low / normal / high) |
| Carpet mode | `switch` | Raise suction on carpets |
| Do not disturb | `switch` | Keep the robot quiet between the start and end times |
| Do not disturb start / end | `time` | Do-not-disturb period |
| Volume | `number` | Voice volume, 0–100 % |
| Voice | `select` | Voice pack (the robot downloads a new one itself) |
| Filter / Side brush / Main brush | `sensor` | Remaining life, % (filter 150 h, side brush 100 h, main brush 200 h) |
| Cleaning mode | `sensor` | Mode of the current or last clean (auto, edge, spot, rooms, zones, …) |
| Cleaned area / Cleaning time | `sensor` | Area (m²) and time (min) of the current or last clean |
| Error | `sensor` | What the robot reports is wrong (dustbin missing, brush tangled, …); `Error code` is a disabled diagnostic sensor with the raw code |
| Schedule N | `switch` | Turns a schedule made in the app on or off; attributes show days, start, duration, mode, suction and water |

#### Extra commands (`vacuum.send_command`)

| Command | Params | What it does |
|---------|--------|--------------|
| `move` | `direction`: forward / back / left / right, `duration`: seconds (default 1, max 5) | Drives the robot by hand for a moment, then stops it |
| `clean_edge` | — | Cleans along the walls (experimental) |
| `clean_spot` | — | Cleans the spot around the robot (experimental) |

```yaml
action: vacuum.send_command
target:
  entity_id: vacuum.powerbot
data:
  command: move
  params:
    direction: forward
    duration: 1
```

### Supported models

| Model | Model code | Support |
|-------|------------|---------|
| POWERbot-S VR7700 (Europe) | 610VR510 | Full, tested |
| POWERbot-S VR7700 (North America) | 620VR520 | Full (same app plugin), not tested yet |
| Any other robot in the POWERbot-S app | — | State and battery only; Home Assistant shows a repair notice with the model details |

The water level control appears only when the robot reports a mop attached.

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
| Пилосос | `vacuum` | Старт, стоп, пауза/продовження, на базу, пошук (звуковий сигнал), потужність всмоктування (вимк. / тихо / низька / нормальна / турбо / максимум) |
| Стан | `sensor` | Рядок стану з хмари (`cleaning`, `charging_finish`, …) |
| Батарея | `sensor` | Рівень заряду (%) |
| Швидкість вентилятора | `sensor` | Поточний рівень всмоктування |
| З'єднання | `sensor` | онлайн / офлайн (діагностика) |
| Проблема | `binary_sensor` | `on`, коли робот повідомляє про помилку |
| Прибирання | `binary_sensor` | `on` під час прибирання |
| На базі | `binary_sensor` | `on`, коли робот на зарядній станції |
| Підключення | `binary_sensor` | `on`, коли хмара доступна (діагностика) |
| Рівень води | `select` | Подача води для вологого прибирання (вимк. / низький / нормальний / високий) |
| Режим килима | `switch` | Підвищує всмоктування на килимах |
| Не турбувати | `switch` | Робот мовчить між часом початку і кінця |
| Початок / кінець «Не турбувати» | `time` | Період «Не турбувати» |
| Гучність | `number` | Гучність голосу, 0–100 % |
| Голос | `select` | Голосовий пакет (робот сам завантажує новий) |
| Фільтр / Бічна щітка / Основна щітка | `sensor` | Залишок ресурсу, % (фільтр 150 год, бічна щітка 100 год, основна 200 год) |
| Режим прибирання | `sensor` | Режим поточного або останнього прибирання (авто, вздовж стін, точкове, кімнати, зони, …) |
| Прибрана площа / Час прибирання | `sensor` | Площа (м²) і час (хв) поточного або останнього прибирання |
| Помилка | `sensor` | Що робот повідомляє як проблему (немає контейнера, заплутана щітка, …); «Код помилки» — вимкнений діагностичний сенсор із сирим кодом |
| Розклад N | `switch` | Вмикає або вимикає розклад, створений у застосунку; атрибути показують дні, початок, тривалість, режим, всмоктування і воду |

#### Додаткові команди (`vacuum.send_command`)

| Команда | Параметри | Що робить |
|---------|-----------|-----------|
| `move` | `direction`: forward / back / left / right, `duration`: секунди (типово 1, максимум 5) | Ненадовго рушає робота вручну, потім зупиняє |
| `clean_edge` | — | Прибирання вздовж стін (експериментально) |
| `clean_spot` | — | Прибирання навколо робота (експериментально) |

### Підтримувані моделі

| Модель | Код моделі | Підтримка |
|--------|------------|-----------|
| POWERbot-S VR7700 (Європа) | 610VR510 | Повна, перевірена |
| POWERbot-S VR7700 (Північна Америка) | 620VR520 | Повна (той самий плагін застосунку), ще не перевірена |
| Будь-який інший робот у застосунку POWERbot-S | — | Лише стан і заряд; Home Assistant показує сповіщення з даними моделі |

Керування рівнем води з'являється, лише коли робот повідомляє, що мопа встановлена.

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
