#!/bin/bash
# by Evgeniy Bondarenko <Bondarenko.Hub@gmail.com>
# v5   add tmp variable $first_run for run Build static and localization
# v4.3 edit for variable for default Openshift envaroment

# DynIP
IP=$(cat /etc/hosts|grep $HOSTNAME |awk '{print $1}')
export IP=${IP:-"127.0.0.1"}
export MIGRATION=${MIGRATION:-"false"}

export BIND_ADDR=${BIND_ADDR:-"0.0.0.0"}
export BIND_PORT=${BIND_PORT:-"80"}


if $MIGRATION ; then
    echo "start  Build static and localization"
    ./manage.py migrate
    ./manage.py collectstatic
    ./manage.py create_admin_user
fi

exec "$@"

