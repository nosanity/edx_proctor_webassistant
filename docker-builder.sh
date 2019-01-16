#!/bin/bash
# by Evgeniy Bondarenko <Bondarenko.Hub@gmail.com>
# last changes 08.11.2018 Updated

dockerhub='docker.2bond.cloud'
name=${1:-"epw"}
tag=${2:-$(git rev-parse --abbrev-ref HEAD | cut -f2 -d/)}
version="_$(date +%Y-%m-%d_%H-%M-%S)"
outsource=${3:-"false"}

docker build -t ${dockerhub}/${name}:latest -t ${dockerhub}/${name}:${tag} -t ${dockerhub}/${name}:${tag}${version}  . && \
docker push ${dockerhub}/${name}:${tag}${version} && docker push ${dockerhub}/${name}:${tag} &&   docker push ${dockerhub}/${name}:latest

#ssh root@ubuntu-ui.2bond.cloud  oc import-image name --from=docker.2bond.cloud/$name:latest --confirm=true

# for upload to outsource
if $outsource ; then
dockerhub='docker.oeplatform.ru'
docker tag  docker.2bond.cloud/${name}:latest ${dockerhub}/evgeniy/docker/${name}:latest
docker push ${dockerhub}/evgeniy/docker/${name}:latest
fi