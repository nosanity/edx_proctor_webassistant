'use strict';

/**
 *
 * Main module of the application.
 */
(function () {
    var app = angular.module('proctor', [
        'ngRoute',
        'ngCookies',
        'ngAnimate',
        'ngSanitize',
        'ui.bootstrap',
        'checklist-model',
        'proctor.i18n',
        'proctor.api',
        'proctor.session',
        'proctor.date',
        'websocket',
        'pascalprecht.translate',
        'tokenAuth',
        'dataGrid',
        'pagination'
    ]);
    app.config(function ($routeProvider,
                         $controllerProvider,
                         $locationProvider,
                         $compileProvider,
                         $filterProvider,
                         $provide,
                         $httpProvider,
                         $translateProvider,
                         $translateLocalStorageProvider,
                         $interpolateProvider) {

        // Redefine angular entities for lazy loading feature
        app.controller = $controllerProvider.register;
        app.directive = $compileProvider.directive;
        app.routeProvider = $routeProvider;
        app.filter = $filterProvider.register;
        app.service = $provide.service;
        app.factory = $provide.factory;

        app.path = window.app.rootPath;
        app.language = {
            // current: (window.localStorage['NG_TRANSLATE_LANG_KEY'] !== undefined && window.localStorage['NG_TRANSLATE_LANG_KEY']) ? window.localStorage['NG_TRANSLATE_LANG_KEY'] : 'en',
            current: window.app.spaConfig.language,
            supported: ['en', 'ru']
        };

        $locationProvider.html5Mode(true);

        delete $httpProvider.defaults.headers.common['X-Requested-With'];

        $interpolateProvider.startSymbol('{[');
        $interpolateProvider.endSymbol(']}');

        var translateSuffix = '.json';

        if (app.language.current in window.app.langs) {
            var langFileName = window.app.langs[app.language.current].split('/');
            var langFileNameArr = langFileName.pop().split('.');
            if (langFileNameArr.length === 3) {
                translateSuffix = '.' + langFileNameArr[1] + '.' + langFileNameArr[2];
            }
        }

        // I18N
        $translateProvider.useStaticFilesLoader({
            prefix: app.path + 'i18n/',
            suffix: translateSuffix
        });
        $translateProvider.preferredLanguage(app.language.current);
        $translateProvider.useSanitizeValueStrategy('sanitize');
        $translateProvider.useLocalStorage();

        // Decorators for modals and popups
        // Redefine bootstrap ui templates
        $provide.decorator('uibModalBackdropDirective', function ($delegate) {
            $delegate[0].templateUrl = window.app.templates.backdrop;
            return $delegate;
        });
        $provide.decorator('uibModalWindowDirective', function ($delegate) {
            $delegate[0].templateUrl = window.app.templates.window;
            return $delegate;
        });
        $provide.decorator('uibTooltipPopupDirective', function ($delegate) {
            $delegate[0].templateUrl = window.app.templates.tooltipPopup;
            return $delegate;
        });

        $routeProvider
            .when('/', {
                templateUrl: window.app.templates.sessions,
                controller: 'SessionCtrl',
                resolve: {
                    data: function (Api) {
                        return Api.get_session_data();
                    }
                }
            })
            .when('/session/:hash', {
                templateUrl: window.app.templates.home,
                controller: 'MainCtrl',
                resolve: {
                    students: function ($location, $route, $q, TestSession, Api, Auth) {
                        var deferred = $q.defer();
                        Auth.is_instructor().then(function (is) {
                            if (is) {
                                deferred.resolve();
                                $location.path('/');
                            } else {
                                TestSession
                                    .fetchSession($route.current.params.hash)
                                    .then(function() {
                                        Api.restore_session().then(function(response) {
                                            deferred.resolve(response);
                                        }, function() {
                                            deferred.resolve();
                                            $location.path('/');
                                        });
                                    }, function(reason) {
                                        if (reason.status == 403) {
                                            deferred.resolve();
                                            $location.path('/archive');
                                        }
                                    });
                            }
                        });

                        return deferred.promise;
                    }
                }
            })
            .when('/archive', {
                templateUrl: window.app.templates.archive,
                controller: 'ArchCtrl',
                resolve: {
                    events: function (Api, $location) {
                        return Api.get_archived_events().then(function(response) {
                            return response;
                        }, function(err) {
                            console.error(err);
                            $location.path('/index');
                            return { resolveError : err }
                        });
                    },
                    courses_data: function (Api, $location) {
                        return Api.get_session_data().then(function(response) {
                            return response
                        }, function(err) {
                            console.error(err);
                            $location.path('/index');
                            return { resolveError : err }
                        });
                    }
                }
            })
            .when('/archive/:hash', {
                templateUrl: window.app.templates.archiveSessions,
                controller: 'ArchAttCtrl',
                resolve: {
                    sessions: function ($route, Api) {
                        return Api.get_archived_sessions($route.current.params.hash).then(function(response) {
                            return response
                        }, function(err) {
                            console.error(err);
                            return { resolveError: err }
                        });
                    }
                }
            })
            .when('/profile', {
                templateUrl: window.app.templates.profile,
                controller: 'ProfileCtrl',
                resolve: {
                    me: function (Auth) {
                        return true;
                    }
                }
            })
            .when('/index', {
                template: '<div>Error</div>',
                controller : 'errControler'
            })
            .otherwise({
                redirectTo: '/'
            });
    });

    app.run(['$rootScope', '$location', '$translate', function ($rootScope, $location, $translate) {
        var domain;
        var match = $location.absUrl().match(/(?:https?:\/\/)?(?:www\.)?(.*?)\//);
        if (match !== null)
            domain = match[1];
        var api_port = '', socket_port = '';
        var protocol = 'http://';
        if ("https:" == document.location.protocol) {
            protocol = 'https://';
        }
        $rootScope.apiConf = {
            domain: domain,
            protocol: protocol,
            ioServer: domain + (socket_port ? ':' + socket_port : ''),
            apiServer: protocol + domain + (api_port ? ':' + api_port : '') + '/api'
        };

        // Preload language files
        // Use only if `allow_language_change` is true
        //angular.forEach(app.language.supported, function (val) {
        //    if (val !== app.language.current) {
        //        $translate.use(val);
        //    }
        //});
    }]);

    // MAIN CONTROLLER
    app.controller('MainController', ['$scope', '$translate', '$http', 'i18n', 'TestSession', 'Auth',
        function ($scope, $translate, $http, i18n, TestSession, Auth) {

            var lng_is_supported = function (val) {
                return app.language.supported.indexOf(val) >= 0 ? true : false;
            };

            $scope.get_supported_languages = function () {
                return app.language.supported;
            };

            $scope.changeLanguage = function (langKey) {
                if (langKey == undefined) langKey = app.language.current;
                if (lng_is_supported(langKey)) {
                    $translate.use(langKey);
                    i18n.clear_cache();
                    app.language.current = langKey;
                }
            };

            $scope.sso_auth = function () {
                window.location = window.app.loginUrl;
            };

            $scope.logout = function () {
                TestSession.flush();
                window.location = window.app.logoutUrl;
            };

            $scope.i18n = function (text) {
                return i18n.translate(text);
            };

            $scope.proctorName = Auth.get_proctor();
            $scope.projectName = window.app.projectName;
            $scope.projectLogo = window.app.logo;
            $scope.myProfileUrl = window.app.myProfileUrl;
            $scope.myCoursesUrl = window.app.myCoursesUrl;

            //$scope.changeLanguage();
        }]);

    app.controller('HeaderController', ['$scope', '$location', function ($scope, $location) {
        $scope.session = function () {
            $location.path('/session');
        };
    }]);

    app.controller('WindowAlertCtrl', ['$scope', '$uibModalInstance', 'i18n', 'data',
            function ($scope, $uibModalInstance, i18n, data) {
        $scope.title = data.title;
        $scope.description = data.description;

        $scope.close = function () {
            $uibModalInstance.close();
        };

        $scope.i18n = function (text) {
            return i18n.translate(text);
        };
    }]);

    app.controller('WindowConfirmationCtrl', ['$scope', '$uibModalInstance', 'i18n', 'data',
            function ($scope, $uibModalInstance, i18n, data) {
        $scope.title = data.title;
        $scope.description = data.description;
        $scope.btnDisabled = false;

        $scope.ok = function () {
            $scope.btnDisabled = true;
            if (data.okFunc) {
                data.okFunc();
            }
            $uibModalInstance.close();
        };

        $scope.cancel = function () {
            if (!$scope.btnDisabled) {
                $uibModalInstance.close();
            }
        };

        $scope.i18n = function (text) {
            return i18n.translate(text);
        };
    }]);

    app.directive('header', [function () {
        return {
            restrict: 'E',
            templateUrl: window.app.templates.header,
            link: function (scope, e, attr) {}
        };
    }]);

    app.directive('windowAlert', [function(){
        return {
            restrict: 'E',
            templateUrl: window.app.templates.windowAlert,
            link: function(scope, e, attr) {}
        };
    }]);

    app.directive('windowConfirmation', [function(){
        return {
            restrict: 'E',
            templateUrl: window.app.templates.windowConfirmation,
            link: function(scope, e, attr) {}
        };
    }]);
})();
