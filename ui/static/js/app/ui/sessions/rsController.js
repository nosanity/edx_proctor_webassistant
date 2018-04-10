(function () {
    angular.module('proctor').controller('SessionCtrl', function ($scope, $location, data, TestSession,
                                                                  DateTimeService, $uibModal, Api) {
        $scope.orgs = [];
        $scope.orgDetails = [];
        $scope.courses = [];
        $scope.runs = [];
        $scope.exams = [];
        $scope.chosenOrg = null;
        $scope.chosenCourse = null;
        $scope.chosenRun = null;
        $scope.chosenExam = null;
        $scope.testingCentre = '';
        $scope.startSessionInProgress = false;
        $scope.errorMsg = '';
        $scope.archGridOptions = {
            data: [],
            sort: {
                predicate: 'id',
                direction: 'desc'
            }
        };

        function checkProctoredExams(v) {
            return v.proctored_exams.length && (v.has_access === true);
        }

        function sortArr(key) {
            return function(a, b) {
                if (a[key] < b[key]) return -1;
                if (a[key] > b[key]) return 1;
                return 0;
            };
        }

        var sortOrgsArr = sortArr('name');
        var sortRunsArr = sortArr('run');
        var sortExamsArr = sortArr('exam_name');

        $scope.updateCourses = function() {
            var courses = [];
            angular.forEach(data.data.results, function (val) {
                if ((val.org === $scope.chosenOrg.key) && (courses.indexOf(val.course) === -1)
                    && checkProctoredExams(val)) {
                    courses.push(val.course);
                }
            });
            courses.sort();
            $scope.courses = courses;

            if ($scope.courses.length > 0) {
                $scope.chosenCourse = $scope.courses[0];
            }

            $scope.updateRuns();
        };

        $scope.updateRuns = function() {
            var runs = [];
            angular.forEach(data.data.results, function (val) {
                if ((val.org === $scope.chosenOrg.key) && (val.course === $scope.chosenCourse)
                    && (runs.indexOf(val.run) === -1) && checkProctoredExams(val)) {
                    runs.push(val);
                }
            });
            runs.sort(sortRunsArr);
            $scope.runs = runs;

            if ($scope.runs.length > 0) {
                $scope.chosenRun = $scope.runs[0];
            }

            $scope.updateSessions();
        };

        $scope.updateSessions = function () {
            var runs = [];
            angular.forEach(data.data.results, function (val) {
                if ((val.org === $scope.chosenOrg.key) && (val.course === $scope.chosenCourse) &&
                    (val.run === $scope.chosenRun.run) && (runs.indexOf(val.run) === -1) && checkProctoredExams(val)) {
                    $scope.exams = val.proctored_exams;
                    $scope.exams.sort(sortExamsArr);
                    $scope.chosenExam = val.proctored_exams[0];
                }
            });
            $scope.errorMsg = '';
        };

        $scope.showSessionCreateError = function (exam) {
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

        $scope.startSession = function () {
            $scope.startSessionInProgress = true;
            $scope.errorMsg = '';

            console.log($scope.testingCentre, $scope.chosenRun.id, $scope.chosenExam.id,
                $scope.chosenRun.name, $scope.chosenExam.exam_name);

            TestSession.registerSession($scope.testingCentre, $scope.chosenRun.id, $scope.chosenExam.id,
                $scope.chosenRun.name, $scope.chosenExam.exam_name, function() {
                    $scope.errorMsg = i18n.translate('SESSION_ERROR_1');
                    $scope.startSessionInProgress = false;
                }).then(function (data) {
                    $scope.startSessionInProgress = false;
                    if (data) {
                        if (data.created) {
                            $location.path('/');
                        } else {
                            $scope.showSessionCreateError(data.exam);
                        }
                    }
            }, function () {});
        };

        function getArchData() {
            Api.get_archived_events(5).then(function(response) {
                var data = [];
                angular.forEach(response.data.results, function (val) {
                    var start = moment(val.start_date);
                    var end = moment(val.end_date);
                    var dateAndTime = '';
                    if (start.format('YYYY MM DD') === end.format('YYYY MM DD')) {
                        dateAndTime = start.format('HH:mm') + ' - ' + end.format('HH:mm')
                            + '<br />' + start.format('DD.MM.YYYY');
                    } else {
                        dateAndTime = start.format('DD.MM.YYYY HH:mm') + ' - ' + end.format('DD.MM.YYYY HH:mm');
                    }
                    val.datetime = dateAndTime;
                    val.datetimeFull = start.format('YYYY.MM.DD HH:mm') + ' - ' + end.format('YYYY.MM.DD HH:mm');
                    data.push(val);
                });
                $scope.archGridOptions.data = data;
            }, function(err) {

            });
        }

        if (data.data.results !== undefined && data.data.results.length) {
            var orgs = [];
            var orgDetails = [];
            angular.forEach(data.data.results, function (val) {
                if ((orgs.indexOf(val.org) === -1) && checkProctoredExams(val)) {
                    orgs.push(val.org);
                    orgDetails.push({
                        name: val.org_description,
                        key: val.org
                    })
                }
            });
            orgs.sort();
            orgDetails.sort(sortOrgsArr);
            $scope.orgs = orgs;
            $scope.orgDetails = orgDetails;
            if ($scope.orgDetails.length > 0) {
                $scope.chosenOrg = $scope.orgDetails[0];
            }
            $scope.updateCourses();
        }

        getArchData();
    });

    angular.module('proctor').controller('SessionErrorCtrl', function ($scope, $uibModalInstance, DateTimeService,
                                                                       i18n, exam) {
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
