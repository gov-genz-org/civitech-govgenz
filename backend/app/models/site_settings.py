from datetime import datetime
from sqlalchemy import Column, Integer, String, Text, DateTime, Boolean
from app.database import Base

# Clés publiques (lisibles sans authentification)
PUBLIC_KEYS = {
    "cookie_consent_required",
    "site_tagline",
    "site_description",
    "homepage_hero_title",
    "homepage_hero_subtitle",
    "homepage_cta_primary",
    "homepage_cta_secondary",
    "platform_name",
    "contact_email",
    "social_facebook",
    "social_twitter",
    "social_instagram",
    "social_tiktok",
    "social_youtube",
    "social_linkedin",
    "website_main",
    "maintenance_mode",
    "maintenance_message",
}

# Valeurs par défaut
DEFAULTS = {
    "cookie_consent_required":  "false",
    "platform_name":            "Civitech",
    "site_tagline":             "L'observatoire civique de la jeunesse malgache",
    "site_description":         "Civitech est une plateforme de transparence et de participation citoyenne développée par GoV Gen Z Madagascar.",
    "homepage_hero_title":      "LA TRANSPARENCE,\nC'EST MAINTENANT.",
    "homepage_hero_subtitle":   "Observe. Vérifie. Agis. Civitech centralise les faits documentés, les alertes citoyennes et les consultations publiques pour une Madagascar plus transparente.",
    "homepage_cta_primary":     "Explorer les faits",
    "homepage_cta_secondary":   "Rejoindre la communauté",
    "contact_email":            "contact@genzgov.org",
    "social_facebook":          "",
    "social_twitter":           "",
    "social_instagram":         "",
    "social_tiktok":            "",
    "social_youtube":           "",
    "social_linkedin":          "",
    "website_main":             "https://govgenz.org",
    "maintenance_mode":         "false",
    "maintenance_message":      "La plateforme est en maintenance. Revenez bientôt.",
}


class SiteSetting(Base):
    __tablename__ = "site_settings"

    id         = Column(Integer, primary_key=True, index=True)
    key        = Column(String(100), unique=True, index=True, nullable=False)
    value      = Column(Text, nullable=True)
    label      = Column(String(200))           # Libellé affiché en admin
    group      = Column(String(50))            # Groupe : "general" | "homepage" | "cookies" | "social"
    updated_by = Column(Integer, nullable=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
