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
