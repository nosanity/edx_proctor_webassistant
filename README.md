# Instalation guide

## Requirements

Api extension must be installed for you OpenEDX.
See https://github.com/miptliot/open_edx_api_extension

## Proctor web assistant installation

Create venv and activate it:
```
virtualenv --no-site-packages assistant_env
source assistant_env/bin/activate
```

Install bower using npm:
```
npm install -g bower
```

Get source from GitHub:
```
git clone https://github.com/miptliot/edx_proctor_webassistant
```

Be sure that edX RabbitMQ is available for the webassistant application:
```
import pika
from pika import adapters
adapters.TornadoConnection(pika.URLParameters('amqp://user:pass@127.0.0.1:5673/'))
```

If you are using edX through Vagrant image you may add the settings below to your `Vagrantfile`:
```
if not ENV['VAGRANT_NO_PORTS']
  ...
  config.vm.network :forwarded_port, guest: 15672, host: 15673    # rabbitmq web panel
  config.vm.network :forwarded_port, guest: 5672, host: 5673      # rabbitmq server
end
```

Setup the project:
```
cd edx_proctor_webassistant
pip install -r requirements.txt 
```

Create file `settings_local.py` in one level with `settings.py` and specify all custom settings there (see example in the `settings_local.example`)

Then run commands:
```
python manage.py bower install
python manage.py migrate
python manage.py collectstatic
```

## SSO authorization setup

- Create new client in SSO admin panel. Set redirect uri as `http://<domain>/complete/sso_pwa-oauth2/`
- Enter client's KEY and SECRET in web assistant's settings:
```
    SOCIAL_AUTH_SSO_PWA_OAUTH2_KEY = '<KEY>'
    SOCIAL_AUTH_SSO_PWA_OAUTH2_SECRET = '<SECRET>'
```

- Enter SSO application's url in web assistant's settings:
```
    SSO_PWA_URL = "http://<SSO url>"
```
- Set up an `AUTH_SESSION_COOKIE_DOMAIN`. It must be proctor domain address without subdomain. For example `.yourdomain.com` for `proctor.yourdomain.com`

## Setup uWSGI

**NOTE:** if you run application locally and `DEBUG=True`, no uwsgi configuration is needed

Install uwsgi globally:
```
sudo pip install uwsgi
```

All actions below will be considered from the point when your cloned code lives in `/edxapps`.

Create somewhere the file named `uwsgi.ini` with the following content (assuming you want to run django server on `:8080` port)
```
[uwsgi]
emperor = vassals
uid = www-data
gid = www-data
die-on-term = true
offload-threads = 1
route = ^/ uwsgi:/127.0.0.1:8080,0,0
```

Create `vassals` dir with config (change path to the directory where uwsgi.ini was created)
```
# mkdir /edxapp/edx_proctor_webassistant/vassals
# cd /edxapp/edx_proctor_webassistant/vassals
# touch runserver.ini
```

`runserver.ini` content for django application (change params to your according to your needs): 
```
[uwsgi]
umask = 002
userhome = /tmp
virtualenv = /edxapps/assistant_env
chdir = /edxapps/edx_proctor_webassistant
master = true
no-orphans = true
die-on-term = true
memory-report = true
env = DJANGO_SETTINGS_MODULE=edx_proctor_webassistant.settings
socket = 127.0.0.1:8080
module = edx_proctor_webassistant.wsgi
buffer-size = 32768
processes = 2
```

check the config is correct
```
# cd /edxapp/edx_proctor_webassistant
# uwsgi --ini uwsgi.ini
```

## Tornado notifications server

Just run server with the command:

```
source assistant_env/bin/activate
python notificator.py

```

In production you should use something like `systemd` or `supervisor` to manage daemon and check it availability  

## NGINX

Upgrade your Nginx version to >=1.4
 
Nginx server allows us to serve our static files and supports websockets switching protocol feature
 
Create `proctor` config (or place a symlink) in nginx sites-available dir
```
upstream django {
    server 127.0.0.1:8080;
}

server {
    listen 80;
    server_name proctor.sandbox; # place your server name here

    charset utf-8;
    client_max_body_size 20M;
    keepalive_timeout 0;
    large_client_header_buffers 8 32k;

    access_log /var/log/nginx/proctoring_access.log;
    error_log /var/log/nginx/proctoring_error.log;

    location / {
        include /etc/nginx/uwsgi_params;
        uwsgi_pass django;
    }

    location /static {
        alias /edxapps/edx_proctor_webassistant/static;
    }

    location /notifications {
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_pass http://127.0.0.1:9090;
        proxy_buffers 8 32k;
        proxy_buffer_size 64k;
    }

}
```
