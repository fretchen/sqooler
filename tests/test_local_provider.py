"""
The tests for the storage provider using mongodb
"""

import uuid
import json
import shutil

from sqooler.storage_providers import LocalProvider
from sqooler.schemes import ResultDict, LocalLoginInformation

# get the environment variables
from decouple import config


class TestLocalProvider:
    """
    The class that contains all the tests for the dropbox provider.
    """

    @classmethod
    def teardown_class(cls) -> None:
        """
        Remove the `storage` folder.
        """
        shutil.rmtree("storage")

    def get_login(self) -> LocalLoginInformation:
        """
        Pull all the login information from the environment variables.
        """
        return LocalLoginInformation(base_path=config("BASE_PATH"))

    def test_upload_etc(self) -> None:
        """
        Test that it is possible to upload a file.
        """
        storage_provider = LocalProvider(self.get_login())
        # upload a file and get it back
        test_content = {"experiment_0": "Nothing happened here."}
        storage_path = "test/subcollection"

        job_id = uuid.uuid4().hex[:24]
        storage_provider.upload(test_content, storage_path, job_id)
        test_result = storage_provider.get_file_content(storage_path, job_id)

        assert test_content["experiment_0"] == test_result["experiment_0"]

        # move it and get it back
        second_path = "test/subcollection_2"
        storage_provider.move_file(storage_path, second_path, job_id)
        test_result = storage_provider.get_file_content(second_path, job_id)
        assert test_content["experiment_0"] == test_result["experiment_0"]

        # test that we can also get the job from the database
        test_result = storage_provider.get_job_content(second_path, job_id)
        assert test_content["experiment_0"] == test_result["experiment_0"]

        # test that we can update the file properly

        new_content = {"experiment_0": "What happened here."}
        storage_provider.update_file(new_content, second_path, job_id)
        test_result = storage_provider.get_job_content(second_path, job_id)
        assert new_content["experiment_0"] == test_result["experiment_0"]

        # clean up our mess
        storage_provider.delete_file(second_path, job_id)

    def test_upload_configs(self) -> None:
        """
        We would like to make sure that we can properly upload the configuration files
        that come from the spoolers.
        """

        storage_provider = LocalProvider(self.get_login())
        dummy_id = uuid.uuid4().hex[:5]
        backend_name = f"dummy_{dummy_id}"

        dummy_dict: dict = {}
        dummy_dict["gates"] = []
        dummy_dict["display_name"] = backend_name
        dummy_dict["num_wires"] = 3
        dummy_dict["version"] = "0.0.1"

        storage_provider.upload_config(dummy_dict, backend_name)

        # can we get the backend in the list ?
        # get the database on which we work
        uploaded_path = storage_provider.base_path + "/backends/configs"
        full_json_path = uploaded_path + "/" + backend_name + ".json"
        with open(full_json_path, "r", encoding="UTF-8") as json_file:
            result_found = json.load(json_file)

        if result_found is None:
            raise ValueError("The backend was not uploaded properly.")
        assert result_found["display_name"] == dummy_dict["display_name"]

        # make sure that the upload of the same backend does only update it.
        dummy_dict["num_wires"] = 4
        storage_provider.upload_config(dummy_dict, backend_name)
        with open(full_json_path, "r", encoding="UTF-8") as json_file:
            result_found = json.load(json_file)

        # clean up our mess and remove the file
        storage_provider.delete_file("backends/configs", backend_name)

    def test_get_next_job_in_queue(self) -> None:
        """
        Is it possible to work through the queue of jobs?
        """
        storage_provider = LocalProvider(self.get_login())

        # create a dummy backend
        dummy_id = uuid.uuid4().hex[:5]
        backend_name = f"dummy_{dummy_id}"

        # first we have to upload a dummy job
        job_id = (uuid.uuid4().hex)[:24]
        job_dict = {"job_id": job_id, "job_json_path": "None"}
        queue_path = "jobs/queued/" + backend_name
        job_dict["job_json_path"] = queue_path

        storage_provider.upload(job_dict, queue_path, job_id=job_id)

        # test if the file_queue is working

        job_list = storage_provider.get_file_queue(queue_path)
        assert job_list

        # the last step is to get the next job and see if this nicely worked out
        next_job = storage_provider.get_next_job_in_queue(backend_name)

        assert next_job["job_id"] == job_id

        # now also get the job content
        job_json_dict = storage_provider.get_job_content(
            storage_path=next_job["job_json_path"], job_id=next_job["job_id"]
        )
        assert "_id" not in job_json_dict.keys()

        # we now also need to test the update_in_database part of the storage provider
        result_dict: ResultDict = {
            "display_name": backend_name,
            "backend_version": "0.0.1",
            "job_id": next_job["job_id"],
            "qobj_id": None,
            "success": True,
            "status": "finished",
            "header": {},
            "results": [],
        }

        # upload the status dict without other status.
        status_msg_dict = {"status": "INITIALIZING"}
        status_json_dir = "status/" + backend_name
        storage_provider.upload(status_msg_dict, status_json_dir, job_id)

        status_msg_dict = {"status": "DONE"}
        storage_provider.update_in_database(
            result_dict, status_msg_dict, next_job["job_id"], backend_name
        )

        # we now need to check if the job is in the finished jobs folder
        job_finished_json_dir = "jobs/finished/" + backend_name

        finshed_job = storage_provider.get_file_content(job_finished_json_dir, job_id)
        assert finshed_job["job_id"] == job_id

        # we check if the status was updated
        status_dict = storage_provider.get_file_content(status_json_dir, job_id)
        assert status_dict["status"] == "DONE"

        # clean up the mess
        storage_provider.delete_file(job_finished_json_dir, job_id)
        storage_provider.delete_file(status_json_dir, job_id)
