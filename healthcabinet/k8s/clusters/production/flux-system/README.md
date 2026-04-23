# FluxCD Bootstrap Placeholder

This directory is created for FluxCD bootstrap artifacts.

To bootstrap against a live EKS cluster (AWS eu-central-1):

```bash
flux bootstrap github \
  --owner=<org> \
  --repository=healthcabinet \
  --branch=main \
  --path=k8s/clusters/production \
  --personal
```

FluxCD will manage image updates via ImageRepository + ImagePolicy + ImageUpdateAutomation.
The `secrets.enc.yaml` files are decrypted by a SOPS provider configured in the flux-system namespace.

See: https://fluxcd.io/docs/guides/mozilla-sops/
