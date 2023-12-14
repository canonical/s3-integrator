# S3-integrator
## Description

An operator charm providing an integrator for connecting to S3 provides.

## Usage
>[!WARNING]
> Commands are shown by default for **juju >= 3.0**.
>
> For **juju <= 2.9**, see the collapsible sections.

### Deploying the S3 Integrator

#### Charmhub
```shell
juju deploy s3-integrator --channel edge
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
juju deploy ./s3-integrator_ubuntu-20.04-amd64.charm
```

### Adding your S3 Credentials

To deploy your S3 credentials to the application, run the following action:
<details open>
<summary><small>juju >= 3.0</small></summary>
  
```bash
$ juju run s3-integrator/leader sync-s3-credentials access-key=<your_key> secret-key=<your_secret_key>
```
</details>
<details>
<summary><small>juju <= 2.9</small></summary>
  
```bash
$ juju run-action s3-integrator/leader sync-s3-credentials access-key=<your_key> secret-key=<your_secret_key>
```
</details>
  
### Configuring the Integrator

To configure the S3 integrator charm, you may provide the following configuration options:

- endpoint: the endpoint used to connect to the object storage.
- bucket: the bucket/container name delivered by the provider (the bucket name can be specified also on the requirer application).
- region: the region used to connect to the object storage.
- path: the path inside the bucket/container to store objects.
- attributes: the custom metadata (HTTP headers).
- s3-uri-style: the S3 protocol specific bucket path lookup type.
- storage-class:the storage class for objects uploaded to the object storage.
- tls-ca-chain: the complete CA chain, which can be used for HTTPS validation.
- s3-api-version: the S3 protocol specific API signature.

The only mandatory fields for the integrator are access-key secret-key and bucket.

In order to set ca-chain certificate use the following command:
```bash
$ juju config s3-integrator tls-ca-chain="$(base64 -w0 your_ca_chain.pem)"
```
Attributes needs to be specified in comma-separated format. 

### Configuring the Integrator

To retrieve the S3 credentials, run the following action:

<details open>
<summary><small>juju >= 3.0</small></summary>
  
```bash
$ juju run s3-integrator/leader get-s3-credentials --wait
```
</details>
<details>
<summary><small>juju <= 2.9</small></summary>

```bash
$ juju run-action s3-integrator/leader get-s3-credentials --wait
```
</details>

If the credentials are not set, the action will fail.

To retrieve the set of connection parameters, run the following command:

<details open>
<summary><small>juju >= 3.0</small></summary>

```bash
$ juju run s3-integrator/leader get-s3-connection-info --wait
```
</details>
<details>
<summary><small>juju <= 2.9</small></summary>

```bash
$ juju run-action s3-integrator/leader get-s3-connection-info --wait
```
</details>


## Relations 

Relations are supported via the `s3` interface. To create a relation:

<details open>
<summary><small>juju >= 3.0</small></summary>

```bash
$ juju integrate s3-integrator application
```
</details>
<details>
<summary><small>juju <= 2.9</small></summary>

```bash
$ juju relate s3-integrator application
```
</details>

To remove relation a relation:
```bash
$ juju remove-relation s3-integrator application
```

## Security
Security issues in the Charmed S3 Integrator Operator can be reported through [LaunchPad](https://wiki.ubuntu.com/DebuggingSecurity#How%20to%20File). Please do not file GitHub issues about security issues.


## Contributing

Please see the [Juju SDK docs](https://juju.is/docs/sdk) for guidelines on enhancements to this charm following best practice guidelines, and [CONTRIBUTING.md](https://github.com/canonical/s3-integrator/blob/main/CONTRIBUTING.md) for developer guidance.

