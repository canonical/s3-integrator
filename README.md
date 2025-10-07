# S3-integrator
[![Charmhub](https://charmhub.io/s3-integrator/badge.svg)](https://charmhub.io/s3-integrator)
[![Release](https://github.com/canonical/s3-integrator/actions/workflows/release.yaml/badge.svg)](https://github.com/canonical/s3-integrator/actions/workflows/release.yaml)
[![Tests](https://github.com/canonical/s3-integrator/actions/workflows/ci.yaml/badge.svg)](https://github.com/canonical/s3-integrator/actions/workflows/ci.yaml)

## Description

An operator charm providing an integrator for connecting to S3 provides. The charm in the current repository allows to configure the S3 bucket informations using Juju actions, and it is publishes to the [s3-integrator](https://charmhub.io/s3-integrator?channel=1/stable) charm under the track `1/*`.

For the Juju secret-based user-experience, please refer to the [object-storage-integrators](https://github.com/canonical/object-storage-integrators) repository, that is published to the [s3-integrator](https://charmhub.io/s3-integrator?channel=2/edge) charm under the track `2/*.`

> `latest/stable` is deprecated and it should not be used moving forward. After 26.10, the `latest/stable` channel will be removed. 

## Usage
>[!WARNING]
> This README uses **Juju 3** commands.
>
> If you are using **Juju <= 2.9**, check the collapsible sections below code blocks.

### Deploying the S3 Integrator

#### Charmhub
```shell
juju deploy s3-integrator --channel 1/stable
```
#### From source
```shell
git clone https://github.com/canonical/s3-integrator.git
cd s3-integrator/
lxd init --auto
lxc network set lxdbr0 ipv6.address none
sudo snap install charmcraft --classic
charmcraft pack
```
Then,
```shell
juju deploy ./s3-integrator_ubuntu-22.04-amd64.charm
```

### Adding your S3 Credentials

To deploy your S3 credentials to the application, run the following action:
  
```bash
juju run s3-integrator/leader sync-s3-credentials access-key=<your_key> secret-key=<your_secret_key>
```
<details>
<summary><small><b>juju <= 2.9</b></small></summary>
  
```bash
juju run-action s3-integrator/leader sync-s3-credentials access-key=<your_key> secret-key=<your_secret_key>
```
</details>
  
### Configuring the Integrator

To configure the S3 integrator charm, you may provide the following configuration options:
  
- `endpoint`: the endpoint used to connect to the object storage.
- `bucket`: the bucket/container name delivered by the provider (the bucket name can be specified also on the requirer application).
- `region`: the region used to connect to the object storage.
- `path`: the path inside the bucket/container to store objects.
- `attributes`: the custom metadata (HTTP headers).
- `s3-uri-style`: the S3 protocol specific bucket path lookup type.
- `storage-class`:the storage class for objects uploaded to the object storage.
- `tls-ca-chain`: the complete CA chain, which can be used for HTTPS validation.
- `s3-api-version`: the S3 protocol specific API signature.
- `experimental-delete-older-than-days`: the amount of day after which backups going to be deleted. EXPERIMENTAL option.


The only mandatory fields for the integrator are access-key secret-key and bucket.

In order to set ca-chain certificate use the following command:
```bash
juju config s3-integrator tls-ca-chain="$(base64 -w0 your_ca_chain.pem)"
```
Attributes needs to be specified in comma-separated format. 

### Configuring the Integrator

To retrieve the S3 credentials, run the following action:
  
```bash
juju run s3-integrator/leader get-s3-credentials
```
<details>
<summary><small><b>juju <= 2.9</b></small></summary>

```bash
juju run-action s3-integrator/leader get-s3-credentials --wait
```
</details>

If the credentials are not set, the action will fail.

To retrieve the set of connection parameters, run the following command:

```bash
juju run s3-integrator/leader get-s3-connection-info
```
<details>
<summary><small><b>juju <= 2.9</b></small></summary>

```bash
juju run-action s3-integrator/leader get-s3-connection-info --wait
```
</details>


## Relations 

Relations are supported via the `s3` interface. To create a relation:

```bash
juju integrate s3-integrator application
```
<details>
<summary><small><b>juju <= 2.9</b></small></summary>

```bash
juju relate s3-integrator application
```
</details>

To remove relation a relation:
```bash
juju remove-relation s3-integrator application
```

## Security
Security issues in the Charmed S3 Integrator Operator can be reported through [LaunchPad](https://wiki.ubuntu.com/DebuggingSecurity#How%20to%20File). Please do not file GitHub issues about security issues.


## Contributing

Please see the [Juju SDK docs](https://juju.is/docs/sdk) for guidelines on enhancements to this charm following best practice guidelines, and [CONTRIBUTING.md](https://github.com/canonical/s3-integrator/blob/main/CONTRIBUTING.md) for developer guidance.

