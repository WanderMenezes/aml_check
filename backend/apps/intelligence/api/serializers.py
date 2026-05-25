from rest_framework import serializers

from apps.intelligence.models import Country, CountryRiskEntry, RiskRule, SanctionsSource, SyncJobLog, WatchlistEntry


class CountrySerializer(serializers.ModelSerializer):
    class Meta:
        model = Country
        fields = "__all__"
        read_only_fields = ("normalized_name", "updated_at")


class SanctionsSourceSerializer(serializers.ModelSerializer):
    class Meta:
        model = SanctionsSource
        fields = "__all__"

    def validate_code(self, value):
        # Ensure code is provided
        if not value:
            raise serializers.ValidationError("O campo Code é obrigatório.")

        # When updating, allow the same instance
        instance = getattr(self, "instance", None)
        qs = SanctionsSource.objects.filter(code=value)
        if instance and instance.pk:
            qs = qs.exclude(pk=instance.pk)
        if qs.exists():
            raise serializers.ValidationError(f"Sanctions source com este Code já existe. Code: {value}")
        return value


class WatchlistEntrySerializer(serializers.ModelSerializer):
    source_code = serializers.CharField(source="source.code", read_only=True)

    class Meta:
        model = WatchlistEntry
        fields = "__all__"


class CountryRiskEntrySerializer(serializers.ModelSerializer):
    source_code = serializers.CharField(source="source.code", read_only=True)

    class Meta:
        model = CountryRiskEntry
        fields = "__all__"


class SyncJobLogSerializer(serializers.ModelSerializer):
    source_code = serializers.CharField(source="source.code", read_only=True)

    class Meta:
        model = SyncJobLog
        fields = "__all__"


class RiskRuleSerializer(serializers.ModelSerializer):
    class Meta:
        model = RiskRule
        fields = "__all__"
