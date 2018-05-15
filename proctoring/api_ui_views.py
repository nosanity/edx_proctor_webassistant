"""
Views for UI application
"""
# -*- coding: utf-8 -*-
import json
from datetime import datetime, timedelta

from rest_framework import viewsets, status, mixins
from rest_framework.authentication import BasicAuthentication
from rest_framework.generics import get_object_or_404
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.exceptions import ValidationError

from django.conf import settings
from django.shortcuts import redirect

from edx_proctor_webassistant.web_soket_methods import send_notification
from edx_proctor_webassistant.auth import (CsrfExemptSessionAuthentication,
                                           SsoTokenAuthentication,
                                           IsProctor, IsProctorOrInstructor)
from edx_proctor_webassistant.rest_framework import PaginationBy25
from journaling.models import Journaling
from proctoring import models
from proctoring.serializers import (EventSessionSerializer, CommentSerializer,
                                    ArchivedEventSessionSerializer)
from proctoring.edx_api import (start_exam_request, stop_exam_request,
                                poll_statuses_attempts_request, poll_status,
                                send_review_request,
                                get_proctored_exams_request,
                                bulk_start_exams_request)


def _get_status(code):
    """
    Get exam status calling EdX API
    :param code: str
    :return: str
    """
    try:
        res = poll_status(code)
        ret_data = res.json()
        return ret_data['status']
    except:
        pass


class StartExam(APIView):
    """
    Start Exam endpoint
    Supports only GET request
    """
    authentication_classes = (SsoTokenAuthentication,)
    permission_classes = (IsAuthenticated, IsProctor)

    def get(self, request, attempt_code):
        """
        Endpoint for exam start
        Exam code sends in the end of URL
        """
        exam = get_object_or_404(
            models.Exam.objects.by_user_perms(request.user),
            exam_code=attempt_code
        )
        response = start_exam_request(exam.exam_code)
        if response.status_code == 200:
            models.Exam.objects.filter(id=exam.id).update(
                exam_status=exam.STARTED,
                proctor=request.user
            )
            Journaling.objects.create(
                journaling_type=Journaling.EXAM_STATUS_CHANGE,
                event=exam.event,
                exam=exam,
                proctor=request.user,
                note="%s -> %s" % (exam.NEW, exam.STARTED)
            )
            data = {
                'hash': exam.generate_key(),
                'proctor': exam.proctor.username if exam.proctor else None,
                'status': exam.attempt_status,
                'code': attempt_code
            }
        else:
            data = {'error': 'Edx response error. See logs'}
        return Response(data=data, status=response.status_code)


def _stop_attempt(code, action, user_id):
    """
    Stop exam using EdX API
    Send `max_retries` request until status won't be `submitted`
    :param code: str
    :param action: str
    :param user_id: int
    :return: tuple (response data and status)
    """
    max_retries = 3
    attempt = 0
    response = stop_exam_request(code, action, user_id)
    current_status = _get_status(code)
    while attempt < max_retries and current_status != 'submitted':
        response = stop_exam_request(code, action, user_id)
        current_status = _get_status(code)
        attempt += 1
    return response, current_status


class StopExam(APIView):
    """
    Stop Exam endpoint
    Supports only PUT request
    """
    authentication_classes = (SsoTokenAuthentication,
                              CsrfExemptSessionAuthentication)
    permission_classes = (IsAuthenticated, IsProctor)

    def put(self, request, attempt_code):
        """
        Endpoint for exam stops. Attempt code sends in url.
        POST parameters:
            {
                'hash': "hash_key",
                'status': "submitted"
            }
        """
        exam = get_object_or_404(
            models.Exam.objects.by_user_perms(request.user),
            exam_code=attempt_code
        )
        action = request.data.get('action')
        user_id = request.data.get('user_id')
        if action and user_id:
            response, current_status = _stop_attempt(attempt_code, action,
                                                     user_id)
            if response.status_code == 200:
                models.Exam.objects.filter(id=exam.id).update(
                    exam_status=exam.STOPPED,
                    proctor=request.user
                )
                data = {
                    'hash': exam.generate_key(),
                    'status': current_status,
                    'code': attempt_code
                }
            else:
                data = {'error': 'Edx response error. See logs'}
            return Response(status=response.status_code, data=data)
        else:
            return Response(status=status.HTTP_400_BAD_REQUEST)


class StopExams(APIView):
    """
    Bulk exams stop endpoint
    Support only PUT reqest
    """
    authentication_classes = (SsoTokenAuthentication,
                              CsrfExemptSessionAuthentication)
    permission_classes = (IsAuthenticated, IsProctor)

    def put(self, request):
        """
        Endpoint for exams stop
        """
        attempts = request.data.get('attempts')
        if isinstance(attempts, str):
            attempts = json.loads(attempts)
        if attempts:
            status_list = []
            for attempt in attempts:
                exam = get_object_or_404(
                    models.Exam.objects.by_user_perms(request.user),
                    exam_code=attempt['attempt_code']
                )
                user_id = attempt.get('user_id')
                action = attempt.get('action')
                if action and user_id:
                    response, current_status = _stop_attempt(
                        attempt['attempt_code'], action, user_id
                    )
                    if response.status_code == 200:
                        models.Exam.objects.filter(id=exam.id).update(
                            exam_status=exam.STOPPED,
                            proctor=request.user
                        )
                    else:
                        status_list.append(response.status_code)
                else:
                    return Response(status=status.HTTP_400_BAD_REQUEST)
            if status_list:
                return Response(status=status.HTTP_500_INTERNAL_SERVER_ERROR)
            return Response(status=status.HTTP_200_OK)
        else:
            return Response(status=status.HTTP_400_BAD_REQUEST)


class PollStatus(APIView):
    """
    Endpoint for getting status
    Supports only POST method
    """
    authentication_classes = (SsoTokenAuthentication,
                              CsrfExemptSessionAuthentication)
    permission_classes = (IsAuthenticated, IsProctor)

    def post(self, request):
        """
        Get statuses for list of exams

        Request example:

        ```
        {"list":["code1","code2"]}
        ```
        """
        data = request.data.copy()
        result_in_response = request.GET.get('result')
        result = [] if result_in_response else None
        if 'list' in data and data['list']:
            exams = models.Exam.objects.by_user_perms(request.user)\
                .filter(exam_code__in=data['list'])\
                .select_related('event')
            codes_dict = {exam.exam_code: exam for exam in exams}
            if codes_dict:
                response = poll_statuses_attempts_request(list(codes_dict.keys()))
                for attempt_code, new_status in response.items():
                    exam = codes_dict.get(attempt_code, None)
                    if exam and new_status:
                        if exam.attempt_status != new_status:
                            data = {
                                'hash': exam.generate_key(),
                                'status': exam.attempt_status,
                                'code': attempt_code
                            }
                            if exam.attempt_status == 'ready_to_start' and new_status == 'started':
                                exam.actual_start_date = datetime.now()
                            if (exam.attempt_status == 'started' and new_status == 'submitted') \
                              or (exam.attempt_status == 'ready_to_submit' and new_status == 'submitted'):
                                dt_end = datetime.now()
                                exam.actual_end_date = dt_end
                                data['actual_end_date'] = dt_end.isoformat() + 'Z'
                            exam.attempt_status = new_status
                            exam.attempt_status_updated = datetime.now()
                            exam.last_poll = datetime.now()
                            exam.save()
                            if not result_in_response:
                                send_notification(data, channel=exam.event.course_event_id)
                        if result_in_response:
                            result.append({'code': attempt_code, 'status': exam.attempt_status,
                                           'updated': exam.attempt_status_updated.timestamp()})
            return Response(data=result, status=status.HTTP_200_OK) if result_in_response\
                else Response(status=status.HTTP_200_OK)
        else:
            return Response(status=status.HTTP_400_BAD_REQUEST)


class EventSessionViewSet(mixins.ListModelMixin,
                          mixins.CreateModelMixin,
                          mixins.RetrieveModelMixin,
                          mixins.UpdateModelMixin,
                          viewsets.GenericViewSet):
    """
    Event management API

    For **create** send `testing_center`,`course_id`,`course_event_id`
    Other fields filling automatically

    You can **update** only `status` and `notify` fields
    """
    serializer_class = EventSessionSerializer
    queryset = models.EventSession.objects.all()
    authentication_classes = (SsoTokenAuthentication,
                              CsrfExemptSessionAuthentication,
                              BasicAuthentication)
    permission_classes = (IsAuthenticated, IsProctor)

    def get_queryset(self):
        """
        This view should return a list of all the purchases for
        the user as determined by the username portion of the URL.
        """
        hash_key = self.request.query_params.get('session')
        if hash_key:
            queryset = models.EventSession.objects.filter(
                hash_key=hash_key)
            queryset = models.EventSession.update_queryset_with_permissions(
                queryset, self.request.user
            )
        else:
            queryset = models.EventSession.objects.all()
        return queryset

    def create(self, request, *args, **kwargs):
        """
        Create endpoint for event session
        Validate session and check user permissions before create
        """
        fields_for_create = [
            'testing_center',
            'course_id',
            'course_event_id',
            'exam_name'
        ]
        data = {}

        for field in fields_for_create:
            if field == 'course_id':
                if request.data.get('course'):
                    course = models.Course.objects.get(
                        pk=request.data.get('course'))
                else:
                    course = models.Course.create_by_course_run(
                        request.data.get(field))
                course.course_name = request.data.get('course_name')
                course.save()
                data['course'] = course.pk
            else:
                data[field] = request.data.get(field)
        # Return existing session if match test_center, course_id and exam_id
        # so the proctor is able to connect to existing session
        data['status'] = models.EventSession.IN_PROGRESS
        sessions = models.InProgressEventSession.objects.filter(
            course_event_id=data.get('course_event_id'),
            course=course.pk
        ).order_by('-start_date')
        if sessions:
            session = sessions[0]
            serializer = EventSessionSerializer(session)
            return Response(serializer.data,
                            status=status.HTTP_200_OK,
                            headers=self.get_success_headers(serializer.data))
        # else create session
        data['proctor'] = request.user.pk
        serializer = self.get_serializer(data=data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        Journaling.objects.create(
            journaling_type=Journaling.EVENT_SESSION_START,
            event=serializer.instance,
            proctor=request.user,
        )
        headers = self.get_success_headers(serializer.data)
        return Response(serializer.data,
                        status=status.HTTP_201_CREATED,
                        headers=headers)

    def partial_update(self, request, *args, **kwargs):
        """
        Endpoint for status, notify and comment updates
        """
        instance = self.get_object()
        fields_for_update = ['status', 'notify', 'comment']
        data = {}

        for field in fields_for_update:
            data[field] = request.data.get(field)
        change_end_date = instance.status == models.EventSession.IN_PROGRESS \
                          and data.get('status') == models.EventSession.ARCHIVED

        if change_end_date:
            exams = models.Exam.objects.by_user_perms(self.request.user).filter(event=instance)\
                .exclude(attempt_status__in=settings.FINAL_ATTEMPT_STATUSES)
            if len(exams) > 0:
                return Response(status=status.HTTP_403_FORBIDDEN)

        if str(instance.status) != data.get('status', ''):
            Journaling.objects.create(
                journaling_type=Journaling.EVENT_SESSION_STATUS_CHANGE,
                event=instance,
                proctor=request.user,
                note="%s -> %s" % (instance.status, data.get('status', ''))
            )
        serializer = self.get_serializer(instance, data=data, partial=True)
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)
        if change_end_date:
            event_session = models.ArchivedEventSession.objects.get(
                pk=instance.pk)
            event_session.end_date = datetime.now()
            event_session.save()
            serializer = self.get_serializer(event_session)
            ws_data = {
                'session_id': event_session.id,
                'end_session': change_end_date
            }
            send_notification(ws_data, channel=instance.course_event_id)
        return Response(serializer.data)


class ArchivedEventSessionViewSet(mixins.ListModelMixin,
                                  viewsets.GenericViewSet):
    """
    Return list of Archived Event session with pagiantion.

    You can filter results by `testing_center`, `proctor`, `hash_key`,
    `course_id`, `course_event_id`, `start_date`, `end_date`

    Add GET parameter in end of URL, for example:
    `?start_date=2015-12-04&proctor=proctor_username`
    """
    serializer_class = ArchivedEventSessionSerializer
    queryset = models.ArchivedEventSession.objects.order_by('-pk')
    pagination_class = PaginationBy25
    authentication_classes = (SsoTokenAuthentication,
                              CsrfExemptSessionAuthentication,
                              BasicAuthentication)
    permission_classes = (IsAuthenticated, IsProctorOrInstructor)

    def get_queryset(self):
        """
        Filters for Archived Event Session List
        :return: queryset
        """
        queryset = super(ArchivedEventSessionViewSet, self).get_queryset()
        queryset = models.EventSession.update_queryset_with_permissions(
            queryset,
            self.request.user
        )
        params = self.request.query_params
        if "testing_center" in params:
            queryset = queryset.filter(testing_center=params["testing_center"])
        if "proctor" in params:
            try:
                first_name, last_name = params["proctor"].split(" ")
                queryset = queryset.filter(proctor__first_name=first_name,
                                           proctor__last_name=last_name)
            except ValueError:
                queryset = queryset.filter(proctor__username=params["proctor"])
        if "hash_key" in params:
            queryset = queryset.filter(hash_key=params["hash_key"])
        if "course_id" in params:
            try:
                course = models.Course.get_by_course_run(params["course_id"])
                queryset = queryset.filter(course=course)
            except models.Course.DoesNotExist:
                queryset = queryset.filter(pk__lt=0)
        if "course_event_id" in params:
            queryset = queryset.filter(
                course_event_id=params["course_event_id"])
        if "start_date" in params:
            try:
                query_date = datetime.strptime(params["start_date"],
                                               "%Y-%m-%d")
                queryset = queryset.filter(
                    start_date__gte=query_date,
                    start_date__lt=query_date + timedelta(days=1)
                )
            except ValueError:
                pass
        if "end_date" in params:
            try:
                query_date = datetime.strptime(params["end_date"], "%Y-%m-%d")
                queryset = queryset.filter(
                    end_date__gte=query_date,
                    end_date__lt=query_date + timedelta(
                        days=1)
                )
            except ValueError:
                pass
        return queryset


class ArchivedEventSessionAllViewSet(ArchivedEventSessionViewSet):
    pagination_class = None


class Review(APIView):
    """
    POST Request example:

    ```
    {
        "examMetaData": {
            "examCode": "C27DE6D1-39D6-4147-8BE0-9E9440D4A971"
        },
         "reviewStatus": "Clean",
         "videoReviewLink": "http://video.url",
         "desktopComments": [ ]
    }
    ```

    """
    authentication_classes = (SsoTokenAuthentication,
                              CsrfExemptSessionAuthentication,
                              BasicAuthentication)
    permission_classes = (IsAuthenticated, IsProctor)

    # EDX can ignore review post save procedure
    # that will result in `Pending` status for student
    # so we need to send review few times
    max_resend_attempts = 3

    def post(self, request):
        """
        Passing review statuses:  `Clean`, `Rules Violation`
        Failing review status: `Not Reviewed`, `Suspicious`
        """
        payload = request.data.copy()
        required_fields = ['examMetaData', 'reviewStatus', 'videoReviewLink',
                           'desktopComments']
        for field in required_fields:
            if field not in payload:
                return Response(status=status.HTTP_400_BAD_REQUEST)

        if isinstance(payload['examMetaData'], str):
            payload['examMetaData'] = json.loads(payload['examMetaData'])
        if isinstance(payload['desktopComments'], str):
            payload['desktopComments'] = json.loads(payload['desktopComments'])
        exam = get_object_or_404(
            models.Exam.objects.by_user_perms(request.user),
            exam_code=payload['examMetaData'].get('examCode', '')
        )

        payload['examMetaData'].update(
            {
                "ssiRecordLocator": exam.generate_key(),
                "reviewerNotes": ""
            }
        )

        for comment in payload['desktopComments']:
            try:
                models.Comment.objects.get(
                    comment=comment.get('comments'),
                    event_status=comment.get('eventStatus'),
                    exam=exam
                )
            except models.Comment.DoesNotExist:
                models.Comment.objects.get_or_create(
                    comment=comment.get('comments'),
                    event_status=comment.get('eventStatus'),
                    event_start=int(comment.get('eventStart')),
                    event_finish=int(comment.get('eventFinish')),
                    duration=comment.get('duration'),
                    exam=exam
                )

        response, current_status = self.send_review(payload)
        models.Exam.objects.filter(id=exam.id).update(
            proctor=request.user
        )

        return Response(
            status=response.status_code
        )

    @staticmethod
    def _sent(_status):
        """
        Check is review sent
        :param _status: str
        :return: bool
        """
        return _status in ['verified', 'rejected']

    def send_review(self, payload):
        attempt = 0
        code = payload['examMetaData']['examCode']
        response = send_review_request(payload)
        current_status = _get_status(code)
        while attempt < self.max_resend_attempts \
            and not self._sent(current_status):
            response = send_review_request(payload)
            current_status = _get_status(code)
            attempt += 1
        return response, current_status


class GetExamsProctored(APIView):
    """
    Endpoint for getting all Courses with proctored exams
    Supports only GET request
    """

    def get(self, request):
        response = get_proctored_exams_request()
        try:
            content = response.json()
        except ValueError:
            content = {}
        permissions = request.user.permission_set.all()
        results = []
        orgs = []
        for row in content.get('results', []):
            if 'proctored_exams' in row and row['proctored_exams']:
                row['has_access'] = models.has_permission_to_course(
                    request.user, row.get('id'), permissions)
                if 'org' in row:
                    row['org_description'] = row['org']
                    results.append(row)
                    if row['org'] not in orgs:
                        orgs.append(row['org'])
        if orgs:
            orgs_descriptions = {item.slug: item.description
                                 for item in models.OrgDescription.objects.filter(slug__in=orgs)}
            for i, res in enumerate(results):
                if res['org'] in orgs_descriptions:
                    results[i]['org_description'] = orgs_descriptions[res['org']]
        current_active_sessions = models.InProgressEventSession.objects.filter(
            proctor=request.user
        ).order_by('-start_date')

        return Response(
            status=response.status_code,
            data={"results": results,
                  "current_active_sessions": [EventSessionSerializer(sess).data for sess in current_active_sessions]}
        )


class BulkStartExams(APIView):
    """
    Bulk exams start endpoint
    """
    authentication_classes = (SsoTokenAuthentication,
                              CsrfExemptSessionAuthentication)
    permission_classes = (IsAuthenticated, IsProctor)

    def post(self, request):
        """
        Start list of exams by exam codes.

        Request example

            {
                "list":['<exam_id_1>','<exam_id_2>']
            }

        """
        exam_codes = request.data.get('list', [])
        exam_list = models.Exam.objects.filter(exam_code__in=exam_codes)
        items = bulk_start_exams_request(exam_list)
        ids_list = []
        for exam in items:
            ids_list.append(exam.id)
        models.Exam.objects.filter(id__in=ids_list).update(
            exam_status=exam.STARTED,
            proctor=request.user
        )

        Journaling.objects.create(
            journaling_type=Journaling.BULK_EXAM_STATUS_CHANGE,
            note="%s. %s -> %s" % (
                exam_codes, models.Exam.NEW, models.Exam.STARTED
            ),
            proctor=request.user,
        )
        return Response(status=status.HTTP_200_OK)


def redirect_ui(request):
    """
    Redirect when Angular html5 mode enabled
    """
    return redirect('/#{}'.format(request.path))


class Comment(APIView):
    """
    Add comment to exams.

    """
    authentication_classes = (SsoTokenAuthentication,
                              CsrfExemptSessionAuthentication,
                              BasicAuthentication)
    permission_classes = (IsAuthenticated, IsProctor)

    def post(self, request):
        comment = request.data.get('comment')
        if isinstance(comment, str):
            comment = json.loads(comment)
        exam_codes = request.data.get('codes', [])
        if isinstance(exam_codes, str):
            exam_codes = json.loads(exam_codes)
        for code in exam_codes:
            exam = get_object_or_404(
                models.Exam.objects.by_user_perms(request.user),
                exam_code=code
            )
            exam_comment = comment.copy()
            exam_comment['exam'] = exam.pk
            if 'event_start' in exam_comment:
                exam_comment['event_start'] = int(exam_comment['event_start'])
            if 'event_finish' in comment:
                exam_comment['event_finish'] = int(exam_comment['event_finish'])
            serializer = CommentSerializer(data=exam_comment)
            try:
                serializer.is_valid(raise_exception=True)
            except ValidationError as e:
                return Response(e.detail, status=status.HTTP_400_BAD_REQUEST)
            serializer.save()
            send_notification(serializer.data, channel=exam.event.course_event_id)

            # comment journaling
            Journaling.objects.create(
                journaling_type=Journaling.EXAM_COMMENT,
                event=exam.event,
                exam=exam,
                proctor=request.user,
                note="""
                    Duration: %s
                    Event start: %s
                    Event finish: %s
                    eventStatus": %s
                    Comment:
                    %s
                """ % (
                    serializer.data.get('duration'),
                    int(serializer.data.get('event_start')) if serializer.data.get('event_start') else None,
                    int(serializer.data.get('event_finish')) if serializer.data.get('event_finish') else None,
                    serializer.data.get('event_status'),
                    serializer.data.get('comment'),
                ),
            )
        return Response(status=status.HTTP_201_CREATED)
