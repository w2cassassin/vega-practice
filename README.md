# Сервис для сравнения разных версия расписания.  

## 1. Настройка приложения
#### 1. Загрузить исходники приложения
```
git clone https://vgit.mirea.ru/w3cassassin/schedule-compare
cd schedule-compare
```
#### 2. Переименовать файл .env.example в .env и заполнить все переменные
Описание переменных:
```
APP_HOST=0.0.0.0               # Хост приложения
APP_PORT=8000                  # Порт приложения внутри контейнера
DOCKER_PORT=8012               # Внешний порт для доступа к приложению
ROOT_PATH=/your-path            # Корневой путь для API

POSTGRES_HOST=db               # Имя хоста PostgreSQL
POSTGRES_PORT=5432             # Порт PostgreSQL внутри контейнера
POSTGRES_OUT_PORT=54333        # Внешний порт для PostgreSQL
POSTGRES_USER=postgres         # Имя пользователя PostgreSQL
POSTGRES_PASSWORD=yourpassword # Пароль для PostgreSQL
POSTGRES_DB=yourdatabase       # Имя базы данных

```
#### 3. Собрать и запустить контейнеры
``` 
sudo docker-compose up -d --build
```
## 2.Настройка nginx
#### 1. Добавить конфигурацию Nginx

Пример конфигурации:
```
server {
    ...

    #your-path = ROOT_PATH

    location /your-path { 
    rewrite ^/your-path$ /your-path/ permanent;
    }

    location /your-path/ {
        proxy_pass http://localhost:8012/; 
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme; # <- ВАЖНО
    }

}
```
