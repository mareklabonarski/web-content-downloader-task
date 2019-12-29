docker-compose down
docker volume rm semantive_media || true
docker-compose up -d --build
