# Copyright 2021 Canonical Ltd.
# SPDX-License-Identifier: Apache-2.0
import collections
import contextlib
import json
import pathlib
import sys
import unittest.mock
from typing import Optional

import ops.charm
import ops.model
import ops.testing
import pytest
from _pytest.monkeypatch import MonkeyPatch
from charms.s3_integrator.v0.s3 import S3Consumer, S3Provider

sys.path.append(pathlib.Path(__file__).parent.joinpath("../src").as_posix())
sys.path.append(pathlib.Path(__file__).parent.joinpath("../lib").as_posix())
# fmt:off
import charm  # noqa  # isort:skip
# fmt:on

ARTIFACT_PATH = pathlib.Path(__file__).parent / "artifacts"
CHARM_PATH = pathlib.Path(__file__).parent.parent.absolute()
CLIENT_META = """
name: s3client
requires:
  s3-client:
    interface: s3_credentials
"""


@pytest.fixture
def charm_path():
    return CHARM_PATH


@pytest.fixture
def template_path():
    return CHARM_PATH / "templates"


@pytest.fixture
def artifact_path():
    return ARTIFACT_PATH


class UnitMock:
    def __init__(self):
        self.status = None


class CharmMock:
    def __init__(self):
        self.unit = UnitMock()


@pytest.fixture
def charm_mock():
    charm_mock = CharmMock()
    yield charm_mock


class TestClientCharm(ops.charm.CharmBase):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.event_calls = collections.defaultdict(lambda: 0)
        self.event_map = {}
        self.s3_client = S3Consumer(
            self,
            "s3-client",
        )
        self.framework.observe(
            self.s3_client.on.credentials_changed,
            self._on_s3_credentials_changed,
        )

    def _on_s3_credentials_changed(self, event):
        self.event_calls["credentials_changed"] += 1
        self.event_map["credentials_changed"] = event


@pytest.fixture
def client_charm():
    client_harness = ops.testing.Harness(TestClientCharm, meta=CLIENT_META)
    yield client_harness


class S3Charm:
    def __init__(
        self,
        monkeypatch_context: MonkeyPatch,
        stack: contextlib.ExitStack,
        relate_s3: bool = False,
        relate_consumer: bool = False,
        harness: Optional[ops.testing.Harness] = None,
    ):
        # store monkeypatch context, ExitStack so they are available for tests to use
        self.monkeypatch_context = monkeypatch_context
        self.stack = stack
        # mock relevant shutil, subprocess calls
        self.mock_subprocess_calls()
        self.mock_ingress_address()
        if harness:
            self.harness = harness
        else:
            self.harness = ops.testing.Harness(charm.S3IntegratorCharm)
        self.remote_unit_number = 0
        if relate_consumer:
            self.consumer_relation_id = self.harness.add_relation(
                "s3-credentials", "s3client"
            )
            self.consumer_unit = f"s3client/{self.remote_unit_number}"
            self.remote_unit_number += 1
            self.harness.add_relation_unit(
                self.consumer_relation_id, self.consumer_unit
            )
        if relate_s3:
            self.s3_relation_id = self.harness.add_relation(
                "s3-client", "s3-integrator"
            )
            self.add_s3_relation()
            self.remote_unit_number += 1

    def mock_ingress_address(self):
        self.network_binding_mock = self.stack.enter_context(
            unittest.mock.patch(
                "ops.model.Binding.network", new_callable=unittest.mock.PropertyMock
            )
        )
        self.network_mock = unittest.mock.MagicMock(spec=ops.model.Network)
        self.network_mock.ingress_address = "127.1.2.3"
        self.network_binding_mock.return_value = self.network_mock

    def mock_subprocess_calls(self):
        self.check_output_mock = self.stack.enter_context(
            unittest.mock.patch("subprocess.check_output")
        )
        self.check_call_mock = self.stack.enter_context(
            unittest.mock.patch("subprocess.check_call")
        )
        self.run_mock = self.stack.enter_context(unittest.mock.patch("subprocess.run"))

    def add_s3_relation(self):
        self.s3_unit = f"s3-integrator/{self.remote_unit_number}"
        self.harness.add_relation_unit(self.s3_relation_id, self.s3_unit)

    @property
    def s3_relation(self):
        return self.harness.model.relations["s3-client"][0]

    @property
    def consumer_relation(self):
        return self.harness.model.relations["s3-credentials"][0]

    @property
    def s3_remote_app(self):
        return self.s3_relation.app

    @property
    def s3_relation_data(self):
        return self.harness.get_relation_data(self.s3_relation_id, self.s3_unit)

    def set_s3_relation_data(
        self,
        bucket: str = "",
        endpoint: str = "https://amazonaws.com",
        region: str = "us-west-2",
        access_key_id: Optional[str] = None,
        secret_access_key: Optional[str] = None,
        path: str = "",
    ):
        data = {
            "bucket": bucket,
            "region": region,
            "endpoint": endpoint,
            "access_key_id": access_key_id,
            "secret_access_key": secret_access_key,
            "path": path,
        }
        data = {k: v for k, v in data.items() if v is not None}
        self.harness.update_relation_data(
            self.s3_relation_id,
            "s3-integrator",
            {"s3_credentials": json.dumps(data)},
        )

    def start(self, with_hooks=False, with_leadership=True):
        if with_leadership:
            self.harness.set_leader(True)
        if with_hooks:
            self.harness.begin_with_initial_hooks()
        else:
            self.harness.begin()

    @property
    def charm(self):
        return self.harness.charm

    @property
    def local_app(self):
        return self.harness.model.unit.app

    @property
    def local_unit(self):
        return self.harness.model.unit

    def stop(self):
        self.harness.cleanup()


@pytest.fixture
def s3_charm(monkeypatch):
    with contextlib.ExitStack() as stack:
        ctx = stack.enter_context(monkeypatch.context())
        s3_inst = S3Charm(ctx, stack, relate_consumer=True)
        s3_inst.start()
        yield s3_inst
        s3_inst.stop()


@pytest.fixture
def s3_charm_with_hooks(monkeypatch):
    with contextlib.ExitStack() as stack:
        ctx = stack.enter_context(monkeypatch.context())
        s3_inst = S3Charm(ctx, stack, relate_consumer=True)
        s3_inst.start(with_hooks=True)
        yield s3_inst
        s3_inst.stop()


@pytest.fixture
def s3_charm_not_started(monkeypatch):
    with contextlib.ExitStack() as stack:
        ctx = stack.enter_context(monkeypatch.context())
        s3_inst = S3Charm(ctx, stack, relate_consumer=True)
        yield s3_inst
        try:
            s3_inst.stop()
        except Exception:
            pass


@pytest.fixture
def s3_consumer(monkeypatch, client_charm):
    with contextlib.ExitStack() as stack:
        ctx = stack.enter_context(monkeypatch.context())
        charm_inst = S3Charm(ctx, stack, relate_s3=True, harness=client_charm)
        charm_inst.start()
        yield charm_inst
        charm_inst.stop()
