import json
from pathlib import Path
from typing import Dict, List

BASE_DATA_PATH = Path("/home/symroe/Data/StaticOrgLayer/")


class Administration:
    def __init__(self, admin_id, data: Dict):
        self.admin_id = admin_id
        self.data = data

    @property
    def administration_type(self):
        if self.admin_id.startswith("D::"):
            return "division"
        return "organisation"

    @property
    def role_type(self):
        return self.admin_id.split("::")[-1]

    def friendly_name(self):
        org_name = self.data["organisation"]["common_name"]

        if self.administration_type == "organisation":
            if self.role_type == "mayor":
                org_name = f"Mayor of {org_name}"

            return org_name
        div_name = self.data["division"]["name"]

        if self.role_type == "local":
            div_name = f"{div_name} ward"

        if self.role_type == "parl":
            return f"MP for {div_name}"
        return f"{org_name}: {div_name}"

    def seats_contested(self): ...

    def friendly_description(self):
        return "asd"


class AdministrationsHelper:
    def __init__(self, administration_ids: List[str]):
        self.administration_ids = administration_ids
        self.data_path = BASE_DATA_PATH
        self.administrations: List[Administration] = []
        for admin_id in self.administration_ids:
            data = self.load_json(admin_id)
            self.administrations.append(Administration(admin_id, data))

    def load_json(self, administration_id):
        path = self.data_path / f"{administration_id}.json"
        with path.open() as f:
            return json.load(f)
