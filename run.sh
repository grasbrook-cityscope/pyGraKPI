#!/bin/sh

if [ "$#" -gt 0 ]; then # if command line arguments were given
    docker stop gracio_pygrakpi_instance_$1
    docker rm gracio_pygrakpi_instance_$1
    docker run --name gracio_pygrakpi_instance_$1 -d gracio_pygrakpi --endpoint $1
    # docker logs -f gracio_pygrakpi_instance_$1  ## do not force logs when multiple instances start

else # no command line args -> don't choose endpoint
    docker stop gracio_pygrakpi_instance
    docker rm gracio_pygrakpi_instance
    docker run --name gracio_pygrakpi_instance -d gracio_pygrakpi
    docker logs -f gracio_pygrakpi_instance
fi