'use strict';
(function(){
    var app = angular.module('proctor');
    app.directive('sessionCreateError', [function(){
        return {
            restrict: 'E',
            templateUrl: app.path + 'ui/partials/session_create_error.html',
            link: function(scope, e, attr) {}
        };
    }]);
})();
