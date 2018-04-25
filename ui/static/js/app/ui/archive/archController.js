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

        $scope.archGridOptions.data = getArchGridData(sessions.data, i18n);
    });
})();
