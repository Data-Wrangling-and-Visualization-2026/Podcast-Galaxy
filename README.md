# Podcast-Galaxy

### 1. Клонируйте репозиторий
### 2. Настройте переменные окружения
```bash
cp .env.example .env
```
### 3. Запустите Docker
#### 1. Собрать всё (и фронт, и бек)
```bash
docker-compose build
```
#### 2. Собрать только бек
```bash
docker-compose build backend
```
#### 3. Собрать только фронт
```bash
docker-compose build frontend
```
#### 4. Запустить всё
```bash
docker-compose up
```
#### 5. Запустить всё с пересборкой
```bash
docker-compose up --build
```
#### 6. Запустить только конкретный сервис
```bash
docker-compose up backend
docker-compose up frontend
```
#### 7. Посмотреть логи всех сервисов
```bash
docker-compose logs -f
```
#### 8. Посмотреть логи только бекенда
```bash
docker-compose logs -f backend
```
#### 9. Посмотреть логи только фронтенда
```bash
docker-compose logs -f frontend
```
#### 10. Остановить всё
```bash
docker-compose down
```
### 4. Формат коммитов
```bash
<type>(<scope>): <description>
```
#### Типы (types):
- feat (новая функция)
- fix (исправление бага)
- refactor (рефакторинг кода)
- docs (изменение документации)
- style (форматирование, отступы, ; (не влияющее на код))
- test (добавление или исправление тестов)
- perf (изменения для улучшения производительности)
- revert (откат изменений)
#### Пример 
```bash
fix(parser): handle null values in JSON response
refactor(database): optimize query performance
perf(images): compress assets for faster loading 
```
Описание в настоящем времени (не added, а add)
