import frappe
from frappe import _
from frappe.utils.nestedset import get_descendants_of


@frappe.whitelist()
def get_wiki_tree(space_id: str) -> dict:
	"""Get the tree structure of Wiki Documents for a given Wiki Space."""
	space = frappe.get_cached_doc("Wiki Space", space_id)
	space.check_permission("read")

	if not space.root_group:
		return {"children": [], "root_group": None}

	root_group = space.root_group
	descendants = get_descendants_of("Wiki Document", root_group, ignore_permissions=True)

	if not descendants:
		return {"children": [], "root_group": root_group}

	tree = _build_wiki_tree_for_api(descendants)
	return {"children": tree, "root_group": root_group}


def _build_wiki_tree_for_api(documents: list[str]) -> list[dict]:
	"""Build a nested tree structure from a list of Wiki Document names."""
	wiki_documents = frappe.db.get_all(
		"Wiki Document",
		fields=["name", "title", "is_group", "parent_wiki_document", "route", "is_published"],
		filters={"name": ("in", documents)},
		order_by="lft asc",
	)

	doc_map = {doc["name"]: {**doc, "label": doc["title"], "children": []} for doc in wiki_documents}

	root_nodes = []
	for doc in wiki_documents:
		parent_name = doc["parent_wiki_document"]
		if parent_name and parent_name in doc_map:
			doc_map[parent_name]["children"].append(doc_map[doc["name"]])
		else:
			root_nodes.append(doc_map[doc["name"]])

	return root_nodes


@frappe.whitelist()
def reorder_wiki_documents(
	doc_name: str,
	new_parent: str | None,
	new_index: int,
	siblings: str,
	batch: str | None = None,
):
	"""
	Reorder a Wiki Document by changing its parent and/or position among siblings.

	Args:
			doc_name: The name of the document being moved (can be a temp_id for draft items)
			new_parent: The new parent document name (can be None for root level)
			new_index: The new index position among siblings
			siblings: JSON string of sibling document names in the new order
			batch: Optional batch name for contribution mode

	Returns:
			For contribution mode: dict with contribution and batch info
			For direct reorder: None (implicit success)
	"""
	import json

	siblings_list = json.loads(siblings) if isinstance(siblings, str) else siblings

	# Check if this is a draft item (temp_id from a contribution)
	if doc_name.startswith("temp_"):
		return _update_draft_item_parent(doc_name, new_parent, new_index, siblings_list)

	doc = frappe.get_doc("Wiki Document", doc_name)

	# Check if user has write permission
	has_write_permission = frappe.has_permission("Wiki Document", "write", doc=doc)

	# If batch is provided or user doesn't have write permission, create a contribution
	if batch or not has_write_permission:
		return _create_reorder_contribution(doc, new_parent, new_index, siblings_list, batch)

	# Direct reorder for users with write permission
	# Update parent if changed
	if doc.parent_wiki_document != new_parent:
		doc.parent_wiki_document = new_parent
		doc.save()

	# Update the sort_order for all siblings based on the new order
	for idx, sibling_name in enumerate(siblings_list):
		# Skip temp items (drafts) - they don't exist in the database
		if sibling_name.startswith("temp_"):
			continue
		frappe.db.set_value("Wiki Document", sibling_name, "sort_order", idx, update_modified=False)

	# Rebuild the nested set tree with custom ordering by idx
	rebuild_wiki_tree()


def _create_reorder_contribution(
	doc, new_parent: str | None, new_index: int, siblings: list, batch: str | None
) -> dict:
	"""Create a reorder/move contribution for contribution mode."""
	import json

	from wiki.frappe_wiki.doctype.wiki_contribution_batch.wiki_contribution_batch import (
		get_or_create_draft_batch,
	)

	# Get the wiki space from the document's hierarchy
	wiki_space = _get_wiki_space_for_document(doc.name)
	if not wiki_space:
		frappe.throw(_("Could not determine wiki space for this document"))

	# Get or create batch if not provided
	if not batch:
		batch_doc = get_or_create_draft_batch(wiki_space)
		batch = batch_doc.get("name")

	# Determine if this is a move (parent change) or just a reorder
	is_move = doc.parent_wiki_document != new_parent
	operation = "move" if is_move else "reorder"

	# Create the contribution
	contrib = frappe.new_doc("Wiki Contribution")
	contrib.batch = batch
	contrib.operation = operation
	contrib.target_document = doc.name

	if is_move:
		contrib.new_parent_ref = new_parent
		contrib.new_sort_order = new_index
	else:
		contrib.proposed_sort_order = new_index

	# Store the full siblings order so we can reconstruct the order during merge
	contrib.siblings_order = json.dumps(siblings)

	contrib.insert()

	return {
		"contribution": contrib.name,
		"batch": batch,
		"is_contribution": True,
	}


def _update_draft_item_parent(temp_id: str, new_parent: str | None, new_index: int, siblings: list) -> dict:
	"""Update the parent_ref of a draft contribution (for moving draft items)."""
	import json

	# Find the contribution with this temp_id
	contrib = frappe.db.get_value(
		"Wiki Contribution",
		{"temp_id": temp_id},
		["name", "parent_ref"],
		as_dict=True,
	)

	if not contrib:
		frappe.throw(_("Draft contribution not found"))

	# Update the parent_ref, sort order, and siblings order on the contribution
	frappe.db.set_value(
		"Wiki Contribution",
		contrib.name,
		{
			"parent_ref": new_parent,
			"proposed_sort_order": new_index,
			"siblings_order": json.dumps(siblings),
		},
	)

	return {"is_contribution": True}


def _get_wiki_space_for_document(doc_name: str) -> str | None:
	"""Get the wiki space that contains this document."""
	# Walk up the tree to find a document that's a root_group for a space
	current = doc_name
	visited = set()

	while current and current not in visited:
		visited.add(current)

		# Check if this document is the root_group of any space
		space = frappe.db.get_value("Wiki Space", {"root_group": current}, "name")
		if space:
			return space

		# Move up to parent
		current = frappe.db.get_value("Wiki Document", current, "parent_wiki_document")

	return None


def rebuild_wiki_tree():
	"""Rebuild the Wiki Document tree ordering siblings by sort_order field."""
	from frappe.query_builder import Order
	from frappe.query_builder.functions import Coalesce

	doctype = "Wiki Document"
	parent_field = "parent_wiki_document"
	table = frappe.qb.DocType(doctype)

	# Get all root nodes (no parent), ordered by sort_order then name
	roots = (
		frappe.qb.from_(table)
		.where((table.parent_wiki_document == "") | (table.parent_wiki_document.isnull()))
		.orderby(Coalesce(table.sort_order, 0), order=Order.asc)
		.orderby(table.name, order=Order.asc)
		.select(table.name)
	).run(pluck="name")

	frappe.db.auto_commit_on_many_writes = 1

	right = 1
	for root in roots:
		right = _rebuild_wiki_node(doctype, root, right, parent_field)

	frappe.db.auto_commit_on_many_writes = 0


def _rebuild_wiki_node(doctype: str, name: str, left: int, parent_field: str) -> int:
	"""Rebuild a single node and its children, ordering by sort_order."""
	from frappe.query_builder import Order
	from frappe.query_builder.functions import Coalesce

	right = left + 1
	table = frappe.qb.DocType(doctype)
	parent_col = getattr(table, parent_field)

	# Get children ordered by sort_order then name
	children = (
		frappe.qb.from_(table)
		.where(parent_col == name)
		.orderby(Coalesce(table.sort_order, 0), order=Order.asc)
		.orderby(table.name, order=Order.asc)
		.select(table.name)
	).run(pluck="name")

	for child in children:
		right = _rebuild_wiki_node(doctype, child, right, parent_field)

	# Update lft and rgt
	frappe.db.set_value(doctype, name, {"lft": left, "rgt": right}, update_modified=False)

	return right + 1
