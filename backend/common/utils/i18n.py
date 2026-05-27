TRANSLATIONS = {
    "pt": {
        "login_success": "Autenticação realizada com sucesso.",
        "logout_success": "Sessão encerrada com sucesso.",
        "password_reset_sent": "Se o e-mail existir, as instruções de recuperação serão enviadas.",
        "screening_completed": "Screening concluído.",
        "report_title": "Relatório de Screening AML/KYC",
        "client_data": "Dados do cliente",
        "results": "Resultados",
        "risk_level": "Nível de risco",
        "recommendation": "Recomendação",
        "generated_at": "Gerado em",
        "source": "Origem",
        "score": "Pontuação",
        "details": "Detalhes",
        "digital_signature": "Assinatura digital",
        "validation_qr": "QR de validação",
        "admin_invalid": "Acesso administrativo inválido.",
        "admin_login_success": "Sessão administrativa iniciada.",
        "admin_logout_success": "Sessão administrativa terminada.",
        "user_email_required": "Informe um e-mail válido para criar o utilizador.",
        "user_email_exists": "Já existe um utilizador com esse e-mail.",
        "user_password_short": "A senha do novo utilizador deve ter pelo menos 8 caracteres.",
        "user_created": "Utilizador criado com sucesso.",
        "search_link_name_required": "Informe o nome do link de pesquisa.",
        "search_link_url_invalid": "Informe um URL válido para o link de pesquisa.",
        "search_link_created": "Link de pesquisa adicionado com sucesso.",
        "search_link_updated": "Link de pesquisa atualizado com sucesso.",
        "search_link_deleted": "Link de pesquisa removido com sucesso.",
        "company_name_required": "Informe a razão social da empresa.",
        "company_profile_saved": "Dados da empresa guardados com sucesso.",
    },
    "en": {
        "login_success": "Authentication completed successfully.",
        "logout_success": "Session closed successfully.",
        "password_reset_sent": "If the e-mail exists, password reset instructions will be sent.",
        "screening_completed": "Screening completed.",
        "report_title": "AML/KYC Screening Report",
        "client_data": "Client data",
        "results": "Results",
        "risk_level": "Risk level",
        "recommendation": "Recommendation",
        "generated_at": "Generated at",
        "source": "Source",
        "score": "Score",
        "details": "Details",
        "digital_signature": "Digital signature",
        "validation_qr": "Validation QR",
        "admin_invalid": "Invalid administrative access.",
        "admin_login_success": "Administrative session started.",
        "admin_logout_success": "Administrative session ended.",
        "user_email_required": "Provide a valid e-mail address to create the user.",
        "user_email_exists": "A user with that e-mail already exists.",
        "user_password_short": "The new user's password must have at least 8 characters.",
        "user_created": "User created successfully.",
        "search_link_name_required": "Provide the research link name.",
        "search_link_url_invalid": "Provide a valid URL for the research link.",
        "search_link_created": "Research link added successfully.",
        "search_link_updated": "Research link updated successfully.",
        "search_link_deleted": "Research link removed successfully.",
        "company_name_required": "Provide the company legal name.",
        "company_profile_saved": "Company data saved successfully.",
    },
}


SUPPORTED_LANGUAGES = frozenset(TRANSLATIONS)


def normalize_language(value: str | None, fallback: str = "pt") -> str:
    fallback = fallback if fallback in SUPPORTED_LANGUAGES else "pt"
    if not value:
        return fallback
    lang = str(value).split(",", 1)[0].split(";", 1)[0].replace("_", "-").split("-", 1)[0].strip().lower()
    return lang if lang in SUPPORTED_LANGUAGES else fallback


def get_language(request=None, fallback: str = "pt") -> str:
    if request is None:
        return normalize_language(fallback)
    headers = getattr(request, "headers", {})
    lang = getattr(request, "LANGUAGE_CODE", None) or headers.get("Accept-Language", "")
    return normalize_language(lang, fallback=fallback)


def translate(key: str, lang: str = "pt") -> str:
    lang = normalize_language(lang)
    return TRANSLATIONS.get(lang, TRANSLATIONS["pt"]).get(key, key)
