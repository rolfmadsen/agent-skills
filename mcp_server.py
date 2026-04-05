# /// script
# requires-python = ">=3.10"
# dependencies = [
#     "mcp",
#     "pyyaml",
# ]
# ///

"""
mcp_server.py — MCP adapter for the Agent Skills project.

Exposes engineering workflows (Spec-Driven Dev, TDD, etc.) as MCP tools,
enabling any AI agent to discover and follow senior engineering processes.

Tools:
    list_skills: List names/descriptions of all 20+ skills.
    get_skill: Get full SKILL.md or specific section (e.g. Process).
    validate_state: Check if project has spec.md, plan.md, task.md.
"""

import os
import yaml
import re
from pathlib import Path
import json
from mcp.server.fastmcp import FastMCP

# ---------------------------------------------------------------------------
# Initialize
# ---------------------------------------------------------------------------

mcp = FastMCP(
    "agent-skills",
    instructions=(
        "Production-grade engineering skills for AI coding agents. "
        "Use these tools to discover and follow senior workflows: "
        "Spec-Driven Development, TDD, Incremental Implementation, and more. "
        "You MUST use validate_state before starting any meaningful implementation."
    ),
)

SKILLS_DIR = Path(__file__).parent / "skills"

def parse_skill_md(file_path: Path):
    """Parse YAML frontmatter and Markdown content from a SKILL.md file."""
    with open(file_path, "r", encoding="utf-8") as f:
        content = f.read()
    
    # Split YAML frontmatter from content
    match = re.match(r"^---\s*\n(.*?)\n---\s*\n(.*)$", content, re.DOTALL)
    if not match:
        return None, content
    
    frontmatter_raw = match.group(1)
    markdown_content = match.group(2)
    
    try:
        frontmatter = yaml.safe_load(frontmatter_raw)
        return frontmatter, markdown_content
    except yaml.YAMLError:
        return None, markdown_content

def extract_section(markdown: str, section_name: str) -> str:
    """Extract a specific ## header section from markdown."""
    pattern = rf"## {re.escape(section_name)}(.*?)(?=\n## |$)"
    match = re.search(pattern, markdown, re.DOTALL | re.IGNORECASE)
    if match:
        return match.group(1).strip()
    return ""

# ---------------------------------------------------------------------------
# Tools
# ---------------------------------------------------------------------------

@mcp.tool()
def list_skills() -> str:
    """
    List all available engineering skills with their descriptions.
    
    Returns:
        JSON list of skill metadata (name, description, path).
    """
    skills = []
    for skill_path in SKILLS_DIR.glob("*/SKILL.md"):
        frontmatter, _ = parse_skill_md(skill_path)
        if frontmatter:
            skills.append({
                "name": frontmatter.get("name", skill_path.parent.name),
                "description": frontmatter.get("description", ""),
                "skill_id": skill_path.parent.name
            })
    
    return json.dumps(skills, indent=2)

@mcp.tool()
def get_skill(skill_id: str, section: str = "") -> str:
    """
    Get the details of a specific engineering skill.
    
    Args:
        skill_id: The ID of the skill (e.g. 'spec-driven-development').
        section: Optional. Specific section to return (e.g. 'Process', 'Verification').
                 If empty, returns the full content.
    
    Returns:
        The skill content or section text.
    """
    skill_path = SKILLS_DIR / skill_id / "SKILL.md"
    if not skill_path.exists():
        return f"Error: Skill '{skill_id}' not found."
    
    frontmatter, markdown = parse_skill_md(skill_path)
    
    if section:
        extracted = extract_section(markdown, section)
        if not extracted:
            return f"Section '{section}' not found in skill '{skill_id}'."
        return extracted
    
    return markdown

@mcp.tool()
def validate_state(cwd: str = ".") -> str:
    """
    Validate the current project state against Spec-Driven Development requirements.
    Checks for the existence of spec.md, implementation_plan.md, and task.md.
    
    Args:
        cwd: The project directory to check (defaults to current dir).
    
    Returns:
        JSON report of found/missing SDD artifacts and a status recommendation.
    """
    root = Path(cwd).resolve()
    
    # Check for core artifacts (case-insensitive check)
    files = list(root.glob("*"))
    file_names = [f.name.lower() for f in files]
    
    report = {
        "spec_found": "spec.md" in file_names or "specification.md" in file_names,
        "plan_found": "implementation_plan.md" in file_names or "plan.md" in file_names,
        "task_found": "task.md" in file_names,
        "is_valid": False,
        "recommendation": ""
    }
    
    if not report["spec_found"]:
        report["recommendation"] = "STOP: No spec.md found. Use 'spec-driven-development' workflow first."
    elif not report["plan_found"]:
        report["recommendation"] = "STOP: No implementation_plan.md found. Use 'planning-and-task-breakdown' workflow."
    elif not report["task_found"]:
        report["recommendation"] = "WARNING: No task.md found. Create a task list to track execution."
    else:
        report["is_valid"] = True
        report["recommendation"] = "GO: Project state is compliant with Spec-Driven Development."
        
    return json.dumps(report, indent=2)

# ---------------------------------------------------------------------------
# Entry Point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    mcp.run()
