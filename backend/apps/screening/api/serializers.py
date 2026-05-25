from rest_framework import serializers

from apps.screening.models import Alert, Client, PDFReport, ScreeningMatch, ScreeningRequest
from common.utils.countries import canonical_country
from common.utils.strings import normalize_text


def _name_tokens(value: str) -> list[str]:
    return [token for token in normalize_text(value).split(" ") if token]


class ClientSerializer(serializers.ModelSerializer):
    class Meta:
        model = Client
        fields = "__all__"
        read_only_fields = ("created_by", "created_at", "updated_at")


class ScreeningMatchSerializer(serializers.ModelSerializer):
    class Meta:
        model = ScreeningMatch
        fields = "__all__"


class ScreeningRequestSerializer(serializers.ModelSerializer):
    client = ClientSerializer()
    matches = ScreeningMatchSerializer(many=True, read_only=True)
    grouped_matches = serializers.SerializerMethodField()

    class Meta:
        model = ScreeningRequest
        fields = "__all__"
        read_only_fields = ("created_by", "risk_level", "status", "recommendation", "metadata")

    def create(self, validated_data):
        client_data = validated_data.pop("client")
        client = Client.objects.create(created_by=self.context["request"].user, **client_data)
        return ScreeningRequest.objects.create(client=client, created_by=self.context["request"].user, **validated_data)

    def get_grouped_matches(self, obj: ScreeningRequest):
        groups: dict[str, dict] = {}
        for match in obj.matches.all():
            details = match.details or {}
            url = details.get("url") or ""
            key = url or match.source_code or "UNKNOWN"
            if key not in groups:
                groups[key] = {
                    "key": key,
                    "url": url,
                    "source_code": match.source_code,
                    "title": details.get("title") or "",
                    "snippet": details.get("snippet") or "",
                    "matches": [],
                }
            groups[key]["matches"].append(ScreeningMatchSerializer(match).data)
        # return as list ordered by highest match score in each group
        grouped_list = list(groups.values())
        grouped_list.sort(key=lambda g: max((m.get("score") or 0) for m in g["matches"]), reverse=True)
        return grouped_list


class ScreeningClientInputSerializer(serializers.Serializer):
    search_type = serializers.ChoiceField(required=False, choices=("person", "country", "company"))
    subject_type = serializers.ChoiceField(required=False, choices=("INDIVIDUAL", "COMPANY"))
    full_name = serializers.CharField(required=False, allow_blank=True, max_length=255)
    company_name = serializers.CharField(required=False, allow_blank=True, max_length=255)
    country = serializers.CharField(required=False, allow_blank=True, max_length=120)

    def to_internal_value(self, data):
        unknown = set(data.keys()) - {"search_type", "subject_type", "full_name", "company_name", "country"}
        if unknown:
            raise serializers.ValidationError(
                {field: "Screening accepts only search_type, full_name, company_name and country." for field in sorted(unknown)}
            )
        return super().to_internal_value(data)

    def validate(self, attrs):
        requested_type = (attrs.get("search_type") or "").strip()
        full_name = (attrs.get("full_name") or "").strip()
        company_name = (attrs.get("company_name") or "").strip()
        country = (attrs.get("country") or "").strip()
        search_type = requested_type
        if not search_type:
            if full_name:
                search_type = "person"
            elif company_name:
                search_type = "company"
            elif country:
                search_type = "country"

        if search_type == "person":
            if not full_name:
                raise serializers.ValidationError({"full_name": "Provide the person's complete name."})
            tokens = _name_tokens(full_name)
            if len(tokens) < 2 or any(len(token) < 2 for token in tokens):
                raise serializers.ValidationError(
                    {"full_name": "Person screening requires a complete name with at least two words."}
                )
            if any(char.isdigit() for char in full_name):
                raise serializers.ValidationError({"full_name": "Person names cannot include numbers or identifiers."})
            attrs["subject_type"] = "INDIVIDUAL"

        if search_type == "company":
            if not company_name:
                raise serializers.ValidationError({"company_name": "Provide the company name."})
            if len(_name_tokens(company_name)) < 1 or len(company_name) < 2:
                raise serializers.ValidationError({"company_name": "Company screening requires a valid company name."})
            attrs["subject_type"] = "COMPANY"
            attrs["full_name"] = ""

        if search_type == "country":
            if not country:
                raise serializers.ValidationError({"country": "Provide the complete official country name."})
            resolved_country = canonical_country(country)
            if not resolved_country:
                raise serializers.ValidationError({"country": "Use a complete official country name, not a partial term."})
            attrs["country"] = resolved_country
            attrs["subject_type"] = "INDIVIDUAL"
            attrs["full_name"] = ""
            attrs["company_name"] = ""
        elif country:
            resolved_country = canonical_country(country)
            if not resolved_country:
                raise serializers.ValidationError({"country": "Use a complete official country name, not a partial term."})
            attrs["country"] = resolved_country

        attrs["search_type"] = search_type
        if search_type == "person":
            attrs["full_name"] = full_name
            attrs["company_name"] = ""
        if search_type == "company":
            attrs["full_name"] = ""
            attrs["company_name"] = company_name
        return attrs


class ScreeningRunSerializer(serializers.Serializer):
    client = ScreeningClientInputSerializer()
    comments = serializers.CharField(required=False, allow_blank=True)

    def validate(self, attrs):
        client = attrs.get("client", {})
        attrs["search_type"] = client.pop("search_type", "")
        return attrs


class PDFReportSerializer(serializers.ModelSerializer):
    file_url = serializers.SerializerMethodField()

    class Meta:
        model = PDFReport
        fields = "__all__"

    def get_file_url(self, obj):
        return obj.file.url if obj.file else ""


class AlertSerializer(serializers.ModelSerializer):
    class Meta:
        model = Alert
        fields = "__all__"
