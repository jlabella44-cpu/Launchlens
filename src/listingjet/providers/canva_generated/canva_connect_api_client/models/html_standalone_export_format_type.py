from enum import Enum


class HtmlStandaloneExportFormatType(str, Enum):
    HTML_STANDALONE = "html_standalone"

    def __str__(self) -> str:
        return str(self.value)
