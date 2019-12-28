docker build ./app -t semantive_app_image:latest

docker run semantive_app_image:latest /bin/bash -c 'pytest -v --disable-warnings /app/tests'

