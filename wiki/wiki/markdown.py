"""
Custom Markdown Renderer with Callout/Aside Support

This module provides a custom markdown-to-HTML renderer using Mistune,
with support for Astro Starlight-style callouts/asides.

Syntax:
    :::note
    Content here
    :::

    :::tip[Custom Title]
    Content with custom title
    :::

Supported types: note, tip, caution, danger, warning (alias for caution)
"""

import re

import mistune

# Default titles for each callout type
DEFAULT_TITLES = {
	"note": "Note",
	"tip": "Tip",
	"caution": "Caution",
	"danger": "Danger",
	"warning": "Caution",  # warning is alias for caution
}

# SVG icons for each callout type
CALLOUT_ICONS = {
	"note": '<svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"/><path d="M12 16v-4"/><path d="M12 8h.01"/></svg>',
	"tip": '<svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M15 14c.2-1 .7-1.7 1.5-2.5 1-.9 1.5-2.2 1.5-3.5A6 6 0 0 0 6 8c0 1 .2 2.2 1.5 3.5.7.7 1.3 1.5 1.5 2.5"/><path d="M9 18h6"/><path d="M10 22h4"/></svg>',
	"caution": '<svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="m21.73 18-8-14a2 2 0 0 0-3.48 0l-8 14A2 2 0 0 0 4 21h16a2 2 0 0 0 1.73-3Z"/><path d="M12 9v4"/><path d="M12 17h.01"/></svg>',
	"danger": '<svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10"/><path d="M12 8v4"/><path d="M12 16h.01"/></svg>',
}

# Pattern to match callout blocks
# Matches: :::type or :::type[title]
# Content continues until closing :::
CALLOUT_PATTERN = re.compile(
	r"^:::(?P<type>note|tip|caution|danger|warning)(?:\[(?P<title>[^\]]*)\])?\s*\n(?P<content>[\s\S]*?)\n:::[ \t]*$",
	re.MULTILINE,
)


def _process_callout_match(match, md_instance):
	"""Process a single callout match and return HTML."""
	callout_type = match.group("type")
	title = match.group("title")
	content = match.group("content")

	# Normalize warning to caution for consistency
	if callout_type == "warning":
		callout_type = "caution"

	# Use default title if none provided
	if not title:
		title = DEFAULT_TITLES.get(callout_type, callout_type.capitalize())

	icon = CALLOUT_ICONS.get(callout_type, CALLOUT_ICONS["note"])

	# Render the inner content as markdown
	inner_html = md_instance(content.strip()) if content.strip() else ""

	return (
		f'<aside class="callout callout-{callout_type}">\n'
		f'<div class="callout-title">{icon}<span>{title}</span></div>\n'
		f'<div class="callout-content">{inner_html}</div>\n'
		f"</aside>\n"
	)


def _preprocess_callouts(content, md_instance):
	"""
	Pre-process callout blocks before main markdown parsing.
	This handles the :::type[title] syntax and converts to HTML.
	"""

	def replacer(match):
		return _process_callout_match(match, md_instance)

	# Process callouts (may be nested, so we process iteratively)
	prev_content = None
	while prev_content != content:
		prev_content = content
		content = CALLOUT_PATTERN.sub(replacer, content)

	return content


def render_markdown(content: str) -> str:
	"""
	Convert markdown content to HTML with callout support.

	Args:
	    content: Markdown string to convert

	Returns:
	    HTML string
	"""
	if not content:
		return ""

	# Create a base Mistune markdown instance for rendering inner content
	md = mistune.create_markdown(
		plugins=[
			"strikethrough",
			"footnotes",
			"table",
			"task_lists",
		],
		escape=False,
	)

	# First, process callouts (they can contain markdown)
	processed_content = _preprocess_callouts(content, md)

	# Then render remaining markdown
	return md(processed_content)
