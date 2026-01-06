# Copyright (c) 2025, Frappe and Contributors
# See license.txt

import json

import frappe
from frappe.tests.utils import FrappeTestCase


class TestReorderWikiDocumentsAPI(FrappeTestCase):
	"""Tests for the reorder_wiki_documents API."""

	def setUp(self):
		# Always start as Administrator
		frappe.set_user("Administrator")

	def tearDown(self):
		# Reset to Administrator before rollback
		frappe.set_user("Administrator")
		frappe.db.rollback()

	def test_direct_reorder_as_manager(self):
		"""Test direct reorder when user has write permission."""
		space = create_test_wiki_space()

		# Create multiple pages
		page1 = create_wiki_document(space.root_group, "Page 1")
		page2 = create_wiki_document(space.root_group, "Page 2")
		page3 = create_wiki_document(space.root_group, "Page 3")

		# Set as administrator (has write permission)
		frappe.set_user("Administrator")

		# Reorder - move page3 to first position
		from wiki.api.wiki_space import reorder_wiki_documents

		siblings = json.dumps([page3.name, page1.name, page2.name])
		result = reorder_wiki_documents(
			doc_name=page3.name,
			new_parent=space.root_group,
			new_index=0,
			siblings=siblings,
		)

		# Direct reorder returns None (implicit success)
		self.assertIsNone(result)

		# Verify sort orders were updated
		page1.reload()
		page2.reload()
		page3.reload()

		self.assertEqual(page3.sort_order, 0)
		self.assertEqual(page1.sort_order, 1)
		self.assertEqual(page2.sort_order, 2)

	def test_direct_move_changes_parent(self):
		"""Test that moving a document to a new parent updates the parent."""
		space = create_test_wiki_space()

		# Create a group and a page
		group = create_wiki_document(space.root_group, "Group", is_group=True)
		page = create_wiki_document(space.root_group, "Page to Move")

		frappe.set_user("Administrator")

		from wiki.api.wiki_space import reorder_wiki_documents

		# Move page into the group
		result = reorder_wiki_documents(
			doc_name=page.name,
			new_parent=group.name,
			new_index=0,
			siblings=json.dumps([page.name]),
		)

		# Direct move returns None (implicit success)
		self.assertIsNone(result)

		page.reload()
		self.assertEqual(page.parent_wiki_document, group.name)

	def test_reorder_creates_contribution_without_permission(self):
		"""Test that reorder creates a contribution when user lacks write permission."""
		space = create_test_wiki_space()
		page = create_wiki_document(space.root_group, "Test Page")

		# Create a test user without Wiki Manager role
		test_user = create_test_user("contributor@test.com")
		frappe.set_user(test_user.name)

		from wiki.api.wiki_space import reorder_wiki_documents

		result = reorder_wiki_documents(
			doc_name=page.name,
			new_parent=space.root_group,
			new_index=5,
			siblings=json.dumps([page.name]),
		)

		# Contribution mode returns dict with contribution info
		self.assertTrue(result.get("is_contribution"))
		self.assertIsNotNone(result.get("contribution"))
		self.assertIsNotNone(result.get("batch"))

		# Verify contribution was created
		contrib = frappe.get_doc("Wiki Contribution", result["contribution"])
		self.assertEqual(contrib.operation, "reorder")
		self.assertEqual(contrib.target_document, page.name)
		self.assertEqual(contrib.proposed_sort_order, 5)

	def test_move_creates_contribution_without_permission(self):
		"""Test that moving creates a contribution when user lacks write permission."""
		space = create_test_wiki_space()
		group = create_wiki_document(space.root_group, "Target Group", is_group=True)
		page = create_wiki_document(space.root_group, "Page to Move")

		test_user = create_test_user("contributor2@test.com")
		frappe.set_user(test_user.name)

		from wiki.api.wiki_space import reorder_wiki_documents

		result = reorder_wiki_documents(
			doc_name=page.name,
			new_parent=group.name,
			new_index=0,
			siblings=json.dumps([page.name]),
		)

		# Contribution mode returns dict with contribution info
		self.assertTrue(result.get("is_contribution"))

		contrib = frappe.get_doc("Wiki Contribution", result["contribution"])
		self.assertEqual(contrib.operation, "move")
		self.assertEqual(contrib.target_document, page.name)
		self.assertEqual(contrib.new_parent_ref, group.name)

	def test_reorder_draft_item_updates_contribution(self):
		"""Test that reordering a draft item updates its parent_ref."""
		space = create_test_wiki_space()
		batch = create_test_batch(space.name)

		# Create a draft contribution
		contrib = frappe.new_doc("Wiki Contribution")
		contrib.batch = batch.name
		contrib.operation = "create"
		contrib.parent_ref = space.root_group
		contrib.proposed_title = "Draft Page"
		contrib.proposed_content = "Content"
		contrib.insert()

		temp_id = contrib.temp_id

		# Create a new group to move the draft into
		group = create_wiki_document(space.root_group, "Target Group", is_group=True)

		# Move the draft item (as any user - drafts are editable by owner)
		from wiki.api.wiki_space import reorder_wiki_documents

		result = reorder_wiki_documents(
			doc_name=temp_id,
			new_parent=group.name,
			new_index=0,
			siblings=json.dumps([temp_id]),
		)

		# Draft item update returns is_contribution flag
		self.assertTrue(result.get("is_contribution"))

		# Verify the contribution's parent_ref was updated
		contrib.reload()
		self.assertEqual(contrib.parent_ref, group.name)
		self.assertEqual(contrib.proposed_sort_order, 0)

		# Verify siblings_order was stored
		self.assertIsNotNone(contrib.siblings_order)
		stored_siblings = json.loads(contrib.siblings_order)
		self.assertEqual(stored_siblings, [temp_id])

	def test_reorder_skips_temp_items_in_siblings(self):
		"""Test that temp items in siblings list are skipped when updating sort_order."""
		space = create_test_wiki_space()

		page1 = create_wiki_document(space.root_group, "Page 1")
		page2 = create_wiki_document(space.root_group, "Page 2")

		frappe.set_user("Administrator")

		from wiki.api.wiki_space import reorder_wiki_documents

		# Include a temp item in siblings (simulating a draft in the list)
		siblings = json.dumps([page1.name, "temp_abc123", page2.name])

		result = reorder_wiki_documents(
			doc_name=page1.name,
			new_parent=space.root_group,
			new_index=0,
			siblings=siblings,
		)

		# Direct reorder returns None (implicit success)
		self.assertIsNone(result)

		# Verify sort orders - temp item should be skipped
		page1.reload()
		page2.reload()

		self.assertEqual(page1.sort_order, 0)
		# page2 gets index 2 because temp_abc123 was at index 1 but skipped
		self.assertEqual(page2.sort_order, 2)

	def test_reorder_with_explicit_batch(self):
		"""Test reorder with explicit batch parameter creates contribution."""
		space = create_test_wiki_space()
		batch = create_test_batch(space.name)
		page = create_wiki_document(space.root_group, "Test Page")

		frappe.set_user("Administrator")  # Even as admin, explicit batch creates contribution

		from wiki.api.wiki_space import reorder_wiki_documents

		result = reorder_wiki_documents(
			doc_name=page.name,
			new_parent=space.root_group,
			new_index=3,
			siblings=json.dumps([page.name]),
			batch=batch.name,
		)

		# Contribution mode returns dict with contribution info
		self.assertTrue(result.get("is_contribution"))
		self.assertEqual(result.get("batch"), batch.name)

	def test_reorder_children_within_group(self):
		"""Test reordering children within a group (not at root level)."""
		space = create_test_wiki_space()

		# Create a group with three children
		group = create_wiki_document(space.root_group, "Test Group", is_group=True)
		child1 = create_wiki_document(group.name, "Child 1")
		child2 = create_wiki_document(group.name, "Child 2")
		child3 = create_wiki_document(group.name, "Child 3")

		frappe.set_user("Administrator")

		from wiki.api.wiki_space import reorder_wiki_documents

		# Reorder children: move child3 to first position
		# New order: child3, child1, child2
		siblings = json.dumps([child3.name, child1.name, child2.name])
		result = reorder_wiki_documents(
			doc_name=child3.name,
			new_parent=group.name,
			new_index=0,
			siblings=siblings,
		)

		# Direct reorder returns None (implicit success)
		self.assertIsNone(result)

		# Verify sort orders were updated
		child1.reload()
		child2.reload()
		child3.reload()

		self.assertEqual(child3.sort_order, 0)
		self.assertEqual(child1.sort_order, 1)
		self.assertEqual(child2.sort_order, 2)

		# Verify parent wasn't changed
		self.assertEqual(child1.parent_wiki_document, group.name)
		self.assertEqual(child2.parent_wiki_document, group.name)
		self.assertEqual(child3.parent_wiki_document, group.name)

	def test_reorder_children_within_group_contribution_mode(self):
		"""Test reordering children within a group in contribution mode."""
		space = create_test_wiki_space()

		# Create a group with three children
		group = create_wiki_document(space.root_group, "Test Group", is_group=True)
		child1 = create_wiki_document(group.name, "Child 1")
		child2 = create_wiki_document(group.name, "Child 2")
		child3 = create_wiki_document(group.name, "Child 3")

		# Create a test user without Wiki Manager role
		test_user = create_test_user("contributor3@test.com")
		frappe.set_user(test_user.name)

		from wiki.api.wiki_space import reorder_wiki_documents

		# Reorder children: move child3 to first position
		siblings = json.dumps([child3.name, child1.name, child2.name])
		result = reorder_wiki_documents(
			doc_name=child3.name,
			new_parent=group.name,
			new_index=0,
			siblings=siblings,
		)

		# Contribution mode returns dict with contribution info
		self.assertTrue(result.get("is_contribution"))

		# Verify contribution was created with correct data
		contrib = frappe.get_doc("Wiki Contribution", result["contribution"])
		self.assertEqual(contrib.operation, "reorder")
		self.assertEqual(contrib.target_document, child3.name)
		self.assertEqual(contrib.proposed_sort_order, 0)

		# Verify siblings_order was stored for frontend merging
		self.assertIsNotNone(contrib.siblings_order)
		stored_siblings = json.loads(contrib.siblings_order)
		self.assertEqual(stored_siblings, [child3.name, child1.name, child2.name])


class TestRebuildWikiTree(FrappeTestCase):
	"""Tests for the rebuild_wiki_tree function."""

	def setUp(self):
		frappe.set_user("Administrator")

	def tearDown(self):
		frappe.set_user("Administrator")
		frappe.db.rollback()

	def test_rebuild_respects_sort_order(self):
		"""Test that rebuild_wiki_tree respects sort_order field."""
		space = create_test_wiki_space()

		# Create pages with explicit sort orders (reverse alphabetical)
		page_c = create_wiki_document(space.root_group, "Page C")
		page_b = create_wiki_document(space.root_group, "Page B")
		page_a = create_wiki_document(space.root_group, "Page A")

		# Set sort orders to put them in reverse order
		frappe.db.set_value("Wiki Document", page_c.name, "sort_order", 0)
		frappe.db.set_value("Wiki Document", page_b.name, "sort_order", 1)
		frappe.db.set_value("Wiki Document", page_a.name, "sort_order", 2)

		from wiki.api.wiki_space import rebuild_wiki_tree

		rebuild_wiki_tree()

		# Reload and check lft values
		page_c.reload()
		page_b.reload()
		page_a.reload()

		# Page C should have lowest lft (comes first)
		self.assertLess(page_c.lft, page_b.lft)
		self.assertLess(page_b.lft, page_a.lft)


# Helper functions


def create_test_wiki_space():
	"""Create a test Wiki Space with a root group."""
	root_group = frappe.new_doc("Wiki Document")
	root_group.title = f"Test Root {frappe.generate_hash(length=6)}"
	root_group.is_group = 1
	root_group.insert()

	space = frappe.new_doc("Wiki Space")
	space.space_name = f"Test Space {frappe.generate_hash(length=6)}"
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


def create_wiki_document(parent: str, title: str, is_group: bool = False, content: str = ""):
	"""Create a Wiki Document."""
	doc = frappe.new_doc("Wiki Document")
	doc.title = title
	doc.parent_wiki_document = parent
	doc.is_group = 1 if is_group else 0
	doc.content = content
	doc.insert()
	return doc


def create_test_user(email: str, roles: list | None = None):
	"""Create a test user with specified roles.

	This function should be called while logged in as Administrator.
	"""
	# Save current user and switch to Administrator for user creation
	current_user = frappe.session.user
	frappe.set_user("Administrator")

	try:
		if frappe.db.exists("User", email):
			user = frappe.get_doc("User", email)
			# Update roles if specified
			if roles:
				for role in roles:
					if not user.has_role(role):
						user.add_roles(role)
			return user

		user = frappe.new_doc("User")
		user.email = email
		user.first_name = "Test"
		user.last_name = "User"
		user.send_welcome_email = 0
		user.insert()

		# Add specified roles or default to Website Manager
		if roles:
			user.add_roles(*roles)
		else:
			user.add_roles("Website Manager")

		return user
	finally:
		# Restore original user
		frappe.set_user(current_user)


def create_wiki_manager_user(email: str):
	"""Create a test user with Wiki Manager role."""
	return create_test_user(email, roles=["Wiki Manager"])


class TestWikiDocumentPermissions(FrappeTestCase):
	"""Tests for Wiki Document permission enforcement."""

	def setUp(self):
		frappe.set_user("Administrator")

	def tearDown(self):
		frappe.set_user("Administrator")
		frappe.db.rollback()

	def test_wiki_manager_can_edit_document_directly(self):
		"""Test that Wiki Manager can edit documents directly via API."""
		space = create_test_wiki_space()
		page = create_wiki_document(space.root_group, "Test Page", content="Original content")

		# Create a Wiki Manager user
		manager = create_wiki_manager_user("manager@test.com")
		frappe.set_user(manager.name)

		# Manager should be able to edit the document directly
		page.content = "Updated content"
		page.save()  # Should not raise

		page.reload()
		self.assertEqual(page.content, "Updated content")

	def test_regular_user_cannot_edit_document_directly(self):
		"""Test that regular user cannot edit documents directly."""
		space = create_test_wiki_space()
		page = create_wiki_document(space.root_group, "Test Page", content="Original content")

		# Create a regular user (no Wiki Manager role)
		user = create_test_user("regular@test.com")
		frappe.set_user(user.name)

		# Regular user should NOT be able to edit directly
		page.content = "Hacked content"
		with self.assertRaises(frappe.PermissionError):
			page.save()

	def test_regular_user_cannot_delete_document(self):
		"""Test that regular user cannot delete documents."""
		space = create_test_wiki_space()
		page = create_wiki_document(space.root_group, "Test Page")

		user = create_test_user("deleter@test.com")
		frappe.set_user(user.name)

		with self.assertRaises(frappe.PermissionError):
			page.delete()

	def test_regular_user_cannot_create_document_directly(self):
		"""Test that regular user cannot create documents directly."""
		space = create_test_wiki_space()

		user = create_test_user("creator@test.com")
		frappe.set_user(user.name)

		doc = frappe.new_doc("Wiki Document")
		doc.title = "Unauthorized Page"
		doc.parent_wiki_document = space.root_group
		doc.content = "Content"

		with self.assertRaises(frappe.PermissionError):
			doc.insert()

	def test_wiki_manager_can_create_document(self):
		"""Test that Wiki Manager can create documents."""
		space = create_test_wiki_space()

		manager = create_wiki_manager_user("manager2@test.com")
		frappe.set_user(manager.name)

		doc = frappe.new_doc("Wiki Document")
		doc.title = "Manager Page"
		doc.parent_wiki_document = space.root_group
		doc.content = "Content"
		doc.insert()  # Should not raise

		self.assertTrue(frappe.db.exists("Wiki Document", doc.name))

	def test_wiki_manager_can_delete_document(self):
		"""Test that Wiki Manager can delete documents."""
		space = create_test_wiki_space()
		page = create_wiki_document(space.root_group, "Page to Delete")

		manager = create_wiki_manager_user("manager3@test.com")
		frappe.set_user(manager.name)

		page_name = page.name
		page.delete()  # Should not raise

		self.assertFalse(frappe.db.exists("Wiki Document", page_name))


class TestWikiSpacePermissions(FrappeTestCase):
	"""Tests for Wiki Space permission enforcement."""

	def setUp(self):
		frappe.set_user("Administrator")

	def tearDown(self):
		frappe.set_user("Administrator")
		frappe.db.rollback()

	def test_regular_user_cannot_create_space(self):
		"""Test that regular user cannot create wiki spaces."""
		user = create_test_user("spaceuser@test.com")
		frappe.set_user(user.name)

		root = frappe.new_doc("Wiki Document")
		root.title = "Unauthorized Root"
		root.is_group = 1

		# First, user can't create documents
		with self.assertRaises(frappe.PermissionError):
			root.insert()

	def test_wiki_manager_can_create_space(self):
		"""Test that Wiki Manager can create wiki spaces."""
		manager = create_wiki_manager_user("spacemanager@test.com")
		frappe.set_user(manager.name)

		root = frappe.new_doc("Wiki Document")
		root.title = "Manager Root"
		root.is_group = 1
		root.insert()

		space = frappe.new_doc("Wiki Space")
		space.space_name = "Manager Space"
		space.route = f"manager-space-{frappe.generate_hash(length=6)}"
		space.root_group = root.name
		space.insert()  # Should not raise

		self.assertTrue(frappe.db.exists("Wiki Space", space.name))

	def test_regular_user_cannot_modify_space_settings(self):
		"""Test that regular user cannot modify space settings."""
		space = create_test_wiki_space()

		user = create_test_user("spaceeditor@test.com")
		frappe.set_user(user.name)

		space.space_name = "Hacked Space Name"
		with self.assertRaises(frappe.PermissionError):
			space.save()


class TestContributionBatchWorkflow(FrappeTestCase):
	"""Tests for the contribution batch workflow."""

	def setUp(self):
		frappe.set_user("Administrator")

	def tearDown(self):
		frappe.set_user("Administrator")
		frappe.db.rollback()

	def test_user_can_create_own_batch(self):
		"""Test that a user can create their own contribution batch."""
		space = create_test_wiki_space()
		user = create_test_user("batchuser@test.com")
		frappe.set_user(user.name)

		from wiki.frappe_wiki.doctype.wiki_contribution_batch.wiki_contribution_batch import (
			get_or_create_draft_batch,
		)

		batch = get_or_create_draft_batch(space.name)

		self.assertIsNotNone(batch)
		self.assertEqual(batch["contributor"], user.name)
		self.assertEqual(batch["status"], "Draft")

	def test_user_can_submit_own_batch(self):
		"""Test that a user can submit their own batch for review."""
		space = create_test_wiki_space()
		page = create_wiki_document(space.root_group, "Test Page")

		user = create_test_user("submituser@test.com")
		frappe.set_user(user.name)

		# Create batch and add a contribution
		from wiki.frappe_wiki.doctype.wiki_contribution_batch.wiki_contribution_batch import (
			get_or_create_draft_batch,
			submit_batch,
		)

		batch_data = get_or_create_draft_batch(space.name)

		# Create an edit contribution
		contrib = frappe.new_doc("Wiki Contribution")
		contrib.batch = batch_data["name"]
		contrib.operation = "edit"
		contrib.target_document = page.name
		contrib.proposed_title = "New Title"
		contrib.proposed_content = "New Content"
		contrib.insert()

		# Submit for review
		result = submit_batch(batch_data["name"])

		self.assertEqual(result["status"], "Submitted")

	def test_user_cannot_submit_empty_batch(self):
		"""Test that a user cannot submit an empty batch."""
		space = create_test_wiki_space()
		user = create_test_user("emptysubmit@test.com")
		frappe.set_user(user.name)

		from wiki.frappe_wiki.doctype.wiki_contribution_batch.wiki_contribution_batch import (
			get_or_create_draft_batch,
			submit_batch,
		)

		batch_data = get_or_create_draft_batch(space.name)

		with self.assertRaises(frappe.ValidationError):
			submit_batch(batch_data["name"])

	def test_user_can_withdraw_own_batch(self):
		"""Test that a user can withdraw their own submitted batch."""
		space = create_test_wiki_space()
		page = create_wiki_document(space.root_group, "Test Page")

		user = create_test_user("withdrawuser@test.com")
		frappe.set_user(user.name)

		from wiki.frappe_wiki.doctype.wiki_contribution_batch.wiki_contribution_batch import (
			get_or_create_draft_batch,
			submit_batch,
			withdraw_batch,
		)

		batch_data = get_or_create_draft_batch(space.name)

		# Add contribution and submit
		contrib = frappe.new_doc("Wiki Contribution")
		contrib.batch = batch_data["name"]
		contrib.operation = "edit"
		contrib.target_document = page.name
		contrib.proposed_content = "New Content"
		contrib.insert()

		submit_batch(batch_data["name"])

		# Withdraw
		result = withdraw_batch(batch_data["name"])
		self.assertEqual(result["status"], "Draft")

	def test_user_cannot_submit_others_batch(self):
		"""Test that a user cannot submit another user's batch."""
		space = create_test_wiki_space()

		# User 1 creates a batch
		user1 = create_test_user("owner@test.com")
		frappe.set_user(user1.name)

		from wiki.frappe_wiki.doctype.wiki_contribution_batch.wiki_contribution_batch import (
			get_or_create_draft_batch,
			submit_batch,
		)

		batch_data = get_or_create_draft_batch(space.name)

		# User 2 tries to submit user 1's batch
		user2 = create_test_user("thief@test.com")
		frappe.set_user(user2.name)

		# The submit_batch function throws ValidationError for permission issues
		with self.assertRaises(frappe.ValidationError):
			submit_batch(batch_data["name"])


class TestApproveRejectAPIs(FrappeTestCase):
	"""Tests for the approve/reject contribution APIs."""

	def setUp(self):
		frappe.set_user("Administrator")

	def tearDown(self):
		frappe.set_user("Administrator")
		frappe.db.rollback()

	def test_wiki_manager_can_approve_batch(self):
		"""Test that Wiki Manager can approve a submitted batch."""
		space = create_test_wiki_space()
		page = create_wiki_document(space.root_group, "Test Page", content="Original")

		# User submits a contribution
		user = create_test_user("contributor4@test.com")
		frappe.set_user(user.name)

		from wiki.frappe_wiki.doctype.wiki_contribution_batch.wiki_contribution_batch import (
			get_or_create_draft_batch,
			submit_batch,
		)

		batch_data = get_or_create_draft_batch(space.name)

		contrib = frappe.new_doc("Wiki Contribution")
		contrib.batch = batch_data["name"]
		contrib.operation = "edit"
		contrib.target_document = page.name
		contrib.proposed_content = "Updated by contributor"
		contrib.insert()

		submit_batch(batch_data["name"])

		# Manager approves
		manager = create_wiki_manager_user("approver@test.com")
		frappe.set_user(manager.name)

		from wiki.api.contributions import approve_contribution_batch

		# Should not raise - implicit success
		approve_contribution_batch(batch_data["name"])

		# Verify changes were merged
		page.reload()
		self.assertEqual(page.content, "Updated by contributor")

		# Verify batch status
		batch = frappe.get_doc("Wiki Contribution Batch", batch_data["name"])
		self.assertEqual(batch.status, "Merged")

	def test_wiki_manager_can_reject_batch(self):
		"""Test that Wiki Manager can reject a submitted batch."""
		space = create_test_wiki_space()
		page = create_wiki_document(space.root_group, "Test Page")

		# User submits a contribution
		user = create_test_user("contributor5@test.com")
		frappe.set_user(user.name)

		from wiki.frappe_wiki.doctype.wiki_contribution_batch.wiki_contribution_batch import (
			get_or_create_draft_batch,
			submit_batch,
		)

		batch_data = get_or_create_draft_batch(space.name)

		contrib = frappe.new_doc("Wiki Contribution")
		contrib.batch = batch_data["name"]
		contrib.operation = "edit"
		contrib.target_document = page.name
		contrib.proposed_content = "Bad content"
		contrib.insert()

		submit_batch(batch_data["name"])

		# Manager rejects
		manager = create_wiki_manager_user("rejecter@test.com")
		frappe.set_user(manager.name)

		from wiki.api.contributions import reject_contribution_batch

		# Should not raise - implicit success
		reject_contribution_batch(batch_data["name"], "Please improve the content")

		# Verify batch status and comment
		batch = frappe.get_doc("Wiki Contribution Batch", batch_data["name"])
		self.assertEqual(batch.status, "Rejected")
		self.assertEqual(batch.review_comment, "Please improve the content")

	def test_regular_user_cannot_approve_batch(self):
		"""Test that regular user cannot approve batches."""
		space = create_test_wiki_space()
		page = create_wiki_document(space.root_group, "Test Page")

		# User 1 submits
		user1 = create_test_user("contributor6@test.com")
		frappe.set_user(user1.name)

		from wiki.frappe_wiki.doctype.wiki_contribution_batch.wiki_contribution_batch import (
			get_or_create_draft_batch,
			submit_batch,
		)

		batch_data = get_or_create_draft_batch(space.name)

		contrib = frappe.new_doc("Wiki Contribution")
		contrib.batch = batch_data["name"]
		contrib.operation = "edit"
		contrib.target_document = page.name
		contrib.proposed_content = "Content"
		contrib.insert()

		submit_batch(batch_data["name"])

		# User 2 (non-manager) tries to approve
		user2 = create_test_user("notmanager@test.com")
		frappe.set_user(user2.name)

		from wiki.api.contributions import approve_contribution_batch

		with self.assertRaises(frappe.ValidationError):
			approve_contribution_batch(batch_data["name"])

	def test_regular_user_cannot_reject_batch(self):
		"""Test that regular user cannot reject batches."""
		space = create_test_wiki_space()
		page = create_wiki_document(space.root_group, "Test Page")

		user1 = create_test_user("contributor7@test.com")
		frappe.set_user(user1.name)

		from wiki.frappe_wiki.doctype.wiki_contribution_batch.wiki_contribution_batch import (
			get_or_create_draft_batch,
			submit_batch,
		)

		batch_data = get_or_create_draft_batch(space.name)

		contrib = frappe.new_doc("Wiki Contribution")
		contrib.batch = batch_data["name"]
		contrib.operation = "edit"
		contrib.target_document = page.name
		contrib.proposed_content = "Content"
		contrib.insert()

		submit_batch(batch_data["name"])

		user2 = create_test_user("notmanager2@test.com")
		frappe.set_user(user2.name)

		from wiki.api.contributions import reject_contribution_batch

		with self.assertRaises(frappe.ValidationError):
			reject_contribution_batch(batch_data["name"], "Rejected")


class TestContributionListAPIs(FrappeTestCase):
	"""Tests for the contribution listing APIs."""

	def setUp(self):
		frappe.set_user("Administrator")

	def tearDown(self):
		frappe.set_user("Administrator")
		frappe.db.rollback()

	def test_get_my_contribution_batches_returns_only_own(self):
		"""Test that get_my_contribution_batches only returns user's own batches."""
		space = create_test_wiki_space()

		# User 1 creates a batch
		user1 = create_test_user("listuser1@test.com")
		frappe.set_user(user1.name)

		from wiki.frappe_wiki.doctype.wiki_contribution_batch.wiki_contribution_batch import (
			get_or_create_draft_batch,
		)

		batch1 = get_or_create_draft_batch(space.name)

		# User 2 creates a batch
		user2 = create_test_user("listuser2@test.com")
		frappe.set_user(user2.name)

		batch2 = get_or_create_draft_batch(space.name)

		# User 1 should only see their batch
		frappe.set_user(user1.name)
		from wiki.api.contributions import get_my_contribution_batches

		batches = get_my_contribution_batches()
		batch_names = [b["name"] for b in batches]

		self.assertIn(batch1["name"], batch_names)
		self.assertNotIn(batch2["name"], batch_names)

	def test_get_pending_reviews_requires_wiki_manager(self):
		"""Test that get_pending_reviews requires Wiki Manager role."""
		user = create_test_user("nonmanager@test.com")
		frappe.set_user(user.name)

		from wiki.api.contributions import get_pending_reviews

		with self.assertRaises(frappe.ValidationError):
			get_pending_reviews()

	def test_get_pending_reviews_returns_submitted_batches(self):
		"""Test that get_pending_reviews returns submitted batches for managers."""
		space = create_test_wiki_space()
		page = create_wiki_document(space.root_group, "Test Page")

		# User submits a batch
		user = create_test_user("submitter@test.com")
		frappe.set_user(user.name)

		from wiki.frappe_wiki.doctype.wiki_contribution_batch.wiki_contribution_batch import (
			get_or_create_draft_batch,
			submit_batch,
		)

		batch_data = get_or_create_draft_batch(space.name)

		contrib = frappe.new_doc("Wiki Contribution")
		contrib.batch = batch_data["name"]
		contrib.operation = "edit"
		contrib.target_document = page.name
		contrib.proposed_content = "Content"
		contrib.insert()

		submit_batch(batch_data["name"])

		# Manager checks pending reviews
		manager = create_wiki_manager_user("reviewer@test.com")
		frappe.set_user(manager.name)

		from wiki.api.contributions import get_pending_reviews

		reviews = get_pending_reviews()
		review_names = [r["name"] for r in reviews]

		self.assertIn(batch_data["name"], review_names)

	def test_get_pending_reviews_excludes_draft_batches(self):
		"""Test that get_pending_reviews excludes draft batches."""
		space = create_test_wiki_space()

		# User creates a draft batch (not submitted)
		user = create_test_user("draftholder@test.com")
		frappe.set_user(user.name)

		from wiki.frappe_wiki.doctype.wiki_contribution_batch.wiki_contribution_batch import (
			get_or_create_draft_batch,
		)

		batch_data = get_or_create_draft_batch(space.name)

		# Manager checks pending reviews
		manager = create_wiki_manager_user("reviewer2@test.com")
		frappe.set_user(manager.name)

		from wiki.api.contributions import get_pending_reviews

		reviews = get_pending_reviews()
		review_names = [r["name"] for r in reviews]

		self.assertNotIn(batch_data["name"], review_names)


class TestContributionOperations(FrappeTestCase):
	"""Tests for individual contribution operations (create, edit, delete)."""

	def setUp(self):
		frappe.set_user("Administrator")

	def tearDown(self):
		frappe.set_user("Administrator")
		frappe.db.rollback()

	def test_create_contribution_applies_correctly(self):
		"""Test that a create contribution creates the document on merge."""
		space = create_test_wiki_space()

		user = create_test_user("createuser@test.com")
		frappe.set_user(user.name)

		from wiki.frappe_wiki.doctype.wiki_contribution_batch.wiki_contribution_batch import (
			get_or_create_draft_batch,
			submit_batch,
		)

		batch_data = get_or_create_draft_batch(space.name)

		# Create contribution for a new page
		contrib = frappe.new_doc("Wiki Contribution")
		contrib.batch = batch_data["name"]
		contrib.operation = "create"
		contrib.parent_ref = space.root_group
		contrib.proposed_title = "New Page Created via Contribution"
		contrib.proposed_content = "This is new content"
		contrib.proposed_is_published = 1
		contrib.insert()

		submit_batch(batch_data["name"])

		# Manager approves
		manager = create_wiki_manager_user("mergemanager@test.com")
		frappe.set_user(manager.name)

		from wiki.api.contributions import approve_contribution_batch

		approve_contribution_batch(batch_data["name"])

		# Verify the page was created
		new_page = frappe.db.get_value(
			"Wiki Document",
			{"title": "New Page Created via Contribution", "parent_wiki_document": space.root_group},
			"name",
		)
		self.assertIsNotNone(new_page)

	def test_delete_contribution_applies_correctly(self):
		"""Test that a delete contribution deletes the document on merge."""
		space = create_test_wiki_space()
		page = create_wiki_document(space.root_group, "Page to Delete via Contribution")
		page_name = page.name

		user = create_test_user("deletecontribuser@test.com")
		frappe.set_user(user.name)

		from wiki.frappe_wiki.doctype.wiki_contribution_batch.wiki_contribution_batch import (
			get_or_create_draft_batch,
			submit_batch,
		)

		batch_data = get_or_create_draft_batch(space.name)

		# Create delete contribution
		contrib = frappe.new_doc("Wiki Contribution")
		contrib.batch = batch_data["name"]
		contrib.operation = "delete"
		contrib.target_document = page_name
		contrib.insert()

		submit_batch(batch_data["name"])

		# Manager approves
		manager = create_wiki_manager_user("deletemerger@test.com")
		frappe.set_user(manager.name)

		from wiki.api.contributions import approve_contribution_batch

		approve_contribution_batch(batch_data["name"])

		# Verify the page was deleted
		self.assertFalse(frappe.db.exists("Wiki Document", page_name))

	def test_edit_contribution_detects_conflict(self):
		"""Test that merging an edit contribution fails if the document was modified."""
		space = create_test_wiki_space()
		page = create_wiki_document(space.root_group, "Test Page", content="Original content")

		# Contributor creates an edit contribution
		user = create_test_user("conflictuser@test.com")
		frappe.set_user(user.name)

		from wiki.frappe_wiki.doctype.wiki_contribution_batch.wiki_contribution_batch import (
			get_or_create_draft_batch,
			submit_batch,
		)

		batch_data = get_or_create_draft_batch(space.name)

		contrib = frappe.new_doc("Wiki Contribution")
		contrib.batch = batch_data["name"]
		contrib.operation = "edit"
		contrib.target_document = page.name
		contrib.proposed_content = "Contributor's changes"
		contrib.insert()

		submit_batch(batch_data["name"])

		# Meanwhile, a manager directly modifies the document
		manager = create_wiki_manager_user("directedit@test.com")
		frappe.set_user(manager.name)

		page.reload()
		page.content = "Manager's direct edit - newer content"
		page.save()

		# Now try to approve the contribution - should fail due to conflict
		from wiki.api.contributions import approve_contribution_batch

		with self.assertRaises(frappe.ValidationError) as context:
			approve_contribution_batch(batch_data["name"])

		self.assertIn("Conflict detected", str(context.exception))

	def test_edit_contribution_succeeds_without_conflict(self):
		"""Test that merging an edit contribution succeeds if document unchanged."""
		space = create_test_wiki_space()
		page = create_wiki_document(space.root_group, "Test Page", content="Original content")

		# Contributor creates an edit contribution
		user = create_test_user("noconflictuser@test.com")
		frappe.set_user(user.name)

		from wiki.frappe_wiki.doctype.wiki_contribution_batch.wiki_contribution_batch import (
			get_or_create_draft_batch,
			submit_batch,
		)

		batch_data = get_or_create_draft_batch(space.name)

		contrib = frappe.new_doc("Wiki Contribution")
		contrib.batch = batch_data["name"]
		contrib.operation = "edit"
		contrib.target_document = page.name
		contrib.proposed_content = "Contributor's changes"
		contrib.insert()

		submit_batch(batch_data["name"])

		# Approve without any intermediate changes - should succeed
		manager = create_wiki_manager_user("approver2@test.com")
		frappe.set_user(manager.name)

		from wiki.api.contributions import approve_contribution_batch

		# Should not raise
		approve_contribution_batch(batch_data["name"])

		# Verify the changes were applied
		page.reload()
		self.assertEqual(page.content, "Contributor's changes")

	def test_concurrent_edit_contributions_detect_conflict(self):
		"""Test that when two contributors edit the same page, the second merge fails."""
		space = create_test_wiki_space()
		page = create_wiki_document(space.root_group, "Shared Page", content="Original content")

		# Contributor 1 creates an edit contribution
		user1 = create_test_user("contributor_a@test.com")
		frappe.set_user(user1.name)

		from wiki.frappe_wiki.doctype.wiki_contribution_batch.wiki_contribution_batch import (
			get_or_create_draft_batch,
			submit_batch,
		)

		batch1_data = get_or_create_draft_batch(space.name)

		contrib1 = frappe.new_doc("Wiki Contribution")
		contrib1.batch = batch1_data["name"]
		contrib1.operation = "edit"
		contrib1.target_document = page.name
		contrib1.proposed_content = "Contributor A's changes"
		contrib1.insert()

		submit_batch(batch1_data["name"])

		# Contributor 2 also creates an edit contribution on the same page
		user2 = create_test_user("contributor_b@test.com")
		frappe.set_user(user2.name)

		batch2_data = get_or_create_draft_batch(space.name)

		contrib2 = frappe.new_doc("Wiki Contribution")
		contrib2.batch = batch2_data["name"]
		contrib2.operation = "edit"
		contrib2.target_document = page.name
		contrib2.proposed_content = "Contributor B's changes"
		contrib2.insert()

		submit_batch(batch2_data["name"])

		# Manager approves Contributor 1's batch first
		manager = create_wiki_manager_user("concurrent_approver@test.com")
		frappe.set_user(manager.name)

		from wiki.api.contributions import approve_contribution_batch

		# First approval should succeed
		approve_contribution_batch(batch1_data["name"])

		# Verify Contributor 1's changes were applied
		page.reload()
		self.assertEqual(page.content, "Contributor A's changes")

		# Now try to approve Contributor 2's batch - should fail due to conflict
		with self.assertRaises(frappe.ValidationError) as context:
			approve_contribution_batch(batch2_data["name"])

		self.assertIn("Conflict detected", str(context.exception))
