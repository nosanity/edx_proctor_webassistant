Array.prototype.in_array = function (val){
    return this.indexOf(val) >= 0;
};

Array.prototype.filterBy = function(params){
    return $.grep(this, function(e){
        var is = true;
        angular.forEach(params, function(val, key){
            is = is && e[key] == val;
        });
        return is;
    });
};

function getArchGridData(sessionsData, i18n) {
    var data = [];
    angular.forEach(sessionsData, function (val) {
        var start = moment(val.start_date);
        var end = val.end_date ? moment(val.end_date) : null;
        var dateAndTime = '';
        if (end && (start.format('YYYY MM DD') === end.format('YYYY MM DD'))) {
            dateAndTime = start.format('HH:mm') + ' - ' + end.format('HH:mm')
                            + '<br />' + start.format('DD.MM.YYYY');
        } else {
            dateAndTime = start.format('DD.MM.YYYY HH:mm') +
                ' - ' + (end ? end.format('DD.MM.YYYY HH:mm') : i18n.translate('NOT_SET'));
        }
        val.datetime = dateAndTime;
        val.datetimeFull = start.format('YYYY.MM.DD HH:mm') +
            ' - ' + (end ? end.format('YYYY.MM.DD HH:mm') : i18n.translate('NOT_SET'));
        val.searchField = val.testing_center + ' ' + val.course_name + ' ' + val.exam_name;
        data.push(val);
    });
    return data;
}

