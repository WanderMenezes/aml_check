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
        # Allow empty here; code may be auto-generated later from name
        if not value:
            return value

        # When updating, allow the same instance
        instance = getattr(self, "instance", None)
        qs = SanctionsSource.objects.filter(code=value)
        if instance and instance.pk:
            qs = qs.exclude(pk=instance.pk)
        if qs.exists():
            raise serializers.ValidationError(f"Sanctions source com este Code já existe. Code: {value}")
        return value

    def _generate_code_from_name(self, name: str) -> str:
        # Normalize name to an uppercase code: remove non-alnum, replace spaces with underscore
        import re

        base = (name or "").upper()
        base = re.sub(r"[^A-Z0-9]+", "_", base).strip("_")
        if not base:
            base = "SOURCE"
        # truncate to 20 chars to match model max_length
        base = base[:20]

        candidate = base
        suffix = 1
        while SanctionsSource.objects.filter(code=candidate).exists():
            suffix += 1
            tail = f"_{suffix}"
            candidate = (base[: max(0, 20 - len(tail))] + tail)
        return candidate

    def create(self, validated_data):
        if not validated_data.get("code"):
            validated_data["code"] = self._generate_code_from_name(validated_data.get("name", ""))
        return super().create(validated_data)

    def update(self, instance, validated_data):
        if not validated_data.get("code") and not instance.code:
            validated_data["code"] = self._generate_code_from_name(validated_data.get("name", instance.name))
        return super().update(instance, validated_data)


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
