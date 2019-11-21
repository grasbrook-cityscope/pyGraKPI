#!/bin/sh

docker stop gracio_pystocs_instance
docker rm gracio_pystocs_instance
docker run --name gracio_pystocs_instance -d gracio_pystocs
docker logs -f gracio_pystocs_instance