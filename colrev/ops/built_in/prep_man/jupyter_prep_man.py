#! /usr/bin/env python
from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

import zope.interface
from dacite import from_dict

import colrev.env.package_manager
import colrev.env.utils
import colrev.record


if TYPE_CHECKING:
    import colrev.ops.prep_man

# pylint: disable=too-few-public-methods


@zope.interface.implementer(colrev.env.package_manager.PrepManPackageInterface)
class CurationJupyterNotebookManPrep:
    """Manual preparation based on a Jupyter Notebook"""

    settings_class = colrev.env.package_manager.DefaultSettings

    def __init__(
        self, *, prep_man_operation: colrev.ops.prep_man.PrepMan, settings: dict
    ) -> None:
        self.settings = from_dict(data_class=self.settings_class, data=settings)

        Path("prep_man").mkdir(exist_ok=True)
        if not Path("prep_man/prep_man_curation.ipynb").is_file():
            prep_man_operation.review_manager.logger.info(
                f"Activated jupyter notebook to"
                f"{Path('prep_man/prep_man_curation.ipynb')}"
            )
            colrev.env.utils.retrieve_package_file(
                template_file=Path("template/prep_man_curation.ipynb"),
                target=Path("prep_man/prep_man_curation.ipynb"),
            )

    def prepare_manual(
        self,
        prep_man_operation: colrev.ops.prep_man.PrepMan,  # pylint: disable=unused-argument
        records: dict,
    ) -> dict:

        input(
            "Navigate to the jupyter notebook available at\n"
            "prep_man/prep_man_curation.ipynb\n"
            "Press Enter to continue."
        )
        return records


if __name__ == "__main__":
    pass
