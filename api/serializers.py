import re
import json
from dateutil import parser
from collections import OrderedDict
from rest_framework import serializers
from django.core.exceptions import ValidationError
from django.utils.translation import ugettext as _
from models import Exam, ArchivedEventSession, Comment, \
    Permission, has_permisssion_to_course, InProgressEventSession
from journaling.models import Journaling


class JSONSerializerField(serializers.Field):
    """ Serializer for orgExtraField"""
    FIELD_LIST = [
        u'courseID',
        u'email',
        u'examEndDate',
        u'examID',
        u'examStartDate',
        u'firstName',
        u'lastName',
        u'noOfStudents',
        u'userID',
        u'username'
    ]

    def to_internal_value(self, data):
        """
        Validate orgExtra data
        :param data: dict
        :return: dict
        """
        json_data = {}
        if isinstance(data, basestring):
            data = json.loads(data)
        try:
            for field_name in self.FIELD_LIST:
                if field_name in data:
                    json_data[field_name] = data[field_name]
                else:
                    raise serializers.ValidationError(
                        _("orgExtra fields list incorrect. Missed %s" % field_name))
        except ValueError:
            raise serializers.ValidationError(
                _("orgExtra field value error. Must be json"))
        return json_data

    def to_representation(self, instance):
        """
        Get org extra data from Exam model and make dict.
        """
        result = {}
        for field in self.FIELD_LIST:
            result[field] = getattr(
                instance, re.sub('([A-Z]+)', r'_\1', field).lower()
            )
        return result


class ExamSerializer(serializers.ModelSerializer):
    """
    Exam serializer
    """
    class Meta:
        model = Exam
        fields = ('examCode', 'organization', 'duration', 'reviewedExam',
                  'reviewerNotes', 'examPassword', 'examSponsor',
                  'examName', 'ssiProduct', 'orgExtra', 'attempt_status',
                  'hash')

    examCode = serializers.CharField(source='exam_code', max_length=60)
    reviewedExam = serializers.CharField(source='reviewed_exam', max_length=60)
    reviewerNotes = serializers.CharField(source='reviewer_notes',
                                          max_length=60, allow_blank=True)
    examPassword = serializers.CharField(source='exam_password', max_length=60)
    examSponsor = serializers.CharField(source='exam_sponsor', max_length=60)
    examName = serializers.CharField(source='exam_name', max_length=60)
    ssiProduct = serializers.CharField(source='ssi_product', max_length=60)
    attempt_status = serializers.CharField(read_only=True)
    hash = serializers.SerializerMethodField()

    orgExtra = JSONSerializerField(
        style={'base_template': 'textarea.html'},
    )

    def get_hash(self, obj):
        """
        get hash key for exam
        :param obj: Exam instance
        :return: str
        """
        return obj.generate_key()

    def to_representation(self, instance):
        """
        Object instance -> Dict of primitive datatypes.
        """
        ret = OrderedDict()
        fields = self._readable_fields

        for field in fields:
            try:
                attribute = field.get_attribute(instance)
            except AttributeError:
                if isinstance(field, JSONSerializerField):
                    ret[field.field_name] = field.to_representation(instance)
                continue

            if attribute is None:
                ret[field.field_name] = None
            else:
                ret[field.field_name] = field.to_representation(attribute)

        return ret

    def validate(self, data):
        """
        Move fields from orgExtra to data and rename fieldname from camelCase
        to underscore
        :param data: data from post/put request
        :return: clean data
        """
        for key, value in data['orgExtra'].items():
            data[re.sub('([A-Z]+)', r'_\1', key).lower()] = value
        try:
            course_org, course_id, course_run = Exam.get_course_data(
                data['course_id'])
        except ValueError as e:
            raise serializers.ValidationError("Wrong courseId data")
        data['course_organization'] = course_org
        data['course_identify'] = "/".join((course_org, course_id))
        data['course_run'] = "/".join((course_org, course_id, course_run))
        data['exam_end_date'] = parser.parse(data['exam_end_date'])
        data['exam_start_date'] = parser.parse(data['exam_start_date'])
        del (data['orgExtra'])
        try:
            Exam(**data).full_clean()
        except ValidationError as e:
            raise serializers.ValidationError(e.message_dict)
        return super(ExamSerializer, self).validate(data)


class CommentSerializer(serializers.ModelSerializer):
    """
    Comment serializer
    """
    exam_code = serializers.ReadOnlyField(source='exam.exam_code')
    exam = serializers.PrimaryKeyRelatedField(queryset=Exam.objects.all(),
                                              write_only=True)

    class Meta:
        model = Comment


class ArchivedExamSerializer(ExamSerializer):
    """
    Exam archive serializer
    """
    comments = CommentSerializer(source='comment_set', many=True)

    class Meta:
        model = Exam
        exclude = (
            'exam_code', 'reviewed_exam', 'reviewer_notes', 'exam_password',
            'exam_sponsor', 'exam_name', 'ssi_product',
            'course_id', 'email', 'exam_end_date', 'exam_id',
            'exam_start_date',
            'first_name', 'last_name', 'no_of_students', 'user_id', 'username',
            'course_organization', 'course_identify', 'course_run')


class EventSessionSerializer(serializers.ModelSerializer):
    """
    Event session serializer
    """
    hash_key = serializers.CharField(read_only=True)
    start_date = serializers.DateTimeField(read_only=True)
    end_date = serializers.DateTimeField(read_only=True)

    class Meta:
        model = InProgressEventSession

    def validate(self, data):
        '''
        Data validation
        :param data: data from post/put request
        :return: clean data
        '''

        if not self.instance and not has_permisssion_to_course(
            data.get('proctor'),
            data.get('course_id', '')):
            raise serializers.ValidationError(
                "You have not permissions to create event for this course")
        return super(EventSessionSerializer, self).validate(data)


class ArchivedEventSessionSerializer(serializers.ModelSerializer):
    """
    Event session archive serializer
    """
    proctor = serializers.SerializerMethodField()
    serializers.ReadOnlyField(source='proctor.username')

    def get_proctor(self, obj):
        proctor = obj.proctor
        return ' '.join([proctor.first_name,
                         proctor.last_name]).strip() or proctor.username

    class Meta:
        read_only_fields = (
            'testing_center', 'course_id', 'course_event_id', 'proctor',
            'status', 'hash_key', 'notify', 'start_date', 'end_date', 'comment'
        )
        model = ArchivedEventSession


class JournalingSerializer(serializers.ModelSerializer):
    """
    Journaling serializer
    """
    proctor = serializers.ReadOnlyField(source='proctor.username')
    event = serializers.ReadOnlyField(source='event.hash_key')
    exam_code = serializers.ReadOnlyField(source='exam.exam_code')
    type_name = serializers.SerializerMethodField()
    student = serializers.SerializerMethodField()

    def get_student(self, obj):
        """
        Get student data
        :param obj: Journaling instance
        :return: str
        """
        return obj.get_student()

    def get_type_name(self, obj):
        """
        Get userfriendly type name
        :param obj:
        :return:
        """
        return obj.get_type_display()

    class Meta:
        model = Journaling
        exclude = ("exam",)


class PermissionSerializer(serializers.ModelSerializer):
    object_id = serializers.SerializerMethodField()

    def get_object_id(self, obj):
        """
        Delete course run
        :param obj:
        :return:
        """
        return obj.prepare_object_id()

    class Meta:
        model = Permission
        exclude = ("id", "user")
