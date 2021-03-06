import json

import luigi
from betterboto import client as betterboto_client
from deepmerge import always_merger

from servicecatalog_puppet import config
from servicecatalog_puppet.workflow import dependency
from servicecatalog_puppet.workflow import tasks


class GetSSMParamTask(tasks.PuppetTask):
    parameter_name = luigi.Parameter()
    name = luigi.Parameter()
    region = luigi.Parameter(default=None)

    depends_on = luigi.ListParameter(default=[])
    manifest_file_path = luigi.Parameter(default="")
    puppet_account_id = luigi.Parameter(default="")
    spoke_account_id = luigi.Parameter(default="")
    spoke_region = luigi.Parameter(default="")

    def params_for_results_display(self):
        return {
            "parameter_name": self.parameter_name,
            "name": self.name,
            "region": self.region,
            "cache_invalidator": self.cache_invalidator,
        }

    def api_calls_used(self):
        return ["ssm.get_parameter"]

    def requires(self):
        if len(self.depends_on) > 0:
            return dependency.generate_dependency_tasks(
                self.depends_on,
                self.manifest_file_path,
                self.puppet_account_id,
                self.spoke_account_id,
                self.spoke_region,
                self.execution_mode,
            )
        else:
            return []

    def run(self):
        with betterboto_client.ClientContextManager(
            "ssm", region_name=self.region
        ) as ssm:
            try:
                p = ssm.get_parameter(Name=self.name,)
                self.write_output(
                    {
                        "Name": self.name,
                        "Region": self.region,
                        "Value": p.get("Parameter").get("Value"),
                        "Version": p.get("Parameter").get("Version"),
                    }
                )
            except ssm.exceptions.ParameterNotFound as e:
                raise e


class PuppetTaskWithParameters(tasks.PuppetTask):
    def get_all_of_the_params(self):
        all_params = dict()
        always_merger.merge(all_params, tasks.unwrap(self.manifest_parameters))
        always_merger.merge(all_params, tasks.unwrap(self.launch_parameters))
        always_merger.merge(all_params, tasks.unwrap(self.account_parameters))
        return all_params

    def get_ssm_parameters(self):
        ssm_params = dict()

        all_params = self.get_all_of_the_params()

        for param_name, param_details in all_params.items():
            if param_details.get("ssm"):
                if param_details.get("default"):
                    del param_details["default"]
                ssm_parameter_name = param_details.get("ssm").get("name")
                ssm_parameter_name = ssm_parameter_name.replace(
                    "${AWS::Region}", self.region
                )
                ssm_parameter_name = ssm_parameter_name.replace(
                    "${AWS::AccountId}", self.account_id
                )
                ssm_params[param_name] = GetSSMParamTask(
                    parameter_name=param_name,
                    name=ssm_parameter_name,
                    region=param_details.get("ssm").get(
                        "region", config.get_home_region(self.puppet_account_id)
                    ),
                    depends_on=param_details.get("ssm").get("depends_on", []),
                    manifest_file_path=self.manifest_file_path,
                    puppet_account_id=self.puppet_account_id,
                    spoke_account_id=self.account_id,
                    spoke_region=self.region,
                )

        return ssm_params

    def get_parameter_values(self):
        all_params = {}
        self.info(f"collecting all_params")
        p = self.get_all_of_the_params()
        for param_name, param_details in p.items():
            if param_details.get("ssm"):
                with self.input().get("ssm_params").get(param_name).open() as f:
                    all_params[param_name] = json.loads(f.read()).get("Value")
            if param_details.get("default"):
                all_params[param_name] = param_details.get("default")
            if param_details.get("mapping"):
                all_params[param_name] = self.manifest.get_mapping(
                    param_details.get("mapping"), self.account_id, self.region
                )

        self.info(f"finished collecting all_params: {all_params}")
        return all_params
