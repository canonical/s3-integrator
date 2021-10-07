#!/usr/bin/env python3
# Copyright 2021 Canonical Ltd.
# SPDX-License-Identifier: Apache-2.0
"""A charm of the s3 integrator service."""

import logging

import ops
import ops.charm
import ops.framework
import ops.lib
import ops.main
import ops.model
from charms.s3_integrator.v0.s3 import S3Provider

logger = logging.getLogger(__name__)


class S3IntegratorCharm(ops.charm.CharmBase):
    """Charm for s3 integrator service."""

    _stored = ops.framework.StoredState()

    def __init__(self, *args) -> None:
        super().__init__(*args)
        self._stored.set_default(
            **{
                "s3_endpoint": "s3.amazonaws.com",
                "s3_bucket": "",
                "s3_region": "us-west-2",
                "s3_path": "filestore",
                "s3_access_key_id": "",
                "s3_secret_access_key": "",
            }
        )
        self.s3_provider = S3Provider(self, "s3_credentials")
        self.framework.observe(self.on.start, self._on_start)
        self.framework.observe(self.on.config_changed, self._on_config_changed)
        self.framework.observe(
            self.on.sync_s3_credentials_action, self._on_sync_s3_credentials
        )

    def _on_start(self, _: ops.charm.StartEvent) -> None:
        """Handle the charm startup event.

        Puts the charm into :class:`~ops.model.WaitingStatus` if successful
        otherwise sets the status to :class:`~ops.model.BlockedStatus`

        Args:
            _ (ops.charm.StartEvent): The triggering start event

        Returns:
            None: None
        """
        self.unit.status = ops.model.WaitingStatus("Waiting for S3 credentials")

    def _on_config_changed(self, _: ops.charm.ConfigChangedEvent) -> None:
        """Event handler for configuration changed events.

        Args:
            _ (ops.charm.ConfigChangedEvent): The configuration changed event

        Returns:
            None: None
        """
        resend_credentials = False
        for k in ("s3_endpoint", "s3_bucket", "s3_region", "s3_path"):
            # exit logic first to short circuit - if the config has the same values
            # as the stored data, ignore the key since it has not been updated
            if self.config[k] == getattr(self._stored, k):
                continue
            # we can just set the value and use a flag to indicate we need to update
            # the relationship
            setattr(self._stored, k, self.config[k])
            resend_credentials = True
        if resend_credentials:
            self._send_s3_credentials()
        self.unit.status = ops.model.ActiveStatus()

    def _send_s3_credentials(self) -> None:
        """Send S3 credentials over to any consumers.

        Returns:

            None: None
        """
        if self._stored.s3_secret_access_key and self._stored.s3_access_key_id:
            self.status = ops.model.MaintenanceStatus("Sending S3 credentials...")
            self.s3_provider.set_credentials(
                bucket=self._stored.s3_bucket,
                region=self._stored.s3_region,
                endpoint=self._stored.s3_endpoint,
                access_key_id=self._stored.s3_access_key_id,
                secret_access_key=self._stored.s3_secret_access_key,
                path=self._stored.s3_path,
            )
            self.status = ops.model.ActiveStatus()

    def _on_sync_s3_credentials(self, event: ops.charm.ActionEvent) -> None:
        """Handle a user synchronizing their S3 credentials to the charm.

        Updates the configuration instance and writes the binary store data

        Args:
            event (ops.charm.ActionEvent): The sync event instance

        Returns:
            None: None
        """
        logger.info("updating s3 credentials...")
        self._stored.s3_access_key_id = event.params["access-key-id"]
        self._stored.s3_secret_access_key = event.params["secret-access-key"]
        self._send_s3_credentials()


if __name__ == "__main__":
    ops.main.main(S3IntegratorCharm)
