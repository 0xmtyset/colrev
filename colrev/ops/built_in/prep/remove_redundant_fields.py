#! /usr/bin/env python
from __future__ import annotations

from typing import TYPE_CHECKING

import zope.interface
from dacite import from_dict
from thefuzz import fuzz

import colrev.env.package_manager
import colrev.ops.built_in.database_connectors
import colrev.ops.search_sources
import colrev.record

if TYPE_CHECKING:
    import colrev.ops.prep

# pylint: disable=too-few-public-methods


@zope.interface.implementer(colrev.env.package_manager.PrepPackageInterface)
class RemoveRedundantFieldPrep:

    """Prepares records by removing redundant fields"""

    settings_class = colrev.env.package_manager.DefaultSettings

    source_correction_hint = "check with the developer"
    always_apply_changes = False

    def __init__(
        self,
        *,
        prep_operation: colrev.ops.prep.Prep,  # pylint: disable=unused-argument
        settings: dict,
    ) -> None:
        self.settings = from_dict(data_class=self.settings_class, data=settings)

    def prepare(
        self,
        prep_operation: colrev.ops.prep.Prep,  # pylint: disable=unused-argument
        record: colrev.record.PrepRecord,
    ) -> colrev.record.Record:

        if "article" == record.data["ENTRYTYPE"]:
            if "journal" in record.data and "booktitle" in record.data:
                if (
                    fuzz.partial_ratio(
                        record.data["journal"].lower(), record.data["booktitle"].lower()
                    )
                    / 100
                    > 0.9
                ):
                    record.remove_field(key="booktitle")
        if "inproceedings" == record.data["ENTRYTYPE"]:
            if "journal" in record.data and "booktitle" in record.data:
                if (
                    fuzz.partial_ratio(
                        record.data["journal"].lower(), record.data["booktitle"].lower()
                    )
                    / 100
                    > 0.9
                ):
                    record.remove_field(key="journal")
        return record


if __name__ == "__main__":
    pass
