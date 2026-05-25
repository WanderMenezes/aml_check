TRANSLATIONS = {
    "pt": {
        "login_success": "Autenticação realizada com sucesso.",
        "logout_success": "Sessão encerrada com sucesso.",
        "password_reset_sent": "Se o e-mail existir, as instruções de recuperação serão enviadas.",
        "screening_completed": "Screening concluído.",
        "report_title": "Relatório de Screening AML/KYC",
        "client_data": "Dados do Cliente",
        "results": "Resultados",
        "risk_level": "Nível de Risco",
        "recommendation": "Recomendação",
        "generated_at": "Gerado em",
        "source": "Origem",
        "score": "Pontuação",
        "details": "Detalhes",
        "digital_signature": "Assinatura digital",
        "validation_qr": "QR de validação",
    },
    "en": {
        "login_success": "Authentication completed successfully.",
        "logout_success": "Session closed successfully.",
        "password_reset_sent": "If the e-mail exists, password reset instructions will be sent.",
        "screening_completed": "Screening completed.",
        "report_title": "AML/KYC Screening Report",
        "client_data": "Client Data",
        "results": "Results",
        "risk_level": "Risk Level",
        "recommendation": "Recommendation",
        "generated_at": "Generated at",
        "source": "Source",
        "score": "Score",
        "details": "Details",
        "digital_signature": "Digital signature",
        "validation_qr": "Validation QR",
    },
}


def get_language(request=None, fallback: str = "pt") -> str:
    if request is None:
        return fallback
    lang = getattr(request, "LANGUAGE_CODE", None) or request.headers.get("Accept-Language", "")
    lang = (lang or fallback).split(",")[0].split("-")[0].strip().lower()
    return lang if lang in TRANSLATIONS else fallback


def translate(key: str, lang: str = "pt") -> str:
    return TRANSLATIONS.get(lang, TRANSLATIONS["pt"]).get(key, key)
