"""The agents: one narrow question each (book Sections 5.3.1.2 and 5.5.1).

ADAPT THIS FILE. An agent is an instruction plus the inputs it may see. Keep
each instruction short: small models follow short, directive prompts better
(book Section 5.3.2.6). Give each agent only the inputs it needs.
"""
from dataclasses import dataclass


@dataclass(frozen=True)
class Agent:
    name: str
    instruction: str
    inputs: tuple[str, ...]


AGENTS = (
    Agent("criteria",
          "Extract each requirement of the reference as a criterion. Use the identifier written in "
          "the reference (REQ-1, REQ-2, ...). In evidence, copy the requirement exactly as written. "
          "Leave status unknown. Do not read any artifact. Do not invent requirements.",
          ("reference",)),
    Agent("conformance",
          "For each criterion given, decide whether the artifact satisfies it (supported), contradicts "
          "it (not_met), or whether you cannot tell (unknown). In evidence, quote the exact line of the "
          "artifact between backticks. Report each not_met criterion also as a finding with severity "
          "high. Judge nothing that is not in the criteria. The results of the tools are facts; never "
          "contradict them.",
          ("reference", "artifact", "criteria", "tools")),
)
