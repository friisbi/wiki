import frappe
from frappe.translate import get_all_translations
from frappe.utils.nestedset import get_descendants_of


@frappe.whitelist()
def get_user_info() -> dict:
	"""Get basic information about the logged-in user."""
	if frappe.session.user == "Guest":
		return {"is_logged_in": False}

	user = frappe.get_cached_doc("User", frappe.session.user)

	return {
		"name": user.name,
		"is_logged_in": True,
		"first_name": user.first_name,
		"last_name": user.last_name,
		"full_name": user.full_name,
		"email": user.email,
		"user_image": user.user_image,
		"roles": user.roles,
		"brand_image": frappe.get_single_value("Website Settings", "banner_image"),
		"language": user.language,
	}


@frappe.whitelist(allow_guest=True)
def get_translations():
	if frappe.session.user != "Guest":
		language = frappe.db.get_value("User", frappe.session.user, "language")
	else:
		language = frappe.db.get_single_value("System Settings", "language")

	return get_all_translations(language)


@frappe.whitelist()
def get_wiki_tree(space_id: str) -> dict:
	"""Get the tree structure of Wiki Documents for a given Wiki Space."""
	space = frappe.get_cached_doc("Wiki Space", space_id)
	space.check_permission("read")

	if not space.root_group:
		return {"children": [], "root_group": None}

	root_group = space.root_group
	descendants = get_descendants_of("Wiki Document", root_group)

	if not descendants:
		return {"children": [], "root_group": root_group}

	tree = build_wiki_tree_for_api(descendants)
	return {"children": tree, "root_group": root_group}


def build_wiki_tree_for_api(documents: list[str]) -> list[dict]:
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
def reorder_wiki_documents(doc_name: str, new_parent: str | None, new_index: int, siblings: str) -> dict:
	"""
	Reorder a Wiki Document by changing its parent and/or position among siblings.

	Args:
			doc_name: The name of the document being moved
			new_parent: The new parent document name (can be None for root level)
			new_index: The new index position among siblings
			siblings: JSON string of sibling document names in the new order

	Returns:
			dict with success status
	"""
	import json

	siblings_list = json.loads(siblings) if isinstance(siblings, str) else siblings

	doc = frappe.get_doc("Wiki Document", doc_name)
	doc.check_permission("write")

	# Update parent if changed
	if doc.parent_wiki_document != new_parent:
		doc.parent_wiki_document = new_parent
		doc.save()

	# Update the sort_order for all siblings based on the new order
	for idx, sibling_name in enumerate(siblings_list):
		frappe.db.set_value("Wiki Document", sibling_name, "sort_order", idx, update_modified=False)

	# Rebuild the nested set tree with custom ordering by idx
	rebuild_wiki_tree()

	return {"success": True, "message": "Document reordered successfully"}


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
		right = rebuild_wiki_node(doctype, root, right, parent_field)

	frappe.db.auto_commit_on_many_writes = 0


def rebuild_wiki_node(doctype: str, name: str, left: int, parent_field: str) -> int:
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
		right = rebuild_wiki_node(doctype, child, right, parent_field)

	# Update lft and rgt
	frappe.db.set_value(doctype, name, {"lft": left, "rgt": right}, update_modified=False)

	return right + 1
