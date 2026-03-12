from rest_framework import serializers
from .models import User, MentorProfile, ScholarProfile, SponsorProfile, MentoringMatch, MentorWaitingList


class MentorProfileSerializer(serializers.ModelSerializer):
    current_scholar_count = serializers.ReadOnlyField()
    has_capacity = serializers.ReadOnlyField()

    class Meta:
        model = MentorProfile
        exclude = ['user']


class ScholarProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = ScholarProfile
        exclude = ['user']


class SponsorProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = SponsorProfile
        exclude = ['user']


class UserSerializer(serializers.ModelSerializer):
    full_name = serializers.ReadOnlyField()
    mentor_profile = MentorProfileSerializer(read_only=True)
    scholar_profile = ScholarProfileSerializer(read_only=True)
    sponsor_profile = SponsorProfileSerializer(read_only=True)

    class Meta:
        model = User
        fields = [
            'id', 'email', 'username', 'first_name', 'last_name', 'full_name',
            'role', 'phone', 'bio', 'profile_picture', 'date_of_birth', 'location',
            'engineering_discipline', 'interests', 'notification_email',
            'notification_sms', 'is_verified', 'crm_id', 'is_active',
            'mentor_profile', 'scholar_profile', 'sponsor_profile',
        ]
        read_only_fields = ['is_verified', 'crm_id']


class UserListSerializer(serializers.ModelSerializer):
    """Lightweight serializer for list views."""
    full_name = serializers.ReadOnlyField()

    class Meta:
        model = User
        fields = ['id', 'email', 'full_name', 'role', 'is_active', 'location', 'engineering_discipline']


class UserCreateSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, min_length=8)

    class Meta:
        model = User
        fields = [
            'email', 'username', 'first_name', 'last_name', 'role',
            'phone', 'location', 'engineering_discipline', 'password',
        ]

    def create(self, validated_data):
        password = validated_data.pop('password')
        user = User(**validated_data)
        user.set_password(password)
        user.save()
        return user


class MentoringMatchSerializer(serializers.ModelSerializer):
    scholar_name = serializers.CharField(source='scholar.full_name', read_only=True)
    mentor_name = serializers.CharField(source='mentor.full_name', read_only=True)

    class Meta:
        model = MentoringMatch
        fields = '__all__'
        read_only_fields = ['matched_on', 'matched_by']


class MentorWaitingListSerializer(serializers.ModelSerializer):
    scholar_name = serializers.CharField(source='scholar.full_name', read_only=True)
    preferred_mentor_name = serializers.CharField(source='preferred_mentor.full_name', read_only=True, default='')

    class Meta:
        model = MentorWaitingList
        fields = [
            'id', 'scholar', 'scholar_name', 'preferred_mentor', 'preferred_mentor_name',
            'engineering_discipline', 'notes', 'requested_at', 'is_matched', 'matched_at',
        ]
        read_only_fields = ['scholar', 'requested_at', 'matched_at']
