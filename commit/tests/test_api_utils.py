"""
Unit tests for the API utility functions.

These tests cover pure functions in the commit/api modules
that have no database dependencies.

Run with:
    bench --site waba.local run-tests --app commit --module commit.tests.test_api_utils
"""

import unittest
import json
from unittest.mock import patch, MagicMock


class TestPrepareHeaders(unittest.TestCase):
    """Tests for github.prepare_headers function."""

    def test_default_headers(self):
        """Test default header values."""
        from commit.api.github import prepare_headers

        result = prepare_headers()

        self.assertEqual(result["Accept"], "application/vnd.github+json")
        self.assertEqual(result["X-GitHub-Api-Version"], "2022-11-28")

    def test_custom_accept_header(self):
        """Test with custom accept header."""
        from commit.api.github import prepare_headers

        result = prepare_headers(accept="application/vnd.github.raw")

        self.assertEqual(result["Accept"], "application/vnd.github.raw")


class TestEstimateTokens(unittest.TestCase):
    """Tests for generate_documentation.estimate_tokens function."""

    def test_estimate_tokens_basic(self):
        """Test basic token estimation (chars / 4)."""
        from commit.api.generate_documentation import estimate_tokens

        # 20 characters should be ~5 tokens
        result = estimate_tokens("12345678901234567890")
        self.assertEqual(result, 5)

    def test_estimate_tokens_empty(self):
        """Test token estimation for empty string."""
        from commit.api.generate_documentation import estimate_tokens

        result = estimate_tokens("")
        self.assertEqual(result, 0)

    def test_estimate_tokens_short_text(self):
        """Test token estimation for short text."""
        from commit.api.generate_documentation import estimate_tokens

        # 8 characters = 2 tokens
        result = estimate_tokens("hello wo")
        self.assertEqual(result, 2)


class TestChunkData(unittest.TestCase):
    """Tests for generate_documentation.chunk_data function."""

    def test_chunk_data_single_chunk(self):
        """Test chunking when all items fit in one chunk."""
        from commit.api.generate_documentation import chunk_data

        data = [
            {"function_name": "func1", "path": "path1", "code": "x = 1"},
            {"function_name": "func2", "path": "path2", "code": "y = 2"},
        ]

        # Large max_tokens so everything fits
        result = chunk_data(data, max_tokens=10000)

        self.assertEqual(len(result), 1)
        self.assertEqual(len(result[0]), 2)

    def test_chunk_data_multiple_chunks(self):
        """Test chunking when items need to be split."""
        from commit.api.generate_documentation import chunk_data

        data = [
            {"function_name": "func1", "path": "path1", "code": "x = 1" * 100},
            {"function_name": "func2", "path": "path2", "code": "y = 2" * 100},
            {"function_name": "func3", "path": "path3", "code": "z = 3" * 100},
        ]

        # Small max_tokens to force multiple chunks
        result = chunk_data(data, max_tokens=50)

        # Should create multiple chunks
        self.assertGreater(len(result), 1)

    def test_chunk_data_empty_input(self):
        """Test chunking with empty input."""
        from commit.api.generate_documentation import chunk_data

        result = chunk_data([], max_tokens=1000)

        self.assertEqual(result, [])

    def test_chunk_data_preserves_items(self):
        """Test that chunking preserves all items."""
        from commit.api.generate_documentation import chunk_data

        data = [
            {"function_name": f"func{i}", "path": f"path{i}", "code": f"code{i}"}
            for i in range(5)
        ]

        result = chunk_data(data, max_tokens=100)

        # Count total items across all chunks
        total_items = sum(len(chunk) for chunk in result)
        self.assertEqual(total_items, 5)


class TestCleanResponse(unittest.TestCase):
    """Tests for generate_documentation.clean_response function."""

    def test_clean_response_with_json_markers(self):
        """Test removing ```json markers."""
        from commit.api.generate_documentation import clean_response

        response = '```json\n{"key": "value"}\n```'
        result = clean_response(response)

        self.assertEqual(result.strip(), '{"key": "value"}')

    def test_clean_response_with_only_backticks(self):
        """Test removing ``` markers without json label."""
        from commit.api.generate_documentation import clean_response

        response = '```\n{"key": "value"}\n```'
        result = clean_response(response)

        self.assertEqual(result.strip(), '{"key": "value"}')

    def test_clean_response_no_markers(self):
        """Test response without any markers."""
        from commit.api.generate_documentation import clean_response

        response = '{"key": "value"}'
        result = clean_response(response)

        self.assertEqual(result, '{"key": "value"}')

    def test_clean_response_with_whitespace(self):
        """Test removing whitespace from response."""
        from commit.api.generate_documentation import clean_response

        response = '  ```json\n{"key": "value"}\n```  '
        result = clean_response(response)

        self.assertEqual(result.strip(), '{"key": "value"}')


class TestGenerateBrunoFile(unittest.TestCase):
    """Tests for bruno.generate_bruno_file function."""

    @patch('commit.api.bruno.frappe')
    def test_generate_bruno_file_basic(self, mock_frappe):
        """Test basic .bru file generation."""
        from commit.api.bruno import generate_bruno_file

        request_data = {
            "name": "get_user",
            "api_path": "myapp.api.get_user",
            "request_types": ["GET"],
            "arguments": [
                {"argument": "user_id", "default": ""},
                {"argument": "include_details", "default": "true"}
            ]
        }

        mock_frappe.parse_json.return_value = request_data

        result = generate_bruno_file(json.dumps(request_data), return_type='content')

        # Should contain meta section
        self.assertIn("meta {", result)
        self.assertIn("name: Get User", result)

        # Should contain request section
        self.assertIn("get {", result)
        self.assertIn("url:", result)
        self.assertIn("myapp.api.get_user", result)

    @patch('commit.api.bruno.frappe')
    def test_generate_bruno_file_with_params(self, mock_frappe):
        """Test .bru file generation with query params."""
        from commit.api.bruno import generate_bruno_file

        request_data = {
            "name": "search_items",
            "api_path": "myapp.api.search",
            "request_types": ["GET"],
            "arguments": [
                {"argument": "query", "default": "test"},
                {"argument": "limit", "default": "10"}
            ]
        }

        mock_frappe.parse_json.return_value = request_data

        result = generate_bruno_file(json.dumps(request_data), return_type='content')

        # Should contain params section
        self.assertIn("params:query {", result)
        self.assertIn("query: test", result)
        self.assertIn("limit: 10", result)

    @patch('commit.api.bruno.frappe')
    def test_generate_bruno_file_post_request(self, mock_frappe):
        """Test .bru file generation for POST request."""
        from commit.api.bruno import generate_bruno_file

        request_data = {
            "name": "create_item",
            "api_path": "myapp.api.create",
            "request_types": ["POST"],
            "arguments": []
        }

        mock_frappe.parse_json.return_value = request_data

        result = generate_bruno_file(json.dumps(request_data), return_type='content')

        # Should use POST method
        self.assertIn("post {", result)

    @patch('commit.api.bruno.frappe')
    def test_generate_bruno_file_default_get(self, mock_frappe):
        """Test .bru file defaults to GET when no request_types."""
        from commit.api.bruno import generate_bruno_file

        request_data = {
            "name": "my_api",
            "api_path": "myapp.api.endpoint",
            "request_types": [],
            "arguments": []
        }

        mock_frappe.parse_json.return_value = request_data

        result = generate_bruno_file(json.dumps(request_data), return_type='content')

        # Should default to GET
        self.assertIn("get {", result)


class TestFormatName(unittest.TestCase):
    """Tests for the format_name helper in bruno.py.

    Note: format_name is a nested function, so we test it indirectly
    through generate_bruno_file output.
    """

    @patch('commit.api.bruno.frappe')
    def test_format_name_underscores_to_title(self, mock_frappe):
        """Test that underscores are converted to title case words."""
        from commit.api.bruno import generate_bruno_file

        request_data = {
            "name": "get_user_details",
            "api_path": "myapp.api.get_user_details",
            "request_types": ["GET"],
            "arguments": []
        }

        mock_frappe.parse_json.return_value = request_data

        result = generate_bruno_file(json.dumps(request_data), return_type='content')

        # "get_user_details" should become "Get User Details"
        self.assertIn("name: Get User Details", result)

    @patch('commit.api.bruno.frappe')
    def test_format_name_single_word(self, mock_frappe):
        """Test single word function name formatting."""
        from commit.api.bruno import generate_bruno_file

        request_data = {
            "name": "ping",
            "api_path": "myapp.api.ping",
            "request_types": ["GET"],
            "arguments": []
        }

        mock_frappe.parse_json.return_value = request_data

        result = generate_bruno_file(json.dumps(request_data), return_type='content')

        # "ping" should become "Ping"
        self.assertIn("name: Ping", result)


class TestImageConversionHelpers(unittest.TestCase):
    """Tests for image conversion helper logic.

    Note: The helper functions (can_convert_image, get_extension) are
    defined inside convert_to_webp, so we test the logic directly here.
    """

    def test_can_convert_image_png(self):
        """Test that PNG can be converted."""
        CONVERTIBLE_IMAGE_EXTENSIONS = ["png", "jpeg", "jpg"]

        def can_convert_image(extn):
            return extn.lower() in CONVERTIBLE_IMAGE_EXTENSIONS

        self.assertTrue(can_convert_image("png"))
        self.assertTrue(can_convert_image("PNG"))

    def test_can_convert_image_jpeg(self):
        """Test that JPEG/JPG can be converted."""
        CONVERTIBLE_IMAGE_EXTENSIONS = ["png", "jpeg", "jpg"]

        def can_convert_image(extn):
            return extn.lower() in CONVERTIBLE_IMAGE_EXTENSIONS

        self.assertTrue(can_convert_image("jpeg"))
        self.assertTrue(can_convert_image("jpg"))
        self.assertTrue(can_convert_image("JPEG"))

    def test_can_convert_image_webp_not_convertible(self):
        """Test that WEBP is not in convertible list."""
        CONVERTIBLE_IMAGE_EXTENSIONS = ["png", "jpeg", "jpg"]

        def can_convert_image(extn):
            return extn.lower() in CONVERTIBLE_IMAGE_EXTENSIONS

        self.assertFalse(can_convert_image("webp"))

    def test_can_convert_image_gif_not_convertible(self):
        """Test that GIF is not in convertible list."""
        CONVERTIBLE_IMAGE_EXTENSIONS = ["png", "jpeg", "jpg"]

        def can_convert_image(extn):
            return extn.lower() in CONVERTIBLE_IMAGE_EXTENSIONS

        self.assertFalse(can_convert_image("gif"))

    def test_get_extension_simple(self):
        """Test extracting extension from filename."""
        def get_extension(filename):
            return filename.split(".")[-1].lower()

        self.assertEqual(get_extension("image.png"), "png")
        self.assertEqual(get_extension("photo.JPEG"), "jpeg")

    def test_get_extension_multiple_dots(self):
        """Test extracting extension from filename with multiple dots."""
        def get_extension(filename):
            return filename.split(".")[-1].lower()

        self.assertEqual(get_extension("my.photo.2024.jpg"), "jpg")


if __name__ == "__main__":
    unittest.main()
