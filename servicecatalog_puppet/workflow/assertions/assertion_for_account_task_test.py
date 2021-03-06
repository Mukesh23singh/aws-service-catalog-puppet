from unittest import skip
from servicecatalog_puppet.workflow import tasks_unit_tests_helper
from unittest import skip, mock


class AssertionForAccountTaskTest(tasks_unit_tests_helper.PuppetTaskUnitTest):
    puppet_account_id = "puppet_account_id"
    assertion_name = "assertion_name"
    manifest_file_path = "manifest_file_path"
    account_id = "account_id"

    def setUp(self) -> None:
        from servicecatalog_puppet.workflow.assertions import assertion_for_account_task

        self.module = assertion_for_account_task

        self.sut = self.module.AssertionForAccountTask(
            puppet_account_id=self.puppet_account_id,
            assertion_name=self.assertion_name,
            manifest_file_path=self.manifest_file_path,
            account_id=self.account_id,
        )

        self.wire_up_mocks()

    def test_params_for_results_display(self):
        # setup
        expected_result = {
            "puppet_account_id": self.puppet_account_id,
            "assertion_name": self.assertion_name,
            "account_id": self.account_id,
            "cache_invalidator": self.cache_invalidator,
        }

        # exercise
        actual_result = self.sut.params_for_results_display()

        # verify
        self.assertEqual(expected_result, actual_result)

    @mock.patch(
        "servicecatalog_puppet.workflow.manifest.manifest_mixin.ManifestMixen.manifest"
    )
    def test_requires(self, manifest_mock):
        # setup
        dependencies = list()
        requirements = dict(dependencies=dependencies,)

        klass = self.sut.get_klass_for_provisioning()

        for task in self.sut.manifest.get_tasks_for_launch_and_account(
            self.sut.puppet_account_id,
            self.sut.section_name,
            self.sut.assertion_name,
            self.sut.account_id,
        ):
            dependencies.append(
                klass(**task, manifest_file_path=self.sut.manifest_file_path)
            )

        expected_result = requirements

        # exercise
        actual_result = self.sut.requires()

        # assert
        self.assertEqual(expected_result, actual_result)
