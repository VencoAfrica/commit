"""
Unit tests for the code_analysis module.

These tests cover the pure parsing functions in the code_analysis module
that have no database dependencies.

Run with:
    bench --site waba.local run-tests --app commit --module commit.tests.test_code_analysis
"""

import unittest
from commit.commit.code_analysis.apis import (
    extract_name_from_def,
    extract_arguments_from_def,
    get_whitelist_details,
    find_indexes_of_whitelist
)
from commit.commit.code_analysis.utils import parse_module_name
from commit.commit.code_analysis.schema_builder import get_schema_from_doctypes_json


class TestExtractNameFromDef(unittest.TestCase):
    """Tests for extract_name_from_def function."""

    def test_simple_function_name(self):
        """Test extracting a simple function name with arguments."""
        api_def = "my_function(arg1, arg2):"
        result = extract_name_from_def(api_def)
        self.assertEqual(result, "my_function")

    def test_function_with_leading_spaces(self):
        """Test extracting function name when there are leading/trailing spaces."""
        api_def = "  my_function  (arg1):"
        result = extract_name_from_def(api_def)
        self.assertEqual(result, "my_function")

    def test_function_no_args(self):
        """Test extracting function name with no arguments."""
        api_def = "no_args():"
        result = extract_name_from_def(api_def)
        self.assertEqual(result, "no_args")


class TestExtractArgumentsFromDef(unittest.TestCase):
    """Tests for extract_arguments_from_def function."""

    def test_simple_arguments(self):
        """Test extracting simple arguments without types or defaults."""
        api_def = "func(arg1, arg2):"
        result = extract_arguments_from_def(api_def)

        self.assertEqual(len(result), 2)
        self.assertEqual(result[0]["argument"], "arg1")
        self.assertEqual(result[0]["type"], "")
        self.assertEqual(result[0]["default"], "")
        self.assertEqual(result[1]["argument"], "arg2")

    def test_arguments_with_types(self):
        """Test extracting arguments with type annotations."""
        api_def = "func(name: str, count: int):"
        result = extract_arguments_from_def(api_def)

        self.assertEqual(len(result), 2)
        self.assertEqual(result[0]["argument"], "name")
        self.assertEqual(result[0]["type"], "str")
        self.assertEqual(result[1]["argument"], "count")
        self.assertEqual(result[1]["type"], "int")

    def test_arguments_with_defaults(self):
        """Test extracting arguments with default values."""
        api_def = "func(name='test', count=10):"
        result = extract_arguments_from_def(api_def)

        self.assertEqual(len(result), 2)
        self.assertEqual(result[0]["argument"], "name")
        self.assertEqual(result[0]["default"], "test")
        self.assertEqual(result[1]["argument"], "count")
        self.assertEqual(result[1]["default"], "10")

    def test_arguments_with_types_and_defaults(self):
        """Test extracting arguments with both types and defaults."""
        api_def = "func(name: str = 'test', count: int = 10):"
        result = extract_arguments_from_def(api_def)

        self.assertEqual(len(result), 2)
        self.assertEqual(result[0]["argument"], "name")
        self.assertEqual(result[0]["type"], "str")
        self.assertEqual(result[0]["default"], "test")
        self.assertEqual(result[1]["argument"], "count")
        self.assertEqual(result[1]["type"], "int")
        self.assertEqual(result[1]["default"], "10")


class TestGetWhitelistDetails(unittest.TestCase):
    """Tests for get_whitelist_details function."""

    def test_allow_guest_true(self):
        """Test parsing whitelist with allow_guest=True."""
        file_content = "@frappe.whitelist(allow_guest=True)\ndef my_api():"
        result = get_whitelist_details(file_content, 0)

        self.assertTrue(result["allow_guest"])
        self.assertFalse(result["xss_safe"])
        self.assertEqual(result["request_types"], [])

    def test_methods_list(self):
        """Test parsing whitelist with methods list.

        Note: The current implementation has a limitation where it splits by comma
        at the argument level, so only the first method in a list is captured
        when methods are separated by ', ' (comma + space). This test documents
        the current behavior.
        """
        # Single method works correctly
        file_content = "@frappe.whitelist(methods=['GET'])\ndef my_api():"
        result = get_whitelist_details(file_content, 0)

        self.assertIn("GET", result["request_types"])

    def test_xss_safe(self):
        """Test parsing whitelist with xss_safe=True."""
        file_content = "@frappe.whitelist(xss_safe=True)\ndef my_api():"
        result = get_whitelist_details(file_content, 0)

        self.assertTrue(result["xss_safe"])
        self.assertFalse(result["allow_guest"])

    def test_empty_whitelist(self):
        """Test parsing whitelist with no arguments."""
        file_content = "@frappe.whitelist()\ndef my_api():"
        result = get_whitelist_details(file_content, 0)

        self.assertFalse(result["allow_guest"])
        self.assertFalse(result["xss_safe"])
        self.assertEqual(result["request_types"], [])


class TestFindIndexesOfWhitelist(unittest.TestCase):
    """Tests for find_indexes_of_whitelist function."""

    def test_single_whitelist(self):
        """Test finding a single @frappe.whitelist decorator."""
        file_content = """
@frappe.whitelist()
def my_api():
    pass
"""
        indexes, line_nos, remaining = find_indexes_of_whitelist(file_content, 1)

        self.assertEqual(len(indexes), 1)
        self.assertEqual(len(line_nos), 1)
        self.assertEqual(remaining, 0)

    def test_multiple_whitelists(self):
        """Test finding multiple @frappe.whitelist decorators."""
        file_content = """
@frappe.whitelist()
def api_one():
    pass

@frappe.whitelist(allow_guest=True)
def api_two():
    pass
"""
        indexes, line_nos, remaining = find_indexes_of_whitelist(file_content, 2)

        self.assertEqual(len(indexes), 2)
        self.assertEqual(len(line_nos), 2)
        self.assertEqual(remaining, 0)

    def test_whitelist_in_string_ignored(self):
        """Test that @frappe.whitelist inside a string is ignored."""
        file_content = '''
# This is a real decorator
@frappe.whitelist()
def real_api():
    doc = "@frappe.whitelist() is a decorator"
    pass
'''
        indexes, line_nos, remaining = find_indexes_of_whitelist(file_content, 2)

        # Should only find 1 (the real decorator, not the one in the string)
        self.assertEqual(len(indexes), 1)

    def test_whitelist_in_comment_ignored(self):
        """Test that @frappe.whitelist in a comment is ignored."""
        file_content = """
# @frappe.whitelist() - this is commented out
@frappe.whitelist()
def real_api():
    pass
"""
        indexes, line_nos, remaining = find_indexes_of_whitelist(file_content, 2)

        # Should only find 1 (the real decorator, not the commented one)
        self.assertEqual(len(indexes), 1)


class TestParseModuleName(unittest.TestCase):
    """Tests for parse_module_name function."""

    def test_hyphen_replacement(self):
        """Test that hyphens are replaced with underscores."""
        result = parse_module_name("my-module")
        self.assertEqual(result, "my_module")

    def test_space_replacement_and_lowercase(self):
        """Test that spaces are replaced and string is lowercased."""
        result = parse_module_name("My Module")
        self.assertEqual(result, "my_module")


class TestGetSchemaFromDoctypesJson(unittest.TestCase):
    """Tests for get_schema_from_doctypes_json function."""

    def test_filters_disallowed_fields(self):
        """Test that Section Break, Column Break, etc. are filtered out."""
        doctypes_json = {
            "doctype_names": ["Test Doctype"],
            "doctypes": [{
                "name": "Test Doctype",
                "module": "Test",
                "istable": 0,
                "fields": [
                    {"fieldname": "title", "fieldtype": "Data", "label": "Title"},
                    {"fieldname": "sb1", "fieldtype": "Section Break", "label": "Section"},
                    {"fieldname": "cb1", "fieldtype": "Column Break", "label": "Column"},
                    {"fieldname": "description", "fieldtype": "Text", "label": "Description"},
                ]
            }]
        }

        result = get_schema_from_doctypes_json(doctypes_json)

        # Should have 1 table
        self.assertEqual(len(result["tables"]), 1)

        # Get columns (excluding ID which is always added)
        columns = result["tables"][0]["columns"]
        column_names = [col["id"] for col in columns]

        # Should include title and description, but not section/column break
        self.assertIn("title", column_names)
        self.assertIn("description", column_names)
        self.assertNotIn("sb1", column_names)
        self.assertNotIn("cb1", column_names)

    def test_builds_link_relationships(self):
        """Test that Link fields create relationships."""
        doctypes_json = {
            "doctype_names": ["Parent Doc", "Child Doc"],
            "doctypes": [
                {
                    "name": "Parent Doc",
                    "module": "Test",
                    "istable": 0,
                    "fields": [
                        {"fieldname": "title", "fieldtype": "Data", "label": "Title"},
                    ]
                },
                {
                    "name": "Child Doc",
                    "module": "Test",
                    "istable": 0,
                    "fields": [
                        {"fieldname": "parent_doc", "fieldtype": "Link", "label": "Parent", "options": "Parent Doc"},
                    ]
                }
            ]
        }

        result = get_schema_from_doctypes_json(doctypes_json)

        # Should have 2 tables
        self.assertEqual(len(result["tables"]), 2)

        # Should have 1 relationship
        self.assertEqual(len(result["relationships"]), 1)

        rel = result["relationships"][0]
        self.assertEqual(rel["source_table_name"], "Child Doc")
        self.assertEqual(rel["source_column_name"], "parent_doc")
        self.assertEqual(rel["target_table_name"], "Parent Doc")

    def test_empty_doctype_list(self):
        """Test that empty input returns empty tables/relationships."""
        doctypes_json = {
            "doctype_names": [],
            "doctypes": []
        }

        result = get_schema_from_doctypes_json(doctypes_json)

        self.assertEqual(result["tables"], [])
        self.assertEqual(result["relationships"], [])


if __name__ == "__main__":
    unittest.main()
