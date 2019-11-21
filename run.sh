#!/bin/sh

docker stop gracio_pygrakpi_instance
docker rm gracio_pygrakpi_instance
docker run --name gracio_pygrakpi_instance -d gracio_pygrakpi
docker logs -f gracio_pygrakpi_instance