# Copyright (c) 2025, Frappe and Contributors
# See license.txt

import frappe
from frappe.tests.utils import FrappeTestCase


class TestWikiContribution(FrappeTestCase):
	"""Tests for Wiki Contribution."""

	def tearDown(self):
		frappe.db.rollback()

	def test_create_contribution(self):
		"""Test creating a new page contribution."""
		space = create_test_wiki_space()
		batch = create_test_batch(space.name)

		contrib = frappe.new_doc("Wiki Contribution")
		contrib.batch = batch.name
		contrib.operation = "create"
		contrib.parent_ref = space.root_group
		contrib.proposed_title = "New Page"
		contrib.proposed_content = "New content"
		contrib.insert()

		self.assertIsNotNone(contrib.temp_id)
		self.assertEqual(contrib.sequence, 1)

	def test_edit_contribution_snapshots_original(self):
		"""Test that edit contributions snapshot the original content."""
		space = create_test_wiki_space()
		batch = create_test_batch(space.name)

		# Create existing page
		existing_page = frappe.new_doc("Wiki Document")
		existing_page.title = "Existing Page"
		existing_page.content = "Original content"
		existing_page.parent_wiki_document = space.root_group
		existing_page.is_published = 1
		existing_page.insert()

		contrib = frappe.new_doc("Wiki Contribution")
		contrib.batch = batch.name
		contrib.operation = "edit"
		contrib.target_document = existing_page.name
		contrib.proposed_title = "Updated Title"
		contrib.proposed_content = "Updated content"
		contrib.insert()

		self.assertEqual(contrib.original_title, "Existing Page")
		self.assertEqual(contrib.original_content, "Original content")
		self.assertEqual(contrib.target_route, existing_page.route)

	def test_delete_contribution(self):
		"""Test creating a delete contribution."""
		space = create_test_wiki_space()
		batch = create_test_batch(space.name)

		existing_page = frappe.new_doc("Wiki Document")
		existing_page.title = "Existing Page"
		existing_page.content = "Original content"
		existing_page.parent_wiki_document = space.root_group
		existing_page.insert()

		contrib = frappe.new_doc("Wiki Contribution")
		contrib.batch = batch.name
		contrib.operation = "delete"
		contrib.target_document = existing_page.name
		contrib.insert()

		self.assertEqual(contrib.original_title, "Existing Page")

	def test_move_contribution(self):
		"""Test creating a move contribution."""
		space = create_test_wiki_space()
		batch = create_test_batch(space.name)

		existing_page = frappe.new_doc("Wiki Document")
		existing_page.title = "Existing Page"
		existing_page.parent_wiki_document = space.root_group
		existing_page.insert()

		# Create a new group to move to
		new_group = frappe.new_doc("Wiki Document")
		new_group.title = "New Group"
		new_group.is_group = 1
		new_group.parent_wiki_document = space.root_group
		new_group.insert()

		contrib = frappe.new_doc("Wiki Contribution")
		contrib.batch = batch.name
		contrib.operation = "move"
		contrib.target_document = existing_page.name
		contrib.new_parent_ref = new_group.name
		contrib.new_sort_order = 5
		contrib.insert()

		self.assertEqual(contrib.original_parent, space.root_group)

	def test_reorder_contribution(self):
		"""Test creating a reorder contribution."""
		space = create_test_wiki_space()
		batch = create_test_batch(space.name)

		existing_page = frappe.new_doc("Wiki Document")
		existing_page.title = "Existing Page"
		existing_page.parent_wiki_document = space.root_group
		existing_page.insert()

		contrib = frappe.new_doc("Wiki Contribution")
		contrib.batch = batch.name
		contrib.operation = "reorder"
		contrib.target_document = existing_page.name
		contrib.proposed_sort_order = 10
		contrib.insert()

		self.assertEqual(contrib.proposed_sort_order, 10)

	def test_auto_sequence(self):
		"""Test that sequence is auto-incremented."""
		space = create_test_wiki_space()
		batch = create_test_batch(space.name)

		contrib1 = create_test_contribution(batch.name, space.root_group, title="Page 1")
		contrib2 = create_test_contribution(batch.name, space.root_group, title="Page 2")
		contrib3 = create_test_contribution(batch.name, space.root_group, title="Page 3")

		self.assertEqual(contrib1.sequence, 1)
		self.assertEqual(contrib2.sequence, 2)
		self.assertEqual(contrib3.sequence, 3)

	def test_cannot_modify_submitted_batch_contribution(self):
		"""Test that contributions cannot be added to a submitted batch."""
		space = create_test_wiki_space()
		batch = create_test_batch(space.name)

		create_test_contribution(batch.name, space.root_group)
		batch.submit_for_review()

		with self.assertRaises(frappe.ValidationError):
			contrib2 = frappe.new_doc("Wiki Contribution")
			contrib2.batch = batch.name
			contrib2.operation = "create"
			contrib2.parent_ref = space.root_group
			contrib2.proposed_title = "Another Page"
			contrib2.insert()

	def test_validation_create_requires_title(self):
		"""Test that create operation requires proposed_title."""
		space = create_test_wiki_space()
		batch = create_test_batch(space.name)

		contrib = frappe.new_doc("Wiki Contribution")
		contrib.batch = batch.name
		contrib.operation = "create"
		contrib.parent_ref = space.root_group
		# Missing proposed_title

		with self.assertRaises(frappe.ValidationError):
			contrib.insert()

	def test_validation_edit_requires_target(self):
		"""Test that edit operation requires target_document."""
		space = create_test_wiki_space()
		batch = create_test_batch(space.name)

		contrib = frappe.new_doc("Wiki Contribution")
		contrib.batch = batch.name
		contrib.operation = "edit"
		contrib.proposed_title = "New Title"
		# Missing target_document

		with self.assertRaises(frappe.ValidationError):
			contrib.insert()


class TestWikiContributionMerge(FrappeTestCase):
	"""Test the merge operations for contributions."""

	def tearDown(self):
		frappe.db.rollback()

	def test_apply_create(self):
		"""Test applying a create contribution."""
		space = create_test_wiki_space()
		batch = create_test_batch(space.name)

		contrib = create_test_contribution(
			batch.name,
			space.root_group,
			title="New Page",
			content="New content",
		)

		temp_to_real = {}
		contrib_doc = frappe.get_doc("Wiki Contribution", contrib.name)
		contrib_doc.apply(temp_to_real)

		# Check that the document was created
		self.assertIn(contrib.temp_id, temp_to_real)
		new_doc_name = temp_to_real[contrib.temp_id]

		new_doc = frappe.get_doc("Wiki Document", new_doc_name)
		self.assertEqual(new_doc.title, "New Page")
		self.assertEqual(new_doc.content, "New content")
		self.assertEqual(new_doc.parent_wiki_document, space.root_group)

	def test_apply_edit(self):
		"""Test applying an edit contribution."""
		space = create_test_wiki_space()
		batch = create_test_batch(space.name)

		# Create existing page
		existing = frappe.new_doc("Wiki Document")
		existing.title = "Original Title"
		existing.content = "Original content"
		existing.parent_wiki_document = space.root_group
		existing.insert()

		# Create edit contribution
		contrib = frappe.new_doc("Wiki Contribution")
		contrib.batch = batch.name
		contrib.operation = "edit"
		contrib.target_document = existing.name
		contrib.proposed_title = "Updated Title"
		contrib.proposed_content = "Updated content"
		contrib.insert()

		# Apply
		contrib.apply({})

		# Verify
		existing.reload()
		self.assertEqual(existing.title, "Updated Title")
		self.assertEqual(existing.content, "Updated content")

	def test_apply_delete(self):
		"""Test applying a delete contribution."""
		space = create_test_wiki_space()
		batch = create_test_batch(space.name)

		# Create existing page
		existing = frappe.new_doc("Wiki Document")
		existing.title = "To Delete"
		existing.content = "Will be deleted"
		existing.parent_wiki_document = space.root_group
		existing.insert()
		existing_name = existing.name

		# Create delete contribution
		contrib = frappe.new_doc("Wiki Contribution")
		contrib.batch = batch.name
		contrib.operation = "delete"
		contrib.target_document = existing_name
		contrib.insert()

		# Apply
		contrib.apply({})

		# Verify deletion
		self.assertFalse(frappe.db.exists("Wiki Document", existing_name))

	def test_apply_move(self):
		"""Test applying a move contribution."""
		space = create_test_wiki_space()
		batch = create_test_batch(space.name)

		# Create existing page
		existing = frappe.new_doc("Wiki Document")
		existing.title = "To Move"
		existing.parent_wiki_document = space.root_group
		existing.insert()

		# Create new group
		new_group = frappe.new_doc("Wiki Document")
		new_group.title = "New Group"
		new_group.is_group = 1
		new_group.parent_wiki_document = space.root_group
		new_group.insert()

		# Create move contribution
		contrib = frappe.new_doc("Wiki Contribution")
		contrib.batch = batch.name
		contrib.operation = "move"
		contrib.target_document = existing.name
		contrib.new_parent_ref = new_group.name
		contrib.insert()

		# Apply
		contrib.apply({})

		# Verify
		existing.reload()
		self.assertEqual(existing.parent_wiki_document, new_group.name)

	def test_apply_nested_creates(self):
		"""Test creating nested documents using temp_id references."""
		space = create_test_wiki_space()
		batch = create_test_batch(space.name)

		# Create a group
		group_contrib = frappe.new_doc("Wiki Contribution")
		group_contrib.batch = batch.name
		group_contrib.operation = "create"
		group_contrib.parent_ref = space.root_group
		group_contrib.proposed_title = "New Group"
		group_contrib.proposed_is_group = 1
		group_contrib.temp_id = "temp_group"
		group_contrib.insert()

		# Create a page under the group using temp_id
		page_contrib = frappe.new_doc("Wiki Contribution")
		page_contrib.batch = batch.name
		page_contrib.operation = "create"
		page_contrib.parent_ref = "temp_group"  # Reference the temp group
		page_contrib.proposed_title = "Page in Group"
		page_contrib.proposed_content = "Content"
		page_contrib.temp_id = "temp_page"
		page_contrib.insert()

		# Apply both in order
		temp_to_real = {}
		group_contrib.apply(temp_to_real)
		page_contrib.apply(temp_to_real)

		# Verify hierarchy
		self.assertIn("temp_group", temp_to_real)
		self.assertIn("temp_page", temp_to_real)

		group_doc = frappe.get_doc("Wiki Document", temp_to_real["temp_group"])
		page_doc = frappe.get_doc("Wiki Document", temp_to_real["temp_page"])

		self.assertEqual(page_doc.parent_wiki_document, group_doc.name)

	def test_batch_merge(self):
		"""Test merging a complete batch."""
		space = create_test_wiki_space()
		batch = create_test_batch(space.name)

		# Create contributions
		create_test_contribution(batch.name, space.root_group, title="Page 1")
		create_test_contribution(batch.name, space.root_group, title="Page 2")

		# Submit and approve
		batch.submit_for_review()
		batch.approve()

		# Merge
		batch.merge()

		# Verify batch status
		self.assertEqual(batch.status, "Merged")

		# Verify documents were created
		pages = frappe.get_all(
			"Wiki Document",
			filters={
				"parent_wiki_document": space.root_group,
				"title": ("in", ["Page 1", "Page 2"]),
			},
		)
		self.assertEqual(len(pages), 2)


class TestMergedTreePreview(FrappeTestCase):
	"""Test the merged tree preview functionality."""

	def tearDown(self):
		frappe.db.rollback()

	def test_merged_tree_with_new_page(self):
		"""Test that merged tree shows new pages."""
		from wiki.frappe_wiki.doctype.wiki_contribution.wiki_contribution import get_merged_tree

		space = create_test_wiki_space()
		batch = create_test_batch(space.name)

		# Create an existing page
		page1 = frappe.new_doc("Wiki Document")
		page1.title = "Page 1"
		page1.content = "Content 1"
		page1.parent_wiki_document = space.root_group
		page1.is_published = 1
		page1.insert()

		# Add a new page contribution
		create_test_contribution(batch.name, space.root_group, title="New Page")

		tree = get_merged_tree(space.name, batch.name)

		# Should have Page 1 (live) and New Page (new)
		titles = [node["title"] for node in tree]
		self.assertIn("Page 1", titles)
		self.assertIn("New Page", titles)

		# New page should be marked as 'new'
		new_page = next(n for n in tree if n["title"] == "New Page")
		self.assertEqual(new_page["status"], "new")

	def test_merged_tree_with_edit(self):
		"""Test that merged tree shows edited pages."""
		from wiki.frappe_wiki.doctype.wiki_contribution.wiki_contribution import get_merged_tree

		space = create_test_wiki_space()
		batch = create_test_batch(space.name)

		page1 = frappe.new_doc("Wiki Document")
		page1.title = "Page 1"
		page1.content = "Content 1"
		page1.parent_wiki_document = space.root_group
		page1.is_published = 1
		page1.insert()

		# Create edit contribution
		contrib = frappe.new_doc("Wiki Contribution")
		contrib.batch = batch.name
		contrib.operation = "edit"
		contrib.target_document = page1.name
		contrib.proposed_title = "Updated Page 1"
		contrib.proposed_content = "Updated content"
		contrib.insert()

		tree = get_merged_tree(space.name, batch.name)

		# Should show updated title
		page1_node = next(n for n in tree if n["name"] == page1.name)
		self.assertEqual(page1_node["title"], "Updated Page 1")
		self.assertEqual(page1_node["status"], "modified")

	def test_merged_tree_with_delete(self):
		"""Test that merged tree shows deleted pages."""
		from wiki.frappe_wiki.doctype.wiki_contribution.wiki_contribution import get_merged_tree

		space = create_test_wiki_space()
		batch = create_test_batch(space.name)

		page1 = frappe.new_doc("Wiki Document")
		page1.title = "Page 1"
		page1.content = "Content 1"
		page1.parent_wiki_document = space.root_group
		page1.is_published = 1
		page1.insert()

		# Create delete contribution
		contrib = frappe.new_doc("Wiki Contribution")
		contrib.batch = batch.name
		contrib.operation = "delete"
		contrib.target_document = page1.name
		contrib.insert()

		tree = get_merged_tree(space.name, batch.name)

		# Should show page as deleted
		page1_node = next(n for n in tree if n["name"] == page1.name)
		self.assertEqual(page1_node["status"], "deleted")


# Helper functions


def create_test_wiki_space():
	"""Create a test Wiki Space with a root group."""
	root_group = frappe.new_doc("Wiki Document")
	root_group.title = f"Test Root {frappe.generate_hash(length=6)}"
	root_group.is_group = 1
	root_group.insert()

	space = frappe.new_doc("Wiki Space")
	space.space_name = "Test Space"
	space.route = f"test-space-{frappe.generate_hash(length=6)}"
	space.root_group = root_group.name
	space.insert()

	return space


def create_test_batch(wiki_space: str, title: str = "Test Batch"):
	"""Create a test contribution batch."""
	batch = frappe.new_doc("Wiki Contribution Batch")
	batch.title = title
	batch.wiki_space = wiki_space
	batch.insert()
	return batch


def create_test_contribution(
	batch: str,
	parent_ref: str,
	title: str = "Test Page",
	content: str = "Test content",
	operation: str = "create",
):
	"""Create a test contribution."""
	contrib = frappe.new_doc("Wiki Contribution")
	contrib.batch = batch
	contrib.operation = operation
	contrib.parent_ref = parent_ref
	contrib.proposed_title = title
	contrib.proposed_content = content
	contrib.proposed_is_published = 1
	contrib.insert()
	return contrib
