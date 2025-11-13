"""Contains a function to generate person data."""

from __future__ import annotations

from enum import StrEnum
from typing import Any, Iterable, Optional, List

import polars as pl

from ..random_utils import fake, make_ids, weighted_sample

__all__ = ["PersonField", "generate"]


class PersonField(StrEnum):
    """Enumerates output column names for Person in snake_case.

    When invoked via an orchestrator with a registry, the calling layer can
    re-order and reconcile columns to a spreadsheet spec; this generator
    emits the full set so padding/dropping isn't needed.
    """

    # core identifiers / lineage
    person_id = "person_id"
    source_table = "person_source_table_name"
    source_id_field = "person_source_id_field_name"
    source_id = "person_source_field_value"
    company_id = "company_id"

    # lead / ownership / role
    lead_role_name = "lead_role_name"
    lead_source_name = "lead_source_name"
    job_title_value = "job_title_value"
    external_sales_person_id = "external_sales_person_id"

    # status flags
    active_ind = "active_ind"
    contact_status = "contact_status"

    # consent (TM/SMS/Mobile/Email) + standardised values + timestamps
    tm_consent_ind = "tm_consent_ind"
    tm_standardised_consent_value = "tm_standardised_consent_value"
    tm_consent_dtm = "tm_consent_dtm"

    sms_consent_ind = "sms_consent_ind"
    sms_standardised_consent_value = "sms_standardised_consent_value"
    sms_consent_dtm = "sms_consent_dtm"

    mobile_consent_ind = "mobile_consent_ind"
    mobile_standardised_consent_value = "mobile_standardised_consent_value"
    mobile_consent_dtm = "mobile_consent_dtm"

    email_consent_ind = "email_consent_ind"
    email_standardised_consent_value = "email_standardised_consent_value"
    email_consent_dtm = "email_consent_dtm"

    # address
    city_name = "city_name"
    state_name = "state_name"
    country_name = "country_name"
    postal_code = "postal_code"

    # direct mail consent
    direct_mail_consent_ind = "direct_mail_consent_ind"
    direct_mail_standardised_consent_value = "direct_mail_standardised_consent_value"

    # app / service messages
    app_consent_flag_ind = "app_consent_ind"
    app_consent_dtm = "app_consent_dtm"
    service_message_only_ind = "service_message_only_ind"

    # suppressions
    overall_suppression_ind = "overall_suppression_ind"
    phone_suppression_ind = "phone_suppression_ind"
    email_suppression_ind = "email_suppression_ind"
    mobile_suppression_ind = "mobile_suppression_ind"
    mail_suppression_ind = "mail_suppression_ind"

    # quality / misc
    vulgarity_ind = "vulgarity_ind"

    # prime contact indicators
    prime_telephone_contact_ind = "prime_telephone_contact_ind"
    prime_mobile_contact_ind = "prime_mobile_contact_ind"
    prime_email_contact_ind = "prime_email_contact_ind"
    prime_direct_mail_contact_ind = "prime_direct_mail_contact_ind"
    prime_sms_contact_ind = "prime_sms_contact_ind"
    prime_visit_contact_ind = "prime_visit_contact_ind"

    # roles & ranking
    key_decision_maker_ind = "key_decision_maker_ind"
    best_sms_contact_priority_number = "best_sms_contact_priority_number"
    best_phone_contact_priority_number = "best_phone_contact_priority_number"
    best_email_contact_priority_number = "best_email_contact_priority_number"
    best_dm_contact_priority_number = "best_dm_contact_priority_number"
    uniquerankemail = "contact_unique_rank_email"
    uniquerankphone = "contact_unique_rank_phone"
    uniqueranksms = "contact_unique_rank_sms"
    uniquerankdm = "contact_unique_rank_dm"

    # sourcing & lifecycle
    marketo_sourced_ind = "marketo_sourced_ind"
    is_billing_contact_ind = "is_billing_contact_ind"
    delete_ind = "delete_ind"
    record_insert_dtm = "record_insert_dtm"
    record_update_dtm = "record_update_dtm"
    contactless_company_ind = "contactless_company_ind"


# Shared small helpers
STANDARDISED_CONSENT = ["Consent", "Dissent", "Not Asked", "Blank", "Implied"]
STD_WEIGHTS = [0.55, 0.10, 0.15, 0.10, 0.10]  # skew towards Consent

LEAD_ROLES = [
    "Primary Contact",
    "Technical Contact",
    "Billing Contact",
    "Decision Maker",
    "Influencer",
    "End User",
    "Unknown",
]
LEAD_SOURCES = [
    "CRM",
    "Marketo",
    "Salesforce",
    "HubSpot",
    "Web Form",
    "Manual Entry",
    "Partner Import",
]
CONTACT_STATUS = ["Active", "Inactive"]


def _maybe_timestamp(enabled_flags: Iterable[bool]) -> list[pl.datetime]:
    """Generate a list of timestamps where True -> recent dt, False -> None."""
    out: list[Any] = []
    for flag in enabled_flags:
        if flag:
            out.append(fake.date_time_between(start_date="-3y", end_date="now", tzinfo=None))
        else:
            out.append(None)
    return out


def _pick_country_state_city(n: int) -> tuple[list[str], list[str], list[str]]:
    """Return parallel lists for country, state/region, and city.

    Avoids Faker's locale-specific state/county/department providers to keep things portable.
    """
    countries = ["United Kingdom", "United States", "Germany", "France", "India"]

    uk_regions = [
        "Greater London",
        "West Midlands",
        "Greater Manchester",
        "West Yorkshire",
        "Kent",
        "Hampshire",
        "Essex",
        "Lancashire",
        "Surrey",
        "Merseyside",
    ]
    us_states = [
        "California",
        "Texas",
        "New York",
        "Florida",
        "Illinois",
        "Pennsylvania",
        "Ohio",
        "Georgia",
        "North Carolina",
        "Michigan",
    ]
    de_laender = [
        "Bayern",
        "Nordrhein-Westfalen",
        "Baden-Württemberg",
        "Niedersachsen",
        "Hessen",
        "Sachsen",
        "Rheinland-Pfalz",
        "Berlin",
        "Schleswig-Holstein",
        "Thüringen",
    ]
    fr_regions = [
        "Île-de-France",
        "Auvergne-Rhône-Alpes",
        "Nouvelle-Aquitaine",
        "Occitanie",
        "Hauts-de-France",
        "Grand Est",
        "Provence-Alpes-Côte d'Azur",
        "Bretagne",
    ]
    in_states = [
        "Maharashtra",
        "Karnataka",
        "Tamil Nadu",
        "Delhi",
        "Telangana",
        "Uttar Pradesh",
        "Gujarat",
        "West Bengal",
        "Rajasthan",
        "Madhya Pradesh",
    ]

    countries = weighted_sample(countries, [0.45, 0.20, 0.12, 0.10, 0.13], n)
    states, cities = [], []
    for c in countries:
        if c == "United Kingdom":
            states.append(fake.random_element(uk_regions))
            cities.append(fake.city())
        elif c == "United States":
            states.append(fake.random_element(us_states))
            cities.append(fake.city())
        elif c == "Germany":
            states.append(fake.random_element(de_laender))
            cities.append(fake.city())
        elif c == "France":
            states.append(fake.random_element(fr_regions))
            cities.append(fake.city())
        else:  # India
            states.append(fake.random_element(in_states))
            cities.append(fake.city())
    return countries, states, cities


def generate(  # noqa: PLR0912,PLR0915 Too many branches (21 > 12) Too many statements (98 > 50)
    n: int, **kwargs: Any
) -> pl.DataFrame:
    """Generate a DataFrame of person data.

    :param n: Number of rows to generate
    :param kwargs: May include `prior` with a "Company" DataFrame to source company_ids
    :returns: Polars DataFrame with all fields in the Person spec
    """
    # Try to source Company IDs from prior for FK coherence
    prior = kwargs.get("prior", {})
    company_df = prior.get("Company")
    if company_df is not None and "company_id" in company_df.columns:
        company_ids: list[str] = company_df.get_column("company_id").to_list()
    else:
        company_ids = []

    # IDs
    person_ids = make_ids(n, "PER")

    # Company assignment (allow duplicates)
    company_id: List[Optional[str]] = (
        weighted_sample(company_ids, n=n) if company_ids else [None] * n
    )

    # Lead / ownership
    lead_role_name = weighted_sample(LEAD_ROLES, n=n)
    lead_source_name = weighted_sample(LEAD_SOURCES, n=n)
    job_title_value = [fake.job() for _ in range(n)]
    external_sales_person_id = [
        (
            f"SF{fake.random_int(min=100000, max=999999)}"
            if fake.boolean(chance_of_getting_true=35)
            else None
        )
        for _ in range(n)
    ]

    # Status
    active_ind = [fake.boolean(chance_of_getting_true=88) for _ in range(n)]
    contact_status = ["Active" if a else "Inactive" for a in active_ind]

    # Consent (booleans first so we can drive timestamps)
    tm_consent_ind = [fake.boolean(chance_of_getting_true=60) for _ in range(n)]
    sms_consent_ind = [fake.boolean(chance_of_getting_true=55) for _ in range(n)]
    mobile_consent_ind = [fake.boolean(chance_of_getting_true=50) for _ in range(n)]
    email_consent_ind = [fake.boolean(chance_of_getting_true=65) for _ in range(n)]
    direct_mail_consent_ind = [fake.boolean(chance_of_getting_true=40) for _ in range(n)]
    app_consent_flag_ind = [fake.boolean(chance_of_getting_true=30) for _ in range(n)]

    # Standardised values (skewed to Consent)
    tm_standardised = weighted_sample(STANDARDISED_CONSENT, STD_WEIGHTS, n)
    sms_standardised = weighted_sample(STANDARDISED_CONSENT, STD_WEIGHTS, n)
    mobile_standardised = weighted_sample(STANDARDISED_CONSENT, STD_WEIGHTS, n)
    email_standardised = weighted_sample(STANDARDISED_CONSENT, STD_WEIGHTS, n)
    direct_mail_standardised = weighted_sample(STANDARDISED_CONSENT, STD_WEIGHTS, n)

    # Consent timestamps (only when ind == True)
    tm_consent_dtm = _maybe_timestamp(tm_consent_ind)
    sms_consent_dtm = _maybe_timestamp(sms_consent_ind)
    mobile_consent_dtm = _maybe_timestamp(mobile_consent_ind)
    email_consent_dtm = _maybe_timestamp(email_consent_ind)
    app_consent_dtm = _maybe_timestamp(app_consent_flag_ind)

    # Address
    countries, states, cities = _pick_country_state_city(n)
    postal_code = [fake.postcode() for _ in range(n)]

    # Suppressions (overall often correlates with channel suppressions)
    phone_supp = [fake.boolean(chance_of_getting_true=15) for _ in range(n)]
    email_supp = [fake.boolean(chance_of_getting_true=12) for _ in range(n)]
    mobile_supp = [fake.boolean(chance_of_getting_true=10) for _ in range(n)]
    mail_supp = [fake.boolean(chance_of_getting_true=18) for _ in range(n)]
    overall_supp = [
        (phone_supp[i] or email_supp[i] or mobile_supp[i] or mail_supp[i] or fake.boolean(5))
        for i in range(n)
    ]

    # Misc quality
    vulgarity_ind = [False for _ in range(n)]  # you can wire this to a detector later

    # Prime contact indicators: pick one or two "prime" channels, skew to email/phone
    prime_email = [False] * n
    prime_phone = [False] * n
    prime_mobile = [False] * n
    prime_dm = [False] * n
    prime_sms = [False] * n
    prime_visit = [False] * n
    for i in range(n):
        choice = weighted_sample(
            ["email", "phone", "mobile", "dm", "sms", "visit"],
            [0.35, 0.30, 0.12, 0.08, 0.10, 0.05],
            1,
        )[0]
        if choice == "email":
            prime_email[i] = True
        elif choice == "phone":
            prime_phone[i] = True
        elif choice == "mobile":
            prime_mobile[i] = True
        elif choice == "dm":
            prime_dm[i] = True
        elif choice == "sms":
            prime_sms[i] = True
        else:
            prime_visit[i] = True
        # small chance of a second prime
        if fake.boolean(10):
            second = weighted_sample(["email", "phone", "mobile", "dm", "sms", "visit"], None, 1)[0]
            if second == "email":
                prime_email[i] = True
            elif second == "phone":
                prime_phone[i] = True
            elif second == "mobile":
                prime_mobile[i] = True
            elif second == "dm":
                prime_dm[i] = True
            elif second == "sms":
                prime_sms[i] = True
            else:
                prime_visit[i] = True

    # Best priority numbers (1 is best). Skew to 1/2.
    best_email = weighted_sample([1, 2, 3], [0.6, 0.3, 0.1], n)
    best_phone = weighted_sample([1, 2, 3], [0.55, 0.3, 0.15], n)
    best_sms = weighted_sample([1, 2, 3], [0.5, 0.35, 0.15], n)
    best_dm = weighted_sample([1, 2, 3], [0.45, 0.35, 0.20], n)

    # If a channel is prime, nudge its priority to 1
    for i in range(n):
        if prime_email[i]:
            best_email[i] = 1
        if prime_phone[i]:
            best_phone[i] = 1
        if prime_sms[i]:
            best_sms[i] = 1
        if prime_dm[i]:
            best_dm[i] = 1

    # Sourcing & lifecycle
    marketo_sourced_ind = [fake.boolean(chance_of_getting_true=25) for _ in range(n)]
    is_billing_contact_ind = [("Billing Contact" in lead_role_name[i]) for i in range(n)]
    delete_ind = [fake.boolean(chance_of_getting_true=2) for _ in range(n)]  # rare deletes
    record_insert_dtm = [
        fake.date_time_between(start_date="-3y", end_date="-1d", tzinfo=None) for _ in range(n)
    ]
    record_update_dtm = [
        fake.date_time_between(start_date=record_insert_dtm[i], end_date="now", tzinfo=None)
        for i in range(n)
    ]
    contactless_company_ind = [company_id[i] is None for i in range(n)]

    # Lineage columns
    source_table = weighted_sample(
        ["CRM", "Marketo", "Salesforce", "HubSpot", "Web Form", "Manual Entry"], n=n
    )
    source_id_field = weighted_sample(
        ["contact_id", "lead_id", "sf_contact_id", "hs_contact_id"], n=n
    )
    source_id = [f"SRC{fake.random_int(min=100000, max=999999)}" for _ in range(n)]

    # Build the frame
    df = pl.DataFrame(
        {
            PersonField.person_id: person_ids,
            PersonField.source_table: source_table,
            PersonField.source_id_field: source_id_field,
            PersonField.source_id: source_id,
            PersonField.company_id: company_id,
            PersonField.lead_role_name: lead_role_name,
            PersonField.lead_source_name: lead_source_name,
            PersonField.job_title_value: job_title_value,
            PersonField.external_sales_person_id: external_sales_person_id,
            PersonField.active_ind: active_ind,
            PersonField.contact_status: contact_status,
            PersonField.tm_consent_ind: tm_consent_ind,
            PersonField.tm_standardised_consent_value: tm_standardised,
            PersonField.tm_consent_dtm: tm_consent_dtm,
            PersonField.sms_consent_ind: sms_consent_ind,
            PersonField.sms_standardised_consent_value: sms_standardised,
            PersonField.sms_consent_dtm: sms_consent_dtm,
            PersonField.mobile_consent_ind: mobile_consent_ind,
            PersonField.mobile_standardised_consent_value: mobile_standardised,
            PersonField.mobile_consent_dtm: mobile_consent_dtm,
            PersonField.email_consent_ind: email_consent_ind,
            PersonField.email_standardised_consent_value: email_standardised,
            PersonField.email_consent_dtm: email_consent_dtm,
            PersonField.city_name: cities,
            PersonField.state_name: states,
            PersonField.country_name: countries,
            PersonField.postal_code: postal_code,
            PersonField.direct_mail_consent_ind: direct_mail_consent_ind,
            PersonField.direct_mail_standardised_consent_value: direct_mail_standardised,
            PersonField.app_consent_flag_ind: app_consent_flag_ind,
            PersonField.app_consent_dtm: app_consent_dtm,
            PersonField.service_message_only_ind: [
                fake.boolean(chance_of_getting_true=10) for _ in range(n)
            ],
            PersonField.overall_suppression_ind: overall_supp,
            PersonField.phone_suppression_ind: phone_supp,
            PersonField.email_suppression_ind: email_supp,
            PersonField.mobile_suppression_ind: mobile_supp,
            PersonField.mail_suppression_ind: mail_supp,
            PersonField.vulgarity_ind: vulgarity_ind,
            PersonField.prime_telephone_contact_ind: prime_phone,
            PersonField.prime_mobile_contact_ind: prime_mobile,
            PersonField.prime_email_contact_ind: prime_email,
            PersonField.prime_direct_mail_contact_ind: prime_dm,
            PersonField.prime_sms_contact_ind: prime_sms,
            PersonField.prime_visit_contact_ind: prime_visit,
            PersonField.key_decision_maker_ind: [
                fake.boolean(chance_of_getting_true=22) for _ in range(n)
            ],
            PersonField.best_sms_contact_priority_number: best_sms,
            PersonField.best_phone_contact_priority_number: best_phone,
            PersonField.best_email_contact_priority_number: best_email,
            PersonField.best_dm_contact_priority_number: best_dm,
            # unique rank placeholders (filled below via group-by row_number)
            PersonField.uniquerankemail: [None] * n,
            PersonField.uniquerankphone: [None] * n,
            PersonField.uniqueranksms: [None] * n,
            PersonField.uniquerankdm: [None] * n,
            PersonField.marketo_sourced_ind: marketo_sourced_ind,
            PersonField.is_billing_contact_ind: is_billing_contact_ind,
            PersonField.delete_ind: delete_ind,
            PersonField.record_insert_dtm: record_insert_dtm,
            PersonField.record_update_dtm: record_update_dtm,
            PersonField.contactless_company_ind: contactless_company_ind,
        }
    )

    # Compute per-company unique rank within each best_* priority number
    # If company_id is None, we still rank within that None bucket (ok for mock data).
    def add_unique_rank(df_in: pl.DataFrame, best_col: str, out_col: str) -> pl.DataFrame:
        return df_in.with_columns(
            pl.when(pl.col(best_col).is_not_null())
            .then(
                pl.col(best_col)
                .over([PersonField.company_id, best_col])
                .cum_count()
                .add(1)  # row_number starting at 1
            )
            .otherwise(None)
            .alias(out_col)
        )

    df = add_unique_rank(
        df, PersonField.best_email_contact_priority_number, PersonField.uniquerankemail
    )
    df = add_unique_rank(
        df, PersonField.best_phone_contact_priority_number, PersonField.uniquerankphone
    )
    df = add_unique_rank(
        df, PersonField.best_sms_contact_priority_number, PersonField.uniqueranksms
    )
    return add_unique_rank(
        df, PersonField.best_dm_contact_priority_number, PersonField.uniquerankdm
    )
