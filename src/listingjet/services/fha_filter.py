import re
from dataclasses import dataclass, field

# BASELINE_FHA_TERMS: hardcoded, version-controlled, legal-reviewed.
# Cannot be deleted by admin action. DB table fha_filter_terms is ADDITIVE only.
BASELINE_FHA_TERMS = [
    r'\b(?:perfect|ideal|great)[\s-]for[\s-](?:families|couples|singles|retirees|young[\s-]professionals)\b',
    r'\bfamily[\s-]friendly\b',
    r'\bno[\s-](?:section[\s-]8|vouchers?|hud)\b',
    r'\bwalk(?:ing)?[\s-]distance[\s-](?:to|from)[\s-](?:church|mosque|synagogue|temple)\b',
    r'\bminutes?[\s-](?:from|to)[\s-](?:church|mosque|synagogue|temple)\b',
    r'\bgreat[\s-](?:schools|neighborhood|area|community)\b',
    r'\bsafe[\s-]neighborhood\b',
    r'\bexclusive[\s-](?:community|neighborhood|area)\b',
]


@dataclass
class FHAResult:
    passed: bool
    violations: list[str] = field(default_factory=list)


def fha_check(content_json: dict) -> FHAResult:
    full_text = " ".join(str(v) for v in content_json.values() if v)
    violations = []
    for pattern in BASELINE_FHA_TERMS:
        match = re.search(pattern, full_text, re.IGNORECASE)
        if match:
            violations.append(match.group(0))
    return FHAResult(passed=len(violations) == 0, violations=violations)
