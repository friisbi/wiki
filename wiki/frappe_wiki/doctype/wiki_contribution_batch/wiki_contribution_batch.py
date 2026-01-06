# Copyright (c) 2025, Frappe and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import now_datetime


class WikiContributionBatch(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		contributor: DF.Link | None
		description: DF.SmallText | None
		review_comment: DF.Text | None
		reviewed_at: DF.Datetime | None
		reviewed_by: DF.Link | None
		status: DF.Literal["Draft", "Submitted", "Under Review", "Approved", "Rejected", "Merged"]
		submitted_at: DF.Datetime | None
		title: DF.Data
		wiki_space: DF.Link
	# end: auto-generated types

	def validate(self):
		self.validate_status_transition()

	def validate_status_transition(self):
		"""Validate that status transitions are valid."""
		if self.is_new():
			return

		old_status = self.get_doc_before_save().status if self.get_doc_before_save() else None
		if not old_status:
			return

		valid_transitions = {
			"Draft": ["Submitted"],
			"Submitted": [
				"Under Review",
				"Approved",
				"Rejected",
				"Draft",
			],  # Can approve/reject directly or start review
			"Under Review": ["Approved", "Rejected", "Draft"],  # Reviewer can send back
			"Approved": ["Merged"],
			"Rejected": ["Draft"],  # Contributor can revise and try again
			"Merged": [],  # Terminal state
		}

		if self.status != old_status and self.status not in valid_transitions.get(old_status, []):
			frappe.throw(
				_("Cannot transition from {0} to {1}").format(old_status, self.status),
				frappe.ValidationError,
			)

	def before_save(self):
		if self.status == "Submitted" and not self.submitted_at:
			self.submitted_at = now_datetime()

	def submit_for_review(self):
		"""Submit this batch for review."""
		if self.status != "Draft":
			frappe.throw(_("Only draft batches can be submitted for review"))

		# Check if there are any contributions
		contribution_count = frappe.db.count("Wiki Contribution", {"batch": self.name})
		if contribution_count == 0:
			frappe.throw(_("Cannot submit an empty batch. Add at least one contribution."))

		self.status = "Submitted"
		self.submitted_at = now_datetime()
		self.save()

		return self

	def withdraw(self):
		"""Withdraw a submitted batch back to draft."""
		if self.status not in ["Submitted", "Under Review"]:
			frappe.throw(_("Only submitted or under review batches can be withdrawn"))

		self.status = "Draft"
		self.submitted_at = None
		self.save()

		return self

	def start_review(self):
		"""Mark batch as under review."""
		if self.status != "Submitted":
			frappe.throw(_("Only submitted batches can be reviewed"))

		self.status = "Under Review"
		self.save()

		return self

	def approve(self, comment: str | None = None):
		"""Approve this batch."""
		if self.status not in ["Submitted", "Under Review"]:
			frappe.throw(_("Only submitted or under review batches can be approved"))

		self.status = "Approved"
		self.reviewed_by = frappe.session.user
		self.reviewed_at = now_datetime()
		if comment:
			self.review_comment = comment
		self.save()

		return self

	def reject(self, comment: str | None = None):
		"""Reject this batch."""
		if self.status not in ["Submitted", "Under Review"]:
			frappe.throw(_("Only submitted or under review batches can be rejected"))

		self.status = "Rejected"
		self.reviewed_by = frappe.session.user
		self.reviewed_at = now_datetime()
		if comment:
			self.review_comment = comment
		self.save()

		return self

	def get_contributions(self) -> list:
		"""Get all contributions in this batch, ordered by sequence."""
		return frappe.get_all(
			"Wiki Contribution",
			filters={"batch": self.name},
			fields=["*"],
			order_by="sequence asc",
		)

	def merge(self):
		"""
		Merge all approved contributions into the live Wiki Document tree.
		This is the main operation that applies all changes.
		"""
		if self.status != "Approved":
			frappe.throw(_("Only approved batches can be merged"))

		contributions = self.get_contributions()
		if not contributions:
			frappe.throw(_("No contributions to merge"))

		# Map temp_ids to real document names as we create them
		temp_to_real = {}

		for contrib in contributions:
			contrib_doc = frappe.get_doc("Wiki Contribution", contrib.name)
			contrib_doc.apply(temp_to_real)

		# Mark batch as merged
		self.status = "Merged"
		self.save()

		# Rebuild the NSM tree to ensure consistency
		frappe.db.auto_commit_on_many_writes = True
		try:
			from frappe.utils.nestedset import rebuild_tree

			rebuild_tree("Wiki Document")
		finally:
			frappe.db.auto_commit_on_many_writes = False

		return self


@frappe.whitelist()
def get_or_create_draft_batch(wiki_space: str, title: str | None = None) -> dict:
	"""
	Get an existing draft batch for the current user and space,
	or create a new one if none exists.
	"""
	existing_batch = frappe.db.get_value(
		"Wiki Contribution Batch",
		{
			"wiki_space": wiki_space,
			"contributor": frappe.session.user,
			"status": "Draft",
		},
		"name",
	)

	if existing_batch:
		return frappe.get_doc("Wiki Contribution Batch", existing_batch).as_dict()

	# Create new batch
	batch = frappe.new_doc("Wiki Contribution Batch")
	batch.wiki_space = wiki_space
	batch.title = title or _("Contribution by {0}").format(frappe.session.user)
	batch.contributor = frappe.session.user
	batch.status = "Draft"
	batch.insert()

	return batch.as_dict()


@frappe.whitelist()
def submit_batch(batch_name: str) -> dict:
	"""Submit a batch for review."""
	batch = frappe.get_doc("Wiki Contribution Batch", batch_name)

	# Check permission
	if batch.contributor != frappe.session.user and not frappe.has_permission(
		"Wiki Contribution Batch", "write"
	):
		frappe.throw(_("You don't have permission to submit this batch"))

	batch.submit_for_review()
	return batch.as_dict()


@frappe.whitelist()
def withdraw_batch(batch_name: str) -> dict:
	"""Withdraw a submitted batch."""
	batch = frappe.get_doc("Wiki Contribution Batch", batch_name)

	# Check permission
	if batch.contributor != frappe.session.user and not frappe.has_permission(
		"Wiki Contribution Batch", "write"
	):
		frappe.throw(_("You don't have permission to withdraw this batch"))

	batch.withdraw()
	return batch.as_dict()


@frappe.whitelist()
def approve_batch(batch_name: str, comment: str | None = None) -> dict:
	"""Approve a batch (Wiki Manager only)."""
	if not frappe.has_permission("Wiki Contribution Batch", "write"):
		frappe.throw(_("You don't have permission to approve batches"))

	batch = frappe.get_doc("Wiki Contribution Batch", batch_name)
	batch.approve(comment)
	return batch.as_dict()


@frappe.whitelist()
def reject_batch(batch_name: str, comment: str | None = None) -> dict:
	"""Reject a batch (Wiki Manager only)."""
	if not frappe.has_permission("Wiki Contribution Batch", "write"):
		frappe.throw(_("You don't have permission to reject batches"))

	batch = frappe.get_doc("Wiki Contribution Batch", batch_name)
	batch.reject(comment)
	return batch.as_dict()


@frappe.whitelist()
def merge_batch(batch_name: str) -> dict:
	"""Merge an approved batch (Wiki Manager only)."""
	if not frappe.has_permission("Wiki Contribution Batch", "write"):
		frappe.throw(_("You don't have permission to merge batches"))

	batch = frappe.get_doc("Wiki Contribution Batch", batch_name)
	batch.merge()
	return batch.as_dict()


@frappe.whitelist()
def get_my_batches(status: str | None = None) -> list:
	"""Get all batches for the current user."""
	filters = {"contributor": frappe.session.user}
	if status:
		filters["status"] = status

	return frappe.get_all(
		"Wiki Contribution Batch",
		filters=filters,
		fields=["name", "title", "wiki_space", "status", "creation", "submitted_at"],
		order_by="modified desc",
	)


@frappe.whitelist()
def get_pending_batches() -> list:
	"""Get all batches pending review (for reviewers)."""
	if not frappe.has_permission("Wiki Contribution Batch", "write"):
		frappe.throw(_("You don't have permission to view pending batches"))

	return frappe.get_all(
		"Wiki Contribution Batch",
		filters={"status": ["in", ["Submitted", "Under Review"]]},
		fields=["name", "title", "wiki_space", "status", "contributor", "submitted_at"],
		order_by="submitted_at asc",
	)
