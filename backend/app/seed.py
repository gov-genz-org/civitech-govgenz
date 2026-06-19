import secrets
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from app.models.user import User, UserRole, VerificationStatus
from app.models.ambassador import Ambassador, AmbassadorStatus, AmbassadorType
from app.models.sector import Sector, SECTORS
from app.models.consultation import Consultation, Question, ConsultationStatus, ConsultationScope, QuestionType
from app.models.alert import Alert, AlertType, AlertSeverity, AlertStatus
from app.models.entity import Entity, EntityLink, EntityType, EntitySubtype, RepublicPeriod, LinkType
from app.models.fact import Fact, FactActor, FactSource, Thread, ThreadFact, FactType, VerificationStatus as FactVerif, ActorRole, SourceType
from app.utils.security import hash_password
from app.config import settings
import re


def slugify(text: str, suffix: int = None) -> str:
    s = text.lower()
    for fr, en in [('à','a'),('á','a'),('â','a'),('é','e'),('è','e'),('ê','e'),
                   ('î','i'),('ï','i'),('ô','o'),('ù','u'),('û','u'),('ü','u'),('ç','c')]:
        s = s.replace(fr, en)
    s = re.sub(r'[^a-z0-9]+', '-', s).strip('-')
    if suffix:
        s = f"{s[:70]}-{suffix}"
    return s[:100]


def seed_sectors(db: Session):
    if db.query(Sector).count() > 0:
        return
    for code, label, icon in SECTORS:
        db.add(Sector(code=code, label=label, icon=icon))
    db.commit()
    print("✓ Secteurs créés")


SUPERADMIN_EMAIL = "rasoloarivony@proton.me"


def seed_superadmin(db: Session):
    """Crée le superadmin s'il n'existe pas encore."""
    if db.query(User).filter(User.email == SUPERADMIN_EMAIL).first():
        return
    superadmin = User(
        email=SUPERADMIN_EMAIL,
        hashed_password=hash_password(secrets.token_hex(32)),  # hash inutilisable — magic link only
        role=UserRole.superadmin,
        pseudo="superadmin",
        full_name="Superadmin GoV Gen Z",
        verification_status=VerificationStatus.verified,
        trust_score=100.0,
        country="Madagascar",
        is_active=True,
    )
    db.add(superadmin)
    db.commit()
    print(f"✓ Superadmin créé : {SUPERADMIN_EMAIL}")


def seed_users(db: Session):
    if db.query(User).filter(User.email == settings.ADMIN_EMAIL).first():
        return

    admin = User(
        email=settings.ADMIN_EMAIL,
        hashed_password=hash_password(secrets.token_hex(32)),  # magic link only
        role=UserRole.admin, pseudo="admin-govgenz",
        full_name="Admin GoV Gen Z",
        verification_status=VerificationStatus.verified,
        trust_score=100.0, country="Madagascar", is_active=True,
    )
    db.add(admin)

    moderator = User(
        email="moderateur@civitech.genzgov.org",
        hashed_password=hash_password(secrets.token_hex(32)),  # magic link only
        role=UserRole.moderator, pseudo="moderateur-civitech",
        full_name="Moderateur Civitech",
        verification_status=VerificationStatus.verified,
        trust_score=90.0, country="Madagascar",
        region="Analamanga", city="Antananarivo", is_active=True,
    )
    db.add(moderator)

    citizen = User(
        email="citoyen@test.mg",
        hashed_password=hash_password(secrets.token_hex(32)),  # magic link only
        role=UserRole.z_citizen, pseudo="citoyen-test",
        full_name="Jean Rakoto",
        verification_status=VerificationStatus.verified,
        trust_score=75.0, country="Madagascar",
        region="Analamanga", city="Antananarivo",
        profession="Étudiant", age_range="18-25",
        priorities="Éducation, Emploi, Sécurité", is_active=True,
    )
    db.add(citizen)
    db.flush()

    ambassador_user = User(
        email="ambassador@test.mg",
        hashed_password=hash_password(secrets.token_hex(32)),  # magic link only
        role=UserRole.z_ambassador, pseudo="z-ambassador-test",
        full_name="Marie Rasoa",
        verification_status=VerificationStatus.verified,
        trust_score=85.0, country="Madagascar",
        region="Atsinanana", city="Toamasina", is_active=True,
    )
    db.add(ambassador_user)
    db.flush()

    ambassador = Ambassador(
        user_id=ambassador_user.id,
        ambassador_type=AmbassadorType.individual,
        status=AmbassadorStatus.active,
        public_name="Marie Rasoa — Toamasina",
        bio="Militante citoyenne active dans la région Atsinanana",
        zone_action="Atsinanana, Toamasina",
        sectors_interest="education,health,economy",
        objectives="Collecter 500 réponses d'ici décembre 2026",
        mobilization_capacity=200,
        charter_signed=True, charter_signed_at=datetime.utcnow(),
        verify_code=secrets.token_urlsafe(16),
        valid_from=datetime.utcnow(),
        valid_until=datetime.utcnow() + timedelta(days=365),
        total_responses_collected=45, valid_responses=42, trust_score=88.0,
    )
    db.add(ambassador)
    db.commit()
    print("✓ Utilisateurs créés")


def seed_consultations(db: Session):
    if db.query(Consultation).count() > 0:
        return

    admin = db.query(User).filter(User.role == UserRole.admin).first()
    if not admin:
        return

    consultation = Consultation(
        title="Priorités citoyennes pour Madagascar 2026",
        description="Dites-nous quelles sont vos priorités pour l'avenir de Madagascar.",
        scope=ConsultationScope.national, sector_main="citizen",
        sectors_related="education,economy,health",
        status=ConsultationStatus.active, is_public=True,
        created_by=admin.id,
        starts_at=datetime.utcnow(),
        ends_at=datetime.utcnow() + timedelta(days=90),
    )
    db.add(consultation)
    db.flush()

    questions = [
        Question(consultation_id=consultation.id, order_index=0,
                 question_type=QuestionType.single_choice,
                 text="Quel est le secteur le plus urgent pour Madagascar selon vous ?",
                 options=["Éducation","Santé","Économie","Infrastructure","Sécurité","Environnement","Autre"]),
        Question(consultation_id=consultation.id, order_index=1,
                 question_type=QuestionType.satisfaction_scale,
                 text="Comment évaluez-vous la qualité des services publics dans votre région ?",
                 options=["1 - Très mauvais","2","3","4","5 - Excellent"]),
        Question(consultation_id=consultation.id, order_index=2,
                 question_type=QuestionType.text,
                 text="Décrivez un problème concret que vous vivez au quotidien."),
    ]
    for q in questions:
        db.add(q)
    db.commit()
    print("✓ Consultation de démo créée")


def seed_alerts(db: Session):
    if db.query(Alert).count() > 0:
        return

    citizen = db.query(User).filter(User.role == UserRole.z_citizen).first()
    if not citizen:
        return

    alerts_data = [
        dict(title="Coupure d'eau fréquente — Toamasina Centre",
             description="Interruptions quotidiennes depuis 3 semaines. Les habitants n'ont plus accès à l'eau potable.",
             alert_type=AlertType.water_cut, severity=AlertSeverity.high,
             sector_main="water", sectors_related="health",
             region="Atsinanana", city="Toamasina",
             status=AlertStatus.published, is_public=True),
        dict(title="École sans enseignants — Ambositra",
             description="Deux classes sans enseignants depuis le début de l'année scolaire.",
             alert_type=AlertType.school_problem, severity=AlertSeverity.high,
             sector_main="education",
             region="Amoron'i Mania", city="Ambositra",
             status=AlertStatus.verified, is_public=True),
        dict(title="Route nationale impraticable — RN7",
             description="Portion de route totalement dégradée, bloquant l'accès aux villages.",
             alert_type=AlertType.infrastructure, severity=AlertSeverity.medium,
             sector_main="infrastructure",
             region="Haute Matsiatra", city="Fianarantsoa",
             status=AlertStatus.pending, is_public=False),
        dict(title="Mine illégale signalée — Ilakaka",
             description="Extraction non déclarée de saphirs par un groupe inconnu, avec complicité suspectée de forces locales.",
             alert_type=AlertType.corruption, severity=AlertSeverity.critical,
             sector_main="mines", sectors_related="security,environment",
             region="Ihorombe", city="Ilakaka",
             status=AlertStatus.pending, is_public=False, is_sensitive=True),
    ]
    for a in alerts_data:
        db.add(Alert(**a, author_id=citizen.id))
    db.commit()
    print("✓ Alertes de démo créées")


def seed_transparency(db: Session):
    """Données de démo pour le module Observatoire / Transparence"""
    if db.query(Entity).count() > 0:
        return

    admin = db.query(User).filter(User.role == UserRole.admin).first()
    admin_id = admin.id if admin else None

    # ─────────────────────────────────────────────────────────────
    # ENTITÉS
    # ─────────────────────────────────────────────────────────────

    entities_data = [
        # Personnalités politiques
        dict(name="Andry Rajoelina", entity_type=EntityType.politician,
             subtype=EntitySubtype.government,
             description="Président de la République de Madagascar depuis 2019. Ancien maire d'Antananarivo (2007-2009), puis président de la HAT (Haute Autorité de Transition) de 2009 à 2014.",
             active_since="2009", republic_period=RepublicPeriod.republic_4,
             region="Analamanga", suspicion_score=5.5, power_index=10.0,
             sector_codes="citizen,economy,mines,infrastructure", is_sensitive=False),

        dict(name="Marc Ravalomanana", entity_type=EntityType.politician,
             subtype=EntitySubtype.opposition,
             description="Ancien président de Madagascar (2002-2009). Chef de file de l'opposition. Fondateur du mouvement TIM (Tiako i Madagasikara).",
             active_since="2002", republic_period=RepublicPeriod.republic_3,
             region="Analamanga", suspicion_score=4.0, power_index=7.0,
             sector_codes="citizen,economy,food", is_sensitive=False),

        dict(name="Hajo Andrianainarivelo", entity_type=EntityType.politician,
             subtype=EntitySubtype.government,
             description="Vice-Premier ministre chargé du Développement et de l'Aménagement du territoire. Acteur influent dans les marchés publics d'infrastructure.",
             active_since="2019", republic_period=RepublicPeriod.republic_4,
             region="Analamanga", suspicion_score=6.0, power_index=7.5,
             sector_codes="infrastructure,territories,mines"),

        # Institutions
        dict(name="Présidence de la République", entity_type=EntityType.institution,
             subtype=EntitySubtype.government,
             description="Institution présidentielle de Madagascar. Siège au Palais d'Iavoloha.",
             active_since="1960", republic_period=RepublicPeriod.all_periods,
             region="Analamanga", power_index=10.0, sector_codes="citizen"),

        dict(name="Ministère des Mines et des Ressources Stratégiques", entity_type=EntityType.institution,
             subtype=EntitySubtype.government,
             description="Gère l'attribution des permis miniers, la réglementation et les partenariats dans le secteur extractif.",
             active_since="1960", republic_period=RepublicPeriod.republic_4,
             region="Analamanga", suspicion_score=7.0, power_index=8.0,
             sector_codes="mines,energy,environment", is_sensitive=True),

        dict(name="BIANCO (Bureau Indépendant Anti-Corruption)", entity_type=EntityType.institution,
             subtype=EntitySubtype.judiciary,
             description="Organe indépendant de lutte contre la corruption. Souvent critiqué pour son manque d'indépendance réelle vis-à-vis de l'exécutif.",
             active_since="2004", power_index=4.0, suspicion_score=3.5,
             region="Analamanga", sector_codes="citizen,security"),

        dict(name="Assemblée Nationale de Madagascar", entity_type=EntityType.institution,
             subtype=EntitySubtype.government,
             description="Chambre basse du parlement malgache. Dominée par la coalition IRD (Isika Rehetra Miaraka amin'i Andry Rajoelina) depuis 2019.",
             active_since="1960", republic_period=RepublicPeriod.all_periods,
             region="Analamanga", power_index=7.0, suspicion_score=4.5,
             sector_codes="citizen"),

        # Entreprises / Partenaires
        dict(name="Kraoma S.A. (Kraomita Malagasy)", entity_type=EntityType.company,
             subtype=EntitySubtype.economic,
             description="Entreprise d'État exploitant le chrome à Andriamena. Accusée de sous-déclarer sa production et de corruption de fonctionnaires locaux.",
             active_since="1967", region="Betsiboka",
             suspicion_score=7.8, power_index=6.0,
             sector_codes="mines,economy,environment", is_sensitive=True),

        dict(name="QMM / Rio Tinto Madagascar", entity_type=EntityType.company,
             subtype=EntitySubtype.foreign,
             description="Joint-venture entre Rio Tinto (80%) et l'État malgache (20%) exploitant l'ilménite à Fort-Dauphin. Controverses environnementales et bénéfices reversés.",
             active_since="2009", region="Anosy",
             suspicion_score=6.5, power_index=7.0,
             sector_codes="mines,environment,economy", is_sensitive=True),

        dict(name="Banque Mondiale / Madagascar", entity_type=EntityType.ptf,
             subtype=EntitySubtype.foreign,
             description="Principal bailleur de fonds de Madagascar. Conditionne ses prêts à des réformes de gouvernance. Budget annuel moyen : 300M USD.",
             active_since="1963", power_index=8.0, suspicion_score=2.0,
             sector_codes="economy,education,health,infrastructure"),

        dict(name="FMI — Fonds Monétaire International", entity_type=EntityType.ptf,
             subtype=EntitySubtype.foreign,
             description="Supervise le programme économique malgache. Publie régulièrement des rapports sur la gouvernance financière.",
             active_since="1963", power_index=8.5, suspicion_score=1.5,
             sector_codes="economy"),

        # Médias
        dict(name="Midi Madagasikara", entity_type=EntityType.media,
             subtype=EntitySubtype.independent,
             description="Quotidien francophone fondé en 1983. L'un des journaux les plus lus. Rédaction parfois sous pression gouvernementale.",
             active_since="1983", region="Analamanga",
             suspicion_score=3.0, power_index=4.0,
             sector_codes="citizen"),

        dict(name="MBS (Malagasy Broadcasting System)", entity_type=EntityType.media,
             subtype=EntitySubtype.government,
             description="Chaîne de télévision nationale. Fondée initialement par Andry Rajoelina avant d'être cédée. Accusée de propagande pro-gouvernementale.",
             active_since="2001", region="Analamanga",
             suspicion_score=7.0, power_index=6.0,
             sector_codes="citizen", is_sensitive=True),

        # Groupes suspects / réseaux
        dict(name="Réseau Saphir Ilakaka", entity_type=EntityType.group,
             subtype=EntitySubtype.suspect,
             description="Réseau informel de négociants en pierres précieuses opérant à Ilakaka et Sakaraha. Soupçonné de financer des acteurs politiques via la vente illégale de saphirs.",
             active_since="1998", region="Ihorombe",
             suspicion_score=9.2, power_index=5.0,
             sector_codes="mines,economy,security", is_sensitive=True, is_public=False),

        dict(name="Groupe Tiko (Ravalomanana)", entity_type=EntityType.company,
             subtype=EntitySubtype.economic,
             description="Conglomérat agro-alimentaire de Marc Ravalomanana. Accusé d'avoir bénéficié de marchés publics favorables et d'avantages fiscaux abusifs sous la présidence Ravalomanana (2002-2009).",
             active_since="1982", region="Analamanga",
             suspicion_score=6.0, power_index=6.5,
             sector_codes="food,economy", is_sensitive=True),
    ]

    entities = []
    for i, data in enumerate(entities_data):
        e = Entity(**data, created_by=admin_id)
        db.add(e)
        db.flush()
        e.slug = slugify(e.name, e.id)
        entities.append(e)
    db.commit()

    # Récupérer par nom pour les liens
    def get_entity(name):
        return next((e for e in entities if e.name == name), None)

    rajoelina = get_entity("Andry Rajoelina")
    ravalomanana = get_entity("Marc Ravalomanana")
    presidence = get_entity("Présidence de la République")
    min_mines = get_entity("Ministère des Mines et des Ressources Stratégiques")
    kraoma = get_entity("Kraoma S.A. (Kraomita Malagasy)")
    qmm = get_entity("QMM / Rio Tinto Madagascar")
    mbs = get_entity("MBS (Malagasy Broadcasting System)")
    reseau_saphir = get_entity("Réseau Saphir Ilakaka")
    tiko = get_entity("Groupe Tiko (Ravalomanana)")
    hajo = get_entity("Hajo Andrianainarivelo")

    # ─────────────────────────────────────────────────────────────
    # LIENS ENTRE ENTITÉS
    # ─────────────────────────────────────────────────────────────

    links = [
        dict(from_entity_id=rajoelina.id, to_entity_id=presidence.id,
             link_type=LinkType.controls, description="Rajoelina dirige l'exécutif depuis 2019", strength=10.0, is_verified=True),
        dict(from_entity_id=rajoelina.id, to_entity_id=mbs.id,
             link_type=LinkType.owns, description="MBS fondée par Rajoelina en 2001, cédée lors de son entrée en politique", strength=7.0, is_verified=True),
        dict(from_entity_id=rajoelina.id, to_entity_id=min_mines.id,
             link_type=LinkType.controls, description="Le Président nomme et révoque le ministre des Mines", strength=9.0, is_verified=True),
        dict(from_entity_id=min_mines.id, to_entity_id=kraoma.id,
             link_type=LinkType.controls, description="Le Ministère supervise Kraoma et signe les permis", strength=8.0, is_verified=True),
        dict(from_entity_id=min_mines.id, to_entity_id=qmm.id,
             link_type=LinkType.controls, description="Convention minière signée avec QMM/Rio Tinto", strength=7.5, is_verified=True),
        dict(from_entity_id=reseau_saphir.id, to_entity_id=min_mines.id,
             link_type=LinkType.finances, description="Soupçon de corruption de fonctionnaires du Ministère pour obtenir des permis", strength=6.0, is_verified=False),
        dict(from_entity_id=ravalomanana.id, to_entity_id=tiko.id,
             link_type=LinkType.owns, description="Fondateur et actionnaire majoritaire du groupe Tiko", strength=10.0, is_verified=True),
        dict(from_entity_id=rajoelina.id, to_entity_id=ravalomanana.id,
             link_type=LinkType.opposes, description="Rivaux politiques depuis le coup d'État de 2009", strength=9.0, is_verified=True),
        dict(from_entity_id=hajo.id, to_entity_id=presidence.id,
             link_type=LinkType.belongs_to, description="Membre du gouvernement, coalition IRD", strength=8.0, is_verified=True),
    ]
    for l in links:
        db.add(EntityLink(**l))
    db.commit()

    # ─────────────────────────────────────────────────────────────
    # FAITS
    # ─────────────────────────────────────────────────────────────

    facts_data = [
        # Faits vérifiés
        dict(
            title="Coup d'État de 2009 — Rajoelina prend le pouvoir",
            fact_type=FactType.decision,
            official_version="Transition politique pacifique suite à des manifestations populaires contre la gestion de Ravalomanana.",
            real_version="Coup d'État soutenu par une partie de l'armée. Rajoelina, alors maire d'Antananarivo, est propulsé à la tête d'une Haute Autorité de Transition non reconnue par l'UA. Madagascar est suspendu de l'Union Africaine et perd 500M USD d'aide internationale.",
            context="La crise éclate après la fermeture de la chaîne MBS par le gouvernement Ravalomanana en janvier 2009. Rajoelina mobilise la rue. Le 17 mars 2009, l'armée remet les commandes à Rajoelina.",
            event_date="2009-03-17", is_historical=True,
            republic_period="transition_2009",
            location="Antananarivo", region_code="Analamanga",
            sector_codes="citizen,security",
            gravity_score=9.5, suspicion_score=8.0, opacity_score=7.0,
            is_published=True, verification_status=FactVerif.verified,
            actors_data=[
                (rajoelina.id, ActorRole.author),
                (ravalomanana.id, ActorRole.victim),
            ],
            sources_data=[
                dict(source_type=SourceType.press, title="RFI — Le coup d'État malgache de 2009",
                     url="https://www.rfi.fr", reliability_score=9.0, is_verified=True),
                dict(source_type=SourceType.official_doc, title="Résolution UA — Suspension de Madagascar",
                     reliability_score=9.5, is_verified=True),
            ]
        ),
        dict(
            title="Scandale Rosewood — Exportation illégale de bois de rose (2009-2013)",
            fact_type=FactType.scandale,
            official_version="Le gouvernement de transition a suspendu les exportations de bois de rose. Quelques infractions isolées ont été constatées.",
            real_version="Pendant la période de transition (2009-2013), 460 000 rondins de bois de rose précieux ont été exportés illégalement depuis les parcs nationaux de Masoala et Marojejy. Les exportateurs bénéficiaient de permis délivrés par des fonctionnaires corrompus. Valeur estimée : plus de 300 millions USD. Aucune poursuite sérieuse n'a abouti.",
            context="Le bois de rose est protégé par la CITES. Les forêts de Madagascar sont parmi les plus riches du monde en biodiversité. La déforestation illégale a augmenté de 300% pendant la transition.",
            event_date="2009", event_date_end="2013", is_historical=True,
            republic_period="transition_2009",
            location="Masoala, Marojejy, Antananarivo", region_code="SAVA",
            sector_codes="environment,mines,economy,security",
            gravity_score=9.8, suspicion_score=9.5, opacity_score=8.5,
            is_published=True, verification_status=FactVerif.verified,
            actors_data=[(min_mines.id, ActorRole.author)],
            sources_data=[
                dict(source_type=SourceType.official_doc, title="Rapport Global Witness — Madagascar's Forests Lost Billions",
                     url="https://www.globalwitness.org", reliability_score=9.5, is_verified=True),
                dict(source_type=SourceType.press, title="Le Monde — Le trafic de bois précieux à Madagascar",
                     url="https://www.lemonde.fr", reliability_score=9.0, is_verified=True),
            ]
        ),
        dict(
            title="Contrat QMM/Rio Tinto — Convention minière de Fort-Dauphin",
            fact_type=FactType.accord,
            official_version="Partenariat stratégique entre l'État malgache et Rio Tinto pour exploiter l'ilménite. L'État détient 20% des parts via QMM. Création de 2000 emplois locaux prévue.",
            real_version="Selon les rapports de Global Witness et d'Oxfam, Madagascar ne reçoit que 1,5% des revenus miniers nets. Les communautés de Fort-Dauphin ont été déplacées sans compensation adéquate. La mangrove d'Anosy a été partiellement détruite. Entre 2009 et 2022, Madagascar a reçu 35M USD de revenus pour une valeur extraite estimée à 1,2 milliard USD.",
            context="La convention a été signée en 2005 sous Ravalomanana, mais l'exploitation industrielle a démarré en 2009 sous la transition.",
            event_date="2005", event_date_end="2025", is_historical=True,
            republic_period="republic_3",
            location="Fort-Dauphin (Tôlanaro)", region_code="Anosy",
            sector_codes="mines,environment,economy",
            gravity_score=8.0, suspicion_score=7.5, opacity_score=8.0,
            is_published=True, verification_status=FactVerif.verified,
            actors_data=[
                (qmm.id, ActorRole.beneficiary),
                (min_mines.id, ActorRole.author),
            ],
            sources_data=[
                dict(source_type=SourceType.official_doc, title="Convention minière QMM — Texte officiel partiel",
                     reliability_score=8.0, is_verified=True),
                dict(source_type=SourceType.financial, title="Rapport Oxfam — Recettes minières Madagascar 2009-2022",
                     url="https://www.oxfam.org", reliability_score=9.0, is_verified=True),
            ]
        ),
        dict(
            title="Promesse des 101 terrains — Distribution de terres à Antananarivo",
            fact_type=FactType.promesse,
            official_version="Le Président Rajoelina annonce la distribution de 101 terrains constructibles aux familles démunies d'Antananarivo dans le cadre du programme 'Trano ho an'ny Malagasy'.",
            real_version="Selon plusieurs enquêtes journalistiques, une partie des bénéficiaires étaient des proches de responsables politiques locaux. Des familles inscrites sur les listes initiales n'ont jamais reçu de terrain. Le programme a été suspendu sans bilan officiel publié.",
            context="Annonce faite lors d'un meeting politique à Mahamasina en 2021.",
            event_date="2021-06", is_historical=True,
            republic_period="republic_4",
            location="Antananarivo", region_code="Analamanga",
            sector_codes="citizen,territories,economy",
            gravity_score=7.0, suspicion_score=8.0, opacity_score=7.5,
            is_published=True, verification_status=FactVerif.verified,
            actors_data=[(rajoelina.id, ActorRole.author)],
            sources_data=[
                dict(source_type=SourceType.press, title="Midi Madagasikara — Enquête sur les 101 terrains",
                     reliability_score=7.5, is_verified=False),
                dict(source_type=SourceType.social_media, title="Déclaration officielle Présidence — Facebook",
                     reliability_score=8.0, is_verified=True),
            ]
        ),
        dict(
            title="Budget éducation 2024 — Sous-exécution de 43%",
            fact_type=FactType.decision,
            official_version="Le gouvernement affirme avoir investi massivement dans l'éducation pour la rentrée 2024, avec un budget de 800 milliards d'Ariary alloués.",
            real_version="Selon le rapport d'exécution budgétaire du FMI et du MFB, seuls 57% du budget éducation ont été effectivement décaissés. Motif officiel : 'retards administratifs'. Conséquence : 1 200 écoles publiques sans manuels scolaires en début d'année, 340 enseignants FRAM non payés depuis 4 mois.",
            context="Madagascar consacre environ 3,1% de son PIB à l'éducation, contre 6% recommandé par l'UNESCO pour les PMA.",
            event_date="2024", is_historical=False,
            republic_period="republic_4",
            location="National", region_code="national",
            sector_codes="education,economy",
            gravity_score=8.5, suspicion_score=7.0, opacity_score=6.5,
            is_published=True, verification_status=FactVerif.verified,
            actors_data=[(presidence.id, ActorRole.author)],
            sources_data=[
                dict(source_type=SourceType.official_doc, title="Rapport FMI — Article IV Madagascar 2024",
                     url="https://www.imf.org", reliability_score=9.5, is_verified=True),
                dict(source_type=SourceType.official_doc, title="Rapport d'exécution budgétaire MFB T3-2024",
                     reliability_score=9.0, is_verified=True),
            ]
        ),
        dict(
            title="Arrestation de Ruffin Rakotonjanahary — opposant emprisonné",
            fact_type=FactType.arrestation,
            official_version="Arrestation pour 'trouble à l'ordre public' et 'diffusion de fausses nouvelles' lors d'une manifestation non autorisée.",
            real_version="Ruffin Rakotonjanahary, responsable politique du parti Tiako i Madagasikara (opposition), arrêté 48h avant un grand rassemblement de l'opposition prévu à Mahamasina. Détenu 37 jours sans procès. Amnesty International le qualifie de 'prisonnier politique'. Libéré sans inculpation.",
            context="Contexte pré-électoral, 4 mois avant les présidentielles de novembre 2023.",
            event_date="2023-07", is_historical=True,
            republic_period="republic_4",
            location="Antananarivo", region_code="Analamanga",
            sector_codes="security,citizen",
            gravity_score=8.0, suspicion_score=8.5, opacity_score=8.0,
            is_sensitive=True, is_published=True, verification_status=FactVerif.verified,
            actors_data=[
                (presidence.id, ActorRole.author),
                (ravalomanana.id, ActorRole.target),
            ],
            sources_data=[
                dict(source_type=SourceType.press, title="Amnesty International — Madagascar : Libérer les prisonniers politiques",
                     url="https://www.amnesty.org", reliability_score=9.5, is_verified=True),
                dict(source_type=SourceType.press, title="RFI — Arrestation de l'opposant malgache",
                     url="https://www.rfi.fr", reliability_score=9.0, is_verified=True),
            ]
        ),
        dict(
            title="Réseau saphir d'Ilakaka — trafic estimé à 100M$/an",
            fact_type=FactType.transaction,
            official_version="Le gouvernement affirme que l'exploitation des pierres précieuses est réglementée. Des opérations de contrôle sont menées régulièrement.",
            real_version="Selon les douanes thaïlandaises et srilankaises (principaux marchés), 90% des saphirs malgaches sont exportés sans déclaration. Le réseau Ilakaka implique des intermédiaires locaux, des exportateurs sri-lankais et thaïlandais, et des 'facilitateurs' dans les services des mines. Pertes fiscales estimées à 40M USD/an pour l'État.",
            context="Ilakaka est devenu en 1998 l'un des plus grands gisements de saphirs du monde. La ville a explosé de 40 habitants à plus de 100 000 en 5 ans.",
            event_date="2000", event_date_end="2025", is_historical=False,
            republic_period="republic_4",
            location="Ilakaka, Sakaraha", region_code="Ihorombe",
            sector_codes="mines,economy,security",
            gravity_score=9.0, suspicion_score=9.3, opacity_score=9.0,
            is_sensitive=True, is_published=True, verification_status=FactVerif.in_review,
            actors_data=[
                (reseau_saphir.id, ActorRole.author),
                (min_mines.id, ActorRole.target),
            ],
            sources_data=[
                dict(source_type=SourceType.official_doc, title="Rapport EITI Madagascar — Secteur extractif 2023",
                     reliability_score=8.5, is_verified=True),
                dict(source_type=SourceType.financial, title="Données douanières Thaïlande — Importations saphirs 2020-2024",
                     reliability_score=8.0, is_verified=False),
            ]
        ),
        dict(
            title="Plan Émergence Madagascar (PEM) — Annonce des 13 villes",
            fact_type=FactType.projet,
            official_version="Le Plan Émergence Madagascar prévoit de construire 13 nouvelles villes modernes d'ici 2030, avec des zones industrielles, des hôpitaux de référence et des universités. Budget annoncé : 3 milliards USD.",
            real_version="Deux ans après l'annonce, seule la ville de Tanamasoandro (Antananarivo) a commencé des travaux. Le financement réel identifié reste partiel. Plusieurs PTF interrogés indiquent ne pas avoir confirmé leurs engagements. Le projet est utilisé comme outil de communication électorale.",
            context="Annonce faite lors du Sommet des investisseurs à Paris en 2023.",
            event_date="2023-11", is_historical=False,
            republic_period="republic_4",
            location="National — Antananarivo, Toamasina...", region_code="national",
            sector_codes="infrastructure,economy,territories",
            gravity_score=6.0, suspicion_score=7.5, opacity_score=7.0,
            is_published=True, verification_status=FactVerif.in_review,
            actors_data=[(rajoelina.id, ActorRole.author)],
            sources_data=[
                dict(source_type=SourceType.press, title="Présidence — Discours Plan Émergence Madagascar (vidéo officielle)",
                     reliability_score=8.0, is_verified=True),
                dict(source_type=SourceType.press, title="L'Express Madagascar — Où en est le Plan Émergence ?",
                     url="https://lexpress.mg", reliability_score=7.5, is_verified=False),
            ]
        ),
        dict(
            title="Fuite de données BIANCO — Dossiers classés non transmis au parquet",
            fact_type=FactType.scandale,
            official_version="Le BIANCO traite tous les dossiers de corruption dans les délais légaux.",
            real_version="Un lanceur d'alerte interne au BIANCO a révélé en 2024 qu'au moins 47 dossiers documentés de corruption de haut niveau n'ont pas été transmis au parquet depuis 2019, dont des dossiers impliquant des ministres en exercice. Les dossiers auraient été 'perdus' ou classés sans suite sur instruction.",
            context="Le BIANCO est censé être indépendant mais son budget est voté par le Parlement et son directeur nommé par le Président.",
            event_date="2024-03", is_historical=False,
            republic_period="republic_4",
            location="Antananarivo", region_code="Analamanga",
            sector_codes="citizen,security",
            gravity_score=9.5, suspicion_score=9.0, opacity_score=9.5,
            is_sensitive=True, is_published=True, verification_status=FactVerif.unverified,
            actors_data=[],
            sources_data=[
                dict(source_type=SourceType.testimony, title="Témoignage anonyme — agent BIANCO (identité protégée)",
                     reliability_score=6.0, is_verified=False),
            ]
        ),
    ]

    facts = []
    for i, data in enumerate(facts_data):
        actors_data = data.pop('actors_data', [])
        sources_data = data.pop('sources_data', [])

        f = Fact(**data, submitted_by=admin_id)
        db.add(f)
        db.flush()
        f.slug = slugify(f.title, f.id)

        for entity_id, role in actors_data:
            db.add(FactActor(fact_id=f.id, entity_id=entity_id, role=role))

        for src in sources_data:
            db.add(FactSource(fact_id=f.id, **src))

        facts.append(f)
    db.commit()

    # ─────────────────────────────────────────────────────────────
    # THREADS
    # ─────────────────────────────────────────────────────────────

    def get_fact_by_title(title_fragment):
        return next((f for f in facts if title_fragment in f.title), None)

    threads_data = [
        dict(
            title="Le cycle coup d'État → Transition → Légitimation (2009–2019)",
            description="Comment Rajoelina a pris le pouvoir par la force en 2009, géré une décennie de transition chaotique et obtenu une légitimité électorale en 2018. Les pertes pour Madagascar : 500M USD d'aide suspendue, déforestation massive, impunité totale.",
            category="repression_politique",
            sector_codes="citizen,security,economy",
            start_date="2009", end_date="2019", is_ongoing=False,
            is_published=True, verification_status=FactVerif.verified,
            gravity_score=9.0, suspicion_score=8.5,
            fact_titles=["Coup d'État de 2009", "Scandale Rosewood"],
        ),
        dict(
            title="L'industrie minière malgache : qui profite vraiment ?",
            description="Un fil qui retrace les conventions minières, les revenus officiels et réels, les acteurs en coulisse et les communautés sacrifiées. Du chrome au saphir en passant par l'ilménite.",
            category="corruption_ressources",
            sector_codes="mines,economy,environment",
            start_date="1998", is_ongoing=True,
            is_published=True, verification_status=FactVerif.verified,
            gravity_score=9.2, suspicion_score=9.0,
            fact_titles=["Contrat QMM/Rio Tinto", "Réseau saphir d'Ilakaka"],
        ),
        dict(
            title="Les promesses non tenues de la 4ème République",
            description="Toutes les grandes annonces depuis 2019 : Plan Émergence, 13 villes, terrains aux pauvres, budget éducation... Le fossé entre les discours officiels et la réalité documentée.",
            category="promesses_non_tenues",
            sector_codes="citizen,economy,infrastructure,education",
            start_date="2019", is_ongoing=True,
            is_published=True, verification_status=FactVerif.in_review,
            gravity_score=7.5, suspicion_score=7.8,
            fact_titles=["Promesse des 101 terrains", "Plan Émergence Madagascar", "Budget éducation 2024"],
        ),
    ]

    for t_data in threads_data:
        fact_titles = t_data.pop('fact_titles', [])
        thread = Thread(**t_data, created_by=admin_id)
        db.add(thread)
        db.flush()
        thread.slug = slugify(thread.title, thread.id)

        for pos, title_frag in enumerate(fact_titles):
            f = get_fact_by_title(title_frag)
            if f:
                db.add(ThreadFact(thread_id=thread.id, fact_id=f.id, position=pos))

    db.commit()
    print("✓ Module Observatoire — entités, faits, threads créés")


def seed_recent_facts(db: Session):
    """Ajoute les faits 2025-2026 sans toucher aux entités existantes."""
    SENTINEL = "Élection présidentielle 2023 — Rajoelina réélu"
    if db.query(Fact).filter(Fact.title == SENTINEL).first():
        return  # déjà inséré

    admin = db.query(User).filter(User.role == UserRole.admin).first()
    if not admin:
        return
    admin_id = admin.id

    def get_entity_by_name(name):
        return db.query(Entity).filter(Entity.name == name).first()

    rajoelina   = get_entity_by_name("Andry Rajoelina")
    ravalomanana = get_entity_by_name("Marc Ravalomanana")
    presidence  = get_entity_by_name("Présidence de la République")
    min_mines   = get_entity_by_name("Ministère des Mines et des Ressources Stratégiques")
    kraoma      = get_entity_by_name("Kraoma S.A. (Kraomita Malagasy)")
    qmm         = get_entity_by_name("QMM / Rio Tinto Madagascar")

    recent_facts = []

    if rajoelina and ravalomanana:
        recent_facts.append(dict(
            title="Élection présidentielle 2023 — Rajoelina réélu",
            fact_type=FactType.decision,
            official_version="Andry Rajoelina remporte l'élection présidentielle du 16 novembre 2023 avec 58,95% des voix dès le premier tour, selon les résultats officiels de la HCC.",
            real_version="L'opposition, menée par 10 candidats dont Ravalomanana, boycotte le second tour et conteste la légitimité du scrutin. Taux de participation officiel : 46,3% — le plus bas depuis 2002. La mission d'observation de l'UA note des 'irrégularités significatives' dans la gestion du fichier électoral. La CENI a refusé l'accès aux serveurs centraux lors du décompte.",
            context="Rajoelina est réélu pour un second mandat de 5 ans. L'opposition parle de 'hold-up électoral'. Plusieurs ambassadeurs occidentaux expriment leurs 'préoccupations' sans remettre en cause le résultat.",
            event_date="2023-11-16", is_historical=False,
            republic_period="republic_4",
            location="National", region_code="national",
            sector_codes="citizen,security",
            gravity_score=8.5, suspicion_score=8.0, opacity_score=7.5,
            is_published=True, verification_status=FactVerif.verified,
            actors_data=[(rajoelina.id, ActorRole.author), (ravalomanana.id, ActorRole.target)],
            sources_data=[
                dict(source_type=SourceType.official_doc, title="Résultats officiels HCC — Présidentielle 2023",
                     url="https://hcc.gov.mg", reliability_score=8.0, is_verified=True),
                dict(source_type=SourceType.press, title="RFI — Élection Madagascar : l'opposition dénonce une fraude",
                     url="https://www.rfi.fr", reliability_score=9.0, is_verified=True),
                dict(source_type=SourceType.press, title="Rapport préliminaire UA — Mission d'observation électorale Madagascar 2023",
                     reliability_score=8.5, is_verified=True),
            ]
        ))

    if presidence:
        recent_facts.append(dict(
            title="Crise économique 2025 — Ariary en chute libre, inflation record",
            fact_type=FactType.scandale,
            official_version="Le gouvernement affirme maintenir la stabilité macroéconomique et que l'inflation est 'sous contrôle'.",
            real_version="En janvier 2025, l'Ariary a perdu 18% de sa valeur face au dollar en 12 mois. L'inflation atteint 14,7% selon la BFM, touchant principalement le riz (hausse de 34%), le carburant et les médicaments. Plus de 2,4 millions de Malgaches supplémentaires ont basculé sous le seuil de pauvreté en 2024 selon la Banque Mondiale. Les réserves en devises couvrent à peine 2,8 mois d'importations.",
            context="Madagascar est parmi les 5 pays les plus pauvres du monde en 2025 selon l'IDH. La suspension partielle de l'aide internationale (MCC, MCA) suite aux irrégularités électorales aggrave la crise.",
            event_date="2025-01", is_historical=False,
            republic_period="republic_4",
            location="National", region_code="national",
            sector_codes="economy,citizen",
            gravity_score=9.0, suspicion_score=7.0, opacity_score=6.5,
            is_published=True, verification_status=FactVerif.verified,
            actors_data=[(presidence.id, ActorRole.author)],
            sources_data=[
                dict(source_type=SourceType.official_doc, title="Rapport Banque Mondiale — Madagascar Poverty Assessment 2025",
                     url="https://worldbank.org", reliability_score=9.5, is_verified=True),
                dict(source_type=SourceType.official_doc, title="BFM — Bulletin mensuel de statistiques janvier 2025",
                     reliability_score=9.0, is_verified=True),
            ]
        ))

    if min_mines and kraoma:
        recent_facts.append(dict(
            title="Kraoma — Arrêt de production et licenciement de 1 200 ouvriers (2025)",
            fact_type=FactType.decision,
            official_version="L'arrêt de production à Kraoma est présenté comme 'temporaire', lié à une chute mondiale des prix du chrome.",
            real_version="La Kraoma, société d'État d'extraction de chrome, a suspendu toutes ses opérations à Bemanevika (Diana) en mars 2025 suite à des dettes non remboursées à ses fournisseurs d'énergie. 1 200 ouvriers ont été mis en chômage technique sans indemnités. Des audits internes non publiés pointent des détournements dans les contrats de maintenance entre 2021 et 2024.",
            context="Kraoma est l'une des rares entreprises minières à capitaux publics. Sa privatisation partielle est en discussion depuis 2022 mais aucun dossier officiel n'a été rendu public.",
            event_date="2025-03", is_historical=False,
            republic_period="republic_4",
            location="Bemanevika, Ambilobe", region_code="Diana",
            sector_codes="mines,economy,labor",
            gravity_score=8.5, suspicion_score=8.0, opacity_score=8.5,
            is_sensitive=True, is_published=True, verification_status=FactVerif.in_review,
            actors_data=[
                (min_mines.id, ActorRole.author),
                (kraoma.id, ActorRole.target),
            ],
            sources_data=[
                dict(source_type=SourceType.press, title="Midi Madagasikara — Kraoma : 1200 travailleurs en chômage",
                     url="https://www.midi-madagasikara.mg", reliability_score=7.5, is_verified=True),
                dict(source_type=SourceType.testimony, title="Témoignages ouvriers Kraoma — collecte terrain Z-Ambassador (Diana)",
                     reliability_score=6.5, is_verified=False),
            ]
        ))

    if qmm and min_mines:
        recent_facts.append(dict(
            title="QMM / Rio Tinto — Déversement toxique dans la lagune Anosy (2025)",
            fact_type=FactType.scandale,
            official_version="QMM indique que les niveaux de radioactivité et de métaux lourds dans les zones de décantation sont 'dans les limites réglementaires malgaches'.",
            real_version="En février 2025, des analyses indépendantes commandées par l'ONG MadaGreen révèlent des concentrations d'uranium et de thorium 12 fois supérieures aux normes OMS dans trois villages riverains de Fort-Dauphin. L'ONE (Office National de l'Environnement) a refusé de rendre public son propre rapport d'inspection malgré deux demandes officielles. Rio Tinto conteste les méthodes de prélèvement.",
            context="Le projet QMM extrait de l'ilménite depuis 2009 dans la région Anosy. La convention minière originale exempte QMM de plusieurs obligations environnementales standards.",
            event_date="2025-02", is_historical=False,
            republic_period="republic_4",
            location="Fort-Dauphin (Tôlanaro)", region_code="Anosy",
            sector_codes="mines,environment,health",
            gravity_score=9.5, suspicion_score=9.0, opacity_score=9.5,
            is_sensitive=True, is_published=True, verification_status=FactVerif.in_review,
            actors_data=[
                (qmm.id, ActorRole.author),
                (min_mines.id, ActorRole.target),
            ],
            sources_data=[
                dict(source_type=SourceType.press, title="MadaGreen — Rapport d'analyse eau et sol Anosy 2025",
                     reliability_score=7.0, is_verified=False),
                dict(source_type=SourceType.press, title="Le Monde Afrique — Madagascar : pollution minière à Fort-Dauphin",
                     url="https://www.lemonde.fr", reliability_score=9.0, is_verified=True),
            ]
        ))

    if presidence:
        recent_facts.append(dict(
            title="Opération Tany Maitso — Déboisement autorisé en zone protégée (2025)",
            fact_type=FactType.decision,
            official_version="Le gouvernement autorise des 'zones d'activité agro-industrielle' dans certains couloirs forestiers pour 'développer l'emploi rural'.",
            real_version="Des décrets signés en juin 2025 ont déclassé 47 000 hectares de forêts humides classées en zone protégée dans les régions Atsinanana et Analanjirofo. Les bénéficiaires des nouvelles concessions agricoles sont des sociétés enregistrées aux îles Maurice, sans bilan environnemental préalable. Les populations locales n'ont pas été consultées.",
            context="Madagascar a déjà perdu 90% de ses forêts originelles. Les écosystèmes forestiers restants abritent plus de 200 espèces endémiques menacées d'extinction.",
            event_date="2025-06", is_historical=False,
            republic_period="republic_4",
            location="Atsinanana / Analanjirofo", region_code="Atsinanana",
            sector_codes="environment,territories,economy",
            gravity_score=9.0, suspicion_score=8.5, opacity_score=8.0,
            is_sensitive=True, is_published=True, verification_status=FactVerif.unverified,
            actors_data=[(presidence.id, ActorRole.author)],
            sources_data=[
                dict(source_type=SourceType.press, title="Global Forest Watch — Déforestation Madagascar 2025",
                     url="https://www.globalforestwatch.org", reliability_score=9.0, is_verified=True),
                dict(source_type=SourceType.testimony, title="Témoignages communautés forestières — Collecte terrain",
                     reliability_score=6.0, is_verified=False),
            ]
        ))

    if presidence:
        recent_facts.append(dict(
            title="Coupure internet ciblée lors des manifestations de janvier 2026",
            fact_type=FactType.scandale,
            official_version="Aucune déclaration officielle sur des restrictions internet.",
            real_version="Lors des manifestations contre la vie chère des 15-17 janvier 2026 à Antananarivo, les observatoires OONI et NetBlocks documentent des ralentissements ciblés de Twitter/X, Facebook et WhatsApp entre 17h et 22h chaque jour. La TELMA et l'ARTEC (régulateur) n'ont pas répondu aux demandes d'explication. C'est la troisième fois en 18 mois qu'un tel phénomène est documenté à Madagascar.",
            context="Les coupures internet sélectives lors de crises politiques sont un outil utilisé par plusieurs régimes africains pour limiter la coordination des manifestants.",
            event_date="2026-01-15", is_historical=False,
            republic_period="republic_4",
            location="Antananarivo", region_code="Analamanga",
            sector_codes="citizen,security,media",
            gravity_score=8.5, suspicion_score=9.0, opacity_score=9.5,
            is_sensitive=True, is_published=True, verification_status=FactVerif.verified,
            actors_data=[(presidence.id, ActorRole.author)],
            sources_data=[
                dict(source_type=SourceType.official_doc, title="NetBlocks — Internet disruption Madagascar January 2026",
                     url="https://netblocks.org", reliability_score=9.5, is_verified=True),
                dict(source_type=SourceType.official_doc, title="OONI — Network measurement Madagascar 2026-01",
                     url="https://ooni.org", reliability_score=9.5, is_verified=True),
            ]
        ))

    for data in recent_facts:
        actors_data = data.pop('actors_data', [])
        sources_data = data.pop('sources_data', [])

        f = Fact(**data, submitted_by=admin_id)
        db.add(f)
        db.flush()
        f.slug = slugify(f.title, f.id)

        for entity_id, role in actors_data:
            db.add(FactActor(fact_id=f.id, entity_id=entity_id, role=role))

        for src in sources_data:
            db.add(FactSource(fact_id=f.id, **src))

    db.commit()
    print(f"✓ {len(recent_facts)} faits 2025-2026 ajoutés")


def run_seed(db: Session):
    print("Démarrage du seed...")
    seed_sectors(db)
    seed_superadmin(db)   # Toujours en premier — indépendant du reste
    seed_users(db)
    seed_consultations(db)
    seed_alerts(db)
    seed_transparency(db)
    seed_recent_facts(db)
    print("✓ Seed terminé avec succès")
