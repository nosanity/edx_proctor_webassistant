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

        this.stop_all = function(){
            $interval.cancel(timer);
        };

        this.start = function(){
            timer = $interval(function(){
                get_status();
            }, 5000);
        };

        this.add_item = function(key){
            attempts.push(key);
        };

        this.run = function(key){
            self.stop_all();
            self.start();
        };

        this.fetch_statuses = function (needResult) {
            return Api.get_exams_status(attempts, needResult);
        };
    }

    polling.$inject = ['$interval', 'Api'];
})();
