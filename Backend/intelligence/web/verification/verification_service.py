"""
Master Grounded Answer Verification Service for J.A.R.V.I.S. I2.2 V10.
"""
import time
import uuid
from typing import Dict, List, Optional, Set, Any

from intelligence.web.verification.models import (
    AnswerVerificationStatus,
    CitationVerificationStatus,
    ClaimVerificationStatus,
    EvidenceItem,
    EvidenceMatchStatus,
    ExtractedClaim,
    VerificationFinding,
    VerificationWebRequest,
    VerificationWebResponse,
    VerifiedClaim,
)
from intelligence.web.verification.claim_extractor import claim_extractor
from intelligence.web.verification.citation_parser import citation_parser
from intelligence.web.verification.citation_validator import citation_validator
from intelligence.web.verification.evidence_matcher import evidence_matcher
from intelligence.web.verification.temporal_verifier import temporal_verifier
from intelligence.web.verification.knowledge_verifier import knowledge_verifier
from intelligence.web.verification.answer_consistency import answer_consistency_checker
from intelligence.web.verification.verification_policy import verification_policy, ServerHardLimits
from intelligence.web.verification.repair_engine import repair_engine
from intelligence.web.verification.response_sanitizer import response_sanitizer
from intelligence.web.verification.verification_context import verification_context_formatter


class WebVerificationService:
    """
    V10 Master Verification Service.
    Acts as a verification gate between generated draft answers and grounded evidence.
    """

    async def verify_answer(
        self, req: VerificationWebRequest
    ) -> VerificationWebResponse:
        start_time = time.time()
        warnings: List[str] = []

        # 1. Sanitize request
        sanitized_req = verification_policy.sanitize_request(req)
        if not sanitized_req.draft_answer:
            return VerificationWebResponse(
                verification_status=AnswerVerificationStatus.NO_GROUNDED_EVIDENCE,
                warnings=["Empty draft answer provided."],
            )

        # 2. Build Evidence Registry with immutable identity fields
        evidence_registry: Dict[str, EvidenceItem] = {}
        url_to_source_map: Dict[str, str] = {}
        numeric_citation_map: Dict[str, str] = {}

        for idx, ev_dict in enumerate(sanitized_req.evidence_context):
            sid = ev_dict.get("source_id") or f"src_{idx+1}"
            eid = ev_dict.get("evidence_id") or f"ev_{idx+1}_{uuid.uuid4().hex[:6]}"
            url = ev_dict.get("canonical_url")
            path = ev_dict.get("source_path") or "prose"
            prov = ev_dict.get("provenance_status") or "VERIFIED"
            text = ev_dict.get("text", str(ev_dict))

            item = EvidenceItem(
                evidence_id=eid,
                source_id=sid,
                canonical_url=url,
                source_path=path,
                provenance_status=prov,
                text=text,
                metadata=ev_dict,
            )
            evidence_registry[sid] = item
            if url:
                url_to_source_map[url] = sid
            numeric_citation_map[str(idx+1)] = sid

        # 3. Claim Extraction
        extracted_claims = claim_extractor.extract_claims(sanitized_req.draft_answer)
        if not extracted_claims:
            return VerificationWebResponse(
                verification_status=AnswerVerificationStatus.VERIFIED,
                sanitized_answer=sanitized_req.draft_answer,
                grounding_status="NONE",
            )

        # Truncate claims to server limit
        if len(extracted_claims) > ServerHardLimits.MAX_CLAIMS_PER_ANSWER:
            extracted_claims = extracted_claims[: ServerHardLimits.MAX_CLAIMS_PER_ANSWER]
            warnings.append("Claim count truncated to MAX_CLAIMS_PER_ANSWER (30).")

        # 4. Internal Consistency Check
        internal_findings = answer_consistency_checker.check_internal_consistency(extracted_claims)

        verified_claims_list: List[VerifiedClaim] = []
        failed_claims_list: List[VerifiedClaim] = []
        all_findings: List[VerificationFinding] = list(internal_findings)
        citation_results: List[Dict[str, Any]] = []

        repair_needed = False

        # 5. Process & Verify Each Claim
        for claim in extracted_claims:
            if verification_policy.check_deadline(start_time):
                warnings.append("Wall-clock verification deadline reached (8.0s).")
                break

            # Parse citations
            parsed_citations = citation_parser.parse_citations(
                claim_text=claim.text,
                evidence_registry=evidence_registry,
                url_to_source_map=url_to_source_map,
                numeric_citation_map=numeric_citation_map,
            )
            claim.citations = parsed_citations
            citation_results.extend([c.to_dict() for c in parsed_citations])

            # Validate citations
            cit_status, cit_findings = citation_validator.validate_citations_for_claim(
                claim=claim, evidence_registry=evidence_registry
            )
            all_findings.extend(cit_findings)

            # Match evidence
            ev_status, ev_ids, s_ids, c_urls = evidence_matcher.match_claim_against_evidence(
                claim=claim, evidence_items=list(evidence_registry.values())
            )

            # Temporal verification
            temp_status, temp_findings = temporal_verifier.verify_temporal_claim(
                claim=claim, evidence_items=list(evidence_registry.values())
            )
            all_findings.extend(temp_findings)

            # Knowledge & direction verification
            know_status, know_findings = knowledge_verifier.verify_knowledge_claim(
                claim=claim, evidence_items=list(evidence_registry.values())
            )
            all_findings.extend(know_findings)

            # Determine overall claim verification status
            if ev_status == EvidenceMatchStatus.NO_SUPPORT_FOUND:
                claim_status = ClaimVerificationStatus.UNSUPPORTED
            elif know_status == ClaimVerificationStatus.CONTRADICTED:
                claim_status = ClaimVerificationStatus.CONTRADICTED
            elif temp_status == ClaimVerificationStatus.STALE:
                claim_status = ClaimVerificationStatus.STALE
            elif cit_status == CitationVerificationStatus.MISMATCHED:
                claim_status = ClaimVerificationStatus.CITATION_MISMATCH
            elif cit_status in (CitationVerificationStatus.INVALID, CitationVerificationStatus.FORGED):
                claim_status = ClaimVerificationStatus.PROVENANCE_INVALID
            elif ev_status in (EvidenceMatchStatus.DIRECTLY_SUPPORTED, EvidenceMatchStatus.SUPPORTED_BY_MULTIPLE_SOURCES):
                claim_status = ClaimVerificationStatus.SUPPORTED
            elif ev_status == EvidenceMatchStatus.PARTIALLY_SUPPORTED:
                claim_status = ClaimVerificationStatus.PARTIALLY_SUPPORTED
            elif ev_status == EvidenceMatchStatus.CONTRADICTED:
                claim_status = ClaimVerificationStatus.CONTRADICTED
            else:
                claim_status = ClaimVerificationStatus.UNSUPPORTED

            v_claim = VerifiedClaim(
                claim=claim,
                verification_status=claim_status,
                citation_status=cit_status,
                evidence_match_status=ev_status,
                evidence_ids=ev_ids,
                source_ids=s_ids,
                canonical_urls=c_urls,
                findings=cit_findings + temp_findings + know_findings,
            )

            if claim_status == ClaimVerificationStatus.SUPPORTED:
                verified_claims_list.append(v_claim)
            else:
                failed_claims_list.append(v_claim)
                repair_needed = True

        # 6. Bounded Single Repair Attempt (if needed and within limits)
        repair_status = "NONE"
        if repair_needed and failed_claims_list:
            repair_status = "REPAIR_ATTEMPTED"
            for fc in failed_claims_list:
                repaired, new_text = repair_engine.attempt_bounded_repair(
                    failed_claim=fc, evidence_registry=evidence_registry
                )
                if repaired and new_text:
                    fc.repaired_text = new_text
                    fc.verification_status = ClaimVerificationStatus.SUPPORTED
                    repair_status = "REPAIRED"
                    # Move to verified list
                    verified_claims_list.append(fc)

        # 7. Response Sanitization
        sanitized_ans = response_sanitizer.sanitize_answer(
            draft_answer=sanitized_req.draft_answer,
            verified_claims=verified_claims_list,
            failed_claims=failed_claims_list,
        )

        # 8. Final-Answer Provenance Verification on sanitized output
        final_provenance_status = "VERIFIED"
        sanitized_claims = claim_extractor.extract_claims(sanitized_ans)
        for sc in sanitized_claims:
            _, sc_findings = citation_validator.validate_citations_for_claim(
                sc, evidence_registry
            )
            if any(f.finding_type == "UNKNOWN_SOURCE_ID" for f in sc_findings):
                final_provenance_status = "PROVENANCE_INVALID"

        # Determine overall answer verification status
        if not failed_claims_list or repair_status == "REPAIRED":
            answer_status = AnswerVerificationStatus.VERIFIED
        elif verified_claims_list and failed_claims_list:
            answer_status = AnswerVerificationStatus.PARTIAL
        elif any(fc.verification_status == ClaimVerificationStatus.CONTRADICTED for fc in failed_claims_list):
            answer_status = AnswerVerificationStatus.CONTRADICTED
        else:
            answer_status = AnswerVerificationStatus.REJECTED

        return VerificationWebResponse(
            verification_status=answer_status,
            verified_claims=verified_claims_list,
            failed_claims=failed_claims_list,
            citation_results=citation_results,
            findings=[f for f in all_findings if f],
            repair_status=repair_status,
            provenance_status=final_provenance_status,
            grounding_status="GROUNDED",
            sanitized_answer=sanitized_ans,
            warnings=warnings,
        )


web_verification_service = WebVerificationService()
