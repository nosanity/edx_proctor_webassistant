'use strict';
(function(){
    var app = angular.module('proctor');
    app.directive('reviewModal', [function(){
        return {
            restrict: 'E',
            templateUrl: window.app.templates.addReview,
            link: function(scope, e, attr) {}
        };
    }]);

    app.directive('comments', [function(){
        return {
            restrict: 'E',
            templateUrl: window.app.templates.comments,
            link: function(scope, e, attr) {}
        };
    }]);
})();
