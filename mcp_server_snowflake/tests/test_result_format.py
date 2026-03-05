# Copyright 2025 Snowflake Inc.
# SPDX-License-Identifier: Apache-2.0
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
# http://www.apache.org/licenses/LICENSE-2.0
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from unittest.mock import MagicMock, patch

import pytest
import yaml

from mcp_server_snowflake.server import SnowflakeService, parse_arguments
from mcp_server_snowflake.utils import results_to_tsv


# --- results_to_tsv unit tests ---


def test_results_to_tsv_returns_string():
    data = [{"col1": 1, "col2": "a"}, {"col1": 2, "col2": "b"}]
    assert results_to_tsv(data) == "col1\tcol2\n1\ta\n2\tb\n"


def test_results_to_tsv_single_row():
    data = [{"name": "Alice", "score": 99}]
    assert results_to_tsv(data) == "name\tscore\nAlice\t99\n"


def test_results_to_tsv_preserves_column_order():
    data = [{"z": 1, "a": 2, "m": 3}]
    header = results_to_tsv(data).split("\n")[0]
    assert header == "z\ta\tm"


def test_results_to_tsv_escapes_tabs_in_values():
    data = [{"col": "val\twith\ttabs"}]
    lines = results_to_tsv(data).strip().split("\n")
    assert lines[1] == "val\\twith\\ttabs"


def test_results_to_tsv_escapes_newlines_in_values():
    data = [{"col": "line1\nline2"}]
    lines = results_to_tsv(data).strip().split("\n")
    assert lines[1] == "line1\\nline2"


def test_results_to_tsv_escapes_carriage_returns_in_values():
    data = [{"col": "val\r\n"}]
    lines = results_to_tsv(data).strip().split("\n")
    assert lines[1] == "val\\r\\n"


def test_results_to_tsv_none_values():
    data = [{"col1": None, "col2": "ok"}]
    lines = results_to_tsv(data).strip().split("\n")
    assert lines[1] == "\tok"


def test_results_to_tsv_commas_not_quoted():
    # Unlike CSV, commas should pass through unescaped
    data = [{"col": "new york, ny"}]
    lines = results_to_tsv(data).strip().split("\n")
    assert lines[1] == "new york, ny"


# --- SnowflakeService result_format attribute tests ---


@pytest.fixture
def minimal_config_file(tmp_path):
    config = {"search_services": []}
    config_file = tmp_path / "config.yaml"
    config_file.write_text(yaml.dump(config))
    return config_file


@pytest.fixture
def mock_snowflake_connect():
    with (
        patch("mcp_server_snowflake.server.connect") as mock_connect,
        patch("mcp_server_snowflake.server.Root") as mock_root,
    ):
        mock_connect.return_value = MagicMock()
        mock_root.return_value = MagicMock()
        yield mock_connect


def test_snowflake_service_default_result_format(
    mock_snowflake_connect, minimal_config_file
):
    service = SnowflakeService(
        service_config_file=str(minimal_config_file),
        transport="stdio",
        connection_params={},
    )
    assert service.result_format == "json"


def test_snowflake_service_tsv_result_format(
    mock_snowflake_connect, minimal_config_file
):
    service = SnowflakeService(
        service_config_file=str(minimal_config_file),
        transport="stdio",
        connection_params={},
        result_format="tsv",
    )
    assert service.result_format == "tsv"


# --- CLI argument tests ---


def test_parse_arguments_default_result_format(monkeypatch):
    monkeypatch.delenv("SNOWFLAKE_MCP_RESULT_FORMAT", raising=False)
    with patch("sys.argv", ["prog"]):
        args = parse_arguments()
    assert args.result_format == "json"


def test_parse_arguments_tsv_result_format():
    with patch("sys.argv", ["prog", "--result-format", "tsv"]):
        args = parse_arguments()
    assert args.result_format == "tsv"


def test_parse_arguments_invalid_result_format():
    with patch("sys.argv", ["prog", "--result-format", "csv"]):
        with pytest.raises(SystemExit):
            parse_arguments()


def test_parse_arguments_result_format_from_env(monkeypatch):
    monkeypatch.setenv("SNOWFLAKE_MCP_RESULT_FORMAT", "tsv")
    with patch("sys.argv", ["prog"]):
        args = parse_arguments()
    assert args.result_format == "tsv"
