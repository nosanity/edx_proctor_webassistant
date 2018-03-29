(function(){
    var app = angular.module('proctor');

    app.service('Polling', polling);

    function polling($interval, Api){
        var self = this;
        var attempts = [];
        var timer = null;

        var get_status = function(needResult){
            return Api.get_exams_status(attempts, needResult);
        };

        this.stop = function(key){
            var idx = attempts.indexOf(key);
            if (idx >= 0){
                attempts.splice(idx, 1);
            }
        };

        this.start = function(){
            timer = $interval(function(){
                get_status();
            }, 5000);
        };

        this.clear = function () {
            attempts = [];
        };

        this.add_item = function(key){
            attempts.push(key);
        };

        this.fetch_statuses = function (needResult) {
            return Api.get_exams_status(attempts, needResult);
        };
    }

    polling.$inject = ['$interval', 'Api'];
})();
