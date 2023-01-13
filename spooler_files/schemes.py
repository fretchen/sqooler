"""
The module that contains common logic for schemes, validation etc.
There is no obvious need, why this code should be touch in a new back-end.
"""

from typing import Tuple, TypedDict
from pydantic import ValidationError


class ExperimentDict(TypedDict):
    """
    A class that defines the structure of the experiments.
    """

    header: dict
    shots: int
    success: bool
    data: dict


class Spooler:
    """
    The class for the spooler. So it is not just a scheme, but it also contains some common logic.
    So it should most likely live in another file at some point.

    Attributes:
        n_max_wires: maximum number of wires for the spooler
        n_max_shots: the maximum number of shots for the spooler
        ins_schema_dict : A dictionary the contains all the allowed instructions for this spooler.

    Args:
        exper_schema: Sets the `exper_schema` attribute of the class
        ins_schema_dict : Sets the `ins_schema_dict` attribute of the class
    """

    def __init__(self, ins_schema_dict: dict):
        """
        The constructor of the class.
        """
        self.ins_schema_dict = ins_schema_dict

    def check_experiment(self, exper_dict: dict) -> Tuple[str, bool]:
        """
        Check the validity of the experiment.
        This has to be implement in each subclass extra.

        Args:
            exper_dict: The dictionary that contains the logic and should
                be verified.
        """
        raise NotImplementedError("Subclasses should implement this!")

    def check_instructions(self, ins_list: list) -> Tuple[str, bool]:
        """
        Check all the instruction to make sure that they are valid.
        """
        err_code = ""
        exp_ok = False
        for ins in ins_list:
            try:
                gate_dict = gate_dict_from_list(ins)
                self.ins_schema_dict[ins[0]](**gate_dict)
                exp_ok = True
            except ValidationError as err:
                err_code = "Error in instruction " + str(err)
                exp_ok = False
            if not exp_ok:
                break
        return err_code, exp_ok

    def check_json_dict(self, json_dict: dict) -> Tuple[str, bool]:
        """
        Check if the json file has the appropiate syntax.

        Args:
            json_dict (dict): the dictonary that we will test.

        Returns:
            bool: is the expression having the appropiate syntax ?
        """
        max_exps = 50
        for expr in json_dict:
            err_code = "Wrong experiment name or too many experiments"
            # Fix this pylint issue whenever you have time, but be careful !
            # pylint: disable=W0702
            try:
                exp_ok = (
                    expr.startswith("experiment_")
                    and expr[11:].isdigit()
                    and (int(expr[11:]) <= max_exps)
                )
            except:
                exp_ok = False
                break
            if not exp_ok:
                break
            # test the structure of the experiment
            err_code, exp_ok = self.check_experiment(json_dict[expr])
            if not exp_ok:
                break
            # time to check the structure of the instructions
            ins_list = json_dict[expr]["instructions"]
            err_code, exp_ok = self.check_instructions(ins_list)
            if not exp_ok:
                break
        return err_code.replace("\n", ".."), exp_ok


def gate_dict_from_list(inst_list: list) -> dict:
    """
    Transforms a list into an appropiate dictionnary for instructions.
    """
    return {"name": inst_list[0], "wires": inst_list[1], "params": inst_list[2]}


def create_memory_data(
    shots_array: list, exp_name: str, n_shots: int
) -> ExperimentDict:
    """
    The function to create memory key in results dictionary
    with proprer formatting.
    """
    exp_sub_dict: ExperimentDict = {
        "header": {"name": "experiment_0", "extra metadata": "text"},
        "shots": 3,
        "success": True,
        "data": {"memory": None},
    }

    exp_sub_dict["header"]["name"] = exp_name
    exp_sub_dict["shots"] = n_shots
    memory_list = [
        str(shot).replace("[", "").replace("]", "").replace(",", "")
        for shot in shots_array
    ]
    exp_sub_dict["data"]["memory"] = memory_list
    return exp_sub_dict
