from datetime import datetime
from django.conf import settings
from django.conf.urls import url
from django.contrib import admin, messages
from django.db import transaction
from django.http import HttpResponseRedirect
from django.template.response import TemplateResponse
from django.views.decorators.csrf import csrf_protect
from django.utils.decorators import method_decorator
from django.utils.html import format_html
from django.utils.translation import ugettext_lazy as _
from django.urls import reverse
from rest_framework import status
from journaling.models import Journaling
from proctoring import models
from proctoring.edx_api import bulk_update_exams_statuses
from edx_proctor_webassistant.web_soket_methods import send_notification


csrf_protect_m = method_decorator(csrf_protect)


class CourseAdmin(admin.ModelAdmin):
    list_display = ('display_name', 'course_name')
    list_filter = ('course_org', 'course_name')
    search_fields = ('display_name', 'course_name')

    def has_add_permission(self, request):
        return False


class CommentInline(admin.TabularInline):
    """
    Comment inline class
    """
    model = models.Comment


class ExamAdmin(admin.ModelAdmin):
    """
    Exam admin class
    """
    list_display = ('exam_code', 'organization', 'exam_id', 'course',
                    'first_name', 'last_name', 'exam_status',
                    'username', 'exam_start_date', 'exam_end_date')
    list_filter = ('exam_status', 'course')
    search_fields = ['exam_code', 'exam_id', 'first_name', 'last_name',
                     'user_id', 'username', 'email']
    fieldsets = (
        (None, {
            'fields': (
                'exam_code', 'organization', 'duration', 'reviewed',
                'reviewer_notes', 'exam_password', 'exam_sponsor', 'exam_name',
                'ssi_product')
        }),
        ('Org Extra', {
            'fields': (
                'exam_start_date', 'exam_end_date', 'no_of_students',
                'exam_id', 'user_id', 'first_name', 'last_name',
                'username', 'email')
        }),
        ('Additional', {
            'fields': (
                'event',
                'course',
                'exam_status')
        }),
    )
    inlines = [CommentInline]


class EventSessionAdmin(admin.ModelAdmin):
    """
    Event Session admin class
    """
    list_display = (
        'testing_center', 'course_id', 'course_event_id', 'exam_name',
        'proctor', 'status', 'start_date', 'hash_key', 'end_date', 'custom_actions')
    list_filter = ('proctor', 'status')
    search_fields = (
        'testing_center', 'course_id', 'course_event_id', 'exam_name',
        'start_date', 'end_date')
    readonly_fields = ('hash_key', 'start_date', 'end_date', 'custom_actions')

    def custom_actions(self, obj):
        if obj.status == models.EventSession.IN_PROGRESS:
            return format_html(
                '<a class="button" href="{}">{}</a>',
                reverse('admin:end-session-confirm', args=[obj.pk]),
                _('Close')
            )
        return ''
    custom_actions.short_description = _('Actions')
    custom_actions.allow_tags = True


class InProgressEventSessionAdmin(EventSessionAdmin):
    """
    In Progress Event Session admin class
    """
    def get_urls(self):
        urls = super(InProgressEventSessionAdmin, self).get_urls()
        custom_urls = [
            url(
                r'^(?P<event_session_id>.+)/end_session_confirm/$',
                self.admin_site.admin_view(self.end_session_confirm),
                name='end-session-confirm',
            ),
            url(
                r'^(?P<event_session_id>.+)/end_session/$',
                self.admin_site.admin_view(self.end_session),
                name='end-session',
            ),
        ]
        return custom_urls + urls

    def end_session_confirm(self, request, event_session_id):
        event_session = self.get_object(request, event_session_id)
        context = self.admin_site.each_context(request)
        context['opts'] = self.model._meta
        context['event_session'] = event_session
        context['title'] = _('Close session ?')
        return TemplateResponse(request, 'admin/end_session.html', context)

    @csrf_protect_m
    @transaction.atomic
    def end_session(self, request, event_session_id):
        redirect_url = reverse('admin:proctoring_inprogresseventsession_changelist')
        event_session = self.get_object(request, event_session_id)
        if str(event_session.status) != models.EventSession.ARCHIVED:
            Journaling.objects.create(
                journaling_type=Journaling.EVENT_SESSION_STATUS_CHANGE,
                event=event_session,
                proctor=request.user,
                note="%s -> %s" % (event_session.status, models.EventSession.ARCHIVED)
            )

            exams = models.Exam.objects.filter(event=event_session)\
                .exclude(attempt_status__in=settings.FINAL_ATTEMPT_STATUSES)
            code_to_exam = {exam.exam_code: exam for exam in exams}
            codes = [{
                'code': exam.exam_code,
                'user_id': exam.user_id,
                'new_status': 'rejected' if exam.attempt_status == 'submitted' else 'error'
            } for exam in exams]

            if codes:
                response = bulk_update_exams_statuses(codes)
                if response.status_code == status.HTTP_200_OK:
                    new_statuses = response.json()
                    for attempt_code, data_to_update in new_statuses.items():
                        exam_attempt = code_to_exam[attempt_code]
                        if exam_attempt.attempt_status != data_to_update['status']:
                            exam_attempt.attempt_status = data_to_update['status']
                            exam_attempt.attempt_status_updated = datetime.now()
                            exam_attempt.exam_status = models.Exam.FINISHED
                            exam_attempt.save()
                else:
                    messages.error(request, _('Error during request to API edX. Please try again later'))
                    return HttpResponseRedirect(redirect_url)

            event_session.status = models.EventSession.ARCHIVED
            event_session.end_date = datetime.now()
            event_session.comment = _('Closed forcibly from the admin panel')
            event_session.save()
            send_notification({'end_session': True}, channel=event_session.course_event_id)
            messages.add_message(request, messages.INFO, event_session.exam_name + ': ' + str(_('Session was closed')))
        return HttpResponseRedirect(redirect_url)


admin.site.register(models.Course, CourseAdmin)
admin.site.register(models.Exam, ExamAdmin)
admin.site.register(models.InProgressEventSession, InProgressEventSessionAdmin)
admin.site.register(models.ArchivedEventSession, EventSessionAdmin)
