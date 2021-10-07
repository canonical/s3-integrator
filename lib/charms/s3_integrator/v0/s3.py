# Copyright 2021 Canonical Ltd.
# SPDX-License-Identifier: Apache-2.0
"""A library for communicating with the S3 integrator providers and consumers.

This library provides the relevant interface code implementing the communication
specification for fetching, retrieving, triggering, and responding to events related to
the S3 integrator charm and its consumers.

The provider is implemented in the `s3-integrator` charm which is meant to be deployed
alongside one or more consumer charms. The integrator charm should then have credentials
set via its action:

   .. code-block:: bash

      $ juju run-action s3-integrator/leader sync-s3-credentials \
          access-key-id=<your_key> secret-access-key=<your_secret_key>

The consumer end of the charm should be implemented as follows:

   .. code-block:: python

      from charms.s3_integrator.v0.s3 import S3Consumer

      class MyCharm(CharmBase):
          def __init__(self, *args, **kwargs):
              super().__init__(*args, **kwargs)
              self.s3_credentials = {}
              self.s3_credential_client = S3Consumer(
                  self,
                  "s3-credentials",
              )
              self.framework.observe(
                  self.s3_credential_client.on.credentials_changed,
                  self._on_s3_credentials_changed,
              )
          def _on_s3_credentials_changed(self, event):
              credentials = self.s3_client.get_credentials()
              if credentials.get("secret_access_key"):
                  self.s3_credentials.update(credentials)
                  self.write_s3_config(credentials)
                  self.restart()
"""
import json
import logging
from typing import Any, Dict, Optional, Union

import ops.charm
import ops.framework
import ops.model

LIBID = "55c4cfd4a8ac45b1b62f2826272a1cf8"
LIBAPI = 0
LIBPATCH = 1


logger = logging.getLogger(__name__)


class CredentialsChanged(ops.framework.EventBase):
    """Event raised when S3 credentials are changed."""

    def __init__(
        self,
        handle: ops.framework.Handle,
        data: Optional[Dict[str, Dict[str, Any]]] = None,
    ) -> None:
        """Initialize the CredentialsChanged event.

        Args:
            handle (ops.framework.Handle): The handle for the event
            data (Optional[Dict[str, Dict[str, Any]]]): An optional dictionary of event
                data

        Returns:
            None: None
        """
        super().__init__(handle)
        self.data = data

    def snapshot(self) -> Dict[str, Union[Dict[str, Any], None]]:
        """Save the relation data.

        Returns:
            Dict[str, Dict[str, Any]]: A dictionary containing snapshot data
        """
        return {"data": self.data}

    def restore(self, snapshot: Dict[str, Dict[str, Any]]) -> None:
        """Restore snapshot data from the given snapshot dictionary.

        Args:
            snapshot (Dict[str, Dict[str, Any]]): A dictionary of snapshot data
                containing the key 'data'.

        Returns:
            None: None
        """
        self.data = snapshot["data"]


class S3CredentialEvents(ops.framework.ObjectEvents):
    """Event descriptor for events raised by :class:`S3Provider`"""

    credentials_changed = ops.framework.EventSource(CredentialsChanged)


class S3Consumer(ops.framework.Object):
    """A *consumer* of S3 credentials (implements the `requires` side of the relation)

    .. code-block:: yaml
       requires:
          s3-credentials:
           interface: s3-credentials

    Arguments:
        charm (ops.charm.CharmBase): The consumer charm
        relation_name (str): The name of the relation from the consumer metadata
        consumes (Dict[str, Any]): The provider specification
        multi (bool): A flag indicating the presence of multiple relations
    """

    on = S3CredentialEvents()
    _stored = ops.framework.StoredState()

    def __init__(
        self,
        charm: ops.charm.CharmBase,
        relation_name: str,
    ):
        """Create a new S3 Consumer client.

        The client instance provides an interface to consume S3 credentials.

        Args:
            charm (ops.charm.CharmBase): The consumer charm instance
            relation_name (str): The name of the relation

        Returns:
            None: None

        Examples:
            >>> class MyCharm(CharmBase):
                    def __init__(self, *args, **kwargs):
                        super().__init__(*args, **kwargs)
                        self.s3_credential_client = S3Consumer(
                            self,
                            "s3-credentials",
                        )
                        self.framework.observe(
                            self.s3_credential_client.on.credentials_changed,
                            self._on_s3_credentials_changed,
                        )
        """
        super().__init__(charm, relation_name)
        # region default per
        # https://docs.aws.amazon.com/AmazonRDS/latest/UserGuide/Concepts.
        # RegionsAndAvailabilityZones.html
        self._consumer_relation_name = relation_name
        self.charm = charm
        self.framework.observe(
            self.charm.on[self._consumer_relation_name].relation_changed,
            self._on_relation_changed,
        )
        self.framework.observe(
            self.charm.on[self._consumer_relation_name].relation_departed,
            self._on_relation_departed,
        )
        self.framework.observe(
            self.charm.on[self._consumer_relation_name].relation_broken,
            self._on_relation_broken,
        )

    def get_credentials(self) -> Dict[str, str]:
        """Retrieve the credentials from the relationship.

        Returns:
            Dict[str, str]: A dictionary of the S3 credentials.
        """
        credentials: Dict[str, str] = {}
        relation = self.charm.model.get_relation(self._consumer_relation_name)
        if not relation:
            return credentials
        credentials = json.loads(
            relation.data[relation.app].get("s3_credentials", "{}")
        )
        return credentials

    def _on_relation_changed(self, event: ops.charm.RelationChangedEvent) -> None:
        """Notify the charm about the presence of S3 credentials.

        Args:
            event (ops.charm.RelationChangedEvent): The relation changed event
        """
        data = event.relation.data.get(event.app, {})
        if "s3_credentials" not in data:
            return
        self.on.credentials_changed.emit(data["s3_credentials"])

    def _on_relation_departed(self, _: ops.charm.RelationDepartedEvent) -> None:
        """Notify the charm about the departing of the S3 credential store."""
        self.on.credentials_changed.emit()

    def _on_relation_broken(self, _: ops.charm.RelationBrokenEvent) -> None:
        """Notify the charm about a broken S3 credential store relation."""
        self.on.credentials_changed.emit()


class S3Provider(ops.framework.Object):
    """A provider handler for communicating S3 credentials to consumers.

    Args:
        charm (ops.charm.CharmBase): The consumer charm
        name (str): The name of the relation
        bucket (Optional[str]): The name of the target s3 bucket, default None.
        region (Optional[str]): The name of the target region, default None.
        endpoint (Optional[str]): The url of the target AWS endpoint, default None.
        path (Optional[str]): The subdirectory within the target, default None.

    Examples:
        >>> class MyCharm(CharmBase):
                def __init__(self, *args, **kwargs):
                    super().__init__(*args, **kwargs)
                    self.s3_provider = S3Provider(self, "s3-credentials")
                    self.framework.observe(
                        self.on.config_changed, self._on_config_changed
                    )
                    self.framework.observe(
                        self.on.sync_s3_credentials_action, self._on_sync_s3_credentials
                    )

            def _on_config_changed(self, _: ops.charm.ConfigChangedEvent) -> None:
                resend_credentials = False
                for k in ("s3_endpoint", "s3_bucket", "s3_region", "s3_path"):
                    if (self.config[k] == getattr(self._stored, k)):
                        continue
                    setattr(self._stored, k, self.config[k])
                    resend_credentials = True
                if resend_credentials:
                    self._send_s3_credentials()
                self.unit.status = ops.model.ActiveStatus()

            def _send_s3_credentials(self) -> None:
                if self._stored.s3_secret_access_key and self._stored.s3_access_key_id:
                    self.status = ops.model.MaintenanceStatus(
                        "Sending S3 credentials..."
                    )
                    self.s3_provider.set_credentials(
                        bucket=self._stored.s3_bucket,
                        region=self._stored.s3_region,
                        endpoint=self._stored.s3_endpoint,
                        access_key_id=self._stored.s3_access_key_id,
                        secret_access_key=self._stored.s3_secret_access_key,
                        path=self._stored.s3_path,
                    )

            def _on_sync_s3_credentials(self, event: ops.charm.ActionEvent) -> None:
                logger.info("updating s3 credentials...")
                self._stored.s3_access_key_id = event.params["access-key-id"]
                self._stored.s3_secret_access_key = event.params["secret-access-key"]
                self._send_s3_credentials()
    """

    _stored = ops.framework.StoredState()

    def __init__(
        self,
        charm: ops.charm.CharmBase,
        name: str,
    ):
        super().__init__(charm, name)
        self.charm = charm
        self.name = name
        self._stored.set_default(
            bucket="",
            region="",
            endpoint="",
            access_key_id="",
            secret_access_key="",
            path="",
        )
        events = self.charm.on[self.name]
        # if we are going to consider this just some data, it will auto-update
        # so we would not need to monitor `relation_broken/departed`
        self.framework.observe(events.relation_joined, self._on_relation_joined)

    def set_credentials(
        self,
        bucket: str,
        region: str,
        endpoint: str,
        access_key_id: str,
        secret_access_key: str,
        path: str = "",
    ) -> None:
        """Set the S3 access key ID and secret access key:

        Args:
            bucket (str): The bucket name to store files in
            region (str): The AWS region in which the bucket is located
            endpoint (str): The AWS endpoint URL
            access_key_id (str): The S3 access key id
            secret_access_key (str): The S3 secret access key
            path (str): The path inside the bucket where files will be stored, default
                "".

        Return:
            None (None)
        """
        self._stored.bucket = bucket
        self._stored.region = region
        self._stored.endpoint = endpoint
        self._stored.path = path
        self._stored.access_key_id = access_key_id
        self._stored.secret_access_key = secret_access_key
        self._set_relation_data()

    def _set_relation_data(
        self,
        event: Optional[ops.charm.RelationJoinedEvent] = None,
    ) -> None:
        """Set relationship or event data according to the given new data.

        Args:
            data (Dict[str, Any]): A dictionary of updated data to set
            event (Optional[ops.charm.RelationJoinedEvent]): An optional event
                instance, which, if provided, causes data to be set against the
                event instead of the relation itself.

        Returns:
            None: None
        """
        if not self.charm.unit.is_leader():
            return
        if event is not None:
            event.relation.data[self.charm.app].update(self._generate_relation_data())
        else:
            if self.name in self.charm.model.relations:
                for relation in self.charm.model.relations[self.name]:
                    relation.data[self.charm.app].update(self._generate_relation_data())
        return

    def _generate_relation_data(self) -> Dict[str, str]:
        """Generate the S3 credentials data.

        Returns:
            Dict[str, str]: A dictionary with the key "s3_credentials" and a jsonified
                dictionary of the credentials as the value.
        """
        return {
            "s3_credentials": json.dumps(
                {
                    "bucket": self._stored.bucket,
                    "region": self._stored.region,
                    "endpoint": self._stored.endpoint,
                    "access_key_id": self._stored.access_key_id,
                    "secret_access_key": self._stored.secret_access_key,
                    "path": self._stored.path,
                }
            )
        }

    def _on_relation_joined(self, event: ops.charm.RelationJoinedEvent) -> None:
        """React to the relation joined event by consuming data.

        Args:
            event (ops.charm.RelationJoinedEvent): A relation joined event

        Returns:
            None: None
        """
        if not self.charm.unit.is_leader():
            return
        self._set_relation_data(event)
