# VPN Bot

Telegram-бот для продажи VPN-подписок на базе VLESS+Reality протокола.

## Стек

- **Python 3.13**, aiogram 3, FastAPI, SQLAlchemy 2, PostgreSQL
- **VPN backend**: 3x-ui / Xray (VLESS + Reality)
- **Платежи**: Platega
- **Архитектура**: Clean Architecture (Domain / Application / Infrastructure / Presentation)

## Возможности

- Продажа и продление VPN-подписок через Telegram
- Пробный период
- Подписка агрегирует ключи со всех серверов — пользователь вставляет одну ссылку и получает доступ ко всем серверам сразу
- Автоматическое создание VPN-клиентов через 3x-ui API
- Webhook-обработка платежей от Platega
- Система поддержки через отдельный Telegram-бот с форумными топиками
- Страница подписки с редиректом в Happ
- Динамическая конфигурация: тарифы и серверы управляются через БД

## Архитектура

Проект построен по принципам Clean Architecture: \
domain/ — бизнес-сущности (User, Subscription, Plan, Payment, AccessKey) \
application/ — use cases, порты (репозитории, VPN gateway, платёжный провайдер) \
infrastructure/ — SQLAlchemy, репозитории, XUI API клиент, Platega клиент \
presentation/ — Telegram-бот (aiogram), FastAPI (webhook, subscription endpoint) \
core/ — конфиг, утилиты \
app/ — точка входа, DI контейнер \
Направление зависимостей: `Infrastructure → Application → Domain`, `Presentation → Application`. Domain ни от кого не зависит.

Ключевые паттерны: Unit of Work, Repository, Gateway, Use Case.

## Установка

### 1. Клонировать репозиторий

```bash
git clone https://github.com/CTTAPTAH/vpn_bot.git
cd vpn_bot
```

### 2. Создать виртуальное окружение

```bash
python -m venv .venv
source .venv/bin/activate  # Linux/macOS
.venv\Scripts\activate     # Windows
```

### 3. Установить зависимости

```bash
pip install -r requirements.txt
```

### 4. Настроить переменные окружения

Необходимо создать файл .env на основе .env.example. Секретные данные не должны добавляться в репозиторий.

Скопируйте `.env.example` в `.env` и заполните:

```bash
cp .env.example .env
```

```env
# Основной бот
BOT_TOKEN=your_bot_token

# Бот поддержки
SUPPORT_BOT_TOKEN=your_support_bot_token
SUPPORT_GROUP_ID=your_forum_group_id

# PostgreSQL
DB_HOST=localhost
DB_PORT=5432
DB_NAME=vpn_bot
DB_USER=vpn_bot_user
DB_PASSWORD=your_password

# Subscription endpoint
SUB_HOST=your_domain_or_ip
SUB_PROTOCOL=https

# Platega
PLATEGA_MERCHANT_ID=your_merchant_id
PLATEGA_API_KEY=your_api_key
```

### 5. Применить миграции

```bash
alembic upgrade head
```

### 6. Запустить

```bash
python app/main.py
```

Бот, бот поддержки и FastAPI сервер запускаются в одном процессе через `asyncio.gather`.

## Требования к инфраструктуре

- **PostgreSQL** 14+
- **3x-ui** панель с настроенным VLESS+Reality inbound на каждом VPN-сервере
- Публичный домен с HTTPS для webhook Platega и subscription endpoint
- Telegram группа с включёнными форумами для бота поддержки

## Переменные БД

Тарифы и серверы управляются через таблицы `plans` и `servers` — бот подстраивается под них динамически без изменения кода.

## Платёжный провайдер

Используется Platega. Для замены провайдера достаточно реализовать интерфейс `AbstractPaymentProvider` из `application/ports/payment_provider.py`.

## Лицензия

Распространяется под лицензией MIT. Подробнее: файл [LICENSE](LICENSE).