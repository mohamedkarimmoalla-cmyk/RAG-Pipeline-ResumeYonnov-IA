"""Generic prompt construction for the scientific summary quality Judge."""

import json
from typing import Any, Dict

from app.services.quality.quality_schema import REQUIRED_SECTIONS


SECTION_LABELS = {
    "metadata": "Metadata",
    "main_topic": "Main Topic",
    "problem_statement": "Problem Statement",
    "objectives": "Objectives",
    "methodology": "Methodology",
    "main_results": "Main Results",
    "scientific_contributions": "Scientific Contributions",
    "limitations": "Limitations",
    "future_work": "Future Work",
    "keywords": "Keywords",
    "executive_summary": "Executive Summary",
    "key_takeaways": "Key Takeaways",
}


def build_judge_prompt(
    source: Dict[str, Any],
    summary: Dict[str, Any],
) -> str:
    """Build a generic source-vs-summary quality evaluation prompt."""

    source_json = json.dumps(
        source,
        ensure_ascii=False,
        indent=2,
    )
    
    summary_json = json.dumps(
        summary,
        ensure_ascii=False,
        indent=2,
    )

    sections = "\n".join(
        f"- {section}: {SECTION_LABELS[section]}"
        for section in REQUIRED_SECTIONS
    )

    return f"""
You are a scientific summary quality auditor.

Your task is to evaluate a GENERATED SUMMARY against the SOURCE
INFORMATION provided below.

The SOURCE is the authoritative reference.

Do not rewrite the summary.
Do not improve the summary.
Do not use outside knowledge.
Do not assume that a plausible statement is correct.

Your task is to determine whether the generated summary faithfully
represents the information available in the source.

============================================================
SOURCE
============================================================

{source_json}

The SOURCE above is the complete authoritative source.

For synthesized sections, search ALL source sections above.
Do not require matching section names.

============================================================
GENERATED SUMMARY
============================================================

{summary_json}
============================================================
SPECIAL RULE — SYNTHESIZED SECTIONS
============================================================

The following sections are synthesized sections:

- executive_summary
- key_takeaways

Their source_availability MUST be determined from the
evidence supporting their claims in the COMPLETE SOURCE.

Do NOT require the source to contain a section with the
same name.

If the claims are sufficiently supported by information
anywhere in SOURCE:
    source_availability = AVAILABLE

If only some claims are supported:
    source_availability = PARTIAL

If the source provides no relevant supporting evidence:
    source_availability = NOT_AVAILABLE

Evaluate the generated content, not the presence or absence
of a matching source heading.

Do not mark executive_summary or key_takeaways as
NOT_AVAILABLE merely because those headings do not exist
in SOURCE.

============================================================
SECTIONS TO EVALUATE
============================================================

{sections}

LIMITATIONS

Do not invent limitations.
For the LIMITATIONS section, search the complete SOURCE for
explicitly stated:
- limitations
- constraints
- evaluation bounds
- weaknesses
- trade-offs
- restricted coverage
- resource or budget constraints
- acknowledged shortcomings

These may appear in Conclusion, Discussion, Results,
Introduction, or other sections.

If explicit limitation evidence exists anywhere in SOURCE:
source_availability = AVAILABLE or PARTIAL.

If no relevant limitation evidence exists anywhere:
source_availability = NOT_AVAILABLE.

Do not infer a limitation merely because something seems
restrictive.
Do not invent limitations from general knowledge.

A SOURCE FACT IS NOT AUTOMATICALLY A LIMITATION.

For example:
- dataset size
- number of experiments
- hardware configuration
- excluded systems
- benchmark scope
- processing scope

must NOT be classified as a limitation unless the source
explicitly presents it as a limitation, constraint, weakness,
boundary, or trade-off.

Do NOT treat the following as evidence of a limitation:

- absence of a section
- absence of information
- reasonable assumptions
- common limitations of similar studies
- characteristics that merely appear restrictive
- the model's own interpretation
- statements that "could be" limitations
- statements that are merely implied

Unsupported limitation claims must be classified as
UNSUPPORTED or FABRICATED.

Only include them in critical_errors when they are materially
important and clearly unsupported or fabricated.
============================================================
SOURCE AVAILABILITY
============================================================
Availability is semantic, not heading-based.

For every section, inspect the COMPLETE SOURCE before deciding
AVAILABLE, PARTIAL, or NOT_AVAILABLE.

Do not rely only on a source field or heading with the same name
as the summary section.

Relevant evidence may appear:
- under another section
- across multiple source sections
- in metadata
- in the abstract
- in the introduction
- in methodology
- in results
- in discussion
- in conclusion
- in future work
- in nested source fields
- elsewhere in the document content

If relevant evidence exists anywhere in the complete SOURCE:
- use AVAILABLE when the section is sufficiently supported
- use PARTIAL when only some relevant evidence is available
- use NOT_AVAILABLE only when the complete SOURCE contains no
  relevant evidence for that section

A missing heading does NOT mean the information is unavailable.

An empty or missing normalized source field does NOT mean the
information is unavailable.

Do not classify a section as NOT_AVAILABLE until the complete
SOURCE has been checked.

Do not use outside knowledge to determine source availability.
------------------------------------------------------------
SOURCE SECTION SEMANTIC MAPPING

Use the following mappings as guidance, not as exclusive rules:

- main_topic:
  Title, Abstract, Introduction, Results, Applications

- problem_statement:
  Introduction, Abstract, discussion of challenges or limitations

- objectives:
  Abstract, Introduction, methodology, evaluation goals

- methodology:
  Design and Architecture, Pipelines, AI Models,
  Benchmark Dataset, System Configurations,
  Benchmarking Methodology, Performance

- main_results:
  Results, Performance, Runtime Characteristics,
  Profiling, Comparisons, Benchmarks

- scientific_contributions:
  Abstract, Introduction, Architecture, Applications,
  Ecosystem, Future Work and Contributions

- limitations:
  Explicit limitations, constraints, weaknesses,
   or current trade-offs affecting the work

- future_work:
  Future Work and Contributions, roadmap, planned models,
  planned evaluations, proposed extensions, or explicitly
  stated areas for future improvement

These mappings are semantic guidance only.
Always verify the actual claim against the source text.

2. IDENTIFY SOURCE EVIDENCE.

For each section, identify the important facts, claims, findings,
methods, numbers, entities, or statements present in the source.

Focus on information that matters to the section.

------------------------------------------------------------

3. IDENTIFY SUMMARY CLAIMS.

Identify the important claims made by the generated summary.

Do not judge only the wording.

Judge the underlying factual claims.

------------------------------------------------------------

4. COMPARE SOURCE AND SUMMARY.

Classify important summary claims as:

SUPPORTED
PARTIALLY_SUPPORTED
UNSUPPORTED
CONTRADICTED

SUPPORTED:
The source supports the claim.

PARTIALLY_SUPPORTED:
The source supports part of the claim but not all of it.

UNSUPPORTED:
The claim cannot be supported by the provided source.

CONTRADICTED:
The claim conflicts with information in the source.

------------------------------------------------------------

5. CHECK SECTION FIDELITY.

Determine whether information is placed in the correct section.

For example:

Methodology should represent methods, procedures, datasets,
models, configurations, or experimental setup.

Main Results should represent findings, measurements,
comparisons, benchmarks, or observed outcomes.

Scientific Contributions should represent actual contributions
presented by the work.

Future Work should represent planned or proposed future work.

Do not give a high fidelity score merely because information is
generally related to the paper.

------------------------------------------------------------

6. CHECK FACTUAL ACCURACY.

Compare factual claims directly with the source.

Check dynamically for discrepancies involving:

- people
- organizations
- technologies
- models
- hardware
- software
- datasets
- methods
- dates
- configurations
- findings
- conclusions
- claims

Do not assume a claim is correct because it sounds reasonable.

Actively look for contradictions.

------------------------------------------------------------

7. CHECK NUMERICAL ACCURACY.

Check every important numerical claim against the source.

Verify:

ENTITY
+
VALUE
+
METRIC
+
UNIT
+
CONFIGURATION

Do not only check whether the same number appears in the source.

The number must be associated with the correct entity, metric,
unit, and configuration.

Detect dynamically:

- changed values
- wrong units
- changed percentages
- changed counts
- wrong dates
- wrong measurements
- wrong benchmark values
- wrong attribution

------------------------------------------------------------

8. CHECK CONTENT COVERAGE.

Determine whether the summary preserves the important information
available in the source.

Do not require every minor detail.

Do not penalize concise summaries merely because they are short.

Focus on important information.

------------------------------------------------------------

9. CHECK METADATA.

Compare source metadata with summary metadata.

Evaluate the fields that are actually available, such as:

- title
- authors
- year
- source
- DOI
- page count
- other provided metadata

If a field is genuinely unavailable in the source, reporting it as
unavailable is correct.

If the source contains the field but the summary loses or changes it,
report the problem.

------------------------------------------------------------

10. CHECK KEYWORDS.

Evaluate the summary keywords against the source information.

If an authoritative keyword list is provided by the source data,
treat it as authoritative.

Check:

- relevance
- representativeness
- specificity
- consistency
- missing important keywords
- invented or unrelated keywords


------------------------------------------------------------

11. CHECK MISSING INFORMATION HANDLING.

Correctly representing unavailable information is good.

Penalize:

- fabricated information
- unsupported claims
- invented metadata
- invented results
- invented limitations
- invented future work
- presenting inference as explicit source information

------------------------------------------------------------

12. CHECK CONTRIBUTIONS AND FUTURE WORK.

Do not confuse existing contributions with planned work.

If planned or proposed work appears as an existing contribution,
reduce fidelity and report the problem.


14. CHECK READABILITY.

Evaluate:

- clarity
- coherence
- organization
- grammatical quality
- understandability

Readability is independent from factual correctness.

A readable statement can still be factually wrong.

------------------------------------------------------------

15. CHECK NOISE.

Detect harmful generated noise such as:

- corrupted text
- broken words
- duplicated phrases
- random symbols
- OCR artifacts
- irrelevant fragments
- repeated headers
- malformed text
- meaningless content

Noise score:

10 = no meaningful noise
8-9 = very minor noise
6-7 = noticeable but limited noise
4-5 = significant noise
2-3 = severe noise
0-1 = extremely corrupted

A clean section should receive a high noise score.
============================================================
SCORING
============================================================
For every section provide:

source_availability
score
content_coverage
fidelity
readability
noise
issues

All scores must be integers from 0 to 10.

Score meaning:

10 = excellent
8-9 = very good
6-7 = acceptable with noticeable issues
4-5 = significant problems
2-3 = major problems
0-1 = fundamentally incorrect, unsupported, or unusable

CLAIM CLASSIFICATION

For every potentially problematic factual claim, classify it as:

SUPPORTED:
Directly supported by the source.

PARAPHRASED:
Different wording but the same source-supported meaning.

SYNTHESIZED:
Combines multiple source-supported facts without introducing
new factual information.

UNSUPPORTED:
The source does not provide sufficient evidence.

CONTRADICTED:
The source explicitly conflicts with the claim.

FABRICATED:
The claim introduces factual information with no reasonable basis
in the complete source.

Only CONTRADICTED and clearly FABRICATED factual claims may be
included in critical_errors.

SUPPORTED, PARAPHRASED, and SYNTHESIZED claims must never be
included in critical_errors.

UNSUPPORTED alone is not automatically a critical error.
============================================================
GLOBAL CHECKS
============================================================

Provide these global scores:

metadata_accuracy
keyword_quality
numerical_accuracy
factual_accuracy
missing_information_handling

Each must be an integer from 0 to 10.


Do not infer a contradiction from wording, scope, compression,
section placement, or summarization style alone.

When evaluating a synthesized summary section, trace each factual
component of the claim back to the complete source. A claim does
not become incorrect merely because its supporting information
appears in another source section.

If there is insufficient evidence to establish a contradiction,
do not report a critical error.

============================================================
SCORING INDEPENDENCE RULE
============================================================

SOURCE AVAILABILITY AND QUALITY SCORE ARE INDEPENDENT.

AVAILABLE does NOT mean that the generated section deserves
a high score.

Evaluate the generated section itself.

A section may be AVAILABLE but still receive a low or medium
score if the generated summary:

- omits important source information
- contains unsupported claims
- contains factual errors
- is incomplete
- is truncated
- ends mid-sentence or mid-claim
- contains an empty value when relevant source information exists

Do not assign 9 or 10 merely because the source contains
information for the section.

CONTENT_COVERAGE must reflect how much relevant source
information is actually represented in the generated section.

FIDELITY must reflect whether the generated claims accurately
represent the source.

READABILITY must reflect whether the generated section is
complete, coherent, and readable.

If a section is visibly truncated or incomplete, do not give
that section a score of 9 or 10.
============================================================
TRUNCATION AND EMPTY-FIELD CHECK
============================================================

Before assigning the section score, check whether the generated
section is complete.

If the generated section:
- ends in the middle of a sentence,
- ends in the middle of a bullet,
- contains an obviously incomplete phrase,
- contains a placeholder,
- or is empty despite relevant source evidence,

then penalize the appropriate dimensions.

An incomplete section MUST NOT receive:
- content_coverage >= 9
- fidelity >= 9
- readability >= 9

unless there is clear evidence that the incompleteness itself
is faithful to the source.

============================================================
CRITICAL ERRORS
============================================================

Only report a critical error when the source clearly supports
that the summary contains a serious:

- factual contradiction
- numerical contradiction
- fabricated information
- wrong attribution
- fabricated metadata
- invented limitation
- invented future work
- other severe grounding error

Before reporting a critical error, verify the COMPLETE SOURCE.

Do NOT report a critical error because:
- information is summarized
- wording differs
- information appears in another source section
- the summary is shorter
- a claim is merely synthesized
- a claim is only unsupported but not materially important

An UNSUPPORTED claim is NOT automatically a critical error.

A claim becomes a critical error only when it is materially important
and clearly unsupported, fabricated, or contradicted by the source.

For every critical error, explain:

1. What the source says.
2. What the summary says.
3. Why they conflict or why the claim is materially unsupported.

If there are no genuine critical errors:
"critical_errors": []
ABSENCE OF SOURCE INFORMATION

When a section is not available in the source, distinguish
between a factual claim and a statement about source absence.

For example:

"The paper has no limitations."

is a factual claim and should be penalized if unsupported.

But:

"No explicit limitations were identified in the source."

correctly reports that the source does not provide this
information and should NOT be treated as hallucination.

ABSENCE IS NOT AN ERROR

If the source genuinely does not provide information for a section:

- source_availability may be NOT_AVAILABLE.
- Do not penalize the summary merely because the information is absent.
- If the summary explicitly and correctly reports that the information
  is unavailable, this is correct behavior.
- If the summary invents factual content for that section, penalize it.
- Never convert "not found in source" into "the paper states that it
  does not exist."
============================================================
OVERALL SCORE
============================================================

The overall_score is calculated deterministically by the application.

Do NOT calculate or estimate overall_score.

Return the "overall_score" field as 0 in the JSON response.
The application will replace this value with the calculated score.

Focus on producing accurate:

- section scores
- global checks
- critical errors
- recommendations
- decision

IMPORTANT:

Critical factual or numerical contradictions must have a strong
negative impact on the overall assessment.

If the summary contains one or more serious factual contradictions,
the decision MUST NOT be PASS.

If there are multiple serious factual contradictions or widespread
fabricated information, the decision should normally be FAIL.
============================================================
RECOMMENDATIONS
============================================================

Provide concise recommendations for improving the summary.

Recommendations must be based on detected problems.

If no meaningful improvement is necessary, return an empty list.

============================================================
DECISION CONSISTENCY RULE
============================================================

The final decision MUST be consistent with the evaluation.

PASS:
No critical errors and no serious/widespread factual problems.


REVIEW:
Noticeable quality issues but no severe factual problems.

FAIL:
One or more genuine critical errors or severe/widespread
factual/numerical misinformation.

The decision must agree with critical_errors.

If "critical_errors" is empty and the summary is otherwise
supported by the source, the decision MUST be "PASS".

Do NOT return "FAIL" when:
- "critical_errors" is empty;
- section scores are high;
- global checks are high;
- and the summary is supported by the source.

The following fields MUST be mutually consistent:

- "overall_score"
- "decision"
- "critical_errors"

Never produce:

- "critical_errors": [] with "decision": "FAIL" unless there
  is another explicitly documented severe failure condition.

- "overall_score": 0 when the evaluated sections and global
  checks indicate a successful evaluation.

- "decision": "PASS" when genuine critical errors are present.

The decision must be based on the evaluation results.
Do not override the evaluation with a default FAIL or PASS.
============================================================
REQUIRED OUTPUT FIELDS
============================================================

The top-level JSON object MUST contain exactly these fields:

- overall_score
- decision
- sections
- global_checks
- critical_errors
- recommendations

"recommendations" is mandatory even when there are no
recommendations.

If there are no recommendations, return:

"recommendations": []

Never omit the recommendations field.

============================================================
OUTPUT REQUIREMENTS
============================================================

Return ONLY valid JSON.

Do not return Markdown.

Do not return explanations outside the JSON.

There must be exactly 12 section objects:

metadata
main_topic
problem_statement
objectives
methodology
main_results
scientific_contributions
limitations
future_work
keywords
executive_summary
key_takeaways

Every section MUST contain:

source_availability
score
content_coverage
fidelity
readability
noise
issues

source_availability MUST be exactly:

AVAILABLE
PARTIAL
NOT_AVAILABLE

All scores MUST be integers from 0 to 10.

Use this exact JSON structure:

{{
  "overall_score": 0,
  "decision": "PASS",

  "sections": {{

    "metadata": {{
      "source_availability": "AVAILABLE",
      "score": 0,
      "content_coverage": 0,
      "fidelity": 0,
      "readability": 0,
      "noise": 10,
      "issues": []
    }},

    "main_topic": {{
      "source_availability": "AVAILABLE",
      "score": 0,
      "content_coverage": 0,
      "fidelity": 0,
      "readability": 0,
      "noise": 10,
      "issues": []
    }},

    "problem_statement": {{
      "source_availability": "AVAILABLE",
      "score": 0,
      "content_coverage": 0,
      "fidelity": 0,
      "readability": 0,
      "noise": 10,
      "issues": []
    }},

    "objectives": {{
      "source_availability": "AVAILABLE",
      "score": 0,
      "content_coverage": 0,
      "fidelity": 0,
      "readability": 0,
      "noise": 10,
      "issues": []
    }},

    "methodology": {{
      "source_availability": "AVAILABLE",
      "score": 0,
      "content_coverage": 0,
      "fidelity": 0,
      "readability": 0,
      "noise": 10,
      "issues": []
    }},

    "main_results": {{
      "source_availability": "AVAILABLE",
      "score": 0,
      "content_coverage": 0,
      "fidelity": 0,
      "readability": 0,
      "noise": 10,
      "issues": []
    }},

    "scientific_contributions": {{
      "source_availability": "AVAILABLE",
      "score": 0,
      "content_coverage": 0,
      "fidelity": 0,
      "readability": 0,
      "noise": 10,
      "issues": []
    }},

    "limitations": {{
      "source_availability": "AVAILABLE",
      "score": 0,
      "content_coverage": 0,
      "fidelity": 0,
      "readability": 0,
      "noise": 10,
      "issues": []
    }},

    "future_work": {{
      "source_availability": "AVAILABLE",
      "score": 0,
      "content_coverage": 0,
      "fidelity": 0,
      "readability": 0,
      "noise": 10,
      "issues": []
    }},

    "keywords": {{
      "source_availability": "AVAILABLE",
      "score": 0,
      "content_coverage": 0,
      "fidelity": 0,
      "readability": 0,
      "noise": 10,
      "issues": []
    }},

    "executive_summary": {{
      "source_availability": "AVAILABLE",
      "score": 0,
      "content_coverage": 0,
      "fidelity": 0,
      "readability": 0,
      "noise": 10,
      "issues": []
    }},

    "key_takeaways": {{
      "source_availability": "AVAILABLE",
      "score": 0,
      "content_coverage": 0,
      "fidelity": 0,
      "readability": 0,
      "noise": 10,
      "issues": []
    }}

  }},

  "global_checks": {{
    "metadata_accuracy": 0,
    "keyword_quality": 0,
    "numerical_accuracy": 0,
    "factual_accuracy": 0,
    "missing_information_handling": 0
  }},

  "critical_errors": [],

  "recommendations": []
}}
""".strip()