# Foodgram

Социальная сеть для рецептов. Пользователи могут публиковать рецепты, добавлять их в избранное, подписываться на авторов и скачивать список покупок для выбранных рецептов.

## Запуск

Находясь в папке infra, выполните команду:

docker-compose up

При выполнении этой команды контейнер frontend подготовит файлы для фронтенд-приложения, а затем прекратит работу.

По адресу http://localhost изучите веб-приложение, а по адресу http://localhost/api/docs/ — спецификацию API.

Для миграции и загрузки ингредиентов исопльзуйте:

docker exec infra-backend-1 python manage.py migrate

docker exec infra-backend-1 python manage.py load_ingredients

Для создания демо-пользователей и рецептов:

docker exec infra-backend-1 python create_demo_data.py

## Автор

Светлана Пигачева
