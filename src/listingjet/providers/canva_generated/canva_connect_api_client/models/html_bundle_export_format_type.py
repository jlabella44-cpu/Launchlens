from enum import Enum


class HtmlBundleExportFormatType(str, Enum):
    HTML_BUNDLE = "html_bundle"

    def __str__(self) -> str:
        return str(self.value)
