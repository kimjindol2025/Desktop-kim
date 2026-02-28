"""
Verdict DSL Parser

Parses Verdict Definition Language rules for the judgment engine
"""

import re
from typing import Dict, List, Any, Optional, Tuple
from .verdict_types import VerdictDSLRule


class VerdictDSLParser:
    """Parser for Verdict Definition Language"""

    def __init__(self):
        self.rules: Dict[str, VerdictDSLRule] = {}

    def parse_rule_text(self, rule_text: str) -> Optional[VerdictDSLRule]:
        """
        Parse a single Verdict DSL rule from text

        Format:
        ```
        rule <rule_id>:
          when: <condition>
          then: <verdict>
          reason: <explanation>
          confidence: <0.0-1.0>
          applies_to: [lang1, lang2, ...]
        ```
        """
        lines = rule_text.strip().split("\n")

        # Extract rule ID
        rule_id = self._extract_rule_id(lines[0])
        if not rule_id:
            return None

        # Parse sections
        sections = self._parse_sections(lines)

        if "when" not in sections or "then" not in sections:
            raise ValueError(f"Rule {rule_id} missing 'when' or 'then' section")

        condition = self._parse_condition(sections["when"])
        action = self._parse_action(sections["then"])
        reason = sections.get("reason", "").strip()
        confidence = float(sections.get("confidence", "0.95"))
        applies_to = self._parse_list(sections.get("applies_to", "[]"))

        return VerdictDSLRule(
            rule_id=rule_id,
            condition=condition,
            action=action,
            reason=reason,
            confidence=confidence,
            applies_to=applies_to,
        )

    def parse_rules_from_file(self, file_path: str) -> Dict[str, VerdictDSLRule]:
        """Parse multiple rules from a file"""
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()

        # Split by rule declarations
        rule_blocks = re.split(r"^rule\s+\w+:", content, flags=re.MULTILINE)

        for block in rule_blocks[1:]:  # Skip first empty split
            try:
                rule = self.parse_rule_text("rule " + block)
                if rule:
                    self.rules[rule.rule_id] = rule
            except Exception as e:
                print(f"Warning: Failed to parse rule: {e}")

        return self.rules

    def _extract_rule_id(self, first_line: str) -> Optional[str]:
        """Extract rule ID from first line"""
        match = re.search(r"rule\s+(\w+):", first_line)
        return match.group(1) if match else None

    def _parse_sections(self, lines: List[str]) -> Dict[str, str]:
        """Parse rule sections (when, then, reason, etc.)"""
        sections = {}
        current_section = None
        current_content = []

        for line in lines[1:]:  # Skip rule definition line
            stripped = line.strip()

            # Check if this is a new section
            if stripped and ":" in stripped and not stripped.startswith("#"):
                section_name = stripped.split(":")[0].strip()
                if section_name in ["when", "then", "reason", "confidence", "applies_to"]:
                    # Save previous section
                    if current_section:
                        sections[current_section] = "\n".join(current_content).strip()

                    current_section = section_name
                    current_content = [stripped.split(":", 1)[1].strip()]
                else:
                    if current_section:
                        current_content.append(stripped)
            elif current_section and stripped:
                current_content.append(stripped)

        # Save last section
        if current_section:
            sections[current_section] = "\n".join(current_content).strip()

        return sections

    def _parse_condition(self, condition_text: str) -> Dict[str, Any]:
        """Parse 'when' condition"""
        condition = {
            "type": "AND",  # Default logical operator
            "clauses": [],
        }

        # Handle basic operators
        if "AND" in condition_text:
            parts = condition_text.split("AND")
            operator = "AND"
        elif "OR" in condition_text:
            parts = condition_text.split("OR")
            operator = "OR"
        else:
            parts = [condition_text]
            operator = "AND"

        condition["type"] = operator

        for part in parts:
            part = part.strip()

            # Parse individual clause
            clause = self._parse_condition_clause(part)
            if clause:
                condition["clauses"].append(clause)

        return condition

    def _parse_condition_clause(self, clause_text: str) -> Optional[Dict[str, Any]]:
        """Parse individual condition clause"""
        clause_text = clause_text.strip()

        # requires_all: [A, B, C]
        if match := re.search(r"requires_all:\s*\[(.*?)\]", clause_text):
            items = [x.strip() for x in match.group(1).split(",")]
            return {"type": "requires_all", "items": items}

        # requires_any: [X, Y, Z]
        if match := re.search(r"requires_any:\s*\[(.*?)\]", clause_text):
            items = [x.strip() for x in match.group(1).split(",")]
            return {"type": "requires_any", "items": items}

        # requires_none: [P, Q]
        if match := re.search(r"requires_none:\s*\[(.*?)\]", clause_text):
            items = [x.strip() for x in match.group(1).split(",")]
            return {"type": "requires_none", "items": items}

        # language_has: "capability"
        if match := re.search(r'language_has:\s*["\']([^"\']+)["\']', clause_text):
            return {"type": "language_has", "capability": match.group(1)}

        # language_lacks: "capability"
        if match := re.search(r'language_lacks:\s*["\']([^"\']+)["\']', clause_text):
            return {"type": "language_lacks", "capability": match.group(1)}

        # <key> = <value>
        if "=" in clause_text and "!=" not in clause_text:
            key, value = clause_text.split("=", 1)
            return {
                "type": "equals",
                "key": key.strip(),
                "value": value.strip().strip('"\''),
            }

        # <key> != <value>
        if "!=" in clause_text:
            key, value = clause_text.split("!=", 1)
            return {
                "type": "not_equals",
                "key": key.strip(),
                "value": value.strip().strip('"\''),
            }

        # <key> > <value>
        if ">" in clause_text and ">=" not in clause_text:
            key, value = clause_text.split(">", 1)
            return {
                "type": "greater_than",
                "key": key.strip(),
                "value": value.strip().strip('"\''),
            }

        # <key> < <value>
        if "<" in clause_text and "<=" not in clause_text:
            key, value = clause_text.split("<", 1)
            return {
                "type": "less_than",
                "key": key.strip(),
                "value": value.strip().strip('"\''),
            }

        return None

    def _parse_action(self, action_text: str) -> Dict[str, Any]:
        """Parse 'then' action (verdict)"""
        action = {}

        # verdict = "..."
        if match := re.search(r'verdict\s*=\s*["\'](\w+)["\']', action_text):
            action["verdict"] = match.group(1)

        # severity = "..."
        if match := re.search(r'severity\s*=\s*["\'](\w+)["\']', action_text):
            action["severity"] = match.group(1)

        # exclude: [...]
        if match := re.search(r"exclude:\s*\[(.*?)\]", action_text):
            items = [x.strip() for x in match.group(1).split(",")]
            action["exclude"] = items

        # recommend: [...]
        if match := re.search(r"recommend:\s*\[(.*?)\]", action_text):
            items = [x.strip() for x in match.group(1).split(",")]
            action["recommend"] = items

        # score_adjust: +10 | -20
        if match := re.search(r"score_adjust:\s*([+-]?\d+)", action_text):
            action["score_adjust"] = int(match.group(1))

        return action

    def _parse_list(self, list_text: str) -> List[str]:
        """Parse list in format [item1, item2, ...]"""
        if not list_text or list_text == "[]":
            return []

        # Remove brackets
        list_text = list_text.strip().strip("[]").strip()

        if not list_text:
            return []

        # Split and clean
        items = [item.strip().strip('"\'') for item in list_text.split(",")]
        return items

    def evaluate_condition(
        self,
        condition: Dict[str, Any],
        requirements: Dict[str, Any],
        language_capabilities: List[str],
    ) -> bool:
        """
        Evaluate condition against requirements and language capabilities

        Returns True if condition is satisfied
        """
        if not condition.get("clauses"):
            return True

        operator = condition.get("type", "AND")
        results = []

        for clause in condition["clauses"]:
            clause_result = self._evaluate_clause(
                clause, requirements, language_capabilities
            )
            results.append(clause_result)

        if operator == "AND":
            return all(results)
        elif operator == "OR":
            return any(results)
        else:
            return all(results)

    def _evaluate_clause(
        self,
        clause: Dict[str, Any],
        requirements: Dict[str, Any],
        language_capabilities: List[str],
    ) -> bool:
        """Evaluate individual condition clause"""
        clause_type = clause.get("type")

        if clause_type == "requires_all":
            items = clause.get("items", [])
            return all(req in requirements for req in items)

        elif clause_type == "requires_any":
            items = clause.get("items", [])
            return any(req in requirements for req in items)

        elif clause_type == "requires_none":
            items = clause.get("items", [])
            return not any(req in requirements for req in items)

        elif clause_type == "language_has":
            capability = clause.get("capability")
            return capability in language_capabilities

        elif clause_type == "language_lacks":
            capability = clause.get("capability")
            return capability not in language_capabilities

        elif clause_type == "equals":
            key = clause.get("key")
            value = clause.get("value")
            return requirements.get(key) == value

        elif clause_type == "not_equals":
            key = clause.get("key")
            value = clause.get("value")
            return requirements.get(key) != value

        elif clause_type == "greater_than":
            key = clause.get("key")
            value = clause.get("value")
            try:
                return float(requirements.get(key, 0)) > float(value)
            except (ValueError, TypeError):
                return False

        elif clause_type == "less_than":
            key = clause.get("key")
            value = clause.get("value")
            try:
                return float(requirements.get(key, 0)) < float(value)
            except (ValueError, TypeError):
                return False

        return False
