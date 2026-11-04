# T020-PS-119: TenderLens --- Tender Bid Evaluation Engine

**Project:** TenderLens --- Tender Bid Evaluation Engine\
**Repository:** `Likhith206/T020-PS-119`\
**Team:** T020\
**Primary language:** Python\
**Project type:** Tender evaluation and decision-support system

> **Document note:** This document describes the agreed project scope
> and proposed implementation. Exact tender-specific thresholds, scoring
> weights, preference percentages, statutory conditions, and approval
> rules must come from the official assignment brief or tender document.
> They are not invented or hard-coded here.

## 1. What we are building

We are building **TenderLens**, a Python-based tender bid evaluation
engine that helps a procurement team evaluate bids in a consistent,
structured, and traceable way.

The system supports the main stages of a tender:

1.  Create and configure a tender.
2.  Register bidders and capture their bid details.
3.  Check bidder eligibility and Earnest Money Deposit (EMD) compliance.
4.  Evaluate technical bids against the tender's stated requirements.
5.  Evaluate financial bids of bidders who qualify for the financial
    stage.
6.  Identify the lowest evaluated responsive bidder (L1), where
    applicable.
7.  Apply eligible Micro and Small Enterprises (MSE) and local-content
    preferences according to configured tender rules.
8.  Record the evaluation outcome, award decision, and supporting
    reports.

TenderLens supports the evaluation process; it does not replace the
authorised procurement committee. Final decisions remain with
responsible officials.

We will keep the implementation modular and understandable: - small
Python functions with clear responsibilities; - separate modules for
tender lifecycle, validation, evaluation, ranking, and reporting; -
explicit evaluation criteria and configurable thresholds; - structured
records for tenders, bidders, documents, scores, and decisions; - clear
error messages for missing or invalid information; - an audit trail for
important actions and evaluation changes; - automated tests for
evaluation rules.

## 2. What our project will do

### Main features

1.  **Tender creation and configuration:** Create a tender with a unique
    ID, title, description, important dates, status, eligibility
    conditions, EMD requirements, technical criteria, and financial
    evaluation method.
2.  **Bidder registration:** Register bidders against a tender and store
    identity/reference information, bid submission details, and
    submitted-document references.
3.  **Eligibility verification:** Check mandatory eligibility conditions
    against bidder information and evidence. Record each condition as
    pending, passed, failed, or requiring manual review, with a reason.
4.  **EMD verification:** Record required and submitted EMD amounts,
    payment references, and exemption details. Flag missing,
    insufficient, invalid, or unverified information. Apply only
    exemptions configured from official tender conditions.
5.  **Technical evaluation:** Score qualified bids against the tender's
    technical criteria. Record criterion-wise marks, remarks, evidence
    references, and evaluator details. Calculate the technical score and
    qualification result using the configured method.
6.  **Financial evaluation:** Record financial bid values, validate the
    data, apply only permitted adjustments, and calculate a comparable
    evaluated price.
7.  **L1 identification and ranking:** Rank eligible and responsive
    bidders using the applicable evaluated-price method. Handle ties
    using the tender's documented procedure.
8.  **MSE and local-content preferences:** Capture declarations and
    supporting evidence. Apply preference benefits only when the bidder
    and tender satisfy configured conditions. Record the calculation and
    reason.
9.  **Award and reporting:** Record the proposed award outcome and
    justification. Generate bidder-wise summaries, tender-level
    comparison reports, and evaluation history.

### What we are not adding in the first version

-   direct bid submission to a government e-procurement portal;
-   online collection or transfer of EMD payments;
-   automatic verification against external government databases;
-   automatic legal interpretation of procurement rules;
-   digital signature or certificate issuance;
-   automatic award approval without authorised human review.

## 3. Simple system flow

``` text
Tender details and evaluation rules
                 |
                 v
          Tender creation
                 |
                 v
          Bidder registration
                 |
                 v
       Bid information/documents
                 |
                 v
       Eligibility verification
                 |
                 v
           EMD verification
                 |
                 v
          Technical evaluation
                 |
          Qualified bidders
                 |
                 v
          Financial evaluation
                 |
                 v
      Evaluated price and ranking
                 |
                 v
       L1 identification (if applicable)
                 |
                 v
    MSE / local-content preference checks
                 |
                 v
          Award recommendation
                 |
                 v
         Reports and audit history
```

The program will work in this order:

1.  Create or load the tender and evaluation configuration.
2.  Register bidders and capture bid information.
3.  Validate required bidder details and documents.
4.  Perform eligibility and EMD checks.
5.  Evaluate technical bids using configured criteria.
6.  Move only technically qualified bidders to the financial stage, as
    required by the tender.
7.  Calculate evaluated financial values and rank responsive bidders.
8.  Apply applicable preference rules.
9.  Prepare the award recommendation and generate reports.

Each stage will save its outcome for later review. A correction should
be recorded with its reason and history rather than silently overwriting
a previous result.

## 4. Data we need to store

  -----------------------------------------------------------------------
  Record                              Important fields
  ----------------------------------- -----------------------------------
  `Tender`                            `tender_id`, `title`,
                                      `description`, `issuing_authority`,
                                      `publish_date`,
                                      `submission_deadline`, `status`

  `TenderRule`                        `rule_id`, `tender_id`,
                                      `rule_type`, `rule_value`,
                                      `description`, `source_reference`,
                                      `is_mandatory`

  `Bidder`                            `bidder_id`, `name`,
                                      `contact_reference`,
                                      `registration_details`

  `Bid`                               `bid_id`, `tender_id`, `bidder_id`,
                                      `submission_time`, `bid_status`,
                                      `quoted_amount`

  `BidDocument`                       `document_id`, `bid_id`,
                                      `document_type`, `file_reference`,
                                      `verification_status`, `remarks`

  `EligibilityCheck`                  `check_id`, `bid_id`,
                                      `criterion_id`, `status`,
                                      `evidence_reference`, `remarks`,
                                      `checked_by`

  `EMDRecord`                         `emd_id`, `bid_id`,
                                      `required_amount`,
                                      `submitted_amount`,
                                      `payment_reference`,
                                      `exemption_claim`,
                                      `verification_status`

  `TechnicalCriterion`                `criterion_id`, `tender_id`,
                                      `name`, `description`,
                                      `maximum_score`, `weight`,
                                      `mandatory`

  `TechnicalScore`                    `score_id`, `bid_id`,
                                      `criterion_id`, `score`, `remarks`,
                                      `evidence_reference`, `evaluator`

  `FinancialEvaluation`               `evaluation_id`, `bid_id`,
                                      `quoted_amount`, `adjustments`,
                                      `evaluated_amount`, `status`,
                                      `remarks`

  `PreferenceRecord`                  `preference_id`, `bid_id`,
                                      `preference_type`,
                                      `declared_status`,
                                      `verified_status`, `rule_applied`,
                                      `result`

  `Ranking`                           `ranking_id`, `tender_id`,
                                      `bid_id`, `evaluated_amount`,
                                      `rank`, `is_l1`, `basis`

  `AwardDecision`                     `decision_id`, `tender_id`,
                                      `selected_bid_id`,
                                      `decision_status`, `justification`,
                                      `approved_by`, `decision_date`

  `AuditLog`                          `event_id`, `tender_id`, `bid_id`,
                                      `action`, `old_value`, `new_value`,
                                      `reason`, `actor`, `timestamp`
  -----------------------------------------------------------------------

Final field names may be adjusted to match the repository's API contract
and implementation. Sensitive bidder documents should be stored
securely; reports should not expose private document contents.

## 5. Input and output information

### Input information

-   tender details and deadlines;
-   eligibility requirements and supporting evidence;
-   EMD requirement and payment or exemption information;
-   bidder registration and bid submission details;
-   technical criteria, weights, minimum scores, and evaluator marks;
-   quoted financial values and permitted adjustments;
-   MSE declarations and supporting evidence;
-   local-content declarations and supporting evidence;
-   evaluator remarks and approval details.

Input formats and exact field names will follow the agreed API contract
and sample data.

### Output reports

-   `eligibility_report` --- bidder-wise eligibility checks and reasons;
-   `emd_report` --- required/submitted EMD details and verification
    status;
-   `technical_evaluation_report` --- criterion-wise scores and
    qualification result;
-   `financial_comparison_report` --- quoted and evaluated amounts with
    adjustments;
-   `bidder_ranking_report` --- ranking and L1 identification basis;
-   `preference_report` --- MSE/local-content declarations and rule
    application;
-   `award_recommendation_report` --- proposed outcome and
    justification;
-   `audit_report` --- actions, changes, timestamps, and responsible
    users;
-   `errors_report` --- invalid or incomplete records requiring
    correction.

Reports should distinguish verified facts, bidder declarations,
evaluator inputs, and system-calculated results.

## 6. Evaluation rules and safeguards

TenderLens will apply rules configured from the official tender
conditions and assignment specification. Exact values and thresholds
must be entered from the authoritative source.

### TR-01: Tender configuration

Each tender must have its own evaluation configuration. Required dates,
eligibility conditions, EMD requirements, technical criteria, financial
method, and applicable preference rules must be present before
evaluation begins.

### TR-02: Bidder eligibility

Each mandatory eligibility condition must be checked separately. Record
the result as passed, failed, pending, or requiring manual review. A
bidder must not be treated as qualified while a mandatory condition
remains unresolved.

### TR-03: EMD compliance

Compare the required EMD with the recorded submission or valid exemption
information. Retain payment references or exemption evidence and
verification status. Acceptance and exemption rules come from the
tender.

### TR-04: Technical qualification

Record marks criterion by criterion. Calculate the total using the
configured scoring method. Apply mandatory technical conditions and
minimum qualifying scores exactly as specified.

### TR-05: Financial evaluation

Use the financial evaluation method stated in the tender. Preserve the
original quoted amount and separately record permitted adjustments so
the evaluated amount can be explained.

### TR-06: L1 identification

Identify L1 from bidders who are eligible, responsive, and qualified for
financial evaluation, using the tender's stated comparison basis.
Disqualified bids must not be ranked as eligible L1 candidates.

### TR-07: MSE preference

Record MSE status, evidence, verification, and the preference rule
applied. Eligibility, purchase-preference range, price matching, and
other conditions must be configured from the applicable tender or
official policy.

### TR-08: Local-content preference

Record the local-content declaration and supporting evidence. Any
category, minimum percentage, preference, or eligibility condition must
come from the applicable tender or policy.

### TR-09: Award recommendation

Produce an award recommendation based on recorded evaluation outcomes
and applicable preferences. Show the basis and retain authorised
approval separately.

### TR-10: Auditability and corrections

Log important actions such as bidder registration, score entry,
verification, evaluation completion, ranking changes, and award
decisions. Corrections should retain old value, new value, reason,
actor, and timestamp.

### Supporting validation

Validate unique IDs, required fields, valid dates, non-negative monetary
values, references between tenders and bids, duplicate submissions, and
score ranges. These are data-quality checks, not additional tender
eligibility rules.

## 7. How we will perform eligibility and EMD checks

For each bidder, the system will:

1.  Confirm that the bidder is registered against the selected tender.
2.  Check whether required bid information and documents are present.
3.  Load the tender's mandatory eligibility conditions.
4.  Compare bidder information and evidence against each condition.
5.  Record each condition's result and explanation.
6.  Check the required EMD amount and submitted amount or exemption
    claim.
7.  Record payment/exemption references and verification status.
8.  Mark unresolved items for manual review.
9.  Determine the stage outcome according to configured tender rules.

The system must not treat a document as valid merely because a file is
present. Verification status and the responsible verifier should be
recorded.

## 8. How we will perform technical evaluation

For each bidder who reaches the technical stage:

1.  Load the technical criteria configured for the tender.
2.  Confirm that required technical evidence is available.
3.  Record the evaluator's score for each criterion.
4.  Validate that each score is within its allowed range.
5.  Calculate the total or weighted score using the configured formula.
6.  Check mandatory requirements and the qualifying threshold.
7.  Record the qualification result and evaluator remarks.
8.  Preserve criterion-wise scores and evaluation history.

If a score is changed, the change and its reason should be recorded.

## 9. How we will perform financial evaluation and ranking

For each bidder permitted to enter the financial stage:

1.  Read and validate the submitted financial bid.
2.  Preserve the original quoted amount.
3.  Apply only adjustments permitted by the tender's method.
4.  Calculate the evaluated amount.
5.  Check whether the bid is responsive under configured rules.
6.  Rank responsive, qualified bidders using the stated comparison
    basis.
7.  Identify L1 where the rules produce a valid L1 result.
8.  Record ties, exceptions, or manual decisions for review.

The system should show calculation components instead of only a final
amount. Monetary calculations should use decimal arithmetic rather than
binary floating-point arithmetic.

## 10. How we will apply MSE and local-content preferences

Preference checks will be performed after the relevant qualification and
financial evaluation stages, in the order required by the tender.

For each preference:

1.  Read the bidder's declaration.
2.  Check whether supporting evidence is recorded.
3.  Record whether the claim is verified, rejected, or pending.
4.  Load the preference conditions configured for the tender.
5.  Check whether bidder and tender satisfy those conditions.
6.  Calculate any permitted preference treatment.
7.  Record how the treatment affects comparison or award recommendation.
8.  Preserve the original ranking and preference-adjusted outcome.

The software will not assume that every MSE or local-content claimant
automatically receives a preference.

## 11. Invalid data and exception handling

If an input record is incomplete or invalid, the system should report
the issue clearly and prevent an unsupported evaluation result.

Examples of error codes:

-   `UNKNOWN_TENDER`
-   `UNKNOWN_BIDDER`
-   `DUPLICATE_BID`
-   `MISSING_REQUIRED_DOCUMENT`
-   `ELIGIBILITY_PENDING`
-   `EMD_AMOUNT_MISMATCH`
-   `INVALID_TECHNICAL_SCORE`
-   `FINANCIAL_VALUE_INVALID`
-   `PREFERENCE_EVIDENCE_MISSING`
-   `EVALUATION_NOT_COMPLETE`

An error should identify the affected tender or bid, the field or rule
involved, and a useful explanation. Valid records may continue where
possible, but a final recommendation must not be generated when a
required stage is incomplete.

## 12. Testing plan

We will write unit tests for individual checks and calculations, along
with integration tests for a complete tender evaluation workflow.

Important test cases include:

-   a tender cannot be evaluated before mandatory configuration is
    complete;
-   a bidder registered under one tender cannot be evaluated under
    another;
-   a missing mandatory eligibility document is flagged;
-   a bidder who fails a mandatory eligibility condition is not
    advanced;
-   an EMD amount equal to the required amount is handled according to
    the configured rule;
-   an EMD exemption is accepted only when configured conditions and
    evidence are satisfied;
-   technical scores below zero or above the permitted maximum are
    rejected;
-   the technical total matches the configured scoring formula;
-   a bidder who fails the technical qualifying condition is excluded
    from financial ranking;
-   financial adjustments are applied only when permitted;
-   L1 is selected from the correct set of qualified and responsive
    bidders;
-   equal evaluated prices are handled using the configured tie
    procedure;
-   an unverified MSE claim does not receive unsupported preference;
-   local-content preference is applied only when configured conditions
    are satisfied;
-   a score correction creates an audit entry;
-   an award recommendation records its evaluation basis and approval
    status;
-   incomplete evaluation stages prevent finalisation.

Expected values for thresholds and preference tests will come from the
official brief or agreed test fixtures.

## 13. Decisions to confirm from the assignment brief

The following details must be checked against the official problem
statement and sample inputs:

1.  Exact eligibility conditions and required evidence.
2.  EMD amount, accepted payment modes, exemptions, and verification
    rules.
3.  Technical criteria, score ranges, weights, and minimum qualifying
    score.
4.  Financial evaluation formula and permitted adjustments.
5.  L1 identification method and tie resolution.
6.  MSE eligibility and preference conditions.
7.  Local-content categories, thresholds, and preference conditions.
8.  Award approval and documentation requirements.
9.  Required input/output formats and command syntax.
10. Prescribed database, interface, or technology constraints.

Until confirmed, these remain configurable tender rules rather than
hard-coded constants. Project-specific assumptions should be documented
in `DECISION_LOG.md`.

## 14. Team responsibilities

The project work is divided into two main areas.

### Procurement Evaluation Engineer

Responsible for evaluation logic: - eligibility verification; - EMD
checks; - technical scoring and qualification; - financial evaluation; -
MSE and local-content preference checks; - bidder ranking and L1
identification; - tests for evaluation calculations and decision rules.

### Backend Intelligence & Lifecycle Engineer

Responsible for the supporting system: - data models and persistence; -
command-line workflow and application lifecycle; - input validation and
integration; - audit trail and evaluation history; - explanation of
evaluation outcomes; - award workflow, reports, and simulations; -
integration tests and overall system coordination.

Both roles should coordinate through the repository's `API_CONTRACT.md`,
`PROJECT_PLAN.md`, `TASK_BOARD.md`, `TEAM_WORKFLOW.md`, and
`DECISION_LOG.md`.

## 15. Implementation order

1.  Review the official problem statement and record all mandatory
    rules.
2.  Confirm data models and interfaces in `API_CONTRACT.md`.
3.  Set up project structure and tender/bidder records.
4.  Implement tender configuration and input validation.
5.  Implement eligibility and EMD checks.
6.  Implement technical scoring and qualification.
7.  Implement financial evaluation and evaluated-price calculation.
8.  Implement ranking and L1 identification.
9.  Implement MSE and local-content preference handling.
10. Integrate audit history, explanations, award workflow, and reports.
11. Add unit and end-to-end tests using agreed sample data.
12. Review error handling, traceability, and readability.
13. Update the README and prepare the final demonstration.

## 16. Expected outcome

At the end of the project, TenderLens should provide a structured way to
manage tender evaluation from tender creation through award
recommendation. It should make evaluation stages clear, apply configured
rules consistently, explain how results were obtained, and preserve a
record of important actions.

The main value of TenderLens is **transparent and traceable
evaluation**: procurement users should be able to understand why a
bidder passed or failed a stage, how technical and financial results
were calculated, how preferences were considered, and how the final
recommendation was reached.
