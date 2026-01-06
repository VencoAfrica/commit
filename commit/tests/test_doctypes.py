"""
Unit tests for the code_analysis/doctypes.py module.

These tests use temporary directories to test filesystem-based functions.

Run with:
    bench --site waba.local run-tests --app commit --module commit.tests.test_doctypes
"""

import unittest
import tempfile
import shutil
import os
import json
from commit.commit.code_analysis.doctypes import (
    get_doctypes_in_module,
    get_doctype_json
)


class TestGetDoctypesInModule(unittest.TestCase):
    """Tests for get_doctypes_in_module function."""

    def setUp(self):
        """Create a temporary directory structure for testing."""
        self.temp_dir = tempfile.mkdtemp()
        self.app_name = "test_app"
        self.module_name = "test_module"

        # Create the module structure: temp_dir/test_app/test_module/doctype/
        self.module_path = os.path.join(self.temp_dir, self.app_name, self.module_name)
        self.doctype_folder = os.path.join(self.module_path, "doctype")
        os.makedirs(self.doctype_folder)

    def tearDown(self):
        """Remove the temporary directory."""
        shutil.rmtree(self.temp_dir)

    def test_get_doctypes_empty_module(self):
        """Test getting doctypes from a module with no doctypes."""
        # doctype folder exists but is empty
        result = get_doctypes_in_module(self.temp_dir, self.app_name, self.module_name)

        self.assertEqual(result["module"], self.module_name)
        self.assertEqual(result["doctype_names"], [])
        self.assertEqual(result["number_of_doctypes"], 0)

    def test_get_doctypes_single_doctype(self):
        """Test getting a single doctype from module."""
        # Create a doctype folder with JSON file
        doctype_name = "test_doctype"
        doctype_path = os.path.join(self.doctype_folder, doctype_name)
        os.makedirs(doctype_path)

        doctype_json = {
            "name": "Test Doctype",
            "module": "Test Module",
            "fields": []
        }
        with open(os.path.join(doctype_path, f"{doctype_name}.json"), "w") as f:
            json.dump(doctype_json, f)

        result = get_doctypes_in_module(self.temp_dir, self.app_name, self.module_name)

        self.assertEqual(result["module"], self.module_name)
        self.assertIn("Test Doctype", result["doctype_names"])
        self.assertEqual(result["number_of_doctypes"], 1)

    def test_get_doctypes_multiple_doctypes(self):
        """Test getting multiple doctypes from module."""
        # Create multiple doctype folders
        doctypes = [
            ("doctype_one", "Doctype One"),
            ("doctype_two", "Doctype Two"),
            ("doctype_three", "Doctype Three")
        ]

        for folder_name, display_name in doctypes:
            doctype_path = os.path.join(self.doctype_folder, folder_name)
            os.makedirs(doctype_path)
            doctype_json = {"name": display_name, "module": "Test", "fields": []}
            with open(os.path.join(doctype_path, f"{folder_name}.json"), "w") as f:
                json.dump(doctype_json, f)

        result = get_doctypes_in_module(self.temp_dir, self.app_name, self.module_name)

        self.assertEqual(result["number_of_doctypes"], 3)
        self.assertIn("Doctype One", result["doctype_names"])
        self.assertIn("Doctype Two", result["doctype_names"])
        self.assertIn("Doctype Three", result["doctype_names"])

    def test_get_doctypes_no_doctype_folder(self):
        """Test module without doctype folder."""
        # Remove the doctype folder
        shutil.rmtree(self.doctype_folder)

        result = get_doctypes_in_module(self.temp_dir, self.app_name, self.module_name)

        self.assertEqual(result["doctype_names"], [])
        self.assertEqual(result["number_of_doctypes"], 0)


class TestGetDoctypeJson(unittest.TestCase):
    """Tests for get_doctype_json function."""

    def setUp(self):
        """Create a temporary directory structure for testing."""
        self.temp_dir = tempfile.mkdtemp()
        self.app_name = "test_app"
        self.module_name = "test_module"

        # Create the module structure
        self.module_path = os.path.join(self.temp_dir, self.app_name, self.module_name)
        self.doctype_folder = os.path.join(self.module_path, "doctype")
        os.makedirs(self.doctype_folder)

    def tearDown(self):
        """Remove the temporary directory."""
        shutil.rmtree(self.temp_dir)

    def test_get_doctype_json_existing(self):
        """Test getting JSON for an existing doctype."""
        # Create doctype
        doctype_name = "test_doctype"
        doctype_path = os.path.join(self.doctype_folder, doctype_name)
        os.makedirs(doctype_path)

        expected_json = {
            "name": "Test Doctype",
            "module": "Test Module",
            "istable": 0,
            "fields": [
                {"fieldname": "title", "fieldtype": "Data", "label": "Title"}
            ]
        }
        with open(os.path.join(doctype_path, f"{doctype_name}.json"), "w") as f:
            json.dump(expected_json, f)

        result = get_doctype_json(self.temp_dir, self.app_name, self.module_name, "Test Doctype")

        self.assertIsNotNone(result)
        self.assertEqual(result["name"], "Test Doctype")
        self.assertEqual(len(result["fields"]), 1)

    def test_get_doctype_json_not_found(self):
        """Test getting JSON for non-existent doctype returns None."""
        result = get_doctype_json(self.temp_dir, self.app_name, self.module_name, "Non Existent")

        self.assertIsNone(result)

    def test_get_doctype_json_with_spaces_in_name(self):
        """Test getting doctype with spaces in name (uses parse_module_name)."""
        # Create doctype with normalized folder name
        doctype_folder_name = "my_test_doctype"  # normalized from "My Test Doctype"
        doctype_path = os.path.join(self.doctype_folder, doctype_folder_name)
        os.makedirs(doctype_path)

        expected_json = {
            "name": "My Test Doctype",
            "module": "Test Module",
            "fields": []
        }
        with open(os.path.join(doctype_path, f"{doctype_folder_name}.json"), "w") as f:
            json.dump(expected_json, f)

        result = get_doctype_json(self.temp_dir, self.app_name, self.module_name, "My Test Doctype")

        self.assertIsNotNone(result)
        self.assertEqual(result["name"], "My Test Doctype")

    def test_get_doctype_json_no_doctype_folder(self):
        """Test when module has no doctype folder."""
        shutil.rmtree(self.doctype_folder)

        result = get_doctype_json(self.temp_dir, self.app_name, self.module_name, "Any Doctype")

        self.assertIsNone(result)


if __name__ == "__main__":
    unittest.main()
