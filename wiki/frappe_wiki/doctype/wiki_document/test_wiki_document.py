# Copyright (c) 2025, Frappe and Contributors
# See license.txt

import unittest

from frappe.tests import IntegrationTestCase

from wiki.wiki.markdown import render_markdown

# On IntegrationTestCase, the doctype test records and all
# link-field test record dependencies are recursively loaded
# Use these module variables to add/remove to/from that list
EXTRA_TEST_RECORD_DEPENDENCIES = []  # eg. ["User"]
IGNORE_TEST_RECORD_DEPENDENCIES = []  # eg. ["User"]


class IntegrationTestWikiDocument(IntegrationTestCase):
	"""
	Integration tests for WikiDocument.
	Use this class for testing interactions between multiple components.
	"""

	pass


class TestMarkdownCallouts(unittest.TestCase):
	"""
	Unit tests for the markdown callout/aside rendering.
	Tests the Astro Starlight-style :::type[title] syntax.
	"""

	def test_basic_note_callout(self):
		"""Test basic :::note callout with default title"""
		md = """:::note
This is a note
:::"""
		html = render_markdown(md)
		self.assertIn('class="callout callout-note"', html)
		self.assertIn("<span>Note</span>", html)
		self.assertIn("This is a note", html)

	def test_tip_callout(self):
		"""Test :::tip callout"""
		md = """:::tip
This is a tip
:::"""
		html = render_markdown(md)
		self.assertIn('class="callout callout-tip"', html)
		self.assertIn("<span>Tip</span>", html)

	def test_caution_callout(self):
		"""Test :::caution callout"""
		md = """:::caution
This is a caution
:::"""
		html = render_markdown(md)
		self.assertIn('class="callout callout-caution"', html)
		self.assertIn("<span>Caution</span>", html)

	def test_danger_callout(self):
		"""Test :::danger callout"""
		md = """:::danger
This is dangerous
:::"""
		html = render_markdown(md)
		self.assertIn('class="callout callout-danger"', html)
		self.assertIn("<span>Danger</span>", html)

	def test_warning_alias_for_caution(self):
		"""Test :::warning is aliased to caution"""
		md = """:::warning
This is a warning
:::"""
		html = render_markdown(md)
		# warning should be rendered as caution
		self.assertIn('class="callout callout-caution"', html)

	def test_custom_title(self):
		"""Test callout with custom title in brackets"""
		md = """:::tip[Did you know?]
This is a tip with a custom title
:::"""
		html = render_markdown(md)
		self.assertIn('class="callout callout-tip"', html)
		self.assertIn("<span>Did you know?</span>", html)

	def test_callout_with_markdown_content(self):
		"""Test callout with markdown formatting inside"""
		md = """:::note
This has **bold** and *italic* text
:::"""
		html = render_markdown(md)
		self.assertIn("<strong>bold</strong>", html)
		self.assertIn("<em>italic</em>", html)

	def test_callout_with_link(self):
		"""Test callout with markdown link"""
		md = """:::note
Check out [this link](https://example.com)
:::"""
		html = render_markdown(md)
		self.assertIn('<a href="https://example.com">this link</a>', html)

	def test_callout_with_code_block(self):
		"""Test callout with fenced code block inside"""
		md = """:::note
Here's some code:

```python
print("Hello")
```
:::"""
		html = render_markdown(md)
		self.assertIn('class="callout callout-note"', html)
		# Quotes may be HTML-encoded as &quot;
		self.assertTrue('print("Hello")' in html or "print(&quot;Hello&quot;)" in html)
		self.assertIn("<code", html)
		self.assertIn("language-python", html)

	def test_callout_with_list(self):
		"""Test callout with bullet list"""
		md = """:::tip
Here are some items:

- Item 1
- Item 2
- Item 3
:::"""
		html = render_markdown(md)
		self.assertIn("<li>Item 1</li>", html)
		self.assertIn("<li>Item 2</li>", html)

	def test_multiple_callouts(self):
		"""Test multiple callouts in same document"""
		md = """:::note
First callout
:::

Some text in between

:::danger
Second callout
:::"""
		html = render_markdown(md)
		self.assertIn("callout-note", html)
		self.assertIn("callout-danger", html)
		self.assertIn("First callout", html)
		self.assertIn("Second callout", html)

	def test_callout_has_icon(self):
		"""Test that callouts include SVG icons"""
		md = """:::note
Content
:::"""
		html = render_markdown(md)
		self.assertIn("<svg", html)
		self.assertIn("</svg>", html)

	def test_empty_content(self):
		"""Test render_markdown with empty string"""
		self.assertEqual(render_markdown(""), "")
		self.assertEqual(render_markdown(None), "")

	def test_regular_markdown_still_works(self):
		"""Test that regular markdown without callouts still renders"""
		md = """# Heading

This is a paragraph with **bold** text.

- List item 1
- List item 2
"""
		html = render_markdown(md)
		self.assertIn("<h1>Heading</h1>", html)
		self.assertIn("<strong>bold</strong>", html)
		self.assertIn("<li>List item 1</li>", html)

	def test_callout_mixed_with_regular_content(self):
		"""Test callout mixed with regular markdown"""
		md = """# Introduction

This is some intro text.

:::note
Important note here
:::

And this is the conclusion.
"""
		html = render_markdown(md)
		self.assertIn("<h1>Introduction</h1>", html)
		self.assertIn("callout-note", html)
		self.assertIn("Important note here", html)
		self.assertIn("conclusion", html)
