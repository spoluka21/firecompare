"""
КРОК 3. Compliance-фільтр

Перевіряє відповідність виробника активним юрисдикціям клієнта.

ВАЖЛИВО: фільтр на ПЕРЕТИН — виробник має пройти ВСІ активні юрисдикції.
Це жорсткіше, ніж окремо UA, але точно: ти не можеш зробити систему, яка
пройде в Україні, але провалиться у британській страховій.

Статуси (3 рівні):
- PASS    — повна відповідність всім активним юрисдикціям
- WARNING — формально проходить, але з нюансами (наприклад, окремі SKU
            потребують перевірки, або сертифікат «в процесі»)
- FAIL    — не проходить хоча б одну активну юрисдикцію

Виробники зі статусом FAIL виключаються з comparison-set, але показуються
у звіті як «розглядався, виключений» з прозорою причиною.
"""
from pydantic import BaseModel, Field

from schemas.catalog import CertificationStatus, Manufacturer
from schemas.object_state import Jurisdiction, ObjectState


class JurisdictionResult(BaseModel):
    """Результат перевірки однієї юрисдикції"""
    jurisdiction: Jurisdiction
    status: str  # "pass" | "warning" | "fail"
    reasoning: str


class ComplianceResult(BaseModel):
    """Загальний результат compliance-перевірки виробника"""
    manufacturer_id: str
    overall_status: str  # "pass" | "warning" | "fail"
    by_jurisdiction: list[JurisdictionResult] = Field(default_factory=list)
    summary_message: str = ""


# ═══════════════════════════════════════════════════════════════════
# ПРАВИЛА ПЕРЕВІРКИ ОДНІЄЇ ЮРИСДИКЦІЇ
# ═══════════════════════════════════════════════════════════════════


def check_ua_jurisdiction(manufacturer: Manufacturer) -> JurisdictionResult:
    """
    UA: вимагається ДСТУ EN 54 сертифікація.
    
    Особливий випадок Cofem: ДСТУ EN 54 «в процесі» — приймаємо як WARNING,
    бо професійна відповідальність проєктувальника покриває цей кейс.
    """
    cert = manufacturer.certifications.UA_DSTU_EN54
    
    if cert.status == CertificationStatus.FULL:
        return JurisdictionResult(
            jurisdiction=Jurisdiction.UA,
            status="pass",
            reasoning="Повна сертифікація ДСТУ EN 54 в Україні",
        )
    elif cert.status == CertificationStatus.IN_PROCESS:
        return JurisdictionResult(
            jurisdiction=Jurisdiction.UA,
            status="warning",
            reasoning=(
                "ДСТУ EN 54 в процесі сертифікації. Покривається професійною "
                "відповідальністю проєктувальника; в експертизі вимагає окремого "
                "обґрунтування у пояснювальній записці."
            ),
        )
    elif cert.status == CertificationStatus.PARTIAL:
        return JurisdictionResult(
            jurisdiction=Jurisdiction.UA,
            status="warning",
            reasoning=(
                "Часткова ДСТУ EN 54-сертифікація. Перевірити, чи конкретні "
                "обрані SKU мають дійсний сертифікат."
            ),
        )
    else:  # NONE
        return JurisdictionResult(
            jurisdiction=Jurisdiction.UA,
            status="fail",
            reasoning="Відсутня ДСТУ EN 54-сертифікація. Не може бути застосована в UA-проєктах.",
        )


def check_uk_jurisdiction(manufacturer: Manufacturer) -> JurisdictionResult:
    """
    UK: BS 5839 / LPCB сертифікація АБО EN 54+CE з прийнятністю в UK.
    
    EU-виробники (Cofem, Bosch, Siemens, Schrack тощо) зазвичай проходять
    через міжнародну гармонізацію EN 54 → BS EN 54.
    UA-виробники зазвичай НЕ проходять — це ключовий розрив у дуальних
    сценаріях.
    """
    cert = manufacturer.certifications.UK_BS_LPCB
    
    if cert.status == CertificationStatus.FULL:
        return JurisdictionResult(
            jurisdiction=Jurisdiction.UK,
            status="pass",
            reasoning="LPCB / BS 5839 сертифікація. Прийнятно для UK-страхових ринків.",
        )
    elif cert.status == CertificationStatus.PARTIAL:
        return JurisdictionResult(
            jurisdiction=Jurisdiction.UK,
            status="warning",
            reasoning="Часткова UK-сертифікація. Перевірити по конкретних моделях.",
        )
    elif cert.status == CertificationStatus.IN_PROCESS:
        return JurisdictionResult(
            jurisdiction=Jurisdiction.UK,
            status="warning",
            reasoning="UK-сертифікація в процесі.",
        )
    else:
        return JurisdictionResult(
            jurisdiction=Jurisdiction.UK,
            status="fail",
            reasoning=(
                "Відсутня BS 5839 / LPCB сертифікація. Не проходить вимоги "
                "британських страхових компаній."
            ),
        )


def check_eu_jurisdiction(manufacturer: Manufacturer) -> JurisdictionResult:
    """
    EU: EN 54 + CE marking — стандартне для європейських проєктів.
    """
    cert = manufacturer.certifications.EU_EN54
    
    if cert.status == CertificationStatus.FULL:
        parts = ", ".join(cert.certified_parts) if cert.certified_parts else ""
        body = f" ({cert.certification_body})" if cert.certification_body else ""
        return JurisdictionResult(
            jurisdiction=Jurisdiction.EU,
            status="pass",
            reasoning=f"Повна EN 54{body}. Частини: {parts}.".strip(),
        )
    elif cert.status == CertificationStatus.PARTIAL:
        return JurisdictionResult(
            jurisdiction=Jurisdiction.EU,
            status="warning",
            reasoning="Часткова EN 54. Перевірити список сертифікованих SKU.",
        )
    else:
        return JurisdictionResult(
            jurisdiction=Jurisdiction.EU,
            status="fail",
            reasoning="Відсутня EN 54-сертифікація. Не може застосовуватись у EU-проєктах.",
        )


def check_us_jurisdiction(manufacturer: Manufacturer) -> JurisdictionResult:
    """
    US: UL 864 / FM Approval — складна юрисдикція, мало виробників проходять
    одночасно з EU-лінійкою.
    """
    cert = manufacturer.certifications.US_UL_FM
    
    if cert.status == CertificationStatus.FULL:
        return JurisdictionResult(
            jurisdiction=Jurisdiction.US,
            status="pass",
            reasoning="UL 864 / FM Approval. Прийнятно для US-проєктів.",
        )
    elif cert.status == CertificationStatus.PARTIAL:
        return JurisdictionResult(
            jurisdiction=Jurisdiction.US,
            status="warning",
            reasoning=(
                "Часткова US-сертифікація. Зазвичай для US — окрема лінійка обладнання, "
                "відрізняється від EU/UA SKU. Уточнити в дистриб'ютора."
            ),
        )
    else:
        return JurisdictionResult(
            jurisdiction=Jurisdiction.US,
            status="fail",
            reasoning="Відсутня UL/FM-сертифікація. Не проходить вимоги США.",
        )


# ═══════════════════════════════════════════════════════════════════
# ГОЛОВНА ФУНКЦІЯ КРОКУ 3
# ═══════════════════════════════════════════════════════════════════


JURISDICTION_CHECKERS = {
    Jurisdiction.UA: check_ua_jurisdiction,
    Jurisdiction.UK: check_uk_jurisdiction,
    Jurisdiction.EU: check_eu_jurisdiction,
    Jurisdiction.US: check_us_jurisdiction,
}


def check_compliance(
    state: ObjectState, manufacturer: Manufacturer
) -> ComplianceResult:
    """
    Перевірити compliance виробника для заданого набору активних юрисдикцій.
    
    Правило об'єднання статусів:
    - Будь-який FAIL → overall = FAIL (виключається з comparison)
    - Інакше будь-який WARNING → overall = WARNING (показуємо з примітками)
    - Усі PASS → overall = PASS
    """
    results: list[JurisdictionResult] = []
    
    for jur in state.pre_object.jurisdictions:
        checker = JURISDICTION_CHECKERS[jur]
        results.append(checker(manufacturer))
    
    # Об'єднання статусів
    statuses = {r.status for r in results}
    
    if "fail" in statuses:
        overall = "fail"
    elif "warning" in statuses:
        overall = "warning"
    else:
        overall = "pass"
    
    # Підсумкове повідомлення
    if overall == "pass":
        active_str = ", ".join(j.value for j in state.pre_object.jurisdictions)
        message = f"Повністю відповідає активним юрисдикціям: {active_str}."
    elif overall == "warning":
        warnings = [r for r in results if r.status == "warning"]
        message = (
            f"Проходить з застереженнями ({len(warnings)} нюанс(ів)). "
            "Деталі — у by_jurisdiction нижче."
        )
    else:
        fails = [r.jurisdiction.value for r in results if r.status == "fail"]
        message = (
            f"Не проходить юрисдикцію(ї): {', '.join(fails)}. "
            "Виключено з comparison-set."
        )
    
    return ComplianceResult(
        manufacturer_id=manufacturer.manufacturer_id,
        overall_status=overall,
        by_jurisdiction=results,
        summary_message=message,
    )
