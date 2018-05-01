'use strict';

(function () {
    angular.module('proctor').controller(
        'MainCtrl', ['$scope', '$interval', '$location',
            '$q', '$route', 'WS', 'Api', 'Auth', 'i18n',
            '$uibModal', 'TestSession', 'wsData', 'Polling',
            'DateTimeService', 'students',
            function ($scope, $interval, $location, $q, $route, WS, Api, Auth, i18n,
                      $uibModal, TestSession, wsData, Polling, DateTimeService, students) {

                var session = TestSession.getSession();

                $scope.readOnlyMode = (session.status === "archived");
                $scope.courseInfo = session.course_id.split('+');
                $scope.startDate = moment(session.start_date).format('DD.MM.YYYY HH:mm');
                $scope.endSessionBtnDisabled = false;
                $scope.endDate = '';
                if (session.end_date) {
                    $scope.endDate = moment(session.end_date).format('DD.MM.YYYY HH:mm');
                }
                $scope.chosenMassAction = 'activate_all_inactive';
                $scope.massAction = {
                    btnDisabled: false,
                    inProgress: false,
                    options: [{
                        key: 'activate_all_inactive',
                        name: i18n.translate('ACTIVATE_ALL_INACTIVE')
                    }, {
                        key: 'make_verified_all_submitted',
                        name: i18n.translate('MAKE_VERIFIED_ALL_SUBMITTED')
                    }, {
                        key: 'make_rejected_all_submitted',
                        name: i18n.translate('MAKE_REJECTED_ALL_SUBMITTED')
                    }]
                };
                $scope.chosenViewOption = '';
                $scope.statuses = {
                    created: {
                        title: i18n.translate('STATUS_CREATED'),
                        cssClass: 'status-blue',
                        actions: [{
                            title: i18n.translate('ACTIVATE'),
                            cssClass: 'btn-primary',
                            action: 'activate'
                        }]
                    },
                    download_software_clicked: {
                        title: i18n.translate('STATUS_DOWNLOAD_SOFTWARE_CLICKED'),
                        cssClass: 'status-blue',
                        actions: []
                    },
                    error: {
                        title: i18n.translate('STATUS_ERROR'),
                        cssClass: 'status-red',
                        actions: []
                    },
                    ready_to_start: {
                        title: i18n.translate('STATUS_READY_TO_START'),
                        cssClass: 'status-orange',
                        actions: []
                    },
                    started: {
                        title: i18n.translate('STATUS_STARTED'),
                        cssClass: 'status-blue',
                        actions: [{
                            title: i18n.translate('STOP'),
                            cssClass: 'btn-warning',
                            action: 'stop'
                        }]
                    },
                    ready_to_submit: {
                        title: i18n.translate('STATUS_STARTED'),
                        cssClass: 'status-orange',
                        actions: []
                    },
                    submitted: {
                        title: i18n.translate('STATUS_SUBMITTED'),
                        cssClass: 'status-blue',
                        actions: [{
                            title: i18n.translate('PASSED'),
                            cssClass: 'btn-success',
                            action: 'set_passed'
                        }, {
                            title: i18n.translate('NOT_PASSED'),
                            cssClass: 'btn-danger',
                            action: 'set_not_passed'
                        }]
                    },
                    deleted_in_edx: {
                        title: i18n.translate('STATUS_DELETED_IN_EDX'),
                        cssClass: 'status-red',
                        actions: []
                    },
                    rejected: {
                        title: i18n.translate('STATUS_REJECTED'),
                        cssClass: 'status-red',
                        actions: []
                    },
                    verified: {
                        title: i18n.translate('STATUS_VERIFIED'),
                        cssClass: 'status-green',
                        actions: []
                    },
                    timed_out: {
                        title: i18n.translate('STATUS_TIMED_OUT'),
                        cssClass: 'status-red',
                        actions: []
                    }
                };

                $scope.studentsGridOptions = {
                    data: [],
                    sort: {
                        predicate: 'id',
                        direction: 'asc'
                    }
                };

                $scope.test_center = session.testing_center;
                $scope.course_name = session.course_name;
                $scope.exam_name = session.exam_name;
                $scope.exam_link = window.location.href + "session/" + session.hash_key;

                $scope.exams = {
                    checked: [],
                    ended: []
                };

                $scope.isOwner = TestSession.is_owner();

                $scope.changeCheckbox = function(item) {
                    if (item.checked) {
                        $scope.checkedItems.number++;
                        $scope.checkedItems.items[item.examCode] = item.status;
                    } else {
                        $scope.checkedItems.number--;
                        delete $scope.checkedItems.items[item.examCode];
                    }
                    updateStatusForCheckedItems();
                };

                $scope.removeSelections = function() {
                    if ($scope.checkedItems.number > 0) {
                        $scope.checkedItems.number = 0;
                        $scope.checkedItems.items = {};
                        wsData.removeCheckedAll();
                        initCheckedItems();
                    }
                };

                $scope.applyAction = function(item, actionName) {
                    var newStatus = (actionName === 'set_passed') ? 'Clean'
                        : ((actionName === 'set_not_passed') ? 'Suspicious' : null);

                    if (actionName === 'activate') {
                        item.btnDisabled = true;
                        Api.accept_exam_attempt(item.examCode)
                            .then(
                                function (data) {},
                                function () {
                                    item.btnDisabled = false;
                                    showServerError();
                                });
                    } else if (actionName === 'stop') {
                        $uibModal.open({
                            animation: true,
                            templateUrl: 'windowConfirmation.html',
                            controller: 'WindowConfirmationCtrl',
                            size: 'md',
                            resolve: {
                                data: {
                                    title: i18n.translate('WARNING'),
                                    description: i18n.translate('STOP_ATTEMPT'),
                                    okFunc: function() {
                                        item.btnDisabled = true;
                                        Api.stop_exam_attempt(item.examCode, item.orgExtra.userID).then(
                                            function (data) {
                                                if (data.data.status = 'submitted') {
                                                    addReviewComment(item, [item.examCode], true);
                                                }
                                            }, function () {
                                                item.btnDisabled = false;
                                                showServerError();
                                            });
                                    }
                                }
                            }
                        });
                    } else if ((actionName === 'set_passed') || (actionName === 'set_not_passed')) {
                        item.btnDisabled = true;
                        sendReview(item, newStatus);
                    }
                };

                $scope.applyActionForChecked = function(actionName) {
                    applyBulkAction(actionName, $scope.checkedItems.items, false, false, function() {
                        $scope.removeSelections();
                    });
                };

                $scope.applyMassAction = function(chosenAction) {
                    var selectedItems = {};
                    var found = false;
                    var onFinish = function () {
                        $scope.massAction.btnDisabled = false;
                        $scope.massAction.inProgress = false;
                    };
                    var beforeStart = function() {
                        $scope.massAction.btnDisabled = true;
                        $scope.massAction.inProgress = true;
                    };

                    angular.forEach(wsData.attempts, function (attempt) {
                        if (((chosenAction === 'activate_all_inactive') && (attempt.status === 'created'))
                        || ((chosenAction === 'make_verified_all_submitted') && (attempt.status === 'submitted'))
                        || ((chosenAction === 'make_rejected_all_submitted') && (attempt.status === 'submitted'))) {
                            selectedItems[attempt.code] = attempt.status;
                            found = true;
                        }
                    });

                    if (found) {
                        if (chosenAction === 'activate_all_inactive') {
                            applyBulkAction('activate', selectedItems, onFinish, onFinish, beforeStart);
                        } else if (chosenAction === 'make_verified_all_submitted') {
                            applyBulkAction('set_passed', selectedItems, onFinish, onFinish, beforeStart);
                        } else if (chosenAction === 'make_rejected_all_submitted') {
                            applyBulkAction('set_not_passed', selectedItems, onFinish, onFinish, beforeStart);
                        }
                    }
                };

                $scope.endSession = function() {
                    $uibModal.open({
                        animation: true,
                        templateUrl: 'reviewContent.html',
                        controller: 'ReviewCtrl',
                        size: 'lg',
                        resolve: {
                            params: {
                                exam: null,
                                attemptCodes: [],
                                review_type: 'session',
                                okCallback: function() {
                                    $scope.endSessionBtnDisabled = true;
                                    WS.disconnect();
                                    wsData.clear();
                                    $location.path('/');
                                },
                                errorCallback: function() {},
                                statuses: $scope.statuses,
                                readOnlyMode: $scope.readOnlyMode,
                                cancelBtnText: i18n.translate('CANCEL')
                            }
                        }
                    });
                };

                $scope.showInfo = function(examCode) {
                    var exam = wsData.findAttempt(examCode);
                    addReviewComment(exam, [examCode], false);
                };

                $scope.expand = function(examCode, expanded) {
                    wsData.setExpanded(examCode, expanded);
                };

                var initCheckedItems = function() {
                    $scope.checkedItems = {
                        number: 0,
                        items: {},
                        status: ''
                    };
                };

                var updateStatusForCheckedItems = function() {
                    var newStatus = null;
                    var firstItem = true;
                    angular.forEach($scope.checkedItems.items, function(status) {
                        if (firstItem) {
                            newStatus = status;
                            firstItem = false;
                        } else if (newStatus !== status) {
                            newStatus = '';
                        }
                    });
                    $scope.checkedItems.status = newStatus;
                };

                var showServerError = function() {
                    $uibModal.open({
                        animation: true,
                        templateUrl: 'windowAlert.html',
                        controller: 'WindowAlertCtrl',
                        size: 'md',
                        resolve: {
                            data: {
                                title: i18n.translate('SERVER_ERROR'),
                                description: i18n.translate('SOMETHING_WRONG')
                            }
                        }
                    });
                };

                var getReviewPayload = function(exam, status) {
                    var payload = {
                        "examMetaData": {
                            "examCode": exam.examCode,
                            "reviewedExam": true,
                            "proctor_username": Auth.get_proctor()
                        },
                        "reviewStatus": status,
                        "videoReviewLink": "",
                        "desktopComments": []
                    };
                    angular.forEach(exam.comments, function (val) {
                        payload.desktopComments.push({
                            "comments": val.comment,
                            "duration": 1,
                            "eventFinish": val.event_finish,
                            "eventStart": val.event_start,
                            "eventStatus": val.event_status
                        });
                    });
                    return payload;
                };

                var addReviewComment = function (exam, attemptCodes, stopAttemptsAction) {
                    stopAttemptsAction = stopAttemptsAction || false;
                    $uibModal.open({
                        animation: true,
                        templateUrl: 'reviewContent.html',
                        controller: 'ReviewCtrl',
                        size: 'lg',
                        resolve: {
                            params: {
                                exam: exam,
                                attemptCodes: attemptCodes,
                                review_type: 'personal',
                                okCallback: function(commentObj) {
                                    wsData.addComments(attemptCodes, commentObj);
                                },
                                errorCallback: function() {},
                                statuses: $scope.statuses,
                                readOnlyMode: $scope.readOnlyMode,
                                cancelBtnText: stopAttemptsAction ? i18n.translate('WITHOUT_COMMENTS') : i18n.translate('CANCEL')
                            }
                        }
                    });
                };

                var sendReview = function (exam, status) {
                    if (exam.review_sent !== true) {
                        Api.send_review(getReviewPayload(exam, status)).then(function () {
                            exam.review_sent = true;
                        }, function () {
                            exam.btnDisabled = false;
                            showServerError();
                        });
                    } else {
                        exam.btnDisabled = false;
                    }
                };

                var sendBatchReview = function (codes, status, onErrorCallback, onSuccessCallback) {
                    var sendNextReview = function(i) {
                        if (i < codes.length) {
                            var exam = wsData.findAttempt(codes[i]);
                            if (exam.review_sent !== true) {
                                Api.send_review(getReviewPayload(exam, status)).then(function () {
                                    exam.review_sent = true;
                                    sendNextReview(i+1);
                                }, function () {
                                    exam.btnDisabled = false;
                                    if (onErrorCallback) {
                                        onErrorCallback();
                                    }
                                });
                            } else {
                                exam.btnDisabled = false;
                                sendNextReview(i+1);
                            }
                        } else {
                            if (onSuccessCallback) {
                                onSuccessCallback();
                            }
                        }
                    };

                    sendNextReview(0);
                };

                var applyBulkAction = function(actionName, selectedItems, onErrorCallback, onSuccessCallback,
                                               beforeStartFunc) {
                    var lstUpdate = [];
                    var attemptsParam = [];
                    var newStatus = (actionName === 'set_passed') ? 'Clean'
                        : ((actionName === 'set_not_passed') ? 'Suspicious' : null);

                    angular.forEach(selectedItems, function(st, code) {
                        var at = wsData.findAttempt(code);
                        lstUpdate.push(code);
                        attemptsParam.push({
                            attempt_code: code,
                            user_id: at.orgExtra.userID,
                            action: 'submit'
                        });
                    });

                    if (actionName === 'activate') {
                        if (beforeStartFunc) {
                            beforeStartFunc();
                        }
                        wsData.setDisabled(lstUpdate, true);
                        Api.start_all_exams(lstUpdate)
                            .then(
                                function () {
                                    if (onSuccessCallback) {
                                        onSuccessCallback();
                                    }
                                },
                                function () {
                                    wsData.setDisabled(lstUpdate, false);
                                    showServerError();
                                    if (onErrorCallback) {
                                        onErrorCallback();
                                    }
                                });
                    } else if (actionName === 'stop') {
                        $uibModal.open({
                            animation: true,
                            templateUrl: 'windowConfirmation.html',
                            controller: 'WindowConfirmationCtrl',
                            size: 'md',
                            resolve: {
                                data: {
                                    title: i18n.translate('WARNING'),
                                    description: i18n.translate('STOP_ATTEMPTS'),
                                    okFunc: function() {
                                        if (beforeStartFunc) {
                                            beforeStartFunc();
                                        }
                                        wsData.setDisabled(lstUpdate, true);
                                        Api.stop_all_exam_attempts(attemptsParam).then(
                                            function () {
                                                if (onSuccessCallback) {
                                                    onSuccessCallback();
                                                }
                                                addReviewComment(null, lstUpdate, true);
                                            }, function () {
                                                wsData.setDisabled(lstUpdate, false);
                                                showServerError();
                                                if (onErrorCallback) {
                                                    onErrorCallback();
                                                }
                                            });
                                    }
                                }
                            }
                        });
                    } else if ((actionName === 'set_passed') || (actionName === 'set_not_passed')) {
                        $uibModal.open({
                            animation: true,
                            templateUrl: 'windowConfirmation.html',
                            controller: 'WindowConfirmationCtrl',
                            size: 'md',
                            resolve: {
                                data: {
                                    title: i18n.translate('WARNING'),
                                    description: (actionName === 'set_passed') ? i18n.translate('MARK_ATTEMPTS_AS_PASSED')
                                        : i18n.translate('MARK_ATTEMPTS_AS_NOT_PASSED'),
                                    okFunc: function() {
                                        if (beforeStartFunc) {
                                            beforeStartFunc();
                                        }
                                        wsData.setDisabled(lstUpdate, true);
                                        sendBatchReview(lstUpdate, newStatus, function() {
                                            wsData.setDisabled(lstUpdate, false);
                                            showServerError();
                                            if (onErrorCallback) {
                                                onErrorCallback();
                                            }
                                        }, onSuccessCallback);
                                    }
                                }
                            }
                        });
                    }
                };

                if (session && !$scope.readOnlyMode) {
                    $interval(function () {
                        $scope.session_duration = TestSession.getSessionDuration();
                    }, 1000);
                }

                // get student exams from session
                if (students !== undefined) {
                    angular.forEach(students.data, function (attempt) {
                        wsData.addNewAttempt(attempt);
                    });
                }

                $scope.$on('$routeChangeStart', function($event, next, current) {
                    if (!$scope.readOnlyMode) {
                        WS.disconnect();
                    }
                    wsData.clear();
                    TestSession.flush();
                });

                // Start SockJS (websocket) connection
                if (!$scope.readOnlyMode) {
                    WS.init(session.course_event_id, wsData.websocket_callback, true,
                        function(attempt, prevStatus, code, newStatus) {
                            if (attempt.checked) {
                                updateStatusForCheckedItems();
                            }
                            $scope.gridActions.refresh();
                        },
                        function(wsCallback) {
                            // fallback function in case if SockJS connection is failed
                            Api.restore_session().then(function(response) {
                                angular.forEach(response.data, function (attempt) {
                                    var item = wsData.findAttempt(attempt.examCode);
                                    if (!item) {
                                        wsData.addNewAttempt(attempt);
                                    }
                                    if (item && item.hasOwnProperty('comments') && attempt.comments
                                        && (item.comments.length < attempt.comments.length)) {
                                        item.comments = attempt.comments.slice();
                                    }
                                });
                                if (Polling.get_attempts().length > 0) {
                                    Polling.fetch_statuses(true).then(function(response) {
                                        angular.forEach(response.data, function (attempt) {
                                            wsData.updateAttemptStatus(attempt.code, attempt.status, attempt.updated);
                                        });
                                        wsCallback();
                                    }, function() {
                                        wsCallback();
                                    });
                                } else {
                                    wsCallback();
                                }
                            }, function() {
                                wsCallback();
                            });
                        }, true);
                }

                $scope.studentsGridOptions.data = wsData.attempts;
                $scope.statusesCounters = wsData.counters;
                initCheckedItems();
            }]);

    angular.module('proctor').controller('ReviewCtrl', function ($scope, $uibModalInstance, i18n, TestSession, Api,
                                                                 DateTimeService, params) {
        var session = TestSession.getSession();
        var okCallback = params.okCallback;
        var errorCallback = params.errorCallback;

        $scope.exam = params.exam;

        $scope.courseInfo = session.course_id.split('+');
        $scope.startDate = moment(session.start_date).format('DD.MM.YYYY HH:mm');
        $scope.course_name = session.course_name;
        $scope.exam_name = session.exam_name;
        $scope.test_center = session.testing_center;

        $scope.review_type = params.review_type;
        $scope.errorMsg = '';
        $scope.requestInProgress = false;
        $scope.readOnlyMode = params.readOnlyMode;
        $scope.statuses = params.statuses;
        $scope.cancelBtnText = params.cancelBtnText;

        $scope.available_statuses_dict = {
            comment: i18n.translate('COMMENT'),
            warning: i18n.translate('SUSPICIOUS')
        };

        $scope.available_statuses = [{
            type: 'comment',
            status: $scope.available_statuses_dict['comment']
        }];
        if ($scope.review_type === 'personal') {
            $scope.available_statuses.push({
                type: 'warning',
                status: $scope.available_statuses_dict['warning']
            });
        }
        $scope.comment = {
            type: $scope.available_statuses[0].type,
            message: ""
        };

        $scope.ok = function () {
            var dt = new Date();
            var timestamp = dt.getTime();

            $scope.errorMsg = '';
            $scope.requestInProgress = true;

            if ($scope.review_type === 'session') {
                TestSession.endSession($scope.comment.message).then(
                    function () {
                        $uibModalInstance.close();
                        if (okCallback) {
                            okCallback();
                        }
                    },
                    function () {
                        $scope.requestInProgress = false;
                        $scope.errorMsg = i18n.translate('SOMETHING_WRONG');
                        if (errorCallback) {
                            errorCallback();
                        }
                    }
                );
            } else {
                var obj = {
                    comment: $scope.comment.message,
                    duration: 1,
                    event_finish: parseInt(timestamp / 1000),
                    event_start: parseInt(timestamp / 1000),
                    event_type: $scope.comment.type,
                    event_status: $scope.available_statuses_dict[$scope.comment.type]
                };
                Api.save_comment(params.attemptCodes, obj).then(
                    function () {
                        $uibModalInstance.close();
                        if (okCallback) {
                            okCallback(obj);
                        }
                    },
                    function () {
                        $scope.requestInProgress = false;
                        $scope.errorMsg = i18n.translate('SOMETHING_WRONG');
                        if (errorCallback) {
                            errorCallback();
                        }
                    }
                );
            }
        };

        $scope.cancel = function () {
            $uibModalInstance.close();
        };

        $scope.i18n = function (text) {
            return i18n.translate(text);
        };

        $scope.get_date = function () {
            return DateTimeService.get_now_date();
        };

        $scope.get_time = function () {
            return DateTimeService.get_now_time();
        };
    });
})();
