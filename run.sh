#!/bin/sh

docker stop gracio_pygrakpi_instance
docker rm gracio_pygrakpi_instance
if [ "$#" -gt 0 ]; then # if command line arguments were given
    docker run --name gracio_pygrakpi_instance -d gracio_pygrakpi --endpoint $1
else # no command line args -> don't choose endpoint
    docker run --name gracio_pygrakpi_instance -d gracio_pygrakpi
fi
docker logs -f gracio_pygrakpi_instance