"""
Lab 11 — Optional enrichment: Human-in-the-Loop Design
  (Không chấm — tham khảo. Tóm tắt nộp do scripts/grade.py tự sinh,
   không viết report/*.md tay.)
  - Confidence Router
  - 3 HITL decision points
"""
from dataclasses import dataclass


# ============================================================
# Optional enrichment: ConfidenceRouter (không chấm)
#
# Route agent responses based on confidence scores:
#   - HIGH (>= 0.9): Auto-send to user
#   - MEDIUM (0.7 - 0.9): Queue for human review
#   - LOW (< 0.7): Escalate to human immediately
#
# Special case: if the action is HIGH_RISK (e.g., money transfer,
# account deletion), ALWAYS escalate regardless of confidence.
#
# Implement the route() method.
# ============================================================

HIGH_RISK_ACTIONS = [
    "transfer_money",
    "close_account",
    "change_password",
    "delete_data",
    "update_personal_info",
]


@dataclass
class RoutingDecision:
    """Result of the confidence router."""
    action: str          # "auto_send", "queue_review", "escalate"
    confidence: float
    reason: str
    priority: str        # "low", "normal", "high"
    requires_human: bool


class ConfidenceRouter:
    """Route agent responses based on confidence and risk level.

    Thresholds:
        HIGH:   confidence >= 0.9 -> auto-send
        MEDIUM: 0.7 <= confidence < 0.9 -> queue for review
        LOW:    confidence < 0.7 -> escalate to human

    High-risk actions always escalate regardless of confidence.
    """

    HIGH_THRESHOLD = 0.9
    MEDIUM_THRESHOLD = 0.7

    def route(self, response: str, confidence: float,
              action_type: str = "general") -> RoutingDecision:
        """Route a response based on confidence score and action type.

        Args:
            response: The agent's response text
            confidence: Confidence score between 0.0 and 1.0
            action_type: Type of action (e.g., "general", "transfer_money")

        Returns:
            RoutingDecision with routing action and metadata
        """
        # Optional: Implement routing logic
        #
        # 1. Check if action_type is in HIGH_RISK_ACTIONS
        #    -> If yes: always escalate (action="escalate", priority="high",
        #       requires_human=True, reason="High-risk action: {action_type}")
        #
        # 2. Check confidence thresholds:
        #    - confidence >= 0.9:
        #      action="auto_send", priority="low",
        #      requires_human=False, reason="High confidence"
        #
        #    - 0.7 <= confidence < 0.9:
        #      action="queue_review", priority="normal",
        #      requires_human=True, reason="Medium confidence — needs review"
        #
        #    - confidence < 0.7:
        #      action="escalate", priority="high",
        #      requires_human=True, reason="Low confidence — escalating"

        if action_type in HIGH_RISK_ACTIONS:
            return RoutingDecision(
                action="escalate",
                confidence=confidence,
                reason=f"High-risk action: {action_type}",
                priority="high",
                requires_human=True,
            )

        if confidence >= self.HIGH_THRESHOLD:
            return RoutingDecision(
                action="auto_send",
                confidence=confidence,
                reason="High confidence",
                priority="low",
                requires_human=False,
            )

        if confidence >= self.MEDIUM_THRESHOLD:
            return RoutingDecision(
                action="queue_review",
                confidence=confidence,
                reason="Medium confidence — needs review",
                priority="normal",
                requires_human=True,
            )

        return RoutingDecision(
            action="escalate",
            confidence=confidence,
            reason="Low confidence — escalating",
            priority="high",
            requires_human=True,
        )


# ============================================================
# Optional enrichment: 3 HITL decision points (không chấm)
# ============================================================

hitl_decision_points = [
    {
        "id": 1,
        "name": "High-Value Interbank Wire Transfer Approval",
        "trigger": "Action is 'transfer_money' or proposed transfer amount exceeds 50,000,000 VND or targets an unverified external beneficiary.",
        "hitl_model": "human-in-the-loop",
        "context_needed": "Customer KYC status, source & destination account numbers, transfer amount, 30-day transaction velocity, and untrusted input provenance (whether initiated by user or parsed from email/RAG).",
        "example": "A customer asks the assistant to execute a 100,000,000 VND wire transfer to a first-time external recipient account.",
        "approval_path": "Approve: issue signed approval_id (HITL-XXXXXXXX) and release to https://api.vinbank.example/v1/transfers. Reject: cancel transaction and notify customer. Timeout (15m): auto-cancel fail-closed.",
        "audit_fields": "correlation_id, user_id, action='transfer_money', destination, payload_diff (before/after balance & beneficiary), reviewer_id, approval_id, decision_timestamp.",
    },
    {
        "id": 2,
        "name": "Account Closure & Permanent Data Deletion",
        "trigger": "Action is 'close_account' or 'delete_data', which permanently terminates banking services or purges customer records.",
        "hitl_model": "human-in-the-loop",
        "context_needed": "Account balance, pending settlements/loans, active credit cards, customer identity verification status, and full chat transcript.",
        "example": "Customer requests immediate closure of their primary savings and current account along with GDPR/PDPD personal data deletion.",
        "approval_path": "Approve: compliance officer verifies zero outstanding debt, logs HITL approval token, and schedules closure. Reject: hold account open and explain pending obligations. Timeout (24h): escalate to branch manager.",
        "audit_fields": "correlation_id, user_id, action='close_account', account_state_diff, outstanding_liabilities_check, reviewer_id, approval_id, decision_reason.",
    },
    {
        "id": 3,
        "name": "Ambiguous Policy / Low-Confidence Financial Advice & Credential Update",
        "trigger": "Action is 'change_password' / 'update_personal_info' OR model confidence score falls below 0.90 (0.70–0.89 queued for review; <0.70 immediate escalation) or LLM-as-Judge flags potential rate hallucination.",
        "hitl_model": "human-as-tiebreaker",
        "context_needed": "User query, candidate LLM response, ground-truth VinBank rate sheet (4.25% 12m APY), confidence score, and guardrail/judge flags.",
        "example": "Customer asks about a custom pledged-deposit loan rate where the model confidence is 0.65 and the draft response cites an unverified promotional APR.",
        "approval_path": "Approve/Edit: human specialist corrects or approves the response before sending to customer. Reject: replace with standard official rate table and hotline 1900 545 467. Timeout (5m): send safe fallback message and create callback ticket.",
        "audit_fields": "correlation_id, user_id, intent, confidence_score, draft_ vs_approved_response_diff, reviewer_id, decision_outcome.",
    },
]


# ============================================================
# Quick tests
# ============================================================

def test_confidence_router():
    """Test ConfidenceRouter with sample scenarios."""
    router = ConfidenceRouter()

    test_cases = [
        ("Balance inquiry", 0.95, "general"),
        ("Interest rate question", 0.82, "general"),
        ("Ambiguous request", 0.55, "general"),
        ("Transfer $50,000", 0.98, "transfer_money"),
        ("Close my account", 0.91, "close_account"),
    ]

    print("Testing ConfidenceRouter:")
    print("=" * 80)
    print(f"{'Scenario':<25} {'Conf':<6} {'Action Type':<18} {'Decision':<15} {'Priority':<10} {'Human?'}")
    print("-" * 80)

    for scenario, conf, action_type in test_cases:
        decision = router.route(scenario, conf, action_type)
        print(
            f"{scenario:<25} {conf:<6.2f} {action_type:<18} "
            f"{decision.action:<15} {decision.priority:<10} "
            f"{'Yes' if decision.requires_human else 'No'}"
        )

    print("=" * 80)


def test_hitl_points():
    """Display HITL decision points."""
    print("\nHITL Decision Points:")
    print("=" * 60)
    for point in hitl_decision_points:
        print(f"\n  Decision Point #{point['id']}: {point['name']}")
        print(f"    Trigger:  {point['trigger']}")
        print(f"    Model:    {point['hitl_model']}")
        print(f"    Context:  {point['context_needed']}")
        print(f"    Example:  {point['example']}")
    print("\n" + "=" * 60)


if __name__ == "__main__":
    test_confidence_router()
    test_hitl_points()
