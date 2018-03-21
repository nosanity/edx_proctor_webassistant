(function () {
    angular.module('websocket', []).factory('WS', ['$rootScope', function ($rootScope) {
        var sock, sock_params = {}, force_close = false;

        var disconnect = function() {
          if (sock !== null) {
              force_close = true;
              console.log("SockJS disconnecting...");
              sock.close();
              sock = null;
          }
        };

        var init = function (course_event_id, callback, reconnect, onErrorCloseCallback) {
            if (!course_event_id) {
                throw new Error("Invalid course_event_id param: " + course_event_id);
            }

            sock_params.channel = course_event_id;
            sock_params.callback = callback;
            var sock_url = document.location.protocol + '//' + $rootScope.apiConf.ioServer + window.app.notificationsUrl +
                '?course_event_id=' + course_event_id;
            sock = new SockJS(sock_url);
            force_close = false;

            sock.onopen = function () {
                console.log("SockJS connection opened");
            };
            sock.onmessage = function (e) {
                try {
                    callback(e.data);
                } catch (err) {
                    console.log("SockJS onmessage error", err);
                }
            };
            sock.onerror = function (e) {
                console.log('SockJS error:', e);
            };
            sock.onclose = function () {
                console.log("SockJS connection closed");
                sock = null;
                if (reconnect !== undefined && reconnect === true && !force_close) {
                    setTimeout(function() {
                        if (onErrorCloseCallback) {
                            onErrorCloseCallback(function() {
                                init(course_event_id, callback, reconnect, onErrorCloseCallback);
                            });
                        } else {
                            init(course_event_id, callback, reconnect);
                        }

                    }, 3000);
                }
            };
            $rootScope.$on('$locationChangeStart', function (event, next, current) {
                if (sock && !force_close) {
                    sock.close();
                }
            });
        };

        return {
            init: init,
            disconnect: disconnect
        };
    }]);
})();