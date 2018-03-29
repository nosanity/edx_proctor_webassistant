(function(){
    angular.module('proctor')
        .service('wsData', function($route, TestSession, DateTimeService, WS, Polling) {

            var self = this;

            this.attempts = [];

            var updateStatus = function (code, status, updated) {
                var obj = self.attempts.filterBy({code: code});
                if (obj.length > 0) {
                    if ((obj[0].review_sent !== true)
                      && (!obj[0]['status_updated'] || !updated || (updated > obj[0]['status_updated']))
                      && (obj[0]['status'] !== status)) {
                        obj[0]['status'] = status;
                        obj[0]['status_updated'] = updated;
                    }
                }
            };

            var addAttempt = function (attempt) {
                if (!attempt.hasOwnProperty('comments')) {
                    attempt.comments = [];
                }
                var item = self.attempts.filterBy({code: attempt.examCode});
                item = item.length ? item[0] : null;
                if (!item) {
                    self.attempts.push(angular.copy(attempt));
                    Polling.add_item(attempt.examCode);
                }
            };

            var recievedComments = function (msg) {
                var item = self.attempts.filterBy({code: msg.code});
                item = item.length ? item[0] : null;
                if (item) {
                    var comment = item.comments.filterBy({timestamp: msg.comments.timestamp});
                    if (!comment.length) {
                        item.comments.push(msg.comments);
                    }
                }
            };

            var pollStatus = function (msg) {
                var item = self.attempts.filterBy({code: msg.code});
                item = item.length ? item[0] : null;
                if (msg.status === 'started' && item && item.status === 'ready_to_start') {
                    // variable to display in view
                    item.started_at = DateTimeService.get_now_time();
                }
                updateStatus(msg['code'], msg['status'], msg['created']);
                if (['verified', 'error', 'rejected', 'deleted_in_edx'].in_array(msg['status'])) {
                    Polling.stop(msg['code']);
                }
            };

            var endSession = function () {
                WS.disconnect();
                Polling.clear();
                TestSession.flush();
                $route.reload();
            };

            this.addNewAttempt = function (attempt) {
                addAttempt(attempt)
            };

            this.findAttempt = function(code) {
                return self.attempts.filterBy({code: code});
            };

            this.updateAttemptStatus = function (code, status, updated) {
                updateStatus(code, status, updated);
                if (['verified', 'error', 'rejected', 'deleted_in_edx'].in_array(status)) {
                    Polling.stop(code);
                }
            };

            this.websocket_callback = function(msg) {
                if (msg) {
                    if (msg.examCode) {
                        addAttempt(msg);
                        return;
                    }
                    if (msg.code && msg.hasOwnProperty('comments')) {
                        recievedComments(msg);
                        return;
                    }
                    if (msg.code && msg['status']) {
                        pollStatus(msg);
                        return;
                    }
                    if (msg.hasOwnProperty('end_session') && msg.hasOwnProperty('session_id')) {
                        var session = TestSession.getSession();
                        if (session.id === parseInt(msg.session_id)) {
                            endSession();
                        }
                    }
                }
            };

            this.clear = function () {
                this.attempts = [];
            }
        });
})();
