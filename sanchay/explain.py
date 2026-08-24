"""Narrate the ranking. The model never chooses what to delete.

Ranking is decided by regret.py from file metadata. The model only explains a
list that already exists, so a hallucination cannot promote an irreplaceable
file into the recommendations.
"""
import os

PROMPT = """You are advising a Linux user on reclaiming disk space.

These candidates were ranked by a regret model. "kind" is how recoverable the
file is: disposable (a build tool regenerates it), duplicate (another copy
survives), tracked (committed to a repo). Irreplaceable files were excluded
before you saw this list.

{table}

Group these into 3-4 cleanup actions. For each: what to remove, roughly how much
it frees, and why it is safe. One short paragraph each. Do not suggest deleting
anything not listed."""


def table(rows):
    return "\n".join(
        f"- {r['path']}  ({r['size'] / 1e6:.1f} MB, {r['kind']}, "
        f"unused {r['staleness'] * 365:.0f}d)" for r in rows)


def explain(rows, model=None):
    if not rows:
        return "Nothing safe to reclaim."
    if not os.environ.get("ANTHROPIC_API_KEY"):
        return "Set ANTHROPIC_API_KEY for narrative advice.\n\n" + table(rows)

    from anthropic import Anthropic

    selected_model = model or os.environ.get("ANTHROPIC_MODEL", "claude-3-5-sonnet-20241022")
    try:
        message = Anthropic().messages.create(
            model=selected_model,
            max_tokens=1024,
            messages=[{"role": "user", "content": PROMPT.format(table=table(rows))}],
        )
        return message.content[0].text
    except Exception as e:
        return f"[LLM explanation unavailable: {e}]\n\n" + table(rows)
