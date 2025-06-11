# build env
FROM node:21.7.1-alpine as build
WORKDIR /app
COPY package*.json ./
RUN npm install
COPY . .
ENV CI=false
RUN npm run build

# Копирование всех файлов в результирующую директорию build
RUN mkdir -p /app/result_build && cp -r /app/build/. /app/result_build/

CMD ["cp", "-r", "/app/build/.", "/app/result_build/"]