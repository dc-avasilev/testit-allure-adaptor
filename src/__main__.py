from testit_allure_adaptor.reader import AttributeReader
from testit_allure_adaptor.utils import form_steps
from testit_allure_adaptor.utils import form_labels_namespace_classname_workitems_id
from testit_allure_adaptor.utils import form_links
from testit_allure_adaptor.utils import form_setup_teardown
from testit_allure_adaptor.utils import form_parameters
from testit_pytest.api import Api
from testit_pytest.json_fixture import JSONFixture
from datetime import datetime


def get_attachment(requests, attachments_sources, path):
    attachments = []
    for attachment_source in attachments_sources:
        attachments.append({'id': requests.load_attachment(open(f"{path}/{attachment_source['source']}", 'rb'))})
    return attachments


def console_main():
    reader = AttributeReader()
    data_tests, data_before_after = reader.get_attr()
    if data_tests:
        data_before_after = dict(sorted(data_before_after.items(), key=lambda x: x[0]))
        requests = Api(reader.get_url(), reader.get_privatetoken())
        tests_results_data = []
        for history_id in data_tests:
            labels, namespace, classname, workitems_id = form_labels_namespace_classname_workitems_id(data_tests[history_id]['labels'])

            attachments = get_attachment(requests, data_tests[history_id]['attachments'], reader.get_path()) if 'attachments' in data_tests[history_id] else []

            setup, results_setup, teardown, results_teardown, inner_attachments = form_setup_teardown(data_before_after, data_tests[history_id]['uuid'])
            attachments += get_attachment(requests, inner_attachments, reader.get_path())

            if 'steps' in data_tests[history_id]:
                steps, results_steps, inner_attachments = form_steps(data_tests[history_id]['steps'])
                attachments += get_attachment(requests, inner_attachments, reader.get_path())
            else:
                steps = []
                results_steps = []

            links = form_links(data_tests[history_id]['links']) if 'links' in data_tests[history_id] else []

            outcome = data_tests[history_id]['status'].title() if data_tests[history_id]['status'] in ('passed', 'skipped') else 'Failed'

            autotest = requests.get_autotest(history_id, reader.get_project_id()).json()
            if not autotest:
                autotest_id = requests.create_autotest(
                    JSONFixture.create_autotest(
                        history_id,
                        reader.get_project_id(),
                        data_tests[history_id]['name'],
                        namespace,
                        classname,
                        links,
                        steps,
                        setup,
                        teardown,
                        None,
                        data_tests[history_id]['description'] if 'description' in data_tests[history_id] else None,
                        labels
                    )
                )
            else:
                autotest_id = autotest[0]['id']
                if outcome == 'Passed':
                    requests.update_autotest(
                        JSONFixture.update_autotest(
                            history_id,
                            reader.get_project_id(),
                            data_tests[history_id]['name'],
                            namespace,
                            classname,
                            links,
                            steps,
                            setup,
                            teardown,
                            None,
                            data_tests[history_id]['description'] if 'description' in data_tests[history_id] else None,
                            labels,
                            autotest_id
                        )
                    )
                else:
                    requests.update_autotest(
                        JSONFixture.update_autotest(
                            history_id,
                            reader.get_project_id(),
                            autotest[0]['name'],
                            autotest[0]['namespace'],
                            autotest[0]['classname'],
                            links,
                            autotest[0]['steps'],
                            autotest[0]['setup'],
                            autotest[0]['teardown'],
                            autotest[0]['title'],
                            autotest[0]['description'],
                            autotest[0]['labels'],
                            autotest_id
                        )
                    )

            for workitem_id in workitems_id:
                requests.link_autotest(autotest_id, workitem_id)

            tests_results_data.append(
                JSONFixture.set_results_for_testrun(
                    history_id,
                    reader.get_configuration_id(),
                    outcome,
                    results_steps,
                    results_setup,
                    results_teardown,
                    data_tests[history_id]['statusDetails']['trace'] if 'statusDetails' in data_tests[history_id] else None,
                    links,
                    data_tests[history_id]['stop'] - data_tests[history_id]['start'],
                    None,
                    data_tests[history_id]['statusDetails']['message'] if 'statusDetails' in data_tests[history_id] else None,
                    form_parameters(data_tests['parameters']) if 'parameters' in data_tests else None,
                    attachments
                )
            )
        testrun_id = requests.create_testrun(JSONFixture.create_testrun(reader.get_project_id(), f'AllureRun {datetime.today().strftime("%d %b %Y %H:%M:%S")}'))
        if tests_results_data:
            requests.set_results_for_testrun(
                testrun_id,
                tests_results_data
            )


if __name__ == "__main__":
    console_main()
