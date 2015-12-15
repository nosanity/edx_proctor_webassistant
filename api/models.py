# -*- coding: utf-8 -*-
import hashlib
import operator
from django.db import models
from django.db.models.signals import post_save
from django.utils.translation import ugettext_lazy as _
from django.contrib.auth.models import User, AnonymousUser
from django.db.models import Q


def has_permisssion_to_course(user, course_id, permissions=None, role=None):
    """
    Check is user has access to this course
    :param user: User instance
    :param course_id: str
    :param permissions: list of all user's permissions
    :param role: role of user
    :return: bool
    """
    course_data = {}
    try:
        edxorg, edxcourse, edxcourserun = Exam.get_course_data(course_id)
        course_data['edxorg'] = edxorg
        course_data['edxcourse'] = "/".join((edxorg, edxcourse))
        course_data['edxcourserun'] = "/".join(
            (edxorg, edxcourse, edxcourserun))
    except ValueError as e:
        return False
    if not isinstance(user, AnonymousUser):
        if user.is_superuser:
            return True
        permissions = permissions if permissions else user.permission_set.all()
        if role:
            permissions = permissions.filter(role=role)
        for permission in permissions:
            if permission.object_id != "*":
                if course_data.get(
                    permission.object_type
                ) == permission.prepare_object_id():
                    return True
            else:
                return True
    return False


class ExamsByUserPermsManager(models.Manager):
    """
    Manager for getting list of exams consider permissions
    """

    def by_user_perms(self, user):
        """
        Update queryset consider permissions
        :param user: User instance
        :return: queryset
        """
        qs = super(ExamsByUserPermsManager, self).get_queryset()
        q_objects = []
        if not isinstance(user, AnonymousUser):
            if user.is_superuser:
                return qs
            for permission in user.permission_set.all():
                if permission.object_id != "*":
                    q_objects.append(Q(**{permission._get_exam_field_by_type():
                                              permission.prepare_object_id()}))
                else:
                    return qs
            if len(q_objects):
                return qs.filter(reduce(operator.or_, q_objects))

        return qs.filter(pk__lt=0)


class Exam(models.Model):
    """
    Exam model
    """
    NEW = 'new'
    STARTED = 'started'
    FINISHED = 'finished'
    FAILED = 'failed'

    EXAM_STATUS_CHOICES = {
        (NEW, _("Not started")),
        (STARTED, _("Started")),
        (FINISHED, _("Finished")),
        (FAILED, _("Failed")),
    }

    exam_code = models.CharField(max_length=60, unique=True)
    organization = models.CharField(max_length=60)
    duration = models.IntegerField()
    reviewed_exam = models.CharField(max_length=60)
    reviewer_notes = models.CharField(max_length=60, blank=True, null=True)
    exam_password = models.CharField(max_length=60)
    exam_sponsor = models.CharField(max_length=60)
    exam_name = models.CharField(max_length=60)
    ssi_product = models.CharField(max_length=60)
    # org extra
    exam_start_date = models.DateTimeField(blank=True, null=True)
    exam_end_date = models.DateTimeField(blank=True, null=True)
    no_of_students = models.IntegerField(blank=True, null=True)
    exam_id = models.CharField(max_length=64, blank=True, null=True)
    course_id = models.CharField(max_length=64, blank=True, null=True)
    first_name = models.CharField(max_length=60, blank=True, null=True)
    last_name = models.CharField(max_length=60, blank=True, null=True)
    email = models.EmailField(max_length=60, blank=True, null=True)
    user_id = models.IntegerField(blank=True, null=True)
    username = models.CharField(max_length=50, blank=True, null=True)
    # own fields
    course_organization = models.CharField(
        max_length=64,
        blank=True,
        null=True,
        db_index=True
    )
    course_identify = models.CharField(
        max_length=64,
        blank=True,
        null=True,
        db_index=True
    )
    course_run = models.CharField(
        max_length=64,
        blank=True,
        null=True,
        db_index=True
    )
    proctor = models.ForeignKey(User, blank=True, null=True)
    exam_status = models.CharField(
        max_length=8,
        choices=EXAM_STATUS_CHOICES,
        default=NEW)

    attempt_status = models.CharField(max_length=20, blank=True, null=True)

    event = models.ForeignKey('EventSession', blank=True, null=True)

    objects = ExamsByUserPermsManager()

    def generate_key(self):
        """
        generate key for edx
        :return: string
        """
        str_to_hash = str(self.exam_code) + str(self.user_id) + str(
            self.exam_id) + str(self.email)
        return hashlib.md5(str_to_hash).hexdigest()

    @classmethod
    def get_course_data(cls, course_id):
        """
        Check course format and return list using separator
        :param course_id: str
        :return: list
        """
        sp = course_id.split(':')
        if len(sp) == 2:
            return sp[-1].split('+')
        else:
            return course_id.split('/')

    def __unicode__(self):
        return self.exam_id


class InProgressEventSessionManager(models.Manager):
    """
    Manager for getting all active Event Sessions
    """

    def get_queryset(self):
        return super(InProgressEventSessionManager,
                     self).get_queryset().exclude(
            status=EventSession.ARCHIVED)


class ArchivedEventSessionManager(models.Manager):
    """
    Manager for getting all finished Event Sessions
    """

    def get_queryset(self):
        return super(ArchivedEventSessionManager, self).get_queryset().filter(
            status=EventSession.ARCHIVED)


class EventSession(models.Model):
    """
    Event session model
    """
    IN_PROGRESS = 'in_progress'
    ARCHIVED = 'archived'

    SESSION_STATUS_CHOICES = {
        (IN_PROGRESS, _("In progress")),
        (ARCHIVED, _("Archived")),
    }
    testing_center = models.CharField(max_length=128)
    course_id = models.CharField(max_length=128, blank=True, null=True)
    course_event_id = models.CharField(max_length=128, blank=True, null=True)
    proctor = models.ForeignKey(User)
    status = models.CharField(
        max_length=11,
        choices=SESSION_STATUS_CHOICES,
        default=IN_PROGRESS
    )
    hash_key = models.CharField(max_length=128, db_index=True, blank=True,
                                null=True)
    notify = models.TextField(blank=True, null=True)
    start_date = models.DateTimeField(auto_now_add=True, blank=True)
    end_date = models.DateTimeField(null=True, blank=True)
    comment = models.TextField(null=True, blank=True)

    course_run = models.CharField(
        max_length=64,
        blank=True,
        null=True,
        db_index=True
    )

    @staticmethod
    def update_queryset_with_permissions(queryset, user):
        """
        Update queryset consider permissions
        :param queryset: queryset
        :param user: User instance
        :return: queryset
        """
        if user.permission_set.filter(
            role=Permission.ROLE_PROCTOR).exists():
            is_super_proctor = False
            for permission in user.permission_set.filter(
                role=Permission.ROLE_PROCTOR).all():
                if permission.object_id == "*":
                    is_super_proctor = True
                    break
            if not is_super_proctor:
                queryset = queryset.filter(
                    proctor=user)
        elif user.permission_set.filter(role=Permission.ROLE_INSTRUCTOR
                                        ).exists():
            for permission in user.permission_set.filter(
                    role=Permission.ROLE_INSTRUCTOR).all():
                q_objects = []
                if permission.object_id != "*":
                    q_objects.append(Q(**{
                        "course_run__startswith":
                            permission.prepare_object_id()
                    }))
            if len(q_objects):
                queryset = queryset.filter(reduce(operator.or_, q_objects))

        return queryset

    @staticmethod
    def post_save(sender, instance, created, **kwargs):
        """
        Method for post save signal.
        Add hash key, add slashseparated course_run
        :param sender:
        :param instance:
        :param created:
        :param kwargs:
        :return:
        """
        if created and not instance.hash_key:
            instance.hash_key = hashlib.md5(
                unicode(instance.testing_center).encode('utf-8') + str(
                    instance.course_id) + str(
                    instance.course_event_id) + str(instance.proctor.pk) + str(
                    instance.start_date)).hexdigest()
            instance.save()
        if created or not instance.course_run:
            org, course, courserun = Exam.get_course_data(instance.course_id)
            instance.course_run = "/".join((org, course, courserun))
            instance.save()

    def __unicode__(self):
        return u" | ".join((self.testing_center,
                            self.course_id,
                            self.course_event_id))


class InProgressEventSession(EventSession):
    """
    Proxy model for active event sessions
    """
    class Meta:
        proxy = True

    objects = InProgressEventSessionManager()


class ArchivedEventSession(EventSession):
    """
    Proxy model for finished event sessions
    """
    class Meta:
        proxy = True

    objects = ArchivedEventSessionManager()


post_save.connect(ArchivedEventSession.post_save, ArchivedEventSession,
                  dispatch_uid='add_hash')
post_save.connect(InProgressEventSession.post_save, InProgressEventSession,
                  dispatch_uid='add_hash')


class Permission(models.Model):
    """
    User permissions model
    """
    TYPE_ORG = 'edxorg'
    TYPE_COURSE = 'edxcourse'
    TYPE_COURSERUN = 'edxcourserun'

    ROLE_PROCTOR = 'proctor'
    ROLE_INSTRUCTOR = 'instructor'

    OBJECT_TYPE_CHOICES = {
        ('*', "*"),
        (TYPE_ORG, _("Organization")),
        (TYPE_COURSE, _("Course")),
        (TYPE_COURSERUN, _("Courserun")),
    }

    ROLES_CHOICES = {
        (ROLE_PROCTOR, _("Proctor")),
        (ROLE_INSTRUCTOR, _("Instructor")),
    }
    user = models.ForeignKey(User)
    object_id = models.CharField(max_length=64)
    object_type = models.CharField(max_length=64,
                                   choices=OBJECT_TYPE_CHOICES)
    role = models.CharField(max_length=10, choices=ROLES_CHOICES,
                            default=ROLE_PROCTOR)

    def _get_exam_field_by_type(self):
        """
        return field name by object type
        :return: str
        """
        fields = {
            self.TYPE_ORG: "course_organization",
            self.TYPE_COURSE: "course_identify",
            self.TYPE_COURSERUN: "course_run"
        }
        return fields[self.object_type]

    def prepare_object_id(self):
        """
        Delete courserun from object_id if object type is course id
        :return: str
        """
        return self.object_id if \
            self.object_type != Permission.TYPE_COURSE else \
            Permission._course_run_to_course(self.object_id)

    @classmethod
    def _course_run_to_course(cls, courserun):
        """
        Delete courserun from string
        :param courserun: str
        :return: str
        """
        try:
            edxorg, edxcourse, edxcourserun = Exam.get_course_data(courserun)
            return "/".join((edxorg, edxcourse))
        except:
            return courserun


class Student(models.Model):
    """
    Student model
    """
    sso_id = models.IntegerField()
    email = models.EmailField()
    first_name = models.CharField(max_length=60, blank=True, null=True)
    last_name = models.CharField(max_length=60, blank=True, null=True)


class Comment(models.Model):
    """
    Comment model
    """
    comment = models.TextField()
    event_status = models.CharField(max_length=60)
    event_start = models.IntegerField()
    event_finish = models.IntegerField()
    exam = models.ForeignKey(Exam)
    duration = models.IntegerField(blank=True, null=True)
