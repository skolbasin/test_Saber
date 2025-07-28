# Saber - Система управления сборками

## Краткое описание

Saber - это высокопроизводительная система управления сборками на основе FastAPI с поддержкой топологической сортировки задач, асинхронной обработки через Celery и Docker-контейнеризации.

## Быстрый запуск для проверяющих

### Предварительные требования

- Docker и Docker Compose
- Python 3.11+ (для разработки)
- PostgreSQL (включен в docker-compose)
- Redis (включен в docker-compose)
- Заменить .env.example на .env. При необходимости, заменить данные переменных.

### Запуск через Docker (рекомендуется)

```bash
# 1. Клонировать репозиторий
git clone <repository-url>
cd test_saber

# 2. Запустить все сервисы(5-7 минут)
docker-compose up -d

# 3. Дождаться инициализации (30-60 секунд)
docker-compose logs -f saber-api

# 4. Проверить состояние
curl http://localhost:80/health
```

Сервис будет доступен по адресу: http://localhost:80

### Альтернативный запуск для разработки

```bash
# 1. Установить зависимости
pip install -r requirements.txt

# 2. Запустить PostgreSQL и Redis через Docker
docker-compose up -d postgres redis

# 3. Настроить переменные окружения
export DATABASE_URL="postgresql://saber_user:saber_password@localhost:5432/saber_db"
export REDIS_URL="redis://localhost:6379/0"

# 4. Запустить миграции
alembic upgrade head

# 5. Запустить приложение
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

# 6. В отдельном терминале запустить Celery worker
celery -A app.core.celery_app.celery_app worker --loglevel=info

# 7. В отдельном терминале запустить Celery beat
celery -A app.core.celery_app.celery_app beat --loglevel=info
```

## Проверка работоспособности

### 1. Базовая проверка API

```bash
# Проверка здоровья сервиса
curl http://localhost:80/health

# Получение документации API
curl http://localhost:80/docs
```

### 2. Тестирование основного функционала

Перед проверкой функционала, необходимо авторизоваться. Это можно сделать 2 способами:

#### Через Swagger/ReDoc(рекомендуется):

Необходимо перейти на http://localhost:80/docs и по очереди вызвать:
- api/v1/auth/register
- api/v1/auth/login

Cохранить полученный токен. Сверху справа в форме
любого из endpoint`ов есть замок. Нажимаем на него и вставляем сгенерированный токен. Он сработает
на все ручки.


#### Через командную строку: 
```bash
# Регистрация пользователя
curl -X POST http://localhost:80/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "username": "testuser",
    "email": "test@example.com",
    "password": "password123"
  }'

# Логин
curl -X POST http://localhost:80/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "username": "testuser",
    "password": "password123"
  }'

# Сохранить полученный токен в переменную
docker exec -it test_saber-saber-api-1 /bin/bash
export TOKEN="your_access_token_here"

```

#### Создание билдов и задач(не обязательно, т.к. БД уже заполнена объектами из yaml-файлов)

```bash
# Создание сборки
curl -X POST http://localhost:80/api/v1/builds \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "test_build",
    "tasks": ["compile", "test", "package"]
  }'

# Создание задач
curl -X POST http://localhost:80/api/v1/tasks \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "compile",
    "dependencies": []
  }'

curl -X POST http://localhost:80/api/v1/tasks \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "test",
    "dependencies": ["compile"]
  }'

curl -X POST http://localhost:80/api/v1/tasks \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "package",
    "dependencies": ["test"]
  }'

# Запуск сборки
curl -X POST http://localhost:80/api/v1/execute_build \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "build": "test_build"
  }'

# Проверка статуса сборки
curl -X POST http://localhost:80/api/v1/get_build_status \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "build": "test_build"
  }'
```

После успешной авторизации можно проверить, что билды и задачи добавлены в БД. 
Для этого заходим на http://localhost:80/docs и проверяем:
- api/v1/tasks/(GET)
- api/v1/builds(GET)

Не забываем вставить токен в запрос!

#### Результат api/v1/builds
```commandline
{
...
      "name": "write_beautiful",
      "tasks": [
        "bring_gray_ogres",
        "bring_green_orcs",
        "bring_silver_leprechauns",
        "bring_silver_witches",
        "bring_teal_cyclops",
        "coloring_fuchsia_orcs",
        "coloring_green_fairies",
        "coloring_maroon_gorgons",
        "coloring_navy_humans",
        "coloring_teal_gnomes",
        "coloring_white_golems",
        "coloring_yellow_centaurs",
        "create_aqua_centaurs",
        "create_navy_witches",
        "design_purple_centaurs",
        "enable_black_humans",
        "enable_black_witches",
        "enable_white_goblins",
        "map_black_goblins",
        "read_gray_leprechauns",
        "read_lime_gnomes",
        "train_white_fairies",
        "train_white_leprechauns",
        "write_maroon_humans",
        "write_purple_leprechauns"
      ],
      "status": "pending",
      "created_at": "2025-07-28T08:00:01.548280Z",
      "updated_at": "2025-07-28T08:00:01.548280Z",
      "error_message": null
    }
  ],
  "total": 5
```
#### Результат api/v1/tasks
```commandline
{
...
"name": "build_aqua_witches",
      "dependencies": [],
      "status": "pending",
      "created_at": "2025-07-28T08:00:01.548280Z",
      "updated_at": "2025-07-28T08:00:01.548280Z",
      "error_message": null
    },
    {
      "name": "build_black_goblins",
      "dependencies": [],
      "status": "pending",
      "created_at": "2025-07-28T08:00:01.548280Z",
      "updated_at": "2025-07-28T08:00:01.548280Z",
      "error_message": null
    },
    {
      "name": "build_black_golems",
      "dependencies": [],
      "status": "pending",
      "created_at": "2025-07-28T08:00:01.548280Z",
      "updated_at": "2025-07-28T08:00:01.548280Z",
      "error_message": null
    }
  ],
  "total": 588
}
```

В случае успеха можем дергать **api/v1/get_tasks(POST)**.

## Запуск тестов

```bash
# Запуск всех тестов
docker-compose exec app pytest

# Запуск с покрытием
docker-compose exec app pytest --cov=app --cov-report=html

# Запуск только интеграционных тестов
docker-compose exec app pytest tests/integration/

# Запуск только unit тестов
docker-compose exec app pytest tests/unit/
```
*вместо *app* вставляем название нужного нам сервиса контейнера, например *saber-api*

## Что реализовано

### Основной функционал
- ✅ FastAPI REST API с аутентификацией JWT
- ✅ Система управления пользователями
- ✅ CRUD операции для задач и сборок
- ✅ Топологическая сортировка задач (алгоритмы Kahn и DFS)
- ✅ Обнаружение циклических зависимостей
- ✅ Асинхронная обработка сборок через Celery
- ✅ Система логирования и мониторинга
- ✅ Управление архивами логов

### Архитектура
- ✅ Clean Architecture с разделением на слои
- ✅ Dependency Injection через FastAPI
- ✅ Repository pattern для работы с данными
- ✅ Service layer для бизнес-логики
- ✅ Pydantic схемы для валидации данных

### Инфраструктура
- ✅ Docker контейнеризация
- ✅ PostgreSQL база данных с миграциями Alembic
- ✅ Redis для Celery и кэширования
- ✅ Nginx как reverse proxy
- ✅ Структурированное логирование

### Тестирование
- ✅ 100% покрытие unit тестами (144 теста)
- ✅ Полное покрытие integration тестами (87 тестов)
- ✅ Тестирование всех API endpoints (24 теста)
- ✅ Моки для внешних зависимостей
- ✅ Fixture-based тестирование

## Архитектурные решения

### Выбор FastAPI
- Высокая производительность
- Автоматическая генерация OpenAPI документации
- Встроенная валидация через Pydantic
- Нативная поддержка async/await

### Топологическая сортировка
- **Алгоритм Kahn**: Оптимален для разреженных графов, раннее обнаружение циклов
- **DFS**: Подходит для плотных графов, полная информация о циклах

### Celery для асинхронных задач
- Масштабируемость обработки
- Надежность через Redis
- Мониторинг выполнения задач

### Clean Architecture
- Разделение ответственности
- Тестируемость
- Расширяемость

## Логи и мониторинг

Логи доступны через:
- Docker: `docker-compose logs -f app`
- Файловая система: `/app/logs/` внутри контейнера
- API endpoints для статистики логов

## Troubleshooting

### Проблемы с запуском
1. Убедитесь, что порты 8000, 5432, 6379 свободны
2. Проверьте, что Docker daemon запущен
3. Очистите Docker кэш: `docker-compose down -v && docker-compose up -d`

### Проблемы с базой данных
```bash
# Пересоздать базу данных
docker-compose down -v
docker-compose up -d postgres
docker-compose exec app alembic upgrade head
```

### Проблемы с Celery
```bash
# Перезапустить Celery workers
docker-compose restart celery-worker celery-beat
```

## Документация API

Полная документация доступна по адресу: http://localhost:8000/docs

## Контакты

Для вопросов и предложений создавайте issue в репозитории.