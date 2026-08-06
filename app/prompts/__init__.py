"""
Phase 2 prompts — extraction agents for action items, requirements, and risks.

WHY separate prompts per agent (not one mega-prompt):
- Each agent is focused and produces more reliable JSON
- Easier to iterate/tune one agent without breaking others
- Smaller context = less hallucination risk
"""
