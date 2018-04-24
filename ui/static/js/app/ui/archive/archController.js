(function(){
    angular.module('proctor').controller('ArchCtrl', function($scope, $filter, DateTimeService, i18n, sessions) {
        $scope.archGridOptions = {
            data: [],
            sort: {
                predicate: 'id',
                direction: 'desc'
            },
            pagination: {
                itemsPerPage: '15'
            }
        };

        $scope.gotoSession = function(hash_key) {
            window.location.href = window.location.origin + '/session/' + hash_key;
        };

        var data = [];
        angular.forEach(sessions.data, function (val) {
            var start = moment(val.start_date);
            var end = val.end_date ? moment(val.end_date) : null;
            var dateAndTime = '';
            if (end && (start.format('YYYY MM DD') === end.format('YYYY MM DD'))) {
                dateAndTime = start.format('HH:mm') + ' - ' + end.format('HH:mm')
                            + '<br />' + start.format('DD.MM.YYYY');
            } else {
                dateAndTime = start.format('DD.MM.YYYY HH:mm') + ' - ' + (end ? end.format('DD.MM.YYYY HH:mm') : i18n.translate('NOT_SET'));
            }
            val.datetime = dateAndTime;
            val.datetimeFull = start.format('YYYY.MM.DD HH:mm') + ' - ' + (end ? end.format('YYYY.MM.DD HH:mm') : i18n.translate('NOT_SET'));
            val.searchField = val.testing_center + ' ' + val.course_name + ' ' + val.exam_name;
            data.push(val);
        });
        $scope.archGridOptions.data = data;
    });
})();