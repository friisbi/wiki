# Copyright (c) 2025, Frappe and Contributors
# See license.txt

import frappe
from frappe.tests.utils import FrappeTestCase


class TestWikiContributionBatch(FrappeTestCase):
	"""Tests for Wiki Contribution Batch."""

	def tearDown(self):
		frappe.db.rollback()

	def test_create_batch(self):
		"""Test creating a contribution batch."""
		space = create_test_wiki_space()

		batch = frappe.new_doc("Wiki Contribution Batch")
		batch.title = "Test Contribution"
		batch.wiki_space = space.name
		batch.insert()

		self.assertEqual(batch.status, "Draft")
		self.assertEqual(batch.contributor, frappe.session.user)

	def test_batch_status_transitions(self):
		"""Test valid status transitions."""
		space = create_test_wiki_space()
		batch = create_test_batch(space.name)

		# Add a contribution so we can submit
		create_test_contribution(batch.name, space.root_group)

		# Draft -> Submitted
		batch.submit_for_review()
		self.assertEqual(batch.status, "Submitted")
		self.assertIsNotNone(batch.submitted_at)

		# Submitted -> Under Review
		batch.start_review()
		self.assertEqual(batch.status, "Under Review")

		# Under Review -> Approved
		batch.approve(comment="Looks good!")
		self.assertEqual(batch.status, "Approved")
		self.assertIsNotNone(batch.reviewed_at)
		self.assertEqual(batch.review_comment, "Looks good!")

	def test_batch_reject(self):
		"""Test rejecting a batch."""
		space = create_test_wiki_space()
		batch = create_test_batch(space.name)
		create_test_contribution(batch.name, space.root_group)

		batch.submit_for_review()
		batch.reject(comment="Needs more work")

		self.assertEqual(batch.status, "Rejected")
		self.assertEqual(batch.review_comment, "Needs more work")

	def test_batch_withdraw(self):
		"""Test withdrawing a submitted batch."""
		space = create_test_wiki_space()
		batch = create_test_batch(space.name)
		create_test_contribution(batch.name, space.root_group)

		batch.submit_for_review()
		batch.withdraw()

		self.assertEqual(batch.status, "Draft")
		self.assertIsNone(batch.submitted_at)

	def test_cannot_submit_empty_batch(self):
		"""Test that empty batches cannot be submitted."""
		space = create_test_wiki_space()
		batch = create_test_batch(space.name)

		with self.assertRaises(frappe.ValidationError):
			batch.submit_for_review()

	def test_invalid_status_transition(self):
		"""Test that invalid status transitions are rejected."""
		space = create_test_wiki_space()
		batch = create_test_batch(space.name)
		batch.status = "Merged"  # Try to jump directly to Merged

		with self.assertRaises(frappe.ValidationError):
			batch.save()

	def test_get_or_create_draft_batch(self):
		"""Test the get_or_create_draft_batch API."""
		from wiki.frappe_wiki.doctype.wiki_contribution_batch.wiki_contribution_batch import (
			get_or_create_draft_batch,
		)

		space = create_test_wiki_space()

		# First call should create
		batch1 = get_or_create_draft_batch(space.name)
		self.assertIsNotNone(batch1.get("name"))

		# Second call should return same batch
		batch2 = get_or_create_draft_batch(space.name)
		self.assertEqual(batch1["name"], batch2["name"])

	def test_get_contributions(self):
		"""Test getting contributions from a batch."""
		space = create_test_wiki_space()
		batch = create_test_batch(space.name)

		# Add multiple contributions
		create_test_contribution(batch.name, space.root_group, title="Page 1")
		create_test_contribution(batch.name, space.root_group, title="Page 2")

		contributions = batch.get_contributions()

		self.assertEqual(len(contributions), 2)
		# Should be ordered by sequence
		self.assertEqual(contributions[0].proposed_title, "Page 1")
		self.assertEqual(contributions[1].proposed_title, "Page 2")


# Helper functions for tests


def create_test_wiki_space():
	"""Create a test Wiki Space with a root group."""
	# Create root group
	root_group = frappe.new_doc("Wiki Document")
	root_group.title = f"Test Root {frappe.generate_hash(length=6)}"
	root_group.is_group = 1
	root_group.insert()

	# Create space
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
