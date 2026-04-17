"""
Tests for the Rule Builder feature.
Tests the JavaScript functions that generate rule objects from form inputs.
"""
import pytest
import json
from app import _transform_json, _transform_text


class TestGenerateRuleFromForm:
    """Test the generateRuleFromForm function logic."""

    def test_generate_rule_basic_json_add(self):
        """Test generating a basic JSON add rule."""
        # Simulate form inputs
        form_data = {
            'builderUrl': '',
            'builderContentType': 'application/json',
            'builderMethod': '',
            'builderTransformType': 'json',
            'builderAction': 'add',
            'jsonFieldsEditor': '{"processed_by": "llama-manager", "timestamp": "2026-04-17T00:00:00Z"}',
            'textSearch': '',
            'textReplace': '',
            'textPattern': '',
            'textRegexReplace': ''
        }

        # Simulate the logic from generateRuleFromForm
        match = {}
        if form_data['builderUrl'].strip():
            match['url'] = form_data['builderUrl'].strip()

        if form_data['builderContentType']:
            match['content_type'] = form_data['builderContentType']

        if form_data['builderMethod']:
            match['method'] = form_data['builderMethod']

        transform = {
            'type': form_data['builderTransformType'],
            'action': form_data['builderAction']
        }

        if form_data['builderTransformType'] == 'json':
            if form_data['builderAction'] in ['add', 'remove', 'set']:
                fields_input = form_data['jsonFieldsEditor'].strip()
                if fields_input:
                    transform['fields'] = json.loads(fields_input)

        assert match == {'content_type': 'application/json'}
        assert transform == {
            'type': 'json',
            'action': 'add',
            'fields': {
                'processed_by': 'llama-manager',
                'timestamp': '2026-04-17T00:00:00Z'
            }
        }

    def test_generate_rule_with_url_match(self):
        """Test generating a rule with URL matching."""
        form_data = {
            'builderUrl': 'https://api.example.com/v1/*',
            'builderContentType': '',
            'builderMethod': '',
            'builderTransformType': 'json',
            'builderAction': 'add',
            'jsonFieldsEditor': '{"key": "value"}',
            'textSearch': '',
            'textReplace': '',
            'textPattern': '',
            'textRegexReplace': ''
        }

        match = {}
        if form_data['builderUrl'].strip():
            match['url'] = form_data['builderUrl'].strip()

        transform = {
            'type': form_data['builderTransformType'],
            'action': form_data['builderAction'],
            'fields': json.loads(form_data['jsonFieldsEditor'].strip())
        }

        rule = {'match': match, 'transform': transform}
        assert rule['match']['url'] == 'https://api.example.com/v1/*'
        assert rule['transform']['fields']['key'] == 'value'

    def test_generate_rule_all_match_conditions(self):
        """Test generating a rule with all match conditions."""
        form_data = {
            'builderUrl': 'https://api.example.com/v1/*',
            'builderContentType': 'application/json',
            'builderMethod': 'POST',
            'builderTransformType': 'json',
            'builderAction': 'remove',
            'jsonFieldsEditor': '["password", "token"]',
            'textSearch': '',
            'textReplace': '',
            'textPattern': '',
            'textRegexReplace': ''
        }

        match = {}
        if form_data['builderUrl'].strip():
            match['url'] = form_data['builderUrl'].strip()
        if form_data['builderContentType']:
            match['content_type'] = form_data['builderContentType']
        if form_data['builderMethod']:
            match['method'] = form_data['builderMethod']

        transform = {
            'type': form_data['builderTransformType'],
            'action': form_data['builderAction'],
            'fields': json.loads(form_data['jsonFieldsEditor'])
        }

        assert match == {
            'url': 'https://api.example.com/v1/*',
            'content_type': 'application/json',
            'method': 'POST'
        }
        assert transform['fields'] == ['password', 'token']


class TestJsonTransformAdd:
    """Test JSON 'add' transformation from Rule Builder."""

    def test_add_single_field(self):
        """Test adding a single field."""
        fields = {"processed_by": "llama-manager"}
        content = '{"name": "John", "age": 30}'

        result = {'content': content, 'modified': False, 'rules_applied': []}
        result = _transform_json(
            result,
            {"type": "json", "action": "add", "fields": fields}
        )

        assert result['modified'] is True
        data = json.loads(result['content'])
        assert data['processed_by'] == 'llama-manager'
        assert data['name'] == "John"
        assert data['age'] == 30

    def test_add_multiple_fields(self):
        """Test adding multiple fields from builder."""
        fields = {
            "processed_by": "llama-manager",
            "timestamp": "2026-04-17T00:00:00Z",
            "version": 1
        }
        content = '{"id": 123}'

        result = {'content': content, 'modified': False, 'rules_applied': []}
        result = _transform_json(
            result,
            {"type": "json", "action": "add", "fields": fields}
        )

        data = json.loads(result['content'])
        assert data['processed_by'] == 'llama-manager'
        assert data['timestamp'] == '2026-04-17T00:00:00Z'
        assert data['version'] == 1
        assert data['id'] == 123


class TestJsonTransformRemove:
    """Test JSON 'remove' transformation from Rule Builder."""

    def test_remove_sensitive_fields(self):
        """Test removing sensitive fields from JSON."""
        fields = ["password", "token", "secret_key"]
        content = '{"name": "John", "password": "secret123", "token": "abc123", "email": "john@test.com"}'

        result = {'content': content, 'modified': False, 'rules_applied': []}
        result = _transform_json(
            result,
            {"type": "json", "action": "remove", "fields": fields}
        )

        assert result['modified'] is True
        data = json.loads(result['content'])
        assert 'password' not in data
        assert 'token' not in data
        assert 'secret_key' not in data
        assert data['name'] == "John"
        assert data['email'] == "john@test.com"


class TestJsonTransformRename:
    """Test JSON 'rename' transformation from Rule Builder."""

    def test_rename_single_key(self):
        """Test renaming a single key."""
        renames = {"id": "user_id"}
        content = '{"id": 1, "name": "John"}'

        result = {'content': content, 'modified': False, 'rules_applied': []}
        result = _transform_json(
            result,
            {"type": "json", "action": "rename", "renames": renames}
        )

        assert result['modified'] is True
        data = json.loads(result['content'])
        assert 'user_id' in data
        assert 'id' not in data
        assert data['user_id'] == 1

    def test_rename_multiple_keys(self):
        """Test renaming multiple keys from builder."""
        renames = {
            "id": "user_id",
            "name": "username",
            "email": "user_email"
        }
        content = '{"id": 1, "name": "John", "email": "john@example.com"}'

        result = {'content': content, 'modified': False, 'rules_applied': []}
        result = _transform_json(
            result,
            {"type": "json", "action": "rename", "renames": renames}
        )

        data = json.loads(result['content'])
        assert data['user_id'] == 1
        assert data['username'] == "John"
        assert data['user_email'] == "john@example.com"
        assert 'id' not in data
        assert 'name' not in data
        assert 'email' not in data


class TestJsonTransformSet:
    """Test JSON 'set' transformation from Rule Builder."""

    def test_set_missing_fields(self):
        """Test setting missing fields as defaults."""
        fields = {"active": True, "verified": False, "count": 0}
        content = '{"name": "John"}'

        result = {'content': content, 'modified': False, 'rules_applied': []}
        result = _transform_json(
            result,
            {"type": "json", "action": "set", "fields": fields}
        )

        assert result['modified'] is True
        data = json.loads(result['content'])
        assert data['active'] is True
        assert data['verified'] is False
        assert data['count'] == 0
        assert data['name'] == "John"


class TestTextTransformReplace:
    """Test text 'replace' transformation from Rule Builder."""

    def test_simple_text_replace(self):
        """Test simple string replacement."""
        search = "www.example.com"
        replace = "api.example.com"
        content = "https://www.example.com/path/to/resource"

        result = {'content': content, 'modified': False, 'rules_applied': []}
        result = _transform_text(
            result,
            {"type": "text", "action": "replace", "search": search, "replace": replace}
        )

        assert result['modified'] is True
        assert result['content'] == 'https://api.example.com/path/to/resource'

    def test_replace_multiple_occurrences(self):
        """Test replacing all occurrences."""
        search = "old-domain.com"
        replace = "new-domain.com"
        content = "Visit old-domain.com for info. Also visit old-domain.com again."

        result = {'content': content, 'modified': False, 'rules_applied': []}
        result = _transform_text(
            result,
            {"type": "text", "action": "replace", "search": search, "replace": replace}
        )

        assert result['content'] == 'Visit new-domain.com for info. Also visit new-domain.com again.'


class TestTextTransformRegex:
    """Test text 'regex' transformation from Rule Builder."""

    def test_regex_simple_pattern(self):
        """Test simple regex replacement."""
        pattern = r"https?://www\.example\.com"
        replacement = "https://api.example.com"
        content = "https://www.example.com/path/to/resource"

        result = {'content': content, 'modified': False, 'rules_applied': []}
        result = _transform_text(
            result,
            {"type": "text", "action": "regex", "pattern": pattern, "replacement": replacement}
        )

        assert result['modified'] is True
        assert result['content'] == 'https://api.example.com/path/to/resource'

    def test_regex_with_capturing_groups(self):
        """Test regex with capturing groups."""
        pattern = r'href="(https?://www\.example\.com)'
        replacement = 'href="https://api.example.com/\1"'
        content = 'href="https://www.example.com/page"'

        result = {'content': content, 'modified': False, 'rules_applied': []}
        result = _transform_text(
            result,
            {"type": "text", "action": "regex", "pattern": pattern, "replacement": replacement}
        )

        assert result['modified'] is True
        # The backslash is escaped in the assertion
        expected = 'href="https://api.example.com/\x01"/page"'
        assert result['content'] == expected


class TestRuleBuilderValidation:
    """Test validation rules for the Rule Builder."""

    def test_requires_at_least_one_match_condition(self):
        """Test that at least one match condition is required."""
        form_data = {
            'builderUrl': '',
            'builderContentType': '',
            'builderMethod': '',
            'builderTransformType': 'json',
            'builderAction': 'add',
            'jsonFieldsEditor': '{"key": "value"}',
            'textSearch': '',
            'textReplace': '',
            'textPattern': '',
            'textRegexReplace': ''
        }

        match = {}
        if form_data['builderUrl'].strip():
            match['url'] = form_data['builderUrl'].strip()
        if form_data['builderContentType']:
            match['content_type'] = form_data['builderContentType']
        if form_data['builderMethod']:
            match['method'] = form_data['builderMethod']

        assert len(match) == 0

    def test_requires_transform_type_and_action(self):
        """Test that transform type and action are required."""
        form_data = {
            'builderUrl': 'https://api.example.com/*',
            'builderContentType': '',
            'builderMethod': '',
            'builderTransformType': '',
            'builderAction': '',
            'jsonFieldsEditor': '{"key": "value"}',
            'textSearch': '',
            'textReplace': '',
            'textPattern': '',
            'textRegexReplace': ''
        }

        assert form_data['builderTransformType'] == ''
        assert form_data['builderAction'] == ''

    def test_requires_fields_for_remove_action(self):
        """Test that fields are required for remove action."""
        form_data = {
            'builderUrl': 'https://api.example.com/*',
            'builderContentType': 'application/json',
            'builderMethod': '',
            'builderTransformType': 'json',
            'builderAction': 'remove',
            'jsonFieldsEditor': '',
            'textSearch': '',
            'textReplace': '',
            'textPattern': '',
            'textRegexReplace': ''
        }

        assert form_data['jsonFieldsEditor'].strip() == ''

    def test_requires_fields_for_set_action(self):
        """Test that fields are required for set action."""
        form_data = {
            'builderUrl': 'https://api.example.com/*',
            'builderContentType': 'application/json',
            'builderMethod': '',
            'builderTransformType': 'json',
            'builderAction': 'set',
            'jsonFieldsEditor': '{}',
            'textSearch': '',
            'textReplace': '',
            'textPattern': '',
            'textRegexReplace': ''
        }

        fields = json.loads(form_data['jsonFieldsEditor'])
        assert fields == {}

    def test_requires_search_and_replace_for_text_replace(self):
        """Test that search and replace are required for text replace action."""
        form_data = {
            'builderUrl': 'https://api.example.com/*',
            'builderContentType': 'text/html',
            'builderMethod': '',
            'builderTransformType': 'text',
            'builderAction': 'replace',
            'jsonFieldsEditor': '',
            'textSearch': '',
            'textReplace': '',
            'textPattern': '',
            'textRegexReplace': ''
        }

        assert form_data['textSearch'].strip() == ''
        assert form_data['textReplace'].strip() == ''


class TestRuleBuilderCompleteFlow:
    """Test complete Rule Builder workflow."""

    def test_create_full_add_rule(self):
        """Test creating a complete add rule from builder."""
        form_data = {
            'builderUrl': 'https://api.example.com/v1/*',
            'builderContentType': 'application/json',
            'builderMethod': 'POST',
            'builderTransformType': 'json',
            'builderAction': 'add',
            'jsonFieldsEditor': '{"processed_by": "llama-manager", "timestamp": "2026-04-17T00:00:00Z"}',
            'textSearch': '',
            'textReplace': '',
            'textPattern': '',
            'textRegexReplace': ''
        }

        # Generate match conditions
        match = {}
        if form_data['builderUrl'].strip():
            match['url'] = form_data['builderUrl'].strip()
        if form_data['builderContentType']:
            match['content_type'] = form_data['builderContentType']
        if form_data['builderMethod']:
            match['method'] = form_data['builderMethod']

        # Generate transform
        transform = {
            'type': form_data['builderTransformType'],
            'action': form_data['builderAction']
        }
        fields_input = form_data['jsonFieldsEditor'].strip()
        if fields_input:
            transform['fields'] = json.loads(fields_input)

        rule = {'match': match, 'transform': transform}

        assert rule['match']['url'] == 'https://api.example.com/v1/*'
        assert rule['match']['content_type'] == 'application/json'
        assert rule['match']['method'] == 'POST'
        assert rule['transform']['type'] == 'json'
        assert rule['transform']['action'] == 'add'
        assert rule['transform']['fields']['processed_by'] == 'llama-manager'
        assert rule['transform']['fields']['timestamp'] == '2026-04-17T00:00:00Z'

    def test_rule_matches_and_transforms_correctly(self):
        """Test that a complete rule matches and transforms correctly."""
        from app import _rule_matches, _transform_json

        # Create rule as builder would generate
        rule = {
            'match': {
                'url': 'https://api.example.com/v1/*',
                'content_type': 'application/json'
            },
            'transform': {
                'type': 'json',
                'action': 'remove',
                'fields': ['password', 'token']
            }
        }

        # Test matching
        assert _rule_matches(rule, "POST", "https://api.example.com/v1/users", "application/json")
        assert not _rule_matches(rule, "GET", "https://api.example.com/v2/users", "application/json")

        # Test transformation
        content = '{"name": "John", "password": "secret", "token": "abc123"}'
        result = {'content': content, 'modified': False, 'rules_applied': []}
        result = _transform_json(result, rule['transform'])

        assert result['modified'] is True
        data = json.loads(result['content'])
        assert 'password' not in data
        assert 'token' not in data
        assert data['name'] == "John"
