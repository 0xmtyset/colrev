#! /usr/bin/env python
"""Umbrella review"""
from dataclasses import dataclass

import zope.interface
from dataclasses_jsonschema import JsonSchemaMixin

import colrev.env.package_manager
import colrev.ops.search
import colrev.record.record

# pylint: disable=unused-argument
# pylint: disable=duplicate-code
# pylint: disable=too-few-public-methods


@zope.interface.implementer(
    colrev.env.package_manager.ReviewTypePackageEndpointInterface
)
@dataclass
class UmbrellaReview(JsonSchemaMixin):
    """Umbrella review"""

    settings_class = colrev.env.package_manager.DefaultSettings
    ci_supported: bool = True

    def __init__(
        self, *, operation: colrev.process.operation.Operation, settings: dict
    ) -> None:
        self.settings = self.settings_class.load_settings(data=settings)

    def __str__(self) -> str:
        return "umbrella review"

    def initialize(
        self, settings: colrev.settings.Settings
    ) -> colrev.settings.Settings:
        """Initialize an umbrella review"""

        settings.data.data_package_endpoints = [
            {
                "endpoint": "colrev.paper_md",
                "version": "1.0",
                "word_template": "APA-7.docx",
            },
        ]
        return settings