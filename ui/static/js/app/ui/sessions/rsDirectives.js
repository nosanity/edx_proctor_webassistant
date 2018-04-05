'use strict';
(function(){
    var app = angular.module('proctor');
    app.directive('sessionCreateError', [function(){
        return {
            restrict: 'E',
            templateUrl: window.app.templates.sessionCreateError,
            link: function(scope, e, attr) {}
        };
    }]);
})();
