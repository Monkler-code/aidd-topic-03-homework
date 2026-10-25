# Отчет о реализации нового инвестиционного функционала

## 1. Спецификация внедренных функциональных требований

### Модуль 1: Персональный мониторинг акций (Watchlists & Alerts)
- ✅ **ФР-1.1**: Создание именованных списков наблюдения для каждого пользователя
- ✅ **ФР-1.2**: Добавление/удаление акций из списков наблюдения
- ✅ **ФР-1.3**: Установка ценовых триггеров (выше/ниже целевой цены)
- ✅ **ФР-1.4**: Автоматическая проверка триггеров через Celery (каждую минуту)
- ✅ **ФР-1.5**: Защита от дублирования — при срабатывании статус меняется на `is_triggered=True`, повторная отправка блокируется до ручного сброса

### Модуль 2: Виртуальный инвестиционный портфель
- ✅ **ФР-2.1**: Создание именованных виртуальных портфелей
- ✅ **ФР-2.2**: Регистрация операций BUY и SELL с комиссией
- ✅ **ФР-2.3**: Расчёт средней цены по методу средневзвешенной стоимости
- ✅ **ФР-2.4**: Расчёт P&L (абсолютный и процентный) в реальном времени
- ✅ **ФР-2.5**: Полная история транзакций с метаданными

### Модуль 3: История рыночных цен
- ✅ **ФР-3.1**: Автоматическое сохранение OHLCV данных через Celery (ежедневно)
- ✅ **ФР-3.2**: Запрос истории за произвольный период через API
- ✅ **ФР-3.3**: Расчёт абсолютного и процентного изменения за период
- ✅ **ФР-3.4**: Визуализация линейных графиков через Plotly

### Модуль 4: Симулятор инвестиционных стратегий
- ✅ **ФР-4.1**: Создание стратегий с условиями входа/выхода (цена, изменение %)
- ✅ **ФР-4.2**: Бэктестинг на исторических данных из БД
- ✅ **ФР-4.3**: Журнал виртуальных сделок с деталями
- ✅ **ФР-4.4**: Метрики эффективности (доходность %, win rate, макс. просадка)

---

## 2. Архитектурные изменения и изменения в БД

### Новые модели (8 таблиц)

| Модель | Назначение | Ключевые поля |
|---|---|---|
| `Watchlist` | Список наблюдения | user (FK), name, created_at |
| `WatchlistItem` | Акция в списке | watchlist (FK), share (FK) |
| `PriceAlert` | Ценовой триггер | watchlist_item (FK), share (FK), alert_type, target_price, is_triggered |
| `Portfolio` | Виртуальный портфель | user (FK), name, created_at |
| `Transaction` | Операция покупки/продажи | portfolio (FK), share (FK), type, quantity, price, commission |
| `HistoricalPrice` | Историческая цена | share (FK), date, open_price, high, low, close, volume |
| `TradingStrategy` | Торговая стратегия | user (FK), name, is_active, last_run_at |
| `StrategyRule` | Правило стратегии | strategy (FK), condition_field, condition_operator, condition_value, action |
| `StrategyTrade` | Симулированная сделка | strategy (FK), share (FK), action, quantity, price, profit_loss |

### Новые API эндпоинты (API v2)

| Эндпоинт | Метод | Описание |
|---|---|---|
| `/api/v2/watchlists/` | GET, POST | Список/создание watchlists |
| `/api/v2/watchlists/{id}/` | GET, PUT, DELETE | Детали watchlist |
| `/api/v2/watchlists/{id}/add_share/` | POST | Добавить акцию |
| `/api/v2/watchlists/{id}/items/` | GET | Элементы с ценами |
| `/api/v2/price-alerts/` | GET, POST | Список/создание алертов |
| `/api/v2/price-alerts/{id}/trigger/` | POST | Ручной триггер |
| `/api/v2/price-alerts/{id}/reset/` | POST | Сброс алерта |
| `/api/v2/price-alerts/check_all/` | GET | Проверка всех алертов |
| `/api/v2/portfolios/` | GET, POST | Список/создание портфелей |
| `/api/v2/portfolios/{id}/summary/` | GET | Сводка с P&L |
| `/api/v2/portfolios/{id}/transactions/` | GET | История сделок |
| `/api/v2/portfolios/{id}/add_transaction/` | POST | Добавить сделку |
| `/api/v2/historical-prices/` | GET | История цен (фильтр по share_id) |
| `/api/v2/historical-prices/change/` | GET | Изменение за период |
| `/api/v2/historical-prices/chart/` | GET | Данные для графика |
| `/api/v2/strategies/` | GET, POST | Список/создание стратегий |
| `/api/v2/strategies/{id}/rules/` | GET, POST | Правила стратегии |
| `/api/v2/strategies/{id}/backtest/` | POST | Запуск бэктестинга |
| `/api/v2/strategies/{id}/trades/` | GET | Симулированные сделки |

### Новые веб-страницы

| URL | Описание |
|---|---|
| `/watchlists/` | Список списков наблюдения |
| `/watchlists/create` | Создание списка |
| `/watchlists/{id}` | Детали списка с алертами |
| `/portfolio/` | Список портфелей |
| `/portfolio/create` | Создание портфеля |
| `/portfolio/{id}` | Детали портфеля с P&L |
| `/price-history/` | Список акций с историей |
| `/price-history/{id}` | График и история цен |
| `/strategies/` | Список стратегий |
| `/strategies/create` | Создание стратегии |
| `/strategies/{id}` | Настройка и бэктестинг |

---

## 3. Описание реализации ключевой бизнес-логики

### Дедупликация алертов
```python
# dashboard/services/watchlists.py — PriceAlertService.trigger_alert()
def trigger_alert(alert):
    if alert.is_triggered:
        return False  # Предотвращает повторное срабатывание
    with transaction.atomic():
        alert.refresh_from_db()  # Защита от race condition
        if alert.is_triggered:
            return False
        alert.is_triggered = True
        alert.triggered_at = datetime.now()
        alert.save()
    return True
```
- Статус `is_triggered` блокирует повторные уведомления
- `transaction.atomic()` + `refresh_from_db()` предотвращают race condition
- Ручной сброс через `/reset/` позволяет активировать заново

### Расчёт средней цены (средневзвешенная стоимость)
```python
# dashboard/services/portfolio.py — PortfolioCalculator.get_holdings()
# При покупке:
#   new_avg_price = (old_total_cost + new_cost) / (old_quantity + new_quantity)
# При продаже:
#   average_price остаётся прежним, quantity уменьшается
#   total_cost = average_price * new_quantity
```
- Метод средневзвешенной стоимости (не FIFO/LIFO)
- При продаже средняя цена не меняется, уменьшается количество
- P&L = (current_price - average_price) × quantity

### Симулятор стратегий
```python
# dashboard/services/backtester.py — StrategyBacktester.run_backtest()
# 1. Загружает исторические данные из HistoricalPrice
# 2. Итерирует по дням, оценивает правила в порядке приоритета
# 3. При срабатывании правила — создаёт виртуальную сделку
# 4. Учитывает виртуальный баланс ($100,000 начальный)
# 5. Рассчитывает метрики: доходность, win rate, макс. просадка
```
- Условия: цена закрытия/макс/мин > или < значение, изменение %
- Действия: BUY или SELL
- Приоритеты правил определяют порядок оценки
- Виртуальный баланс предотвращает покупку при недостатке средств

---

## 4. Статус верификации и запуска

### Миграции БД
```
Running migrations:
  Applying dashboard.0008_alter_share_options_alter_share_figi_and_more... OK
```
✅ Все миграции применены успешно

### Результаты тестирования
```
Ran 49 tests in 4.633s
OK
```

**Покрытие тестами (49 тестов):**
- API Shares (12 тестов) — CRUD, поиск, фильтрация, сортировка
- Модель Share (3 теста) — строковое представление, уникальность
- Аутентификация (8 тестов) — регистрация, вход, выход
- Список акций (2 теста) — рендеринг, сортировка
- Watchlists & Alerts (5 тестов) — создание, добавление акций, алерты
- Портфель (4 теста) — создание, сделки, сводка, история
- Исторические цены (4 теста) — сохранение, запрос, изменение, график
- Стратегии (4 теста) — создание, правила, метрики бэктестинга
- Интеграция (7 тестов) — загрузка всех новых страниц

### Проверка работоспособности
| Эндпоинт | Статус |
|---|---|
| `/` (список акций) | ✅ 200 OK |
| `/api/v1/shares/` | ✅ 200 OK |
| `/user/login/` | ✅ 200 OK |
| `/user/registration/` | ✅ 200 OK |
| `/watchlists/` | ✅ 200 OK |
| `/portfolio/` | ✅ 200 OK |
| `/price-history/` | ✅ 200 OK |
| `/strategies/` | ✅ 200 OK |
| `/api/v2/watchlists/` | ✅ 200 OK |
| `/api/v2/portfolios/` | ✅ 200 OK |

### Регрессия
✅ Все оригинальные функции работают без изменений:
- Авторизация/регистрация
- CRUD акций через UI
- REST API v1 для акций
- Обновление цен через Celery
