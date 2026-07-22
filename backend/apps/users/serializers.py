from rest_framework import serializers
from .models import User, MentorProfile, ScholarProfile, SponsorProfile, MentoringMatch, MentorWaitingList
from .validators import validate_profile_picture


class MentorProfileSerializer(serializers.ModelSerializer):
    current_scholar_count = serializers.ReadOnlyField()
    has_capacity = serializers.ReadOnlyField()
    active_matches = serializers.SerializerMethodField()

    class Meta:
        model = MentorProfile
        exclude = ['user']

    def get_active_matches(self, obj):
        """Return list of active scholar matches for this mentor, with cohort info."""
        from apps.cohorts.models import CohortMembership
        matches = []
        for m in obj.user.mentor_matches.filter(is_active=True).select_related('scholar'):
            # Get the scholar's current cohort (most recent active)
            cohort_membership = (
                CohortMembership.objects
                .filter(user=m.scholar, cohort__is_active=True)
                .select_related('cohort', 'cohort__programme')
                .order_by('-cohort__year')
                .first()
            )
            matches.append({
                'scholar_id': m.scholar_id,
                'scholar_name': m.scholar.full_name,
                'matched_on': m.matched_on,
                'is_active': m.is_active,
                'cohort_name': cohort_membership.cohort.name if cohort_membership else None,
                'programme_name': cohort_membership.cohort.programme.name if cohort_membership else None,
            })
        return matches


class ScholarProfileSerializer(serializers.ModelSerializer):
    matched_mentor = serializers.SerializerMethodField()
    sponsor_name = serializers.SerializerMethodField()

    class Meta:
        model = ScholarProfile
        exclude = ['user']

    def get_matched_mentor(self, obj):
        """Return the scholar's current active mentor match, or None."""
        match = (
            MentoringMatch.objects
            .filter(scholar=obj.user, is_active=True)
            .select_related('mentor')
            .first()
        )
        if match:
            return {
                'mentor_id': match.mentor_id,
                'mentor_name': match.mentor.full_name,
                'matched_on': match.matched_on,
            }
        return None

    def get_sponsor_name(self, obj):
        """TC-23: Return the linked sponsor's display name, or None."""
        if obj.sponsor:
            return obj.sponsor.full_name
        return None


class SponsorProfileSerializer(serializers.ModelSerializer):
    sponsored_scholars = serializers.SerializerMethodField()

    class Meta:
        model = SponsorProfile
        exclude = ['user']

    def get_sponsored_scholars(self, obj):
        """Return basic info for each scholar linked to this sponsor."""
        return [
            {'id': sp.user_id, 'full_name': sp.user.full_name}
            for sp in obj.user.sponsored_scholars.select_related('user').all()
        ]


class UserSerializer(serializers.ModelSerializer):
    full_name = serializers.ReadOnlyField()
    mentor_profile = MentorProfileSerializer(required=False, allow_null=True)
    scholar_profile = ScholarProfileSerializer(required=False, allow_null=True)
    sponsor_profile = SponsorProfileSerializer(required=False, allow_null=True)
    has_mentor = serializers.SerializerMethodField()
    cohorts = serializers.SerializerMethodField()
    profile_picture = serializers.ImageField(validators=[validate_profile_picture], required=False, allow_null=True)

    def get_has_mentor(self, obj):
        if obj.role != 'scholar':
            return False
        return MentoringMatch.objects.filter(scholar=obj, is_active=True).exists()

    def get_cohorts(self, obj):
        """Return all cohorts this user belongs to, with programme name."""
        from apps.cohorts.models import CohortMembership
        return [
            {
                'cohort_id': m.cohort_id,
                'cohort_name': m.cohort.name,
                'cohort_year': m.cohort.year,
                'programme_id': m.cohort.programme_id,
                'programme_name': m.cohort.programme.name,
                'is_active': m.cohort.is_active,
            }
            for m in (
                CohortMembership.objects
                .filter(user=obj)
                .select_related('cohort', 'cohort__programme')
            )
        ]

    def update(self, instance, validated_data):
        mentor_data  = validated_data.pop('mentor_profile',  None)
        scholar_data = validated_data.pop('scholar_profile', None)
        sponsor_data = validated_data.pop('sponsor_profile', None)

        instance = super().update(instance, validated_data)

        for data, attr in (
            (mentor_data,  'mentor_profile'),
            (scholar_data, 'scholar_profile'),
            (sponsor_data, 'sponsor_profile'),
        ):
            if data and hasattr(instance, attr):
                profile = getattr(instance, attr)
                for key, val in data.items():
                    setattr(profile, key, val)
                profile.save()

        return instance

    class Meta:
        model = User
        fields = [
            'id', 'email', 'username', 'first_name', 'last_name', 'full_name',
            'role', 'secondary_roles', 'phone', 'bio', 'profile_picture', 'date_of_birth',
            'location', 'engineering_discipline', 'engineering_disciplines', 'interests',
            'notification_email', 'notification_sms', 'is_verified', 'crm_id', 'is_active',
            'mentor_profile', 'scholar_profile', 'sponsor_profile', 'has_mentor',
            'cohorts',
        ]
        read_only_fields = ['is_verified', 'crm_id']


class UserListSerializer(serializers.ModelSerializer):
    """Lightweight serializer for list views."""
    full_name = serializers.ReadOnlyField()
    mentor_profile = MentorProfileSerializer(required=False, allow_null=True)

    class Meta:
        model = User
        fields = ['id', 'email', 'first_name', 'last_name', 'full_name', 'role',
                  'is_active', 'location',
                  'engineering_discipline', 'engineering_disciplines',
                  'bio', 'is_verified', 'mentor_profile']


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
