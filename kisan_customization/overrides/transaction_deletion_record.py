# Copyright (c) 2026, Hidayatali and contributors

import frappe
from erpnext.setup.doctype.transaction_deletion_record.transaction_deletion_record import (
	TransactionDeletionRecord,
)

from kisan_customization.setup.company_master_data import get_company_master_doctypes


class KisanTransactionDeletionRecord(TransactionDeletionRecord):
	"""Never delete or touch Kisan configuration masters during company transaction wipe."""

	def get_doctypes_to_be_ignored_list(self):
		ignored = super().get_doctypes_to_be_ignored_list()
		for doctype in get_company_master_doctypes():
			if doctype not in ignored:
				ignored.append(doctype)
		return ignored

	def delete_company_transactions(self):
		self.validate_doc_status()
		if self.delete_transactions:
			return

		protected = frozenset(get_company_master_doctypes())
		doctypes_to_be_ignored_list = self.get_doctypes_to_be_ignored_list()
		self.get_doctypes_with_company_field(doctypes_to_be_ignored_list)
		self.get_all_child_doctypes()

		for docfield in self.doctypes:
			if docfield.doctype_name != self.doctype and not docfield.done:
				if docfield.doctype_name in protected:
					frappe.db.set_value(docfield.doctype, docfield.name, "done", 1)
					continue

				no_of_docs = self.get_number_of_docs_linked_with_specified_company(
					docfield.doctype_name, docfield.docfield_name
				)
				if no_of_docs > 0:
					reference_docs = frappe.get_all(
						docfield.doctype_name,
						filters={docfield.docfield_name: self.company},
						limit=self.batch_size,
					)
					reference_doc_names = [r.name for r in reference_docs]

					self.delete_version_log(docfield.doctype_name, reference_doc_names)
					self.delete_communications(docfield.doctype_name, reference_doc_names)
					self.delete_comments(docfield.doctype_name, reference_doc_names)
					self.unlink_attachments(docfield.doctype_name, reference_doc_names)
					self.delete_child_tables(docfield.doctype_name, reference_doc_names)
					self.delete_docs_linked_with_specified_company(
						docfield.doctype_name, reference_doc_names
					)
					processed = int(docfield.no_of_docs) + len(reference_doc_names)
					frappe.db.set_value(docfield.doctype, docfield.name, "no_of_docs", processed)
				else:
					naming_series = frappe.db.get_value("DocType", docfield.doctype_name, "autoname")
					if naming_series:
						if "#" in naming_series:
							self.update_naming_series(naming_series, docfield.doctype_name)
					frappe.db.set_value(docfield.doctype, docfield.name, "done", 1)

		pending_doctypes = frappe.db.get_all(
			"Transaction Deletion Record Details",
			filters={"parent": self.name, "done": 0},
			pluck="doctype_name",
		)
		if pending_doctypes:
			self.enqueue_task(task="Delete Transactions")
		else:
			self.db_set("status", "Completed")
			self.db_set("delete_transactions", 1)
			self.db_set("error_log", None)
