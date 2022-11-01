import os

import pulumi
import pulumi_kubernetes as k8s
from pulumi_kubernetes.helm.v3 import Release, ReleaseArgs, RepositoryOptsArgs

from kic_util import pulumi_config

config = pulumi.Config('resurface')
chart_name = config.get('chart_name')
if not chart_name:
    chart_name = 'resurface'
chart_version = config.get('chart_version')
if not chart_version:
    chart_version = '3.2.6'
helm_repo_name = config.get('helm_repo_name')
if not helm_repo_name:
    helm_repo_name = 'resurfaceio'
helm_repo_url = config.get('helm_repo_url')
if not helm_repo_url:
    helm_repo_url = 'https://resurfaceio.github.io/containers'

#
# Allow the user to set timeout per helm chart; otherwise
# we default to 5 minutes.
#
helm_timeout = config.get_int('helm_timeout')
if not helm_timeout:
    helm_timeout = 300


def project_name_from_project_dir(dirname: str):
    script_dir = os.path.dirname(os.path.abspath(__file__))
    project_path = os.path.join(script_dir, '..', '..', '..', 'python', 'infrastructure', dirname)
    return pulumi_config.get_pulumi_project_name(project_path)


stack_name = pulumi.get_stack()
project_name = pulumi.get_project()
pulumi_user = pulumi_config.get_pulumi_user()

k8_project_name = project_name_from_project_dir('kubeconfig')
k8_stack_ref_id = f"{pulumi_user}/{k8_project_name}/{stack_name}"
k8_stack_ref = pulumi.StackReference(k8_stack_ref_id)
kubeconfig = k8_stack_ref.require_output('kubeconfig').apply(lambda c: str(c))

k8s_provider = k8s.Provider(resource_name=f'ingress-controller',
                            kubeconfig=kubeconfig)

ns = k8s.core.v1.Namespace(resource_name='resurface',
                           metadata={'name': 'resurface'},
                           opts=pulumi.ResourceOptions(provider=k8s_provider))

resurface_release_args = ReleaseArgs(
    chart=chart_name,
    repository_opts=RepositoryOptsArgs(
        repo=helm_repo_url
    ),
    version=chart_version,
    namespace=ns.metadata.name,
    value_yaml_files=[
        pulumi.FileAsset("./values.yaml")
    ],
    # User configurable timeout
    timeout=helm_timeout,
    # By default, Release resource will wait till all created resources
    # are available. Set this to true to skip waiting on resources being
    # available.
    skip_await=False,
    # If we fail, clean up
    cleanup_on_fail=True,
    # Provide a name for our release
    name="resurface",
    # Lint the chart before installing
    lint=True,
    # Force update if required
    force_update=True)

resurface_release = Release("resurface", args=resurface_release_args)

# Print out our status
rstatus = resurface_release.status
pulumi.export("resurface_status", rstatus)
