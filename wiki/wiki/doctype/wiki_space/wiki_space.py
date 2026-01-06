# Copyright (c) 2023, Frappe and contributors
# For license information, please see license.txt
import frappe
from frappe.model.document import Document


class WikiSpace(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF
		from frappe.website.doctype.top_bar_item.top_bar_item import TopBarItem

		from wiki.wiki.doctype.wiki_group_item.wiki_group_item import WikiGroupItem

		app_switcher_logo: DF.AttachImage | None
		dark_mode_logo: DF.AttachImage | None
		enable_feedback_collection: DF.Check
		favicon: DF.AttachImage | None
		is_published: DF.Check
		light_mode_logo: DF.AttachImage | None
		navbar_items: DF.Table[TopBarItem]
		root_group: DF.Link | None
		route: DF.Data
		show_in_switcher: DF.Check
		space_name: DF.Data | None
		wiki_sidebars: DF.Table[WikiGroupItem]
	# end: auto-generated types

	def before_insert(self):
		self.create_root_group()

	def validate(self):
		self.remove_leading_slash_from_route()

	def remove_leading_slash_from_route(self):
		if self.route and self.route.startswith("/"):
			self.route = self.route[1 : len(self.route)]

	def create_root_group(self):
		if not self.root_group:
			root_group = frappe.get_doc(
				{
					"doctype": "Wiki Document",
					"title": f"{self.space_name} [Root Group]",
					"route": f"/{self.route}",
					"is_group": 1,
					"published": 0,
					"content": "[root_group]",
				}
			)
			root_group.insert()
			self.root_group = root_group.name

	@frappe.whitelist()
	def migrate_to_v3(self):
		if self.root_group:
			return  # Migration already done

		self.create_root_group()
		self.save()

		sidebar = self.wiki_sidebars
		if not sidebar:
			return

		groups, group_order = self._group_sidebar_items(sidebar)

		for sort_order, group_label in enumerate(group_order):
			self._create_group_with_pages(group_label, groups[group_label], sort_order)

		self.save()

	def _group_sidebar_items(self, sidebar):
		"""Group sidebar items by parent_label while maintaining order"""
		groups = {}
		group_order = []
		for item in sorted(sidebar, key=lambda x: x.idx):
			if item.parent_label not in groups:
				groups[item.parent_label] = []
				group_order.append(item.parent_label)
			groups[item.parent_label].append(item)
		return groups, group_order

	def _create_group_with_pages(self, group_label, items, sort_order):
		"""Create a group Wiki Document and its child page documents"""
		group_doc = frappe.get_doc(
			{
				"doctype": "Wiki Document",
				"title": group_label,
				"route": f"{self.route}/{frappe.scrub(group_label).replace('_', '-')}",
				"is_group": 1,
				"is_published": 1,
				"content": "",
				"parent_wiki_document": self.root_group,
				"sort_order": sort_order,
			}
		)
		group_doc.insert(ignore_permissions=True)

		for page_sort_order, item in enumerate(items):
			self._create_page_document(item.wiki_page, group_doc.name, page_sort_order)

	def _create_page_document(self, wiki_page_name, parent_group, sort_order):
		"""Create a leaf Wiki Document from a Wiki Page"""
		wiki_page = frappe.get_cached_doc("Wiki Page", wiki_page_name)
		leaf_doc = frappe.get_doc(
			{
				"doctype": "Wiki Document",
				"title": wiki_page.title,
				"route": wiki_page.route,
				"is_group": 0,
				"is_published": wiki_page.published,
				"is_private": not wiki_page.allow_guest,
				"content": wiki_page.content,
				"parent_wiki_document": parent_group,
				"sort_order": sort_order,
			}
		)
		leaf_doc.insert(ignore_permissions=True)
