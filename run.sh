#!/bin/sh

docker stop gracio_pygrakpi_instance
docker rm gracio_pygrakpi_instance
if [ "$#" -gt 0 ]; then
    docker run --name gracio_pygrakpi_instance -d gracio_pygrakpi --endpoint $1
else
    docker run --name gracio_pygrakpi_instance -d gracio_pygrakpi
fi
docker logs -f gracio_pygrakpi_instance