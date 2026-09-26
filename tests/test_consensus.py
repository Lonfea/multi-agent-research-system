from app.models import FactCheckReport, SupervisorDecision


def consensus(fact: FactCheckReport, supervisor: SupervisorDecision, threshold: float) -> bool:
    return (
        fact.verification_score >= threshold
        and supervisor.approved
        and not fact.unsupported_claims
    )


def test_consensus_requires_both_agents():
    fact = FactCheckReport(verification_score=0.95)
    supervisor = SupervisorDecision(approved=True, confidence=0.9)
    assert consensus(fact, supervisor, 0.8)


def test_unsupported_claim_blocks_consensus():
    fact = FactCheckReport(
        verification_score=0.95,
        unsupported_claims=["Claim X"],
    )
    supervisor = SupervisorDecision(approved=True, confidence=0.9)
    assert not consensus(fact, supervisor, 0.8)
