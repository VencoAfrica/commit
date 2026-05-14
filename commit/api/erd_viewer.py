import frappe
from commit.commit.code_analysis.schema_builder import get_schema_from_doctypes_json
import json


# SECURITY: API CHANGE [M-24] — Removed allow_guest=True. DocType schemas and API structure must not be enumerable by unauthenticated callers.
@frappe.whitelist()
def get_doctype_json(project_branch: str, doctype: str):
    '''
    Get doctype json from a project branch
    '''
    project_branch = frappe.get_cached_doc(
        "Commit Project Branch", project_branch)
    doctype_json = project_branch.get_doctype_json(doctype)
    return doctype_json


# SECURITY: API CHANGE [M-24] — Removed allow_guest=True. DocType schemas and API structure must not be enumerable by unauthenticated callers.
@frappe.whitelist()
def get_erd_schema_for_module(project_branch: str, module: str):
    '''
    Get ERD schema for a module
    '''

    project_branch = frappe.get_cached_doc(
        "Commit Project Branch", project_branch)
    module_doctypes = project_branch.get_doctypes_in_module(module)
    schema = get_erd_schema_for_doctypes(
        project_branch.name, json.dumps(module_doctypes))
    return schema


# SECURITY: API CHANGE [M-24] — Removed allow_guest=True. DocType schemas and API structure must not be enumerable by unauthenticated callers.
@frappe.whitelist()
def get_erd_schema_for_doctypes(project_branch: list, doctypes):
    doctypes = json.loads(doctypes)
    branch_doctypes = {}
    doctype_list = []
    for doctype in doctypes:
        if doctype['project_branch'] not in branch_doctypes:
            branch_doctypes[doctype['project_branch']] = []
        branch_doctypes[doctype['project_branch']].append(doctype['doctype'])
        doctype_list.append(doctype['doctype'])

    doctype_jsons = []
    for project_branch, doctypes in branch_doctypes.items():
        project_branch_doc = frappe.get_cached_doc(
            "Commit Project Branch", project_branch)

        for doctype in doctypes:
            doctype_json = project_branch_doc.get_doctype_json(doctype)
            doctype_jsons.append(doctype_json)

    schema = get_schema_from_doctypes_json({
        'doctypes': doctype_jsons,
        'doctype_names': doctype_list
    })

    return schema

@frappe.whitelist()
def get_meta_erd_schema_for_doctypes(doctypes):
    '''
    Get ERD schema for a list of doctypes
    '''
    # Debug logging
    print(f"DEBUG: doctypes received = {doctypes}, type = {type(doctypes)}")
    print(f"DEBUG: form_dict = {frappe.form_dict}")

    # Handle different input formats from frontend
    if doctypes is None:
        doctypes = []
    elif isinstance(doctypes, str):
        if not doctypes:
            doctypes = []
        else:
            try:
                doctypes = json.loads(doctypes)
            except json.JSONDecodeError:
                # If not valid JSON, treat as single doctype name
                doctypes = [doctypes]
    elif not isinstance(doctypes, list):
        doctypes = [doctypes]

    print(f"DEBUG: doctypes after parsing = {doctypes}")

    if not doctypes:
        return {'tables': [], 'relationships': []}

    doctype_jsons = []
    for doctype in doctypes:
        doctype_json = frappe.get_meta(doctype)
        doctype_jsons.append(doctype_json)

    schema = get_schema_from_doctypes_json({
        'doctypes': doctype_jsons,
        'doctype_names': doctypes
    })

    return schema

@frappe.whitelist()
def get_meta_for_doctype(doctype):
    '''
    Get meta for a doctype
    '''
    return frappe.get_meta(doctype)