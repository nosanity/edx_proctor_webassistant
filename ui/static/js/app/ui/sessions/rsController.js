(function () {
    angular.module('proctor').controller('SessionCtrl', function ($scope, $location, data, TestSession, DateTimeService, $uibModal) {
        $scope.courses = [];
        $scope.exams = [];
        $scope.session = {};

        DateTimeService.start_timer();
        $scope.$watch(function () {
            return DateTimeService.value;
        }, function (val) {
            $scope.date = val;
        }, true);


        if (data.data.results !== undefined && data.data.results.length) {
            var c_list = [];
            angular.forEach(data.data.results, function (val, key) {
                if (val.proctored_exams.length && val.has_access === true) {
                    c_list.push({name: val.name, id: val.id});
                }
            });
            $scope.courses = c_list;
            if ($scope.courses.length)
                $scope.session.course = c_list[0].id;
        }

        $scope.$watch('session.course', function (val) {
            if (data.data.results !== undefined && data.data.results.length) {
                var e_list = $.grep(data.data.results, function (e) {
                    return e.id == val;
                });
                if (e_list.length) {
                    $scope.exams = e_list[0].proctored_exams;
                    if ($scope.exams.length) {
                        $scope.session.exam = e_list[0].proctored_exams[0].id;
                    }
                }
            }
        });

        $scope.show_session_create_error = function (exam) {

            $uibModal.open({
                animation: true,
                templateUrl: 'sessionCreateError.html',
                controller: 'SessionErrorCtrl',
                size: 'lg',
                resolve: {
                    exam: exam
                }
            });
        };

        $scope.start_session = function () {
            TestSession.registerSession(
                $scope.session.testing_centre,
                $scope.session.course,
                $scope.session.exam,
                $.grep($scope.courses, function (e) {
                    return e.id == $scope.session.course
                })[0].name,
                $.grep($scope.exams, function (e) {
                    return e.id == $scope.session.exam
                })[0].exam_name
            )
                .then(function (data) {
                    if (data) {
                        if (data.created) {
                            $location.path('/');
                        } else {
                            $scope.show_session_create_error(data.exam);
                        }
                    }
                }, function () {

                });
        };

        $scope.$on('$locationChangeStart', function (event, next, current) {
            DateTimeService.stop_timer();
        });

    });

    angular.module('proctor').controller('SessionErrorCtrl', function ($scope, $uibModalInstance, DateTimeService, i18n, exam) {
        $scope.exam = exam;
        $scope.examLink = window.location.origin + '/session/' + exam.hash_key;

        $scope.ok = function () {
            $uibModalInstance.close();
            window.location.href = $scope.examLink;
        };

        $scope.cancel = function () {
            $uibModalInstance.close();
        };

        $scope.i18n = function (text) {
            return i18n.translate(text);
        };
    });
})();
