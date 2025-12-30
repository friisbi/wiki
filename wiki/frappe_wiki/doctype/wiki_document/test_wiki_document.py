# Copyright (c) 2025, Frappe and Contributors
# See license.txt

import unittest

import frappe
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


class TestGetWebContext(IntegrationTestCase):
	"""
	Unit tests for the get_web_context method of WikiDocument.
	Tests navigation (prev/next doc) edge cases and wiki spaces switcher.
	"""

	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		cls.test_docs = []
		cls.test_spaces = []

	def tearDown(self):
		# Clean up test documents
		for doc_name in reversed(self.test_docs):
			if frappe.db.exists("Wiki Document", doc_name):
				frappe.delete_doc("Wiki Document", doc_name, force=True)
		self.test_docs = []

		# Clean up test spaces
		for space_name in self.test_spaces:
			if frappe.db.exists("Wiki Space", space_name):
				frappe.delete_doc("Wiki Space", space_name, force=True)
		self.test_spaces = []

	def _create_wiki_document(self, title, parent=None, is_group=False, is_published=True, sort_order=0):
		"""Helper to create a wiki document for testing."""
		doc = frappe.get_doc(
			{
				"doctype": "Wiki Document",
				"title": title,
				"parent_wiki_document": parent,
				"is_group": is_group,
				"is_published": is_published,
				"sort_order": sort_order,
				"content": f"Content for {title}",
			}
		)
		doc.insert(ignore_permissions=True)
		self.test_docs.append(doc.name)
		return doc

	def _create_wiki_space(self, space_name, route, root_group, show_in_switcher=True, is_published=True):
		"""Helper to create a wiki space for testing."""
		doc = frappe.get_doc(
			{
				"doctype": "Wiki Space",
				"space_name": space_name,
				"route": route,
				"root_group": root_group,
				"show_in_switcher": show_in_switcher,
				"is_published": is_published,
			}
		)
		doc.insert(ignore_permissions=True)
		self.test_spaces.append(doc.name)
		return doc

	def test_first_document_has_no_prev_doc(self):
		"""Test that the first document in the tree has no previous document."""
		# Create a simple tree: Root Group -> Doc1 -> Doc2 -> Doc3
		root_group = self._create_wiki_document("Test Root Group", is_group=True)
		doc1 = self._create_wiki_document("First Document", parent=root_group.name)
		self._create_wiki_document("Second Document", parent=root_group.name)
		self._create_wiki_document("Third Document", parent=root_group.name)

		# Create wiki space
		self._create_wiki_space("Test Space", "test-space", root_group.name)

		# Get context for the first document
		doc1.reload()
		context = doc1.get_web_context()

		# First document should have no prev_doc but should have next_doc
		self.assertIsNone(context["prev_doc"])
		self.assertIsNotNone(context["next_doc"])
		self.assertEqual(context["next_doc"]["title"], "Second Document")

	def test_last_document_has_no_next_doc(self):
		"""Test that the last document in the tree has no next document."""
		# Create a simple tree: Root Group -> Doc1 -> Doc2 -> Doc3
		root_group = self._create_wiki_document("Test Root Group Last", is_group=True)
		self._create_wiki_document("First Doc", parent=root_group.name)
		self._create_wiki_document("Second Doc", parent=root_group.name)
		doc3 = self._create_wiki_document("Third Doc", parent=root_group.name)

		# Create wiki space
		self._create_wiki_space("Test Space Last", "test-space-last", root_group.name)

		# Get context for the last document
		doc3.reload()
		context = doc3.get_web_context()

		# Last document should have prev_doc but no next_doc
		self.assertIsNotNone(context["prev_doc"])
		self.assertEqual(context["prev_doc"]["title"], "Second Doc")
		self.assertIsNone(context["next_doc"])

	def test_middle_document_has_both_prev_and_next(self):
		"""Test that a middle document has both prev and next documents."""
		# Create a simple tree: Root Group -> Doc1 -> Doc2 -> Doc3
		root_group = self._create_wiki_document("Test Root Group Middle", is_group=True)
		self._create_wiki_document("First Page", parent=root_group.name)
		doc2 = self._create_wiki_document("Middle Page", parent=root_group.name)
		self._create_wiki_document("Last Page", parent=root_group.name)

		# Create wiki space
		self._create_wiki_space("Test Space Middle", "test-space-middle", root_group.name)

		# Get context for the middle document
		doc2.reload()
		context = doc2.get_web_context()

		# Middle document should have both prev_doc and next_doc
		self.assertIsNotNone(context["prev_doc"])
		self.assertEqual(context["prev_doc"]["title"], "First Page")
		self.assertIsNotNone(context["next_doc"])
		self.assertEqual(context["next_doc"]["title"], "Last Page")

	def test_single_document_has_no_prev_or_next(self):
		"""Test that a single document in the tree has neither prev nor next."""
		# Create a tree with only one document
		root_group = self._create_wiki_document("Test Root Group Single", is_group=True)
		only_doc = self._create_wiki_document("Only Document", parent=root_group.name)

		# Create wiki space
		self._create_wiki_space("Test Space Single", "test-space-single", root_group.name)

		# Get context for the only document
		only_doc.reload()
		context = only_doc.get_web_context()

		# Single document should have neither prev_doc nor next_doc
		self.assertIsNone(context["prev_doc"])
		self.assertIsNone(context["next_doc"])

	def test_wiki_spaces_for_switcher_includes_current_space_even_if_not_published(self):
		"""
		Test that wiki_spaces_for_switcher includes the current space
		even when show_in_switcher is disabled, because of or_filters.
		"""
		# Create three wiki spaces with their root groups
		root1 = self._create_wiki_document("Root Group Space 1", is_group=True)
		doc1 = self._create_wiki_document("Doc in Space 1", parent=root1.name)

		root2 = self._create_wiki_document("Root Group Space 2", is_group=True)
		self._create_wiki_document("Doc in Space 2", parent=root2.name)

		root3 = self._create_wiki_document("Root Group Space 3", is_group=True)
		self._create_wiki_document("Doc in Space 3", parent=root3.name)

		# Create spaces - Space 1 has show_in_switcher=False but current doc belongs to it
		self._create_wiki_space("Space One", "space-one", root1.name, show_in_switcher=False)
		self._create_wiki_space("Space Two", "space-two", root2.name, show_in_switcher=True)
		self._create_wiki_space("Space Three", "space-three", root3.name, show_in_switcher=True)

		# Get context for doc in Space 1 (which has show_in_switcher=False)
		doc1.reload()
		context = doc1.get_web_context()

		# wiki_spaces_for_switcher should include all 3 test spaces:
		# - Space 1 because it's the current space (or_filter: name=space1.name)
		# - Space 2 and 3 because show_in_switcher=True
		# Note: There may be other pre-existing spaces in the database
		switcher_spaces = context["wiki_spaces_for_switcher"]
		space_names = [s["space_name"] for s in switcher_spaces]

		self.assertIn("Space One", space_names)
		self.assertIn("Space Two", space_names)
		self.assertIn("Space Three", space_names)
		# Ensure at least our 3 test spaces are included
		self.assertGreaterEqual(len(switcher_spaces), 3)

	def test_wiki_spaces_for_switcher_excludes_hidden_spaces(self):
		"""
		Test that wiki_spaces_for_switcher excludes spaces with show_in_switcher=False
		when viewing a document from a different space.
		"""
		# Create three wiki spaces with their root groups
		root1 = self._create_wiki_document("Root Hidden Space", is_group=True)
		self._create_wiki_document("Doc in Hidden Space", parent=root1.name)

		root2 = self._create_wiki_document("Root Visible Space", is_group=True)
		doc2 = self._create_wiki_document("Doc in Visible Space", parent=root2.name)

		root3 = self._create_wiki_document("Root Another Visible", is_group=True)
		self._create_wiki_document("Doc in Another Visible", parent=root3.name)

		# Create spaces - Space 1 (Hidden) has show_in_switcher=False
		self._create_wiki_space("Hidden Space", "hidden-space", root1.name, show_in_switcher=False)
		self._create_wiki_space("Visible Space", "visible-space", root2.name, show_in_switcher=True)
		self._create_wiki_space("Another Visible", "another-visible", root3.name, show_in_switcher=True)

		# Get context for doc in Visible Space
		doc2.reload()
		context = doc2.get_web_context()

		# wiki_spaces_for_switcher should include only visible spaces + current space
		# Since current space (Visible Space) has show_in_switcher=True,
		# Hidden Space should be excluded
		switcher_spaces = context["wiki_spaces_for_switcher"]
		space_names = [s["space_name"] for s in switcher_spaces]

		self.assertNotIn("Hidden Space", space_names)
		self.assertIn("Visible Space", space_names)
		self.assertIn("Another Visible", space_names)
		# At least our 2 visible test spaces should be included
		self.assertGreaterEqual(len(switcher_spaces), 2)


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
